-- ============================================================================
-- VaultKey — db/init.sql  (BASELINE schema)
-- Creates the four core tables with constraints, indexes, soft-delete,
-- audit snapshots, and two seeded superadmins (break-glass).
--
-- Safe to re-run (idempotent): all statements use IF NOT EXISTS / ON CONFLICT
-- DO NOTHING so re-running against an existing DB will not break anything.
-- This is important for CI/CD pipelines.
--
-- Apply: psql -U postgres -d vaultkey -f db/init.sql
-- Incremental changes go in db/migrations/ and are handled by the CI/CD pipeline.
--
-- Design notes:
--   * Vault secrets are ENCRYPTED, never hashed → stored as ciphertext (bytea).
--   * No login passwords exist (Google-only login) → no password columns.
--   * entry_type distinguishes login vs api_key vs secure_note; username is
--     nullable (an API key like TS_AUTHKEY has no username).
--   * Soft-delete on vault_entries (history must survive).
--   * audit_log is append-only and self-contained (text snapshots), indexed on
--     timestamp for filtering + future archive-by-date.
--   * UUID PKs for users/vault_entries (non-enumerable, since their ids appear
--     in API calls); BIGSERIAL for audit_log (high-volume, internal).
--   * role/status/entry_type/action use TEXT + CHECK (easier to evolve by hand
--     than native ENUM types, given we have no ORM/Alembic).
-- ============================================================================

BEGIN;

-- gen_random_uuid() is built into PostgreSQL 13+. If on an older version,
-- uncomment the next line to enable it via pgcrypto:
-- CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ----------------------------------------------------------------------------
-- 1. users — who may access the app (the REAL access-control gate;
--            Google only authenticates, this table authorizes)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,                 -- from Google
    name        TEXT,                                 -- display name from Google
    role        TEXT NOT NULL DEFAULT 'member'
                    CHECK (role IN ('superadmin', 'member')),
    status      TEXT NOT NULL DEFAULT 'approved'      -- approval gate
                    CHECK (status IN ('approved', 'revoked')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  users         IS 'Approved-users allowlist. Pending requests live in access_requests table.';
COMMENT ON COLUMN users.status  IS 'approved = can log in; revoked = blocked.';


-- ----------------------------------------------------------------------------
-- 2. vault_entries — the credentials ("key table")
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vault_entries (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_type        TEXT NOT NULL,                  -- free-form category (SSH Key, Database, API Key, etc.)
    title             TEXT NOT NULL,                  -- label shown in the list
    username          TEXT,                           -- optional, plaintext
    encrypted_secret  BYTEA NOT NULL,                 -- ENCRYPTED ciphertext (password / API key / note body)
    url               TEXT,                           -- optional, plaintext
    description       TEXT,                           -- optional, plaintext context about the entry
    notes             BYTEA,                          -- ENCRYPTED (can hold secrets: recovery codes, key halves, etc.)

    -- accountability
    created_by        UUID NOT NULL REFERENCES users(id),
    updated_by        UUID REFERENCES users(id),

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- soft-delete (history/credentials must survive a delete)
    is_deleted        BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at        TIMESTAMPTZ,
    deleted_by        UUID REFERENCES users(id)
);

COMMENT ON COLUMN vault_entries.entry_type
    IS 'Free-form category label (SSH Key, Database, API Key, etc.). No fixed list.';
COMMENT ON COLUMN vault_entries.description
    IS 'Optional plaintext context about the entry. Not sensitive — do not put secrets here.';
COMMENT ON COLUMN vault_entries.encrypted_secret
    IS 'Ciphertext only (Fernet). Never plaintext, never hashed.';
COMMENT ON COLUMN vault_entries.notes
    IS 'Encrypted because notes can hold secrets (recovery codes, key halves, etc.).';

-- index for listing active (non-deleted) entries quickly
CREATE INDEX IF NOT EXISTS idx_vault_entries_active
    ON vault_entries (created_at DESC)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_vault_entries_created_by ON vault_entries (created_by);


-- ----------------------------------------------------------------------------
-- 3. totp_secrets — each user's 2FA seed (isolated; highly sensitive)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS totp_secrets (
    user_id     UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    secret      BYTEA NOT NULL,                       -- TOTP seed, ENCRYPTED at rest
    confirmed   BOOLEAN NOT NULL DEFAULT FALSE,       -- finished scanning the QR?
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON COLUMN totp_secrets.secret
    IS 'TOTP seed, encrypted at rest (as sensitive as the vault itself).';
COMMENT ON COLUMN totp_secrets.confirmed
    IS 'FALSE = enrollment started (QR shown) but not yet verified; TRUE = active.';


-- ----------------------------------------------------------------------------
-- 4. audit_log — append-only, self-contained record of every action
--    NOTE: no UPDATE/DELETE is ever issued against this table by the app.
--          Old rows leave ONLY via the future archive-then-prune job (docs/06).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id            BIGSERIAL PRIMARY KEY,
    user_id       UUID REFERENCES users(id),          -- who acted (for linking)
    actor_email   TEXT NOT NULL,                       -- SNAPSHOT (survives user changes)
    action        TEXT NOT NULL
                      CHECK (action IN (
                          'view',
                          'create',
                          'update',
                          'delete',
                          'login',
                          'approve_user',
                          'reject_user',
                          'revoke_user',
                          'reset_totp',
                          'enroll_totp'
                      )),
    entry_id      UUID REFERENCES vault_entries(id),   -- nullable; soft link
    target_label  TEXT,                                -- SNAPSHOT of entry title at action time
    detail        TEXT,                                -- optional free text ("changed username")
    ip_address    TEXT,                                -- optional
    "timestamp"   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  audit_log              IS 'Append-only. No edits, no per-row deletes — by anyone, superadmin included.';
COMMENT ON COLUMN audit_log.actor_email  IS 'Frozen snapshot so a row reads standalone even after the user changes.';
COMMENT ON COLUMN audit_log.target_label IS 'Frozen snapshot of the entry title (e.g. so "deleted TS_AUTHKEY" still reads).';

-- indexed on timestamp: powers the audit-page filtering AND the future
-- date-ranged archive-to-R2 job (docs/06).
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log ("timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action    ON audit_log (action);
CREATE INDEX IF NOT EXISTS idx_audit_log_user      ON audit_log (user_id);


-- ----------------------------------------------------------------------------
-- 5. access_requests — public access request form submissions
--    Pending users live here, NOT in users table.
--    Rows are never deleted — approved/rejected stay for audit trail.
--    Future: archive old rows to cold storage (see docs/06).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS access_requests (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    phone        TEXT NOT NULL UNIQUE,
    reason       TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'approved', 'rejected')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(), -- TIMESTAMPZ is timestamp stores with zone
    actioned_at  TIMESTAMPTZ,
    actioned_by  UUID REFERENCES users(id)
);


-- ----------------------------------------------------------------------------
-- 6. Seed TWO superadmins (break-glass: each can recover the other).
--    ON CONFLICT DO NOTHING makes this safe to re-run.
--    >>> REPLACE placeholder emails with real Google account emails. <<<
-- ----------------------------------------------------------------------------
INSERT INTO users (email, name, role, status) VALUES
    ('REPLACE_ME_admin1@example.com', 'Superadmin 1', 'superadmin', 'approved'),
    ('REPLACE_ME_admin2@example.com', 'Superadmin 2', 'superadmin', 'approved')
ON CONFLICT (email) DO NOTHING;

COMMIT;

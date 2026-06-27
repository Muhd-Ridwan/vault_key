# VaultKey

A self-hosted, shared credential vault for a small approved group of users.
Login is handled by Google (no passwords of our own). Secrets are encrypted at
rest. Sensitive actions (viewing or adding a secret) require a TOTP step-up.
Every meaningful action is recorded in an append-only audit log.

This document set captures **every design decision made during planning**,
including the reasoning and the honest tradeoffs — not just the final answers.
Read these before writing code so the *why* is never lost.

---

## What VaultKey is (and is not)

**It is:** an internal-tier shared vault. Think "the safe place where a small
team keeps the AWS root login, the office Netflix password, the `TS_AUTHKEY`
API key." Everyone approved sees the same shared list. Accountability comes from
the audit log, not from per-entry permissions.

**It is not:** a zero-knowledge, Bitwarden-grade vault. That tier was
**consciously ruled out** the moment we chose Google-only login (see
`02_security_model.md`). We know our security ceiling and we accept it
deliberately.

---

## The locked design (one-screen summary)

| Area | Decision |
|---|---|
| **Login** | Google Sign-In only. No typed username/password. No password to hash. No "forgot password." |
| **First admins** | Seed **two** superadmins at DB init (break-glass for each other). |
| **Access control** | Our own `users` approval table — *not* Google. Google authenticates; our allowlist authorizes. |
| **Vault secrets** | **Encrypted** at rest (Fernet), key in env/secrets manager, never in DB, never hashed. |
| **Step-up for view/add** | **TOTP** (`pyotp`), with a short unlock window so it isn't maddening. No NRIC. |
| **Database** | PostgreSQL, accessed via raw SQL with `psycopg[binary]` (no ORM). |
| **Migrations** | Manual, numbered `.sql` files + a tracking table. |
| **Frontend** | Vue 3 + Vite + Vue Router + Pinia. |
| **Backend** | FastAPI + Uvicorn. |
| **Infra** | Docker on a VPS, Cloudflare in front (**Full Strict**), frontend on Cloudflare Pages. |
| **Audit log** | Append-only. No per-row deletion by anyone, superadmin included. Archive >12mo to R2 later. |

---

## Document index

- `00_README.md` — this file
- `01_architecture.md` — tech stack, infra, the end-to-end login flow
- `02_security_model.md` — the central doc: hashing vs encryption, key handling, the security tier and its ceiling
- `03_database_schema.md` — the four tables, every column, and *why*
- `04_audit_logging.md` — append-only design, the lifecycle of a log row
- `05_development_roadmap.md` — the build order (layered, so you never debug five unknowns at once) + the guided-help list
- `06_future_enhancements.md` — cold-storage archiving, and other upgrade paths we deliberately deferred
- `../db/init.sql` — the baseline schema (all four tables + seeds), run once

---

## Non-negotiables (carry these into every step)

1. **Vault secrets are encrypted, never hashed.** Hashing is one-way; the eye
   button needs the value back. Hashing is only for things you verify, not
   things you retrieve. (There are no login passwords here anyway.)
2. **The encryption key never touches the database or git.** Env var / secrets
   manager only.
3. **All SQL is parameterized.** With no ORM, injection prevention is *our* job.
   Always `%s` placeholders, never f-strings/concatenation into SQL.
4. **The audit log is append-only and self-contained.** No edits, no per-row
   deletes, by anyone. Each row makes sense standalone.
5. **TLS everywhere, Cloudflare Full (Strict).** Never Flexible for a vault.
6. **Cloudflare authenticates the *transport*; our `users` table authorizes the
   *person*.** Google login lets anyone with a Google account in the door — the
   approval table is the real gate.

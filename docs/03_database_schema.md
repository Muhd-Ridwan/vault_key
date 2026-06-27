# 03 — Database Schema

PostgreSQL, accessed via raw SQL with `psycopg[binary]` (no ORM).

**Four tables:** `users`, `vault_entries`, `totp_secrets`, `audit_log`.
`users` connects to all three others.

---

## A myth to kill first

> "users and the vault table don't need to be connected, because everyone sees
> everything."

**This reasoning is wrong**, even though the *shared-visibility feature* is fine.
Two separate concerns were being collapsed:

1. **Visibility** (who can *see* entries) — yes, shared; everyone approved sees all.
2. **Accountability** (who *created/changed* an entry) — still needs a link.

In a **shared** vault, traceability is the whole reason it's safer than a sticky
note. Every entry records **who created it** and **who last modified it** via FKs
to `users`. The shared-list feature and the who-did-what link are independent —
don't let one argue away the other.

---

## Table 1 — `users`

Who is allowed into the app. The **real access-control gate** (Google only
authenticates).

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `email` | text, **unique** | from Google |
| `name` | text | display name from Google |
| `role` | enum-ish text | `superadmin` / `member` |
| `status` | enum-ish text | `pending` / `approved` / `revoked` — the approval gate |
| `created_at` | timestamptz | |

- New Google emails arrive as **`pending`** (an access request).
- **Seed two `superadmin` + `approved` rows** at init (break-glass).

---

## Table 2 — `vault_entries`

The credentials (the "key table").

**Design correction baked in:** entries are **not** all username+password pairs.
Some are a *single secret* with no username — an API key / auth token like
`TS_AUTHKEY`. So we use an explicit **`entry_type`** and make `username`
**nullable**.

| Column | Type | Plain/Enc | Notes |
|---|---|---|---|
| `id` | PK | — | |
| `entry_type` | text | plain | `login` / `api_key` / `secure_note` — tells the frontend how to render |
| `title` | text | plain | human label (e.g. `TS_AUTHKEY`, "AWS root login"). **Required for every type.** |
| `username` | text, **nullable** | plain | used **only** by `login` type |
| `encrypted_secret` | bytea/text | **ENCRYPTED** | the API key / password / note body. Required. Ciphertext only — never plaintext, never hashed. |
| `url` | text, nullable | plain | optional |
| `notes` | bytea/text, nullable | **ENCRYPTED** | optional; encrypted because it can hold secrets |
| `created_by` | FK → users.id | — | accountability |
| `updated_by` | FK → users.id, nullable | — | accountability |
| `created_at` | timestamptz | — | |
| `updated_at` | timestamptz | — | |
| `is_deleted` | boolean | — | **soft-delete** flag (default false) |

**To answer the original question directly:** `username` is the login username
for **`login`-type** entries only (e.g. `admin@site.com` + its password). For a
`TS_AUTHKEY` API key: `entry_type = api_key`, `username = NULL`,
`title = 'TS_AUTHKEY'`, and `encrypted_secret` holds the key itself. The `title`
is what every entry shares (the label in the list); `encrypted_secret` is what
the eye reveals.

**Plaintext-label rule (confirmed — do NOT encrypt the title):** `title` (e.g.
`TS_AUTHKEY`, "AWS root login"), plus `username`, `url`, and `entry_type`, are
stored **plaintext on purpose** so the vault list is readable and you know which
eye to click. Only `encrypted_secret` (and `notes`) are ciphertext. Consequence
to accept: a DB leak exposes the *labels* (the attacker learns this team stores
an AWS login and a `TS_AUTHKEY`) but **not the secret values**. This is the normal
trade every password manager makes. **Never put a secret inside a title** — title
is "AWS root login", never "AWS root login pw=hunter2". A future change that
"helpfully" encrypts the title would break the list view; don't.

**Soft-delete (confirmed):** deletes mark `is_deleted = true` and keep the row.
Hard deletes in a password manager are how you permanently lose a credential
nobody backed up — and they'd also break audit history.

**UI display rule (confirmed):** show **both** `created_by` and `updated_by` on
the entry detail (show `updated_by` only when it exists). The audit log page is
the deep forensic trail; the inline `updated_by` is the at-a-glance "is this
current value trustworthy" signal. The DB stores both regardless of UI.

---

## Table 3 — `totp_secrets`

Each user's 2FA seed. Separate table (not a column on `users`) because it's
highly sensitive and cleaner isolated.

| Column | Type | Notes |
|---|---|---|
| `user_id` | FK → users.id | |
| `secret` | text/bytea | the TOTP seed — **encrypted at rest** (as sensitive as the vault) |
| `confirmed` | boolean | did they finish scanning the QR, or only start? |
| `created_at` | timestamptz | |

---

## Table 4 — `audit_log`

Who did what. **Do not skip this** — in a shared vault where everyone sees
everything, this is the *only* way to answer "who viewed/added/deleted X." It's
what makes total visibility acceptable instead of reckless.

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `user_id` | FK → users.id | who acted (for linking) |
| `actor_email` | text | **snapshot** of who acted — survives later user changes |
| `action` | text | `view` / `create` / `update` / `delete` / `approve_user` / `login` |
| `entry_id` | FK → vault_entries.id, **nullable** | which entry (null for non-entry actions); soft link |
| `target_label` | text, nullable | **snapshot** of the entry title at the time (e.g. "deleted 'TS_AUTHKEY'") |
| `detail` | text, nullable | optional free text ("changed username") |
| `ip_address` | text, nullable | optional |
| `timestamp` | timestamptz | **indexed** (for filtering + future date-ranged archiving) |

**Design principles (see `04` for the full rationale):**
- **Append-only.** No edits, no per-row deletes — by anyone, **superadmin
  included**.
- **Self-contained.** Text snapshots (`actor_email`, `target_label`) mean a row
  reads sensibly even if the linked user or entry later changes/disappears, and
  even after the row is archived to cold storage standalone.
- **Views are logged too** (filtered in the UI), because reading a secret is the
  sensitive action in a shared vault.
- **Indexed on `timestamp`** — supports the audit page's filtering and the future
  archive-by-date job (see `06`).

---

## Migrations (no Alembic)

- Baseline `db/init.sql` (run once), then incremental numbered files in `db/migrations/`: `001_*.sql`, `002_*.sql`, …
- A tiny **tracking table** (e.g. `schema_migrations(version, applied_at)`)
  records which files have run, so you never re-apply or lose track.
- `db/init.sql` creates all four tables + the tracking table + seeds the two
  superadmins.

---

## Relationship summary

```
users ──< created_by / updated_by >── vault_entries
users ──< user_id >── totp_secrets
users ──< user_id >── audit_log
vault_entries ──< entry_id (nullable, soft) >── audit_log
```

`users` is the hub. The "two unconnected tables" idea would have shipped a vault
with no idea who did anything in it — fine for a personal notepad, wrong for a
shared credential store.

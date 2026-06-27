# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Read this fully before writing any code. Then read `/docs/00_README.md` →
> `06_future_enhancements.md` in order. The docs are the source of truth; this
> file is the short version of the rules.

## What this project is

A self-hosted, **shared** credential vault for a small approved team. Everyone
approved sees the same shared list of entries; the secret values are masked until
revealed. Accountability comes from an append-only audit log, not per-entry
permissions. This is an **internal-tier** vault (server-side encryption), _not_ a
zero-knowledge / Bitwarden-grade vault — that distinction is deliberate (see
`/docs/02_security_model.md`).

This is also a **learning project**. Build in small, testable layers and explain
what each piece does as you go. Do **not** scaffold the whole app at once.

## Tech stack (locked — do not substitute)

- **Frontend:** Vue 3 (Composition API) + Vite + Vue Router + Pinia + Google
  Identity Services + Axios
- **Backend:** FastAPI + Uvicorn
- **Config:** `pydantic-settings` — `Settings` class in `backend/config.py` reads `.env` from the repo root
- **DB access:** `psycopg[binary]`, **raw SQL, NO ORM** (no SQLAlchemy, no Alembic)
- **Auth:** `google-auth` (verify Google ID token) + `PyJWT` (our own session token)
- **2FA:** `pyotp` + `qrcode`
- **Encryption:** `cryptography` (Fernet)
- **DB:** PostgreSQL
- **Infra:** Docker + `docker-compose.yml` on a VPS (backend + PostgreSQL together);
  frontend on Cloudflare Pages (not in compose); Cloudflare Full (Strict) in front

## Commands

### Database

```bash
# Apply the baseline schema on a fresh database (run ONCE)
psql -f db/init.sql

# Apply a single migration manually
psql -f db/migrations/002_example.sql
```

### Backend (once `/backend` exists)

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload             # dev server
pytest backend/tests/                         # run all tests
pytest backend/tests/test_foo.py::test_bar    # run one test
```

### Docker (VPS — backend + PostgreSQL only)

```bash
docker compose up -d        # start backend + db
docker compose down         # stop
docker compose logs -f      # stream logs
docker compose exec db psql -U postgres vaultkey   # psql into the db container
```

### Frontend (once `/frontend` exists)

```bash
npm install
npm run dev    # Vite dev server
npm run build  # production build
```

## Environment variables

Copy `.env.example` to `.env` (never commit `.env`). Required keys:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | psycopg connection string |
| `FERNET_KEY` | Fernet encryption key (generate once with `Fernet.generate_key()`) |
| `JWT_SECRET` | Secret for signing our own session JWTs |
| `GOOGLE_CLIENT_ID` | OAuth client ID for Google token verification |

All vars are loaded once at startup via `backend/config.py` (`pydantic-settings`). Every other module imports the `Settings` singleton from there — no `os.getenv()` scattered around the codebase.

The `FERNET_KEY` must never touch the DB, code, or git — env var or secrets manager only.

## NON-NEGOTIABLES (violating any of these is a bug, not a style choice)

1. **Vault secrets are ENCRYPTED, never hashed.** Fernet. The eye button must be
   able to return the plaintext. There are no login passwords anywhere, so there
   is no password hashing in this project at all.
2. **All SQL is parameterized** — always `%s` placeholders passed as params.
   **Never** f-string or concatenate values into a SQL string. This is the whole
   injection defense; with no ORM it is our job. No exceptions, ever.
3. **The encryption key lives in an env var / secrets manager.** Never in the DB,
   never in code, never committed to git. Read it from the environment.
4. **The audit log is append-only.** No `UPDATE`, no `DELETE` against `audit_log`
   anywhere in the codebase. No "delete logs" endpoint or UI. Ever.
5. **Login is Google-only.** No username/password login, no "forgot password"
   flow. Do not add one. Google authenticates; our `users` table authorizes.
6. **Access control is the `users` approval table, not Google.** Every login must
   check `status` (pending/approved/revoked) and reject non-approved users.
7. **No NRIC** stored anywhere. The second factor is TOTP only.
8. **Do not invent crypto.** Use the named libraries as documented. If a task
   seems to require designing a crypto scheme, stop and flag it.

## Database

### Tables

- `users` — the real access gate (Google authenticates; this table authorizes)
- `vault_entries` — credentials with `entry_type` (`login` / `api_key` / `secure_note`)
- `totp_secrets` — per-user 2FA seed, isolated table, encrypted at rest
- `audit_log` — append-only, self-contained action log (BIGSERIAL PK for volume)

No `schema_migrations` table — migrations are tracked and applied by the CI/CD pipeline, not the app.

Full schema and rationale in `/docs/03_database_schema.md`.

### What is and isn't encrypted

| Column | Stored as |
|---|---|
| `title`, `username`, `url`, `entry_type` | **Plaintext** — the list must be readable |
| `vault_entries.encrypted_secret` | **Fernet ciphertext** (`bytea`) |
| `vault_entries.notes` | **Fernet ciphertext** (`bytea`) |
| `totp_secrets.secret` | **Fernet ciphertext** (`bytea`) |

Fernet returns `bytes` — pass `bytes` directly through psycopg for `bytea` columns.

### Baseline vs migrations

- `db/create_db.sql` — creates the database, run once before anything else.
- `db/init.sql` — creates all tables and indexes, run once on a fresh DB. Idempotent — safe to re-run in CI/CD pipelines.
- `db/migrations/` — incremental changes applied by the CI/CD pipeline in ascending numeric order (`001_*.sql`, `002_*.sql`, …).
- **Baseline maintenance workflow:** after enough migrations accumulate, fold them into `db/init.sql` and delete the migration files. Fresh installs always run only `db/init.sql`.
- Fresh-machine apply order: `db/create_db.sql` → `db/init.sql` → `db/migrations/` via CI/CD pipeline.

Before running `db/init.sql` in any real environment, replace the two
`REPLACE_ME_admin*@example.com` placeholders with real Google account emails.

## Architecture: request flow

```
Browser
  → Google Identity Services  →  Google ID token
  → POST /auth/google (token)
      → google-auth verifies token signature + audience + expiry
      → check users.status:
            approved  → issue our own PyJWT session token
            pending   → reject (or create pending row if first visit)
            revoked   → reject
  → all subsequent requests: Authorization: Bearer <our JWT>
      → view / add secret
            → backend checks TOTP unlock window (server-side, session-tied)
            → if window expired: client prompts 6-digit code
            → pyotp verifies → unlock window set (~10–15 min)
            → Fernet decrypts (view) or encrypts (add)
      → every action  →  INSERT into audit_log (append-only)
```

CORS must allow **only** the exact frontend origin. The session token travels as
`Authorization: Bearer`, not a cookie, to avoid cross-subdomain cookie footguns
between a Cloudflare Pages frontend and a separate API origin.

## Key behaviors to get right

- **TOTP unlock window is enforced SERVER-SIDE**, tied to the session — never a
  frontend flag. The backend refuses to decrypt unless the server-side unlock is
  currently valid. Frontend only _prompts_; backend _enforces_.
- **Labels are plaintext on purpose.** `title`, `username`, `url`, `entry_type`
  are stored unencrypted so the list is readable. Only `encrypted_secret` + `notes`
  are ciphertext. Never encrypt the title. Never put a secret in a title.
- **Soft-delete** vault entries (`is_deleted = true`), never hard-delete.
- **Audit rows are self-contained:** store text snapshots (`actor_email`,
  `target_label`) so a row reads standalone even after the user/entry changes.

## Build order (currently starting at step 2)

1. ✅ Postgres + schema (`db/init.sql` baseline done & tested)
2. **FastAPI skeleton + thin psycopg DB helper module + a migration runner.** No
   auth yet. Prove parameterized queries work end to end. ← START HERE
3. Google login + approval gate (verify ID token, check users table, issue our JWT)
4. Vault CRUD with Fernet encryption (no TOTP yet — get encryption reversible)
5. TOTP step-up (enroll via QR, verify, **server-side unlock window ~10–15 min**)
6. Audit logging wired into every action (view/create/update/delete/approve/login)
7. Vue frontend (Google button, list+eye+add, TOTP prompt, audit page)
8. Dockerize + deploy behind Cloudflare

Each step must work and be testable before starting the next.

## How I want you to work

- Explain your plan before generating large chunks; I'm learning, not just
  shipping. One layer at a time.
- When a decision could go multiple ways, ask me rather than assuming.
- If anything you're about to do conflicts with a non-negotiable above, **stop and
  say so** instead of working around it.

# 05 — Development Roadmap

Build in **layers**, each working before the next. The single biggest mistake is
wiring Google + TOTP + encryption + Vue all at once and drowning. Each step below
is testable on its own, so you're never debugging five unknowns simultaneously.

---

## Build order

1. **Postgres + schema.** Get the database and the four tables existing first
   (`db/init.sql`), plus the `schema_migrations` tracking table and the two
   seeded superadmins. Nothing works without data structure.

2. **FastAPI skeleton + DB connection.** Plain endpoints, no auth yet. Confirm the
   backend talks to Postgres through the thin `psycopg` helper module. Prove
   parameterized queries work end to end.

3. **Google login + approval gate.** Verify a Google ID token (`google-auth`),
   check the `users` table (approved / pending / revoked), issue your own session
   JWT (`PyJWT`). This is the hardest auth piece — do it alone.

4. **Vault CRUD with encryption.** Add / list / soft-delete entries, with secrets
   **encrypted at rest** (Fernet). Eye-click returns the decrypted value. **No
   TOTP yet** — just get encryption working and reversible.

5. **TOTP step-up.** Layer the 6-digit gate onto view/add: enrollment (QR via
   `qrcode`), verification (`pyotp`), and the **short unlock-window cache** so
   it's not maddening.

6. **Audit logging wired in.** Append a row on view/create/update/delete/
   approve_user/login, with the snapshot columns. Build the read-only audit page.

7. **Vue frontend.** Wire the UI to all of the above: Google button, entry list
   with eye + add, TOTP prompt, audit page. CORS + `Authorization: Bearer`.

8. **Dockerize + deploy** behind Cloudflare (Full Strict, origin cert, firewall
   locked to Cloudflare IPs).

> Audit logging (step 6) can also be folded into steps 4–5 as you build each
> action — log the action in the same handler that performs it. Listed separately
> here for clarity.

---

## Guided-help list (where to ask for a walk-through)

Flag these when you reach them; we tackle each live, not before:

1. **Reading library docs / using an installed package.** General skill — note:
   "using open source" here means installing **libraries** (`pip install` /
   `npm install` + import), **not** forking a big project like Bitwarden.
   Bitwarden is a *reference textbook* for ideas, never a codebase to graft onto.
   You are building VaultKey **from scratch**.

2. **Safe parameterized SQL with `psycopg` + the manual migration system**
   (numbered `.sql` files + `schema_migrations` tracking table). Replaces the
   SQLAlchemy/Alembic path.

3. **Google token verification + approval-gate endpoint** (the trickiest auth
   logic — steps 3–4 of the login flow).

4. **Issuing & verifying your own session JWT.**

5. **Fernet encryption** — encrypt on save, decrypt on eye-click, and **where the
   key lives** (env/secrets manager, never DB/git).

6. **TOTP enrollment (QR generation) + verification + the unlock-window caching.**

7. **Vue ↔ FastAPI wiring** — CORS, sending the Bearer token, the Google button.

8. **Dockerizing FastAPI + deploying behind Cloudflare.**

---

## What NOT to build in v1 (avoid over-engineering)

- **No audit archiver / cold-storage job.** Can't have 12 months of logs yet.
  Schema is already archive-ready; build the job months in, when the table
  actually grows. (See `06`.)
- **No zero-knowledge crypto / per-user keypairs / sharing scheme.** Ruled out by
  Google-only login; it's a future upgrade with real complexity (`06`).
- **No table partitioning.** Over-engineering at this scale.
- **No password hashing / "forgot password."** There is no login password.

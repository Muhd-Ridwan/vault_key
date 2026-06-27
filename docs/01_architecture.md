# 01 — Architecture

## Tech stack (locked)

### Frontend
- **Vue 3** (Composition API) + **Vite**
- **Vue Router** — routing
- **Pinia** — auth/session state + vault state
- **Google Identity Services (GIS)** — renders the Sign-In button, returns a
  Google **ID token** (a JWT signed by Google)
- **Axios** — API calls
- *(optional)* Tailwind or a component library (PrimeVue / Vuetify) for looks

### Backend
- **FastAPI** + **Uvicorn** (Gunicorn in front for production)
- **`psycopg[binary]`** — direct PostgreSQL access, raw SQL (no ORM, by choice)
- **`google-auth`** — verifies the Google ID token against Google's public keys
- **`PyJWT`** — issues/verifies *our own* session token after the Google check passes
- **`pyotp`** — TOTP for the view/add step-up
- **`qrcode`** — generates the QR image for TOTP enrollment
- **`cryptography`** (Fernet) — encrypts vault secrets at rest

**Explicitly NOT used:**
- No `passlib` / `bcrypt` — there is no login password to hash.
- No SQLAlchemy / Alembic — raw SQL by choice (tradeoffs in `02` and `03`).

### Database
- **PostgreSQL**

### Infra
- Backend in a **Docker** container on a **VPS**
- **Cloudflare** in front, **SSL/TLS mode: Full (Strict)**
- Frontend on **Cloudflare Pages**
- Subdomains under a single domain (e.g. `vault.example.com` for the app,
  `api.example.com` or similar for the backend)

---

## Why "no ORM, raw psycopg" — the honest tradeoff

**Gained:** you write real SQL and understand every query; less magic; lighter
deps; better learning.

**Taken on yourself:**
- **Migrations are manual.** No Alembic auto-generation. We use numbered `.sql`
  files + a tracking table (see `03` and `05`).
- **SQL-injection prevention is your job.** The rule is absolute: **always pass
  values as `%s` parameters, never concatenate/f-string into the SQL string.**
  For a vault this is the difference between safe and leaking the whole DB.
- A little more boilerplate (connections, cursors, row→dict mapping) — contained
  in one thin DB helper module so endpoints stay clean.

Verdict: fine — arguably better for learning — at VaultKey's ~4-table scale.

---

## The login flow (end to end)

1. User clicks **"Sign in with Google"** → GIS returns a **Google ID token** to
   the Vue app.
2. Vue sends that token to FastAPI.
3. FastAPI **verifies it with `google-auth`** (confirms Google signed it, checks
   audience + expiry).
4. FastAPI extracts the **email** and checks the `users` table:
   - **approved** → continue
   - **not present** → create as `pending` (this is an *access request*); reject login
   - **pending / revoked** → reject login
   This step is the **superadmin approval gate**.
5. If approved → FastAPI issues **its own session JWT**. That token — not
   Google's — authorizes every subsequent API call (sent as
   `Authorization: Bearer <token>`).
6. **View (eye) / Add** → frontend prompts for the **6-digit TOTP code** →
   FastAPI verifies with `pyotp` → on success, decrypts and returns the secret
   (or accepts the new entry). **Unlock is cached for ~5–15 min** so the user
   isn't entering a code on every click.

**Key distinction to hold onto:** Google sign-in proves *identity* and lets
*anyone with a Google account* authenticate. It does **not** restrict access.
The `users` approval table is what restricts access. Don't conflate the two.

---

## Cross-origin notes (frontend and backend on different subdomains)

- **CORS** in FastAPI must allow **only** the exact frontend origin.
- **Session token:** prefer returning the session JWT and sending it as an
  `Authorization: Bearer` header rather than a cookie. This avoids cross-site
  cookie footguns (SameSite, cookie-domain rules) between a Cloudflare-Pages
  frontend and a separate API.

---

## Infra / TLS — the Cloudflare rules

- **SSL/TLS mode = Full (Strict).** Never Flexible. Flexible encrypts only
  browser→Cloudflare and sends Cloudflare→origin over **plain HTTP** — for a
  vault that's disqualifying.
- The origin needs a valid cert Cloudflare trusts. Easiest: a **Cloudflare
  Origin Certificate** (free, 15-year) installed on the VPS, served on 443.
- **Lock the origin firewall to Cloudflare's published IP ranges**, so attackers
  can't bypass the proxy by hitting the raw origin IP directly.
- **Note on a single Cloudflare zone:** SSL/TLS mode is **per-zone**, so it
  applies to *all* subdomains of the one domain. You cannot natively set Strict
  on one subdomain and Flexible on another. The right fix is to put a valid cert
  on every origin (including any other project under the same domain) so the
  whole zone can be Full (Strict).

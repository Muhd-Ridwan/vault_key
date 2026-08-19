# VaultKey

A self-hosted, shared credential vault for personal usage. Secrets are encrypted at rest. Every action is recorded in an append-only audit log. Login is Google-only — no passwords.

## What it is

VaultKey is an **internal-tier** shared vault. Everyone approved sees the same list of entries. Secrets are masked until revealed. Accountability comes from the audit log, not per-entry permissions.

It is **not** a zero-knowledge, Bitwarden-grade vault — that tradeoff is deliberate. See `docs/02_security_model.md`.

## Tech stack

| Layer      | Technology                                                            |
| ---------- | --------------------------------------------------------------------- |
| Frontend   | Vue 3 (Composition API) + Vite + Vue Router + Pinia + Tailwind CSS v4 |
| Backend    | FastAPI + Uvicorn                                                     |
| Database   | PostgreSQL (raw SQL via `psycopg[binary]`, no ORM)                    |
| Auth       | Google Identity Services + PyJWT                                      |
| 2FA        | pyotp + qrcode                                                        |
| Encryption | Fernet (`cryptography`)                                               |
| Email      | Resend                                                                |
| Infra      | Docker + docker-compose (VPS) + Cloudflare Pages (frontend)           |

Login Page
<img width="974" height="754" alt="image" src="https://github.com/user-attachments/assets/e946e6b6-4cfa-465c-b980-bd967cba8416" />
<br />
Main Dashboard
<img width="2546" height="1265" alt="image" src="https://github.com/user-attachments/assets/3139d140-c152-419d-aba2-b339ddbe040f" />
<br />
Admin Panel
<img width="2554" height="936" alt="image" src="https://github.com/user-attachments/assets/487c32b2-9ecc-42dc-8990-4f8d493c9534" />
<br />
MFA Device
<img width="861" height="325" alt="image" src="https://github.com/user-attachments/assets/d05151b3-ddc4-4ef9-971a-a6c5ad4d1ee3" />
<br />
Adding New Entry
<img width="995" height="997" alt="image" src="https://github.com/user-attachments/assets/a79827cb-a217-40cf-ad58-802f268333b8" />





## File structure

```
vault_key/
├── backend/
│   ├── routers/
│   │   ├── auth.py          # Google login, access request form
│   │   ├── vault.py         # Vault CRUD with Fernet encryption
│   │   ├── totp.py          # TOTP enroll / verify / unlock / reset
│   │   └── admin.py         # Superadmin: users, requests, audit, settings
│   ├── audit.py             # log_action() helper (append-only)
│   ├── config.py            # pydantic-settings — reads .env
│   ├── crypto.py            # encrypt / decrypt via Fernet
│   ├── db.py                # psycopg connection pool + query helpers
│   ├── dependencies.py      # FastAPI deps: get_current_user, require_totp_unlock
│   ├── main.py              # App entry, CORS, router registration
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── AddEntryModal.vue
│       │   ├── EditEntryModal.vue
│       │   ├── TotpEnrollModal.vue
│       │   ├── TotpUnlockModal.vue
│       │   ├── ToastNotification.vue
│       │   └── UserMenu.vue
│       ├── pages/
│       │   ├── LoginPage.vue
│       │   ├── RequestAccessPage.vue
│       │   ├── VaultPage.vue
│       │   └── AdminPage.vue
│       ├── router/index.js
│       ├── services/api.js   # Axios instance + TOTP interceptor
│       ├── stores/
│       │   ├── toast.js
│       │   └── totp.js       # Promise-gate for TOTP unlock modal
│       └── utils/jwt.js      # Safe JWT payload parser
├── db/
│   ├── create_db.sql         # Creates the database (run once)
│   ├── init.sql              # Creates all tables + seeds (idempotent)
│   └── migrations/           # Incremental changes (applied in order)
├── docs/                     # Design decisions and architecture docs
├── .github/workflows/
│   └── deploy.yml            # CI/CD: build image → push → SSH deploy
├── docker-compose.yml
└── .env.example
```

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+

### 1. Clone and configure environment

```bash
git clone https://github.com/your-username/vault_key.git
cd vault_key
cp .env.example .env
```

Edit `.env` and fill in all values (see [Environment variables](#environment-variables) below).

### 2. Set up the database

```bash
# Create the database (run once)
psql -U postgres -f db/create_db.sql

# Create all tables and seed superadmins (idempotent)
psql -U postgres -d vaultkey -f db/init.sql
```

Before running `db/init.sql`, replace the two `REPLACE_ME_admin*@example.com` placeholders with real Google account emails.

### 3. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`.

### 4. Frontend

```bash
cd frontend
cp .env.example .env            # set VITE_API_BASE_URL and VITE_GOOGLE_CLIENT_ID
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## Environment variables

Copy `.env.example` to `.env` at the repo root. Required keys:

| Variable            | Purpose                                                            |
| ------------------- | ------------------------------------------------------------------ |
| `DATABASE_URL`      | psycopg connection string                                          |
| `FERNET_KEY`        | Fernet encryption key — generate once with `Fernet.generate_key()` |
| `JWT_SECRET`        | Secret for signing session JWTs                                    |
| `GOOGLE_CLIENT_ID`  | OAuth client ID from Google Cloud Console                          |
| `RESEND_API`        | Resend API key for transactional email                             |
| `RESEND_EMAIL_FROM` | Verified sender address on Resend                                  |
| `FRONTEND_URL`      | Allowed CORS origin (e.g. `https://yourapp.pages.dev`)             |

The frontend needs its own `frontend/.env`:

| Variable                | Purpose                     |
| ----------------------- | --------------------------- |
| `VITE_API_BASE_URL`     | Backend API base URL        |
| `VITE_GOOGLE_CLIENT_ID` | Same Google OAuth client ID |

**Never commit `.env` files. Never put `FERNET_KEY` in code or the database.**

## Docker (VPS deploy)

The backend and PostgreSQL run together via docker-compose. The frontend is deployed separately on Cloudflare Pages.

```bash
# Start backend + db
docker compose up -d

# Stream logs
docker compose logs -f

# psql into the db container
docker compose exec db psql -U postgres vaultkey
```

## Request flow

```
Browser
  → Google Identity Services  →  Google ID token
  → POST /auth/google
      → verify token signature + audience + expiry
      → check users.status (approved / revoked)
      → issue 8h PyJWT session token
  → all subsequent requests: Authorization: Bearer <JWT>
      → vault actions require active TOTP unlock window (server-side, 30 min)
      → if expired: frontend prompts 6-digit code → backend verifies → window reset
      → Fernet decrypts (view) or encrypts (add/edit)
      → every action → INSERT into audit_log (append-only)
```

## Security notes

- Secrets are **encrypted** (Fernet), never hashed — the eye button needs the value back
- All SQL uses `%s` parameterized queries — no f-strings into SQL, ever
- The `FERNET_KEY` lives only in env vars / secrets manager
- The audit log is append-only — no `UPDATE` or `DELETE` against it, ever
- Login is Google-only — no username/password, no "forgot password"
- TOTP unlock is enforced **server-side** — the frontend only prompts, the backend enforces

## Docs

Detailed design decisions are in `/docs`:

- `00_README.md` — overview
- `01_architecture.md` — tech stack and request flow
- `02_security_model.md` — encryption vs hashing, key handling, security tier
- `03_database_schema.md` — all tables and columns
- `04_audit_logging.md` — append-only design
- `05_development_roadmap.md` — build order
- `06_future_enhancements.md` — deferred upgrades

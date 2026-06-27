# 02 — Security Model

This is the most important document in the set. The whole project lives or dies
on getting these distinctions right.

---

## The one mistake that breaks everything: hashing vs encryption

There are **two different kinds of "password"** in this system, and they need
**opposite** treatment. Collapsing them is the single most common conceptual
error in building a vault.

### Type 1 — the login password (gets a user *into* the app)
- We **don't have one.** Login is Google-only.
- *If we did,* it would be **hashed + salted** (Argon2id), because login passwords
  only ever need to be **verified**, never retrieved. Hashing is **one-way**.
- Because we chose Google login: **no password hashing anywhere, no "forgot
  password" flow.** Recovery of *login* is Google's job (and Google does it
  better than we ever would).

### Type 2 — the vault secrets (the things behind the eye icon)
- These **must be shown again in plaintext** when someone clicks the eye. That is
  the entire point of the feature.
- Therefore they **cannot be hashed** — hashing is a shredder; you can't
  un-shred. If you hash them, the eye button has nothing to reveal.
- They must be **encrypted** (two-way: encrypt with a key, decrypt later with the
  same key).

### The rule, in one line
> **Hashing** is for secrets you only need to *verify*.
> **Encryption** is for secrets you need to *get back*.
>
> Vault secrets need to come back → **encrypt**, never hash.

---

## How vault secrets are encrypted

- Library: **`cryptography`** (Fernet) — authenticated symmetric encryption.
  (libsodium / `pynacl` secretbox is an equally fine alternative.)
- **Encrypt on save**, store only ciphertext in `vault_entries.encrypted_secret`.
- **Decrypt on eye-click**, only after TOTP step-up passes.
- **The key lives in an environment variable / secrets manager. Never in the
  database, never in code, never in git.**
  - Local dev: `.env` (gitignored).
  - Prod: a real secrets manager (Doppler, Infisical, AWS Secrets Manager, or the
    host's built-in secrets — Railway/Render/Fly all have them).

### Also encrypt these, not just the password field
Anything that can hold a secret gets encrypted:
- `encrypted_secret` — the API key / password / note body (**always** encrypted)
- `notes` — **encrypt if it can ever hold sensitive info** (recovery codes, the
  other half of a key, etc.). Safe default: treat notes as sensitive and encrypt.
- `totp_secrets.secret` — the TOTP seed itself is as sensitive as the vault;
  **encrypt it at rest too.**

### Plaintext (searchable metadata) vs encrypted (secrets)
- **Plaintext (searchable/displayable):** `title`, `username`, `url`, `entry_type`
- **Encrypted:** `encrypted_secret`, and `notes` if it can hold anything sensitive

---

## Our security tier — and its ceiling (stated honestly)

VaultKey uses **server-side encryption-at-rest with a server-held key.**

- **Protects against:** a **database-only** leak (SQL injection, a stolen DB
  dump, a backup left somewhere). The attacker gets **ciphertext**, useless
  without the key — which isn't in the DB.
- **Does NOT protect against:** **full server compromise.** If the attacker owns
  the running server, they have both the ciphertext *and* the key (it's in the
  env). **Game over.** This is our ceiling, and we accept it knowingly.

### Threat model — what each tier actually protects against

A common and dangerous misconception is that "encrypted at rest" means "safe if
the server is hacked." **It does not.** Read this table literally:

| Threat scenario | No encryption | **Server-side encryption (our v1)** | Zero-knowledge (v2, see `06`) |
|---|---|---|---|
| **DB-only leak** (stolen dump, SQL injection, stray backup) | ❌ secrets exposed | ✅ ciphertext only — key isn't in the DB | ✅ ciphertext only |
| **Full server compromise** (attacker owns the running app + env) | ❌ exposed | ❌ **exposed** — key sits in the env next to the app | ✅ ciphertext only — key never on the server |
| **Your own server operator can read secrets** | yes | **yes** (server decrypts on every view) | no (server never has the key) |

The middle column is where VaultKey v1 sits. The thing to internalize: **our v1
defends against a stolen database, NOT against a hacked server.** If the actual
requirement is "survive full server compromise / hacker sees only ciphertext,"
that is the **zero-knowledge** column, and it is the *only* column that delivers
it — see the decision note in `06` §B.

### Why we can't do better (the Google-login consequence)
The gold standard is **zero-knowledge / client-side encryption** (Bitwarden
style): the vault key is derived in the browser from a **master password the user
types**, and the server only ever sees ciphertext — so even full server
compromise leaks only ciphertext.

**Choosing Google-only login closed that door**, on purpose:
- With no typed password, there is **no user-held secret** to derive a key from.
- Google gives us *identity*, not key material.
- So zero-knowledge is **off the table** unless we later add a **separate vault
  passphrase** on top of Google login — which reintroduces the typing we were
  trying to avoid. (That's the upgrade path; see `06`.)

This was a deliberate trade: we offload all authentication risk to Google
(password storage, brute-forcing, resets, 2FA — all theirs, all better than ours)
in exchange for a lower encryption ceiling. For an internal shared vault, a sound
trade — as long as we **know** the ceiling and don't pretend we're zero-knowledge.

### Trust concentration (accept consciously)
- Hard **dependency on Google** (no Google account → can't use the app).
- A compromise of a user's **Google account** is a compromise of their vault
  access. Reasonable price for not handling passwords ourselves.

---

## TOTP step-up — what it does and does NOT do

- **What it is:** TOTP (RFC 6238), via **`pyotp`** + **`qrcode`** for enrollment.
  A rotating 6-digit code from an authenticator app (Google Authenticator /
  Authy). Gates **view (eye)** and **add**.
- **What it protects:** proves *the person acting is who they claim* — guards
  against a logged-in user casually clicking around / shoulder-surfing.
- **What it does NOT protect:** it is **authentication, not encryption.** If the
  DB leaks or the server is compromised, the attacker reads the store directly
  and the 6-digit code never enters the picture. TOTP is **not** a substitute for
  encrypting at rest. Both are needed; they do different jobs.
- **Usability rule:** a code on *every* eye-click is maddening. **Verify once,
  cache the unlock for ~5–15 min, then re-lock.** Build this from the start.
- Consider **different friction for read vs. add** (viewing is constant; adding
  is rare).

### Why NOT NRIC digits as a factor (rejected, do not add)
The idea of "NRIC last 3 digits" as a second factor was **rejected**:
- **Almost no entropy** — 3 decimal digits = 1,000 values, brute-forced in
  seconds. The last digit is gender-correlated, so effectively fewer.
- **Not secret** — NRIC is printed on the card and handed to banks, telcos,
  landlords. 2FA factors must be secret, possessed, or inherent. An *identifier*
  is not a *credential*.
- **Static** — can't rotate or revoke if exposed.
- **Legal exposure** — under Malaysia's PDPA, NRIC (even partial) is sensitive
  personal data; storing it adds compliance/liability for **zero** security gain.
  *(Not legal advice — confirm with a proper source before going near NRIC. The
  strong recommendation is simply: don't store it.)*

**The real second factor is TOTP.** WebAuthn/passkeys is a stronger future option
(see `06`), but TOTP is enough.

---

## Access control — the real gate

- **Google authenticates; the `users` approval table authorizes.**
- Anyone with a Google account can *authenticate*. Only **approved** emails get
  in. New emails land as **`pending`** (an access request) for a superadmin to
  approve.
- **Seed two superadmins** at DB init (break-glass for each other). One admin is a
  single point of failure; if that Google account is lost, the app becomes
  unmanageable.
- Account/role recovery inside the app is a **DB operation** (re-promote via SQL),
  not a user-facing "forgot" flow — because there is no password to forget.

---

## Security checklist (carry into build)

- [ ] Vault secrets **encrypted** (Fernet), never hashed
- [ ] Encryption key in **env/secrets manager**, never in DB/git
- [ ] `notes` encrypted if it can hold secrets; `totp_secrets.secret` encrypted
- [ ] **All SQL parameterized** (`%s`), never concatenated
- [ ] TOTP step-up on view/add, with **short unlock window**
- [ ] **Two** seeded superadmins
- [ ] Approval gate enforced on every login (pending/revoked rejected)
- [ ] Cloudflare **Full (Strict)** + origin cert + firewall locked to Cloudflare IPs
- [ ] CORS limited to the exact frontend origin
- [ ] Audit log append-only (see `04`)
- [ ] No NRIC stored, anywhere

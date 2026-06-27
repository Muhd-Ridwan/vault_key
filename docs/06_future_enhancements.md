# 06 — Future Enhancements

Deliberately deferred work. Captured here so the *plan* exists, but **none of this
is built in v1.** Building these now would be writing code for problems that can't
occur yet.

---

## A. Audit log archiving to cold storage (R2 / S3)

### The problem it solves
The audit log is **append-only** (no deletion — see `04`), and views are logged,
so it grows steadily. Over the long term that consumes DB space. We solve growth
by **archiving, never by deleting** — integrity is preserved because the data
isn't destroyed, just **moved** down the temperature gradient.

> Do the math before assuming you need this. An audit row is a few hundred bytes;
> a million rows ≈ a few hundred MB; Postgres handles tens of millions of rows in
> a simple indexed table comfortably. For VaultKey's likely volume you may not
> hit the ceiling for **years**. So: design for it now, **build it later** — only
> when you actually see the table growing.

### The lifecycle
```
hot in Postgres (≤ 12 months)
   → export rows older than 12 months to R2 as a dated immutable file
   → verify the export is uploaded AND readable
   → only then prune those rows from the hot table (oldest first, by date only)
   → retain in cold storage indefinitely
```

### The sacred ordering: archive → verify → prune
**Never delete first.** Never delete rows you haven't **confirmed** landed safely
and are **readable** in R2. A failed/corrupt upload you didn't verify, followed by
a prune, means you've permanently destroyed logs while believing you archived
them. For an audit log that's the one unforgivable bug. So always:
1. Export,
2. **Verify** (upload succeeded *and* the file reads back correctly),
3. Prune — by date only, oldest first.

### Storage choices & rules
- **Use Cloudflare R2 over S3** for this — **no egress fees**, and you're already
  in the Cloudflare ecosystem. If you ever pull archives back to investigate an
  incident, S3 charges egress; R2 doesn't.
- **Private bucket, no public access, encrypted at rest** — archived logs record
  who accessed what; treat them with the same care as the vault itself.
- **Append-only in cold storage too** — write each archive as a **dated immutable
  file** (e.g. `audit-2026-01.jsonl.gz`); never overwrite. The cold copy inherits
  the "never alter history" rule.
- **Self-contained export format** — JSON Lines (or CSV) carrying the text
  snapshots (`actor_email`, `target_label`) so an archived log is readable
  **standalone**, with no live DB needed to resolve IDs. (This is exactly why
  those snapshot columns exist in `audit_log` — they pay off here.)

### Why this is already easy in our schema
- `audit_log.timestamp` is **indexed** → date-ranged export is trivial.
- Snapshot columns make rows self-contained → archives read standalone.
- No schema change is needed to add the archiver later. It's a separate background
  job, not a table.

### What we will NOT do
- No "delete logs" button in the UI — ever.
- No per-row deletion — only **old, already-archived** data ever leaves the hot
  table.
- We never delete logs *newer* than the retention window to "save space" on
  demand. The only thing that exits is old, archived, verified data.

---

## B. Zero-knowledge upgrade (raising the encryption ceiling)

> **Decision record (do not re-litigate from scratch):**
> - **Trigger for doing this:** the named requirement "survive full server
>   compromise — if my server is hacked, the attacker sees only ciphertext."
>   That is a *real, specific* threat-model requirement, and zero-knowledge is the
>   **only** tier that delivers it. Server-side encryption (v1) does **not** — its
>   key sits in the server env (see the threat-model table in `02`).
> - **Plan:** ship **v1 server-side first**, upgrade to zero-knowledge as **v2**.
>   Reason: ZK is free in money but expensive in complexity (the shared-vault
>   key-wrapping below is where beginners ship something insecure). Building it as
>   your *first* crypto, wrapped inside five other unknowns, is the failure mode.
> - **v1 is not wasted:** schema, audit log, TOTP, Vue UI, approval flow's
>   non-crypto parts, and deployment all carry over. What changes in v2 is only
>   *where* encryption happens (browser, not server) and *how* sharing works
>   (key-wrapping, not "server hands it to everyone").
> - **Cost:** $0 in licensing. Uses free libraries (Web Crypto API / libsodium.js
>   in the browser, Argon2id/PBKDF2 for key derivation). The cost is engineering
>   time and the risk of subtle crypto bugs — not money.

Our current tier is **server-side encryption with a server-held key**; ceiling =
**full server compromise** (see `02`). To exceed that ceiling you'd move to
**zero-knowledge / client-side encryption**, where the server never holds the key.

Because login is Google-only (no typed secret), reaching zero-knowledge requires
adding a **separate vault passphrase** the user types — used in the browser to
derive the vault key (e.g. Argon2id). Consequences to weigh:
- Reintroduces typing (the thing Google-login removed).
- **Shared decryption across users** then needs an **asymmetric-key sharing
  scheme**: each user gets a keypair, and each entry's key is encrypted to every
  authorized user's public key. This is a **real complexity jump** and the most
  common place beginners build something insecure.
- Largely changes the "everyone logs in and sees the same shared list" model.

Defer unless/until the threat model genuinely demands surviving full server
compromise. Study Bitwarden's architecture as the reference if you go here.

---

## C. WebAuthn / passkeys (stronger step-up)

TOTP is our step-up factor and is sufficient. A stronger future option is
**WebAuthn / passkeys** (fingerprint, FaceID, security key) for the view/add gate
— phishing-resistant and nothing to type. Additive; not needed for v1.

---

## D. Other deferrals (noted, not planned)

- **Postgres time-partitioning** of `audit_log` — the "big-system" growth answer;
  over-engineering at our scale. Archiving (A) is the right-sized solution.
- **Per-entry / per-group permissions** — current model is a single shared list.
  Only revisit if the access model genuinely needs to stop being fully shared.

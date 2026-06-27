# 04 — Audit Logging

The audit log is what makes a **shared** vault (everyone sees everything)
acceptable instead of reckless. Total visibility + zero accountability is a
liability; the audit log supplies the accountability.

---

## The core principle: append-only

> An audit log's entire value rests on one guarantee: **nobody can alter or erase
> it — including admins.**

The moment a superadmin can delete log rows, the log is worthless **for the exact
scenario it exists for**. Walk the threat through: if the superadmin account is
the one that abuses access (views/exfiltrates a credential), and the superadmin
can also delete logs, they simply delete the evidence of their own action. That's
a security camera with a delete button wired to the person most able to do harm.

**Therefore:**
- **No edits.** Rows are never updated.
- **No per-row deletes.** By anyone. Superadmin included.
- **No "delete logs" button in the app UI.** Ever.

This was an explicit decision. The original idea — "superadmin can delete early
logs to save space" — was **rejected** because it destroys integrity. The
legitimate concern underneath it (disk growth) is solved by **archiving**, not
deletion (see `06`).

---

## What gets logged

`action` is one of: `view` / `create` / `update` / `delete` / `approve_user` /
`login`.

**Views are logged too** (not just writes). Reasoning: in a shared vault,
*reading* a secret is the sensitive event. If a credential later leaks, the
question is "who **looked at** it," not "who edited it." A log that captures edits
but not views misses the exact event you'll want during an incident.

Tradeoff accepted: view events are high-volume (a row per eye-click). That's fine
— rows are tiny — but the **audit page must let you filter by action type** so
views don't drown out the rarer create/update/delete events.

---

## Self-contained rows (why the snapshot columns exist)

A log row must make sense **on its own**, without depending on other tables still
holding matching data:

- **`actor_email`** — text snapshot of who acted. If a user is later revoked or
  removed, past log rows still say who did it.
- **`target_label`** — text snapshot of the entry's title at action time. If an
  entry is ever truly removed, "deleted entry 'TS_AUTHKEY'" still reads correctly
  without joining to a row that's gone.

This is standard audit-table design: **a log captures what was true when it
happened, frozen.** It never changes or blanks out because a row elsewhere
changed later. These snapshots also make archived logs (in cold storage) readable
**standalone**, with no live DB needed to resolve IDs (see `06`).

---

## Surviving deletion of what a row points to

Two defenses, both used:
1. **Soft-delete** on `vault_entries` — the row stays (flagged), so history's link
   survives naturally.
2. **Text snapshots** (`target_label`) — so even a hypothetical hard delete leaves
   a readable log.

The `entry_id` FK is a *soft* link for convenience when the entry still exists; it
is never relied on as the sole source of truth for what the row describes.

---

## The audit log page (UI)

A dedicated page, separate from the vault list. It should:
- List actions newest-first.
- **Filter by action type** (so you can hide `view` noise and see only
  create/update/delete, etc.).
- Show: timestamp, actor (email/name), action, target label, detail.
- Be **read-only.** No delete controls. No edit controls.

---

## Lifecycle of a single audit row

```
created (append-only)
   → lives hot in PostgreSQL  (≤ 12 months)
   → exported to R2 as a dated immutable file        ← future job, see 06
   → verified readable
   → pruned from the hot table (oldest first, by date only)
   → retained in cold storage indefinitely
```

Nothing is ever truly destroyed — it only moves down the temperature gradient.
That ordering (**archive → verify → prune, by date only, oldest first**) is what
keeps the log trustworthy while still controlling space.

---

## v1 scope for the audit log

- Build it **append-only**, **indexed on `timestamp`**, with the snapshot columns.
- **No deletion path** of any kind in v1.
- **No archiver in v1** — you can't have 12 months of logs until 12 months pass.
  The schema is already archive-friendly (clean indexed timestamp + self-contained
  rows); the archiver is a separate background job added later (`06`).

# ADR-0008: Deployment idempotency & rollback safety

## Status
Accepted — 2026-09-02

## Context
Deployment requests can be duplicated (double-click, client retry, at-least-once delivery).
A duplicate must not create a second deployment. Separately, rolling back Production must be
**safe** — never leave an environment with nothing running.

## Decision
- **Business uniqueness (the primary guard)**: a **partial unique index** on
  `(model_id, environment)` WHERE status is in-flight (`REQUESTED/VALIDATING/DEPLOYING`) allows
  **at most one active deployment per model per environment**. DB-enforced → race-free even for
  concurrent requests with *different* keys/versions. Violations surface as **`409`**. Scoped to
  in-flight states so a new deployment can still supersede a previously succeeded one. `model_id`
  is denormalized onto the row (immutable) so the index needs no join.
- **Idempotency key (complementary)**: `POST /deployments` accepts an optional client-supplied
  `idempotencyKey` (unique). A request whose key already exists returns the *existing* deployment
  with **`200`** (vs `202` for a newly-queued one). This dedupes *request replay*; the index above
  dedupes *intent* — a changed key cannot bypass it.
- **Retry**: only a `FAILED` deployment can be retried; it resets to `REQUESTED` (clears
  worker/lock/error) and is re-picked by the worker. Any other status → `409`.
- **Rollback safety**: only a `SUCCEEDED` deployment can be rolled back, and only if an
  **earlier successful deployment of a different version exists in the same environment**
  (found via the time-ordered UUIDv7 id). If none exists → `409` (refuse unsafe rollback). The
  rolled-back deployment records `rolledBackToId` for audit.
- All transitions append a **DeploymentEvent** (`requested`, `retry_requested`, `rolled_back`).

## Alternatives Considered
- **Idempotency key as the *only* dedup** — insufficient: a client that changes the key creates a
  second deployment for the same model/env. Rejected as the sole guard; the partial unique index
  enforces the real business invariant.
- **model+env vs version+env scope** — chose **model+env**: "≤1 in-flight deploy of the model per
  environment" keeps "what's deploying to prod" unambiguous; version+env would let two versions
  race into the same environment.
- **Check-then-insert in the service (no DB constraint)** — racy under concurrency; the partial
  unique index is the real, race-free guarantee.
- **Server-generated dedupe (hash of body)** — no client control over retry windows; a client
  key is explicit and standard. Rejected as the primary mechanism.
- **Allow rollback with no prior deployment (mark inactive)** — risks an empty environment.
  Rejected; refusing is the safe default.
- **Enforce idempotency only in the service, no DB constraint** — racy under concurrency. The
  unique constraint is the real guarantee.

## Consequences
### Positive
- Duplicate requests are safe (acceptance scenario); retry/rollback have clear, tested rules.
- Rollback cannot strand an environment; every action is auditable.

### Negative
- Idempotency requires clients to supply and reuse a key to benefit.
- Rollback "previous good" is per-environment/version; more complex traffic-shifting (canary)
  is out of scope.

## Follow-up Actions
- Optional idempotency-key TTL/expiry if key volume grows.
- Extend rollback to re-activate the target deployment when real traffic-routing exists.

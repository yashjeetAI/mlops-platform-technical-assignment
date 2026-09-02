# ADR-0007: Asynchronous deployment execution

## Status
Accepted — 2026-09-02

## Context
Deploying a model is long-running and can fail (validate → push → health-check). Doing it
inline would block the API and lose state on a crash. We need async execution that is
durable, observable (status/timeline), multi-worker-safe, and runnable offline via
`docker compose` with no external broker or cloud credentials.

## Decision
- The API **records intent and returns `202`** immediately; a **separate worker container**
  (same image, `python -m app.worker`) executes the deployment.
- **The `deployments` table is the queue.** Inserting the `REQUESTED` row *is* the enqueue —
  one transaction, no dual write (this is the answer to "external success / DB failure
  reconciliation": there is no external system to reconcile).
- **Dispatch = Postgres `LISTEN/NOTIFY`** (push, no Redis) + a **poll safety net**. The worker
  claims work with `SELECT … FOR UPDATE SKIP LOCKED` so replicas never collide.
- **Claim-and-release**: claim flips `REQUESTED → VALIDATING` and stamps `worker_id`/`locked_at`
  (short txn), then the slow work runs and status advances — so the UI sees live progress.
- **Crash recovery**: a reaper re-queues rows stuck in a transient state past a visibility
  timeout (`attempts` bounds retries, then `FAILED` with `worker_lost`).
- Each step writes a **DeploymentEvent** (audit timeline); the request's **correlation id** is
  carried on the row and re-bound in the worker (contextvars don't cross the process boundary).

## Alternatives Considered
- **Redis + RQ/Celery** — real broker, push-based, but adds infra and the dual-write gap.
  Deferred; the DB queue covers the need without it.
- **SQS / cloud queue** — great on AWS, but can't run offline for grading (creds/emulator) and
  is itself a dual-write. Documented as the production dispatch adapter behind the same seam.
- **FastAPI BackgroundTasks / in-process** — no durability across restarts; weak platform story.
- **Hold the row lock for the whole job** — simple but blocks a txn for the full deploy and
  hides progress. Rejected for claim-and-release.

## Consequences
### Positive
- Durable, atomic enqueue; survives restarts; multi-worker-safe; push-latency with poll
  fallback; no extra infrastructure or secrets.
- Full audit timeline + correlated logs across the API↔worker boundary.

### Negative
- Poll/reaper add a little periodic DB load (bounded by backoff/interval).
- `LISTEN/NOTIFY` is Postgres-specific; degrades to pure polling elsewhere (tests/SQLite).

## Follow-up Actions
- Add an `SqsDispatcher` adapter for AWS behind the same dispatch seam.
- Scale workers horizontally; tune visibility timeout and backoff under load.

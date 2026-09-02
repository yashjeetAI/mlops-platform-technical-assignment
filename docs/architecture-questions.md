# Architecture Q&A — G12 Scaling & Design Questions

Answers to the ten questions in the G12 expectations. Each states what the codebase does today
and how it extends. Cross-references point to the relevant ADRs.

---

### 1. How would this scale from 100 to 10,000 models?

**Today:** the registry is read-mostly and paginated. List endpoints return newest-first by the
time-ordered UUIDv7 `id` (no `OFFSET` scan of the whole table needed for the common "recent"
case), search is server-side (`?q=`), and every foreign key / lookup column is indexed. The UI
paginates and debounces search, so a 10k-model registry renders one page at a time.

**Extending:**
- **API + worker are stateless** → scale horizontally behind a load balancer; add workers to
  raise deployment throughput (they cooperate via `SKIP LOCKED`).
- **Reads** → add Postgres read replicas and a short-TTL cache (Redis) for hot list/detail
  queries; switch deep pagination to **keyset/cursor** pagination on `id`.
- **Writes** stay modest (registry changes are human-paced); the deployment queue is the only
  hot write path and is already partition-friendly by `model_id`.
- **Metrics** are the real volume driver — see #6.

The 100→10k jump is a capacity/indexing problem, not a redesign: the domain model and API
contract are unchanged.

---

### 2. How are conflicting promotions prevented?

Two layers. First, the **lifecycle state machine** ([ADR-0005](adr/0005-lifecycle-state-machine.md))
allows only forward transitions and requires an APPROVER for APPROVED/STAGING/PRODUCTION, so an
illegal promotion is rejected before it touches the DB. Second, for **deployment** conflicts, a
**partial unique index** `uq_active_deployment (model_id, environment) WHERE status IN
(REQUESTED,VALIDATING,DEPLOYING)` makes "at most one active deployment per model+environment"
a **database invariant** ([ADR-0008](adr/0008-idempotency-and-rollback.md),
[ADR-0009](adr/0009-deployment-eligibility.md)). Concurrent requests race to insert; exactly one
wins, the loser gets a `409`. This is race-free without application locking.

---

### 3. How is external success / internal database failure reconciled?

This is the classic dual-write problem, avoided by design: **the queue is a table**. Requesting
a deployment is a single DB transaction that inserts the `REQUESTED` row — there is no separate
broker to get out of sync with. The worker then follows a **claim → act → record** loop where
each status advance is committed transactionally with its `DeploymentEvent`.

For the genuinely external step (the runtime rollout), we treat it as **at-least-once with an
idempotency guard**: if the runtime call succeeds but the DB write of `SUCCEEDED` fails, the row
stays claimed and the **reaper** re-queues it after the visibility timeout; the re-run must be
idempotent (reconcile "is this version already the active rollout?" before acting). The audit
trail (`attempts`, events) makes the reconciliation observable. A production adapter would record
the runtime's external id on the row so re-runs can query rather than re-apply.

---

### 4. How are multiple model runtimes supported?

The worker's execution step is deliberately behind a seam: the runner drives the state machine
and calls an **execution strategy**, which today simulates the rollout. Supporting real,
heterogeneous runtimes (scikit-learn container, PyTorch/Triton, ONNX runtime, a managed endpoint)
is a **strategy/adapter per runtime**, selected by the version's `framework` (already an enum on
the model). Each adapter implements the same contract — `validate()`, `deploy()`, `rollback()`,
`healthcheck()` — so the domain layer stays runtime-agnostic and the guarantees (idempotency,
audit, rollback) are enforced once, above the adapter.

---

### 5. How would multi-tenancy work?

Single-tenant today, but the model is tenant-ready. The pragmatic path is a **`tenant_id` scoping
column** on the top-level aggregates (Model, Deployment, User) with:
- a tenant claim in the JWT and a dependency that **binds tenant to every query** (defence in
  depth: a service-layer filter plus Postgres **row-level security** so a missing filter can't
  leak data);
- tenant-scoped uniqueness (e.g. model `key` unique per tenant, and the active-deployment index
  extended to `(tenant_id, model_id, environment)`);
- per-tenant quotas/rate-limits on the deployment queue so one tenant can't starve others.

Stronger isolation (schema-per-tenant or database-per-tenant) is available for regulated tenants
at higher operational cost; the shared-schema + RLS approach covers the common case first.

---

### 6. How are large metric volumes partitioned?

Metrics are the write-heavy, append-only, time-series table. Scaling plan:
- **Time-based partitioning** (native Postgres declarative partitioning by `timestamp`, e.g.
  daily/weekly) so queries hit recent partitions and old ones can be detached/dropped cheaply.
- **Retention + downsampling**: keep raw samples for a short window, roll up to hourly/daily
  aggregates for history (the monitoring UI already consumes summaries, not every raw point).
- **Read path**: the dashboard reads only the *latest* sample per (version, environment) plus a
  short recent series, which is index-friendly and partition-local.
- **At real scale**, offload to a purpose-built TSDB (Timescale/Prometheus/ClickHouse) and keep
  the relational registry as the system of record; the metric write becomes a fire-and-forget
  emit rather than a synchronous insert.

---

### 7. How is unsafe rollback prevented?

Rollback is constrained on multiple axes ([ADR-0008](adr/0008-idempotency-and-rollback.md)):
- **Authorization** — only ADMIN may roll back (`require_roles(ADMIN)`).
- **Preconditions** — you can only roll back a **SUCCEEDED** deployment; there must be a prior
  good deployment to roll back *to*, and the target is validated.
- **Forward-only + auditable** — rollback is modelled as a **new superseding deployment** that
  records `rolled_back_to_id`, not a mutation of history, so the audit trail and the
  one-active-per-environment invariant both hold.
- **Same async guarantees** — it runs through the worker with idempotency and event logging, so
  a rollback can itself be retried safely.

---

### 8. How are zero-downtime schema migrations handled?

Alembic drives schema; PostgreSQL is the target. The discipline is **expand → migrate →
contract**:
1. **Expand** — add columns/tables as nullable/with defaults; deploy code that can read old and
   new shapes (backwards-compatible migration, no blocking locks — create indexes
   `CONCURRENTLY`, avoid long table rewrites).
2. **Backfill** in batches out of band.
3. **Migrate** — switch the app to the new shape once data is populated.
4. **Contract** — drop the old column/table in a later release after the old code is gone.

Migrations run before the new app version serves traffic; readiness (`/ready`) gates rollout.
Because API JSON is decoupled from the DB (camelCase boundary, [ADR-0004](adr/0004-api-naming-convention.md)),
internal column changes don't ripple to clients. The rule: **never combine an
expand and a contract in the same release**.

---

### 9. How is Angular isolated from backend internals?

Several deliberate seams:
- **Stable REST contract** in **camelCase** ([ADR-0004](adr/0004-api-naming-convention.md)) — the
  DB/Python stay snake_case; internal renames never reach the client.
- **Same-origin `/api`** via nginx/proxy — the frontend never knows a backend host, and there's
  no CORS coupling; the backend can move/split without a UI change.
- **Typed service layer**: components talk to Angular services (`registry.service`,
  `monitoring.service`) that own HTTP + DTO interfaces, so a schema tweak touches one file, not
  every component. Errors are normalised (`apiErrorMessage`) so the UI renders failures
  consistently regardless of backend shape.
- **OpenAPI** (`/docs`) is the contract of record and could generate the client types.

---

### 10. How would work be split across teams?

The modular boundaries map cleanly to ownership (see the [delivery plan](delivery-plan.md)):
- **Registry & lifecycle** — models/versions, state machine, approvals, audit.
- **Deployment platform** — the worker, queue semantics, retry/rollback, runtime adapters (#4).
- **Monitoring & observability** — metrics ingestion, rollups, dashboards, tracing.
- **Frontend/UX** — the Angular console, consuming the stable API contract (#9).
- **Platform/infra** — CI/CD, Docker/K8s, migrations, secrets.

The **API contract + ADRs are the coordination interface**: teams integrate through documented
endpoints and decisions, not shared internals. Vertical slices (a feature that crosses UI→API→DB)
are delivered by a pair of frontend+backend owners against an agreed contract, keeping teams
decoupled day to day.

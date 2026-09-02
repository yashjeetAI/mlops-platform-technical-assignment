# Known Limitations

Deliberate scope boundaries for the assignment time-box. Each notes the impact and the intended
resolution (tracked in the [roadmap](roadmap.md)).

## Simulated deployment runtime
The worker drives the real deployment **state machine, timing, events, and metrics**, but the
rollout step itself is simulated — it does not call a Kubernetes/KServe/serving backend.
*Impact:* deployments always "succeed" unless failure is simulated. *Resolution:* per-framework
runtime adapters behind the existing execution seam (architecture Q&A #4).

## Test database vs. production database
Unit/API tests run on in-memory **SQLite**; the app + migrations run on **PostgreSQL**.
*Impact:* Postgres-only mechanisms — the `uq_active_deployment` partial index,
`FOR UPDATE SKIP LOCKED`, `LISTEN/NOTIFY` — are guarded in code and verified against the running
DB, not in the fast suite. *Resolution:* a Postgres-backed integration lane in CI.

## Single tenant
No `tenant_id` scoping yet. *Impact:* one logical organisation. *Resolution:* tenant column + JWT
claim + row-level security (architecture Q&A #5).

## Observability depth
Structured logs, correlation IDs, health/readiness, and monitoring metrics are in place;
**OpenTelemetry tracing and a metrics exporter (Prometheus) are not**. *Impact:* no distributed
traces or external dashboards out of the box. *Resolution:* OTel instrumentation + Grafana
dashboard (roadmap).

## Metric volume
Metrics live in a single unpartitioned table. *Impact:* fine at assignment scale, not at millions
of samples. *Resolution:* time-based partitioning + downsampling / TSDB (architecture Q&A #6).

## Auth scope
JWT + RBAC with seeded demo users and a shared demo password; no refresh tokens, password reset,
SSO, or user-management UI. Demo credentials and the default `JWT_SECRET` are for the demo only
and **must** be overridden in any real deployment.

## Frontend testing depth
Component/service unit tests exist; **no browser E2E** (Playwright/Cypress) suite yet. Screenshots
in the README are captured manually against the running stack.

## Deep pagination
List endpoints use `limit`/`offset`. *Impact:* very deep offsets scan rows. *Resolution:*
keyset/cursor pagination on the UUIDv7 `id` (architecture Q&A #1).

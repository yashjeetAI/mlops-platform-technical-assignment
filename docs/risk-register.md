# Risk Register

Likelihood (L) and Impact (I): **L**ow / **M**edium / **H**igh. Ordered by exposure.

| # | Risk | L | I | Mitigation | Owner |
|---|------|---|---|------------|-------|
| R1 | **Runtime integration** proves harder than the simulated seam suggests (heterogeneous frameworks, partial failures) | M | H | Spike one adapter first; strict `validate/deploy/rollback/healthcheck` contract; at-least-once + idempotency already in place | Deployment Platform |
| R2 | **Metric volume** outgrows a single table; dashboard queries slow | M | H | Time-based partitioning + retention/downsampling; move to TSDB when needed (arch Q&A #6) | Monitoring |
| R3 | **Split-brain / dual-write** between queue and DB | L | H | Avoided by design — queue *is* a DB table, single-transaction enqueue; reaper for crash recovery ([ADR-0007](adr/0007-async-deployment-execution.md)) | Deployment Platform |
| R4 | **Unsafe or unauthorised rollback** causes an outage | L | H | ADMIN-only; preconditions (SUCCEEDED + valid target); rollback is a superseding, audited deployment ([ADR-0008](adr/0008-idempotency-and-rollback.md)) | Registry & Governance |
| R5 | **Schema migration** locks tables / breaks a live release | M | M | Expand→migrate→contract; `CONCURRENTLY` indexes; readiness-gated rollout; camelCase boundary decouples clients (arch Q&A #8) | Platform / DevEx |
| R6 | **Secrets leak** (JWT secret, DB creds) | L | H | Env-only secrets, `.env.example` documents knobs, nothing sensitive in Git; rotate `JWT_SECRET` per environment | Platform / DevEx |
| R7 | **SQLite/Postgres test gap** hides a Postgres-only bug | M | M | Guard Postgres-only paths; add a Postgres integration lane in CI (roadmap Phase 1) | Platform / DevEx |
| R8 | **Concurrency guard** regressions (double active deployment) | L | H | Enforced by partial unique index, not app logic; covered by conflict tests ([ADR-0009](adr/0009-deployment-eligibility.md)) | Deployment Platform |
| R9 | **Multi-tenant data leakage** once tenancy lands | L | H | Service-layer tenant filter **plus** Postgres row-level security (defence in depth); tenant-scoped uniqueness (arch Q&A #5) | Registry & Governance |
| R10 | **Key-person / bus factor** on the async subsystem | M | M | ADRs capture rationale; pairing on the worker; runbooks in prod-readiness checklist | Tech Lead |
| R11 | **Scope creep / gold-plating** beyond the graded requirements | M | M | Requirements-driven backlog; ADRs justify complexity; reject "complexity without rationale" in review | Tech Lead |

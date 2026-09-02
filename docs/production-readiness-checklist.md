# Production-Readiness Checklist

Gate before promoting a release to production. Items marked *(gap)* are honest current limitations
tracked in [known-limitations](known-limitations.md) / [roadmap](roadmap.md).

## Reliability & data
- [x] Async work is **crash-safe**: claim with `SKIP LOCKED`, visibility-timeout **reaper**
      re-queues abandoned rows; retries bounded by `attempts`.
- [x] **No dual-write**: enqueue is a single-transaction DB insert; queue and registry cannot
      diverge.
- [x] Concurrency invariants enforced in the **database** (partial unique index), not app logic.
- [ ] **Backups + restore drill** for Postgres; PITR configured. *(gap — infra)*
- [ ] **Schema migrations** run zero-downtime (expand→contract), gated by readiness. *(process ready; verify per release)*

## Security
- [x] JWT auth + **RBAC** on governance-critical endpoints (least privilege).
- [x] Secrets via env; **nothing sensitive in Git**; `.env.example` documents required config.
- [ ] `JWT_SECRET` rotated per environment; demo password/users removed for real deployments. *(must-do at deploy)*
- [ ] Rate limiting / WAF at the edge; dependency & image scanning in CI. *(gap)*
- [ ] TLS termination + HSTS at nginx/ingress. *(gap — infra)*

## Observability
- [x] **Structured JSON logs** with per-request **correlation IDs**, carried API→worker.
- [x] **Health** (`/health`) and **readiness** (`/ready`, checks DB) endpoints for probes.
- [x] Failure **classification** in logs (`domain_error`, `deployment_failed`).
- [ ] **Metrics export (Prometheus)** + **traces (OpenTelemetry)** + Grafana dashboard + alerts. *(gap — roadmap Phase 2)*
- [ ] SLOs/SLIs defined (deploy success rate, queue latency, error rate) with paging. *(gap)*

## Operability
- [x] One-command bring-up: `docker compose up --build` (db, backend, worker, frontend).
- [x] **CI** green: lint + tests + build on every PR.
- [x] Stateless API + worker → **horizontal scale**; workers cooperate via the queue.
- [ ] Kubernetes manifests/Helm with probes, resource limits, HPA, and a rollout strategy. *(gap — roadmap)*
- [ ] Runbooks for stuck deployments, reaper behaviour, and rollback; on-call ownership. *(gap)*

## Functional gates
- [x] Lifecycle, eligibility, idempotency, retry, and rollback covered by automated tests.
- [x] Sample data seeded idempotently for demo/eval.
- [ ] **Real runtime adapter** replaces the simulated rollout. *(gap — roadmap Phase 1)*
- [ ] Load/soak test at target scale (10k models, metric ingest). *(gap)*

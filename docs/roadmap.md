# Roadmap

## Now — delivered in this submission

- Model & version **registry** with search + pagination scaled for 10k models.
- **Forward-only lifecycle** with approvals and full audit trail ([ADR-0005](adr/0005-lifecycle-state-machine.md)).
- **Asynchronous deployment** via a separate worker (DB-as-queue, `SKIP LOCKED`, `LISTEN/NOTIFY`
  + poll/reaper) with **retry** and safe **rollback** ([ADR-0007](adr/0007-async-deployment-execution.md), [ADR-0008](adr/0008-idempotency-and-rollback.md)).
- **Stage-gated eligibility** + one-active-deployment-per-environment DB invariant ([ADR-0009](adr/0009-deployment-eligibility.md)).
- **Monitoring** with per-version metrics and health rollups.
- **RBAC** (JWT, four roles), **structured logging** + correlation IDs, health/readiness.
- **CI** (lint + tests + build) and this documentation set.

## Near-term (next quarter)

- **Real runtime adapters** (K8s/KServe; sklearn/ONNX/PyTorch) behind the execution seam.
- **OpenTelemetry** tracing + **Prometheus** metrics export + a **Grafana** operational dashboard.
- **Postgres integration lane** in CI covering the partial index / `SKIP LOCKED` / `NOTIFY` paths.
- **Metric partitioning** + retention/downsampling; **keyset pagination** for deep lists.
- Read replica + hot-read cache; secrets manager integration.

## Future

- **Multi-tenancy**: tenant scoping, row-level security, per-tenant quotas ([arch Q&A #5](architecture-questions.md)).
- **Drift & quality alerting** with thresholds and notifications; auto-rollback on SLO breach.
- **Progressive delivery** (canary / blue-green) via the runtime adapters.
- **Approval policies** (multi-approver, environment-specific gates) and change-management hooks.
- **Generated API clients** from OpenAPI; **browser E2E** suite; load/soak testing.

## Explicitly deferred

Model training, feature stores, and experiment tracking — this is a **control plane**, and those
belong to adjacent platforms it would integrate with, not own.

# Delivery Plan — Small Team

How I would take this from prototype to production with a team of **~4–5 engineers** over a
quarter, and how ownership maps to the architecture's module boundaries.

## Team shape & ownership

| Stream | Owns | Skills |
|--------|------|--------|
| **Registry & Governance** | Models/versions, lifecycle state machine, approvals, audit | Python/FastAPI, domain modelling |
| **Deployment Platform** | Worker, queue semantics, retry/rollback, runtime adapters | Python, concurrency, K8s |
| **Frontend / UX** | Angular console, states, accessibility | Angular, TypeScript, RxJS |
| **Platform / DevEx** | CI/CD, Docker/K8s, migrations, observability, secrets | Infra, SRE |

One **tech lead** (me) owns the API contract, the ADRs, cross-cutting invariants, and review
standards. Streams integrate through the **documented API + ADRs**, not shared internals, so they
move independently.

## Ways of working

- **Vertical slices**: each feature crosses UI→API→DB and ships behind the stable contract;
  a frontend+backend pair delivers it against an agreed schema.
- **Trunk-based** with short-lived `feat/*`/`fix/*` branches → PR → green CI → review → merge.
  Never commit to `main` (enforced by hook).
- **Definition of Done**: tests (incl. an error path), docs/ADR if a decision changed, CI green,
  observability for new workflows (logs + correlation), and a reviewer sign-off against the
  [code-review checklist](code-review-checklist.md).

## Phased roadmap

**Phase 0 — Foundations (done in this submission).** Registry, lifecycle+approvals, async
deployment with retry/rollback, monitoring, RBAC, audit trails, CI, docs/ADRs.

**Phase 1 — Make it real (weeks 1–4).** First real runtime adapter (containerised sklearn/ONNX)
behind the execution seam; Postgres integration lane in CI; secrets management; `.env`→config
hardening. *Exit:* a genuine deployment reaches a running endpoint.

**Phase 2 — Operate at scale (weeks 5–8).** OpenTelemetry traces + Prometheus metrics + Grafana
dashboard; metric partitioning/retention; keyset pagination; read replica + cache for hot reads.
*Exit:* dashboards + SLOs; 10k-model registry demonstrated.

**Phase 3 — Platform (weeks 9–12).** Multi-tenancy (tenant scoping + RLS + quotas); additional
runtime adapters; drift/quality alerting; user management. *Exit:* second tenant onboarded in
isolation.

## Milestones & risks

Milestones are the phase exits above; delivery risks are tracked in the
[risk register](risk-register.md) with owners and mitigations. We de-risk the highest-uncertainty
item first each phase (Phase 1: the runtime adapter contract) via a spike before committing the
stream.

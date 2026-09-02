# ADR-0009: Deployment eligibility (stage-gating)

## Status
Accepted — 2026-09-02

## Context
Requesting a deployment must be governed by the version's lifecycle stage — not just a
Production approval check. Two gaps existed: a DRAFT version could deploy to dev/staging, and
an ARCHIVED (retired) version could still deploy if once approved. The lifecycle stages
(STAGING, PRODUCTION) also correspond to deployment environments, so the stage should gate
which environment a version may reach.

## Decision
Stage-gate deployments (`services/deployment_policy.py`): a version may deploy to an
environment only if its stage is high enough.

| Version stage | Deployable environments |
|---|---|
| DRAFT | none |
| VALIDATED | DEVELOPMENT |
| APPROVED | DEVELOPMENT |
| STAGING | DEVELOPMENT, STAGING |
| PRODUCTION | DEVELOPMENT, STAGING, PRODUCTION |
| ARCHIVED | none |

- Enforced at request time (`_assert_deployable` → `409`) **and** re-checked in the worker
  (belt-and-suspenders, since stage can change between request and execution).
- One source of truth (`DEPLOYABLE_STAGES` / `is_deployable`) shared by API and worker.

## Alternatives Considered
- **Approval-only gate (previous)** — Production requires `approved`; dev/staging allow anything.
  Rejected: lets DRAFT deploy and leaves ARCHIVED deployable.
- **Environment == stage (1:1)** — deploy to STAGING env only if stage is exactly STAGING.
  Rejected: too rigid (a Production-stage version couldn't be redeployed to staging).
- **No re-check in the worker** — rejected; the version could be archived between request and
  execution, so the worker re-validates.

## Consequences
### Positive
- "Promote the version, then deploy" is an explicit, auditable governance flow.
- DRAFT/ARCHIVED can never be deployed; Production requires full promotion.

### Negative
- Deploying requires promoting the version to the matching stage first (intended friction).
- Couples the lifecycle stage to environment eligibility (acceptable; that is the intent).

## Follow-up Actions
- Surface the required stage in the deploy dialog when a version is ineligible.

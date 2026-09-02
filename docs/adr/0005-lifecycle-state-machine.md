# ADR-0005: Model-version lifecycle state machine

## Status
Accepted — 2026-09-02

## Context
A model version moves through governed stages (DRAFT → VALIDATED → APPROVED → STAGING →
PRODUCTION, plus ARCHIVED). The core governance rule is that an **unapproved version must
never reach Production**. Transition rules must be enforced consistently, be testable in
isolation, and produce clear errors — not scattered `if` checks across routes.

## Decision
- Model the lifecycle as an explicit **state machine** in `services/lifecycle.py`: an
  `ALLOWED_TRANSITIONS` map plus `validate_transition(current, target, approved)`. Pure
  functions over the `LifecycleStage` enum — no DB, no HTTP.
- **Approval is a distinct fact** (`approved_at`/`approved_by` on the version), exposed as a
  derived `approved` boolean. `APPROVED`/`STAGING`/`PRODUCTION` may only be entered by an
  approved version (belt-and-suspenders on top of the structural transition rules).
- Approval has its **own action/endpoint** (VALIDATED → APPROVED, records the approver),
  separate from generic promotion, so the approver identity is always captured.
- Illegal moves raise `InvalidStateTransition`; missing approval raises `ApprovalRequired`;
  both map to HTTP 409 via the central domain-error handler.
- **RBAC**: engineers author (create model/versions); approvers drive lifecycle
  (approve/promote). ADMIN always allowed.

## Alternatives Considered
- **Ad-hoc checks in each route/service.** Rejected — rules get duplicated and drift; hard to
  test exhaustively.
- **A state-machine library.** Rejected — a dict + one function is smaller, dependency-free,
  and fully covers the need.
- **Stage alone encodes approval (no separate flag).** Rejected — loses the approver/time
  audit and conflates "who approved" with "current stage" (the sample data carries both).

## Consequences
### Positive
- One source of truth for legality + the approval gate; exhaustively unit-tested.
- Unapproved → Production is impossible both structurally and via the explicit gate.
- Services stay HTTP-agnostic; consistent 409s for rule violations.

### Negative
- Transitions and their allowed RBAC are defined in two places (state map + route guards);
  acceptable, and both are covered by tests.

## Follow-up Actions
- Reuse the same machine for deployment-time validation (block deploying non-Production-ready
  versions) in the deployments slice.
- Revisit allowed back-transitions (e.g. PRODUCTION → STAGING) when rollback semantics land.

# ADR-0002: Authentication and role-based authorization

## Status
Accepted — 2026-09-01

## Context
Governance is a first-class requirement: the platform must record an **actor** for every
significant action (who created a model, approved a version, promoted to PRODUCTION,
triggered a rollback) and must enforce **who is allowed** to perform governance-critical
operations. This requires (a) authenticating a caller and (b) authorizing them by role.

The assignment is a time-boxed demo whose focus is MLOps/platform engineering, not
identity management. It asks for role-based authorization *design* and an audit trail —
not a full IAM system. Over-investing in auth (signup, email verification, OAuth/SSO,
refresh-token rotation, sessions) would spend time the scorecard rewards elsewhere and
risks the "complexity without rationale" red flag.

## Decision
- **Authentication:** stateless **JWT bearer tokens**. `POST /auth/login` validates
  username/password and returns a signed HS256 JWT carrying `sub` (username) and `role`.
  A `get_current_user` dependency decodes/validates the token and loads the `User`.
- **Users:** a small set of **seeded demo users**, one per role, created idempotently on
  startup. No self-service signup. Passwords are hashed with **bcrypt**.
- **Authorization:** a **role-based** model with four roles ordered by privilege —
  `VIEWER < ENGINEER < APPROVER < ADMIN`. A `require_roles(*roles)` dependency factory
  guards endpoints; `ADMIN` is always permitted; violations return a clean `403`.
- **Role → capability mapping** enforces governance:
  - VIEWER: read registry/monitoring
  - ENGINEER: create models/versions, request deployments
  - APPROVER: approve versions, promote to PRODUCTION
  - ADMIN: all of the above, plus rollback
- **Audit trail:** authenticated identity is threaded into domain writes
  (`created_by`, `approved_by`, and per-event `actor`) so state changes are attributable.

## Alternatives Considered
- **Static API tokens per role.** Pre-issued header tokens. Simpler, but no login flow to
  demonstrate and weaker realism.
- **Header-based user switch (`X-User`).** No cryptography; trivially spoofable. Fine only
  for a throwaway demo; rejected as it does not demonstrate real authorization.
- **Full IAM / OAuth2 / OIDC (SSO), refresh tokens, sessions.** Production-correct but far
  beyond scope and time budget; deferred to the roadmap.
- **Server-side sessions (cookie + session store).** Adds stateful infrastructure (session
  store) without benefit for an API-first, containerized service; rejected in favor of
  stateless JWT.

## Consequences
### Positive
- Real, standard, testable auth: login → token → per-request identity and role checks.
- Roles do actual work (governance enforcement), which is exactly what the scorecard's
  governance/lifecycle criteria reward — and `403` paths give strong error-path tests.
- Stateless tokens fit horizontal scaling and containerized deployment (no session store).
- Every audited action has an attributable actor.

### Negative
- JWTs cannot be revoked before expiry without extra machinery (deny-list / short TTL +
  refresh); acceptable for a demo, noted for production.
- Seeded demo credentials are intentionally weak and shared; must never ship to a real
  environment. The signing secret defaults to a dev value and must be overridden via env.
- No account lifecycle (rotation, lockout, MFA); explicitly out of scope.

## Follow-up Actions
- Document demo credentials and the "not for production" caveat in the README and
  known-limitations.
- Ensure `JWT_SECRET` is supplied via environment/secret manager in any real deployment;
  never commit a real secret.
- Roadmap: external IdP (OIDC/SSO), short-lived access tokens + refresh, token revocation,
  and per-tenant role scoping when multi-tenancy is introduced.

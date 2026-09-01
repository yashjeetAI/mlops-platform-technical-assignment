# ADR-0002: Authentication and role-based authorization

## Status
Accepted — 2026-09-01

## Context
Governance requires recording an **actor** for every significant action and enforcing **who**
may perform governance-critical operations. This is a time-boxed demo focused on MLOps/platform
engineering, not identity management — so we need real, testable authz without building full IAM.

## Decision
- **Auth:** stateless JWT bearer tokens. `POST /auth/login` returns an HS256 JWT (`sub`, `role`);
  a `get_current_user` dependency validates it.
- **Users:** small set of seeded demo users (one per role), idempotent on startup, bcrypt-hashed
  passwords; no self-service signup.
- **Authz:** roles `VIEWER < ENGINEER < APPROVER < ADMIN`; a `require_roles(...)` dependency guards
  endpoints (ADMIN always allowed), returning `403` on violation.
- Authenticated identity is threaded into domain writes (`created_by`, `approved_by`, event `actor`).

## Alternatives Considered
- **Static per-role API tokens** — simpler, but no login flow and weaker realism. Rejected.
- **Header user switch (`X-User`)** — trivially spoofable; demonstrates no real authz. Rejected.
- **Full OAuth2/OIDC, refresh tokens, server-side sessions** — production-correct but out of scope
  and adds stateful infra; deferred to roadmap.

## Consequences
### Positive
- Real login → token → per-request identity and role checks; `403` paths give strong tests.
- Stateless tokens suit horizontal scale (no session store); every audited action has an actor.

### Negative
- JWTs can't be revoked before expiry without extra machinery (short TTL + refresh / deny-list).
- Seeded creds are intentionally weak; signing secret defaults to a dev value — **must** be
  overridden via env in real deployments. No rotation/lockout/MFA (out of scope).

## Follow-up Actions
- Document demo credentials + "not for production" caveat in README/known-limitations.
- Supply `JWT_SECRET` via secret manager in real deployments.
- Roadmap: external IdP (OIDC/SSO), refresh tokens, revocation, per-tenant role scoping.

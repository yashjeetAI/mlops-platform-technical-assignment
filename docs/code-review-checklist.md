# Code-Review Checklist

The reviewer's job is to protect the **invariants** and the **contract**, not to rewrite the
author's style. Pull requests are small, single-purpose, and green in CI before review.

## Correctness & domain
- [ ] Change respects the **lifecycle** rules (forward-only; approval where required) — no bypass
      of `services/lifecycle.py`.
- [ ] Deployment changes preserve **eligibility** and **one-active-per-environment** (guard in the
      DB, not just the app).
- [ ] **Idempotency / rollback** semantics intact; rollback stays ADMIN-only and audited.
- [ ] New/changed behaviour is **attributable**: audit event written, actor + correlation id set.
- [ ] Error paths return the right **status + `{detail}`** (404/409/403/422), not a 500.

## API & schema
- [ ] JSON stays **camelCase** at the boundary; Python/DB stay snake_case (no hand-mapping).
- [ ] List endpoints are **paginated** (`{items,total,limit,offset}`) and **newest-first by id**;
      search is server-side.
- [ ] Backwards-compatible contract change (or versioned); OpenAPI still accurate.

## Persistence & migrations
- [ ] Model change has an **Alembic migration**, generated against **Postgres**, and it is
      reversible.
- [ ] Migration is **safe to run live** (expand→contract split; `CONCURRENTLY` indexes; no long
      locks). Committed migrations are **not edited** after the fact.
- [ ] Queries are indexed for the access pattern; no accidental N+1.

## Security
- [ ] Endpoint carries the correct `require_roles(...)` guard; least privilege.
- [ ] **No secrets** in code, tests, or fixtures; config via env.
- [ ] Input validated by Pydantic; no trust of client-supplied ids for authorization.

## Tests & quality
- [ ] Tests cover the **happy path + at least one error/conflict path**; assertions check the
      contract, not implementation details.
- [ ] `ruff` clean; type hints present; no dead code or stray `print`.
- [ ] Frontend: loading/error/empty states handled; `prettier` clean; a service/component test
      where logic was added.

## Observability & docs
- [ ] New long-running or cross-service work **logs structured events** with correlation id.
- [ ] Decisions of consequence recorded as an **ADR**; README/docs updated if behaviour changed.
- [ ] **Complexity is justified** in the PR description — reject complexity without rationale.

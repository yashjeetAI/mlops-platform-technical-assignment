# ADR-0004: API naming convention (camelCase JSON boundary)

## Status
Accepted — 2026-09-01

## Context
Three layers with different idiomatic casing meet at the API: the database and Python
backend use `snake_case` (SQL convention + PEP 8), while the Angular/TypeScript client uses
`camelCase`. The JSON contract must pick one casing, and whichever we pick, one side risks
carrying non-idiomatic names.

## Decision
- **DB and Python code stay `snake_case`** (idiomatic; unchanged).
- **The JSON wire format is `camelCase`.** A shared Pydantic base (`CamelModel`) applies
  `alias_generator=to_camel` with `populate_by_name=True`; FastAPI serializes responses by
  alias. All request/response schemas extend `CamelModel`.
- **The TypeScript client uses `camelCase`** interfaces directly — no mapping layer.

## Alternatives Considered
- **snake_case JSON everywhere.** Zero backend config, but forces non-idiomatic snake_case
  into all TS models. Rejected — pushes the awkwardness onto every frontend consumer.
- **camelCase in Python too.** Rejected — violates PEP 8; reviewers would read it as wrong.
- **Manual mapping/DTO layer in the frontend.** Rejected — boilerplate per model; the
  Pydantic alias generator does the same job once, at the source.

## Consequences
### Positive
- Every layer stays idiomatic; translation happens once at the boundary.
- Frontend models need no adapters; `populate_by_name` still accepts snake_case input.
- Reinforces separation of the API contract from backend internals.

### Negative
- Response field names differ from Python attribute names (alias indirection); mitigated by
  centralizing the rule in one `CamelModel` base.

## Follow-up Actions
- All new schemas must extend `CamelModel`.
- Keep the contract covered by a test asserting camelCase keys (e.g. `fullName`, not `full_name`).

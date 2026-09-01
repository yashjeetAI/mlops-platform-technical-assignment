# ADR-0003: Identifier strategy (UUID primary keys)

## Status
Accepted — 2026-09-01

## Context
Every entity needs a primary key. The platform targets thousands of models/deployments across
environments and (per G12 questions) possible multi-tenancy, so IDs may be generated in more
than one place and merged without collision. Keys also appear in URLs and payloads. This ADR
concerns the *technical* PK, not user-facing business identifiers (e.g. a model slug).

## Decision
Use **time-ordered UUIDv7** primary keys, generated application-side.

- SQLAlchemy `Uuid(as_uuid=True)` → native `uuid` on Postgres, `CHAR(32)` on SQLite.
- Shared `UUIDPrimaryKeyMixin` with `default=uuid.uuid7`, inherited by all models.
- Provided by stdlib `uuid.uuid7` (**Python 3.14+**); local + container runtimes standardized on 3.14.

## Alternatives Considered
- **Auto-increment integer** — best locality/size, but needs a central sequence, is enumerable,
  and risks collisions when merging across environments. Rejected as PK.
- **UUIDv4 (random)** — poor B-tree index locality on high-volume inserts. Rejected in favor of v7,
  which keeps v4's benefits and adds a sortable timestamp prefix at no dependency cost.
- **ULID / KSUID** — similar benefits but non-standard and an extra dependency. Rejected for stdlib v7.

## Consequences
### Positive
- IDs generated anywhere with no central sequence (scale, future multi-tenancy).
- Non-enumerable; safe to merge across environments; time-ordered → good index locality.

### Negative
- Requires Python 3.14+ (satisfied by standardizing both runtimes on 3.14).
- 16-byte keys are larger than ints; time-ordered keys expose approximate creation time (not a concern here).

## Follow-up Actions
- For high-write tables (metrics), evaluate partitioning/aggregation independent of key type.
- Ensure new models inherit `UUIDPrimaryKeyMixin`.

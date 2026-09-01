# ADR-0003: Identifier strategy (UUID primary keys)

## Status
Accepted — 2026-09-01

## Context
Every persisted entity (users, and upcoming models, versions, deployments, events,
metrics) needs a primary key. The choice of key type has consequences for scalability,
security, cross-environment data movement, and index performance.

The platform is expected to scale toward thousands of models and deployments, potentially
across multiple plants/environments and (per the G12 questions) multi-tenancy. IDs may
need to be generated in more than one place and merged without collision. Keys also appear
in URLs (`/models/{id}`) and API payloads.

Note: user-facing *business* identifiers (e.g. a model slug like `pump-failure-predictor`)
are a separate concern from the *technical* primary key and are modeled independently; this
ADR is about the technical PK.

## Decision
Use **time-ordered UUID (version 7) primary keys** for all entities, generated
application-side.

- Column type is SQLAlchemy's dialect-aware `Uuid(as_uuid=True)` → native `uuid` on
  PostgreSQL, `CHAR(32)` on SQLite (tests). Values are Python `uuid.UUID`.
- A shared `UUIDPrimaryKeyMixin` defines the `id` column with `default=uuid.uuid7`, so all
  tables get identical, consistent keys.
- API schemas expose the id as a `UUID`.
- UUIDv7 is provided by the standard library `uuid.uuid7` (**Python 3.14+**); the runtime
  (local and the container image) is standardized on 3.14 to guarantee availability.

## Alternatives Considered
- **Auto-increment integer (identity/sequence).** Best index locality and smallest key, but:
  requires a central sequence (coordination point), IDs are guessable/enumerable, and merging
  data generated in different environments risks collisions. Rejected as the primary key for a
  distributed, multi-environment platform.
- **UUIDv4 (random).** The obvious UUID default, but random keys have poor B-tree index
  locality and cause page churn on high-volume inserts. Rejected in favor of v7, which keeps
  every UUIDv4 benefit while adding a time-ordered prefix. (Requires no extra dependency now
  that v7 is in the 3.14 stdlib.)
- **ULID / KSUID.** Similar time-ordered benefits to UUIDv7 but non-standard representation
  and an extra dependency; rejected in favor of the stdlib UUIDv7.
- **Composite/natural keys (e.g. slug as PK).** Couples the PK to mutable business data and
  complicates foreign keys; rejected. Business identifiers are modeled as separate unique
  columns instead.

## Consequences
### Positive
- IDs can be generated anywhere (services, tenants, offline) with no central sequence —
  supports horizontal scale and future multi-tenancy.
- Non-enumerable identifiers reduce information leakage and resource-guessing.
- Safe to merge/replicate data across environments without key collisions.
- Native Postgres `uuid` type keeps storage compact and indexed correctly.

### Negative
- Requires **Python 3.14+** (stdlib `uuid.uuid7`). We standardize both local and container
  runtimes on 3.14 to satisfy this.
- 16-byte keys are larger than 4/8-byte integers, marginally increasing index size.
- UUIDs are less human-friendly in logs/URLs than small integers (acceptable).
- Time-ordered keys expose approximate creation time; not a concern here, but noted.

## Follow-up Actions
- For high-write tables (metrics), evaluate partitioning and time-based aggregation
  independently of the key type.
- Ensure all new models inherit `UUIDPrimaryKeyMixin` for consistency.

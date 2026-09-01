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
Use **UUID (version 4) primary keys** for all entities, generated application-side.

- Column type is SQLAlchemy's dialect-aware `Uuid(as_uuid=True)` → native `uuid` on
  PostgreSQL, `CHAR(32)` on SQLite (tests). Values are Python `uuid.UUID`.
- A shared `UUIDPrimaryKeyMixin` defines the `id` column with `default=uuid.uuid4`, so all
  tables get identical, consistent keys.
- API schemas expose the id as a `UUID`.

## Alternatives Considered
- **Auto-increment integer (identity/sequence).** Best index locality and smallest key, but:
  requires a central sequence (coordination point), IDs are guessable/enumerable, and merging
  data generated in different environments risks collisions. Rejected as the primary key for a
  distributed, multi-environment platform.
- **UUIDv7 (time-ordered).** Keeps UUID benefits while restoring sequential index locality.
  Preferred long-term, but not yet in the Python standard library; deferred to avoid a
  third-party dependency now. Chosen as the roadmap successor.
- **ULID / KSUID.** Similar time-ordered benefits to UUIDv7 but non-standard representation
  and extra dependency; rejected in favor of standardizing on UUID.
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
- Random UUIDv4 has poorer B-tree index locality than sequential integers, causing more
  page churn on high-volume inserts (e.g. metrics). Mitigation: adopt UUIDv7 when available,
  and/or partition/aggregate high-volume metric tables (tracked separately).
- 16-byte keys are larger than 4/8-byte integers, marginally increasing index size.
- UUIDs are less human-friendly in logs/URLs than small integers (acceptable).

## Follow-up Actions
- Migrate to **UUIDv7** (time-ordered) once first-class support is available, to regain
  insert/index locality without giving up UUID benefits.
- For high-write tables (metrics), evaluate partitioning and time-based aggregation
  independently of the key type.
- Ensure all new models inherit `UUIDPrimaryKeyMixin` for consistency.

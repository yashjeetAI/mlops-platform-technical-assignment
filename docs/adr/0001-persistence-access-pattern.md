# ADR-0001: Persistence access pattern

## Status
Accepted — 2026-09-01

## Context
The platform persists a workflow-oriented domain (models, versions, deployments,
events, metrics, users) to a single relational store (PostgreSQL in production,
SQLite for local/dev/tests). We need a consistent way for API handlers and business
logic to obtain a database session, run queries, and manage transaction boundaries.

Two questions drive the decision:
1. How is a database session created, scoped, and disposed?
2. Do handlers/services talk to SQLAlchemy directly, or through an abstraction
   (Repository / Unit-of-Work) that hides the ORM?

The persistence target is fixed (relational, SQLAlchemy 2.0). The team is small and
the assignment is time-boxed, so ceremony that does not buy correctness or clarity is
a liability. The evaluation scorecard explicitly flags "complexity without rationale."

## Decision
- Use a **request-scoped SQLAlchemy `Session`**, created and disposed by a FastAPI
  dependency (`get_db`) that `yield`s the session and closes it in a `finally` block.
  Routes declare `db: Session = Depends(get_db)`; the same session is shared by every
  callable in that request, giving one transaction per request.
- Put business logic in a **thin service layer** (`app/services/*`) whose functions
  receive the `Session` as an explicit parameter (e.g. `authenticate(db, ...)`).
- Query through the **SQLAlchemy 2.0 ORM** (`select(Model)` + typed `Mapped[...]`
  models), not raw SQL strings or the legacy `Query` API.
- Do **not** introduce Repository or Unit-of-Work abstraction layers at this time.

## Alternatives Considered
- **Repository + Unit-of-Work pattern.** Wrap the session behind repository classes so
  domain logic never imports SQLAlchemy. Strong for Domain-Driven Design, for swapping
  persistence backends, or for unit-testing domain logic with zero DB. Rejected now: the
  store is fixed, the domain is CRUD/workflow-oriented, and the extra classes and
  indirection add boilerplate without a corresponding correctness or portability gain.
- **Global/module-level session.** A single shared session for the process. Rejected:
  not concurrency-safe, leaks state across requests, and breaks per-request transaction
  isolation.
- **Session created inside each service function.** Rejected: functions could not share a
  transaction, and tests could not inject an in-memory session.

## Consequences
### Positive
- Minimal boilerplate; code reads the way the FastAPI + SQLAlchemy docs recommend.
- One transaction per request with deterministic open/close via the dependency.
- Highly testable: tests override `get_db` with an in-memory SQLite session
  (`app.dependency_overrides`), so services run without a real database.
- Business logic is decoupled from HTTP (services take a `Session`, not a `Request`).

### Negative
- Services are coupled to SQLAlchemy's `Session` API; swapping the ORM/store later would
  touch service code (accepted — no such requirement exists).
- No single choke point to enforce cross-cutting persistence policy; if that need arises
  (multi-store, complex aggregates), a repository layer would be reconsidered.

## Follow-up Actions
- Keep transaction commits inside service functions (or a per-request commit boundary),
  not scattered across routes.
- Revisit and supersede this ADR **if** we must support multiple persistence backends or
  the domain grows aggregates complex enough to warrant repositories.
- Use Alembic migrations for schema evolution in production; `create_all` is used only for
  local/demo bootstrapping.

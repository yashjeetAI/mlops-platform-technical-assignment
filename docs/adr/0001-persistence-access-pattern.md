# ADR-0001: Persistence access pattern

## Status
Accepted — 2026-09-01

## Context
The app persists a workflow-oriented domain to one relational store (PostgreSQL in prod,
SQLite in tests). We must decide how sessions are scoped and whether business logic talks
to SQLAlchemy directly or through an abstraction. The store is fixed, the team small, and
the scorecard penalizes "complexity without rationale."

## Decision
- Request-scoped SQLAlchemy `Session` created/closed by a FastAPI dependency (`get_db`);
  one transaction per request.
- Business logic in a thin service layer whose functions take the `Session` explicitly.
- Query via the SQLAlchemy 2.0 ORM (`select(Model)` + typed `Mapped[...]`).
- No Repository / Unit-of-Work layer.

## Alternatives Considered
- **Repository + Unit-of-Work.** Good for DDD or swappable backends; rejected — the store is
  fixed and the extra indirection buys no correctness or portability here.
- **Global/module-level session.** Rejected — not concurrency-safe, leaks state across requests.
- **Session created inside each service.** Rejected — breaks shared transactions and testability.

## Consequences
### Positive
- Minimal boilerplate; matches FastAPI + SQLAlchemy docs.
- Testable: tests override `get_db` with in-memory SQLite.
- Business logic decoupled from HTTP.

### Negative
- Services are coupled to the `Session` API; swapping the ORM later would touch them (accepted).

## Follow-up Actions
- Keep commits inside services / a per-request boundary, not in routes.
- Revisit only if we need multiple backends or complex aggregates.
- Schema evolution via Alembic; `create_all` is for tests only.

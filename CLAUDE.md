# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An MLOps control-plane application (G12 technical assignment): register, version, approve,
deploy, monitor, and roll back ML models. A FastAPI backend + Angular frontend. The focus is
production-quality engineering, not model training. Assignment brief and rubric live in the
sibling `MLOps_G12_Technical_Assignment_Pack - Copy/` directory (outside this repo).

## Commands

Run backend commands from `backend/` with the venv active (`source .venv/bin/activate`).

```bash
# Backend (Python 3.14 REQUIRED — see UUIDv7 note below)
cd backend
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload            # dev server on :8000 (/docs for OpenAPI)
pytest                                    # all tests
pytest tests/test_auth.py                 # single file
pytest tests/test_auth.py::test_login_wrong_password_401   # single test
alembic revision --autogenerate -m "msg"  # generate migration after model changes
alembic upgrade head                       # apply migrations
alembic downgrade -1                       # roll back one

# Frontend (Angular 22)
cd frontend
npm install
npm start                                 # dev server on :4200 (proxies /api -> :8000)
npm run build
CI=true npx ng test --watch=false         # Vitest unit tests, run once

# Full stack
docker compose up --build                 # db :5432, backend :8000, frontend :4200
```

Port 4200 must be free before `docker compose up` (a stray dev server will block the bind).

## Architecture

### Backend (`backend/app/`)
Layered, request-scoped-session style (see `docs/adr/0001`), NOT a repository pattern:
- **Routes** (`api/routes/`) declare `db: Session = Depends(get_db)` and call **services**.
- **Services** (`services/`) hold business logic and take the `Session` as an explicit param.
- **Models** (`models/`) are SQLAlchemy 2.0 ORM (`Mapped[...]` + `mapped_column`).
- **Schemas** (`schemas/`) are Pydantic; all extend `schemas/base.py:CamelModel`.

Cross-cutting conventions baked into shared code — reuse these, don't reinvent per-model:
- **Every model inherits `UUIDPrimaryKeyMixin` + `TimestampMixin`** (`models/mixins.py`).
  PKs are **time-ordered UUIDv7** (`uuid.uuid7`, hence Python 3.14+). `sort_order` pins `id`
  first and `created_at/updated_at` last in the table.
- **API JSON is camelCase; Python and the DB are snake_case** (ADR-0004). This is automatic
  via `CamelModel` (Pydantic `alias_generator=to_camel`, `populate_by_name=True`). Do not
  hand-map casing. Tests assert the contract (e.g. `fullName`, not `full_name`).
- **Auth/RBAC**: JWT bearer tokens. `api/deps.py` provides `get_current_user` and the
  `require_roles(*roles)` guard factory. Roles are ordered `VIEWER < ENGINEER < APPROVER <
  ADMIN` (`core/enums.py`); **ADMIN always passes** `require_roles`. Guard governance-critical
  endpoints and return 403 on violation.

**Startup** (`main.py` lifespan): runs `alembic upgrade head`, then idempotently seeds demo
users. `Base.metadata.create_all` is used ONLY by tests, never at runtime.

**Logging/observability** (`core/logging.py`, `api/middleware.py`): structured logging via
**structlog** — JSON in Docker, console locally. `CorrelationIdMiddleware` binds a per-request
`correlation_id` (from `X-Request-ID` or generated) into structlog contextvars, so every log
line during a request carries it; it's echoed in the response header. Use
`get_logger(name)` and log domain events as structured key/values (e.g.
`logger.info("version_approved", version_id=...)`), never `print`.

### Database strategy (important, non-obvious)
- **App + all migrations run on PostgreSQL** (the real target).
- **Tests run on in-memory SQLite** for speed — `tests/conftest.py` overrides `get_db` and
  builds the schema with `create_all` (bypassing Alembic). So tests do NOT exercise
  Postgres-specific behavior; verify anything Postgres-only against the running DB.
- After changing a model, generate the migration **against Postgres** (the container must be
  up), then apply it. The `db` service in `docker-compose.yml` provides it.

### Frontend (`frontend/src/app/`)
Angular 22 standalone components + signals (no NgModules). Angular Material with an ABB-red
theme (`styles.scss` pins Material's `--mat-sys-primary` to `#FF000F`).
- **`core/`**: `auth.service.ts` (signals: `currentUser`, `isAuthenticated`, `hasRole`),
  `auth.interceptor.ts` (attaches JWT), `auth.guard.ts` (`authGuard`/`guestGuard` with session
  restore), `models.ts` (TS interfaces — camelCase, mirroring the API), `config.ts`.
- **`features/`**: lazy-loaded route components (`login/`, `home/`).
- **API access is same-origin `/api`** in both dev and prod — the dev proxy
  (`proxy.conf.json`) and prod nginx (`frontend/nginx.conf`) both forward `/api` → backend, so
  there is no CORS layer. Use `/api/...`, never an absolute backend URL.
- **Responsive layout is desktop-first**: base styles target desktop; adjust for small
  screens with `max-width` media queries (breakpoints ~600px for layout, ~480px for the login
  card). Keep new views mobile-friendly (fluid grids, no fixed widths that overflow phones).
- **Favicon** is an ABB wordmark in three formats under `public/` (`.svg` for modern browsers,
  `.png` + multi-size `.ico` for Safari/fallback). Rebuild the frontend container to see asset
  changes; favicons cache hard (hard-refresh or use a private window).

## Workflow conventions
- **Never commit to `main`** (a hook blocks it). Branch as `feat/*` or `fix/*`, push, open a PR.
- **Record significant decisions as ADRs** in `docs/adr/` (numbered, immutable once accepted;
  supersede rather than edit). Keep them lean (~30–40 lines): Context + 2–3 real alternatives
  are the valuable parts.
- Demo credentials (all users, password `demo1234`) and the default `jwt_secret` are for the
  demo only; real deployments must override `JWT_SECRET` via env.

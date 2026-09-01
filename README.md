# MLOps Platform — Technical Assignment

**Role level:** G12 (Principal Software Engineer / Technical Lead)

A control-plane application for managing the lifecycle of machine-learning models across
plants and environments: register, version, approve, deploy, monitor, and roll back.

> The focus is production-quality engineering, not model training.

## Tech stack

| Layer     | Technology                                            |
|-----------|-------------------------------------------------------|
| Backend   | Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2     |
| Database  | PostgreSQL (Docker) / SQLite (local dev & tests)      |
| Frontend  | Angular, TypeScript, SCSS                             |
| Packaging | Docker, Docker Compose                                |
| CI        | GitHub Actions                                        |

## Repository layout

```text
backend/    FastAPI service (registry, deployments, monitoring)
frontend/   Angular operational UI
docs/       Architecture, ADRs, API design, test strategy
data/        Sample/seed data
scripts/    Dev & seed scripts
```

## Getting started

### Backend (local)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
```

### Frontend (local)

```bash
cd frontend
npm install
npm start
# App: http://localhost:4200
```

### Everything via Docker

```bash
docker compose up --build
# frontend :4200  backend :8000  db :5432
```

## Tests

```bash
cd backend && pytest        # Python unit/integration
cd frontend && npm test     # Angular unit tests
```

## Status

Scaffolding in place: backend service with health/readiness endpoints and Angular app shell.
Domain model (registry, deployments, monitoring), async deployment worker, and UI views are
under active development — see `docs/` for the architecture and delivery plan.

## Known limitations

- Domain endpoints beyond `/health` and `/ready` are in progress.

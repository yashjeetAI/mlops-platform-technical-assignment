# Test Strategy

Testing targets the **governance-critical paths** first: lifecycle legality, deployment
eligibility, concurrency guards, idempotency, retry/rollback, and the error contract. The backend
suite (~58 tests across 7 files) runs on **in-memory SQLite** via a dependency-overridden session
for speed and isolation; the app and migrations themselves run on **PostgreSQL**.

## Unit tests

Domain rules in isolation — the highest-value layer:
- **Lifecycle transitions** (`test_lifecycle.py`): every legal DRAFT→…→PRODUCTION step; illegal
  transitions and demotions rejected; approval required for APPROVED/STAGING/PRODUCTION.
- **Deployment eligibility / policy**: stage-gating (DRAFT/ARCHIVED never deployable; VALIDATED→dev,
  STAGING→dev+staging, PRODUCTION→all).
- **Metric rollups**: HEALTHY/DEGRADED/NO_DATA derivation from the latest sample.

## API tests

Full request/response through FastAPI (`test_models.py`, `test_deployments.py`, `test_auth.py`):
success paths, invalid requests (422), missing records (404), conflicts (409: illegal transition,
duplicate/active deployment), and **authorization** (401 unauthenticated, 403 wrong role — e.g.
ENGINEER cannot roll back). Asserts the **camelCase** contract (e.g. `fullName`, `modelVersionId`).

## Integration tests

Cross-component behaviour against the DB (`test_deployments.py`, `test_monitoring.py`): persistence
of models/versions/deployments and their **audit events**; the worker claim → advance → record
loop driving a deployment to SUCCEEDED/FAILED; **retry** re-queueing a FAILED deployment;
**rollback** creating a superseding deployment with `rolled_back_to_id`; and metrics being linked
to the deployment that produced them.

## Angular tests

Vitest component/service tests (`app.spec.ts`, `auth.service.spec.ts`): the auth service's signal
state (`currentUser`, `isAuthenticated`, `hasRole`), token handling, and component rendering.
Loading/error/empty states are modelled with signals and covered as the surface grows.

## Observability tests

`test_observability.py`: a correlation id supplied via `X-Request-ID` is echoed on the response,
and requests without one still get an id — protecting the traceability contract.

## End-to-end scenario

The brief's golden path is covered across the API/integration tests and reproducible in the UI:
**register model → register version → approve → deploy → view metrics → roll back**, including the
negative cases (unapproved version blocked from production; duplicate request deduped).

## CI, coverage & limitations

- **CI** ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) runs on every PR: backend
  `ruff` + `pytest` against a Postgres service; frontend `prettier` + `build` + `vitest`.
- **Coverage focus** is behavioural (rules + contracts), not line-count vanity; the domain and
  API layers are the most densely tested.
- **Limitations**: unit/API tests use SQLite, so **Postgres-only** behaviour (partial unique
  index, `FOR UPDATE SKIP LOCKED`, `LISTEN/NOTIFY`) is guarded in code and verified against the
  running database rather than in the fast suite. Frontend E2E (Playwright/Cypress) and load tests
  are future work ([roadmap](roadmap.md)).

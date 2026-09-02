# API Design

REST over HTTP, JSON in **camelCase** at the boundary ([ADR-0004](adr/0004-api-naming-convention.md)).
Interactive contract: **`/docs`** (Swagger UI) and **`/redoc`**; the OpenAPI schema is the source
of truth. All non-auth endpoints require a JWT bearer token; governance-critical writes are
role-guarded.

## Conventions

- **Auth**: `Authorization: Bearer <token>` from `POST /auth/login`. Roles ordered
  `VIEWER < ENGINEER < APPROVER < ADMIN`; ADMIN passes any guard ([ADR-0002](adr/0002-authentication-and-rbac.md)).
- **Pagination**: collection endpoints accept `limit` (1–100) + `offset` and return an envelope
  `{ items, total, limit, offset }`, ordered **newest-first** by UUIDv7 `id`.
- **Search**: `?q=` is server-side and case-insensitive across relevant columns.
- **Correlation**: send `X-Request-ID` to trace a call; it is echoed on the response and carried
  through to the async worker.
- **Errors**: a consistent `{ "detail": "..." }` body. Status mapping:

  | Status | Meaning | Example |
  |-------:|---------|---------|
  | 400 | Bad request / domain rule | malformed body |
  | 401 | Missing/invalid token | not logged in |
  | 403 | Role not permitted | ENGINEER attempts rollback |
  | 404 | Not found | unknown model id |
  | 409 | Conflict | illegal lifecycle transition, duplicate/active deployment |
  | 422 | Validation | Pydantic schema violation |

## Endpoints

### Auth
| Method | Path | Role | Purpose |
|--------|------|------|---------|
| POST | `/auth/login` | — | Exchange username/password for a JWT |
| GET | `/auth/me` | any | Current user profile |

### Registry — models & versions
| Method | Path | Role | Purpose |
|--------|------|------|---------|
| POST | `/models` | ENGINEER | Register a model (201) |
| GET | `/models` | any | List models (paginated, `?q`) |
| GET | `/models/{model_id}` | any | Model detail |
| POST | `/models/{model_id}/versions` | ENGINEER | Add a version (DRAFT) |
| GET | `/models/{model_id}/versions` | any | List versions (paginated) |
| POST | `/models/{model_id}/versions/{version_id}/approve` | APPROVER | Validate/approve a version |
| POST | `/models/{model_id}/versions/{version_id}/promote` | APPROVER | Promote a version (→ STAGING/PRODUCTION) |
| GET | `/models/{model_id}/versions/{version_id}/events` | any | Version lifecycle audit trail |

### Deployments
| Method | Path | Role | Purpose |
|--------|------|------|---------|
| POST | `/deployments` | ENGINEER | Request a deployment (enqueue; idempotency-key aware) |
| GET | `/deployments` | any | List deployments (paginated, `?q`) |
| GET | `/deployments/{deployment_id}` | any | Deployment detail + event timeline |
| POST | `/deployments/{deployment_id}/retry` | ENGINEER | Re-queue a FAILED deployment |
| POST | `/deployments/{deployment_id}/rollback` | ADMIN | Roll back a SUCCEEDED production deployment |

### Monitoring & health
| Method | Path | Role | Purpose |
|--------|------|------|---------|
| GET | `/monitoring` | any | Health overview across models (paginated, `?q`) |
| GET | `/models/{model_id}/metrics` | any | Per-version/environment metric summary + series |
| GET | `/health` | — | Liveness probe |
| GET | `/ready` | — | Readiness probe (checks DB reachability) |

## Mapping to the brief's minimum APIs

Every required endpoint is present; a few are expressed resource-oriented (the brief permits
"equivalent resource-oriented designs"): lifecycle actions are `POST …/versions/{id}/approve` and
`…/promote`; metrics are `GET /models/{id}/metrics`; monitoring adds `GET /monitoring` for the
cross-model overview.

## Idempotency

`POST /deployments` accepts a client idempotency key; a repeated request with the same key
returns the original deployment rather than creating a duplicate. Independently, the DB's partial
unique index rejects a second *active* deployment for the same (model, environment) with `409`
([ADR-0008](adr/0008-idempotency-and-rollback.md)).

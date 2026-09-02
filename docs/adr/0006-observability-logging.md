# ADR-0006: Observability — structured logging & correlation IDs

## Status
Accepted — 2026-09-02

## Context
The platform needs operational visibility (a G12 requirement): structured logs, request
correlation, and failure classification. Logs must be machine-parseable in production yet
readable locally, and every log line emitted while handling a request must be tied back to
that request.

## Decision
- Use **structlog** for structured logging. **JSON** output in deployed environments,
  **coloured console** locally (driven by `settings.environment`).
- A **correlation id** per request via middleware: reuse an inbound `X-Request-ID` or generate
  a UUIDv7, bind it to structlog **contextvars**, echo it in the response header. Because it is
  bound to context, every log line during the request carries it (like a pino child logger).
- **One structured line per request** (`method`, `path`, `status_code`, `duration_ms`).
- **Domain events** are logged with context: `login_succeeded`/`login_failed`,
  `model_created`, `version_created`, `version_approved`, `version_promoted`.
- **Failure classification**: the central domain-error handler logs `error_type` + status, so
  4xx business errors are queryable by class.

## Alternatives Considered
- **python-json-logger + stdlib logging** — JSON only; correlation IDs must be threaded by
  hand. Rejected; removed from deps in favour of structlog.
- **loguru** — ergonomic but weaker structured/context-binding story. Rejected.
- **OpenTelemetry now** — the assignment marks it *desirable*, not required. Deferred to the
  roadmap to avoid scope creep; the correlation id is OTel-compatible as a future trace id.

## Consequences
### Positive
- Queryable JSON logs correlated end-to-end by request; readable dev output.
- Latency (`duration_ms`) and failure class captured for every request without per-route code.
- Foundation for the operational-dashboard proposal and future tracing.

### Negative
- structlog config + middleware is a small amount of infra to maintain.
- `BaseHTTPMiddleware` adds minor overhead; acceptable at this scale.

## Follow-up Actions
- Add OpenTelemetry tracing/metrics export; map the correlation id to the trace id.
- Emit deployment-lifecycle events once the deployments slice lands.
- Propose log-based operational dashboards (error rate by class, p95 latency).

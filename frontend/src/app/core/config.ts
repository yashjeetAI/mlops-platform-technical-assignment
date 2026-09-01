/**
 * API base path. In dev, the Angular proxy (proxy.conf.json) forwards `/api`
 * to the backend; in prod, nginx proxies `/api` to the backend service.
 * Same-origin in both cases — no CORS needed.
 */
export const API_BASE_URL = '/api';

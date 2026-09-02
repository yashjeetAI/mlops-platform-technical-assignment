import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from './config';
import { MonitoringOverview, MonitoringSummary } from './monitoring.models';

@Injectable({ providedIn: 'root' })
export class MonitoringService {
  private readonly http = inject(HttpClient);

  overview(opts: { limit: number; offset: number; q?: string }): Observable<MonitoringOverview> {
    let params = new HttpParams().set('limit', opts.limit).set('offset', opts.offset);
    if (opts.q) {
      params = params.set('q', opts.q);
    }
    return this.http.get<MonitoringOverview>(`${API_BASE_URL}/monitoring`, { params });
  }

  modelMetrics(
    modelId: string,
    opts?: { version?: string; environment?: string },
  ): Observable<MonitoringSummary> {
    let params = new HttpParams();
    if (opts?.version) {
      params = params.set('version', opts.version);
    }
    if (opts?.environment) {
      params = params.set('environment', opts.environment);
    }
    return this.http.get<MonitoringSummary>(`${API_BASE_URL}/models/${modelId}/metrics`, {
      params,
    });
  }
}

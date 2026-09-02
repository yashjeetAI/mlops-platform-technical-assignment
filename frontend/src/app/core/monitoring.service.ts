import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from './config';
import { MonitoringOverview, MonitoringSummary } from './monitoring.models';

@Injectable({ providedIn: 'root' })
export class MonitoringService {
  private readonly http = inject(HttpClient);

  overview(): Observable<MonitoringOverview> {
    return this.http.get<MonitoringOverview>(`${API_BASE_URL}/monitoring`);
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

import { HttpClient } from '@angular/common/http';
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

  modelMetrics(modelId: string): Observable<MonitoringSummary> {
    return this.http.get<MonitoringSummary>(`${API_BASE_URL}/models/${modelId}/metrics`);
  }
}

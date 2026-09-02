import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from './config';
import {
  CreateModel,
  CreateVersion,
  LifecycleStage,
  ModelDetail,
  ModelPage,
  ModelSummary,
  ModelVersion,
} from './registry.models';

@Injectable({ providedIn: 'root' })
export class RegistryService {
  private readonly http = inject(HttpClient);
  private readonly base = `${API_BASE_URL}/models`;

  listModels(opts: { limit: number; offset: number; q?: string }): Observable<ModelPage> {
    let params = new HttpParams()
      .set('limit', opts.limit)
      .set('offset', opts.offset);
    if (opts.q) {
      params = params.set('q', opts.q);
    }
    return this.http.get<ModelPage>(this.base, { params });
  }

  getModel(id: string): Observable<ModelDetail> {
    return this.http.get<ModelDetail>(`${this.base}/${id}`);
  }

  createModel(payload: CreateModel): Observable<ModelSummary> {
    return this.http.post<ModelSummary>(this.base, payload);
  }

  createVersion(modelId: string, payload: CreateVersion): Observable<ModelVersion> {
    return this.http.post<ModelVersion>(`${this.base}/${modelId}/versions`, payload);
  }

  approveVersion(modelId: string, versionId: string): Observable<ModelVersion> {
    return this.http.post<ModelVersion>(
      `${this.base}/${modelId}/versions/${versionId}/approve`,
      {},
    );
  }

  promoteVersion(
    modelId: string,
    versionId: string,
    targetStage: LifecycleStage,
  ): Observable<ModelVersion> {
    return this.http.post<ModelVersion>(
      `${this.base}/${modelId}/versions/${versionId}/promote`,
      { targetStage },
    );
  }
}

/** Extract the backend's `{ detail }` error message, with sensible fallbacks. */
export function apiErrorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) {
      return 'Cannot reach the server.';
    }
    const detail = err.error?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
  }
  return fallback;
}

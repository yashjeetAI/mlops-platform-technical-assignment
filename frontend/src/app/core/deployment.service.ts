import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from './config';
import {
  CreateDeployment,
  Deployment,
  DeploymentDetail,
  DeploymentPage,
} from './deployment.models';

@Injectable({ providedIn: 'root' })
export class DeploymentService {
  private readonly http = inject(HttpClient);
  private readonly base = `${API_BASE_URL}/deployments`;

  list(opts: { limit: number; offset: number; q?: string }): Observable<DeploymentPage> {
    let params = new HttpParams().set('limit', opts.limit).set('offset', opts.offset);
    if (opts.q) {
      params = params.set('q', opts.q);
    }
    return this.http.get<DeploymentPage>(this.base, { params });
  }

  get(id: string): Observable<DeploymentDetail> {
    return this.http.get<DeploymentDetail>(`${this.base}/${id}`);
  }

  create(payload: CreateDeployment): Observable<DeploymentDetail> {
    return this.http.post<DeploymentDetail>(this.base, payload);
  }

  retry(id: string): Observable<Deployment> {
    return this.http.post<Deployment>(`${this.base}/${id}/retry`, {});
  }

  rollback(id: string): Observable<Deployment> {
    return this.http.post<Deployment>(`${this.base}/${id}/rollback`, {});
  }
}

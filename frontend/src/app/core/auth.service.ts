import { computed, Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, of } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';

import { API_BASE_URL } from './config';
import { LoginRequest, Role, TokenResponse, User } from './models';

const TOKEN_KEY = 'mlops_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  /** Current authenticated user (null when logged out). */
  readonly currentUser = signal<User | null>(null);
  readonly isAuthenticated = computed(() => this.currentUser() !== null);

  token(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  /** Exchange credentials for a token, then load the user profile. */
  login(credentials: LoginRequest): Observable<User> {
    return this.http.post<TokenResponse>(`${API_BASE_URL}/auth/login`, credentials).pipe(
      tap((res) => localStorage.setItem(TOKEN_KEY, res.accessToken)),
      switchMap(() => this.fetchMe()),
    );
  }

  /** Load the current user from the token; used for session restore. */
  fetchMe(): Observable<User> {
    return this.http
      .get<User>(`${API_BASE_URL}/auth/me`)
      .pipe(tap((user) => this.currentUser.set(user)));
  }

  /** Restore a session on app start if a token is present. Never throws. */
  restoreSession(): Observable<boolean> {
    if (!this.token()) {
      return of(false);
    }
    return this.fetchMe().pipe(
      map(() => true),
      catchError(() => {
        this.clearToken();
        return of(false);
      }),
    );
  }

  logout(): void {
    this.clearToken();
    this.currentUser.set(null);
    void this.router.navigateByUrl('/login');
  }

  /** True if the user holds any of the given roles (ADMIN always passes). */
  hasRole(...roles: Role[]): boolean {
    const user = this.currentUser();
    if (!user) {
      return false;
    }
    return user.role === Role.ADMIN || roles.includes(user.role);
  }

  private clearToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  }
}

import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { AuthService } from './auth.service';
import { Role, User } from './models';

const USER: User = {
  id: '00000000-0000-7000-8000-000000000000',
  username: 'engineer',
  email: 'engineer@example.com',
  full_name: 'Eli Engineer',
  role: Role.ENGINEER,
  created_at: '2026-01-01T00:00:00Z',
};

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('login stores the token and loads the current user', () => {
    service.login({ username: 'engineer', password: 'demo1234' }).subscribe();

    const loginReq = http.expectOne('/api/auth/login');
    expect(loginReq.request.method).toBe('POST');
    loginReq.flush({ access_token: 'jwt-token', token_type: 'bearer' });

    const meReq = http.expectOne('/api/auth/me');
    meReq.flush(USER);

    expect(service.token()).toBe('jwt-token');
    expect(service.isAuthenticated()).toBe(true);
    expect(service.currentUser()?.username).toBe('engineer');
  });

  it('hasRole grants a matching role and denies others', () => {
    service.currentUser.set(USER); // ENGINEER
    expect(service.hasRole(Role.ENGINEER)).toBe(true);
    expect(service.hasRole(Role.APPROVER)).toBe(false);
  });

  it('hasRole always grants ADMIN', () => {
    service.currentUser.set({ ...USER, role: Role.ADMIN });
    expect(service.hasRole(Role.APPROVER)).toBe(true);
  });

  it('restoreSession returns false when no token is present', () => {
    service.restoreSession().subscribe((ok) => expect(ok).toBe(false));
    http.expectNone('/api/auth/me');
  });
});

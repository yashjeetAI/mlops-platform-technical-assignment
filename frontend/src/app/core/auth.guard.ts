import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map, of } from 'rxjs';

import { AuthService } from './auth.service';

/** Allows navigation only when authenticated; restores session if a token exists. */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) {
    return of(true);
  }
  return auth.restoreSession().pipe(map((ok) => (ok ? true : router.parseUrl('/login'))));
};

/** Redirects already-authenticated users away from the login page. */
export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) {
    return of(router.parseUrl('/'));
  }
  return auth.restoreSession().pipe(map((ok) => (ok ? router.parseUrl('/') : true)));
};

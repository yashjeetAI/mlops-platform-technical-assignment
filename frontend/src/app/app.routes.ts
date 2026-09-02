import { Routes } from '@angular/router';

import { authGuard, guestGuard } from './core/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/login/login').then((m) => m.Login),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./features/home/home').then((m) => m.Home),
  },
  {
    path: 'models',
    canActivate: [authGuard],
    loadComponent: () => import('./features/models/model-list').then((m) => m.ModelList),
  },
  {
    path: 'models/:id',
    canActivate: [authGuard],
    loadComponent: () => import('./features/models/model-detail').then((m) => m.ModelDetail),
  },
  { path: '**', redirectTo: '' },
];

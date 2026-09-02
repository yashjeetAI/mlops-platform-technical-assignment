import { Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AuthService } from './core/auth.service';

interface NavItem {
  label: string;
  icon: string;
  route?: string;
  exact?: boolean;
  soon?: boolean;
}

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatSidenavModule,
    MatListModule,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatTooltipModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly auth = inject(AuthService);
  private readonly breakpoints = inject(BreakpointObserver);

  /** True on small screens → sidenav becomes an overlay. */
  readonly isHandset = toSignal(
    this.breakpoints.observe(Breakpoints.Handset).pipe(map((r) => r.matches)),
    { initialValue: false },
  );

  /** Overlay open/closed state (only meaningful on handset). */
  readonly sidenavOpen = signal(false);

  readonly nav: NavItem[] = [
    { label: 'Dashboard', icon: 'dashboard', route: '/', exact: true },
    { label: 'Model Registry', icon: 'inventory_2', route: '/models' },
    { label: 'Deployments', icon: 'rocket_launch', route: '/deployments' },
    { label: 'Monitoring', icon: 'monitoring', route: '/monitoring' },
  ];

  toggleSidenav(): void {
    this.sidenavOpen.set(!this.sidenavOpen());
  }

  closeOnHandset(): void {
    if (this.isHandset()) {
      this.sidenavOpen.set(false);
    }
  }

  logout(): void {
    this.auth.logout();
  }
}

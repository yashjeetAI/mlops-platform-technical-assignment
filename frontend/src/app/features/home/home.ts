import { Component, computed, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../../core/auth.service';
import { Role } from '../../core/models';

interface Capability {
  icon: string;
  title: string;
  description: string;
  allowed: boolean;
}

@Component({
  selector: 'app-home',
  imports: [MatCardModule, MatIconModule],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home {
  private readonly auth = inject(AuthService);

  readonly user = this.auth.currentUser;

  /** Role-gated capabilities — mirror the backend RBAC rules. */
  readonly capabilities = computed<Capability[]>(() => [
    {
      icon: 'inventory_2',
      title: 'Browse registry',
      description: 'View models, versions and monitoring.',
      allowed: this.auth.hasRole(Role.VIEWER, Role.ENGINEER, Role.APPROVER),
    },
    {
      icon: 'add_box',
      title: 'Register models & versions',
      description: 'Create models and register new versions.',
      allowed: this.auth.hasRole(Role.ENGINEER),
    },
    {
      icon: 'verified',
      title: 'Approve & promote',
      description: 'Approve versions and promote to Production.',
      allowed: this.auth.hasRole(Role.APPROVER),
    },
    {
      icon: 'settings_backup_restore',
      title: 'Rollback deployments',
      description: 'Roll back a Production deployment.',
      allowed: this.auth.hasRole(Role.ADMIN),
    },
  ]);
}

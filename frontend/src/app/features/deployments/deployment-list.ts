import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { interval, map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';

import { AuthService } from '../../core/auth.service';
import { Role } from '../../core/models';
import { DeploymentService } from '../../core/deployment.service';
import { apiErrorMessage } from '../../core/registry.service';
import {
  CreateDeployment,
  Deployment,
  DeploymentDetail,
  DeploymentStatus,
  isInFlight,
  statusClass,
} from '../../core/deployment.models';
import { DeploymentFormDialog } from './deployment-form-dialog';

@Component({
  selector: 'app-deployment-list',
  imports: [
    DatePipe,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatTableModule,
    MatPaginatorModule,
    MatSidenavModule,
  ],
  templateUrl: './deployment-list.html',
  styleUrl: './deployment-list.scss',
})
export class DeploymentList {
  private readonly svc = inject(DeploymentService);
  private readonly auth = inject(AuthService);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  private readonly breakpoints = inject(BreakpointObserver);

  readonly isHandset = toSignal(
    this.breakpoints.observe(Breakpoints.Handset).pipe(map((r) => r.matches)),
    { initialValue: false },
  );
  readonly columns = ['model', 'environment', 'status', 'attempts', 'created', 'action'];

  readonly deployments = signal<Deployment[]>([]);
  readonly total = signal(0);
  readonly pageIndex = signal(0);
  readonly pageSize = signal(10);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  // Timeline drawer.
  readonly detail = signal<DeploymentDetail | null>(null);
  readonly drawerOpen = signal(false);

  readonly canDeploy = this.auth.hasRole(Role.ENGINEER);
  readonly canRollback = this.auth.hasRole(Role.ADMIN);

  readonly statusClass = statusClass;
  readonly Status = DeploymentStatus;

  constructor() {
    this.loadList();
    // Poll for live status while anything is in flight (list) or the drawer is open.
    interval(2000)
      .pipe(takeUntilDestroyed())
      .subscribe(() => this.poll());
  }

  loadList(quiet = false): void {
    if (!quiet) {
      this.loading.set(true);
    }
    this.error.set(null);
    this.svc
      .list({ limit: this.pageSize(), offset: this.pageIndex() * this.pageSize() })
      .subscribe({
        next: (page) => {
          this.deployments.set(page.items);
          this.total.set(page.total);
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(apiErrorMessage(err, 'Failed to load deployments.'));
          this.loading.set(false);
        },
      });
  }

  private poll(): void {
    if (this.deployments().some((d) => isInFlight(d.status))) {
      this.loadList(true);
    }
    const d = this.detail();
    if (this.drawerOpen() && d && isInFlight(d.status)) {
      this.loadDetail(d.id);
    }
  }

  onPage(event: PageEvent): void {
    this.pageIndex.set(event.pageIndex);
    this.pageSize.set(event.pageSize);
    this.loadList();
  }

  openDetail(dep: Deployment): void {
    this.detail.set(null);
    this.drawerOpen.set(true);
    this.loadDetail(dep.id);
  }

  loadDetail(id: string): void {
    this.svc.get(id).subscribe((d) => this.detail.set(d));
  }

  closeDrawer(): void {
    this.drawerOpen.set(false);
  }

  newDeployment(): void {
    const ref = this.dialog.open(DeploymentFormDialog);
    ref.afterClosed().subscribe((payload: CreateDeployment | undefined) => {
      if (!payload) {
        return;
      }
      this.svc.create(payload).subscribe({
        next: (dep) => {
          this.snack.open('Deployment requested', 'Dismiss', { duration: 3000 });
          this.pageIndex.set(0);
          this.loadList();
          this.detail.set(dep);
          this.drawerOpen.set(true);
        },
        error: (err) => this.snack.open(apiErrorMessage(err), 'Dismiss', { duration: 5000 }),
      });
    });
  }

  retry(dep: Deployment): void {
    this.svc.retry(dep.id).subscribe({
      next: () => this.afterAction('Retry requested', dep.id),
      error: (err) => this.snack.open(apiErrorMessage(err), 'Dismiss', { duration: 5000 }),
    });
  }

  rollback(dep: Deployment): void {
    this.svc.rollback(dep.id).subscribe({
      next: () => this.afterAction('Rolled back', dep.id),
      error: (err) => this.snack.open(apiErrorMessage(err), 'Dismiss', { duration: 5000 }),
    });
  }

  private afterAction(message: string, id: string): void {
    this.snack.open(message, 'Dismiss', { duration: 3000 });
    this.loadDetail(id);
    this.loadList(true);
  }
}

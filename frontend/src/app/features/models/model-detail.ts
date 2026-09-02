import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AuthService } from '../../core/auth.service';
import { Role } from '../../core/models';
import { apiErrorMessage, RegistryService } from '../../core/registry.service';
import {
  CreateVersion,
  LifecycleStage,
  ModelSummary,
  ModelVersion,
  ModelVersionEvent,
  PROMOTE_TARGETS,
  stageClass,
} from '../../core/registry.models';
import { VersionFormDialog } from './version-form-dialog';

@Component({
  selector: 'app-model-detail',
  imports: [
    DatePipe,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatTableModule,
    MatPaginatorModule,
    MatSidenavModule,
    MatTooltipModule,
  ],
  templateUrl: './model-detail.html',
  styleUrl: './model-detail.scss',
})
export class ModelDetail {
  private readonly route = inject(ActivatedRoute);
  private readonly registry = inject(RegistryService);
  private readonly auth = inject(AuthService);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  private readonly breakpoints = inject(BreakpointObserver);

  private readonly modelId = this.route.snapshot.paramMap.get('id')!;

  readonly isHandset = toSignal(
    this.breakpoints.observe(Breakpoints.Handset).pipe(map((r) => r.matches)),
    { initialValue: false },
  );
  readonly columns = ['version', 'stage', 'approved', 'artifact', 'algorithm', 'actions'];

  readonly model = signal<ModelSummary | null>(null);
  readonly versions = signal<ModelVersion[]>([]);
  readonly total = signal(0);
  readonly pageIndex = signal(0);
  readonly pageSize = signal(10);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly canCreate = this.auth.hasRole(Role.ENGINEER);
  readonly canApprove = this.auth.hasRole(Role.APPROVER);

  readonly stageClass = stageClass;

  // Lifecycle-history drawer.
  readonly historyVersion = signal<ModelVersion | null>(null);
  readonly historyEvents = signal<ModelVersionEvent[]>([]);
  readonly drawerOpen = signal(false);

  constructor() {
    this.load();
  }

  openHistory(version: ModelVersion): void {
    this.historyVersion.set(version);
    this.historyEvents.set([]);
    this.drawerOpen.set(true);
    this.registry
      .listVersionEvents(this.modelId, version.id, { limit: 100, offset: 0 })
      .subscribe((page) => this.historyEvents.set(page.items));
  }

  closeDrawer(): void {
    this.drawerOpen.set(false);
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.registry.getModel(this.modelId).subscribe({
      next: (model) => {
        this.model.set(model);
        this.loadVersions();
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err, 'Failed to load model.'));
        this.loading.set(false);
      },
    });
  }

  loadVersions(): void {
    this.registry
      .listVersions(this.modelId, {
        limit: this.pageSize(),
        offset: this.pageIndex() * this.pageSize(),
      })
      .subscribe({
        next: (page) => {
          this.versions.set(page.items);
          this.total.set(page.total);
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(apiErrorMessage(err, 'Failed to load versions.'));
          this.loading.set(false);
        },
      });
  }

  onPage(event: PageEvent): void {
    this.pageIndex.set(event.pageIndex);
    this.pageSize.set(event.pageSize);
    this.loadVersions();
  }

  promoteTargets(version: ModelVersion): LifecycleStage[] {
    return PROMOTE_TARGETS[version.stage];
  }

  canApproveVersion(version: ModelVersion): boolean {
    return this.canApprove && version.stage === LifecycleStage.VALIDATED;
  }

  addVersion(): void {
    const ref = this.dialog.open(VersionFormDialog);
    ref.afterClosed().subscribe((payload: CreateVersion | undefined) => {
      if (!payload) {
        return;
      }
      this.registry.createVersion(this.modelId, payload).subscribe({
        next: () => {
          this.pageIndex.set(0);
          this.afterAction(`Version ${payload.version} registered`);
        },
        error: (err) => this.fail(err),
      });
    });
  }

  approve(version: ModelVersion): void {
    this.registry.approveVersion(this.modelId, version.id).subscribe({
      next: () => this.afterAction(`Version ${version.version} approved`),
      error: (err) => this.fail(err),
    });
  }

  promote(version: ModelVersion, target: LifecycleStage): void {
    this.registry.promoteVersion(this.modelId, version.id, target).subscribe({
      next: () => this.afterAction(`Version ${version.version} → ${target}`),
      error: (err) => this.fail(err),
    });
  }

  private afterAction(message: string): void {
    this.snack.open(message, 'Dismiss', { duration: 3000 });
    this.loadVersions();
    // Refresh the open history drawer so the new transition shows up.
    const v = this.historyVersion();
    if (this.drawerOpen() && v) {
      this.registry
        .listVersionEvents(this.modelId, v.id, { limit: 100, offset: 0 })
        .subscribe((page) => this.historyEvents.set(page.items));
    }
  }

  private fail(err: unknown): void {
    this.snack.open(apiErrorMessage(err), 'Dismiss', { duration: 5000 });
  }
}

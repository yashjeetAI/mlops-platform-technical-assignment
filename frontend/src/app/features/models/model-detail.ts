import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';

import { AuthService } from '../../core/auth.service';
import { Role } from '../../core/models';
import { apiErrorMessage, RegistryService } from '../../core/registry.service';
import {
  CreateVersion,
  LifecycleStage,
  ModelDetail as ModelDetailData,
  ModelVersion,
  PROMOTE_TARGETS,
  stageClass,
} from '../../core/registry.models';
import { VersionFormDialog } from './version-form-dialog';

@Component({
  selector: 'app-model-detail',
  imports: [
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatDialogModule,
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

  private readonly modelId = this.route.snapshot.paramMap.get('id')!;

  readonly model = signal<ModelDetailData | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly canCreate = this.auth.hasRole(Role.ENGINEER);
  readonly canApprove = this.auth.hasRole(Role.APPROVER);

  readonly stageClass = stageClass;
  readonly Stage = LifecycleStage;

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.registry.getModel(this.modelId).subscribe({
      next: (model) => {
        this.model.set(model);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err, 'Failed to load model.'));
        this.loading.set(false);
      },
    });
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
        next: () => this.afterAction(`Version ${payload.version} registered`),
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
    this.load();
  }

  private fail(err: unknown): void {
    this.snack.open(apiErrorMessage(err), 'Dismiss', { duration: 5000 });
  }
}

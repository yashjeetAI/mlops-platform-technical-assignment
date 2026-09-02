import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

import { RegistryService } from '../../core/registry.service';
import { ModelSummary, ModelVersion } from '../../core/registry.models';
import { CreateDeployment, ENVIRONMENTS } from '../../core/deployment.models';

@Component({
  selector: 'app-deployment-form-dialog',
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatSelectModule,
    MatCheckboxModule,
    MatButtonModule,
  ],
  template: `
    <h2 mat-dialog-title>New deployment</h2>
    <form [formGroup]="form" (ngSubmit)="submit()">
      <mat-dialog-content class="dialog-body">
        <mat-form-field appearance="outline">
          <mat-label>Model</mat-label>
          <mat-select formControlName="modelId">
            @for (m of models(); track m.id) {
              <mat-option [value]="m.id">{{ m.name }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Version</mat-label>
          <mat-select formControlName="modelVersionId">
            @for (v of versions(); track v.id) {
              <mat-option [value]="v.id">v{{ v.version }} · {{ v.stage }}</mat-option>
            }
          </mat-select>
          @if (!form.value.modelId) {
            <mat-hint>Select a model first.</mat-hint>
          }
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Environment</mat-label>
          <mat-select formControlName="environment">
            @for (e of environments; track e) {
              <mat-option [value]="e">{{ e }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <mat-checkbox formControlName="simulateFailure" class="sim">
          Simulate failure (demo)
        </mat-checkbox>
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancel</button>
        <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid">
          Deploy
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [
    `
      .dialog-body {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        width: 26rem;
        max-width: 80vw;
        padding-top: 0.75rem;
      }
      mat-form-field {
        width: 100%;
      }
      .sim {
        margin: 0.25rem 0 0.5rem;
      }
    `,
  ],
})
export class DeploymentFormDialog {
  private readonly fb = inject(FormBuilder);
  private readonly registry = inject(RegistryService);
  private readonly ref = inject(MatDialogRef<DeploymentFormDialog, CreateDeployment>);

  readonly models = signal<ModelSummary[]>([]);
  readonly versions = signal<ModelVersion[]>([]);
  readonly environments = ENVIRONMENTS;

  readonly form = this.fb.nonNullable.group({
    modelId: ['', Validators.required],
    modelVersionId: ['', Validators.required],
    environment: ['', Validators.required],
    simulateFailure: [false],
  });

  constructor() {
    this.registry.listModels({ limit: 100, offset: 0 }).subscribe((page) => {
      this.models.set(page.items);
    });
    // Load versions whenever the selected model changes.
    this.form.controls.modelId.valueChanges.subscribe((modelId) => {
      this.form.controls.modelVersionId.setValue('');
      this.versions.set([]);
      if (modelId) {
        this.registry.listVersions(modelId, { limit: 100, offset: 0 }).subscribe((page) => {
          this.versions.set(page.items);
        });
      }
    });
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    const { modelVersionId, environment, simulateFailure } = this.form.getRawValue();
    this.ref.close({
      modelVersionId,
      environment: environment as CreateDeployment['environment'],
      simulateFailure,
    });
  }
}

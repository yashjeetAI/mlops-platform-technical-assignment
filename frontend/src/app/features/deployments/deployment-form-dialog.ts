import { Component, inject, signal } from '@angular/core';
import { FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { RegistryService } from '../../core/registry.service';
import { ModelSummary, ModelVersion } from '../../core/registry.models';
import { CreateDeployment, ENVIRONMENTS } from '../../core/deployment.models';

/** Optional pre-fill (e.g. opening from a version row). */
export interface DeployDialogData {
  modelId: string;
  modelName: string;
  versionId: string;
  versionLabel: string;
}

@Component({
  selector: 'app-deployment-form-dialog',
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatAutocompleteModule,
    MatSelectModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
  ],
  templateUrl: './deployment-form-dialog.html',
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
      .prefilled {
        margin-bottom: 0.75rem;
        font-size: 0.9rem;
      }
      .prefilled strong {
        font-weight: 600;
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
  /** Present when opened pre-filled from a version. */
  readonly data = inject<DeployDialogData | null>(MAT_DIALOG_DATA, { optional: true });

  readonly models = signal<ModelSummary[]>([]);
  readonly versions = signal<ModelVersion[]>([]);
  readonly environments = ENVIRONMENTS;

  // Autocomplete input; its value becomes a ModelSummary once an option is picked.
  readonly modelSearch = new FormControl<string | ModelSummary>('');

  readonly form = this.fb.nonNullable.group({
    modelId: ['', Validators.required],
    modelVersionId: ['', Validators.required],
    environment: ['', Validators.required],
    simulateFailure: [false],
  });

  constructor() {
    if (this.data) {
      // Pre-filled from a version: model + version are fixed (no lookup needed).
      this.form.patchValue({
        modelId: this.data.modelId,
        modelVersionId: this.data.versionId,
      });
    }
  }

  /** Server-side model search (scales to thousands of models). */
  onModelSearch(term: string): void {
    if (!term || term.length < 1) {
      this.models.set([]);
      return;
    }
    this.registry.listModels({ limit: 20, offset: 0, q: term }).subscribe((page) => {
      this.models.set(page.items);
    });
  }

  pickModel(model: ModelSummary): void {
    this.form.patchValue({ modelId: model.id, modelVersionId: '' });
    this.versions.set([]);
    this.registry.listVersions(model.id, { limit: 100, offset: 0 }).subscribe((page) => {
      this.versions.set(page.items);
    });
  }

  displayModel(value: ModelSummary | string | null): string {
    return value && typeof value !== 'string' ? value.name : '';
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

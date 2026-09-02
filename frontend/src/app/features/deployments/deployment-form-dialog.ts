import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
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
    MatSelectModule,
    MatInputModule,
    MatIconModule,
    MatCheckboxModule,
    MatButtonModule,
  ],
  templateUrl: './deployment-form-dialog.html',
  styleUrl: './deployment-form-dialog.scss',
})
export class DeploymentFormDialog {
  private readonly fb = inject(FormBuilder);
  private readonly registry = inject(RegistryService);
  private readonly ref = inject(MatDialogRef<DeploymentFormDialog, CreateDeployment>);
  /** Present when opened pre-filled from a version. */
  readonly data = inject<DeployDialogData | null>(MAT_DIALOG_DATA, { optional: true });

  readonly models = signal<ModelSummary[]>([]); // server search results
  readonly selectedModel = signal<ModelSummary | null>(null);
  readonly versions = signal<ModelVersion[]>([]);
  readonly versionQuery = signal('');
  readonly environments = ENVIRONMENTS;

  // Keep the selected model in the options so mat-select can display it even
  // after the search results change.
  readonly modelOptions = computed<ModelSummary[]>(() => {
    const sel = this.selectedModel();
    const list = this.models();
    return sel && !list.some((m) => m.id === sel.id) ? [sel, ...list] : list;
  });

  readonly filteredVersions = computed<ModelVersion[]>(() => {
    const q = this.versionQuery().toLowerCase();
    const list = this.versions();
    return q ? list.filter((v) => `v${v.version} ${v.stage}`.toLowerCase().includes(q)) : list;
  });

  readonly form = this.fb.nonNullable.group({
    modelId: ['', Validators.required],
    modelVersionId: ['', Validators.required],
    environment: ['', Validators.required],
    simulateFailure: [false],
  });

  constructor() {
    if (this.data) {
      // Pre-filled from a version: model + version are fixed.
      this.form.patchValue({
        modelId: this.data.modelId,
        modelVersionId: this.data.versionId,
      });
    } else {
      this.searchModels(''); // initial list so the dropdown isn't empty
    }
  }

  searchModels(term: string): void {
    this.registry.listModels({ limit: 20, offset: 0, q: term || undefined }).subscribe((page) => {
      this.models.set(page.items);
    });
  }

  onModelChange(modelId: string): void {
    const model = this.modelOptions().find((m) => m.id === modelId) ?? null;
    this.selectedModel.set(model);
    this.form.patchValue({ modelVersionId: '' });
    this.versions.set([]);
    this.versionQuery.set('');
    if (model) {
      this.registry.listVersions(model.id, { limit: 100, offset: 0 }).subscribe((page) => {
        this.versions.set(page.items);
      });
    }
  }

  onVersionSearch(term: string): void {
    this.versionQuery.set(term);
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

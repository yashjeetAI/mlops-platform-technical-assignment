import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { CreateVersion } from '../../core/registry.models';

@Component({
  selector: 'app-version-form-dialog',
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
  ],
  template: `
    <h2 mat-dialog-title>Register version</h2>
    <form [formGroup]="form" (ngSubmit)="submit()">
      <mat-dialog-content class="dialog-body">
        <mat-form-field appearance="outline">
          <mat-label>Version</mat-label>
          <input matInput formControlName="version" placeholder="1.0.0" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Artifact URI</mat-label>
          <input matInput formControlName="artifactUri" placeholder="s3://models/…" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Algorithm (optional)</mat-label>
          <input matInput formControlName="algorithm" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Training-data ref (optional)</mat-label>
          <input matInput formControlName="trainingDataRef" />
        </mat-form-field>
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancel</button>
        <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid">
          Create
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [
    `
      .dialog-body {
        display: flex;
        flex-direction: column;
        min-width: 320px;
        padding-top: 0.5rem;
      }
      mat-form-field {
        width: 100%;
      }
    `,
  ],
})
export class VersionFormDialog {
  private readonly fb = inject(FormBuilder);
  private readonly ref = inject(MatDialogRef<VersionFormDialog, CreateVersion>);

  readonly form = this.fb.nonNullable.group({
    version: ['', Validators.required],
    artifactUri: ['', Validators.required],
    algorithm: [''],
    trainingDataRef: [''],
  });

  submit(): void {
    if (this.form.valid) {
      this.ref.close(this.form.getRawValue());
    }
  }
}

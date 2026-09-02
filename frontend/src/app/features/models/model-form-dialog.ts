import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { CreateModel } from '../../core/registry.models';

@Component({
  selector: 'app-model-form-dialog',
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
  ],
  template: `
    <h2 mat-dialog-title>Register model</h2>
    <form [formGroup]="form" (ngSubmit)="submit()">
      <mat-dialog-content class="dialog-body">
        <mat-form-field appearance="outline">
          <mat-label>Key (slug)</mat-label>
          <input matInput formControlName="key" placeholder="pump-failure-predictor" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Name</mat-label>
          <input matInput formControlName="name" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Owner</mat-label>
          <input matInput formControlName="owner" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Framework</mat-label>
          <input matInput formControlName="framework" placeholder="scikit-learn" />
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
export class ModelFormDialog {
  private readonly fb = inject(FormBuilder);
  private readonly ref = inject(MatDialogRef<ModelFormDialog, CreateModel>);

  readonly form = this.fb.nonNullable.group({
    key: ['', Validators.required],
    name: ['', Validators.required],
    owner: ['', Validators.required],
    framework: ['', Validators.required],
  });

  submit(): void {
    if (this.form.valid) {
      this.ref.close(this.form.getRawValue());
    }
  }
}

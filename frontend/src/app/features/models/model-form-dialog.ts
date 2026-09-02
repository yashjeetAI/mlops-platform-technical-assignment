import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { CreateModel, FRAMEWORKS } from '../../core/registry.models';

@Component({
  selector: 'app-model-form-dialog',
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
  ],
  template: `
    <h2 mat-dialog-title>Register model</h2>
    <form [formGroup]="form" (ngSubmit)="submit()">
      <mat-dialog-content class="dialog-body">
        <mat-form-field appearance="outline">
          <mat-label>Name</mat-label>
          <input matInput formControlName="name" placeholder="Pump Failure Predictor" />
          <mat-hint><span class="abb-hint">Slug is auto-generated.</span></mat-hint>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Owner</mat-label>
          <input matInput formControlName="owner" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Framework</mat-label>
          <mat-select formControlName="framework">
            @for (fw of frameworks; track fw) {
              <mat-option [value]="fw">{{ fw }}</mat-option>
            }
          </mat-select>
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
        gap: 0.4rem;
        width: 26rem;
        max-width: 80vw;
        padding-top: 0.75rem;
      }
      mat-form-field {
        width: 100%;
      }
      .abb-hint {
        color: var(--abb-red);
      }
    `,
  ],
})
export class ModelFormDialog {
  private readonly fb = inject(FormBuilder);
  private readonly ref = inject(MatDialogRef<ModelFormDialog, CreateModel>);

  readonly frameworks = FRAMEWORKS;

  readonly form = this.fb.nonNullable.group({
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

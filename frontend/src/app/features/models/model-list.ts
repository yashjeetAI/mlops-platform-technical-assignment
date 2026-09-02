import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';

import { AuthService } from '../../core/auth.service';
import { Role } from '../../core/models';
import { apiErrorMessage, RegistryService } from '../../core/registry.service';
import { CreateModel, ModelSummary } from '../../core/registry.models';
import { ModelFormDialog } from './model-form-dialog';

@Component({
  selector: 'app-model-list',
  imports: [
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatTableModule,
  ],
  templateUrl: './model-list.html',
  styleUrl: './model-list.scss',
})
export class ModelList {
  private readonly registry = inject(RegistryService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  private readonly breakpoints = inject(BreakpointObserver);

  /** Table on desktop, cards on small screens. */
  readonly isHandset = toSignal(
    this.breakpoints.observe(Breakpoints.Handset).pipe(map((r) => r.matches)),
    { initialValue: false },
  );
  readonly columns = ['name', 'key', 'owner', 'framework', 'action'];

  readonly models = signal<ModelSummary[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly search = signal('');

  readonly canCreate = this.auth.hasRole(Role.ENGINEER);

  readonly filtered = computed(() => {
    const q = this.search().trim().toLowerCase();
    const list = this.models();
    if (!q) {
      return list;
    }
    return list.filter((m) =>
      [m.name, m.key, m.owner, m.framework].some((f) => f.toLowerCase().includes(q)),
    );
  });

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.registry.listModels().subscribe({
      next: (models) => {
        this.models.set(models);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err, 'Failed to load models.'));
        this.loading.set(false);
      },
    });
  }

  onSearch(value: string): void {
    this.search.set(value);
  }

  open(model: ModelSummary): void {
    void this.router.navigate(['/models', model.id]);
  }

  createModel(): void {
    const ref = this.dialog.open(ModelFormDialog);
    ref.afterClosed().subscribe((payload: CreateModel | undefined) => {
      if (!payload) {
        return;
      }
      this.registry.createModel(payload).subscribe({
        next: (model) => {
          this.snack.open(`Model "${model.name}" created`, 'Dismiss', { duration: 3000 });
          this.load();
        },
        error: (err) => this.snack.open(apiErrorMessage(err), 'Dismiss', { duration: 5000 }),
      });
    });
  }
}

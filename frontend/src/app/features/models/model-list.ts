import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { debounceTime, distinctUntilChanged, map, Subject } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
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
    MatPaginatorModule,
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
  readonly total = signal(0);
  readonly pageIndex = signal(0);
  readonly pageSize = signal(20);
  readonly search = signal('');
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly canCreate = this.auth.hasRole(Role.ENGINEER);

  private readonly searchInput$ = new Subject<string>();

  constructor() {
    // Debounced, server-side search — resets to the first page.
    this.searchInput$
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed())
      .subscribe((q) => {
        this.search.set(q);
        this.pageIndex.set(0);
        this.load();
      });
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.registry
      .listModels({
        limit: this.pageSize(),
        offset: this.pageIndex() * this.pageSize(),
        q: this.search() || undefined,
      })
      .subscribe({
        next: (page) => {
          this.models.set(page.items);
          this.total.set(page.total);
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(apiErrorMessage(err, 'Failed to load models.'));
          this.loading.set(false);
        },
      });
  }

  onSearch(value: string): void {
    this.searchInput$.next(value);
  }

  onPage(event: PageEvent): void {
    this.pageIndex.set(event.pageIndex);
    this.pageSize.set(event.pageSize);
    this.load();
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
          this.pageIndex.set(0);
          this.load();
        },
        error: (err) => this.snack.open(apiErrorMessage(err), 'Dismiss', { duration: 5000 }),
      });
    });
  }
}

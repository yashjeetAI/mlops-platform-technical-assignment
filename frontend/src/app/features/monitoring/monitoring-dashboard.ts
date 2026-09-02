import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { apiErrorMessage } from '../../core/registry.service';
import { MonitoringService } from '../../core/monitoring.service';
import {
  MonitoringOverviewItem,
  MonitoringSummary,
  monitoringStatusClass,
} from '../../core/monitoring.models';

interface MetricCard {
  label: string;
  value: string;
  unit: string;
  spark: number[];
}

@Component({
  selector: 'app-monitoring-dashboard',
  imports: [DatePipe, MatCardModule, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './monitoring-dashboard.html',
  styleUrl: './monitoring-dashboard.scss',
})
export class MonitoringDashboard {
  private readonly svc = inject(MonitoringService);

  readonly items = signal<MonitoringOverviewItem[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly selected = signal<MonitoringSummary | null>(null);
  readonly selectedId = signal<string | null>(null);

  readonly statusClass = monitoringStatusClass;

  readonly metricCards = computed<MetricCard[]>(() => {
    const s = this.selected();
    if (!s || !s.latest) {
      return [];
    }
    const p = s.latest;
    const series = s.series;
    return [
      { label: 'Latency', value: p.latencyMs.toFixed(1), unit: 'ms', spark: series.map((x) => x.latencyMs) },
      { label: 'Throughput', value: p.throughputRpm.toFixed(0), unit: 'rpm', spark: series.map((x) => x.throughputRpm) },
      { label: 'Error rate', value: (p.errorRate * 100).toFixed(2), unit: '%', spark: series.map((x) => x.errorRate) },
      { label: 'Quality', value: p.qualityScore.toFixed(3), unit: '', spark: series.map((x) => x.qualityScore) },
      { label: 'Drift', value: p.driftScore.toFixed(3), unit: '', spark: series.map((x) => x.driftScore) },
      { label: 'Availability', value: p.availability.toFixed(2), unit: '%', spark: series.map((x) => x.availability) },
    ];
  });

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.svc.overview().subscribe({
      next: (o) => {
        this.items.set(o.items);
        this.loading.set(false);
        // auto-select the first model with data
        const first = o.items.find((i) => i.latest) ?? o.items[0];
        if (first) {
          this.select(first);
        }
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err, 'Failed to load monitoring.'));
        this.loading.set(false);
      },
    });
  }

  select(item: MonitoringOverviewItem): void {
    this.selectedId.set(item.modelId);
    this.selected.set(null);
    this.svc.modelMetrics(item.modelId).subscribe((s) => this.selected.set(s));
  }

  /** Build an SVG polyline for a metric's recent series, normalised to 100x28. */
  sparkline(values: number[], w = 100, h = 28): string {
    if (values.length < 2) {
      return '';
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    return values
      .map((v, i) => {
        const x = (i / (values.length - 1)) * w;
        const y = h - ((v - min) / range) * h;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }
}

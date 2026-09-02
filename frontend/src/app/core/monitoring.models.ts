export enum MonitoringStatus {
  HEALTHY = 'HEALTHY',
  DEGRADED = 'DEGRADED',
  NO_DATA = 'NO_DATA',
}

export interface MetricPoint {
  timestamp: string;
  version: string;
  environment: string;
  latencyMs: number;
  throughputRpm: number;
  errorRate: number;
  qualityScore: number;
  driftScore: number;
  availability: number;
}

export interface SeriesRef {
  version: string;
  environment: string;
}

export interface MonitoringSummary {
  modelId: string;
  modelKey: string;
  name: string;
  monitoringStatus: MonitoringStatus;
  lastInferenceAt: string | null;
  version: string | null;
  environment: string | null;
  latest: MetricPoint | null;
  series: MetricPoint[];
  available: SeriesRef[];
}

export interface MonitoringOverviewItem {
  modelId: string;
  modelKey: string;
  name: string;
  monitoringStatus: MonitoringStatus;
  lastInferenceAt: string | null;
  latest: MetricPoint | null;
}

export interface MonitoringOverview {
  items: MonitoringOverviewItem[];
  total: number;
  limit: number;
  offset: number;
}

/** CSS modifier class for a monitoring-status chip (styles in styles.scss). */
export function monitoringStatusClass(status: MonitoringStatus): string {
  return `mon-chip mon-${status.toLowerCase()}`;
}

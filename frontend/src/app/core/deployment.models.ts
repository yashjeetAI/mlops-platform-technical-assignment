/** Deployment execution states — mirrors the backend `DeploymentStatus`. */
export enum DeploymentStatus {
  REQUESTED = 'REQUESTED',
  VALIDATING = 'VALIDATING',
  DEPLOYING = 'DEPLOYING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  ROLLED_BACK = 'ROLLED_BACK',
}

/** Deployment target environments — mirrors the backend `Environment`. */
export enum Environment {
  DEVELOPMENT = 'DEVELOPMENT',
  STAGING = 'STAGING',
  PRODUCTION = 'PRODUCTION',
}

export const ENVIRONMENTS = [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION];

/** States where the worker is still acting — used to decide whether to poll. */
export const IN_FLIGHT: DeploymentStatus[] = [
  DeploymentStatus.REQUESTED,
  DeploymentStatus.VALIDATING,
  DeploymentStatus.DEPLOYING,
];

export interface Deployment {
  id: string;
  modelId: string;
  modelVersionId: string;
  modelKey: string | null;
  version: string | null;
  environment: Environment;
  status: DeploymentStatus;
  idempotencyKey: string | null;
  attempts: number;
  error: string | null;
  correlationId: string | null;
  rolledBackToId: string | null;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DeploymentEvent {
  id: string;
  status: DeploymentStatus;
  event: string;
  message: string | null;
  actor: string | null;
  correlationId: string | null;
  createdAt: string;
}

export interface DeploymentDetail extends Deployment {
  events: DeploymentEvent[];
}

export interface DeploymentPage {
  items: Deployment[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateDeployment {
  modelVersionId: string;
  environment: Environment;
  idempotencyKey?: string;
  simulateFailure?: boolean;
}

export function isInFlight(status: DeploymentStatus): boolean {
  return IN_FLIGHT.includes(status);
}

/** CSS modifier class for a status chip (styles defined globally in styles.scss). */
export function statusClass(status: DeploymentStatus): string {
  return `dep-chip dep-${status.toLowerCase()}`;
}

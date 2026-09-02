/** Model-version lifecycle stages — mirrors the backend `LifecycleStage`. */
export enum LifecycleStage {
  DRAFT = 'DRAFT',
  VALIDATED = 'VALIDATED',
  APPROVED = 'APPROVED',
  STAGING = 'STAGING',
  PRODUCTION = 'PRODUCTION',
  ARCHIVED = 'ARCHIVED',
}

export interface ModelSummary {
  id: string;
  key: string;
  name: string;
  owner: string;
  framework: string;
  tags: Record<string, unknown>;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ModelVersion {
  id: string;
  modelId: string;
  version: string;
  stage: LifecycleStage;
  approved: boolean;
  algorithm: string | null;
  artifactUri: string;
  trainingDataRef: string | null;
  tags: Record<string, unknown>;
  approvedBy: string | null;
  approvedAt: string | null;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ModelPage {
  items: ModelSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ModelVersionPage {
  items: ModelVersion[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateModel {
  name: string;
  owner: string;
  framework: string;
  tags?: Record<string, unknown>;
}

/** Supported frameworks — mirrors the backend `Framework` enum. */
export const FRAMEWORKS = [
  'scikit-learn',
  'pytorch',
  'tensorflow',
  'keras',
  'xgboost',
  'lightgbm',
  'onnx',
  'transformers',
  'other',
] as const;

export interface CreateVersion {
  version: string;
  artifactUri: string;
  algorithm?: string | null;
  trainingDataRef?: string | null;
}

/**
 * Structurally-legal promote targets per stage — mirrors the backend state machine.
 * VALIDATED -> APPROVED is intentionally omitted here; that transition is the
 * dedicated "Approve" action (which records the approver).
 */
export const PROMOTE_TARGETS: Record<LifecycleStage, LifecycleStage[]> = {
  [LifecycleStage.DRAFT]: [LifecycleStage.VALIDATED, LifecycleStage.ARCHIVED],
  [LifecycleStage.VALIDATED]: [LifecycleStage.DRAFT, LifecycleStage.ARCHIVED],
  [LifecycleStage.APPROVED]: [
    LifecycleStage.STAGING,
    LifecycleStage.VALIDATED,
    LifecycleStage.ARCHIVED,
  ],
  [LifecycleStage.STAGING]: [
    LifecycleStage.PRODUCTION,
    LifecycleStage.APPROVED,
    LifecycleStage.ARCHIVED,
  ],
  [LifecycleStage.PRODUCTION]: [LifecycleStage.STAGING, LifecycleStage.ARCHIVED],
  [LifecycleStage.ARCHIVED]: [],
};

/** CSS modifier class for a stage chip (styles defined globally in styles.scss). */
export function stageClass(stage: LifecycleStage): string {
  return `stage-chip stage-${stage.toLowerCase()}`;
}


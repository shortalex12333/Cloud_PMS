/** Attention system types — role-aware, time-aware scoring */

export type Severity = 'critical' | 'warning' | 'info' | 'ok';

export type EntitySource =
  | 'fault'
  | 'work_order'
  | 'certificate'
  | 'equipment'
  | 'parts'
  | 'hor_warning'
  | 'hor_signoff'
  | 'receiving'
  | 'handover'
  | 'shopping_list';

export type CrewRole =
  | 'captain'
  | 'chief_engineer'
  | 'eto'
  | 'manager'
  | 'engineer'
  | 'crew'
  | 'deck'
  | 'interior';

export interface ScoredPointer {
  id: string;
  entityId: string;
  source: EntitySource;
  severity: Severity;
  score: number;
  main: string;
  sub: string;
  time: string;
  route: string;
}

export interface AttentionCounts {
  faults: number;
  work_orders: number;
  certificates: number;
  equipment: number;
  parts: number;
  hor_warnings: number;
  hor_signoffs: number;
  receiving: number;
  handover: number;
  shopping_list: number;
}

export interface PillConfig {
  label: string;
  countKey: keyof AttentionCounts | null;
  route: string;
  action?: boolean;
}

/**
 * CelesteOS Situations Module
 *
 * Re-exports all situation detection and management functionality.
 */

// Types
export type {
  Severity,
  SituationType,
  EntityType,
  SituationDomain,
  Urgency,
  UserRole,
  Situation,
  Recommendation,
  ResolvedEntity,
  VesselContext,
  RecurrenceCheckResult,
  WorkOrderSummary,
  SituationContext,
  QueryIntent,
  DetectionResult,
} from './types';

// Engine
export { SituationEngine, getSituationEngine } from './situation-engine';

// Intent Parser
export {
  classifyIntent,
  parseActionQuery,
  extractEntityReferences,
  detectSymptomCodes,
} from './intent-parser';

// Hooks
export { useSituation, useSituationContext } from './hooks';

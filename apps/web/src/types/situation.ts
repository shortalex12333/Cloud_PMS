/**
 * CelesteOS Situation State Management
 *
 * Implements the situation state machine that tracks user intent and context
 * across different entity types (documents, equipment, work orders, etc.)
 *
 * States: IDLE → CANDIDATE → ACTIVE → COOLDOWN → RESOLVED
 *
 * Based on:
 * - /Desktop/situation/active situation state.md
 * - /Desktop/situation/Document Situation View.md
 */

// ============================================================================
// SITUATION STATE MACHINE
// ============================================================================

/**
 * Situation lifecycle states
 */
export type SituationState =
  | 'IDLE'      // No active situation (global search mode)
  | 'CANDIDATE' // Result selected but not yet opened (preview mode)
  | 'ACTIVE'    // Entity opened, situation is active
  | 'COOLDOWN'  // Action completed, waiting for next move
  | 'RESOLVED'; // Situation fully resolved (closed)

/**
 * Primary entity types that can create situations
 */
export type EntityType =
  | 'document'
  | 'equipment'
  | 'part'
  | 'work_order'
  | 'fault'
  | 'location'
  | 'person'
  | 'inventory'
  | 'email_thread';

/**
 * Domain classification for different operational areas
 */
export type SituationDomain =
  | 'manuals'      // Document reading, manual sections
  | 'maintenance'  // Work orders, equipment history
  | 'inventory'    // Parts, stock, locations
  | 'hor'          // Hours of Rest compliance
  | 'purchasing'   // Ordering, procurement
  | 'people'       // Crew management, assignments
  | 'email';       // Email threads as evidence

/**
 * Situation phase (inferred from evidence flags)
 */
export type SituationPhase =
  | 'investigating'  // User is gathering context
  | 'acting'         // User is preparing/executing actions
  | 'wrapping_up';   // User is finalizing/documenting

// ============================================================================
// EVIDENCE FLAGS
// ============================================================================

/**
 * Evidence flags track user behavior to infer situation state
 * Used to determine CANDIDATE → ACTIVE transition and suggest actions
 */
export interface SituationEvidence {
  opened_manual: boolean;
  viewed_history: boolean;
  mutation_prepared: boolean;
  mutation_committed: boolean;
  handover_added: boolean;
  repeated_queries_count: number;
}

// ============================================================================
// SITUATION CONTEXT
// ============================================================================

/**
 * Complete situation context
 * Minimum fields required to trigger action scaffolding safely
 */
export interface SituationContext {
  // Identity
  yacht_id: string;
  user_id: string;
  role: string;
  device_type: 'mobile' | 'desktop';

  // Situation key
  primary_entity_type: EntityType;
  primary_entity_id: string;
  symptom_code?: string;  // Optional but powerful for equipment/fault situations
  domain: SituationDomain;

  // State
  state: SituationState;
  confidence_points: number;  // Deterministic score for state transitions
  phase: SituationPhase;

  // Evidence
  evidence: SituationEvidence;

  // Nudge control
  nudge_last_shown_at?: number;  // Unix timestamp
  nudge_dismissed: Record<string, boolean>;  // nudge_type → dismissed
  nudge_budget_remaining: number;  // Enforce "one new decision at a time"

  // Session tracking
  session_id: string;
  created_at: number;  // Unix timestamp
  last_activity_at: number;  // Unix timestamp
}

// ============================================================================
// DOCUMENT-SPECIFIC TYPES
// ============================================================================

/**
 * Document classification for visibility rules
 * Per Document Situation View.md
 */
export type DocumentClassification =
  | 'operational'   // Manuals, guides, SOPs (Add to Handover visible)
  | 'compliance';   // Certificates, licenses, approvals (Add to Handover in dropdown)

// ============================================================================
// SITUATION TRANSITIONS
// ============================================================================

/**
 * Situation state transition event
 */
export interface SituationTransition {
  from_state: SituationState;
  to_state: SituationState;
  reason: string;
  confidence_change: number;
  timestamp: number;
}

// ============================================================================
// HELPER TYPES
// ============================================================================

/**
 * Situation update payload
 */
export interface SituationUpdate {
  state?: SituationState;
  phase?: SituationPhase;
  evidence?: Partial<SituationEvidence>;
  confidence_points?: number;
  last_activity_at?: number;
}

/**
 * Situation creation payload
 */
export interface CreateSituationPayload {
  entity_type: EntityType;
  entity_id: string;
  domain: SituationDomain;
  initial_state?: SituationState;
  metadata?: Record<string, any>;
}

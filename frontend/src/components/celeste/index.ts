/**
 * CelesteOS UI Components
 * Implements the UX Grammar & Visual Token Specification
 *
 * These components form the trust contract between Celeste and the user.
 * Every element reveals state, enables choice, or protects trust.
 */

// State components
export { default as EntityLine } from './EntityLine';
export { default as StatusLine } from './StatusLine';
export { default as AuditRecord } from './AuditRecord';

// Action components
export { default as ResultCard } from './ResultCard';
export { default as ActionDropdown } from './ActionDropdown';
export type { Action, ActionType } from './ActionDropdown';

// Transition components
export { default as UncertaintySelector } from './UncertaintySelector';
export type { UncertainOption } from './UncertaintySelector';

// Commitment components
export { default as MutationPreview } from './MutationPreview';
export { default as SignaturePrompt } from './SignaturePrompt';
export type { DiffItem } from './MutationPreview';

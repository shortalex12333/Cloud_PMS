/**
 * Shared types for entity list components
 * Used by EntityList, EntityDetailOverlay, and lens-specific adapters
 */

// Result format matching SpotlightResultRow expectations
export interface EntityListResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  snippet?: string;
  metadata?: Record<string, unknown>;
}

// Generic fetch function signature
export interface FetchParams {
  yachtId: string;
  token: string;
  offset: number;
  limit: number;
}

export interface FetchResponse<T> {
  data: T[];
  total: number;
}

// Adapter function signature
export type EntityAdapter<T> = (entity: T) => EntityListResult;

// Props for EntityList component
export interface EntityListProps<T extends { id: string }> {
  queryKey: string[];
  fetchFn: (params: FetchParams) => Promise<FetchResponse<T>>;
  adapter: EntityAdapter<T>;
  onSelect: (id: string) => void;
  selectedId: string | null;
  emptyMessage?: string;
  /** Quick filter ID from URL param */
  filter?: string | null;
  /** Domain for filter execution (e.g., 'work-orders', 'faults', 'inventory') */
  filterDomain?: string;
  /** Callback when filter is cleared */
  onClearFilter?: () => void;
}

// Props for EntityDetailOverlay
export interface EntityDetailOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

/**
 * TypeScript types for search harness truth sets and results
 */

/**
 * Truth set item structure from JSONL files
 */
export interface TruthSetItem {
  title: string;
  canonical: {
    target_id: string;
    target_type: string;
  };
  queries: Array<{
    query: string;
    expected_target_id: string;
  }>;
}

/**
 * Single query execution result
 */
export interface QueryResult {
  query: string;
  expected_id: string;
  actual_ids: string[];
  rank: number | null; // 1-based rank if found, null if not found
  latency_ms: number;
  hit: boolean; // true if expected_id found in top 3
  entity_type: string;
}

/**
 * Metrics for a specific entity type
 */
export interface EntityMetrics {
  entity_type: string;
  total_queries: number;
  recall_at_3: number; // proportion of queries with hit in top 3
  mrr: number; // mean reciprocal rank
  avg_latency_ms: number;
}

/**
 * Aggregate metrics across all queries
 */
export interface AggregateMetrics {
  timestamp: string;
  total_queries: number;
  recall_at_3: number;
  mrr: number;
  p95_latency_ms: number;
  by_entity: EntityMetrics[];
}

/**
 * Search API request body (matching production API requirements)
 */
export interface SearchRequest {
  query: string;
  query_type: "free-text";
  limit: number;
  auth?: {
    user_id?: string;
    yacht_id: string | null;
    role?: string;
    email?: string;
    yacht_signature?: string;
  };
  context: {
    client_ts: number;
    stream_id: string;
    session_id: string;
    source: string;
    client_version: string;
    locale: string;
    timezone: string;
    platform: string;
  };
  stream?: boolean;
}

/**
 * Search API response
 */
export interface SearchResponse {
  results?: Array<{
    id: string;
    [key: string]: any;
  }>;
  error?: string;
}

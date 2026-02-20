#!/usr/bin/env node
/**
 * Pilot Test - Focused Subset Validation
 *
 * Runs a sample of queries (first 10 from each entity type = 90 queries)
 * against production search endpoint to validate test infrastructure
 * and collect initial performance metrics.
 */

import * as fs from 'fs';
import * as path from 'path';
import { createClient } from '@supabase/supabase-js';
import type {
  TruthSetItem,
  QueryResult,
  EntityMetrics,
  AggregateMetrics,
  SearchRequest,
  SearchResponse
} from '../types';

// Configuration
const TRUTH_SET_DIR = '/Volumes/Backup/CELESTE';
const SEARCH_ENDPOINT = 'https://pipeline-core.int.celeste7.ai/webhook/search';
const TEST_YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598'; // Cloud_PMS tenant
const REQUEST_DELAY_MS = 10; // Delay between requests to avoid rate limiting
const BATCH_SIZE = 10; // Number of parallel requests
const OUTPUT_DIR = '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test/pilot';
const QUERIES_PER_ENTITY = 10; // Sample size per entity type

// Supabase configuration (from .env.local)
const MASTER_SUPABASE_URL = 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const MASTER_SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw';

// Test user credentials (from .env.local)
const TEST_USER_EMAIL = 'crew.test@alex-short.com';
const TEST_USER_PASSWORD = 'Password2!';

// Truth set files
const TRUTH_SET_FILES = [
  'truthset_certificate.jsonl',
  'truthset_document.jsonl',
  'truthset_fault.jsonl',
  'truthset_inventory.jsonl',
  'truthset_parts.jsonl',
  'truthset_receiving.jsonl',
  'truthset_shopping_list.jsonl',
  'truthset_work_order_note.jsonl',
  'truthset_work_order.jsonl',
];

/**
 * Load truth set from JSONL file
 */
function loadTruthSet(filename: string): TruthSetItem[] {
  const filepath = path.join(TRUTH_SET_DIR, filename);
  const content = fs.readFileSync(filepath, 'utf-8');
  const lines = content.trim().split('\n');
  return lines.map(line => JSON.parse(line));
}

/**
 * Extract entity type from filename
 * e.g., "truthset_certificate.jsonl" -> "certificate"
 */
function extractEntityType(filename: string): string {
  const match = filename.match(/truthset_(.+)\.jsonl/);
  return match ? match[1] : 'unknown';
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Global state
let authToken: string | null = null;
const SESSION_ID = `pilot-${Date.now()}-${Math.random().toString(36).substring(7)}`;

/**
 * Authenticate with Supabase and get JWT token
 */
async function authenticate(): Promise<string> {
  console.log('Authenticating with Supabase...');

  const supabase = createClient(MASTER_SUPABASE_URL, MASTER_SUPABASE_ANON_KEY);

  const { data, error } = await supabase.auth.signInWithPassword({
    email: TEST_USER_EMAIL,
    password: TEST_USER_PASSWORD,
  });

  if (error || !data.session) {
    throw new Error(`Authentication failed: ${error?.message || 'No session'}`);
  }

  console.log(`✓ Authenticated as ${TEST_USER_EMAIL}`);
  return data.session.access_token;
}

/**
 * Call production search endpoint with correct payload structure
 */
async function searchQuery(query: string): Promise<{ ids: string[], latency_ms: number, error?: string }> {
  const startTime = Date.now();

  // Build payload matching production API requirements
  const request: SearchRequest = {
    query,
    query_type: "free-text",
    limit: 10,
    auth: {
      yacht_id: TEST_YACHT_ID,
      role: "crew", // Default role for testing
    },
    context: {
      client_ts: Math.floor(Date.now() / 1000),
      stream_id: `stream-${Date.now()}-${Math.random().toString(36).substring(7)}`,
      session_id: SESSION_ID,
      source: 'pilot-test',
      client_version: '1.0.0',
      locale: 'en-US',
      timezone: 'UTC',
      platform: 'node',
    },
    stream: false,
  };

  if (!authToken) {
    throw new Error('Not authenticated - call authenticate() first');
  }

  try {
    const response = await fetch(SEARCH_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify(request),
    });

    const latency_ms = Date.now() - startTime;

    if (!response.ok) {
      const errorText = await response.text();
      return { ids: [], latency_ms, error: `${response.status} ${response.statusText}: ${errorText}` };
    }

    const data = await response.json() as SearchResponse;

    if (data.error) {
      return { ids: [], latency_ms, error: data.error };
    }

    const ids = (data.results || []).map(r => r.id);
    return { ids, latency_ms };

  } catch (error) {
    const latency_ms = Date.now() - startTime;
    return { ids: [], latency_ms, error: error instanceof Error ? error.message : String(error) };
  }
}

/**
 * Calculate rank of expected ID in results (1-based)
 * Returns null if not found
 */
function calculateRank(expectedId: string, actualIds: string[]): number | null {
  const index = actualIds.indexOf(expectedId);
  return index === -1 ? null : index + 1;
}

/**
 * Calculate p95 percentile
 */
function calculateP95(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.ceil(sorted.length * 0.95) - 1;
  return sorted[Math.max(0, index)];
}

/**
 * Main execution
 */
async function main() {
  console.log('='.repeat(80));
  console.log('Pilot Test - Focused Subset Validation');
  console.log(`Sample: First ${QUERIES_PER_ENTITY} queries from each entity type`);
  console.log('='.repeat(80));
  console.log();

  // Authenticate
  try {
    authToken = await authenticate();
  } catch (error) {
    console.error('FATAL: Authentication failed:', error);
    process.exit(1);
  }
  console.log();

  const allResults: QueryResult[] = [];
  let totalQueries = 0;
  let errorCount = 0;
  let timeoutCount = 0;
  const errors: Array<{ query: string; error: string; entity_type: string }> = [];

  // Load and process each truth set (sample only)
  for (const filename of TRUTH_SET_FILES) {
    const entityType = extractEntityType(filename);
    console.log(`\nLoading ${filename} (${entityType})...`);

    let truthSet: TruthSetItem[];
    try {
      truthSet = loadTruthSet(filename);
    } catch (error) {
      console.error(`Failed to load ${filename}: ${error instanceof Error ? error.message : String(error)}`);
      continue;
    }

    // Collect all queries for this entity type
    const queries: Array<{ query: string; expected_id: string }> = [];
    for (const item of truthSet) {
      for (const queryDef of item.queries) {
        queries.push({
          query: queryDef.query,
          expected_id: queryDef.expected_target_id,
        });
      }
    }

    // Sample first N queries
    const sampledQueries = queries.slice(0, QUERIES_PER_ENTITY);
    console.log(`Sampled ${sampledQueries.length} queries (from ${queries.length} total)`);

    // Process queries in batches
    for (let i = 0; i < sampledQueries.length; i += BATCH_SIZE) {
      const batch = sampledQueries.slice(i, Math.min(i + BATCH_SIZE, sampledQueries.length));

      // Execute batch in parallel
      const batchResults = await Promise.all(
        batch.map(async (queryDef) => {
          const { ids: actualIds, latency_ms, error } = await searchQuery(queryDef.query);
          const rank = calculateRank(queryDef.expected_id, actualIds);
          const hit = rank !== null && rank <= 3;

          // Track errors
          if (error) {
            errorCount++;
            errors.push({ query: queryDef.query, error, entity_type: entityType });
            if (error.includes('timeout') || latency_ms > 30000) {
              timeoutCount++;
            }
          }

          return {
            query: queryDef.query,
            expected_id: queryDef.expected_id,
            actual_ids: actualIds,
            rank,
            latency_ms,
            hit,
            entity_type: entityType,
          };
        })
      );

      // Add results and log progress
      for (const result of batchResults) {
        totalQueries++;
        allResults.push(result);

        const status = result.hit ? '✓ hit' : '✗ miss';
        const queryDisplay = result.query.substring(0, 45).padEnd(45);
        console.log(`  ${totalQueries.toString().padStart(3)}. ${queryDisplay} -> ${status} (rank: ${result.rank || 'N/A'}, ${result.latency_ms}ms)`);
      }

      // Rate limiting between batches
      await sleep(REQUEST_DELAY_MS);
    }
  }

  console.log();
  console.log('='.repeat(80));
  console.log('Computing metrics...');
  console.log('='.repeat(80));

  // Calculate aggregate metrics
  const hits = allResults.filter(r => r.hit).length;
  const recall_at_3 = allResults.length > 0 ? hits / allResults.length : 0;

  const mrr = allResults.length > 0 ? allResults.reduce((sum, r) => {
    return sum + (r.rank !== null ? 1 / r.rank : 0);
  }, 0) / allResults.length : 0;

  const latencies = allResults.map(r => r.latency_ms);
  const p95_latency_ms = calculateP95(latencies);
  const avg_latency_ms = latencies.length > 0 ? latencies.reduce((sum, l) => sum + l, 0) / latencies.length : 0;

  // Calculate per-entity metrics
  const byEntity: EntityMetrics[] = [];
  const entityTypes = [...new Set(allResults.map(r => r.entity_type))];

  for (const entityType of entityTypes) {
    const entityResults = allResults.filter(r => r.entity_type === entityType);
    const entityHits = entityResults.filter(r => r.hit).length;
    const entityRecall = entityResults.length > 0 ? entityHits / entityResults.length : 0;
    const entityMrr = entityResults.length > 0 ? entityResults.reduce((sum, r) => {
      return sum + (r.rank !== null ? 1 / r.rank : 0);
    }, 0) / entityResults.length : 0;
    const entityLatencies = entityResults.map(r => r.latency_ms);
    const avgLatency = entityLatencies.length > 0 ? entityLatencies.reduce((sum, l) => sum + l, 0) / entityLatencies.length : 0;

    byEntity.push({
      entity_type: entityType,
      total_queries: entityResults.length,
      recall_at_3: entityRecall,
      mrr: entityMrr,
      avg_latency_ms: avgLatency,
    });
  }

  const aggregateMetrics: AggregateMetrics = {
    timestamp: new Date().toISOString(),
    total_queries: allResults.length,
    recall_at_3,
    mrr,
    p95_latency_ms,
    by_entity: byEntity,
  };

  // Save results
  const resultsPath = path.join(OUTPUT_DIR, 'results.json');
  const resultsData = {
    metadata: {
      test_type: 'pilot',
      sample_size: QUERIES_PER_ENTITY,
      timestamp: new Date().toISOString(),
      endpoint: SEARCH_ENDPOINT,
      yacht_id: TEST_YACHT_ID,
    },
    metrics: aggregateMetrics,
    error_summary: {
      total_errors: errorCount,
      timeout_count: timeoutCount,
      error_rate: allResults.length > 0 ? errorCount / allResults.length : 0,
    },
    errors: errors,
    results: allResults,
  };

  fs.writeFileSync(resultsPath, JSON.stringify(resultsData, null, 2));

  console.log();
  console.log('PILOT TEST SUMMARY');
  console.log('='.repeat(80));
  console.log(`Total Queries:   ${aggregateMetrics.total_queries.toLocaleString()}`);
  console.log(`Success Rate:    ${((1 - (errorCount / allResults.length)) * 100).toFixed(2)}%`);
  console.log(`Error Count:     ${errorCount} (${timeoutCount} timeouts)`);
  console.log(`Recall@3:        ${(aggregateMetrics.recall_at_3 * 100).toFixed(2)}%`);
  console.log(`MRR:             ${aggregateMetrics.mrr.toFixed(4)}`);
  console.log(`Avg Latency:     ${avg_latency_ms.toFixed(0)}ms`);
  console.log(`p95 Latency:     ${aggregateMetrics.p95_latency_ms.toFixed(0)}ms`);
  console.log();
  console.log('PER-ENTITY BREAKDOWN');
  console.log('-'.repeat(80));
  console.log('Entity Type'.padEnd(25) + 'Queries'.padEnd(12) + 'Recall@3'.padEnd(12) + 'MRR'.padEnd(12) + 'Avg Latency');
  console.log('-'.repeat(80));

  for (const entity of byEntity) {
    console.log(
      entity.entity_type.padEnd(25) +
      entity.total_queries.toString().padEnd(12) +
      `${(entity.recall_at_3 * 100).toFixed(1)}%`.padEnd(12) +
      entity.mrr.toFixed(4).padEnd(12) +
      `${entity.avg_latency_ms.toFixed(0)}ms`
    );
  }

  console.log('='.repeat(80));
  console.log();
  console.log(`Results saved to: ${resultsPath}`);
  console.log();

  // Exit with error code if high error rate
  if (errorCount / allResults.length > 0.1) {
    console.error('WARNING: Error rate exceeds 10% - check logs');
    process.exit(1);
  }
}

// Execute
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});

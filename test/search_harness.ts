#!/usr/bin/env node
/**
 * Search Harness - Baseline Metrics Collection
 *
 * Runs all 2,700 truth set queries against production search endpoint
 * Records Recall@3, MRR, and p95 latency metrics
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
} from './types';

// Configuration
const TRUTH_SET_DIR = '/Volumes/Backup/CELESTE';
const SEARCH_ENDPOINT = 'https://pipeline-core.int.celeste7.ai/webhook/search';
const TEST_YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598'; // Cloud_PMS tenant
const REQUEST_DELAY_MS = 10; // Delay between requests to avoid rate limiting
const BATCH_SIZE = 10; // Number of parallel requests
const OUTPUT_DIR = '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test/baseline';

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
const SESSION_ID = `harness-${Date.now()}-${Math.random().toString(36).substring(7)}`;

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
async function searchQuery(query: string): Promise<{ ids: string[], latency_ms: number }> {
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
      source: 'test-harness',
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
      // Log first error with full response for debugging
      if (startTime === Date.now() - latency_ms) {
        const errorText = await response.text();
        console.error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
      }
      return { ids: [], latency_ms };
    }

    const data = await response.json() as SearchResponse;

    if (data.error) {
      console.error(`Search error: ${data.error}`);
      return { ids: [], latency_ms };
    }

    const ids = (data.results || []).map(r => r.id);
    return { ids, latency_ms };

  } catch (error) {
    const latency_ms = Date.now() - startTime;
    console.error(`Request failed: ${error instanceof Error ? error.message : String(error)}`);
    return { ids: [], latency_ms };
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
  console.log('Search Harness - Baseline Metrics Collection');
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

  // Create output directory
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const allResults: QueryResult[] = [];
  let totalQueries = 0;

  // Load and process each truth set
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

    console.log(`Loaded ${truthSet.length} items with ${truthSet.reduce((sum, item) => sum + item.queries.length, 0)} queries`);

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

    // Process queries in batches
    for (let i = 0; i < queries.length; i += BATCH_SIZE) {
      const batch = queries.slice(i, Math.min(i + BATCH_SIZE, queries.length));

      // Execute batch in parallel
      const batchResults = await Promise.all(
        batch.map(async (queryDef) => {
          const { ids: actualIds, latency_ms } = await searchQuery(queryDef.query);
          const rank = calculateRank(queryDef.expected_id, actualIds);
          const hit = rank !== null && rank <= 3;

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
        console.log(`Query ${totalQueries}: ${result.query.substring(0, 50).padEnd(50)} -> ${status} (rank: ${result.rank || 'N/A'})`);
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
  const recall_at_3 = hits / allResults.length;

  const mrr = allResults.reduce((sum, r) => {
    return sum + (r.rank !== null ? 1 / r.rank : 0);
  }, 0) / allResults.length;

  const latencies = allResults.map(r => r.latency_ms);
  const p95_latency_ms = calculateP95(latencies);

  // Calculate per-entity metrics
  const byEntity: EntityMetrics[] = [];
  const entityTypes = [...new Set(allResults.map(r => r.entity_type))];

  for (const entityType of entityTypes) {
    const entityResults = allResults.filter(r => r.entity_type === entityType);
    const entityHits = entityResults.filter(r => r.hit).length;
    const entityRecall = entityHits / entityResults.length;
    const entityMrr = entityResults.reduce((sum, r) => {
      return sum + (r.rank !== null ? 1 / r.rank : 0);
    }, 0) / entityResults.length;
    const entityLatencies = entityResults.map(r => r.latency_ms);
    const avgLatency = entityLatencies.reduce((sum, l) => sum + l, 0) / entityLatencies.length;

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
  const metricsPath = path.join(OUTPUT_DIR, 'metrics.json');
  const resultsPath = path.join(OUTPUT_DIR, 'results.jsonl');

  fs.writeFileSync(metricsPath, JSON.stringify(aggregateMetrics, null, 2));
  fs.writeFileSync(resultsPath, allResults.map(r => JSON.stringify(r)).join('\n'));

  console.log();
  console.log('BASELINE METRICS SUMMARY');
  console.log('='.repeat(80));
  console.log(`Total Queries:   ${aggregateMetrics.total_queries.toLocaleString()}`);
  console.log(`Recall@3:        ${(aggregateMetrics.recall_at_3 * 100).toFixed(2)}%`);
  console.log(`MRR:             ${aggregateMetrics.mrr.toFixed(4)}`);
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
  console.log(`Metrics saved to: ${metricsPath}`);
  console.log(`Results saved to: ${resultsPath}`);
  console.log();
}

// Execute
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});

#!/usr/bin/env node
/**
 * Pilot Test: Truth Set Validation (F1 Streaming Endpoint)
 *
 * Runs first 3 items from each entity type against F1 streaming search endpoint.
 * Total: 9 entity types × 3 items × 12 queries = 324 queries
 *
 * SURGICAL STRIKE: Pivoted from /webhook/search (hard tiers) to /api/f1/search/stream (RRF)
 */

import * as fs from 'fs';
import * as path from 'path';
import { createClient } from '@supabase/supabase-js';

// Configuration
const TRUTH_SETS_DIR = '/Volumes/Backup/CELESTE';
const SEARCH_ENDPOINT = 'https://pipeline-core.int.celeste7.ai/api/f1/search/stream';
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';
const DELAY_MS = 100;
const ITEMS_PER_TYPE = 3;

// Supabase configuration
const MASTER_SUPABASE_URL = 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const MASTER_SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw';

// Test user credentials
const TEST_USER_EMAIL = 'crew.test@alex-short.com';
const TEST_USER_PASSWORD = 'Password2!';

const ENTITY_TYPES = [
  'certificate',
  'document',
  'fault',
  'inventory',
  'parts',
  'receiving',
  'shopping_list',
  'work_order_note',
  'work_order'
];

// Map truth set entity_type to database object_type(s)
// Some entity types map to multiple DB types (e.g., inventory items may be stored as 'part')
const ENTITY_TO_DB_TYPES: Record<string, string[]> = {
  'certificate': ['certificate'],
  'document': ['document'],
  'fault': ['fault'],
  'inventory': ['inventory', 'part'],  // Inventory items may be stored as 'part'
  'parts': ['part', 'inventory'],       // Parts may be stored as either
  'receiving': ['receiving'],
  'shopping_list': ['shopping_item'],   // DB uses 'shopping_item' not 'shopping_list'
  'work_order_note': ['work_order_note'],
  'work_order': ['work_order']
};

interface TruthSetItem {
  title: string;
  canonical: {
    target_type: string;
    target_id: string;
    primary_table: string;
  };
  queries: Array<{
    query: string;
    intent_type: string;
    implied_filters: string[];
    expected_target_id: string;
  }>;
}

interface TestResult {
  entity_type: string;
  item_index: number;
  query_index: number;
  query: string;
  expected_id: string;
  actual_ids: string[];
  hit: boolean;
  latency_ms: number;
  error?: string;
}

// Global auth state
let authToken: string | null = null;
const SESSION_ID = `pilot-${Date.now()}-${Math.random().toString(36).substring(7)}`;

// Authenticate with Supabase
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

  console.log(`✓ Authenticated as ${TEST_USER_EMAIL}\n`);
  return data.session.access_token;
}

// Sleep utility
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

interface SearchResultItem {
  id: string;
  object_type: string;
}

// Parse SSE stream and extract result IDs with object_type
async function parseSSEStream(response: Response): Promise<SearchResultItem[]> {
  const results: SearchResultItem[] = [];

  if (!response.body) {
    return results;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        // Parse SSE event format
        if (trimmed.startsWith('data:')) {
          const jsonStr = trimmed.substring(5).trim();
          if (jsonStr && jsonStr !== '[DONE]') {
            try {
              const event = JSON.parse(jsonStr);
              // F1 streaming sends result_batch events with items array
              if (event.items && Array.isArray(event.items)) {
                for (const item of event.items) {
                  if (item.object_id && item.object_type) {
                    results.push({ id: item.object_id, object_type: item.object_type });
                  }
                }
              }
              // Also handle single result events
              if (event.object_id && event.object_type) {
                results.push({ id: event.object_id, object_type: event.object_type });
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  return results;
}

// Call F1 search streaming endpoint
async function searchQuery(query: string): Promise<{ results: SearchResultItem[]; latency_ms: number }> {
  const startTime = Date.now();

  if (!authToken) {
    throw new Error('Not authenticated');
  }

  try {
    // F1 endpoint uses GET with query params
    const params = new URLSearchParams({
      q: query,
    });

    const url = `${SEARCH_ENDPOINT}?${params.toString()}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Accept': 'text/event-stream',
      },
    });

    const latency_ms = Date.now() - startTime;

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
    }

    // Parse SSE stream to extract results with object_type
    const results = await parseSSEStream(response);

    return { results, latency_ms };
  } catch (error) {
    const latency_ms = Date.now() - startTime;
    throw { error: error instanceof Error ? error.message : String(error), latency_ms };
  }
}

// Load first N items from a truth set file
function loadTruthSetItems(entityType: string, limit: number): TruthSetItem[] {
  const filePath = path.join(TRUTH_SETS_DIR, `truthset_${entityType}.jsonl`);

  if (!fs.existsSync(filePath)) {
    console.warn(`Warning: Truth set file not found: ${filePath}`);
    return [];
  }

  const lines = fs.readFileSync(filePath, 'utf-8').trim().split('\n');
  const items: TruthSetItem[] = [];

  for (let i = 0; i < Math.min(limit, lines.length); i++) {
    try {
      items.push(JSON.parse(lines[i]));
    } catch (error) {
      console.warn(`Warning: Failed to parse line ${i + 1} in ${entityType}: ${error}`);
    }
  }

  return items;
}

// Calculate metrics
function calculateMetrics(results: TestResult[]): void {
  const hits = results.filter(r => r.hit).length;
  const total = results.length;
  const recall = (hits / total * 100).toFixed(2);

  const avgLatency = results.reduce((sum, r) => sum + r.latency_ms, 0) / total;
  const errors = results.filter(r => r.error).length;

  console.log('\n' + '='.repeat(60));
  console.log('PILOT TEST RESULTS (F1 Streaming Endpoint)');
  console.log('='.repeat(60));
  console.log(`Recall@3: ${recall}% (${hits}/${total} hits)`);
  console.log(`Average Latency: ${avgLatency.toFixed(0)}ms`);
  console.log(`Errors: ${errors}`);
  console.log('='.repeat(60));

  // Breakdown by entity type
  console.log('\nBreakdown by Entity Type:');
  for (const entityType of ENTITY_TYPES) {
    const typeResults = results.filter(r => r.entity_type === entityType);
    const typeHits = typeResults.filter(r => r.hit).length;
    const typeTotal = typeResults.length;
    const typeRecall = typeTotal > 0 ? (typeHits / typeTotal * 100).toFixed(1) : 'N/A';
    console.log(`  ${entityType.padEnd(20)} ${typeRecall}% (${typeHits}/${typeTotal})`);
  }
}

// Main test execution
async function runPilotTest(): Promise<void> {
  console.log('Starting Pilot Test (F1 Streaming Endpoint)...');
  console.log(`Endpoint: ${SEARCH_ENDPOINT}`);
  console.log(`Yacht ID: ${YACHT_ID}`);
  console.log(`Items per type: ${ITEMS_PER_TYPE}`);
  console.log(`Delay between requests: ${DELAY_MS}ms\n`);

  // Authenticate first
  try {
    authToken = await authenticate();
  } catch (error) {
    console.error('FATAL: Authentication failed:', error);
    process.exit(1);
  }

  const results: TestResult[] = [];
  let totalQueries = 0;
  let completedQueries = 0;

  // Calculate total queries
  for (const entityType of ENTITY_TYPES) {
    const items = loadTruthSetItems(entityType, ITEMS_PER_TYPE);
    totalQueries += items.reduce((sum, item) => sum + item.queries.length, 0);
  }

  console.log(`Total queries to run: ${totalQueries}\n`);

  // Execute tests
  for (const entityType of ENTITY_TYPES) {
    console.log(`\nProcessing entity type: ${entityType}`);
    const items = loadTruthSetItems(entityType, ITEMS_PER_TYPE);
    console.log(`  Loaded ${items.length} items`);

    for (let itemIndex = 0; itemIndex < items.length; itemIndex++) {
      const item = items[itemIndex];
      console.log(`  Item ${itemIndex + 1}/${items.length}: ${item.title}`);

      for (let queryIndex = 0; queryIndex < item.queries.length; queryIndex++) {
        const queryObj = item.queries[queryIndex];
        completedQueries++;

        process.stdout.write(`    Query ${queryIndex + 1}/12: "${queryObj.query.substring(0, 40)}..." `);

        try {
          const { results: searchResults, latency_ms } = await searchQuery(queryObj.query);

          // Group results by object_type for category-aware Recall@3
          const resultsByCategory: Record<string, string[]> = {};
          for (const result of searchResults) {
            if (!resultsByCategory[result.object_type]) {
              resultsByCategory[result.object_type] = [];
            }
            resultsByCategory[result.object_type].push(result.id);
          }

          // Check if expected_id is in top 3 of its mapped DB categories
          // Use ENTITY_TO_DB_TYPES mapping since truth set entity types may differ from DB object_types
          const dbTypes = ENTITY_TO_DB_TYPES[entityType] || [entityType];
          let categoryResults: string[] = [];
          for (const dbType of dbTypes) {
            categoryResults = categoryResults.concat(resultsByCategory[dbType] || []);
          }
          const hit = categoryResults.slice(0, 3).includes(queryObj.expected_target_id); // Category-aware Recall@3

          results.push({
            entity_type: entityType,
            item_index: itemIndex,
            query_index: queryIndex,
            query: queryObj.query,
            expected_id: queryObj.expected_target_id,
            actual_ids: categoryResults.slice(0, 3),
            hit,
            latency_ms,
          });

          console.log(`${hit ? '✓' : '✗'} ${latency_ms}ms [${completedQueries}/${totalQueries}]`);
        } catch (err: any) {
          results.push({
            entity_type: entityType,
            item_index: itemIndex,
            query_index: queryIndex,
            query: queryObj.query,
            expected_id: queryObj.expected_target_id,
            actual_ids: [],
            hit: false,
            latency_ms: err.latency_ms || 0,
            error: err.error || String(err),
          });

          console.log(`✗ ERROR: ${err.error || err} [${completedQueries}/${totalQueries}]`);
        }

        // Delay between requests
        if (completedQueries < totalQueries) {
          await sleep(DELAY_MS);
        }
      }
    }
  }

  // Calculate and display metrics
  calculateMetrics(results);

  // Save results
  const outputPath = path.join('/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test/pilot', 'pilot_results.json');
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
  console.log(`\nResults saved to: ${outputPath}`);
}

// Run the test
runPilotTest().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});

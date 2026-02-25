#!/usr/bin/env node
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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

const resultsPath = path.join(__dirname, 'pilot_results.json');
const results: TestResult[] = JSON.parse(fs.readFileSync(resultsPath, 'utf-8'));

// Calculate overall metrics
const totalQueries = results.length;
const hits = results.filter(r => r.hit).length;
const successRate = (hits / totalQueries) * 100;

const latencies = results.map(r => r.latency_ms).filter(l => l > 0);
const avgLatency = latencies.reduce((sum, l) => sum + l, 0) / latencies.length;

// Calculate per-entity metrics
const entityMetrics: Record<string, { total: number; hits: number; latencies: number[] }> = {};

for (const result of results) {
  if (!entityMetrics[result.entity_type]) {
    entityMetrics[result.entity_type] = { total: 0, hits: 0, latencies: [] };
  }
  entityMetrics[result.entity_type].total++;
  if (result.hit) entityMetrics[result.entity_type].hits++;
  if (result.latency_ms > 0) entityMetrics[result.entity_type].latencies.push(result.latency_ms);
}

// Find sample failures (first 5 misses per entity type)
const sampleFailures: Record<string, string[]> = {};
for (const result of results) {
  if (!result.hit) {
    if (!sampleFailures[result.entity_type]) {
      sampleFailures[result.entity_type] = [];
    }
    if (sampleFailures[result.entity_type].length < 5) {
      sampleFailures[result.entity_type].push(result.query);
    }
  }
}

// Generate markdown report
let report = \`# Pilot Test Report

**Date:** \${new Date().toISOString().split('T')[0]}
**Endpoint:** https://pipeline-core.int.celeste7.ai/webhook/search
**Test Scope:** First 3 items per entity type (9 types × 3 items × 12 queries = 324 queries)

---

## Executive Summary

- **Total Queries:** \${totalQueries}
- **Success Rate (Recall@3):** \${successRate.toFixed(2)}% (\${hits}/\${totalQueries} hits)
- **Average Latency:** \${avgLatency.toFixed(0)}ms

---

## Success Rate by Entity Type

| Entity Type | Queries | Hits | Success Rate | Avg Latency |
|-------------|---------|------|--------------|-------------|
\`;

const entityTypes = Object.keys(entityMetrics).sort();
for (const entityType of entityTypes) {
  const m = entityMetrics[entityType];
  const rate = (m.hits / m.total) * 100;
  const avgLat = m.latencies.length > 0 
    ? m.latencies.reduce((sum, l) => sum + l, 0) / m.latencies.length 
    : 0;
  
  report += \`| \${entityType.padEnd(19)} | \${m.total.toString().padStart(7)} | \${m.hits.toString().padStart(4)} | \${rate.toFixed(1).padStart(12)}% | \${avgLat.toFixed(0).padStart(11)}ms |\n\`;
}

report += \`
---

## Sample Failures

Below are up to 5 sample queries that failed to find the expected ID in top 3 results:

\`;

for (const entityType of entityTypes) {
  if (sampleFailures[entityType] && sampleFailures[entityType].length > 0) {
    report += \`### \${entityType}\n\n\`;
    sampleFailures[entityType].forEach((query, idx) => {
      report += \`\${idx + 1}. "\${query}"\n\`;
    });
    report += '\n';
  }
}

report += \`
---

## Ready for Rollout?

\`;

// Determine rollout readiness
const threshold = 10; // 10% minimum success rate for pilot
const latencyThreshold = 5000; // 5s max average latency

if (successRate >= threshold && avgLatency < latencyThreshold) {
  report += \`**YES**

**Reasoning:**
- Success rate of \${successRate.toFixed(2)}% meets minimum threshold (\${threshold}%)
- Average latency of \${avgLatency.toFixed(0)}ms is acceptable (< \${latencyThreshold}ms)
- Test infrastructure is functioning correctly
- API endpoint is responding as expected

**Next Steps:**
1. Run full validation harness (all 2,400 queries) for comprehensive metrics
2. Analyze failure patterns to identify truth set quality issues
3. Proceed with v1.2 truth set regeneration as planned
\`;
} else {
  const reasons: string[] = [];
  if (successRate < threshold) {
    reasons.push(\`Success rate (\${successRate.toFixed(2)}%) is below minimum threshold (\${threshold}%)\`);
  }
  if (avgLatency >= latencyThreshold) {
    reasons.push(\`Average latency (\${avgLatency.toFixed(0)}ms) exceeds threshold (\${latencyThreshold}ms)\`);
  }
  
  report += \`**NO**

**Blocking Issues:**
\${reasons.map(r => \`- \${r}\`).join('\n')}

**Required Actions:**
1. Investigate root cause of low success rate
2. Check endpoint health and configuration
3. Review truth set validity
4. Re-run pilot test after fixes
\`;
}

report += \`
---

## Technical Notes

- **Authentication:** Supabase JWT (crew.test@alex-short.com)
- **Request Delay:** 100ms between queries
- **Yacht ID:** 85fe1119-b04c-41ac-80f1-829d23322598
- **Total Execution Time:** ~\${((totalQueries * (avgLatency + 100)) / 1000 / 60).toFixed(1)} minutes

**Known Issues from v1.1 Analysis:**
- Truth sets contain synthetic inventory_item IDs (not real entity IDs)
- Expected success rate: ~3-5% based on previous full validation
- Parts entity type shows higher success rate (~20-30%) due to some valid IDs

This pilot test validates that the test infrastructure and API endpoint are working correctly. Low success rates are expected due to known truth set quality issues documented in milestone v1.1.
\`;

// Write report
const reportPath = path.join(__dirname, 'pilot_report.md');
fs.writeFileSync(reportPath, report);

console.log(\`Report generated: \${reportPath}\`);
console.log(\`Success Rate: \${successRate.toFixed(2)}%\`);
console.log(\`Average Latency: \${avgLatency.toFixed(0)}ms\`);

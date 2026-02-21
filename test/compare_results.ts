import fs from 'fs';
import path from 'path';

// Type definitions
interface QueryResult {
  query: string;
  expected_id: string;
  actual_ids: string[];
  rank: number | null;
  latency_ms: number;
  hit: boolean;
  entity_type: string;
}

interface Metrics {
  timestamp: string;
  total_queries: number;
  recall_at_3: number;
  mrr: number;
  p95_latency_ms: number;
  by_entity: Array<{
    entity_type: string;
    total_queries: number;
    recall_at_3: number;
    mrr: number;
    avg_latency_ms: number;
  }>;
}

interface QueryDiff {
  query: string;
  expected_id: string;
  entity_type: string;
  baseline_rank: number | null;
  postdeploy_rank: number | null;
  baseline_hit: boolean;
  postdeploy_hit: boolean;
  status: 'improved' | 'regressed' | 'unchanged_hit' | 'unchanged_miss';
  rank_change?: number;
}

// Load JSONL file
function loadResults(filePath: string): QueryResult[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  return content
    .trim()
    .split('\n')
    .map(line => JSON.parse(line));
}

// Load metrics JSON
function loadMetrics(filePath: string): Metrics {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

// Compare two result sets
function compareResults(baseline: QueryResult[], postDeploy: QueryResult[]): QueryDiff[] {
  const baselineMap = new Map<string, QueryResult>();
  baseline.forEach(result => {
    const key = `${result.query}|${result.expected_id}|${result.entity_type}`;
    baselineMap.set(key, result);
  });

  const diffs: QueryDiff[] = [];

  postDeploy.forEach(postResult => {
    const key = `${postResult.query}|${postResult.expected_id}|${postResult.entity_type}`;
    const baseResult = baselineMap.get(key);

    if (!baseResult) {
      console.warn(`Query not found in baseline: ${postResult.query}`);
      return;
    }

    let status: QueryDiff['status'];
    let rankChange: number | undefined;

    // Determine status
    if (!baseResult.hit && postResult.hit) {
      status = 'improved';
      rankChange = (postResult.rank || 999) - 999;
    } else if (baseResult.hit && !postResult.hit) {
      status = 'regressed';
      rankChange = 999 - (baseResult.rank || 999);
    } else if (baseResult.hit && postResult.hit) {
      // Both hit - check if rank changed
      const baseRank = baseResult.rank || 999;
      const postRank = postResult.rank || 999;
      rankChange = postRank - baseRank;

      if (rankChange < 0) {
        status = 'improved'; // Better rank (lower number)
      } else if (rankChange > 0) {
        status = 'regressed'; // Worse rank (higher number)
      } else {
        status = 'unchanged_hit';
      }
    } else {
      status = 'unchanged_miss';
    }

    diffs.push({
      query: postResult.query,
      expected_id: postResult.expected_id,
      entity_type: postResult.entity_type,
      baseline_rank: baseResult.rank,
      postdeploy_rank: postResult.rank,
      baseline_hit: baseResult.hit,
      postdeploy_hit: postResult.hit,
      status,
      rank_change: rankChange
    });
  });

  return diffs;
}

// Generate diff.json
function generateDiffJson(
  diffs: QueryDiff[],
  baselineMetrics: Metrics,
  postDeployMetrics: Metrics,
  outputPath: string
) {
  const summary = {
    total_queries: diffs.length,
    improved: diffs.filter(d => d.status === 'improved').length,
    regressed: diffs.filter(d => d.status === 'regressed').length,
    unchanged_hit: diffs.filter(d => d.status === 'unchanged_hit').length,
    unchanged_miss: diffs.filter(d => d.status === 'unchanged_miss').length
  };

  const metricsDiff = {
    recall_at_3: {
      baseline: baselineMetrics.recall_at_3,
      post_deploy: postDeployMetrics.recall_at_3,
      delta: postDeployMetrics.recall_at_3 - baselineMetrics.recall_at_3,
      percent_change: ((postDeployMetrics.recall_at_3 - baselineMetrics.recall_at_3) / baselineMetrics.recall_at_3) * 100
    },
    mrr: {
      baseline: baselineMetrics.mrr,
      post_deploy: postDeployMetrics.mrr,
      delta: postDeployMetrics.mrr - baselineMetrics.mrr,
      percent_change: ((postDeployMetrics.mrr - baselineMetrics.mrr) / baselineMetrics.mrr) * 100
    },
    p95_latency_ms: {
      baseline: baselineMetrics.p95_latency_ms,
      post_deploy: postDeployMetrics.p95_latency_ms,
      delta: postDeployMetrics.p95_latency_ms - baselineMetrics.p95_latency_ms,
      percent_change: ((postDeployMetrics.p95_latency_ms - baselineMetrics.p95_latency_ms) / baselineMetrics.p95_latency_ms) * 100
    }
  };

  const byEntity = baselineMetrics.by_entity.map(baseEntity => {
    const postEntity = postDeployMetrics.by_entity.find(e => e.entity_type === baseEntity.entity_type);
    if (!postEntity) return null;

    const entityDiffs = diffs.filter(d => d.entity_type === baseEntity.entity_type);

    return {
      entity_type: baseEntity.entity_type,
      total_queries: baseEntity.total_queries,
      recall_at_3: {
        baseline: baseEntity.recall_at_3,
        post_deploy: postEntity.recall_at_3,
        delta: postEntity.recall_at_3 - baseEntity.recall_at_3
      },
      mrr: {
        baseline: baseEntity.mrr,
        post_deploy: postEntity.mrr,
        delta: postEntity.mrr - baseEntity.mrr
      },
      avg_latency_ms: {
        baseline: baseEntity.avg_latency_ms,
        post_deploy: postEntity.avg_latency_ms,
        delta: postEntity.avg_latency_ms - baseEntity.avg_latency_ms
      },
      improved: entityDiffs.filter(d => d.status === 'improved').length,
      regressed: entityDiffs.filter(d => d.status === 'regressed').length
    };
  }).filter(Boolean);

  const output = {
    timestamp: new Date().toISOString(),
    summary,
    metrics_diff: metricsDiff,
    by_entity: byEntity
  };

  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));
  console.log(`Generated: ${outputPath}`);
}

// Generate failures.jsonl
function generateFailuresJsonl(diffs: QueryDiff[], outputPath: string) {
  const failures = diffs.filter(d =>
    d.status === 'unchanged_miss' || d.status === 'regressed'
  );

  const lines = failures.map(f => JSON.stringify({
    query: f.query,
    expected_id: f.expected_id,
    entity_type: f.entity_type,
    baseline_rank: f.baseline_rank,
    postdeploy_rank: f.postdeploy_rank,
    status: f.status
  }));

  fs.writeFileSync(outputPath, lines.join('\n'));
  console.log(`Generated: ${outputPath} (${failures.length} failures)`);
}

// Generate report.md
function generateReport(
  diffs: QueryDiff[],
  baselineMetrics: Metrics,
  postDeployMetrics: Metrics,
  outputPath: string
) {
  const summary = {
    total_queries: diffs.length,
    improved: diffs.filter(d => d.status === 'improved').length,
    regressed: diffs.filter(d => d.status === 'regressed').length,
    unchanged_hit: diffs.filter(d => d.status === 'unchanged_hit').length,
    unchanged_miss: diffs.filter(d => d.status === 'unchanged_miss').length
  };

  const improved = diffs
    .filter(d => d.status === 'improved')
    .sort((a, b) => (a.rank_change || 0) - (b.rank_change || 0))
    .slice(0, 10);

  const regressed = diffs
    .filter(d => d.status === 'regressed')
    .sort((a, b) => (b.rank_change || 0) - (a.rank_change || 0))
    .slice(0, 10);

  let report = `# Search Pipeline Comparison Report

**Generated:** ${new Date().toISOString()}

**Baseline:** ${baselineMetrics.timestamp}
**Post-Deploy:** ${postDeployMetrics.timestamp}

---

## Executive Summary

Total queries evaluated: **${summary.total_queries}**

| Category | Count | Percentage |
|----------|-------|------------|
| Improved | ${summary.improved} | ${((summary.improved / summary.total_queries) * 100).toFixed(2)}% |
| Regressed | ${summary.regressed} | ${((summary.regressed / summary.total_queries) * 100).toFixed(2)}% |
| Unchanged (Hit) | ${summary.unchanged_hit} | ${((summary.unchanged_hit / summary.total_queries) * 100).toFixed(2)}% |
| Unchanged (Miss) | ${summary.unchanged_miss} | ${((summary.unchanged_miss / summary.total_queries) * 100).toFixed(2)}% |

---

## Overall Metrics Comparison

| Metric | Baseline | Post-Deploy | Delta | Change |
|--------|----------|-------------|-------|--------|
| **Recall@3** | ${(baselineMetrics.recall_at_3 * 100).toFixed(2)}% | ${(postDeployMetrics.recall_at_3 * 100).toFixed(2)}% | ${((postDeployMetrics.recall_at_3 - baselineMetrics.recall_at_3) * 100).toFixed(4)}% | ${(((postDeployMetrics.recall_at_3 - baselineMetrics.recall_at_3) / baselineMetrics.recall_at_3) * 100).toFixed(2)}% |
| **MRR** | ${baselineMetrics.mrr.toFixed(4)} | ${postDeployMetrics.mrr.toFixed(4)} | ${(postDeployMetrics.mrr - baselineMetrics.mrr).toFixed(4)} | ${(((postDeployMetrics.mrr - baselineMetrics.mrr) / baselineMetrics.mrr) * 100).toFixed(2)}% |
| **P95 Latency** | ${baselineMetrics.p95_latency_ms}ms | ${postDeployMetrics.p95_latency_ms}ms | ${postDeployMetrics.p95_latency_ms - baselineMetrics.p95_latency_ms}ms | ${(((postDeployMetrics.p95_latency_ms - baselineMetrics.p95_latency_ms) / baselineMetrics.p95_latency_ms) * 100).toFixed(2)}% |

---

## Per-Entity Breakdown

`;

  baselineMetrics.by_entity.forEach(baseEntity => {
    const postEntity = postDeployMetrics.by_entity.find(e => e.entity_type === baseEntity.entity_type);
    if (!postEntity) return;

    const entityDiffs = diffs.filter(d => d.entity_type === baseEntity.entity_type);
    const entityImproved = entityDiffs.filter(d => d.status === 'improved').length;
    const entityRegressed = entityDiffs.filter(d => d.status === 'regressed').length;

    report += `### ${baseEntity.entity_type} (${baseEntity.total_queries} queries)

| Metric | Baseline | Post-Deploy | Delta |
|--------|----------|-------------|-------|
| Recall@3 | ${(baseEntity.recall_at_3 * 100).toFixed(2)}% | ${(postEntity.recall_at_3 * 100).toFixed(2)}% | ${((postEntity.recall_at_3 - baseEntity.recall_at_3) * 100).toFixed(4)}% |
| MRR | ${baseEntity.mrr.toFixed(4)} | ${postEntity.mrr.toFixed(4)} | ${(postEntity.mrr - baseEntity.mrr).toFixed(4)} |
| Avg Latency | ${baseEntity.avg_latency_ms.toFixed(0)}ms | ${postEntity.avg_latency_ms.toFixed(0)}ms | ${(postEntity.avg_latency_ms - baseEntity.avg_latency_ms).toFixed(0)}ms |
| **Improved** | - | - | **${entityImproved}** |
| **Regressed** | - | - | **${entityRegressed}** |

`;
  });

  report += `---

## Top 10 Improved Queries

`;

  if (improved.length === 0) {
    report += `No queries improved.\n\n`;
  } else {
    improved.forEach((d, i) => {
      report += `${i + 1}. **${d.entity_type}**: "${d.query}"
   - Baseline: ${d.baseline_hit ? `Rank ${d.baseline_rank}` : 'Miss'}
   - Post-Deploy: ${d.postdeploy_hit ? `Rank ${d.postdeploy_rank}` : 'Miss'}
   - Change: ${d.rank_change !== undefined ? (d.rank_change > 0 ? `+${d.rank_change}` : d.rank_change) : 'N/A'} ranks

`;
    });
  }

  report += `---

## Top 10 Regressed Queries

`;

  if (regressed.length === 0) {
    report += `No queries regressed.\n\n`;
  } else {
    regressed.forEach((d, i) => {
      report += `${i + 1}. **${d.entity_type}**: "${d.query}"
   - Baseline: ${d.baseline_hit ? `Rank ${d.baseline_rank}` : 'Miss'}
   - Post-Deploy: ${d.postdeploy_hit ? `Rank ${d.postdeploy_rank}` : 'Miss'}
   - Change: ${d.rank_change !== undefined ? (d.rank_change > 0 ? `+${d.rank_change}` : d.rank_change) : 'N/A'} ranks

`;
    });
  }

  report += `---

## Recommendations

`;

  const recallDelta = postDeployMetrics.recall_at_3 - baselineMetrics.recall_at_3;
  const latencyDelta = postDeployMetrics.p95_latency_ms - baselineMetrics.p95_latency_ms;

  if (recallDelta > 0 && latencyDelta <= 0) {
    report += `### Positive Outcome

- Recall@3 improved by ${(recallDelta * 100).toFixed(4)}%
- Latency improved or stayed neutral
- **Recommendation:** Monitor in production for sustained improvement

`;
  } else if (recallDelta > 0 && latencyDelta > 0) {
    report += `### Mixed Outcome

- Recall@3 improved by ${(recallDelta * 100).toFixed(4)}%
- Latency increased by ${latencyDelta}ms (${((latencyDelta / baselineMetrics.p95_latency_ms) * 100).toFixed(2)}%)
- **Recommendation:** Evaluate if latency trade-off is acceptable

`;
  } else if (recallDelta < 0) {
    report += `### Regression Detected

- Recall@3 decreased by ${(Math.abs(recallDelta) * 100).toFixed(4)}%
- ${summary.regressed} queries regressed
- **Recommendation:** Investigate regressed queries and consider rollback

`;
  } else {
    report += `### No Significant Change

- Recall@3 unchanged (${(Math.abs(recallDelta) * 100).toFixed(4)}% delta)
- **Recommendation:** Continue with current implementation

`;
  }

  // Acceptance criteria check
  report += `---

## Acceptance Criteria Check

### Criterion 1: Recall@3 >= 90%

- **Target:** 90%
- **Actual:** ${(postDeployMetrics.recall_at_3 * 100).toFixed(2)}%
- **Status:** ${postDeployMetrics.recall_at_3 >= 0.9 ? '✓ MET' : '✗ NOT MET'}

### Criterion 2: No Latency Regression

- **Baseline P95:** ${baselineMetrics.p95_latency_ms}ms
- **Post-Deploy P95:** ${postDeployMetrics.p95_latency_ms}ms
- **Delta:** ${latencyDelta}ms (${((latencyDelta / baselineMetrics.p95_latency_ms) * 100).toFixed(2)}%)
- **Status:** ${latencyDelta <= 0 ? '✓ MET' : '✗ NOT MET'}

### Overall Verdict

`;

  if (postDeployMetrics.recall_at_3 >= 0.9 && latencyDelta <= 0) {
    report += `**✓ ALL CRITERIA MET** - Phase E (Iterate) can be skipped.\n\n`;
  } else {
    report += `**✗ CRITERIA NOT MET** - Phase E (Iterate) required to address:\n`;
    if (postDeployMetrics.recall_at_3 < 0.9) {
      report += `- Recall@3 is ${((0.9 - postDeployMetrics.recall_at_3) * 100).toFixed(2)}% below target\n`;
    }
    if (latencyDelta > 0) {
      report += `- Latency increased by ${latencyDelta}ms (${((latencyDelta / baselineMetrics.p95_latency_ms) * 100).toFixed(2)}%)\n`;
    }
    report += `\n`;
  }

  fs.writeFileSync(outputPath, report);
  console.log(`Generated: ${outputPath}`);
}

// Main execution
async function main() {
  const baseDir = '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test';

  console.log('Loading baseline results...');
  const baselineResults = loadResults(path.join(baseDir, 'baseline/results.jsonl'));
  const baselineMetrics = loadMetrics(path.join(baseDir, 'baseline/metrics.json'));

  console.log('Loading post-deploy results...');
  const postDeployResults = loadResults(path.join(baseDir, 'post-deploy/results.jsonl'));
  const postDeployMetrics = loadMetrics(path.join(baseDir, 'post-deploy/metrics.json'));

  console.log('Comparing results...');
  const diffs = compareResults(baselineResults, postDeployResults);

  console.log('Generating outputs...');
  const outputDir = path.join(baseDir, 'comparison');

  generateDiffJson(diffs, baselineMetrics, postDeployMetrics, path.join(outputDir, 'diff.json'));
  generateFailuresJsonl(diffs, path.join(outputDir, 'failures.jsonl'));
  generateReport(diffs, baselineMetrics, postDeployMetrics, path.join(outputDir, 'report.md'));

  console.log('\nComparison complete!');
  console.log(`- Improved: ${diffs.filter(d => d.status === 'improved').length}`);
  console.log(`- Regressed: ${diffs.filter(d => d.status === 'regressed').length}`);
  console.log(`- Unchanged (Hit): ${diffs.filter(d => d.status === 'unchanged_hit').length}`);
  console.log(`- Unchanged (Miss): ${diffs.filter(d => d.status === 'unchanged_miss').length}`);
}

main().catch(console.error);

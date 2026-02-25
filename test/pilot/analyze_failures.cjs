const fs = require('fs');
const results = JSON.parse(fs.readFileSync('./test/pilot/pilot_results.json', 'utf-8'));

const fails = results.filter(x => x.hit === false);
const hits = results.filter(x => x.hit === true);

console.log("=== PILOT TEST ANALYSIS ===\n");
console.log("Total queries:", results.length);
console.log("Hits (Recall@3):", hits.length, `(${(hits.length/results.length*100).toFixed(1)}%)`);
console.log("Failures:", fails.length, `(${(fails.length/results.length*100).toFixed(1)}%)`);

console.log("\n=== BY ENTITY TYPE ===");
const byType = {};
results.forEach(f => {
  if (!byType[f.entity_type]) byType[f.entity_type] = {hits: 0, misses: 0};
  if (f.hit) byType[f.entity_type].hits++;
  else byType[f.entity_type].misses++;
});
Object.entries(byType).forEach(([k,v]) => {
  const total = v.hits + v.misses;
  console.log(`  ${k}: ${v.hits}/${total} hits (${(v.hits/total*100).toFixed(1)}%)`);
});

console.log("\n=== FAILURE PATTERNS ===");
const noResults = fails.filter(f => f.actual_ids.length === 0);
const wrongResults = fails.filter(f => f.actual_ids.length > 0);
console.log("Empty results (search returned nothing):", noResults.length);
console.log("Wrong results (has results but expected not in top 3):", wrongResults.length);

console.log("\n=== SAMPLE FAILURES (first 5) ===");
fails.slice(0, 5).forEach((f, i) => {
  console.log(`\n[${i+1}] Entity: ${f.entity_type}`);
  console.log(`    Query: "${f.query}"`);
  console.log(`    Expected ID: ${f.expected_id}`);
  console.log(`    Actual IDs: ${f.actual_ids.length > 0 ? f.actual_ids.join(', ') : '(none)'}`);
});

console.log("\n=== SAMPLE HITS (first 5) ===");
hits.slice(0, 5).forEach((f, i) => {
  console.log(`\n[${i+1}] Entity: ${f.entity_type}`);
  console.log(`    Query: "${f.query}"`);
  console.log(`    Expected ID: ${f.expected_id}`);
  console.log(`    Actual IDs: ${f.actual_ids.slice(0,3).join(', ')}`);
});

// Analyze what's different between hits and misses
console.log("\n=== QUERY PATTERN ANALYSIS ===");
const hitQueries = hits.map(h => h.query.toLowerCase());
const missQueries = fails.map(f => f.query.toLowerCase());

// Common words in hits
const hitWords = {};
hitQueries.forEach(q => q.split(/\s+/).forEach(w => { hitWords[w] = (hitWords[w] || 0) + 1; }));
const missWords = {};
missQueries.forEach(q => q.split(/\s+/).forEach(w => { missWords[w] = (missWords[w] || 0) + 1; }));

console.log("Words more common in HITS:");
const hitOnly = Object.entries(hitWords)
  .filter(([w, c]) => c > 2 && (!missWords[w] || hitWords[w]/hits.length > missWords[w]/fails.length * 1.5))
  .sort((a,b) => b[1] - a[1])
  .slice(0, 10);
hitOnly.forEach(([w, c]) => console.log(`  "${w}": ${c} hits`));

console.log("\nEntity types with ALL misses (need investigation):");
Object.entries(byType)
  .filter(([k, v]) => v.hits === 0)
  .forEach(([k, v]) => console.log(`  ${k}: 0/${v.misses + v.hits}`));

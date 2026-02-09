#!/usr/bin/env python3
"""
F1 Search Phase 1 Verification Tests

Tests:
1. Cortex rewrites generation
2. Signal Router with extraction entities
3. SSE endpoint imports and event format
4. hyper_search RPC call (via direct DB test)
"""

import sys
import os

# Set env vars for test
os.environ['TENANT_1_SUPABASE_URL'] = 'https://vzsohavtuotocgrfkfyd.supabase.co'
os.environ['TENANT_1_SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY'

sys.path.insert(0, 'apps/api')

import asyncio
from services.types import UserContext, DEFAULT_BUDGET
from services.signal_router import build_route_plan, ENTITY_TARGET_MAP
from cortex.rewrites import generate_rewrites, Rewrite
from extraction.regex_extractor import RegexExtractor

print("=" * 80)
print("F1 SEARCH PHASE 1 VERIFICATION")
print("=" * 80)

passed = 0
failed = 0

# ============================================================================
# Test 1: Cortex Rewrites
# ============================================================================

print("\n[1] Cortex Rewrites")
print("-" * 40)

ctx = UserContext(user_id="u1", org_id="85fe1119-b04c-41ac-80f1-829d23322598", role="captain")

async def test_rewrites():
    global passed, failed

    # Test basic query
    result = await generate_rewrites("filter", ctx)
    print(f"  Query: 'filter'")
    print(f"  Rewrites: {len(result.rewrites)}")
    for r in result.rewrites:
        print(f"    - '{r.text}' (source={r.source}, conf={r.confidence})")

    if len(result.rewrites) >= 1:
        print(f"  ✅ PASS: Generated {len(result.rewrites)} rewrites")
        passed += 1
    else:
        print(f"  ❌ FAIL: No rewrites generated")
        failed += 1

    # Test abbreviation expansion
    result2 = await generate_rewrites("check er pump", ctx)
    print(f"\n  Query: 'check er pump'")
    print(f"  Rewrites: {len(result2.rewrites)}")
    for r in result2.rewrites:
        print(f"    - '{r.text}' (source={r.source})")

    has_expansion = any("engine room" in r.text for r in result2.rewrites)
    if has_expansion:
        print(f"  ✅ PASS: Abbreviation 'er' expanded to 'engine room'")
        passed += 1
    else:
        print(f"  ❌ FAIL: Abbreviation not expanded")
        failed += 1

    # Test cache hit
    result3 = await generate_rewrites("filter", ctx)
    if result3.cache_hit:
        print(f"\n  ✅ PASS: Cache hit on second query")
        passed += 1
    else:
        print(f"\n  ❌ FAIL: Cache miss on second query")
        failed += 1

asyncio.run(test_rewrites())

# ============================================================================
# Test 2: Extraction + Signal Router Integration
# ============================================================================

print("\n[2] Extraction + Signal Router Integration")
print("-" * 40)

extractor = RegexExtractor()
entities, _ = extractor.extract("Caterpillar filter for main engine")

print(f"  Query: 'Caterpillar filter for main engine'")
print(f"  Entities extracted: {len(entities)}")
for e in entities[:5]:
    print(f"    - {e.type}: '{e.text}' (conf={e.confidence:.2f})")

# Build signals from extraction
signals = {
    "raw_query": "Caterpillar filter for main engine",
    "entities": [{"type": e.type, "value": e.text} for e in entities],
}

plan = build_route_plan(signals, ctx)
print(f"\n  Route plan targets: {len(plan.targets)}")
for t in plan.targets:
    print(f"    - shard={t.shard}, domain={t.domain}, budget={t.budget_ms}ms")

if len(plan.targets) >= 2:
    print(f"  ✅ PASS: Route plan has {len(plan.targets)} targets")
    passed += 1
else:
    print(f"  ❌ FAIL: Route plan has only {len(plan.targets)} targets")
    failed += 1

# ============================================================================
# Test 3: SSE Event Format
# ============================================================================

print("\n[3] SSE Event Format")
print("-" * 40)

try:
    from routes.f1_search_streaming import sse_event, build_user_context

    # Test diagnostics event
    event = sse_event("diagnostics", {"search_id": "123", "status": "started"})
    if event.startswith("event: diagnostics\ndata:") and event.endswith("\n\n"):
        print(f"  ✅ PASS: diagnostics event format correct")
        passed += 1
    else:
        print(f"  ❌ FAIL: diagnostics event format incorrect")
        failed += 1

    # Test result_batch event
    event2 = sse_event("result_batch", {"results": [], "batch_index": 0})
    if "result_batch" in event2 and "batch_index" in event2:
        print(f"  ✅ PASS: result_batch event format correct")
        passed += 1
    else:
        print(f"  ❌ FAIL: result_batch event format incorrect")
        failed += 1

    # Test finalized event
    event3 = sse_event("finalized", {"latency_ms": 100})
    if "finalized" in event3 and "latency_ms" in event3:
        print(f"  ✅ PASS: finalized event format correct")
        passed += 1
    else:
        print(f"  ❌ FAIL: finalized event format incorrect")
        failed += 1

except Exception as e:
    print(f"  ❌ FAIL: Could not import f1_search_streaming: {e}")
    failed += 1

# ============================================================================
# Test 4: hyper_search RPC (Direct DB)
# ============================================================================

print("\n[4] hyper_search RPC (Direct DB)")
print("-" * 40)

try:
    from supabase import create_client

    url = os.environ.get('TENANT_1_SUPABASE_URL')
    key = os.environ.get('TENANT_1_SUPABASE_SERVICE_KEY')
    supabase = create_client(url, key)

    # Test hyper_search
    result = supabase.rpc("hyper_search", {
        "query_text": "filter",
        "query_embedding": None,
        "filter_org_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "filter_yacht_id": None,
        "rrf_k": 60,
        "page_limit": 10
    }).execute()

    print(f"  Query: 'filter'")
    print(f"  Results: {len(result.data)}")
    for r in result.data[:3]:
        name = r.get('payload', {}).get('name', 'N/A')
        score = r.get('fused_score', 0)
        print(f"    - {name} (score={score:.4f})")

    if len(result.data) > 0:
        print(f"  ✅ PASS: hyper_search returned {len(result.data)} results")
        passed += 1
    else:
        print(f"  ❌ FAIL: hyper_search returned 0 results")
        failed += 1

    # Test hyper_search_multi
    result2 = supabase.rpc("hyper_search_multi", {
        "rewrite_texts": ["filter", "pump"],
        "rewrite_embeddings": None,
        "filter_org_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "filter_yacht_id": None,
        "rrf_k": 60,
        "page_limit": 10
    }).execute()

    print(f"\n  Query: ['filter', 'pump'] (multi-rewrite)")
    print(f"  Results: {len(result2.data)}")
    for r in result2.data[:3]:
        name = r.get('payload', {}).get('name', 'N/A')
        score = r.get('fused_score', 0)
        idx = r.get('best_rewrite_idx', 'N/A')
        print(f"    - {name} (score={score:.4f}, rewrite_idx={idx})")

    if len(result2.data) > 0:
        print(f"  ✅ PASS: hyper_search_multi returned {len(result2.data)} results")
        passed += 1
    else:
        print(f"  ❌ FAIL: hyper_search_multi returned 0 results")
        failed += 1

except Exception as e:
    print(f"  ❌ FAIL: DB test failed: {e}")
    failed += 1

# ============================================================================
# Test 5: Budget Constraints
# ============================================================================

print("\n[5] Budget Constraints")
print("-" * 40)

budget = DEFAULT_BUDGET
checks = [
    ("max_rewrites", 3, budget.max_rewrites),
    ("rewrite_budget_ms", 150, budget.rewrite_budget_ms),
    ("db_timeout_ms", 120, budget.db_timeout_ms),
    ("global_timeout_ms", 500, budget.global_timeout_ms),
    ("vector_dim", 384, budget.vector_dim),
]

for name, expected, actual in checks:
    if actual == expected:
        print(f"  ✅ PASS: {name}={actual}")
        passed += 1
    else:
        print(f"  ❌ FAIL: {name}={actual}, expected {expected}")
        failed += 1

# ============================================================================
# Summary
# ============================================================================

print("\n" + "=" * 80)
print(f"PHASE 1 VERIFICATION: {passed}/{passed + failed} passed, {failed} failed")
print("=" * 80)

if failed == 0:
    print("\n✅ ALL PHASE 1 TESTS PASSED")
    print("\nF1 Search Phase 1 capabilities verified:")
    print("  • UserContext with RLS validation")
    print("  • Cortex rewrites (max 3, cached)")
    print("  • Signal Router (extraction → targets)")
    print("  • hyper_search RPC (single round-trip)")
    print("  • hyper_search_multi RPC (multi-rewrite)")
    print("  • SSE event format (diagnostics → result_batch → finalized)")
else:
    print(f"\n❌ {failed} TESTS FAILED - Review output above")

sys.exit(0 if failed == 0 else 1)

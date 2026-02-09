#!/usr/bin/env python3
"""
F1 Search Scaffolding Verification Tests

Verifies:
1. UserContext validates correctly (org_id required)
2. Signal Router returns 3-6 targets for PartNumber/AssetAlias
3. SSE endpoint imports and event format is correct
"""

import sys
sys.path.insert(0, 'apps/api')

from services.types import UserContext, SearchBudget, DEFAULT_BUDGET
from services.signal_router import build_route_plan, get_target_count, ENTITY_TARGET_MAP

print("=" * 80)
print("F1 SEARCH SCAFFOLDING VERIFICATION")
print("=" * 80)

passed = 0
failed = 0

# ============================================================================
# Test 1: UserContext Validation
# ============================================================================

print("\n[1] UserContext Validation")
print("-" * 40)

# Test valid UserContext
try:
    ctx = UserContext(
        user_id="user-123",
        org_id="org-456",
        yacht_id="yacht-789",
        role="captain"
    )
    print(f"  ✅ PASS: Valid UserContext created")
    print(f"     user_id={ctx.user_id}, org_id={ctx.org_id}, role={ctx.role}")
    passed += 1
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    failed += 1

# Test missing org_id raises ValueError
try:
    bad_ctx = UserContext(
        user_id="user-123",
        org_id="",  # Empty string should fail
        role="crew"
    )
    print(f"  ❌ FAIL: Should have raised ValueError for empty org_id")
    failed += 1
except ValueError as e:
    print(f"  ✅ PASS: Correctly rejected empty org_id: {e}")
    passed += 1
except Exception as e:
    print(f"  ❌ FAIL: Unexpected exception: {e}")
    failed += 1

# Test dict conversion
try:
    ctx = UserContext(
        user_id="user-123",
        org_id="org-456",
        role="engineer"
    )
    d = ctx.dict
    assert "user_id" in d
    assert "org_id" in d
    assert d["org_id"] == "org-456"
    print(f"  ✅ PASS: .dict property works correctly")
    passed += 1
except Exception as e:
    print(f"  ❌ FAIL: .dict failed: {e}")
    failed += 1

# Test from_jwt
try:
    claims = {
        "sub": "user-abc",
        "org_id": "org-xyz",
        "role": "chief_engineer",
        "yacht_id": "yacht-123"
    }
    ctx = UserContext.from_jwt(claims)
    assert ctx.user_id == "user-abc"
    assert ctx.org_id == "org-xyz"
    assert ctx.yacht_id == "yacht-123"
    print(f"  ✅ PASS: from_jwt() works correctly")
    passed += 1
except Exception as e:
    print(f"  ❌ FAIL: from_jwt failed: {e}")
    failed += 1

# ============================================================================
# Test 2: Signal Router - PartNumber Targets
# ============================================================================

print("\n[2] Signal Router - PartNumber Targets")
print("-" * 40)

ctx = UserContext(user_id="u1", org_id="o1", role="crew")

# Test PartNumber signals
signals = {
    "raw_query": "filter",
    "entities": [{"type": "PartNumber", "value": "FLT-123"}]
}

plan = build_route_plan(signals, ctx)
target_count = len(plan.targets)

print(f"  Targets for PartNumber: {target_count}")
for t in plan.targets:
    print(f"    - shard={t.shard}, domain={t.domain}, budget={t.budget_ms}ms")

if 3 <= target_count <= 6:
    print(f"  ✅ PASS: PartNumber returns {target_count} targets (expected 3-6)")
    passed += 1
else:
    print(f"  ❌ FAIL: PartNumber returns {target_count} targets (expected 3-6)")
    failed += 1

# ============================================================================
# Test 3: Signal Router - AssetAlias/Symptom Targets
# ============================================================================

print("\n[3] Signal Router - AssetAlias/Symptom Targets")
print("-" * 40)

signals = {
    "raw_query": "engine vibration",
    "entities": [
        {"type": "AssetAlias", "value": "main engine"},
        {"type": "Symptom", "value": "vibration"}
    ]
}

plan = build_route_plan(signals, ctx)
target_count = len(plan.targets)

print(f"  Targets for AssetAlias+Symptom: {target_count}")
for t in plan.targets:
    print(f"    - shard={t.shard}, domain={t.domain}, budget={t.budget_ms}ms")

if 3 <= target_count <= 6:
    print(f"  ✅ PASS: AssetAlias+Symptom returns {target_count} targets (expected 3-6)")
    passed += 1
else:
    print(f"  ❌ FAIL: AssetAlias+Symptom returns {target_count} targets (expected 3-6)")
    failed += 1

# ============================================================================
# Test 4: Signal Router - Default Targets (No Entities)
# ============================================================================

print("\n[4] Signal Router - Default Targets (No Entities)")
print("-" * 40)

signals = {
    "raw_query": "random search",
    "entities": []
}

plan = build_route_plan(signals, ctx)
target_count = len(plan.targets)

print(f"  Default targets: {target_count}")
for t in plan.targets:
    print(f"    - shard={t.shard}, domain={t.domain}, budget={t.budget_ms}ms")

if target_count == 3:
    print(f"  ✅ PASS: Default returns 3 targets")
    passed += 1
else:
    print(f"  ❌ FAIL: Default returns {target_count} targets (expected 3)")
    failed += 1

# ============================================================================
# Test 5: Signal Router - Route Plan Structure
# ============================================================================

print("\n[5] Signal Router - Route Plan Structure")
print("-" * 40)

signals = {"entities": [{"type": "part_number"}]}
plan = build_route_plan(signals, ctx, search_id="test-search-123")

# Check required fields
required_fields = ["search_id", "targets", "policy", "user_context"]
missing = [f for f in required_fields if not hasattr(plan, f)]

if not missing:
    print(f"  ✅ PASS: Route plan has all required fields")
    print(f"     search_id={plan.search_id}")
    print(f"     policy={plan.policy}")
    passed += 1
else:
    print(f"  ❌ FAIL: Missing fields: {missing}")
    failed += 1

# Check policy has concurrency caps
if "global_concurrency_cap" in plan.policy and "per_domain_cap" in plan.policy:
    print(f"  ✅ PASS: Policy has concurrency caps")
    passed += 1
else:
    print(f"  ❌ FAIL: Policy missing concurrency caps")
    failed += 1

# ============================================================================
# Test 6: SearchBudget Defaults
# ============================================================================

print("\n[6] SearchBudget Defaults")
print("-" * 40)

budget = DEFAULT_BUDGET
checks = [
    ("max_rewrites", 3),
    ("rewrite_budget_ms", 150),
    ("db_timeout_ms", 120),
    ("vector_dim", 384),
]

for field, expected in checks:
    actual = getattr(budget, field)
    if actual == expected:
        print(f"  ✅ PASS: {field}={actual}")
        passed += 1
    else:
        print(f"  ❌ FAIL: {field}={actual}, expected {expected}")
        failed += 1

# ============================================================================
# Test 7: SSE Event Format
# ============================================================================

print("\n[7] SSE Event Format")
print("-" * 40)

try:
    from routes.f1_search_streaming import sse_event, build_user_context

    event = sse_event("diagnostics", {"search_id": "123", "status": "started"})

    # Check format: event: <type>\ndata: <json>\n\n
    if event.startswith("event: diagnostics\ndata:") and event.endswith("\n\n"):
        print(f"  ✅ PASS: SSE event format is correct")
        print(f"     {event[:60]}...")
        passed += 1
    else:
        print(f"  ❌ FAIL: SSE event format incorrect")
        print(f"     Got: {event}")
        failed += 1

except Exception as e:
    print(f"  ❌ FAIL: Could not import f1_search_streaming: {e}")
    failed += 1

# ============================================================================
# Summary
# ============================================================================

print("\n" + "=" * 80)
print(f"VERIFICATION RESULTS: {passed}/{passed + failed} passed, {failed} failed")
print("=" * 80)

if failed == 0:
    print("\n✅ ALL VERIFICATION TESTS PASSED")
    print("\nNext steps:")
    print("1. Run SQL migration in Supabase: apps/api/migrations/001_f1_search_index.sql")
    print("2. Test hyper_search RPC with real org_id")
    print("3. Verify SSE events in browser: GET /api/f1/search/stream?q=test")
else:
    print(f"\n❌ {failed} TESTS FAILED - Review output above")

sys.exit(0 if failed == 0 else 1)

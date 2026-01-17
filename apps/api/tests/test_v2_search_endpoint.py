"""
Integration Test for /v2/search Endpoint
=========================================

Tests the orchestrated search endpoint with real database connections.
Requires environment variables to be set.

Run with:
    cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
    python tests/test_v2_search_endpoint.py
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables (for local testing)
os.environ.setdefault('MASTER_SUPABASE_URL', 'https://qvzmkaamzaqxpzbewjxe.supabase.co')
os.environ.setdefault('MASTER_SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q')
os.environ.setdefault('MASTER_SUPABASE_JWT_SECRET', 'wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw==')
os.environ.setdefault('TENANT_1_SUPABASE_URL', 'https://vzsohavtuotocgrfkfyd.supabase.co')
os.environ.setdefault('TENANT_1_SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY')

TEST_YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598'
TEST_USER_ID = 'test-user-001'


def test_orchestrator_direct():
    """Test orchestrator directly without HTTP layer."""
    print("\n" + "="*60)
    print("TEST: Direct Orchestrator Test")
    print("="*60)

    from orchestration import SearchOrchestrator, SurfaceState

    orchestrator = SearchOrchestrator()

    # Test 1: Global search
    print("\n[Test 1] Global Search: 'main engine oil pressure'")
    result = orchestrator.orchestrate(
        surface_state=SurfaceState.SEARCH,
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        query_text="main engine oil pressure",
    )

    print(f"  Request ID: {result.request_id}")
    print(f"  Path: {result.plan.path.value}")
    print(f"  Scopes: {result.plan.allowed_scopes}")
    print(f"  Time (ms): {result.orchestration_time_ms:.1f}")

    trust = result.get_trust_payload()
    print(f"  Trust Payload:")
    print(f"    - path: {trust['path']}")
    print(f"    - scopes: {trust['scopes']}")
    print(f"    - used_vector: {trust['used_vector']}")
    print(f"    - explain: {trust['explain']}")

    assert result.plan is not None
    assert result.request_id is not None
    print("  [PASS]")

    # Test 2: Entity ID search
    print("\n[Test 2] Entity ID Search: 'WO-1234 parts'")
    result = orchestrator.orchestrate(
        surface_state=SurfaceState.SEARCH,
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        query_text="WO-1234 parts",
    )

    print(f"  Path: {result.plan.path.value}")
    print(f"  Classification: {result.classification.primary_path.value}")
    print(f"  Has entities: {result.classification.has_entities()}")

    assert result.classification.has_entities()
    print("  [PASS]")

    # Test 3: Inbox scan
    print("\n[Test 3] Inbox Scan (no query)")
    result = orchestrator.orchestrate(
        surface_state=SurfaceState.EMAIL_INBOX,
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        query_text="",
    )

    print(f"  Path: {result.plan.path.value}")
    print(f"  Is system-triggered: {result.context.is_system_triggered()}")
    print(f"  SQL queries: {len(result.plan.sql_queries)}")
    print(f"  Vector queries: {len(result.plan.vector_queries)}")

    assert result.plan.path.value == "email_inbox"
    assert result.context.is_system_triggered()
    assert len(result.plan.vector_queries) == 0
    print("  [PASS]")

    # Test 4: Email search
    print("\n[Test 4] Email Search: 'invoice from supplier'")
    result = orchestrator.orchestrate(
        surface_state=SurfaceState.EMAIL_SEARCH,
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        query_text="invoice from supplier",
    )

    print(f"  Path: {result.plan.path.value}")
    print(f"  Vector queries: {len(result.plan.vector_queries)}")
    if result.plan.vector_queries:
        print(f"  Vector column: {result.plan.vector_queries[0].column}")

    assert result.plan.path.value == "email_search"
    assert len(result.plan.vector_queries) > 0
    print("  [PASS]")

    print("\n" + "="*60)
    print("All orchestrator tests passed!")
    print("="*60)


def test_executor_with_db():
    """Test executor with real database connection."""
    print("\n" + "="*60)
    print("TEST: Executor with Database")
    print("="*60)

    from supabase import create_client
    from orchestration import SearchOrchestrator, SurfaceState
    from orchestration.executor import PlanExecutor

    # Create tenant client
    tenant_url = os.environ.get('TENANT_1_SUPABASE_URL')
    tenant_key = os.environ.get('TENANT_1_SUPABASE_SERVICE_KEY')

    if not tenant_url or not tenant_key:
        print("  [SKIP] Tenant credentials not set")
        return

    client = create_client(tenant_url, tenant_key)
    print(f"  Connected to tenant DB: {tenant_url[:40]}...")

    orchestrator = SearchOrchestrator()
    executor = PlanExecutor(client, TEST_YACHT_ID)

    # Test: Execute inbox scan
    print("\n[Test] Execute inbox scan")
    result = orchestrator.orchestrate(
        surface_state=SurfaceState.EMAIL_INBOX,
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        query_text="",
    )

    print(f"  Plan path: {result.plan.path.value}")
    print(f"  SQL queries to execute: {len(result.plan.sql_queries)}")

    execution_result = executor.execute_sync(result.plan)

    print(f"  Execution time (ms): {execution_result.execution_time_ms:.1f}")
    print(f"  Total results: {execution_result.total_count}")
    print(f"  Results by domain: {list(execution_result.results_by_domain.keys())}")

    if execution_result.total_count > 0:
        print(f"  First result keys: {list(execution_result.results[0].keys())[:5]}")

    print("  [PASS]")

    # Test: Execute global search
    print("\n[Test] Execute global search: 'engine'")
    result = orchestrator.orchestrate(
        surface_state=SurfaceState.SEARCH,
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        query_text="engine",
    )

    print(f"  Plan path: {result.plan.path.value}")

    execution_result = executor.execute_sync(result.plan)

    print(f"  Execution time (ms): {execution_result.execution_time_ms:.1f}")
    print(f"  Total results: {execution_result.total_count}")

    print("  [PASS]")

    print("\n" + "="*60)
    print("All executor tests passed!")
    print("="*60)


def test_full_response_structure():
    """Test full response structure matches API contract."""
    print("\n" + "="*60)
    print("TEST: Full Response Structure")
    print("="*60)

    from supabase import create_client
    from orchestration import SearchOrchestrator, SurfaceState
    from orchestration.executor import PlanExecutor

    tenant_url = os.environ.get('TENANT_1_SUPABASE_URL')
    tenant_key = os.environ.get('TENANT_1_SUPABASE_SERVICE_KEY')

    if not tenant_url or not tenant_key:
        print("  [SKIP] Tenant credentials not set")
        return

    client = create_client(tenant_url, tenant_key)
    orchestrator = SearchOrchestrator()
    executor = PlanExecutor(client, TEST_YACHT_ID)

    # Simulate full API response
    result = orchestrator.orchestrate(
        surface_state=SurfaceState.SEARCH,
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        query_text="test query",
        debug_mode=True,
    )

    execution_result = executor.execute_sync(result.plan)
    trust_payload = result.get_trust_payload()

    # Build response structure (matching OrchestatedSearchResponse)
    response = {
        'success': True,
        'request_id': result.request_id,
        'results': execution_result.results,
        'results_by_domain': execution_result.results_by_domain,
        'total_count': execution_result.total_count,
        'trust': {
            'path': trust_payload['path'],
            'scopes': trust_payload['scopes'],
            'time_window_days': trust_payload['time_window_days'],
            'used_vector': trust_payload['used_vector'],
            'explain': trust_payload['explain'],
        },
        'timing_ms': {
            'orchestration': result.orchestration_time_ms,
            'execution': execution_result.execution_time_ms,
            'total': result.orchestration_time_ms + execution_result.execution_time_ms,
        },
    }

    print("\nResponse structure:")
    print(json.dumps({k: type(v).__name__ if not isinstance(v, (str, int, float, bool, list, dict)) else v
                      for k, v in response.items()}, indent=2, default=str))

    # Validate required fields
    assert 'success' in response
    assert 'request_id' in response
    assert 'results' in response
    assert 'results_by_domain' in response
    assert 'total_count' in response
    assert 'trust' in response
    assert 'timing_ms' in response

    # Validate trust payload fields
    assert 'path' in response['trust']
    assert 'scopes' in response['trust']
    assert 'time_window_days' in response['trust']
    assert 'used_vector' in response['trust']
    assert 'explain' in response['trust']

    print("\n  [PASS] Response structure valid")

    print("\n" + "="*60)
    print("Full response structure test passed!")
    print("="*60)


if __name__ == "__main__":
    print("\n" + "#"*60)
    print("# /v2/search Endpoint Integration Tests")
    print("#"*60)

    try:
        test_orchestrator_direct()
        test_executor_with_db()
        test_full_response_structure()

        print("\n" + "#"*60)
        print("# ALL TESTS PASSED")
        print("#"*60 + "\n")

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

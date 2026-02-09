#!/usr/bin/env python3
"""
Unit test to prove parts query is now included in hybrid retrieval.
Tests the fix to PrepareModule._prepare_hybrid()
"""
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

from orchestration.prepare_module import PrepareModule
from orchestration.surface_state import SurfaceState, SurfaceContext
from orchestration.term_classifier import TermClassification, TermType, ClassifiedTerm
from orchestration.retrieval_plan import RetrievalPath

def test_parts_in_hybrid():
    """Test that parts queries are included in hybrid retrieval."""
    
    prepare = PrepareModule()
    
    # Create a context for "parts low in stock" query
    context = SurfaceContext(
        surface_state=SurfaceState.SEARCH,
        yacht_id="test-yacht-id",
        user_id="test-user-id",
        query_text="parts low in stock",
    )
    
    # Simulate classification that detected 'parts' scope
    # This mimics what TermClassifier.classify() would return
    classification = TermClassification(
        terms=[
            ClassifiedTerm(text="parts", term_type=TermType.DOMAIN),
            ClassifiedTerm(text="low", term_type=TermType.FREE_TEXT),
            ClassifiedTerm(text="stock", term_type=TermType.FREE_TEXT),
        ],
        primary_path=RetrievalPath.HYBRID,
        allowed_scopes=['parts'],
        classification_reason="domain keyword 'parts' detected",
    )
    
    # Call _prepare_hybrid directly
    plan = prepare._prepare_hybrid(context, classification, [])
    
    # Verify parts query is included
    parts_queries = [q for q in plan.sql_queries if q.domain == 'parts']
    
    print("=" * 80)
    print("PARTS QUERY FIX - UNIT TEST")
    print("=" * 80)
    print(f"Query: {context.query_text}")
    print(f"Detected scopes: {classification.allowed_scopes}")
    print(f"Primary path: {plan.path.value}")
    print()
    print(f"Total SQL queries: {len(plan.sql_queries)}")
    print(f"Domains in queries: {[q.domain for q in plan.sql_queries]}")
    print()
    
    if parts_queries:
        print("✅ PASS: Parts query found in hybrid retrieval")
        print()
        print("Parts Query SQL:")
        print("-" * 80)
        print(parts_queries[0].sql.strip())
        print()
        print(f"Params: {parts_queries[0].params}")
        return 0
    else:
        print("❌ FAIL: Parts query NOT found in hybrid retrieval")
        print("This means the fix was not applied correctly.")
        return 1

if __name__ == "__main__":
    exit(test_parts_in_hybrid())

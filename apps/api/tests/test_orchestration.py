"""
Unit Tests for Search Orchestration Layer
==========================================

Tests classification rules, plan building, and ranking.
All tests are deterministic - same input always produces same output.
"""

import pytest
from datetime import datetime

# Import orchestration modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.surface_state import SurfaceState, SurfaceContext, get_default_scopes
from orchestration.retrieval_plan import RetrievalPlan, RetrievalPath, TimeWindow
from orchestration.term_classifier import TermClassifier, TermType, TermClassification
from orchestration.ranking_recipes import (
    RANKING_RECIPES,
    get_ranking_recipe,
    validate_recipe,
    calculate_recency_score,
)
from orchestration.prepare_module import PrepareModule
from orchestration.email_retrieval import EmailRetrieval
from orchestration.search_orchestrator import SearchOrchestrator


# =============================================================================
# Surface State Tests
# =============================================================================

class TestSurfaceState:
    """Tests for surface state enums and context."""

    def test_all_states_defined(self):
        """Verify all expected states exist."""
        assert SurfaceState.SEARCH.value == "search"
        assert SurfaceState.EMAIL_INBOX.value == "email_inbox"
        assert SurfaceState.EMAIL_OPEN.value == "email_open"
        assert SurfaceState.EMAIL_SEARCH.value == "email_search"
        assert SurfaceState.ENTITY_OPEN.value == "entity_open"
        assert SurfaceState.DOCUMENT_OPEN.value == "doc_open"

    def test_context_is_email_surface(self):
        """Test email surface detection."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.EMAIL_INBOX,
            yacht_id="test-yacht",
            user_id="test-user",
        )
        assert ctx.is_email_surface() is True

        ctx2 = SurfaceContext(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
        )
        assert ctx2.is_email_surface() is False

    def test_context_system_triggered(self):
        """Test system-triggered detection (inbox with no query)."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.EMAIL_INBOX,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="",
        )
        assert ctx.is_system_triggered() is True

        ctx2 = SurfaceContext(
            surface_state=SurfaceState.EMAIL_INBOX,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="search term",
        )
        assert ctx2.is_system_triggered() is False

    def test_default_scopes(self):
        """Test default scope sets per surface."""
        search_scopes = get_default_scopes(SurfaceState.SEARCH)
        assert "work_orders" in search_scopes
        assert "equipment" in search_scopes

        email_scopes = get_default_scopes(SurfaceState.EMAIL_INBOX)
        assert email_scopes == ["emails"]


# =============================================================================
# Term Classifier Tests
# =============================================================================

class TestTermClassifier:
    """Tests for term classification rules."""

    @pytest.fixture
    def classifier(self):
        return TermClassifier()

    def test_entity_id_extraction_wo(self, classifier):
        """Test WO-#### pattern extraction."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="show me WO-1234",
        )
        result = classifier.classify(ctx)

        entities = result.get_entities()
        assert len(entities) >= 1
        assert any("wo-1234" in e.text.lower() for e in entities)

    def test_entity_id_extraction_po(self, classifier):
        """Test PO-#### pattern extraction."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="find PO-5678",
        )
        result = classifier.classify(ctx)

        entities = result.get_entities()
        assert len(entities) >= 1
        assert any("po-5678" in e.text.lower() for e in entities)

    def test_domain_extraction_emails(self, classifier):
        """Test email domain hint extraction."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="search emails from supplier",
        )
        result = classifier.classify(ctx)

        assert "emails" in result.allowed_scopes

    def test_domain_extraction_work_orders(self, classifier):
        """Test work order domain hint extraction."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="show work orders for engine",
        )
        result = classifier.classify(ctx)

        assert "work_orders" in result.allowed_scopes

    def test_time_extraction(self, classifier):
        """Test time window extraction."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="emails from last week",
        )
        result = classifier.classify(ctx)

        assert result.time_window_days == 14  # "last week" = 14 days

    def test_system_triggered_inbox(self, classifier):
        """Test inbox scan classification (no query)."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.EMAIL_INBOX,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="",
        )
        result = classifier.classify(ctx)

        assert result.primary_path == RetrievalPath.EMAIL_INBOX
        assert result.allowed_scopes == ["emails"]

    def test_resolved_entity_sql_path(self, classifier):
        """Test that resolved entities trigger SQL path."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="show WO-1234",
        )
        result = classifier.classify(ctx)

        # WO-1234 is a pattern match, should go SQL
        assert result.primary_path == RetrievalPath.SQL_ONLY

    def test_free_text_hybrid_path(self, classifier):
        """Test that free text triggers hybrid path."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="main engine overheating troubleshooting",
        )
        result = classifier.classify(ctx)

        # No entity IDs, mostly free text
        assert result.primary_path == RetrievalPath.HYBRID


# =============================================================================
# Ranking Recipe Tests
# =============================================================================

class TestRankingRecipes:
    """Tests for ranking recipes."""

    def test_all_recipes_sum_to_one(self):
        """Verify all recipe weights sum to 1.0."""
        for name, recipe in RANKING_RECIPES.items():
            assert validate_recipe(recipe), f"Recipe '{name}' does not sum to 1.0"

    def test_global_search_recipe(self):
        """Test global search recipe exists and is valid."""
        recipe = get_ranking_recipe("global_search")
        assert "similarity" in recipe
        assert "recency" in recipe
        assert validate_recipe(recipe)

    def test_email_search_recipe(self):
        """Test email search recipe exists and is valid."""
        recipe = get_ranking_recipe("email_search")
        assert "thread_cohesion" in recipe
        assert validate_recipe(recipe)

    def test_unknown_recipe_fallback(self):
        """Test unknown recipe falls back to global_search."""
        recipe = get_ranking_recipe("nonexistent_recipe")
        assert recipe == RANKING_RECIPES["global_search"]

    def test_recency_score_calculation(self):
        """Test recency score decay."""
        # Today = 1.0
        assert calculate_recency_score(0) == 1.0

        # 45 days ago = 0.5 (halfway through 90 day window)
        assert calculate_recency_score(45, max_days=90) == 0.5

        # 90 days or older = 0.0
        assert calculate_recency_score(90, max_days=90) == 0.0
        assert calculate_recency_score(100, max_days=90) == 0.0


# =============================================================================
# Prepare Module Tests
# =============================================================================

class TestPrepareModule:
    """Tests for the prepare module."""

    @pytest.fixture
    def prepare(self):
        return PrepareModule()

    def test_inbox_scan_plan(self, prepare):
        """Test inbox scan produces correct plan."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.EMAIL_INBOX,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="",
        )
        plan = prepare.prepare(ctx)

        assert plan.path == RetrievalPath.EMAIL_INBOX
        assert plan.allowed_scopes == ["emails"]
        assert len(plan.vector_queries) == 0  # No vectors for inbox

    def test_email_search_plan(self, prepare):
        """Test email search produces hybrid plan."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.EMAIL_SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="invoice from supplier",
        )
        plan = prepare.prepare(ctx)

        assert plan.path == RetrievalPath.EMAIL_SEARCH
        assert len(plan.vector_queries) > 0  # Has vector search

    def test_must_filters_applied(self, prepare):
        """Test yacht_id is always in must_filters."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht-123",
            user_id="test-user-456",
            query_text="anything",
        )
        plan = prepare.prepare(ctx)

        assert plan.must_filters.get('yacht_id') == "test-yacht-123"
        assert plan.must_filters.get('user_id') == "test-user-456"

    def test_plan_has_explain(self, prepare):
        """Test plan includes explanation."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="find WO-1234",
        )
        plan = prepare.prepare(ctx)

        assert plan.explain is not None
        assert len(plan.explain) > 0


# =============================================================================
# Email Retrieval Tests
# =============================================================================

class TestEmailRetrieval:
    """Tests for email-specific retrieval logic."""

    @pytest.fixture
    def email_retrieval(self):
        return EmailRetrieval()

    def test_inbox_scan_sql_only(self, email_retrieval):
        """Test inbox scan uses SQL only."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.EMAIL_INBOX,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="",
        )
        plan = email_retrieval.prepare(ctx)

        assert plan.path == RetrievalPath.EMAIL_INBOX
        assert len(plan.sql_queries) > 0
        assert len(plan.vector_queries) == 0

    def test_email_search_has_vector(self, email_retrieval):
        """Test email search includes vector query."""
        ctx = SurfaceContext(
            surface_state=SurfaceState.EMAIL_SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="parts order",
        )
        plan = email_retrieval.prepare(ctx)

        assert plan.path == RetrievalPath.EMAIL_SEARCH
        assert len(plan.vector_queries) > 0
        assert plan.vector_queries[0].column == "meta_embedding"


# =============================================================================
# Search Orchestrator Integration Tests
# =============================================================================

class TestSearchOrchestrator:
    """Integration tests for the full orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        return SearchOrchestrator()

    def test_orchestrate_global_search(self, orchestrator):
        """Test full orchestration for global search."""
        result = orchestrator.orchestrate(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="main engine oil pressure",
        )

        assert result.plan is not None
        assert result.classification is not None
        assert result.request_id is not None
        assert result.orchestration_time_ms > 0

    def test_orchestrate_inbox_scan(self, orchestrator):
        """Test full orchestration for inbox scan."""
        result = orchestrator.orchestrate(
            surface_state=SurfaceState.EMAIL_INBOX,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="",
        )

        assert result.plan.path == RetrievalPath.EMAIL_INBOX
        assert result.context.is_system_triggered()

    def test_trust_payload_structure(self, orchestrator):
        """Test trust payload has required fields."""
        result = orchestrator.orchestrate(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="test query",
        )

        trust = result.get_trust_payload()

        assert 'path' in trust
        assert 'scopes' in trust
        assert 'explain' in trust
        assert 'used_vector' in trust

    def test_determinism(self, orchestrator):
        """Test same input produces same output."""
        result1 = orchestrator.orchestrate(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="WO-1234 parts",
        )

        result2 = orchestrator.orchestrate(
            surface_state=SurfaceState.SEARCH,
            yacht_id="test-yacht",
            user_id="test-user",
            query_text="WO-1234 parts",
        )

        # Same path
        assert result1.plan.path == result2.plan.path

        # Same scopes
        assert result1.plan.allowed_scopes == result2.plan.allowed_scopes

        # Same classification
        assert result1.classification.primary_path == result2.classification.primary_path


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

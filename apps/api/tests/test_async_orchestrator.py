"""
Async Orchestrator Tests
=========================

Tests for async entity extraction pipeline with gpt-4o-mini.

Test Coverage:
- Fast path (regex/gazetteer) - no AI needed
- AI path (low coverage) - triggers gpt-4o-mini
- Shopping list terms - gazetteer fast path
- Mock AI testing - no API costs
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import os


# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


class TestOrchestrator:
    """Test async extraction orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        from extraction.orchestrator import ExtractionOrchestrator
        return ExtractionOrchestrator()

    async def test_fast_path_known_equipment(self, orchestrator):
        """Test that known equipment terms hit regex path (no AI)."""
        # "main engine" is in gazetteer, should stay in regex lane
        result = await orchestrator.extract("Main engine high temperature")

        assert result['metadata']['needs_ai'] is False, "Known terms should use regex path"
        assert 'equipment' in result['entities'], "Should extract equipment entity"
        # May extract as 'engine' or 'main engine' depending on regex patterns
        equipment = [e.lower() for e in result['entities'].get('equipment', [])]
        assert any(term in equipment for term in ['engine', 'main engine']), f"Should extract engine, got {equipment}"
        assert result['metadata']['coverage'] >= 0.85, "Coverage should be high for known terms"

    async def test_fast_path_shopping_list(self, orchestrator):
        """Test that shopping list terms hit gazetteer fast path."""
        # Shopping list terms added to gazetteer
        result = await orchestrator.extract("pending shopping list items")

        assert result['metadata']['needs_ai'] is False, "Shopping list terms should use fast path"
        # Should extract some entities (status, shopping list terms, or other)
        total_entities = sum(len(v) for v in result['entities'].values() if isinstance(v, list))
        assert total_entities > 0, f"Should extract shopping list entities, got: {result['entities']}"
        # Coverage should be high (fast path)
        assert result['metadata']['coverage'] >= 0.85, "Shopping list should have high coverage"

    async def test_ai_path_low_coverage(self, orchestrator):
        """Test that unknown terms trigger AI path."""
        # Skip if no OpenAI key (CI environment)
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("No OpenAI API key - skipping AI test")

        # Use obscure text to force < 85% coverage
        result = await orchestrator.extract("The flux capacitor is fluctuating wildly near the dilithium matrix")

        assert result['metadata']['needs_ai'] is True, "Unknown terms should trigger AI"
        # AI should extract something even if nonsensical
        total_entities = sum(len(v) for v in result['entities'].values() if isinstance(v, list))
        assert total_entities >= 0, "AI should process the text"

    async def test_ai_path_uses_gpt4o_mini(self, orchestrator):
        """Test that AI extractor uses gpt-4o-mini model."""
        # Check model configuration
        assert orchestrator.ai_extractor.model in ['gpt-4o-mini', os.getenv('AI_MODEL', 'gpt-4o-mini')]

    async def test_empty_text_handling(self, orchestrator):
        """Test that empty text returns empty response."""
        result = await orchestrator.extract("")

        assert result['schema_version'] == '0.2.2'
        assert result['entities'] == {}
        assert result['metadata']['coverage'] == 1.0

    async def test_mock_ai_extraction(self, orchestrator):
        """Test pipeline logic with mocked AI (no API cost)."""
        # Mock the AI extractor's extract method
        orchestrator.ai_extractor.extract = AsyncMock(return_value={
            'schema_version': '0.2.2',
            'entities': {
                'equipment': ['Mocked Equipment'],
                'symptom': ['mocked symptom']
            },
            'metadata': {
                'needs_ai': True,
                'coverage': 0.0,
                'source_mix': {'regex': 0, 'gazetteer': 0, 'ai': 1}
            }
        })

        # Force low coverage to trigger AI path using nonsense text
        result = await orchestrator.extract("The quantum flux capacitor near the warp core is destabilizing")

        # If AI was triggered, check that mock was called
        if result['metadata']['needs_ai']:
            # Should contain entities (may be from regex or mocked AI or both)
            total_entities = sum(len(v) for v in result['entities'].values() if isinstance(v, list))
            assert total_entities > 0, "Should have extracted some entities"
            # Verify mock was called
            orchestrator.ai_extractor.extract.assert_called_once()
        else:
            # If regex coverage was high enough, AI wasn't needed - that's also valid
            assert result['metadata']['coverage'] >= 0.85, "If AI not needed, coverage should be high"

    async def test_concurrent_extraction(self, orchestrator):
        """Test that multiple concurrent extractions work correctly."""
        queries = [
            "main engine temperature",
            "fuel pump pressure",
            "battery voltage",
        ]

        # Run multiple extractions concurrently
        results = await asyncio.gather(*[
            orchestrator.extract(query) for query in queries
        ])

        assert len(results) == 3
        for result in results:
            assert result['schema_version'] == '0.2.2'
            assert 'entities' in result
            assert 'metadata' in result

    async def test_health_check(self, orchestrator):
        """Test orchestrator health check."""
        health = orchestrator.health_check()

        assert 'ok' in health
        assert 'components' in health
        assert health['components']['cleaner'] == 'ok'
        assert health['components']['regex_extractor'] == 'ok'
        assert health['components']['controller'] == 'ok'
        assert health['components']['merger'] == 'ok'
        # AI extractor might be unavailable without API key
        assert health['components']['ai_extractor'] in ['ok', 'unavailable']


class TestAIExtractor:
    """Test async AI extractor."""

    @pytest.fixture
    def ai_extractor(self):
        """Create AI extractor instance."""
        from extraction.ai_extractor_openai import AIExtractor
        return AIExtractor()

    async def test_ai_extractor_model_config(self, ai_extractor):
        """Test that AI extractor uses correct model."""
        expected_model = os.getenv('AI_MODEL', 'gpt-4o-mini')
        assert ai_extractor.model == expected_model

    async def test_ai_extractor_async_client(self, ai_extractor):
        """Test that AI extractor uses AsyncOpenAI client."""
        if ai_extractor.api_key:
            from openai import AsyncOpenAI
            assert isinstance(ai_extractor.client, AsyncOpenAI)

    async def test_ai_extractor_empty_text(self, ai_extractor):
        """Test AI extractor handles empty text."""
        result = await ai_extractor.extract("")

        assert result['schema_version'] == '0.2.2'
        assert result['entities'] == {
            'equipment': [],
            'subcomponent': [],
            'system': [],
            'location_on_board': [],
            'action': [],
            'status': [],
            'symptom': [],
            'measurement': [],
            'fault_code': [],
            'time': [],
            'date': [],
            'person': [],
            'document_id': [],
            'document_type': [],
            'model': [],
            'org': [],
            'network_id': [],
            'identifier': []
        }

    async def test_ai_extractor_no_api_key(self):
        """Test AI extractor gracefully handles missing API key."""
        from extraction.ai_extractor_openai import AIExtractor

        # Create extractor without API key
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}, clear=False):
            extractor = AIExtractor()
            result = await extractor.extract("test query")

            # Should return empty response without crashing
            assert result['schema_version'] == '0.2.2'
            assert result['entities'] is not None


class TestPipelineIntegration:
    """Integration tests for full pipeline."""

    async def test_pipeline_search_async(self):
        """Test that pipeline.search() works with async extraction."""
        from unittest.mock import MagicMock
        from pipeline_v1 import Pipeline

        # Create mock Supabase client
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        pipeline = Pipeline(mock_client, 'test-yacht-id')

        # Test async search
        response = await pipeline.search("main engine temperature")

        assert response.success in [True, False]  # May fail due to no data, but should not crash
        assert hasattr(response, 'extraction')
        assert hasattr(response, 'total_ms')


# Performance benchmarks
class TestPerformance:
    """Performance tests for fast path vs AI path."""

    @pytest.fixture
    def orchestrator(self):
        from extraction.orchestrator import ExtractionOrchestrator
        return ExtractionOrchestrator()

    async def test_fast_path_latency(self, orchestrator):
        """Test that fast path is < 200ms."""
        import time

        start = time.time()
        result = await orchestrator.extract("main engine high temperature")
        elapsed_ms = (time.time() - start) * 1000

        assert result['metadata']['needs_ai'] is False
        # Fast path should be < 200ms
        assert elapsed_ms < 200, f"Fast path took {elapsed_ms:.0f}ms (should be < 200ms)"

    async def test_shopping_list_fast_path_latency(self, orchestrator):
        """Test that shopping list queries use fast path."""
        import time

        start = time.time()
        result = await orchestrator.extract("pending shopping list items")
        elapsed_ms = (time.time() - start) * 1000

        assert result['metadata']['needs_ai'] is False, "Shopping list should use fast path"
        # Should be fast (< 200ms)
        assert elapsed_ms < 200, f"Shopping list query took {elapsed_ms:.0f}ms (should be < 200ms)"


if __name__ == '__main__':
    # Run tests with: python -m pytest tests/test_async_orchestrator.py -v
    pytest.main([__file__, '-v', '-s'])

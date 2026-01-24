"""
Email RAG Worker Unit Tests

Tests the worker components with mocked dependencies:
1. Embedder - mocked OpenAI API
2. Entity Extractor - regex pattern tests
3. Worker - mocked Supabase

Run with: pytest tests/test_email_rag_worker.py -v
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone
import uuid


# ============================================================================
# PART 1: EMBEDDER TESTS (Mock OpenAI)
# ============================================================================

class TestEmbedder:
    """Test email_rag/embedder.py with mocked OpenAI."""

    def test_generate_embedding_sync_success(self):
        """Test synchronous embedding generation with mocked OpenAI."""
        with patch('email_rag.embedder.get_openai_client') as mock_get_client:
            # Setup mock
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_response.usage.total_tokens = 50
            mock_client.embeddings.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            # Import after patching
            from email_rag.embedder import generate_embedding_sync

            result = generate_embedding_sync("Test text for embedding")

            assert result is not None
            assert len(result) == 1536
            mock_client.embeddings.create.assert_called_once()
            call_args = mock_client.embeddings.create.call_args
            assert call_args.kwargs['model'] == 'text-embedding-3-small'

    def test_generate_embedding_sync_truncates_long_text(self):
        """Test that text is truncated to 8000 chars."""
        with patch('email_rag.embedder.get_openai_client') as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_response.usage.total_tokens = 50
            mock_client.embeddings.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            from email_rag.embedder import generate_embedding_sync

            # Send very long text
            long_text = "x" * 10000
            generate_embedding_sync(long_text)

            # Verify truncation
            call_args = mock_client.embeddings.create.call_args
            assert len(call_args.kwargs['input']) == 8000

    def test_generate_embedding_sync_handles_error(self):
        """Test that errors are handled gracefully."""
        with patch('email_rag.embedder.get_openai_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.embeddings.create.side_effect = Exception("API Error")
            mock_get_client.return_value = mock_client

            from email_rag.embedder import generate_embedding_sync

            result = generate_embedding_sync("Test text")
            assert result is None

    def test_estimate_cost(self):
        """Test cost estimation function."""
        from email_rag.embedder import estimate_cost

        result = estimate_cost(1000, avg_preview_length=200)

        assert 'num_emails' in result
        assert result['num_emails'] == 1000
        assert 'embedding_cost' in result
        assert result['embedding_cost'] > 0
        assert result['cost_per_email'] > 0

    def test_estimate_cost_zero_emails(self):
        """Test cost estimation with zero emails."""
        from email_rag.embedder import estimate_cost

        result = estimate_cost(0)
        assert result['cost_per_email'] == 0

    @pytest.mark.asyncio
    async def test_generate_email_embedding_updates_db(self):
        """Test async embedding generation updates database."""
        with patch('email_rag.embedder.get_openai_client') as mock_get_client:
            # Setup mocks
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_response.usage.total_tokens = 50
            mock_client.embeddings.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            mock_supabase = MagicMock()
            mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = None

            from email_rag.embedder import generate_email_embedding

            result = await generate_email_embedding(
                message_id='test-msg-id',
                preview_text='Test email content',
                yacht_id='test-yacht-id',
                supabase=mock_supabase
            )

            assert result is not None
            assert len(result) == 1536
            mock_supabase.table.assert_called_with('email_messages')


# ============================================================================
# PART 2: ENTITY EXTRACTOR TESTS (Regex patterns)
# ============================================================================

class TestEntityExtractor:
    """Test email_rag/entity_extractor.py regex patterns."""

    def test_extract_work_order_references_wo_format(self):
        """Test WO-1234 format extraction."""
        from email_rag.entity_extractor import extract_work_order_references

        text = "Please check WO-1234 and WO-5678 for the parts list."
        refs = extract_work_order_references(text)

        assert '1234' in refs
        assert '5678' in refs

    def test_extract_work_order_references_hash_format(self):
        """Test #1234 format extraction."""
        from email_rag.entity_extractor import extract_work_order_references

        text = "Task #9999 needs attention."
        refs = extract_work_order_references(text)

        assert '9999' in refs

    def test_extract_work_order_references_word_format(self):
        """Test 'work order 1234' format extraction."""
        from email_rag.entity_extractor import extract_work_order_references

        text = "Work order 4567 has been completed."
        refs = extract_work_order_references(text)

        assert '4567' in refs

    def test_extract_work_order_references_mixed(self):
        """Test mixed formats in same text."""
        from email_rag.entity_extractor import extract_work_order_references

        text = "WO-111, #222, task 333, work order 444 all need review"
        refs = extract_work_order_references(text)

        assert '111' in refs
        assert '222' in refs
        assert '333' in refs
        assert '444' in refs

    def test_extract_work_order_references_deduplicates(self):
        """Test that duplicate references are removed."""
        from email_rag.entity_extractor import extract_work_order_references

        text = "WO-1234 is mentioned again: WO-1234"
        refs = extract_work_order_references(text)

        assert len([r for r in refs if r == '1234']) == 1

    def test_extract_work_order_references_case_insensitive(self):
        """Test case insensitivity."""
        from email_rag.entity_extractor import extract_work_order_references

        text = "wo-1234 WO-5678 Wo-9999"
        refs = extract_work_order_references(text)

        assert '1234' in refs
        assert '5678' in refs
        assert '9999' in refs

    def test_extract_equipment_mentions_keywords(self):
        """Test equipment keyword detection."""
        from email_rag.entity_extractor import extract_equipment_mentions

        text = "The main engine needs servicing. Check the generator too."
        mentions = extract_equipment_mentions(text)

        assert 'engine' in mentions
        assert 'generator' in mentions

    def test_extract_equipment_mentions_multiple(self):
        """Test multiple equipment types."""
        from email_rag.entity_extractor import extract_equipment_mentions

        text = "Pump, compressor, and HVAC all need inspection."
        mentions = extract_equipment_mentions(text)

        assert 'pump' in mentions
        assert 'compressor' in mentions
        assert 'hvac' in mentions

    def test_extract_equipment_mentions_case_insensitive(self):
        """Test case insensitivity for equipment."""
        from email_rag.entity_extractor import extract_equipment_mentions

        text = "The ENGINE and PUMP are working fine."
        mentions = extract_equipment_mentions(text)

        assert 'engine' in mentions
        assert 'pump' in mentions

    def test_extract_equipment_mentions_empty_text(self):
        """Test with no equipment mentions."""
        from email_rag.entity_extractor import extract_equipment_mentions

        text = "Meeting scheduled for tomorrow."
        mentions = extract_equipment_mentions(text)

        assert len(mentions) == 0


# ============================================================================
# PART 3: WORKER TESTS (Mock Supabase)
# ============================================================================

class TestEmailRAGWorker:
    """Test worker.py with mocked dependencies."""

    def test_worker_initialization(self):
        """Test worker initializes with correct defaults."""
        from worker import EmailRAGWorker

        worker = EmailRAGWorker()

        assert worker.poll_interval == 60
        assert worker.batch_size == 10
        assert worker.yacht_filter is None
        assert worker.running is False
        assert worker.stats['jobs_processed'] == 0

    def test_worker_initialization_with_params(self):
        """Test worker accepts custom parameters."""
        from worker import EmailRAGWorker

        worker = EmailRAGWorker(
            poll_interval=30,
            batch_size=5,
            yacht_filter='test-yacht-123'
        )

        assert worker.poll_interval == 30
        assert worker.batch_size == 5
        assert worker.yacht_filter == 'test-yacht-123'

    def test_worker_stats_tracking(self):
        """Test worker tracks statistics correctly."""
        from worker import EmailRAGWorker

        worker = EmailRAGWorker()
        worker.stats['jobs_processed'] = 10
        worker.stats['jobs_succeeded'] = 8
        worker.stats['jobs_failed'] = 1
        worker.stats['jobs_skipped'] = 1

        stats = worker.get_stats()

        assert stats['jobs_processed'] == 10
        assert stats['jobs_succeeded'] == 8
        assert stats['jobs_failed'] == 1
        assert stats['jobs_skipped'] == 1

    @pytest.mark.asyncio
    async def test_process_batch_no_jobs(self):
        """Test process_batch returns 0 when no jobs."""
        from worker import EmailRAGWorker

        worker = EmailRAGWorker()

        # Mock supabase to return empty data
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value = mock_query

        worker.supabase = mock_supabase

        result = await worker.process_batch()

        assert result == 0

    @pytest.mark.asyncio
    async def test_process_batch_with_yacht_filter(self):
        """Test process_batch applies yacht filter."""
        from worker import EmailRAGWorker

        worker = EmailRAGWorker(yacht_filter='test-yacht-123')

        # Setup mock chain
        mock_supabase = MagicMock()
        mock_select = MagicMock()
        mock_eq_status = MagicMock()
        mock_eq_yacht = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()

        mock_supabase.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq_status
        mock_eq_status.eq.return_value = mock_eq_yacht
        mock_eq_yacht.order.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.execute.return_value = MagicMock(data=[])

        worker.supabase = mock_supabase

        await worker.process_batch()

        # Verify yacht filter was applied
        mock_eq_status.eq.assert_called_with('yacht_id', 'test-yacht-123')

    @pytest.mark.asyncio
    async def test_mark_job_failed_increments_retry(self):
        """Test that mark_job_failed increments retry count."""
        from worker import EmailRAGWorker

        worker = EmailRAGWorker()

        # Mock supabase
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={'retry_count': 1}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None

        worker.supabase = mock_supabase

        await worker.mark_job_failed('job-123', 'Test error')

        # Verify update was called with incremented retry_count
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]['retry_count'] == 2
        assert update_call[0][0]['status'] == 'pending'  # Still pending (< 3 retries)

    @pytest.mark.asyncio
    async def test_mark_job_failed_max_retries(self):
        """Test that job is marked failed after max retries."""
        from worker import EmailRAGWorker

        worker = EmailRAGWorker()

        # Mock supabase - retry_count already at 2
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={'retry_count': 2}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None

        worker.supabase = mock_supabase

        await worker.mark_job_failed('job-123', 'Test error')

        # Verify status is 'failed' after 3rd attempt
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]['retry_count'] == 3
        assert update_call[0][0]['status'] == 'failed'
        assert worker.stats['jobs_failed'] == 1

    @pytest.mark.asyncio
    async def test_mark_job_skipped(self):
        """Test mark_job_skipped updates status correctly.

        Note: 'skipped' is not a valid DB status, so we use 'completed'
        with embedding_generated=False to indicate a skipped job.
        """
        from worker import EmailRAGWorker

        worker = EmailRAGWorker()

        # Mock supabase
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None

        worker.supabase = mock_supabase

        await worker.mark_job_skipped('job-123')

        # Verify update was called with completed status (skipped not valid in DB)
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]['status'] == 'completed'
        assert update_call[0][0]['embedding_generated'] == False
        assert 'Skipped' in update_call[0][0]['error_message']
        assert worker.stats['jobs_skipped'] == 1

    @pytest.mark.asyncio
    async def test_process_job_success(self):
        """Test successful job processing."""
        from worker import EmailRAGWorker

        worker = EmailRAGWorker()

        # Mock supabase
        mock_supabase = MagicMock()

        # Mock job status update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None

        # Mock message fetch
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                'id': 'msg-123',
                'subject': 'Test Subject',
                'preview_text': 'Test preview content',
                'extraction_status': 'pending'
            }
        )

        # Mock RPC call
        mock_supabase.rpc.return_value.execute.return_value = None

        worker.supabase = mock_supabase

        # Mock embedding and extraction - patch at the module where they're imported
        with patch('email_rag.embedder.generate_email_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            with patch('email_rag.entity_extractor.extract_email_entities', new_callable=AsyncMock) as mock_extract:
                mock_extract.return_value = {'entities': [], 'matches': {}}

                job = {
                    'id': 'job-123',
                    'message_id': 'msg-123',
                    'yacht_id': 'yacht-123',
                    'job_type': 'full',
                    'retry_count': 0
                }

                await worker.process_job(job)

                assert worker.stats['jobs_succeeded'] == 1
                mock_embed.assert_called_once()
                mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_job_skips_empty_preview(self):
        """Test that jobs with no preview_text are skipped."""
        from worker import EmailRAGWorker

        worker = EmailRAGWorker()

        # Mock supabase
        mock_supabase = MagicMock()

        # Mock job status update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None

        # Mock message fetch - empty preview_text
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                'id': 'msg-123',
                'subject': 'Test Subject',
                'preview_text': '',
                'extraction_status': 'pending'
            }
        )

        worker.supabase = mock_supabase

        job = {
            'id': 'job-123',
            'message_id': 'msg-123',
            'yacht_id': 'yacht-123',
            'job_type': 'full',
            'retry_count': 0
        }

        await worker.process_job(job)

        assert worker.stats['jobs_skipped'] == 1


# ============================================================================
# PART 4: INTEGRATION TESTS (Require Real DB)
# ============================================================================

class TestWorkerIntegration:
    """Integration tests that require real Supabase connection.

    These tests are marked to skip if SUPABASE_URL is not set.
    """

    @pytest.fixture
    def supabase(self):
        """Get Supabase client if available."""
        import os
        if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_SERVICE_KEY'):
            pytest.skip("SUPABASE_URL or SUPABASE_SERVICE_KEY not set")

        from integrations.supabase import get_supabase_client
        return get_supabase_client()

    def test_can_fetch_pending_jobs(self, supabase):
        """Test that we can query pending jobs from real DB."""
        result = supabase.table('email_extraction_jobs').select(
            'id, message_id, yacht_id, status'
        ).eq('status', 'pending').limit(5).execute()

        # Should not raise - just verify query works
        assert isinstance(result.data, list)

    def test_can_fetch_email_messages(self, supabase):
        """Test that we can query email messages from real DB."""
        result = supabase.table('email_messages').select(
            'id, subject, preview_text'
        ).limit(1).execute()

        assert isinstance(result.data, list)


# ============================================================================
# RUN CONFIGURATION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

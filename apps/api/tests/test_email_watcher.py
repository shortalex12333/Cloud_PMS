"""
Email Watcher - Integration Tests

Phase 11: End-to-end pytest suite for the email watcher system.

Run:
    cd apps/api
    pytest tests/test_email_watcher.py -v
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

# Import services to test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.token_extractor import TokenExtractor
from services.scoring_engine import ScoringEngine
from services.rate_limiter import MicrosoftRateLimiter


# =============================================================================
# Token Extractor Tests (Phase 7a-d)
# =============================================================================

class TestTokenExtractor:
    """Tests for TokenExtractor."""

    def setup_method(self):
        self.extractor = TokenExtractor()

    def test_extract_wo_id_basic(self):
        """Test basic WO-#### pattern."""
        tokens = self.extractor.extract_ids("Re: WO-1234 Pump replacement")
        assert 'wo_id' in tokens
        assert tokens['wo_id'] == ['1234']

    def test_extract_wo_id_variations(self):
        """Test various WO ID formats."""
        test_cases = [
            ("WO-1234 test", ['1234']),
            ("WO#5678 test", ['5678']),
            ("Work Order 9999: test", ['9999']),
            ("Work Order: 1111", ['1111']),
        ]
        for subject, expected in test_cases:
            tokens = self.extractor.extract_ids(subject)
            assert tokens.get('wo_id') == expected, f"Failed for: {subject}"

    def test_extract_po_id(self):
        """Test PO ID extraction."""
        tokens = self.extractor.extract_ids("PO#5678 - Invoice attached")
        assert 'po_id' in tokens
        assert tokens['po_id'] == ['5678']

    def test_extract_multiple_ids(self):
        """Test extracting multiple IDs from same subject."""
        tokens = self.extractor.extract_ids("Re: PO#123 and WO-456 update")
        assert tokens.get('wo_id') == ['456']
        assert tokens.get('po_id') == ['123']

    def test_extract_serial_number(self):
        """Test serial number extraction."""
        parts = self.extractor.extract_part_numbers("Parts for S/N ABC123456")
        assert 'serial_number' in parts
        assert 'ABC123456' in parts['serial_number']

    def test_extract_part_number(self):
        """Test part number extraction."""
        parts = self.extractor.extract_part_numbers("Need CAT-12345 replacement")
        assert 'part_number' in parts
        assert 'CAT-12345' in parts['part_number']

    def test_classify_procurement_attachments(self):
        """Test attachment classification - procurement."""
        attachments = [
            {'name': 'quote_pump_service.pdf'},
            {'name': 'invoice_12345.pdf'},
            {'name': 'random_file.docx'},
        ]
        signals = self.extractor.classify_attachments(attachments)
        assert len(signals['procurement']) == 2
        assert 'quote_pump_service.pdf' in signals['procurement']
        assert 'invoice_12345.pdf' in signals['procurement']

    def test_classify_service_attachments(self):
        """Test attachment classification - service."""
        attachments = [
            {'name': 'service_report_v1.pdf'},
            {'name': 'completion_certificate.pdf'},
        ]
        signals = self.extractor.classify_attachments(attachments)
        assert len(signals['service']) == 2

    def test_vendor_signals_extraction(self):
        """Test vendor signal extraction."""
        signals = self.extractor.extract_vendor_signals(
            "vendor@marineparts.com",
            None
        )
        assert signals['sender_domain'] == 'marineparts.com'
        assert 'sender_hash' in signals
        assert signals['is_personal_domain'] is False

    def test_personal_domain_detection(self):
        """Test personal email domain detection."""
        signals = self.extractor.extract_vendor_signals("user@gmail.com", None)
        assert signals['is_personal_domain'] is True

    def test_has_procurement_signal(self):
        """Test procurement signal detection."""
        tokens = {
            'ids': {'po_id': ['123']},
            'attachment_signals': {'procurement': ['quote.pdf']}
        }
        assert self.extractor.has_procurement_signal(tokens) is True

    def test_has_service_signal(self):
        """Test service signal detection."""
        tokens = {
            'ids': {'wo_id': ['456']},
        }
        assert self.extractor.has_service_signal(tokens) is True


# =============================================================================
# Scoring Engine Tests (Phase 7h)
# =============================================================================

class TestScoringEngine:
    """Tests for ScoringEngine."""

    def setup_method(self):
        self.engine = ScoringEngine()

    def test_score_wo_id_match_highest(self):
        """Test that WO ID match scores 120."""
        candidates = [
            {'match_reason': 'wo_id_match', 'score': 120},
            {'match_reason': 'vendor_domain_match', 'score': 30},
        ]
        scored = self.engine.score_candidates(candidates)
        assert scored[0]['match_reason'] == 'wo_id_match'
        assert scored[0]['score'] == 120

    def test_score_ordering(self):
        """Test candidates are sorted by score descending."""
        candidates = [
            {'match_reason': 'vendor_domain_match', 'score': 30},
            {'match_reason': 'wo_id_match', 'score': 120},
            {'match_reason': 'serial_match', 'score': 70},
        ]
        scored = self.engine.score_candidates(candidates)
        scores = [c['score'] for c in scored]
        assert scores == [120, 70, 30]

    def test_ambiguous_detection(self):
        """Test ambiguity detection when scores are close."""
        candidates = [
            {'match_reason': 'serial_match', 'score': 70},
            {'match_reason': 'part_number_match', 'score': 65},  # Gap < 15
        ]
        scored = self.engine.score_candidates(candidates)
        assert scored[0].get('ambiguous') is True
        assert scored[1].get('ambiguous') is True

    def test_no_ambiguous_when_clear_winner(self):
        """Test no ambiguity when clear gap."""
        candidates = [
            {'match_reason': 'wo_id_match', 'score': 120},
            {'match_reason': 'vendor_domain_match', 'score': 30},  # Gap = 90
        ]
        scored = self.engine.score_candidates(candidates)
        assert scored[0].get('ambiguous') is None

    def test_select_primary_auto_confirm(self):
        """Test auto-confirm selection for high scores."""
        candidates = [{'match_reason': 'wo_id_match', 'score': 130}]
        scored = self.engine.score_candidates(candidates)
        selection = self.engine.select_primary(scored)

        assert selection is not None
        assert selection['confidence'] == 'deterministic'
        assert selection['action'] == 'auto_link'

    def test_select_primary_strong_suggest(self):
        """Test strong suggestion for medium-high scores."""
        candidates = [{'match_reason': 'serial_match', 'score': 100}]
        scored = self.engine.score_candidates(candidates)
        selection = self.engine.select_primary(scored)

        assert selection is not None
        assert selection['confidence'] == 'suggested'
        assert selection['action'] == 'suggest'

    def test_select_primary_weak_suggest(self):
        """Test weak suggestion for borderline scores."""
        candidates = [{'match_reason': 'vendor_email_match', 'score': 75}]
        scored = self.engine.score_candidates(candidates)
        selection = self.engine.select_primary(scored)

        assert selection is not None
        assert selection['action'] == 'weak_suggest'

    def test_select_primary_no_suggest(self):
        """Test no suggestion for low scores."""
        candidates = [{'match_reason': 'vendor_domain_match', 'score': 30}]
        scored = self.engine.score_candidates(candidates)
        selection = self.engine.select_primary(scored)

        assert selection is None

    def test_should_auto_confirm_thresholds(self):
        """Test auto-confirm threshold checking."""
        assert self.engine.should_auto_confirm(130) is True
        assert self.engine.should_auto_confirm(129) is False
        assert self.engine.should_auto_confirm(150) is True

    def test_should_create_suggestion_thresholds(self):
        """Test suggestion creation threshold."""
        assert self.engine.should_create_suggestion(70) is True
        assert self.engine.should_create_suggestion(69) is False
        assert self.engine.should_create_suggestion(100) is True


# =============================================================================
# Rate Limiter Tests (Phase 4)
# =============================================================================

class TestRateLimiter:
    """Tests for MicrosoftRateLimiter."""

    def setup_method(self):
        self.mock_supabase = Mock()
        self.limiter = MicrosoftRateLimiter(self.mock_supabase)

    @pytest.mark.asyncio
    async def test_can_make_call_under_limit(self):
        """Test call allowed when under limit."""
        self.mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={'api_calls_this_hour': 100, 'hour_window_start': None}
        )
        self.mock_supabase.rpc.return_value.execute.return_value = Mock(data=None)

        result = await self.limiter.can_make_call('user123', 'yacht456')
        assert result is True

    @pytest.mark.asyncio
    async def test_can_make_call_at_limit(self):
        """Test call blocked when at limit."""
        self.mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={'api_calls_this_hour': 9500, 'hour_window_start': datetime.utcnow().isoformat()}
        )
        self.mock_supabase.rpc.return_value.execute.return_value = Mock(data=None)

        result = await self.limiter.can_make_call('user123', 'yacht456')
        assert result is False

    @pytest.mark.asyncio
    async def test_record_call(self):
        """Test recording API calls."""
        self.mock_supabase.rpc.return_value.execute.return_value = Mock(data=101)

        result = await self.limiter.record_call('user123', 'yacht456', 1)
        assert result == 101

        self.mock_supabase.rpc.assert_called_with('record_email_api_calls', {
            'p_user_id': 'user123',
            'p_yacht_id': 'yacht456',
            'p_call_count': 1
        })

    def test_get_stats(self):
        """Test rate limit stats calculation."""
        watcher_data = {
            'api_calls_this_hour': 5000,
            'hour_window_start': datetime.utcnow().isoformat(),
        }

        stats = self.limiter.get_stats(watcher_data)

        assert stats['calls_this_hour'] == 5000
        assert stats['calls_remaining'] == 4500  # 9500 - 5000
        assert stats['is_rate_limited'] is False

    def test_get_stats_rate_limited(self):
        """Test stats when rate limited."""
        watcher_data = {
            'api_calls_this_hour': 9600,
            'hour_window_start': datetime.utcnow().isoformat(),
        }

        stats = self.limiter.get_stats(watcher_data)
        assert stats['is_rate_limited'] is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestEmailWatcherIntegration:
    """Integration tests requiring mock Supabase."""

    @pytest.mark.asyncio
    async def test_full_token_extraction_pipeline(self):
        """Test complete token extraction from email metadata."""
        extractor = TokenExtractor()

        tokens = extractor.extract_all(
            subject="Re: WO-1234 Parts for S/N ABC123456",
            from_address="vendor@marineparts.com",
            attachments=[
                {'name': 'quote_parts.pdf'},
                {'name': 'spec_sheet.pdf'},
            ],
            participant_hashes=['hash1', 'hash2']
        )

        # Should have ID tokens
        assert 'ids' in tokens
        assert tokens['ids'].get('wo_id') == ['1234']

        # Should have part tokens
        assert 'parts' in tokens
        assert 'ABC123456' in tokens['parts'].get('serial_number', [])

        # Should have attachment signals
        assert 'attachment_signals' in tokens
        assert len(tokens['attachment_signals']['procurement']) > 0

        # Should have vendor info
        assert 'vendor' in tokens
        assert tokens['vendor']['sender_domain'] == 'marineparts.com'

    @pytest.mark.asyncio
    async def test_scoring_with_context_bonuses(self):
        """Test scoring with context bonuses applied."""
        engine = ScoringEngine()

        candidates = [
            {
                'match_reason': 'serial_match',
                'score': 70,
                'status': 'open',
                'updated_at': datetime.utcnow().isoformat(),
            }
        ]

        context = {'vendor_affinity': {'equipment': 10}}

        scored = engine.score_candidates(candidates, context)

        # Should have bonuses added
        assert scored[0]['score'] > 70  # Base + bonuses


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

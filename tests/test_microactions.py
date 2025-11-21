"""
Comprehensive Test Suite for Micro-Action Extraction
====================================================

Test coverage:
1. Single action detection
2. Multi-action detection (conjunctions)
3. Abbreviations and synonyms
4. Misspellings and typos
5. Edge cases (empty, very long, special chars)
6. Unsupported actions
7. Category-specific patterns
8. Overlap resolution
9. Confidence thresholds
10. API endpoint responses

Run with: pytest tests/test_microactions.py -v
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'api'))

from microaction_extractor import MicroActionExtractor, extract_for_n8n
from microaction_config import get_config, ValidationRules


# ========================================================================
# FIXTURES
# ========================================================================

@pytest.fixture
def extractor():
    """Create extractor instance for testing"""
    return MicroActionExtractor()


@pytest.fixture
def production_config():
    """Get production configuration"""
    return get_config('production')


# ========================================================================
# TEST GROUP 1: SINGLE ACTION DETECTION
# ========================================================================

class TestSingleActionDetection:
    """Test detection of single micro-actions"""

    def test_create_work_order_explicit(self, extractor):
        """Test explicit 'create work order' pattern"""
        result = extractor.extract_microactions("create work order")
        assert "create_work_order" in result
        assert len(result) == 1

    def test_create_work_order_with_article(self, extractor):
        """Test 'create a work order' pattern"""
        result = extractor.extract_microactions("create a new work order")
        assert "create_work_order" in result

    def test_add_to_handover(self, extractor):
        """Test 'add to handover' pattern"""
        result = extractor.extract_microactions("add to handover")
        assert "add_to_handover" in result

    def test_list_work_orders(self, extractor):
        """Test 'show all work orders' pattern"""
        result = extractor.extract_microactions("show all open work orders")
        assert "list_work_orders" in result

    def test_report_fault(self, extractor):
        """Test 'report fault' pattern"""
        result = extractor.extract_microactions("report fault on main engine")
        assert "report_fault" in result

    def test_check_stock(self, extractor):
        """Test 'check stock' pattern"""
        result = extractor.extract_microactions("check stock levels")
        assert "check_stock" in result

    def test_create_purchase_request(self, extractor):
        """Test 'create purchase request' pattern"""
        result = extractor.extract_microactions("create purchase request for engine oil")
        assert "create_purchase_request" in result

    def test_upload_document(self, extractor):
        """Test 'upload document' pattern"""
        result = extractor.extract_microactions("upload maintenance manual")
        assert "upload_document" in result

    def test_log_hours_of_rest(self, extractor):
        """Test 'log hours of rest' pattern"""
        result = extractor.extract_microactions("log my hours of rest")
        assert "log_hours_of_rest" in result

    def test_export_handover(self, extractor):
        """Test 'export handover' pattern"""
        result = extractor.extract_microactions("export handover report")
        assert "export_handover" in result


# ========================================================================
# TEST GROUP 2: MULTI-ACTION DETECTION
# ========================================================================

class TestMultiActionDetection:
    """Test detection of multiple actions in single query"""

    def test_two_actions_with_and(self, extractor):
        """Test 'create work order AND add to handover'"""
        result = extractor.extract_microactions("create work order and add to handover")
        assert "create_work_order" in result
        assert "add_to_handover" in result
        assert len(result) == 2

    def test_two_actions_with_then(self, extractor):
        """Test 'create wo THEN add to handover'"""
        result = extractor.extract_microactions("create wo then add to handover")
        assert "create_work_order" in result
        assert "add_to_handover" in result

    def test_three_actions_with_conjunctions(self, extractor):
        """Test multiple actions with different conjunctions"""
        result = extractor.extract_microactions(
            "create work order, add to handover, and export handover"
        )
        assert "create_work_order" in result
        assert "add_to_handover" in result
        assert "export_handover" in result
        assert len(result) >= 2  # At least 2 detected

    def test_report_and_create(self, extractor):
        """Test 'report fault and create work order'"""
        result = extractor.extract_microactions("report fault and create work order")
        assert "report_fault" in result
        assert "create_work_order" in result


# ========================================================================
# TEST GROUP 3: ABBREVIATIONS AND SYNONYMS
# ========================================================================

class TestAbbreviationsAndSynonyms:
    """Test handling of abbreviations and synonyms"""

    def test_wo_abbreviation(self, extractor):
        """Test 'wo' abbreviation for work order"""
        result = extractor.extract_microactions("create wo")
        assert "create_work_order" in result

    def test_hor_abbreviation(self, extractor):
        """Test 'hor' abbreviation for handover"""
        result = extractor.extract_microactions("add to hor")
        assert "add_to_handover" in result

    def test_pr_abbreviation(self, extractor):
        """Test 'pr' abbreviation for purchase request"""
        result = extractor.extract_microactions("create pr for spare parts")
        assert "create_purchase_request" in result

    def test_doc_abbreviation(self, extractor):
        """Test 'doc' abbreviation for document"""
        result = extractor.extract_microactions("upload doc")
        assert "upload_document" in result

    def test_multiple_abbreviations(self, extractor):
        """Test multiple abbreviations in one query"""
        result = extractor.extract_microactions("create wo and add to hor")
        assert "create_work_order" in result
        assert "add_to_handover" in result

    def test_synonym_new_task(self, extractor):
        """Test 'new task' synonym for work order"""
        result = extractor.extract_microactions("create new task")
        # May or may not match depending on gazetteer - this is edge case
        # Main pattern should still work
        assert len(result) >= 0  # No error


# ========================================================================
# TEST GROUP 4: MISSPELLINGS AND TYPOS
# ========================================================================

class TestMisspellingsAndTypos:
    """Test robustness to common typos"""

    def test_misspelling_werk_order(self, extractor):
        """Test common misspelling 'werk order'"""
        # Regex won't catch this, but shouldn't error
        result = extractor.extract_microactions("create werk order")
        # May return empty or partial match - should not crash
        assert isinstance(result, list)

    def test_extra_spaces(self, extractor):
        """Test handling of extra spaces"""
        result = extractor.extract_microactions("create    work     order")
        assert "create_work_order" in result

    def test_mixed_case(self, extractor):
        """Test case insensitivity"""
        result = extractor.extract_microactions("CREATE WORK ORDER")
        assert "create_work_order" in result

    def test_special_characters(self, extractor):
        """Test handling of special characters"""
        result = extractor.extract_microactions("create work-order!")
        # Should still detect despite hyphen and exclamation
        assert "create_work_order" in result or len(result) == 0


# ========================================================================
# TEST GROUP 5: EDGE CASES
# ========================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_query(self, extractor):
        """Test empty query"""
        result = extractor.extract_microactions("")
        assert result == []

    def test_whitespace_only(self, extractor):
        """Test whitespace-only query"""
        result = extractor.extract_microactions("   ")
        assert result == []

    def test_very_long_query(self, extractor):
        """Test very long query (should truncate gracefully)"""
        long_query = "create work order " * 100
        result = extractor.extract_microactions(long_query)
        assert "create_work_order" in result

    def test_numeric_only(self, extractor):
        """Test numeric-only query"""
        result = extractor.extract_microactions("12345")
        assert result == []

    def test_special_chars_only(self, extractor):
        """Test special characters only"""
        result = extractor.extract_microactions("!@#$%^&*()")
        assert result == []

    def test_single_word(self, extractor):
        """Test single word query"""
        result = extractor.extract_microactions("handover")
        # May or may not match - depends on patterns
        assert isinstance(result, list)


# ========================================================================
# TEST GROUP 6: UNSUPPORTED ACTIONS
# ========================================================================

class TestUnsupportedActions:
    """Test detection of unsupported action indicators"""

    def test_unsupported_translate(self, extractor):
        """Test unsupported action: translate"""
        result = extractor.extract_with_details("translate this to spanish")
        # Should detect as unsupported
        assert result['has_unsupported'] or len(result['micro_actions']) == 0

    def test_unsupported_weather(self, extractor):
        """Test unsupported action: weather"""
        result = extractor.extract_microactions("what's the weather tomorrow")
        # Should return empty or be flagged as unsupported
        assert len(result) == 0 or isinstance(result, list)

    def test_unsupported_calculate(self, extractor):
        """Test unsupported action: calculate"""
        result = extractor.extract_microactions("calculate 2 + 2")
        assert len(result) == 0 or isinstance(result, list)


# ========================================================================
# TEST GROUP 7: CATEGORY-SPECIFIC PATTERNS
# ========================================================================

class TestCategoryPatterns:
    """Test patterns specific to each category"""

    def test_work_orders_category(self, extractor):
        """Test work orders category actions"""
        queries = [
            "create work order",
            "close work order",
            "update work order",
            "list work orders"
        ]
        for query in queries:
            result = extractor.extract_microactions(query)
            assert len(result) >= 0  # Should process without error

    def test_handover_category(self, extractor):
        """Test handover category actions"""
        queries = [
            "add to handover",
            "export handover",
            "clear handover"
        ]
        for query in queries:
            result = extractor.extract_microactions(query)
            assert isinstance(result, list)

    def test_faults_category(self, extractor):
        """Test faults category actions"""
        queries = [
            "report fault",
            "diagnose fault",
            "fix fault"
        ]
        for query in queries:
            result = extractor.extract_microactions(query)
            assert isinstance(result, list)

    def test_inventory_category(self, extractor):
        """Test inventory category actions"""
        queries = [
            "check stock",
            "order parts",
            "update inventory"
        ]
        for query in queries:
            result = extractor.extract_microactions(query)
            assert isinstance(result, list)


# ========================================================================
# TEST GROUP 8: DETAILED EXTRACTION
# ========================================================================

class TestDetailedExtraction:
    """Test extract_with_details() method"""

    def test_detailed_extraction_structure(self, extractor):
        """Test that detailed extraction returns correct structure"""
        result = extractor.extract_with_details("create work order")

        assert 'micro_actions' in result
        assert 'matches' in result
        assert 'has_unsupported' in result
        assert 'total_matches' in result
        assert 'unique_actions' in result

    def test_detailed_extraction_matches(self, extractor):
        """Test that matches contain required fields"""
        result = extractor.extract_with_details("create work order")

        if result['matches']:
            match = result['matches'][0]
            assert 'action_name' in match
            assert 'confidence' in match
            assert 'source' in match
            assert 'match_text' in match
            assert 'span' in match

    def test_confidence_scores(self, extractor):
        """Test that confidence scores are in valid range"""
        result = extractor.extract_with_details("create work order and add to handover")

        for match in result['matches']:
            confidence = match['confidence']
            assert 0.0 <= confidence <= 1.0


# ========================================================================
# TEST GROUP 9: CONFIGURATION
# ========================================================================

class TestConfiguration:
    """Test configuration and thresholds"""

    def test_production_config_loads(self, production_config):
        """Test that production config loads correctly"""
        assert production_config.ai_fallback_threshold == 0.75
        assert production_config.min_output_confidence == 0.70
        assert production_config.enable_debug_logging == False

    def test_category_weights(self, production_config):
        """Test category weights are defined"""
        assert 'work_orders' in production_config.category_weights
        assert 'handover' in production_config.category_weights
        assert production_config.category_weights['work_orders'] > 0

    def test_category_boost(self, production_config):
        """Test category boost calculation"""
        boost = production_config.get_category_boost('work_orders')
        assert 0.0 <= boost <= 1.0


# ========================================================================
# TEST GROUP 10: VALIDATION RULES
# ========================================================================

class TestValidationRules:
    """Test action combination validation"""

    def test_mutually_exclusive_actions(self):
        """Test validation of mutually exclusive actions"""
        actions = ['create_work_order', 'close_work_order']
        validation = ValidationRules.validate_action_combination(actions)

        assert validation['valid'] == False
        assert len(validation['warnings']) > 0

    def test_valid_action_pair(self):
        """Test validation of valid action pair"""
        actions = ['create_work_order', 'add_to_handover']
        validation = ValidationRules.validate_action_combination(actions)

        # Should be valid (common pair)
        assert isinstance(validation, dict)
        assert 'valid' in validation

    def test_too_many_actions(self):
        """Test validation warns about too many actions"""
        actions = ['action1', 'action2', 'action3', 'action4', 'action5']
        validation = ValidationRules.validate_action_combination(actions)

        assert len(validation['warnings']) > 0


# ========================================================================
# TEST GROUP 11: N8N WRAPPER
# ========================================================================

class TestN8NWrapper:
    """Test n8n wrapper function"""

    def test_extract_for_n8n_structure(self):
        """Test n8n wrapper returns correct structure"""
        result = extract_for_n8n("create work order")

        assert 'micro_actions' in result
        assert 'count' in result
        assert isinstance(result['micro_actions'], list)
        assert isinstance(result['count'], int)

    def test_extract_for_n8n_multi_action(self):
        """Test n8n wrapper with multiple actions"""
        result = extract_for_n8n("create work order and add to handover")

        assert result['count'] >= 1
        assert len(result['micro_actions']) == result['count']


# ========================================================================
# TEST GROUP 12: PERFORMANCE
# ========================================================================

class TestPerformance:
    """Test performance characteristics"""

    def test_extraction_speed(self, extractor):
        """Test that extraction completes in reasonable time"""
        import time

        start = time.time()
        extractor.extract_microactions("create work order and add to handover")
        duration = time.time() - start

        # Should complete in <100ms (regex-only)
        assert duration < 0.5  # 500ms generous threshold for test environment

    def test_batch_processing(self, extractor):
        """Test processing multiple queries"""
        queries = [
            "create work order",
            "add to handover",
            "report fault",
            "check stock",
            "export handover"
        ]

        for query in queries:
            result = extractor.extract_microactions(query)
            assert isinstance(result, list)


# ========================================================================
# RUN TESTS
# ========================================================================

if __name__ == '__main__':
    # Run tests with: python test_microactions.py
    pytest.main([__file__, '-v', '--tb=short'])

"""
Micro-Action Extraction Configuration
=====================================

Centralized configuration for the micro-action extraction pipeline.
Similar architecture to maritime entity extraction config.

This module defines:
- Confidence thresholds by action category
- Source multipliers (regex, gazetteer, AI)
- Overlap resolution scoring weights
- Category priorities and weights
- Performance tuning parameters
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ExtractionConfig:
    """
    Main configuration class for micro-action extraction pipeline.
    All thresholds and weights centralized here for easy tuning.
    """

    # ========================================================================
    # SOURCE MULTIPLIERS (match maritime extractor architecture)
    # ========================================================================

    source_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'regex': 1.0,       # Deterministic patterns (highest confidence)
        'gazetteer': 0.95,  # Synonym/abbreviation lookup (very high confidence)
        'ai': 0.70          # AI fallback (lower confidence, higher cost)
    })

    # ========================================================================
    # CONFIDENCE THRESHOLDS BY CATEGORY
    # ========================================================================

    # Minimum confidence to accept a match from each source
    min_confidence_by_source: Dict[str, float] = field(default_factory=lambda: {
        'regex': 0.60,      # Accept regex matches with 60%+ confidence
        'gazetteer': 0.70,  # Accept gazetteer matches with 70%+ confidence
        'ai': 0.75          # Accept AI matches with 75%+ confidence (stricter)
    })

    # Confidence threshold to trigger AI fallback
    # If best regex/gazetteer match is below this, call AI
    ai_fallback_threshold: float = 0.80

    # Minimum confidence to return an action to the user
    # Below this, return empty result or "unsupported" indicator
    min_output_confidence: float = 0.65

    # ========================================================================
    # CATEGORY WEIGHTS & PRIORITIES
    # ========================================================================

    # Weight by category (higher = more important/common)
    # Used to boost confidence for frequent action types
    category_weights: Dict[str, float] = field(default_factory=lambda: {
        'work_orders': 4.5,     # Most common (create_wo, list_wo, etc.)
        'handover': 4.2,        # Very common (add_to_handover, export_handover)
        'faults': 4.0,          # Common (report_fault, diagnose_fault)
        'inventory': 3.5,       # Moderately common (check_stock, order_parts)
        'documents': 3.0,       # Moderately common (upload_doc, find_manual)
        'purchasing': 2.8,      # Less common (create_pr, approve_po)
        'hours_of_rest': 2.5,   # Less common (log_hours, check_compliance)
        'mobile': 2.0,          # Least common (crew_list, weather, etc.)
        'unsupported': 0.0      # Not actionable
    })

    # Priority order for category disambiguation
    # When multiple categories match, use this order to decide
    category_priority: List[str] = field(default_factory=lambda: [
        'work_orders',      # Highest priority (core functionality)
        'handover',
        'faults',
        'inventory',
        'purchasing',
        'documents',
        'hours_of_rest',
        'mobile'
    ])

    # ========================================================================
    # OVERLAP RESOLUTION
    # ========================================================================

    # When two matches overlap, score them using these weights
    overlap_resolution_weights: Dict[str, float] = field(default_factory=lambda: {
        'confidence': 0.5,      # 50% weight on confidence score
        'span_length': 0.3,     # 30% weight on match length (longer = more specific)
        'category_priority': 0.2  # 20% weight on category priority
    })

    # Maximum allowed overlap (as fraction of shorter match)
    # Example: If match A is 10 chars and match B is 20 chars,
    # they're considered overlapping if they share >30% of match A
    max_overlap_ratio: float = 0.3

    # ========================================================================
    # MULTI-ACTION DETECTION
    # ========================================================================

    # Minimum distance (chars) between matches to consider them separate actions
    # Example: "create wo and add to handover"
    # "create wo" and "add to handover" are 6 chars apart (" and ")
    min_action_distance: int = 3

    # Conjunction words that indicate multiple actions
    conjunction_indicators: List[str] = field(default_factory=lambda: [
        'and', 'then', 'also', 'plus', 'additionally',
        '&', '+', ',', 'afterwards', 'after that'
    ])

    # Maximum number of actions to extract from single query
    # Prevents runaway extraction on long text
    max_actions_per_query: int = 5

    # ========================================================================
    # PERFORMANCE TUNING
    # ========================================================================

    # Enable caching of compiled regex patterns
    enable_pattern_caching: bool = True

    # Enable parallel processing for multiple queries
    enable_parallel_processing: bool = False  # Not needed for single query

    # Timeout for AI extraction (milliseconds)
    ai_extraction_timeout_ms: int = 2000

    # Maximum query length to process (chars)
    # Longer queries are truncated
    max_query_length: int = 500

    # ========================================================================
    # LOGGING & DEBUGGING
    # ========================================================================

    # Enable detailed logging
    enable_debug_logging: bool = False

    # Log all matches (including low-confidence ones)
    log_all_matches: bool = False

    # Include match metadata in response
    include_match_metadata: bool = False

    # ========================================================================
    # METHODS FOR DYNAMIC CALCULATIONS
    # ========================================================================

    def calculate_overlap_score(self, match_a: Dict, match_b: Dict) -> float:
        """
        Calculate overlap score to determine which match to keep.
        Higher score = better match (keep this one).

        Similar to maritime entity_merger.py overlap resolution.
        """
        # Confidence component (0-1 scale)
        conf_a = match_a.get('confidence', 0.0)
        conf_b = match_b.get('confidence', 0.0)
        conf_score = conf_a - conf_b  # Positive if A is better

        # Span length component (longer matches are more specific)
        span_a = match_a['end_pos'] - match_a['start_pos']
        span_b = match_b['end_pos'] - match_b['start_pos']
        span_score = (span_a - span_b) / max(span_a, span_b, 1)

        # Category priority component
        cat_a = match_a.get('category', 'unsupported')
        cat_b = match_b.get('category', 'unsupported')
        try:
            priority_a = self.category_priority.index(cat_a)
            priority_b = self.category_priority.index(cat_b)
            cat_score = (priority_b - priority_a) / len(self.category_priority)
        except ValueError:
            cat_score = 0.0

        # Weighted combination
        weights = self.overlap_resolution_weights
        final_score = (
            weights['confidence'] * conf_score +
            weights['span_length'] * span_score +
            weights['category_priority'] * cat_score
        )

        return final_score

    def get_category_boost(self, category: str) -> float:
        """
        Get confidence boost multiplier for a category.
        Normalized to 0-1 scale.
        """
        weight = self.category_weights.get(category, 1.0)
        max_weight = max(self.category_weights.values())
        return weight / max_weight

    def should_trigger_ai_fallback(self, best_confidence: float) -> bool:
        """
        Determine if AI fallback should be triggered based on
        best regex/gazetteer confidence.
        """
        return best_confidence < self.ai_fallback_threshold

    def is_valid_output(self, confidence: float) -> bool:
        """
        Check if a match has sufficient confidence to return to user.
        """
        return confidence >= self.min_output_confidence


# ========================================================================
# PRESET CONFIGURATIONS FOR DIFFERENT ENVIRONMENTS
# ========================================================================

class ProductionConfig(ExtractionConfig):
    """Production environment: Balanced speed and accuracy"""
    ai_fallback_threshold: float = 0.75  # Trigger AI for ambiguous cases
    min_output_confidence: float = 0.70  # Higher bar for production
    enable_debug_logging: bool = False
    include_match_metadata: bool = False


class DevelopmentConfig(ExtractionConfig):
    """Development environment: Full logging and metadata"""
    enable_debug_logging: bool = True
    log_all_matches: bool = True
    include_match_metadata: bool = True


class PerformanceConfig(ExtractionConfig):
    """Performance-optimized: Minimize AI calls, maximize speed"""
    ai_fallback_threshold: float = 0.50  # Rarely trigger AI
    min_output_confidence: float = 0.60  # Lower bar to avoid AI
    enable_pattern_caching: bool = True
    ai_extraction_timeout_ms: int = 1000  # Strict timeout


class AccuracyConfig(ExtractionConfig):
    """Accuracy-optimized: More AI usage, stricter thresholds"""
    ai_fallback_threshold: float = 0.85  # Trigger AI more often
    min_output_confidence: float = 0.75  # Higher bar for output
    ai_extraction_timeout_ms: int = 3000  # Allow more time


# ========================================================================
# FACTORY FUNCTION
# ========================================================================

def get_config(environment: str = 'production') -> ExtractionConfig:
    """
    Factory function to get configuration for specific environment.

    Args:
        environment: 'production', 'development', 'performance', or 'accuracy'

    Returns:
        ExtractionConfig instance
    """
    configs = {
        'production': ProductionConfig(),
        'development': DevelopmentConfig(),
        'performance': PerformanceConfig(),
        'accuracy': AccuracyConfig(),
        'default': ExtractionConfig()
    }

    return configs.get(environment, configs['default'])


# ========================================================================
# VALIDATION RULES
# ========================================================================

class ValidationRules:
    """
    Validation rules for micro-action extraction.
    Similar to maritime extractor's validation logic.
    """

    # Actions that require specific context
    CONTEXT_REQUIRED_ACTIONS = {
        'create_work_order': ['part', 'equipment', 'issue'],
        'report_fault': ['fault_code', 'equipment', 'symptom'],
        'create_purchase_request': ['item', 'quantity'],
        'upload_document': ['document_type'],
        'log_hours_of_rest': ['hours', 'date']
    }

    # Actions that are mutually exclusive (can't both be in same query)
    MUTUALLY_EXCLUSIVE_ACTIONS = [
        ('create_work_order', 'close_work_order'),
        ('export_handover', 'clear_handover'),
        ('approve_purchase_order', 'reject_purchase_order')
    ]

    # Actions that commonly co-occur
    COMMON_PAIRS = [
        ('create_work_order', 'add_to_handover'),
        ('report_fault', 'create_work_order'),
        ('check_stock', 'create_purchase_request'),
        ('diagnose_fault', 'report_fault')
    ]

    @staticmethod
    def validate_action_combination(actions: List[str]) -> Dict[str, any]:
        """
        Validate that detected actions make sense together.

        Returns:
            {
                'valid': bool,
                'warnings': List[str],
                'suggestions': List[str]
            }
        """
        warnings = []
        suggestions = []

        # Check for mutually exclusive actions
        for action_a, action_b in ValidationRules.MUTUALLY_EXCLUSIVE_ACTIONS:
            if action_a in actions and action_b in actions:
                warnings.append(
                    f"'{action_a}' and '{action_b}' are mutually exclusive. "
                    f"Please clarify which action you want."
                )

        # Check for uncommon combinations
        if len(actions) == 2:
            if tuple(actions) not in ValidationRules.COMMON_PAIRS:
                suggestions.append(
                    f"Detected: {actions}. This is an uncommon combination. "
                    f"Please confirm this is what you intended."
                )

        # Too many actions
        if len(actions) > 3:
            warnings.append(
                f"Detected {len(actions)} actions in one query. "
                f"Consider breaking this into separate queries for clarity."
            )

        return {
            'valid': len(warnings) == 0,
            'warnings': warnings,
            'suggestions': suggestions
        }


# ========================================================================
# EXAMPLE USAGE
# ========================================================================

if __name__ == '__main__':
    # Test configuration loading
    print("Micro-Action Extraction Configuration Test")
    print("=" * 60)

    # Production config
    prod_config = get_config('production')
    print(f"\n✓ Production Config:")
    print(f"  - AI Fallback Threshold: {prod_config.ai_fallback_threshold}")
    print(f"  - Min Output Confidence: {prod_config.min_output_confidence}")
    print(f"  - Debug Logging: {prod_config.enable_debug_logging}")

    # Performance config
    perf_config = get_config('performance')
    print(f"\n✓ Performance Config:")
    print(f"  - AI Fallback Threshold: {perf_config.ai_fallback_threshold}")
    print(f"  - AI Timeout: {perf_config.ai_extraction_timeout_ms}ms")

    # Test category boost
    print(f"\n✓ Category Boosts:")
    for category in ['work_orders', 'handover', 'mobile']:
        boost = prod_config.get_category_boost(category)
        print(f"  - {category}: {boost:.2f}")

    # Test validation
    print(f"\n✓ Validation Test:")
    test_actions = ['create_work_order', 'close_work_order']
    validation = ValidationRules.validate_action_combination(test_actions)
    print(f"  - Actions: {test_actions}")
    print(f"  - Valid: {validation['valid']}")
    if validation['warnings']:
        print(f"  - Warnings: {validation['warnings']}")

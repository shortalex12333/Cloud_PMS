"""
Micro-Action Extraction Configuration
=====================================

=== PLAIN ENGLISH SUMMARY ===
This file contains all the SETTINGS and THRESHOLDS for the entity extraction system.
Think of it like a control panel with knobs and dials that tune how the system behaves.

=== WHY HAVE A CONFIG FILE? ===
1. TUNING: We can adjust behavior without changing code
2. ENVIRONMENTS: Different settings for production vs development
3. TESTING: Easy to try different thresholds
4. DOCUMENTATION: All settings in one place

=== KEY CONCEPTS ===

1. CONFIDENCE THRESHOLDS:
   - How sure do we need to be before acting on a detection?
   - Too low: We act on wrong detections (false positives)
   - Too high: We miss valid detections (false negatives)

2. SOURCE MULTIPLIERS:
   - Different methods have different reliability
   - regex (pattern matching): Most reliable, exact matches
   - gazetteer (lookup tables): Very reliable, known synonyms
   - ai (GPT): Smart but less predictable

3. CATEGORY WEIGHTS:
   - Some actions are more common than others
   - "create_work_order" happens daily
   - "log_hours_of_rest" happens less often
   - Weights help prioritize ambiguous cases

4. OVERLAP RESOLUTION:
   - When two matches overlap in the same text
   - Which one should we keep?
   - Score based on confidence, length, category

=== PRESET CONFIGURATIONS ===
- ProductionConfig: Balanced for real use
- DevelopmentConfig: Full logging for debugging
- PerformanceConfig: Fast, fewer AI calls
- AccuracyConfig: More AI, higher quality

Centralized configuration for the micro-action extraction pipeline.
Similar architecture to maritime entity extraction config.

This module defines:
- Confidence thresholds by action category
- Source multipliers (regex, gazetteer, AI)
- Overlap resolution scoring weights
- Category priorities and weights
- Performance tuning parameters
"""

# =============================================================================
# IMPORTS
# =============================================================================

# typing: Type hints for documentation
# Dict = dictionary, List = array, Optional = can be None
from typing import Dict, List, Optional

# dataclass: Shortcut for creating data-holding classes
# field: Allows setting default values with factories (for mutable defaults)
from dataclasses import dataclass, field


# =============================================================================
# MAIN CONFIGURATION CLASS
# =============================================================================

# @dataclass creates a class that mainly holds data
# All the settings are defined as class attributes
@dataclass
class ExtractionConfig:
    """
    Main configuration class for micro-action extraction pipeline.

    === WHAT THIS DOES ===
    Holds ALL the settings and thresholds for the extraction system.
    Other modules import this config and use its values.

    === HOW TO USE ===
    ```python
    config = ExtractionConfig()  # Get default config
    if config.should_trigger_ai_fallback(confidence):
        # Call AI for help
    ```

    === CHANGING SETTINGS ===
    Don't modify this class directly in production.
    Use one of the preset classes (ProductionConfig, etc.) or
    create your own subclass.

    All thresholds and weights centralized here for easy tuning.
    """

    # ========================================================================
    # SOURCE MULTIPLIERS
    # ========================================================================
    #
    # Different extraction methods have different reliability.
    # These multipliers adjust confidence based on the source.
    #
    # Matches maritime extractor architecture for consistency.

    source_multipliers: Dict[str, float] = field(default_factory=lambda: {

        # REGEX: Pattern matching using regular expressions
        # Most reliable because it's deterministic (same input = same output)
        # If pattern matches, we're very confident it's correct
        # Example: "create work order" always matches "create_work_order" pattern
        'regex': 1.0,       # No adjustment (100% of calculated confidence)

        # GAZETTEER: Lookup tables with known terms and synonyms
        # Very reliable because we've pre-defined these mappings
        # Example: "wo" → "work order", "gen" → "generator"
        # Slightly lower because synonyms can be ambiguous
        'gazetteer': 0.95,  # 95% of calculated confidence

        # AI: GPT-based extraction
        # Smart but less predictable - AI can hallucinate
        # More expensive (API calls cost money)
        # Used as fallback when regex/gazetteer aren't confident enough
        'ai': 0.70          # 70% of calculated confidence
    })

    # ========================================================================
    # CONFIDENCE THRESHOLDS BY SOURCE
    # ========================================================================
    #
    # Each source has a minimum confidence required to accept its results.
    # This prevents low-quality matches from being used.

    min_confidence_by_source: Dict[str, float] = field(default_factory=lambda: {

        # Regex: Accept matches with 60%+ confidence
        # Lower threshold because regex is deterministic
        # If pattern matched, we trust it
        'regex': 0.60,

        # Gazetteer: Accept matches with 70%+ confidence
        # Medium threshold because synonyms can be ambiguous
        'gazetteer': 0.70,

        # AI: Accept matches with 75%+ confidence
        # Higher threshold because AI can be wrong
        # We only trust high-confidence AI predictions
        'ai': 0.75
    })

    # ========================================================================
    # AI FALLBACK THRESHOLD
    # ========================================================================
    #
    # When should we call AI for help?
    #
    # If the best regex/gazetteer match has confidence BELOW this threshold,
    # we call AI to get a potentially better result.
    #
    # Trade-off:
    # - Higher threshold: More AI calls (slower, more expensive, more accurate)
    # - Lower threshold: Fewer AI calls (faster, cheaper, less accurate)

    ai_fallback_threshold: float = 0.80  # Call AI if best match is below 80%

    # ========================================================================
    # MINIMUM OUTPUT CONFIDENCE
    # ========================================================================
    #
    # What's the minimum confidence to return a result to the user?
    #
    # If ALL methods (regex, gazetteer, AI) produce results below this,
    # we return nothing (or an "unsupported" indicator).
    #
    # This prevents acting on uncertain detections.
    #
    # Example:
    # - Query: "blah blah" → best match at 40% confidence
    # - 40% < 65% threshold → don't return this, it's too uncertain

    min_output_confidence: float = 0.65  # Must be 65%+ confident to return

    # ========================================================================
    # CATEGORY WEIGHTS & PRIORITIES
    # ========================================================================
    #
    # Some action categories are more common/important than others.
    # Weights boost confidence for frequent categories.
    #
    # Scale: 0.0 (not actionable) to 5.0 (very important)
    #
    # These are based on usage data from yacht maintenance operations:
    # - Chief Engineers create work orders multiple times per day
    # - Hours of rest is logged once per day
    # - Mobile-specific features are used occasionally

    category_weights: Dict[str, float] = field(default_factory=lambda: {

        # Work Orders: Most common action category
        # Create, list, update, close work orders
        # Chief Engineers live in this category
        'work_orders': 4.5,

        # Handover: Very common, shift changes happen regularly
        # Add to handover, export handover, view handover
        'handover': 4.2,

        # Faults: Common, equipment issues need attention
        # Report fault, diagnose fault, acknowledge fault
        'faults': 4.0,

        # Inventory: Moderately common
        # Check stock, order parts
        'inventory': 3.5,

        # Documents: Moderately common
        # Upload document, find manual
        'documents': 3.0,

        # Purchasing: Less common
        # Create purchase request, approve PO
        'purchasing': 2.8,

        # Hours of Rest: Less common (once per day per crew member)
        # Log hours, check compliance
        'hours_of_rest': 2.5,

        # Mobile: Least common (specific to mobile app features)
        # Crew list, weather, etc.
        'mobile': 2.0,

        # Unsupported: Not actionable
        # Queries we can't handle
        'unsupported': 0.0
    })

    # Priority order for category disambiguation
    # When multiple categories match with similar confidence,
    # prefer categories earlier in this list.
    #
    # Example: If "create document" matches both 'work_orders' and 'documents'
    # at similar confidence, prefer 'work_orders' (higher priority)
    category_priority: List[str] = field(default_factory=lambda: [
        'work_orders',      # Highest priority (most common, core functionality)
        'handover',
        'faults',
        'inventory',
        'purchasing',
        'documents',
        'hours_of_rest',
        'mobile'            # Lowest priority
    ])

    # ========================================================================
    # OVERLAP RESOLUTION
    # ========================================================================
    #
    # Sometimes two matches overlap in the same text.
    # Example: "create work order for generator maintenance"
    # - Match 1: "create work order" at positions 0-17
    # - Match 2: "work order" at positions 7-17
    # These overlap! Which one should we keep?
    #
    # We score each match and keep the higher-scoring one.

    # Weights for overlap scoring
    # Total should be 1.0 (100%)
    overlap_resolution_weights: Dict[str, float] = field(default_factory=lambda: {

        # Confidence: Higher confidence = better match
        # 50% of the score comes from confidence
        'confidence': 0.5,

        # Span length: Longer matches are more specific
        # "create work order" is more specific than just "order"
        # 30% of the score comes from length
        'span_length': 0.3,

        # Category priority: Some categories are more important
        # 20% of the score comes from category priority
        'category_priority': 0.2
    })

    # Maximum allowed overlap (as fraction of shorter match)
    # If two matches overlap by more than this, they're considered duplicates
    #
    # Example: Match A is 10 chars, Match B is 20 chars
    # They share 5 chars of overlap
    # Overlap ratio = 5/10 = 0.5 (50%)
    # 0.5 > 0.3 threshold → they're overlapping, resolve conflict
    max_overlap_ratio: float = 0.3  # 30% overlap triggers resolution

    # ========================================================================
    # MULTI-ACTION DETECTION
    # ========================================================================
    #
    # Users can request multiple actions in one query.
    # Example: "create work order and add to handover"
    #
    # These settings control how we detect and handle multiple actions.

    # Minimum distance (characters) between matches to consider them separate
    # If matches are too close together, they might be part of the same action
    min_action_distance: int = 3  # At least 3 characters apart

    # Conjunction words that indicate multiple actions
    # When we see these words, expect another action to follow
    # Example: "create work order AND add to handover"
    conjunction_indicators: List[str] = field(default_factory=lambda: [
        'and',          # "create wo AND add to handover"
        'then',         # "create wo THEN export handover"
        'also',         # "create wo, ALSO check stock"
        'plus',         # "create wo PLUS report fault"
        'additionally', # "create wo, ADDITIONALLY upload doc"
        '&',            # "create wo & add to handover"
        '+',            # "create wo + add to handover"
        ',',            # "create wo, add to handover"
        'afterwards',   # "create wo, AFTERWARDS export"
        'after that'    # "create wo, AFTER THAT check stock"
    ])

    # Maximum number of actions to extract from single query
    # Prevents runaway extraction on very long text
    # If user requests more than this, we only return the first N
    max_actions_per_query: int = 5  # Max 5 actions per query

    # ========================================================================
    # PERFORMANCE TUNING
    # ========================================================================
    #
    # Settings that affect speed and resource usage.

    # Enable caching of compiled regex patterns
    # Compiled patterns are faster than compiling on every query
    # Should always be True in production
    enable_pattern_caching: bool = True

    # Enable parallel processing for multiple queries
    # Not needed for single query processing
    # Could be useful for batch processing
    enable_parallel_processing: bool = False

    # Timeout for AI extraction (milliseconds)
    # If AI takes longer than this, give up and use regex/gazetteer result
    # Prevents slow AI from blocking user requests
    ai_extraction_timeout_ms: int = 2000  # 2 second timeout

    # Maximum query length to process (characters)
    # Longer queries are truncated to this length
    # Prevents very long inputs from causing performance issues
    max_query_length: int = 500  # Max 500 characters

    # ========================================================================
    # LOGGING & DEBUGGING
    # ========================================================================
    #
    # Settings for troubleshooting and development.

    # Enable detailed logging
    # Shows what patterns matched, confidence calculations, etc.
    # Turn OFF in production (too verbose)
    enable_debug_logging: bool = False

    # Log all matches (including low-confidence ones)
    # Useful for understanding why certain queries fail
    # Turn OFF in production
    log_all_matches: bool = False

    # Include match metadata in response
    # Adds extra fields like matched_pattern, source, etc.
    # Useful for debugging, not needed in production
    include_match_metadata: bool = False

    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    #
    # Methods that use the config values to make calculations.
    # These encapsulate the logic so other modules don't need to understand
    # how the config works internally.

    def calculate_overlap_score(self, match_a: Dict, match_b: Dict) -> float:
        """
        Calculate overlap score to determine which match to keep.

        === WHEN IS THIS USED? ===
        When two matches overlap in the same text and we need to pick one.

        === HOW IT WORKS ===
        1. Compare confidence (higher = better)
        2. Compare span length (longer = more specific)
        3. Compare category priority (higher priority = better)
        4. Combine using weights

        === RETURN VALUE ===
        Positive number: match_a is better (keep match_a)
        Negative number: match_b is better (keep match_b)
        Zero: They're equal

        Similar to maritime entity_merger.py overlap resolution.

        Args:
            match_a: First match dictionary with confidence, start_pos, end_pos, category
            match_b: Second match dictionary

        Returns:
            Score (positive = A is better, negative = B is better)
        """

        # === CONFIDENCE COMPONENT ===
        # Get confidence of each match (default 0.0 if missing)
        conf_a = match_a.get('confidence', 0.0)
        conf_b = match_b.get('confidence', 0.0)

        # Calculate difference (positive if A is more confident)
        conf_score = conf_a - conf_b

        # === SPAN LENGTH COMPONENT ===
        # Calculate length of each match
        span_a = match_a['end_pos'] - match_a['start_pos']
        span_b = match_b['end_pos'] - match_b['start_pos']

        # Normalize to -1 to +1 range
        # Positive if A is longer (more specific)
        span_score = (span_a - span_b) / max(span_a, span_b, 1)

        # === CATEGORY PRIORITY COMPONENT ===
        # Get category of each match
        cat_a = match_a.get('category', 'unsupported')
        cat_b = match_b.get('category', 'unsupported')

        try:
            # Find priority index (lower index = higher priority)
            priority_a = self.category_priority.index(cat_a)
            priority_b = self.category_priority.index(cat_b)

            # Calculate score (positive if A has higher priority)
            # Note: Lower index = higher priority, so B - A
            cat_score = (priority_b - priority_a) / len(self.category_priority)
        except ValueError:
            # Category not in priority list
            cat_score = 0.0

        # === COMBINE WITH WEIGHTS ===
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

        === WHAT THIS DOES ===
        Returns a number between 0 and 1 representing how important
        this category is relative to others.

        === EXAMPLE ===
        - work_orders has weight 4.5 (highest)
        - get_category_boost('work_orders') returns 1.0 (4.5/4.5)
        - mobile has weight 2.0
        - get_category_boost('mobile') returns 0.44 (2.0/4.5)

        Args:
            category: Category name (e.g., 'work_orders', 'handover')

        Returns:
            Boost multiplier normalized to 0-1 scale
        """
        # Get weight for this category (default 1.0 if not found)
        weight = self.category_weights.get(category, 1.0)

        # Find maximum weight across all categories
        max_weight = max(self.category_weights.values())

        # Normalize to 0-1 scale
        return weight / max_weight

    def should_trigger_ai_fallback(self, best_confidence: float) -> bool:
        """
        Determine if AI fallback should be triggered.

        === WHEN TO USE ===
        After regex/gazetteer extraction, check if AI should be called.

        === LOGIC ===
        If best confidence from regex/gazetteer is below threshold,
        AI might be able to do better.

        Args:
            best_confidence: Confidence of best regex/gazetteer match

        Returns:
            True if AI should be called, False otherwise
        """
        return best_confidence < self.ai_fallback_threshold

    def is_valid_output(self, confidence: float) -> bool:
        """
        Check if a match has sufficient confidence to return to user.

        === WHEN TO USE ===
        Before returning results, check if confidence is high enough.
        If not, return empty result or "unsupported" indicator.

        Args:
            confidence: Confidence score of the match

        Returns:
            True if confidence is high enough, False otherwise
        """
        return confidence >= self.min_output_confidence


# ========================================================================
# PRESET CONFIGURATIONS FOR DIFFERENT ENVIRONMENTS
# ========================================================================
#
# These are pre-configured variants of ExtractionConfig for different use cases.
# Each inherits from ExtractionConfig and overrides specific settings.


class ProductionConfig(ExtractionConfig):
    """
    Production environment: Balanced speed and accuracy.

    === WHEN TO USE ===
    Live deployment serving real users.
    Default configuration for Render/production server.

    === KEY DIFFERENCES FROM DEFAULT ===
    - AI threshold slightly lower (0.75) for better accuracy
    - Higher output confidence (0.70) for fewer false positives
    - Debug logging OFF for performance
    """
    ai_fallback_threshold: float = 0.75  # Trigger AI for ambiguous cases
    min_output_confidence: float = 0.70  # Higher bar for production
    enable_debug_logging: bool = False   # No debug noise in production
    include_match_metadata: bool = False # Cleaner responses


class DevelopmentConfig(ExtractionConfig):
    """
    Development environment: Full logging and metadata.

    === WHEN TO USE ===
    Local development, debugging issues, understanding behavior.

    === KEY DIFFERENCES FROM DEFAULT ===
    - Debug logging ON to see what's happening
    - All matches logged (even low-confidence)
    - Match metadata included in responses
    """
    enable_debug_logging: bool = True    # See all the details
    log_all_matches: bool = True         # Log even failed matches
    include_match_metadata: bool = True  # Include extra fields


class PerformanceConfig(ExtractionConfig):
    """
    Performance-optimized: Minimize AI calls, maximize speed.

    === WHEN TO USE ===
    High-traffic scenarios where speed matters more than accuracy.
    Mobile clients with slow connections.

    === KEY DIFFERENCES FROM DEFAULT ===
    - AI threshold very low (0.50) - rarely call AI
    - Lower output confidence (0.60) - accept more regex matches
    - Strict AI timeout (1 second)
    """
    ai_fallback_threshold: float = 0.50   # Rarely trigger AI (fast)
    min_output_confidence: float = 0.60   # Lower bar to avoid AI
    enable_pattern_caching: bool = True   # Always cache patterns
    ai_extraction_timeout_ms: int = 1000  # Strict 1-second timeout


class AccuracyConfig(ExtractionConfig):
    """
    Accuracy-optimized: More AI usage, stricter thresholds.

    === WHEN TO USE ===
    When accuracy matters more than speed.
    Complex queries that need AI understanding.

    === KEY DIFFERENCES FROM DEFAULT ===
    - AI threshold high (0.85) - often call AI
    - Higher output confidence (0.75) - stricter quality bar
    - Longer AI timeout (3 seconds) - allow more time for AI
    """
    ai_fallback_threshold: float = 0.85   # Trigger AI more often
    min_output_confidence: float = 0.75   # Higher bar for output
    ai_extraction_timeout_ms: int = 3000  # Allow 3 seconds for AI


# ========================================================================
# FACTORY FUNCTION
# ========================================================================
#
# A "factory function" is a function that creates and returns objects.
# This is cleaner than having users import each config class directly.

def get_config(environment: str = 'production') -> ExtractionConfig:
    """
    Factory function to get configuration for specific environment.

    === HOW TO USE ===
    ```python
    config = get_config('production')  # Get production config
    config = get_config('development') # Get development config
    ```

    === AVAILABLE ENVIRONMENTS ===
    - 'production': Balanced for real use (default)
    - 'development': Full logging for debugging
    - 'performance': Fast, fewer AI calls
    - 'accuracy': More AI, higher quality
    - 'default': Base ExtractionConfig

    Args:
        environment: One of the environment names above

    Returns:
        ExtractionConfig instance configured for that environment
    """
    # Dictionary mapping environment names to config classes
    configs = {
        'production': ProductionConfig(),
        'development': DevelopmentConfig(),
        'performance': PerformanceConfig(),
        'accuracy': AccuracyConfig(),
        'default': ExtractionConfig()
    }

    # Return requested config, or default if not found
    # .get(key, default) returns default if key not in dictionary
    return configs.get(environment, configs['default'])


# ========================================================================
# VALIDATION RULES
# ========================================================================
#
# Rules for validating detected actions.
# Helps catch impossible or uncommon action combinations.

class ValidationRules:
    """
    Validation rules for micro-action extraction.

    === WHAT THIS DOES ===
    Provides rules to validate that detected actions make sense.
    Catches errors like "create AND close work order" (impossible).

    === RULE TYPES ===
    1. CONTEXT_REQUIRED: Actions that need additional info
    2. MUTUALLY_EXCLUSIVE: Actions that can't happen together
    3. COMMON_PAIRS: Actions that often happen together

    Similar to maritime extractor's validation logic.
    """

    # =================================================================
    # CONTEXT REQUIRED ACTIONS
    # =================================================================
    #
    # Some actions need specific context to be valid.
    # Without this context, the action doesn't make sense.
    #
    # Key = action name
    # Value = list of entity types that should be present

    CONTEXT_REQUIRED_ACTIONS = {
        # Creating a work order needs to know:
        # - What part/equipment? (otherwise what's the work order for?)
        # - What's the issue? (otherwise why create it?)
        'create_work_order': ['part', 'equipment', 'issue'],

        # Reporting a fault needs:
        # - Fault code OR equipment OR symptom
        'report_fault': ['fault_code', 'equipment', 'symptom'],

        # Creating purchase request needs:
        # - What item to purchase
        # - How many to order
        'create_purchase_request': ['item', 'quantity'],

        # Uploading document needs:
        # - What type of document
        'upload_document': ['document_type'],

        # Logging hours of rest needs:
        # - How many hours
        # - What date
        'log_hours_of_rest': ['hours', 'date']
    }

    # =================================================================
    # MUTUALLY EXCLUSIVE ACTIONS
    # =================================================================
    #
    # Some actions can't both be in the same query.
    # If both are detected, something is wrong.
    #
    # List of (action_a, action_b) tuples

    MUTUALLY_EXCLUSIVE_ACTIONS = [
        # Can't create AND close a work order in same action
        ('create_work_order', 'close_work_order'),

        # Can't export AND clear handover at same time
        ('export_handover', 'clear_handover'),

        # Can't approve AND reject same PO
        ('approve_purchase_order', 'reject_purchase_order')
    ]

    # =================================================================
    # COMMON ACTION PAIRS
    # =================================================================
    #
    # Actions that commonly appear together.
    # If we see an uncommon combination, we might want to verify.

    COMMON_PAIRS = [
        # Create work order and add to handover (shift notification)
        ('create_work_order', 'add_to_handover'),

        # Report fault and create work order to fix it
        ('report_fault', 'create_work_order'),

        # Check if we have stock, then order if not
        ('check_stock', 'create_purchase_request'),

        # Diagnose fault, then report it
        ('diagnose_fault', 'report_fault')
    ]

    @staticmethod
    def validate_action_combination(actions: List[str]) -> Dict[str, any]:
        """
        Validate that detected actions make sense together.

        === WHEN TO USE ===
        After detecting multiple actions in a query,
        validate that the combination is sensible.

        === CHECKS PERFORMED ===
        1. Mutually exclusive: Actions that can't happen together
        2. Uncommon combinations: Actions that rarely occur together
        3. Too many actions: More than 3 actions is suspicious

        Args:
            actions: List of detected action names

        Returns:
            Dictionary with:
            - valid: True if no warnings
            - warnings: List of warning messages
            - suggestions: List of suggestions
        """
        warnings = []
        suggestions = []

        # === CHECK 1: Mutually Exclusive Actions ===
        # If both actions in a pair are present, that's a problem
        for action_a, action_b in ValidationRules.MUTUALLY_EXCLUSIVE_ACTIONS:
            if action_a in actions and action_b in actions:
                warnings.append(
                    f"'{action_a}' and '{action_b}' are mutually exclusive. "
                    f"Please clarify which action you want."
                )

        # === CHECK 2: Uncommon Combinations ===
        # If we have exactly 2 actions that aren't a common pair, warn
        if len(actions) == 2:
            # Check if this pair is in our common pairs list
            if tuple(actions) not in ValidationRules.COMMON_PAIRS:
                suggestions.append(
                    f"Detected: {actions}. This is an uncommon combination. "
                    f"Please confirm this is what you intended."
                )

        # === CHECK 3: Too Many Actions ===
        # More than 3 actions in one query is suspicious
        if len(actions) > 3:
            warnings.append(
                f"Detected {len(actions)} actions in one query. "
                f"Consider breaking this into separate queries for clarity."
            )

        # Return validation result
        return {
            'valid': len(warnings) == 0,  # Valid if no warnings
            'warnings': warnings,
            'suggestions': suggestions
        }


# ========================================================================
# TEST / MAIN
# ========================================================================
#
# This block runs when you execute the file directly:
# python microaction_config.py
#
# It demonstrates how to use the config classes.

if __name__ == '__main__':
    # Print header
    print("Micro-Action Extraction Configuration Test")
    print("=" * 60)

    # === TEST 1: Production Config ===
    prod_config = get_config('production')
    print(f"\n✓ Production Config:")
    print(f"  - AI Fallback Threshold: {prod_config.ai_fallback_threshold}")
    print(f"  - Min Output Confidence: {prod_config.min_output_confidence}")
    print(f"  - Debug Logging: {prod_config.enable_debug_logging}")

    # === TEST 2: Performance Config ===
    perf_config = get_config('performance')
    print(f"\n✓ Performance Config:")
    print(f"  - AI Fallback Threshold: {perf_config.ai_fallback_threshold}")
    print(f"  - AI Timeout: {perf_config.ai_extraction_timeout_ms}ms")

    # === TEST 3: Category Boost ===
    print(f"\n✓ Category Boosts:")
    for category in ['work_orders', 'handover', 'mobile']:
        boost = prod_config.get_category_boost(category)
        print(f"  - {category}: {boost:.2f}")

    # === TEST 4: Validation ===
    print(f"\n✓ Validation Test:")
    test_actions = ['create_work_order', 'close_work_order']
    validation = ValidationRules.validate_action_combination(test_actions)
    print(f"  - Actions: {test_actions}")
    print(f"  - Valid: {validation['valid']}")
    if validation['warnings']:
        print(f"  - Warnings: {validation['warnings']}")

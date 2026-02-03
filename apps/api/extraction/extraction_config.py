#!/usr/bin/env python3
"""
Extraction Pipeline Configuration (Python side)
Centralized, parameterized thresholds and multipliers
Matches JavaScript config for consistency
"""

import os
import json
from typing import Dict

class ExtractionConfig:
    """Centralized configuration for entity extraction pipeline"""

    def __init__(self):
        # Source confidence multipliers (reliability of extraction sources)
        self.source_multipliers = self._load_json_or_default(
            'SOURCE_MULTIPLIERS_JSON',
            {
                'regex': 1.0,
                'gazetteer': 0.95,
                'proper_noun': 0.85,
                'ai': 0.70,
                'fallback_py': 0.90,
                'fuzzy': 0.92,  # Fix #4: Fuzzy brand matching (validated by 80% score cutoff)
                'stitched': 1.0  # Phase 2: Adjacency-stitched compounds (high confidence)
            }
        )

        # Confidence thresholds by entity type
        self.confidence_thresholds = self._load_json_or_default(
            'CONFIDENCE_THRESHOLDS_JSON',
            {
                'equipment': 0.55,  # Fix 2026-02-02: Lowered from 0.70 to allow gazetteer matches (0.64*0.95=0.608)
                'measurement': 0.75,
                'fault_code': 0.70,
                'model': 0.75,
                'org': 0.75,
                'org_ai': 0.85,  # AI-sourced ORGs need higher confidence
                'status': 0.75,
                'symptom': 0.70,  # Fix 2026-02-02: Lowered from 0.80 to catch more symptom extractions
                'system': 0.65,   # Fix 2026-02-02: Lowered from 0.75 to allow system extractions
                'location_on_board': 0.55,  # Fix 2026-02-02: Lowered to allow gazetteer matches
                'person': 0.75,
                'document_type': 0.75,
                'document_id': 0.80,
                'identifier': 0.75,
                'network_id': 0.75,
                'subcomponent': 0.75,
                'date': 0.90,
                'time': 0.90,
                'action': 0.70,
                # Parts Lens - Brand/Manufacturer entity types (PR #69 - commit 772337c)
                # Note: Entity types can be lowercase (from regex_extractor) or uppercase (from capability_composer)
                'brand': 0.35,              # From gazetteer (28,834 brands) - lowercase
                'BRAND': 0.35,              # Uppercase variant
                'equipment_brand': 0.35,    # From ENTITY_EXTRACTION_EXPORT - lowercase
                'EQUIPMENT_BRAND': 0.35,    # Uppercase variant
                'manufacturer': 0.35,       # Core manufacturer names - lowercase
                'MANUFACTURER': 0.35,       # Uppercase variant
                # Receiving Lens entity types (PR #47)
                'po_number': 0.80,
                'invoice_number': 0.80,
                'receiving_id': 0.85,
                'supplier_name': 0.75,
                'delivery_date': 0.85,
                'receiver_name': 0.75,
                'receiving_status': 0.35,  # Fix 2026-02-02: Lowered from 0.75 to allow weight-based gazetteer matches (0.40*0.95=0.38)
                # Shopping List & Inventory Lens (Root Cause #2 Fix - 2026-02-02)
                # These were missing, causing entities to be shadow-filtered by default 0.75 threshold
                'shopping_list_term': 0.55,  # Allows 0.60 confidence matches (lowered for "buy list" etc.)
                'approval_status': 0.55,     # Allows 0.60 confidence matches
                'stock_status': 0.45,        # Fix: Lowered from 0.55 to allow 0.50 confidence gazetteer matches
                'source_type': 0.45,         # Low confidence source types
                # Fix #3: Part/Equipment Type thresholds (2026-02-02)
                # Base weight=2.8 → conf=0.56, was defaulting to 0.75 and filtering out
                # Common terms like "filter", "pump", "valve", "seal" were being discarded
                'part': 0.50,                # Allows 0.56 confidence matches
                'equipment_type': 0.50,      # Allows 0.56 confidence matches
                # Crew & Compliance Lens
                'REST_COMPLIANCE': 0.55,     # Allows 0.60+ confidence matches
                'WARNING_STATUS': 0.55,      # Allows 0.60+ confidence matches
                'WARNING_SEVERITY': 0.80,    # Kept high for accuracy
                # Time references
                'time_ref': 0.70,            # Time-based queries
                # Note: location_on_board threshold defined above at 0.55 (line 43)
                # Removed duplicate 0.70 entry that was overriding it (Fix 2026-02-03)
                # Phase 2: Generic numeric identifiers (2026-02-02)
                'identifier': 0.90,          # High threshold - only confident matches
            }
        )

        # Overlap resolution scoring weights
        # Fix (2026-02-02): Increased span_length weight to favor compound phrases over single words
        # "low stock" should beat "low" even though "low" has higher confidence
        self.overlap_weights = self._load_json_or_default(
            'OVERLAP_WEIGHTS_JSON',
            {
                'adjusted_confidence': 0.30,  # Reduced from 0.5 - confidence less important than specificity
                'span_length_norm': 0.55,     # Increased from 0.3 - longer spans (compounds) win overlaps
                'type_priority': 0.15         # Reduced from 0.2
            }
        )

        # Entity type precedence (higher value = higher priority in overlaps)
        self.type_precedence = self._load_json_or_default(
            'TYPE_PRECEDENCE_JSON',
            {
                'fault_code': 100,
                'model': 90,
                'part_number': 85,
                'equipment': 80,
                'org': 70,
                'measurement': 60,
                'location_on_board': 50,
                'action': 40,
                'status': 30,
                'other': 10
            }
        )

        # Brand expansions (bi-directional mapping)
        self.brand_expansions = self._load_json_or_default(
            'BRAND_EXPANSIONS_JSON',
            {
                'caterpillar': ['cat', 'cat marine', 'caterpillar marine'],
                'cummins': ['qsm', 'cummins marine'],
                'northern lights': ['northern', 'nl'],
                'volvo penta': ['volvo', 'vp'],
                'mtu': ['mtu friedrichshafen'],
                'man': ['man diesel', 'man engines'],
                'yanmar': ['yanmar marine'],
                'kohler': ['kohler power'],
                'onan': ['onan generator', 'cummins onan']
            }
        )

        # Debug mode
        self.debug_mode = os.getenv('DEBUG_EXTRACTION', 'false').lower() == 'true'
        self.enable_reason_codes = os.getenv('ENABLE_REASON_CODES', 'true').lower() == 'true'

    def _load_json_or_default(self, env_var: str, default: Dict) -> Dict:
        """Load JSON from environment variable or use default"""
        value = os.getenv(env_var)
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            print(f"[CONFIG] Warning: Failed to parse {env_var}, using default: {e}")
            return default

    def get_threshold(self, entity_type: str, source: str = None) -> float:
        """Get confidence threshold for entity type and source"""
        # Special case for ORG with AI source
        if entity_type == 'org' and source == 'ai':
            return self.confidence_thresholds.get('org_ai', 0.85)

        return self.confidence_thresholds.get(entity_type, 0.75)

    def get_source_multiplier(self, source: str) -> float:
        """Get source reliability multiplier"""
        return self.source_multipliers.get(source, 0.75)

    def get_type_precedence(self, entity_type: str) -> int:
        """Get type precedence score for overlap resolution"""
        return self.type_precedence.get(entity_type, self.type_precedence.get('other', 10))

    def calculate_overlap_score(self, entity, max_span_length: int = 30) -> float:
        """
        Calculate overlap resolution score for an entity

        Score = w1*adjusted_confidence + w2*span_length_norm + w3*type_priority
        """
        adjusted_conf = getattr(entity, 'adjusted_confidence', entity.confidence if hasattr(entity, 'confidence') else 0)

        span_length = 0
        if hasattr(entity, 'span') and entity.span:
            span_length = entity.span[1] - entity.span[0]

        span_length_norm = min(span_length / max_span_length, 1.0)

        entity_type = getattr(entity, 'type', 'other')
        type_priority = self.get_type_precedence(entity_type) / 100.0

        score = (
            self.overlap_weights['adjusted_confidence'] * adjusted_conf +
            self.overlap_weights['span_length_norm'] * span_length_norm +
            self.overlap_weights['type_priority'] * type_priority
        )

        return score

    def get_snapshot(self) -> Dict:
        """Get configuration snapshot for debugging/health checks"""
        return {
            'source_multipliers': self.source_multipliers,
            'confidence_thresholds': self.confidence_thresholds,
            'overlap_weights': self.overlap_weights,
            'type_precedence': self.type_precedence,
            'debug_mode': self.debug_mode,
            'enable_reason_codes': self.enable_reason_codes
        }


# Global singleton instance
config = ExtractionConfig()

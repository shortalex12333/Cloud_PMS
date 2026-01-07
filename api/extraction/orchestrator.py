#!/usr/bin/env python3
"""
Main Extraction Orchestrator
Coordinates the 5-stage pipeline for entity extraction
"""

import time
import logging
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

from .text_cleaner import TextCleaner
from .regex_extractor import RegexExtractor
from .coverage_controller import CoverageController
from .ai_extractor_openai import AIExtractor
from .entity_merger import EntityMerger

logger = logging.getLogger(__name__)


@dataclass
class ExtractionMetrics:
    """Metrics for extraction performance."""
    total_ms: float = 0
    clean_ms: float = 0
    regex_ms: float = 0
    controller_ms: float = 0
    ai_ms: float = 0
    merge_ms: float = 0
    needs_ai: bool = False
    coverage: float = 0
    ai_invocations: int = 0
    total_requests: int = 0


class ExtractionOrchestrator:
    """
    Orchestrates the full extraction pipeline.
    Stages: Clean → Regex → Controller → AI (conditional) → Merge
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}

        # Initialize pipeline components
        self.cleaner = TextCleaner()
        self.regex_extractor = RegexExtractor()
        self.controller = CoverageController()
        self.ai_extractor = AIExtractor()
        self.merger = EntityMerger(config)

        # Metrics tracking
        self.metrics = ExtractionMetrics()

    def extract(self, text: str) -> Dict:
        """
        Main extraction method - orchestrates the full pipeline.

        Args:
            text: Raw input text

        Returns:
            Dict with schema_version, entities, unknown_term, and metadata
        """
        if not text:
            return self._empty_response()

        start_time = time.time()
        timings = {}

        # Stage 0: Clean and tokenize
        stage_start = time.time()
        cleaned = self.cleaner.clean(text)
        timings['clean'] = (time.time() - stage_start) * 1000

        # Stage 1: Deterministic extraction (regex + gazetteer)
        stage_start = time.time()
        regex_entities, covered_spans = self.regex_extractor.extract(cleaned['normalized'])
        timings['regex'] = (time.time() - stage_start) * 1000

        # Stage 2: Coverage controller decision
        stage_start = time.time()
        decision = self.controller.decide(cleaned, regex_entities, text)
        timings['controller'] = (time.time() - stage_start) * 1000

        # Stage 3: AI residual extraction (conditional)
        ai_entities = []
        unknown_terms = []
        timings['ai'] = 0

        if decision.needs_ai:
            stage_start = time.time()
            ai_result = self.ai_extractor.extract(
                cleaned['normalized'],
                decision.uncovered_spans
            )

            # Handle quality AI extractor's response format
            if isinstance(ai_result, dict):
                if 'entities' in ai_result and isinstance(ai_result['entities'], dict):
                    # Convert dict of entity arrays to list of Entity objects
                    from .regex_extractor import Entity
                    for entity_type, values in ai_result['entities'].items():
                        if isinstance(values, list):
                            for value in values:
                                if value:  # Skip empty values
                                    entity = Entity(
                                        text=str(value),
                                        entity_type=entity_type,
                                        confidence=0.85,  # AI confidence
                                        source='ai',
                                        span=None  # AI doesn't provide spans
                                    )
                                    ai_entities.append(entity)

                unknown_terms = ai_result.get('unknown_term', [])

            timings['ai'] = (time.time() - stage_start) * 1000

            # Update metrics
            self.metrics.ai_invocations += 1

        # Stage 4: Merge and validate
        stage_start = time.time()
        merge_result = self.merger.merge_and_validate(
            regex_entities,
            ai_entities,
            cleaned['normalized']
        )
        timings['merge'] = (time.time() - stage_start) * 1000

        # Stage 5: Shape final response
        entities_by_type = self.merger.group_by_type(merge_result['entities'])

        # New: Per-entity provenance for downstream validation
        # Group detailed entities by type including source, confidence, and span
        entities_provenance: Dict[str, List[Dict]] = {}
        for ent in merge_result['entities']:
            ent_type = ent.type
            if ent_type not in entities_provenance:
                entities_provenance[ent_type] = []
            entities_provenance[ent_type].append({
                'text': ent.text,
                'source': getattr(ent, 'source', 'unknown'),
                'confidence': getattr(ent, 'confidence', 0.0),
                'adjusted_confidence': getattr(ent, 'adjusted_confidence', None),
                'span': ent.span
            })

        # Calculate total time
        timings['total'] = (time.time() - start_time) * 1000

        # Update metrics
        self.metrics.total_requests += 1
        self.metrics.needs_ai = decision.needs_ai
        self.metrics.coverage = decision.coverage

        # Build response
        response = {
            'schema_version': '0.2.2',
            'entities': entities_by_type,
            'entities_provenance': entities_provenance,
            'unknown_term': unknown_terms[:5],  # Max 5
            'metadata': {
                'needs_ai': decision.needs_ai,
                'coverage': round(decision.coverage, 2),
                'latency_ms': timings,
                'provenance': {
                    'source_mix': merge_result['source_mix']
                }
            }
        }

        return response

    def _empty_response(self) -> Dict:
        """Return empty response for empty input."""
        return {
            'schema_version': '0.2.2',
            'entities': {},
            'unknown_term': [],
            'metadata': {
                'needs_ai': False,
                'coverage': 1.0,
                'latency_ms': {
                    'total': 0,
                    'clean': 0,
                    'regex': 0,
                    'controller': 0,
                    'ai': 0,
                    'merge': 0
                },
                'provenance': {
                    'source_mix': {'regex': 0, 'gazetteer': 0, 'ai': 0}
                }
            }
        }

    def get_metrics(self) -> Dict:
        """Get extraction metrics."""
        ai_rate = (self.metrics.ai_invocations / max(1, self.metrics.total_requests))

        return {
            'total_requests': self.metrics.total_requests,
            'ai_invocations': self.metrics.ai_invocations,
            'ai_invocation_rate': round(ai_rate, 3),
            'average_coverage': round(self.metrics.coverage, 2)
        }

    def health_check(self) -> Dict:
        """Check health of all components."""
        health = {
            'ok': True,
            'components': {
                'cleaner': 'ok',
                'regex_extractor': 'ok',
                'controller': 'ok',
                'ai_extractor': 'unavailable',
                'merger': 'ok'
            }
        }

        # Check AI availability
        if self.ai_extractor.is_available():
            health['components']['ai_extractor'] = 'ok'

        # Overall health
        if health['components']['ai_extractor'] == 'unavailable':
            health['warning'] = 'AI extractor unavailable - using deterministic only'

        return health

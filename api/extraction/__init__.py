"""
Extraction Module
=================
5-stage extraction pipeline from entity-extraction-api branch.

Stages:
1. text_cleaner - Normalize input
2. regex_extractor - Deterministic patterns
3. coverage_controller - AI decision gate
4. ai_extractor_openai - GPT fallback
5. entity_merger - Combine results
"""

from .orchestrator import ExtractionOrchestrator
from .text_cleaner import TextCleaner
from .regex_extractor import RegexExtractor, Entity
from .coverage_controller import CoverageController, CoverageDecision
from .ai_extractor_openai import AIExtractor
from .entity_merger import EntityMerger
from .extraction_config import config, ExtractionConfig

__all__ = [
    'ExtractionOrchestrator',
    'TextCleaner',
    'RegexExtractor',
    'Entity',
    'CoverageController',
    'CoverageDecision',
    'AIExtractor',
    'EntityMerger',
    'config',
    'ExtractionConfig',
]

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

Additional modules:
- action_detector - Detect user actions/intents (formerly module_a_action_detector)
- entity_extractor - Extract maritime entities (formerly module_b_entity_extractor)
- gpt_extractor - GPT-based extraction (formerly root gpt_extractor)
"""

from .orchestrator import ExtractionOrchestrator
from .text_cleaner import TextCleaner
from .regex_extractor import RegexExtractor, Entity
from .coverage_controller import CoverageController, CoverageDecision
from .ai_extractor_openai import AIExtractor
from .entity_merger import EntityMerger
from .extraction_config import config, ExtractionConfig

# Action detector (formerly module_a_action_detector)
from .action_detector import (
    ActionDetection,
    StrictMicroActionDetector,
    get_detector,
)
# Alias for backward compatibility
ActionDetector = StrictMicroActionDetector

# Entity extractor (formerly module_b_entity_extractor)
from .entity_extractor import (
    EntityDetection,
    MaritimeEntityExtractor,
    get_extractor,
)

# GPT extractor (formerly root gpt_extractor)
from .gpt_extractor import (
    ExtractedEntity,
    NewTerm,
    ExtractionResult,
    GPTExtractor,
    get_gpt_extractor,
)

__all__ = [
    # Pipeline components
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
    # Action detector
    'ActionDetection',
    'StrictMicroActionDetector',
    'ActionDetector',  # Alias for backward compatibility
    'get_detector',
    # Entity extractor
    'EntityDetection',
    'MaritimeEntityExtractor',
    'get_extractor',
    # GPT extractor
    'ExtractedEntity',
    'NewTerm',
    'ExtractionResult',
    'GPTExtractor',
    'get_gpt_extractor',
]

"""
CelesteOS Email Watcher Services

Background email processing services for the Email Watcher system.
"""

from .rate_limiter import MicrosoftRateLimiter
from .token_extractor import TokenExtractor
from .candidate_finder import CandidateFinder
from .scoring_engine import ScoringEngine
from .linking_ladder import LinkingLadder
from .email_sync_service import EmailSyncService
from .action_surfacing import surface_actions_for_query, get_fusion_params_for_query, build_action_response
from .domain_microactions import (
    detect_domain_from_query,
    detect_domain_with_confidence,
    detect_intent_from_query,
    detect_intent_with_confidence,
    get_microactions_for_query,
    get_detection_context,
    extract_filters_from_query,
    DOMAIN_KEYWORDS,
)
from .intent_parser import IntentParser, ParsedIntent, parse_and_route, route_query

__all__ = [
    'MicrosoftRateLimiter',
    'TokenExtractor',
    'CandidateFinder',
    'ScoringEngine',
    'LinkingLadder',
    'EmailSyncService',
    # Action surfacing
    'surface_actions_for_query',
    'get_fusion_params_for_query',
    'build_action_response',
    # Domain microactions
    'detect_domain_from_query',
    'detect_domain_with_confidence',
    'detect_intent_from_query',
    'detect_intent_with_confidence',
    'get_microactions_for_query',
    'get_detection_context',
    'extract_filters_from_query',
    'DOMAIN_KEYWORDS',
    # Intent parser
    'IntentParser',
    'ParsedIntent',
    'parse_and_route',
    'route_query',
]

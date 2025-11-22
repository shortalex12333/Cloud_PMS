"""
Data models for CelesteOS Search Engine
"""
from .requests import SearchRequest, BatchSearchRequest
from .responses import (
    SearchResponse,
    ResultCard,
    MicroAction,
    EntityExtractionResult,
    IntentDetectionResult,
    IntentType,
    CardType
)
from .card import (
    SearchResultCard,
    CardType as CanonicalCardType,
    CardMetadata,
    SourceLabel,
    MicroAction as CanonicalMicroAction
)
from .micro_action_catalogue import (
    ActionId,
    ACTION_CATALOGUE,
    get_actions_for_card
)

__all__ = [
    # Request/Response
    "SearchRequest",
    "BatchSearchRequest",
    "SearchResponse",
    # Legacy card (for backward compatibility)
    "ResultCard",
    "MicroAction",
    # Canonical card
    "SearchResultCard",
    "CanonicalCardType",
    "CardMetadata",
    "SourceLabel",
    "CanonicalMicroAction",
    # Entities/Intent
    "EntityExtractionResult",
    "IntentDetectionResult",
    "IntentType",
    "CardType",
    # Micro-actions
    "ActionId",
    "ACTION_CATALOGUE",
    "get_actions_for_card",
]

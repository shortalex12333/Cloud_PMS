"""
Search Orchestrator - Main Entry Point
========================================

The unified entry point for the Search Orchestration Layer.

Pipeline:
    Input (SurfaceContext)
        ↓
    Intent Parser (existing) → intent_family
        ↓
    Entity Extraction (existing) → entities
        ↓
    Term Classification (NEW) → classification
        ↓
    Prepare Module (NEW) → RetrievalPlan
        ↓
    Return plan for execution

This orchestrator:
    - Does NOT execute queries (that's downstream)
    - Does NOT modify data
    - ONLY builds deterministic, explainable plans
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import uuid

from .surface_state import SurfaceState, SurfaceContext
from .retrieval_plan import RetrievalPlan
from .term_classifier import TermClassifier, TermClassification
from .prepare_module import PrepareModule

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """
    Complete result from orchestration.
    Contains plan + metadata for downstream execution.
    """
    plan: RetrievalPlan
    classification: TermClassification
    context: SurfaceContext
    intent_family: Optional[str]
    orchestration_time_ms: float
    request_id: str

    def get_trust_payload(self) -> Dict[str, Any]:
        """Small payload for frontend trust display."""
        return {
            'request_id': self.request_id,
            'path': self.plan.path.value,
            'scopes': self.plan.allowed_scopes,
            'time_window_days': self.plan.time_window.days,
            'used_vector': self.plan.is_vector_involved(),
            'explain': self.plan.explain,
            'intent': self.intent_family,
        }

    def get_debug_payload(self) -> Dict[str, Any]:
        """Full debug payload for server-side or debug=true."""
        return {
            'request_id': self.request_id,
            'orchestration_time_ms': self.orchestration_time_ms,
            'context': self.context.to_dict(),
            'classification': self.classification.to_dict(),
            'plan': self.plan.get_debug_payload(),
            'intent_family': self.intent_family,
        }


class SearchOrchestrator:
    """
    Main orchestrator. Coordinates classification and plan building.

    Usage:
        orchestrator = SearchOrchestrator()

        result = orchestrator.orchestrate(
            surface_state=SurfaceState.SEARCH,
            yacht_id="...",
            user_id="...",
            query_text="main engine overheating",
        )

        plan = result.plan
        # Execute plan downstream...
    """

    def __init__(
        self,
        intent_parser=None,
        entity_extractor=None,
    ):
        """
        Initialize orchestrator.

        Args:
            intent_parser: Optional intent parser (uses existing if provided)
            entity_extractor: Optional entity extractor (uses existing if provided)
        """
        self.prepare_module = PrepareModule()
        self.intent_parser = intent_parser
        self.entity_extractor = entity_extractor

    def orchestrate(
        self,
        surface_state: SurfaceState,
        yacht_id: str,
        user_id: str,
        query_text: str = "",
        open_entity_type: str = None,
        open_entity_id: str = None,
        open_thread_id: str = None,
        email_direction_bias: str = "inbound",
        debug_mode: bool = False,
        pre_extracted_entities: List[Dict] = None,
        pre_parsed_intent: str = None,
    ) -> OrchestrationResult:
        """
        Main orchestration entry point.

        Args:
            surface_state: Current UI surface state
            yacht_id: Yacht ID (from auth, never trust client)
            user_id: User ID (from auth)
            query_text: User query text (may be empty)
            open_entity_type: Type of currently open entity
            open_entity_id: ID of currently open entity
            open_thread_id: ID of open email thread
            email_direction_bias: 'inbound' or 'outbound' (frontend default)
            debug_mode: Include full debug payload
            pre_extracted_entities: Skip extraction if provided
            pre_parsed_intent: Skip intent parsing if provided

        Returns:
            OrchestrationResult with plan and metadata
        """
        start_time = datetime.utcnow()
        request_id = str(uuid.uuid4())[:12]

        logger.info(f"[Orchestrator:{request_id}] Starting: state={surface_state.value}, "
                    f"query='{query_text[:50]}...' if query_text else '(empty)'")

        # Build context
        context = SurfaceContext(
            surface_state=surface_state,
            yacht_id=yacht_id,
            user_id=user_id,
            query_text=query_text,
            open_entity_type=open_entity_type,
            open_entity_id=open_entity_id,
            open_thread_id=open_thread_id,
            email_direction_bias=email_direction_bias,
            request_id=request_id,
            debug_mode=debug_mode,
        )

        # Step 1: Parse intent (if not pre-provided)
        intent_family = pre_parsed_intent
        if not intent_family and self.intent_parser and query_text.strip():
            try:
                intent_result = self.intent_parser.parse(query_text)
                intent_family = intent_result.get('intent_family')
            except Exception as e:
                logger.warning(f"[Orchestrator:{request_id}] Intent parsing failed: {e}")

        # Step 2: Extract entities (if not pre-provided)
        extracted_entities = pre_extracted_entities or []
        if not extracted_entities and self.entity_extractor and query_text.strip():
            try:
                extraction_result = self.entity_extractor.extract(query_text)
                extracted_entities = extraction_result.get('entities', [])
            except Exception as e:
                logger.warning(f"[Orchestrator:{request_id}] Entity extraction failed: {e}")

        # Step 3: Classify and prepare
        plan = self.prepare_module.prepare(
            context=context,
            extracted_entities=extracted_entities,
            intent_family=intent_family,
        )

        # Get classification for result
        classification = self.prepare_module.term_classifier.classify(
            context=context,
            extracted_entities=extracted_entities,
            intent_family=intent_family,
        )

        # Calculate timing
        end_time = datetime.utcnow()
        orchestration_time_ms = (end_time - start_time).total_seconds() * 1000

        logger.info(f"[Orchestrator:{request_id}] Complete: path={plan.path.value}, "
                    f"time={orchestration_time_ms:.1f}ms")

        return OrchestrationResult(
            plan=plan,
            classification=classification,
            context=context,
            intent_family=intent_family,
            orchestration_time_ms=orchestration_time_ms,
            request_id=request_id,
        )

    def orchestrate_from_request(
        self,
        request_data: Dict[str, Any],
        yacht_id: str,
        user_id: str,
    ) -> OrchestrationResult:
        """
        Convenience method to orchestrate from a request dict.

        Expected request_data keys:
            - query_text (str)
            - surface_state (str)
            - open_entity_type (str, optional)
            - open_entity_id (str, optional)
            - open_thread_id (str, optional)
            - debug (bool, optional)
        """
        surface_state_str = request_data.get('surface_state', 'search')
        try:
            surface_state = SurfaceState(surface_state_str)
        except ValueError:
            surface_state = SurfaceState.SEARCH

        return self.orchestrate(
            surface_state=surface_state,
            yacht_id=yacht_id,
            user_id=user_id,
            query_text=request_data.get('query_text', ''),
            open_entity_type=request_data.get('open_entity_type'),
            open_entity_id=request_data.get('open_entity_id'),
            open_thread_id=request_data.get('open_thread_id'),
            email_direction_bias=request_data.get('direction_bias', 'inbound'),
            debug_mode=request_data.get('debug', False),
        )


# =============================================================================
# Factory function for use with existing pipeline
# =============================================================================

def create_orchestrator(
    intent_parser=None,
    entity_extractor=None,
) -> SearchOrchestrator:
    """
    Factory function to create orchestrator with optional existing components.

    Usage in pipeline_service.py:
        from orchestration import create_orchestrator
        from intent_parser import IntentParser
        from module_b_entity_extractor import get_extractor

        orchestrator = create_orchestrator(
            intent_parser=IntentParser(),
            entity_extractor=get_extractor(),
        )
    """
    return SearchOrchestrator(
        intent_parser=intent_parser,
        entity_extractor=entity_extractor,
    )

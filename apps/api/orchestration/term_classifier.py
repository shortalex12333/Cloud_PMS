"""
Term Classifier - Deterministic Term Classification
=====================================================

Classifies extracted entities and query terms into retrieval buckets.
Decides SQL vs Vector vs Hybrid based on term types.

Term Types (LOCKED):
    ENTITY - Concrete objects with IDs (WO-123, Generator #1)
    DOMAIN - Scope hints (emails, faults, parts)
    TIME - Temporal bounds (today, last week, 30 days)
    ACTION - Verbs (show, link, create, diagnose)
    FREE_TEXT - Semantic residue (everything else)

This classification is:
    - Deterministic (same input → same output)
    - Testable (unit tests for every rule)
    - Logged (classification decisions recorded)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import re
import logging

from .surface_state import SurfaceState, SurfaceContext
from .retrieval_plan import RetrievalPath

logger = logging.getLogger(__name__)


class TermType(Enum):
    """Locked term types for classification."""
    ENTITY = "entity"       # Concrete object with ID
    DOMAIN = "domain"       # Scope hint
    TIME = "time"           # Temporal bound
    ACTION = "action"       # Verb/intent
    FREE_TEXT = "free_text" # Semantic residue


@dataclass
class ClassifiedTerm:
    """A single classified term."""
    text: str
    term_type: TermType
    confidence: float = 1.0
    resolved_id: Optional[str] = None  # If ENTITY and resolved
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TermClassification:
    """Complete classification result."""
    terms: List[ClassifiedTerm]
    primary_path: RetrievalPath
    allowed_scopes: List[str]
    time_window_days: Optional[int] = None
    has_resolved_entities: bool = False
    classification_reason: str = ""

    def get_entities(self) -> List[ClassifiedTerm]:
        return [t for t in self.terms if t.term_type == TermType.ENTITY]

    def get_domains(self) -> List[ClassifiedTerm]:
        return [t for t in self.terms if t.term_type == TermType.DOMAIN]

    def get_free_text(self) -> List[ClassifiedTerm]:
        return [t for t in self.terms if t.term_type == TermType.FREE_TEXT]

    def has_entities(self) -> bool:
        return any(t.term_type == TermType.ENTITY for t in self.terms)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'terms': [
                {'text': t.text, 'type': t.term_type.value, 'confidence': t.confidence}
                for t in self.terms
            ],
            'primary_path': self.primary_path.value,
            'allowed_scopes': self.allowed_scopes,
            'time_window_days': self.time_window_days,
            'has_resolved_entities': self.has_resolved_entities,
            'classification_reason': self.classification_reason,
        }


class TermClassifier:
    """
    Deterministic term classifier.
    Converts extracted entities + text into retrieval intent.
    """

    # Domain keywords → scope mapping
    DOMAIN_KEYWORDS = {
        'email': ['emails'],
        'emails': ['emails'],
        'mail': ['emails'],
        'inbox': ['emails'],
        'message': ['emails'],
        'messages': ['emails'],
        'work order': ['work_orders'],
        'work orders': ['work_orders'],
        'wo': ['work_orders'],
        'task': ['work_orders'],
        'tasks': ['work_orders'],
        'equipment': ['equipment'],
        'machine': ['equipment'],
        'engine': ['equipment'],
        'generator': ['equipment'],
        'part': ['parts'],
        'parts': ['parts'],
        'spare': ['parts'],
        'spares': ['parts'],
        'inventory': ['parts'],
        'stock': ['parts'],
        'low stock': ['parts'],
        'out of stock': ['parts'],
        'stock level': ['parts'],
        # Common part types (Inventory Lens - Finish Line)
        'filter': ['parts'],
        'oil filter': ['parts'],
        'fuel filter': ['parts'],
        'air filter': ['parts'],
        'hydraulic filter': ['parts'],
        'bearing': ['parts'],
        'bearings': ['parts'],
        'gasket': ['parts'],
        'gaskets': ['parts'],
        'seal': ['parts'],
        'seals': ['parts'],
        'o-ring': ['parts'],
        'o-rings': ['parts'],
        'belt': ['parts'],
        'belts': ['parts'],
        'hose': ['parts'],
        'hoses': ['parts'],
        'fitting': ['parts'],
        'fittings': ['parts'],
        'valve': ['parts'],
        'valves': ['parts'],
        'fault': ['faults'],
        'faults': ['faults'],
        'error': ['faults'],
        'alarm': ['faults'],
        'document': ['documents'],
        'documents': ['documents'],
        'manual': ['documents'],
        'manuals': ['documents'],
        'schematic': ['documents'],
        # Shopping List keywords
        'shopping list': ['shopping_list'],
        'shopping': ['shopping_list'],
        'requisition': ['shopping_list'],
        'requisitions': ['shopping_list'],
        'procurement': ['shopping_list'],
        'candidate part': ['shopping_list'],
        'candidate parts': ['shopping_list'],
        'buy list': ['shopping_list'],
        'purchase list': ['shopping_list'],
        'pending approval': ['shopping_list'],
        'needs approval': ['shopping_list'],
        'need approval': ['shopping_list'],
        'awaiting approval': ['shopping_list'],
    }

    # Time keywords → days mapping
    TIME_KEYWORDS = {
        'today': 1,
        'yesterday': 2,
        'this week': 7,
        'last week': 14,
        'this month': 30,
        'last month': 60,
        'recent': 7,
        'recently': 7,
        'last 7 days': 7,
        'last 30 days': 30,
        'last 90 days': 90,
    }

    # Action verbs
    ACTION_KEYWORDS = {
        'show', 'find', 'search', 'get', 'list', 'view',
        'create', 'add', 'new', 'make',
        'update', 'edit', 'modify', 'change',
        'delete', 'remove',
        'diagnose', 'troubleshoot', 'fix',
        'link', 'connect', 'attach',
        'order', 'request', 'purchase',
    }

    # Entity ID patterns
    ENTITY_PATTERNS = [
        (r'\bWO[-#]?\d{1,6}\b', 'work_order'),
        (r'\bPO[-#]?\d{1,6}\b', 'purchase_order'),
        (r'\bEQ[-#]?\d{1,6}\b', 'equipment'),
        (r'\bFAULT[-#]?\d{1,6}\b', 'fault'),
        (r'\b[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}\b', 'uuid'),
    ]

    def __init__(self):
        self._compiled_patterns = [
            (re.compile(p, re.IGNORECASE), t) for p, t in self.ENTITY_PATTERNS
        ]

    def classify(
        self,
        context: SurfaceContext,
        extracted_entities: List[Dict[str, Any]] = None,
        intent_family: str = None,
    ) -> TermClassification:
        """
        Main classification entry point.

        Args:
            context: Surface context with query and state
            extracted_entities: Entities from extraction pipeline
            intent_family: Intent from intent parser

        Returns:
            TermClassification with path, scopes, and classified terms
        """
        extracted_entities = extracted_entities or []
        terms: List[ClassifiedTerm] = []

        # Step 1: Check for system-triggered (no query)
        if context.is_system_triggered():
            return self._handle_system_triggered(context)

        query = context.query_text.lower().strip()

        # Step 2: Extract entity IDs from query
        entity_terms = self._extract_entity_ids(query)
        terms.extend(entity_terms)

        # Step 3: Add pre-extracted entities
        for ent in extracted_entities:
            if ent.get('entity_id') or ent.get('resolved_id'):
                terms.append(ClassifiedTerm(
                    text=ent.get('canonical', ent.get('value', '')),
                    term_type=TermType.ENTITY,
                    confidence=ent.get('confidence', 0.8),
                    resolved_id=ent.get('entity_id') or ent.get('resolved_id'),
                    metadata={'entity_type': ent.get('type')},
                ))

        # Step 4: Extract domain hints
        domain_terms, scopes = self._extract_domains(query)
        terms.extend(domain_terms)

        # Step 5: Extract time bounds
        time_terms, time_days = self._extract_time(query)
        terms.extend(time_terms)

        # Step 6: Extract action verbs
        action_terms = self._extract_actions(query)
        terms.extend(action_terms)

        # Step 7: Remaining text is FREE_TEXT
        free_text = self._extract_free_text(query, terms)
        if free_text:
            terms.append(ClassifiedTerm(
                text=free_text,
                term_type=TermType.FREE_TEXT,
                confidence=1.0,
            ))

        # Step 8: Determine retrieval path
        path, reason = self._determine_path(context, terms, intent_family)

        # Step 9: Determine scopes
        if not scopes:
            from .surface_state import get_default_scopes
            scopes = get_default_scopes(context.surface_state)

        has_resolved = any(t.resolved_id for t in terms if t.term_type == TermType.ENTITY)

        return TermClassification(
            terms=terms,
            primary_path=path,
            allowed_scopes=scopes,
            time_window_days=time_days,
            has_resolved_entities=has_resolved,
            classification_reason=reason,
        )

    def _handle_system_triggered(self, context: SurfaceContext) -> TermClassification:
        """Handle system-triggered queries (inbox fetch, etc.)."""
        if context.surface_state == SurfaceState.EMAIL_INBOX:
            return TermClassification(
                terms=[],
                primary_path=RetrievalPath.EMAIL_INBOX,
                allowed_scopes=['emails'],
                time_window_days=30,
                has_resolved_entities=False,
                classification_reason="System-triggered inbox fetch",
            )

        # Default for other system-triggered states
        from .surface_state import get_default_scopes
        return TermClassification(
            terms=[],
            primary_path=RetrievalPath.SQL_ONLY,
            allowed_scopes=get_default_scopes(context.surface_state),
            time_window_days=90,
            has_resolved_entities=False,
            classification_reason="System-triggered default",
        )

    def _extract_entity_ids(self, query: str) -> List[ClassifiedTerm]:
        """Extract entity IDs using regex patterns."""
        terms = []
        for pattern, entity_type in self._compiled_patterns:
            for match in pattern.finditer(query):
                terms.append(ClassifiedTerm(
                    text=match.group(),
                    term_type=TermType.ENTITY,
                    confidence=0.95,
                    metadata={'pattern_type': entity_type},
                ))
        return terms

    def _extract_domains(self, query: str) -> Tuple[List[ClassifiedTerm], List[str]]:
        """Extract domain hints from query."""
        terms = []
        scopes = []
        for keyword, scope_list in self.DOMAIN_KEYWORDS.items():
            if keyword in query:
                terms.append(ClassifiedTerm(
                    text=keyword,
                    term_type=TermType.DOMAIN,
                    confidence=0.9,
                ))
                scopes.extend(scope_list)
        # Deduplicate while preserving order, with shopping_list prioritized
        # when present (it indicates specific procurement intent)
        unique_scopes = list(dict.fromkeys(scopes))
        if 'shopping_list' in unique_scopes and unique_scopes[0] != 'shopping_list':
            unique_scopes.remove('shopping_list')
            unique_scopes.insert(0, 'shopping_list')
        return terms, unique_scopes

    def _extract_time(self, query: str) -> Tuple[List[ClassifiedTerm], Optional[int]]:
        """Extract time bounds from query."""
        for keyword, days in self.TIME_KEYWORDS.items():
            if keyword in query:
                return [ClassifiedTerm(
                    text=keyword,
                    term_type=TermType.TIME,
                    confidence=0.9,
                    metadata={'days': days},
                )], days
        return [], None

    def _extract_actions(self, query: str) -> List[ClassifiedTerm]:
        """Extract action verbs from query."""
        terms = []
        words = query.split()
        for word in words:
            if word in self.ACTION_KEYWORDS:
                terms.append(ClassifiedTerm(
                    text=word,
                    term_type=TermType.ACTION,
                    confidence=0.85,
                ))
        return terms

    def _extract_free_text(self, query: str, classified: List[ClassifiedTerm]) -> str:
        """Get remaining unclassified text."""
        remaining = query
        for term in classified:
            remaining = remaining.replace(term.text.lower(), ' ')
        # Clean up
        remaining = ' '.join(remaining.split())
        return remaining.strip()

    def _determine_path(
        self,
        context: SurfaceContext,
        terms: List[ClassifiedTerm],
        intent_family: str = None,
    ) -> Tuple[RetrievalPath, str]:
        """
        Determine retrieval path based on classification.
        This is the core decision tree.
        """
        # Rule 1: System-triggered inbox
        if context.surface_state == SurfaceState.EMAIL_INBOX and not context.query_text.strip():
            return RetrievalPath.EMAIL_INBOX, "Inbox fetch (no query)"

        # Rule 2: Email search surface
        if context.surface_state == SurfaceState.EMAIL_SEARCH:
            return RetrievalPath.EMAIL_SEARCH, "Email search surface"

        # Rule 3: Has resolved entity IDs → SQL first
        resolved_entities = [t for t in terms if t.term_type == TermType.ENTITY and t.resolved_id]
        if resolved_entities:
            return RetrievalPath.SQL_ONLY, f"Resolved entity IDs: {len(resolved_entities)}"

        # Rule 4: Has pattern-matched entity IDs → SQL first
        pattern_entities = [t for t in terms if t.term_type == TermType.ENTITY]
        if pattern_entities:
            return RetrievalPath.SQL_ONLY, f"Pattern-matched entity IDs: {len(pattern_entities)}"

        # Rule 5: Action execution intent → SQL only
        if intent_family in ('EXECUTE_ACTION', 'CREATE', 'UPDATE', 'DELETE'):
            return RetrievalPath.SQL_ONLY, f"Action intent: {intent_family}"

        # Rule 6: Has free text → Hybrid
        free_text = [t for t in terms if t.term_type == TermType.FREE_TEXT]
        if free_text and any(len(t.text) > 3 for t in free_text):
            return RetrievalPath.HYBRID, "Free text requires semantic search"

        # Rule 7: Domain-bounded with no free text → SQL
        domain_terms = [t for t in terms if t.term_type == TermType.DOMAIN]
        if domain_terms and not free_text:
            return RetrievalPath.SQL_ONLY, "Domain-bounded, no semantic content"

        # Default: Hybrid
        return RetrievalPath.HYBRID, "Default hybrid search"

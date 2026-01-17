"""
Search Orchestration Layer
===========================

Deterministic query routing between extraction and execution.
Decides SQL vs Vector vs Hybrid based on surface state, intent, and entities.

Modules:
    - surface_state: UI state machine (single URL)
    - term_classifier: Classify terms into retrieval buckets
    - prepare_module: Build RetrievalPlan
    - email_retrieval: Email-specific retrieval logic
    - ranking_recipes: Concrete ranking weights
    - retrieval_plan: Data structures
    - search_orchestrator: Main entry point
"""

from .surface_state import SurfaceState, SurfaceContext
from .retrieval_plan import RetrievalPlan, RetrievalPath, TimeWindow
from .term_classifier import TermClassifier, TermType
from .ranking_recipes import RANKING_RECIPES, get_ranking_recipe
from .prepare_module import PrepareModule
from .email_retrieval import EmailRetrieval
from .search_orchestrator import SearchOrchestrator
from .executor import PlanExecutor, ExecutionResult

__all__ = [
    'SurfaceState',
    'SurfaceContext',
    'RetrievalPlan',
    'RetrievalPath',
    'TimeWindow',
    'TermClassifier',
    'TermType',
    'RANKING_RECIPES',
    'get_ranking_recipe',
    'PrepareModule',
    'EmailRetrieval',
    'SearchOrchestrator',
    'PlanExecutor',
    'ExecutionResult',
]

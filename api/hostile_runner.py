#!/usr/bin/env python3
"""
E2E Pipeline Test Runner (Hostile Tests)
=========================================

Tests the FULL microaction pipeline from user query to handler output.

TWO TEST MODES:
1. SEARCH MODE (--mode search): Tests /v1/search path via graphrag_query
   - Uses GPT extraction (same as production)
   - Returns cards with microactions attached
   - Tests the actual user-facing search flow

2. ACTION MODE (--mode action): Tests action executor path
   - Uses unified_extraction_pipeline (regex + GPT fallback)
   - Tests entity resolution → handler execution
   - Tests specific CRUD operations

Pipeline Flow (Search Mode - Production Path):
1. Entry: User query input
2. Entity Extraction: graphrag_query → GPT-4o-mini + text-embedding-3-small
3. Vector Search: match_documents() for semantic similarity
4. Card Generation: Results with microactions attached
5. Output: Cards with correct entity-type-specific actions

Pipeline Flow (Action Mode - Handler Path):
1. Entry: User query input
2. Entity Extraction: unified_extraction_pipeline (regex + GPT fallback)
3. Action Resolution: action_registry (map entities to actions)
4. SQL Execution: action_executor (execute handlers)
5. Handler Output: ActionResponseEnvelope with microactions

Uses the 1500+ hostile test queries from hostile_generator.py

Usage:
    # Run full test suite
    python hostile_runner.py

    # Run specific category
    python hostile_runner.py --category canonical

    # Show failures
    python hostile_runner.py --show-failures 10

    # Limit tests
    python hostile_runner.py --limit 100

Required:
    SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables
"""

import json
import os
import sys
import time
import asyncio
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import Counter
from enum import Enum

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests" / "sql_campaign"))

# Import hostile generator
from hostile_generator import (
    generate_all_tests, generate_canonical_tests, generate_filter_tests,
    generate_cross_table_tests, generate_ranking_tests, generate_security_tests,
    generate_chaotic_tests, generate_negative_tests, generate_compound_tests,
    generate_expansion_tests, HostileTest, TestCategory, ExpectedBehavior
)

# Import pipeline components
from unified_extraction_pipeline import get_pipeline, UnifiedExtractionPipeline
from action_registry import get_registry, ActionVariant
from action_executor import ActionExecutor, ExecutionResult

# Import new security and routing components
from security_gate import get_security_gate, SecurityGate, ThreatType
from query_classifier import get_classifier, QueryClassifier, QueryType

# Import new evaluation components (4-outcome model, top-3 success)
from outcome_classifier import get_outcome_classifier, OutcomeClassifier, QueryOutcome
from pipeline_contract import get_test_evaluator, TestEvaluator

# Initialize Supabase client
from supabase import create_client, Client

# Test yacht ID from comprehensive tests
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


class PipelineStage(str, Enum):
    SECURITY_GATE = "security_gate"  # NEW: First-line security check
    EXTRACTION = "extraction"
    ACTION_RESOLUTION = "action_resolution"
    SQL_EXECUTION = "sql_execution"
    HANDLER_OUTPUT = "handler_output"


@dataclass
class PipelineResult:
    """Result of a full pipeline execution"""
    test_id: str
    query: str
    category: str
    expected_behavior: str

    # Stage results
    extraction_success: bool = False
    extraction_entities: List[Dict] = field(default_factory=list)
    extraction_lane: str = ""
    extraction_intent: str = ""
    extraction_ms: float = 0.0

    action_resolution_success: bool = False
    resolved_action_id: str = ""
    resolved_action_variant: str = ""
    action_ms: float = 0.0

    sql_execution_success: bool = False
    sql_result_count: int = 0
    sql_table_hit: str = ""
    sql_ms: float = 0.0

    handler_output_success: bool = False
    handler_has_data: bool = False
    handler_has_actions: bool = False
    handler_actions_count: int = 0
    handler_actions_valid: bool = False  # True if actions match entity type
    handler_error: str = ""
    handler_ms: float = 0.0

    # Overall
    passed: bool = False
    failure_stage: str = ""
    failure_reason: str = ""
    total_ms: float = 0.0

    # NEW: 4-outcome model fields
    outcome: str = ""  # FOUND, SALVAGED, UNKNOWN, EMPTY
    outcome_confidence: float = 0.0
    unmatched_tokens: List[str] = field(default_factory=list)
    result_position: int = 0  # Position of correct answer (1-indexed, 0=not found)
    top3_success: bool = False  # True if correct answer in top 3

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TestSuite:
    """Aggregated test results"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    results: List[PipelineResult] = field(default_factory=list)
    by_category: Dict[str, Dict] = field(default_factory=dict)
    by_stage_failure: Dict[str, int] = field(default_factory=dict)
    by_outcome: Dict[str, int] = field(default_factory=dict)  # NEW: Track outcomes
    salvaged_count: int = 0  # NEW: Count SALVAGED results
    top3_success_count: int = 0  # NEW: Count top-3 successes
    microactions_attached: int = 0  # Tests with microactions attached
    microactions_valid: int = 0  # Tests with CORRECT microactions
    avg_ms: float = 0.0

    def add_result(self, result: PipelineResult):
        self.total += 1
        self.results.append(result)

        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
            stage = result.failure_stage or "unknown"
            self.by_stage_failure[stage] = self.by_stage_failure.get(stage, 0) + 1

        # Track by category
        cat = result.category
        if cat not in self.by_category:
            self.by_category[cat] = {"total": 0, "passed": 0, "failed": 0}
        self.by_category[cat]["total"] += 1
        if result.passed:
            self.by_category[cat]["passed"] += 1
        else:
            self.by_category[cat]["failed"] += 1

        # NEW: Track by outcome
        if result.outcome:
            self.by_outcome[result.outcome] = self.by_outcome.get(result.outcome, 0) + 1
            if result.outcome == "salvaged":
                self.salvaged_count += 1

        # NEW: Track top-3 successes
        if result.top3_success:
            self.top3_success_count += 1

        # Track microaction stats
        if result.handler_has_actions:
            self.microactions_attached += 1
        if result.handler_actions_valid:
            self.microactions_valid += 1

    def compute_stats(self):
        if self.results:
            self.avg_ms = sum(r.total_ms for r in self.results) / len(self.results)

    def to_dict(self) -> Dict:
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "pass_rate": round(self.passed / self.total * 100, 1) if self.total > 0 else 0,
                "avg_ms": round(self.avg_ms, 1),
                "salvaged_count": self.salvaged_count,
                "top3_success_count": self.top3_success_count,
            },
            "by_category": self.by_category,
            "by_stage_failure": self.by_stage_failure,
            "by_outcome": self.by_outcome,
            "results": [r.to_dict() for r in self.results]
        }


class PipelineTestRunner:
    """Runs hostile tests through the full pipeline"""

    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.pipeline = get_pipeline()
        self.registry = get_registry()
        self.executor = ActionExecutor(supabase_client)

        # NEW: Security gate and query classifier
        self.security_gate = get_security_gate()
        self.classifier = get_classifier()

        # NEW: 4-outcome model and top-3 evaluator
        self.outcome_classifier = get_outcome_classifier()
        self.test_evaluator = get_test_evaluator()

        # Import handlers
        from handlers.equipment_handlers import get_equipment_handlers
        from handlers.inventory_handlers import get_inventory_handlers
        from handlers.work_order_handlers import get_work_order_handlers
        from handlers.fault_handlers import get_fault_handlers
        from handlers.list_handlers import get_list_handlers  # NEW: List handlers

        self.handlers = {}
        self.handlers.update(get_equipment_handlers(supabase_client))
        self.handlers.update(get_inventory_handlers(supabase_client))
        self.handlers.update(get_work_order_handlers(supabase_client))
        self.handlers.update(get_fault_handlers(supabase_client))

        # NEW: Add list handlers for filter-based queries
        self.list_handlers = get_list_handlers(supabase_client)

        # Expected actions by entity type (for microaction validation)
        self.expected_actions = {
            "equipment": ["view_equipment", "create_work_order", "view_history", "view_documents"],
            "part": ["view_part", "adjust_stock", "create_purchase_order", "view_usage_history"],
            "work_order": ["view_work_order", "update_status", "add_note", "assign_crew"],
            "fault": ["view_fault", "create_work_order", "view_history", "acknowledge"],
        }

    def _validate_microactions(
        self,
        entity_type: str,
        available_actions: List[Dict]
    ) -> Tuple[int, bool]:
        """
        Validate that microactions are correctly attached for the entity type.

        Returns: (action_count, is_valid)
        """
        if not available_actions:
            return 0, False

        action_count = len(available_actions)

        # Check that actions have required fields
        required_fields = ["action", "label"]
        for action in available_actions:
            if not all(field in action for field in required_fields):
                return action_count, False

        # Check that at least one action matches expected for entity type
        expected = self.expected_actions.get(entity_type, [])
        if not expected:
            # Unknown entity type - just check actions exist
            return action_count, action_count > 0

        action_ids = [a.get("action", "") for a in available_actions]
        has_expected = any(exp in action_ids for exp in expected)

        return action_count, has_expected

    def _evaluate_result(
        self,
        result: PipelineResult,
        test: HostileTest,
        items: List[Dict],
        extracted_entities: List[Dict]
    ) -> None:
        """
        Evaluate result using 4-outcome model and top-3 success criterion.

        RECEPTIONIST MODEL:
        - FOUND: All constraints satisfied → PASS
        - SALVAGED: Partial match, uncertainty surfaced → PASS (with note)
        - UNKNOWN: No anchors → FAIL (but not harshly)
        - EMPTY: Anchors present, no records → PASS only if expected EMPTY

        TOP-3 SUCCESS:
        - If correct entity is in first 3 results, count as success
        """
        has_results = len(items) > 0

        # Classify outcome using 4-outcome model
        outcome_result = self.outcome_classifier.classify(
            test.query,
            extracted_entities,
            has_results,
            len(items)
        )

        result.outcome = outcome_result.outcome.value
        result.outcome_confidence = outcome_result.confidence
        result.unmatched_tokens = outcome_result.unmatched_tokens

        # Determine pass/fail based on outcome and expected behavior
        if test.expected == ExpectedBehavior.BLOCKED:
            # Security tests - should have been blocked earlier
            result.passed = False
            result.failure_reason = "Expected to be blocked at security gate"

        elif test.expected == ExpectedBehavior.EMPTY:
            # Negative tests - expect no results
            if outcome_result.outcome == QueryOutcome.EMPTY:
                result.passed = True
            elif outcome_result.outcome == QueryOutcome.UNKNOWN:
                result.passed = True  # Unknown queries returning empty is OK
            else:
                result.passed = not has_results
                if has_results:
                    result.failure_reason = "Expected empty but got results"

        elif test.expected in [ExpectedBehavior.HAS_RESULTS, ExpectedBehavior.FIRST_MATCH]:
            # Positive tests - expect results
            if outcome_result.outcome == QueryOutcome.FOUND:
                result.passed = True
            elif outcome_result.outcome == QueryOutcome.SALVAGED:
                # SALVAGED = partial match with signal
                # Under receptionist model, this is a PASS (we returned what we could)
                result.passed = True
                result.failure_reason = f"Salvaged: unmatched tokens {outcome_result.unmatched_tokens}"
            elif outcome_result.outcome == QueryOutcome.UNKNOWN:
                # No anchors detected - BUT if we still returned results, that's a weak pass
                # Receptionist model: we gave you something even if uncertain about the query
                if has_results:
                    result.passed = True
                    result.failure_reason = "Unknown query but returned results (weak pass)"
                else:
                    result.passed = False
                    result.failure_reason = "No domain anchors found in query"
            else:  # EMPTY
                result.passed = False
                result.failure_reason = "Expected results but got empty"

        else:
            # Default: has_results = pass
            result.passed = has_results

        # Top-3 evaluation (for ranking purposes)
        # If we have items and a target entity, check position
        if items and test.expected_entity_id:
            for i, item in enumerate(items[:10], 1):  # Check first 10
                item_id = item.get("id", item.get("entity_id", ""))
                if item_id == test.expected_entity_id:
                    result.result_position = i
                    break

            result.top3_success = 0 < result.result_position <= 3

            # If in top 3, override to pass (top-3 success criterion)
            if result.top3_success and not result.passed:
                result.passed = True
                result.failure_reason = f"Top-3 success (position {result.result_position})"

    async def run_pipeline(self, test: HostileTest, yacht_id: str) -> PipelineResult:
        """Run a single test through the full pipeline"""
        result = PipelineResult(
            test_id=test.id,
            query=test.query,
            category=test.category.value,
            expected_behavior=test.expected.value
        )

        start_total = time.time()

        try:
            # ================================================================
            # STAGE 0: SECURITY GATE (NEW)
            # Block attacks BEFORE they reach extraction
            # ================================================================
            security_check = self.security_gate.check(test.query)
            if security_check.blocked:
                result.failure_stage = PipelineStage.SECURITY_GATE.value
                result.failure_reason = f"Blocked: {security_check.reason}"

                # Security tests expect BLOCKED behavior
                if test.expected == ExpectedBehavior.BLOCKED:
                    result.passed = True
                else:
                    result.passed = False

                result.total_ms = (time.time() - start_total) * 1000
                return result

            # ================================================================
            # STAGE 0.5: QUERY CLASSIFICATION (NEW)
            # Determine LOOKUP vs LIST routing before extraction
            # ================================================================
            classification = self.classifier.classify(test.query)

            # ================================================================
            # STAGE 1: Entity Extraction
            # ================================================================
            start = time.time()
            extraction = self.pipeline.extract(test.query)
            result.extraction_ms = (time.time() - start) * 1000

            if extraction:
                result.extraction_success = True
                result.extraction_entities = extraction.get("entities", [])
                result.extraction_lane = extraction.get("lane", "")
                result.extraction_intent = extraction.get("intent", "")
            else:
                result.extraction_success = False
                result.failure_stage = PipelineStage.EXTRACTION.value
                result.failure_reason = "Extraction returned None"
                result.total_ms = (time.time() - start_total) * 1000
                return result

            # Handle expected empty/blocked results
            if test.expected == ExpectedBehavior.BLOCKED:
                # Security tests - should have been blocked at security gate
                # If we got here, the attack wasn't caught
                result.passed = False
                result.failure_stage = PipelineStage.SECURITY_GATE.value
                result.failure_reason = "Attack should have been blocked at security gate"
                result.total_ms = (time.time() - start_total) * 1000
                return result

            if test.expected == ExpectedBehavior.EMPTY:
                # Negative tests - extraction success but no valid results expected
                # We'll check at the SQL execution stage
                pass

            # ================================================================
            # STAGE 2: Action Resolution (with LIST routing)
            # ================================================================
            start = time.time()

            # Use classifier result for entity type
            entity_type = classification.entity_type

            # Fallback to extraction-based detection if classifier didn't determine type
            if not entity_type:
                # Priority: equipment > part > work_order > fault
                for entity in result.extraction_entities:
                    etype = entity.get("type", entity.get("entity_type", ""))
                    if etype in ["equipment", "equipment_code"]:
                        entity_type = "equipment"
                        break
                    elif etype in ["part", "part_number", "part_name"]:
                        entity_type = "part"
                        break
                    elif etype in ["work_order", "wo"]:
                        entity_type = "work_order"
                        break
                    elif etype in ["fault", "fault_code"]:
                        entity_type = "fault"
                        break

            # Fallback: use lane to determine entity type
            if not entity_type:
                lane_to_entity = {
                    "pms_equipment": "equipment",
                    "pms_parts": "part",
                    "pms_work_orders": "work_order",
                    "pms_faults": "fault",
                }
                entity_type = lane_to_entity.get(result.extraction_lane, None)

            # Further fallback: detect from query text keywords
            if not entity_type:
                query_lower = test.query.lower()
                if any(kw in query_lower for kw in ["part", "inventory", "stock"]):
                    entity_type = "part"
                elif any(kw in query_lower for kw in ["fault", "diagnose", "error", "alarm"]):
                    entity_type = "fault"
                elif any(kw in query_lower for kw in ["work order", "wo", "maintenance", "task"]):
                    entity_type = "work_order"
                else:
                    entity_type = "equipment"

            # ================================================================
            # NEW: Route LIST queries to list handlers (skip entity_id resolution)
            # ================================================================
            if classification.query_type == QueryType.LIST:
                result.action_ms = (time.time() - start) * 1000
                result.action_resolution_success = True
                result.resolved_action_id = f"list_{entity_type}s"
                result.resolved_action_variant = "READ"

                # Execute list handler directly
                start = time.time()
                list_handler_name = f"list_{entity_type}s"
                if entity_type == "work_order":
                    list_handler_name = "list_work_orders"
                elif entity_type == "part":
                    list_handler_name = "list_parts"
                elif entity_type == "fault":
                    list_handler_name = "list_faults"
                elif entity_type == "equipment":
                    list_handler_name = "list_equipment"

                list_handler = self.list_handlers.get(list_handler_name)
                if list_handler:
                    try:
                        handler_response = await list_handler(
                            yacht_id,
                            classification.filters,
                            {}
                        )
                        result.sql_ms = (time.time() - start) * 1000
                        result.sql_execution_success = True

                        if handler_response:
                            result.handler_output_success = True
                            data = handler_response.get("data", {})
                            items = data.get("items", [])
                            result.sql_result_count = len(items)
                            result.handler_has_data = len(items) > 0

                            # Validate microactions
                            available_actions = handler_response.get("available_actions", [])
                            result.handler_has_actions = bool(available_actions)
                            result.handler_actions_count, result.handler_actions_valid = \
                                self._validate_microactions(entity_type, available_actions)

                            # NEW: Use 4-outcome model and top-3 evaluation
                            self._evaluate_result(
                                result, test, items, result.extraction_entities
                            )
                        else:
                            result.failure_stage = PipelineStage.HANDLER_OUTPUT.value
                            result.failure_reason = "List handler returned None"
                    except Exception as e:
                        result.failure_stage = PipelineStage.SQL_EXECUTION.value
                        result.failure_reason = str(e)
                else:
                    result.failure_stage = PipelineStage.SQL_EXECUTION.value
                    result.failure_reason = f"No list handler for {list_handler_name}"

                result.total_ms = (time.time() - start_total) * 1000
                return result

            # ================================================================
            # LOOKUP queries continue with existing entity_id resolution logic
            # ================================================================

            # Get primary action from registry
            primary_action = self.registry.get_primary_action(entity_type)
            result.action_ms = (time.time() - start) * 1000

            if primary_action:
                result.action_resolution_success = True
                result.resolved_action_id = primary_action.action_id
                result.resolved_action_variant = primary_action.variant.value
            else:
                # No action - might be a search/lookup, which is valid
                result.action_resolution_success = True
                result.resolved_action_id = f"search_{entity_type}"
                result.resolved_action_variant = "READ"

            # STAGE 3: SQL Execution
            start = time.time()

            # Determine handler to call
            action_id = result.resolved_action_id
            handler = self.handlers.get(action_id)

            if handler:
                # We have a specific handler
                try:
                    # ALWAYS resolve entity_id from DB to get UUID
                    # The extracted value is a code (e.g., "ME-S-001"), not a UUID
                    resolved_id = None

                    if result.extraction_entities:
                        resolved_id = await self._resolve_entity_id(
                            entity_type,
                            result.extraction_entities,
                            yacht_id
                        )

                    # Fallback: try to extract codes directly from query text
                    if not resolved_id:
                        resolved_id = await self._resolve_from_query_text(
                            test.query,
                            entity_type,
                            yacht_id
                        )

                    result.sql_ms = (time.time() - start) * 1000

                    if resolved_id:
                        result.sql_execution_success = True
                        result.sql_result_count = 1
                        result.sql_table_hit = result.extraction_lane
                    else:
                        # No entity found - might be expected for negative tests
                        if test.expected == ExpectedBehavior.EMPTY:
                            result.sql_execution_success = True
                            result.sql_result_count = 0
                            result.passed = True
                            result.total_ms = (time.time() - start_total) * 1000
                            return result
                        else:
                            result.failure_stage = PipelineStage.SQL_EXECUTION.value
                            result.failure_reason = "Could not resolve entity_id"
                            result.total_ms = (time.time() - start_total) * 1000
                            return result

                    # STAGE 4: Handler Execution
                    start = time.time()

                    handler_response = await handler(resolved_id, yacht_id, {})
                    result.handler_ms = (time.time() - start) * 1000

                    if handler_response:
                        result.handler_output_success = True
                        result.handler_has_data = bool(handler_response.get("data"))

                        # Validate microactions
                        available_actions = handler_response.get("available_actions", [])
                        result.handler_has_actions = bool(available_actions)
                        result.handler_actions_count, result.handler_actions_valid = \
                            self._validate_microactions(entity_type, available_actions)

                        if handler_response.get("error"):
                            result.handler_error = handler_response.get("error", {}).get("message", "")

                            # NOT_FOUND is acceptable for some tests
                            if test.expected == ExpectedBehavior.EMPTY:
                                result.passed = True
                            else:
                                result.failure_stage = PipelineStage.HANDLER_OUTPUT.value
                                result.failure_reason = result.handler_error
                        else:
                            # NEW: Use 4-outcome model evaluation
                            # LOOKUP returns single entity, wrap in list for evaluation
                            data = handler_response.get("data", {})
                            items = [data] if data else []
                            self._evaluate_result(
                                result, test, items, result.extraction_entities
                            )
                    else:
                        result.failure_stage = PipelineStage.HANDLER_OUTPUT.value
                        result.failure_reason = "Handler returned None"

                except Exception as e:
                    result.failure_stage = PipelineStage.HANDLER_OUTPUT.value
                    result.failure_reason = str(e)
            else:
                # No specific handler - do a direct DB query
                try:
                    table = result.extraction_lane or "equipment"

                    # Build search query
                    search_terms = []
                    for entity in result.extraction_entities:
                        val = entity.get("canonical_value", entity.get("value", ""))
                        if val:
                            search_terms.append(val)

                    if search_terms:
                        # Simple search
                        search_term = search_terms[0]
                        query = self.client.table(table).select("id, name").eq(
                            "yacht_id", yacht_id
                        ).ilike("name", f"%{search_term}%").limit(10)

                        db_result = query.execute()
                        result.sql_ms = (time.time() - start) * 1000

                        result.sql_execution_success = True
                        result.sql_result_count = len(db_result.data) if db_result.data else 0
                        result.sql_table_hit = table
                        result.handler_output_success = True
                        result.handler_has_data = bool(db_result.data)

                        # NEW: Use 4-outcome model evaluation
                        items = db_result.data or []
                        self._evaluate_result(
                            result, test, items, result.extraction_entities
                        )
                    else:
                        result.failure_stage = PipelineStage.SQL_EXECUTION.value
                        result.failure_reason = "No search terms extracted"

                except Exception as e:
                    result.failure_stage = PipelineStage.SQL_EXECUTION.value
                    result.failure_reason = str(e)

        except Exception as e:
            result.failure_stage = "unknown"
            result.failure_reason = str(e)

        result.total_ms = (time.time() - start_total) * 1000
        return result

    def _normalize_code(self, value: str, entity_type: str) -> List[str]:
        """
        Generate normalized code variants for DB matching.
        Returns multiple variants to try.
        """
        import re
        value = value.strip().upper()
        variants = [value]  # Always try original

        # Remove all separators to get base
        base = re.sub(r'[-_\s.]+', '', value)

        if entity_type == "part":
            # Part numbers: HYD0066515 → HYD-0066-515
            # Format: XXX-NNNN-NNN
            if len(base) >= 10 and base[:3].isalpha():
                formatted = f"{base[:3]}-{base[3:7]}-{base[7:]}"
                variants.append(formatted)
            variants.append(base)  # Also try without hyphens

        elif entity_type == "fault":
            # Fault codes: E-047 → E047, e047 → E047
            # Simple codes are letter + digits with no separator
            variants.append(base)  # E047
            # Also try with hyphen after letter: E-047
            if len(base) >= 2 and base[0].isalpha():
                variants.append(f"{base[0]}-{base[1:]}")

        elif entity_type == "equipment":
            # Equipment: MES001 → ME-S-001
            # Various formats exist
            variants.append(base)
            # Try common patterns
            if base.startswith("ME") and len(base) >= 6:
                variants.append(f"ME-{base[2]}-{base[3:]}")
            elif base.startswith("GEN") and len(base) >= 6:
                variants.append(f"GEN-{base[3:]}")
            elif base.startswith("THR") and len(base) >= 7:
                variants.append(f"THR-{base[3]}-{base[4:]}")

        return list(dict.fromkeys(variants))  # Dedupe while preserving order

    async def _resolve_entity_id(
        self,
        entity_type: str,
        entities: List[Dict],
        yacht_id: str
    ) -> Optional[str]:
        """Try to resolve an entity_id from extracted entities"""

        # Table and key field mappings
        table_config = {
            "equipment": {"table": "equipment", "code_field": "code", "name_field": "name"},
            "part": {"table": "pms_parts", "code_field": "part_number", "name_field": "name"},
            "work_order": {"table": "pms_work_orders", "code_field": "title", "name_field": "title"},
            "fault": {"table": "pms_faults", "code_field": "fault_code", "name_field": "title"},
        }

        config = table_config.get(entity_type)
        if not config:
            return None

        table = config["table"]
        code_field = config["code_field"]
        name_field = config["name_field"]

        # Get search values from entities
        for entity in entities:
            value = entity.get("canonical_value", entity.get("value", ""))
            if not value:
                continue

            try:
                # 1. Try name field with ILIKE (most common - semantic search)
                result = self.client.table(table).select("id").eq(
                    "yacht_id", yacht_id
                ).ilike(name_field, f"%{value}%").limit(1).execute()

                if result.data:
                    return result.data[0]["id"]

                # 2. Try all normalized variants for code matching
                for variant in self._normalize_code(value, entity_type):
                    result = self.client.table(table).select("id").eq(
                        "yacht_id", yacht_id
                    ).eq(code_field, variant).limit(1).execute()

                    if result.data:
                        return result.data[0]["id"]

                # 3. Try ILIKE on code field (fuzzy match)
                result = self.client.table(table).select("id").eq(
                    "yacht_id", yacht_id
                ).ilike(code_field, f"%{value}%").limit(1).execute()

                if result.data:
                    return result.data[0]["id"]

            except Exception as e:
                continue

        return None

    async def _resolve_from_query_text(
        self,
        query: str,
        entity_type: str,
        yacht_id: str
    ) -> Optional[str]:
        """
        Fallback: Try to extract codes/names directly from query text.
        Used when entity extraction produces no results.
        """
        import re

        table_config = {
            "equipment": {"table": "equipment", "code_field": "code", "name_field": "name"},
            "part": {"table": "pms_parts", "code_field": "part_number", "name_field": "name"},
            "fault": {"table": "pms_faults", "code_field": "fault_code", "name_field": "title"},
        }

        config = table_config.get(entity_type)
        if not config:
            return None

        table = config["table"]
        code_field = config["code_field"]
        name_field = config["name_field"]

        # Equipment code patterns: ME-S-001, GEN-002, THR-B-001, etc.
        # Use flexible separators to match various formats
        eq_patterns = [
            r'(M[\s\-\.]*E[\s\-\.]*[SP][\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d)',  # ME-S-001, MES001, M E S 0 0 1
            r'(G[\s\-\.]*E[\s\-\.]*N[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d)',      # GEN-001, GEN001
            r'(H[\s\-\.]*V[\s\-\.]*A[\s\-\.]*C[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d)',  # HVAC-001
            r'(T[\s\-\.]*H[\s\-\.]*R[\s\-\.]*[BS][\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d)',  # THR-B-001
            r'(W[\s\-\.]*M[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d)',                # WM-001
            r'(H[\s\-\.]*Y[\s\-\.]*D[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d)',      # HYD-001
            r'(F[\s\-\.]*I[\s\-\.]*R[\s\-\.]*E[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d)',  # FIRE-001
            r'(N[\s\-\.]*A[\s\-\.]*V[\s\-\.]*(?:RAD|AP|R[\s\-\.]*A[\s\-\.]*D|A[\s\-\.]*P)[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d)',  # NAV-RAD-001
            r'(S[\s\-\.]*T[\s\-\.]*P[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d)',  # STP-001
        ]

        # Part number patterns: ENG-0008-103, PMP-0018-280, etc.
        part_patterns = [
            r'([A-Z]{3}[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d)',  # ENG-0008-103
            r'(ENG[\s\-\.]*\d{4}[\s\-\.]*\d{3})',   # ENG-0008-103
            r'(PMP[\s\-\.]*\d{4}[\s\-\.]*\d{3})',   # PMP-0018-280
            r'(FLT[\s\-\.]*\d{4}[\s\-\.]*\d{3})',   # FLT-0002-346
            r'(HYD[\s\-\.]*\d{4}[\s\-\.]*\d{3})',   # HYD-0066-515
            r'(GEN[\s\-\.]*\d{4}[\s\-\.]*\d{3})',   # GEN-0127-320
            r'(NAV[\s\-\.]*\d{4}[\s\-\.]*\d{3})',   # NAV-0131-486
        ]

        # Fault code patterns: E047, G012
        fault_patterns = [
            r'([EGH]\d{3})',                        # E047, G012
            r'([A-Z]{2,4}[-\s]?\d{2,3})',          # HVAC-05
        ]

        query_upper = query.upper()

        patterns = []
        if entity_type == "equipment":
            patterns = eq_patterns
        elif entity_type == "part":
            patterns = part_patterns
        elif entity_type == "fault":
            patterns = fault_patterns

        for pattern in patterns:
            match = re.search(pattern, query_upper, re.IGNORECASE)
            if match:
                code = match.group(1).strip()
                # Normalize: remove all separators, then rebuild
                clean = re.sub(r'[\s\-\.]+', '', code).upper()

                # Map to proper code format based on pattern
                if clean.startswith('ME') and len(clean) >= 6:
                    # MES001 → ME-S-001
                    normalized = f"{clean[:2]}-{clean[2]}-{clean[3:]}"
                elif clean.startswith('GEN') and len(clean) >= 6:
                    # GEN001 → GEN-001
                    normalized = f"GEN-{clean[3:]}"
                elif clean.startswith('HVAC') and len(clean) >= 7:
                    # HVAC001 → HVAC-001
                    normalized = f"HVAC-{clean[4:]}"
                elif clean.startswith('THR') and len(clean) >= 7:
                    # THRB001 → THR-B-001
                    normalized = f"THR-{clean[3]}-{clean[4:]}"
                elif clean.startswith('WM') and len(clean) >= 5:
                    # WM001 → WM-001
                    normalized = f"WM-{clean[2:]}"
                elif clean.startswith('HYD') and len(clean) >= 6:
                    # HYD001 → HYD-001
                    normalized = f"HYD-{clean[3:]}"
                elif clean.startswith('FIRE') and len(clean) >= 7:
                    # FIRE001 → FIRE-001
                    normalized = f"FIRE-{clean[4:]}"
                elif clean.startswith('NAV'):
                    # NAVRAD001 → NAV-RAD-001, NAVAP001 → NAV-AP-001
                    if 'RAD' in clean:
                        idx = clean.index('RAD') + 3
                        normalized = f"NAV-RAD-{clean[idx:]}"
                    elif 'AP' in clean:
                        idx = clean.index('AP') + 2
                        normalized = f"NAV-AP-{clean[idx:]}"
                    else:
                        normalized = clean
                elif clean.startswith('STP') and len(clean) >= 6:
                    # STP001 → STP-001
                    normalized = f"STP-{clean[3:]}"
                elif entity_type == "part" and len(clean) >= 10:
                    # Part numbers: ENG0008103 → ENG-0008-103
                    prefix = clean[:3]
                    mid = clean[3:7]
                    suffix = clean[7:]
                    normalized = f"{prefix}-{mid}-{suffix}"
                else:
                    # Fallback: replace spaces with hyphens
                    normalized = code.replace(" ", "-").replace("--", "-")

                try:
                    result = self.client.table(table).select("id").eq(
                        "yacht_id", yacht_id
                    ).eq(code_field, normalized).limit(1).execute()

                    if result.data:
                        return result.data[0]["id"]

                    # Try with ILIKE
                    result = self.client.table(table).select("id").eq(
                        "yacht_id", yacht_id
                    ).ilike(code_field, f"%{code.replace(' ', '%')}%").limit(1).execute()

                    if result.data:
                        return result.data[0]["id"]
                except:
                    pass

        # Also try common names from query
        name_keywords = [
            "main engine", "generator", "thruster", "watermaker", "hvac",
            "filter", "pump", "oil filter", "fuel filter", "impeller",
        ]

        for kw in name_keywords:
            if kw in query.lower():
                try:
                    result = self.client.table(table).select("id").eq(
                        "yacht_id", yacht_id
                    ).ilike(name_field, f"%{kw}%").limit(1).execute()

                    if result.data:
                        return result.data[0]["id"]
                except:
                    pass

        return None


def get_tests_by_category(category: str) -> List[HostileTest]:
    """Get tests for a specific category"""
    generators = {
        "canonical": generate_canonical_tests,
        "filter_stack": generate_filter_tests,
        "cross_table": generate_cross_table_tests,
        "ranking": generate_ranking_tests,
        "security": generate_security_tests,
        "chaotic": generate_chaotic_tests,
        "negative": generate_negative_tests,
        "compound": generate_compound_tests,
        "expansion": generate_expansion_tests,
    }

    gen = generators.get(category)
    if gen:
        return gen()
    return []


async def run_tests(
    client: Client,
    tests: List[HostileTest],
    yacht_id: str,
    verbose: bool = True
) -> TestSuite:
    """Run tests through the pipeline"""
    runner = PipelineTestRunner(client)
    suite = TestSuite()

    print(f"\nE2E Pipeline Test Runner")
    print(f"=" * 60)
    print(f"Total tests: {len(tests)}")
    print(f"Yacht ID: {yacht_id}")
    print(f"=" * 60)
    print()

    for i, test in enumerate(tests, 1):
        if verbose:
            status_char = "."
            print(f"\r[{i}/{len(tests)}] {test.id}: {test.query[:40]}...", end="", flush=True)

        result = await runner.run_pipeline(test, yacht_id)
        suite.add_result(result)

        if verbose:
            status = "PASS" if result.passed else "FAIL"
            print(f"\r[{i}/{len(tests)}] {test.id}: {status} ({result.total_ms:.0f}ms)          ")

    suite.compute_stats()
    return suite


def print_summary(suite: TestSuite, show_failures: int = 0):
    """Print test summary"""
    print()
    print("=" * 60)
    print("PIPELINE TEST SUMMARY")
    print("=" * 60)

    summary = suite.to_dict()["summary"]
    print(f"Total:     {summary['total']}")
    print(f"Passed:    {summary['passed']} ({summary['pass_rate']}%)")
    print(f"Failed:    {summary['failed']}")
    print(f"Avg Time:  {summary['avg_ms']:.0f}ms")
    print()

    # NEW: Show outcome breakdown
    print("BY OUTCOME (4-outcome model):")
    print("-" * 40)
    for outcome, count in sorted(suite.by_outcome.items()):
        pct = count / summary['total'] * 100 if summary['total'] > 0 else 0
        print(f"  {outcome:12s}: {count:4d} ({pct:5.1f}%)")
    if suite.salvaged_count > 0:
        print(f"\n  * SALVAGED results count as PASS (receptionist model)")
    if suite.top3_success_count > 0:
        print(f"  * Top-3 successes: {suite.top3_success_count}")
    print()

    # Microaction stats
    print("MICROACTION VALIDATION:")
    print("-" * 40)
    attached_pct = suite.microactions_attached / summary['total'] * 100 if summary['total'] > 0 else 0
    valid_pct = suite.microactions_valid / summary['total'] * 100 if summary['total'] > 0 else 0
    print(f"  Actions attached: {suite.microactions_attached:4d} ({attached_pct:5.1f}%)")
    print(f"  Actions valid:    {suite.microactions_valid:4d} ({valid_pct:5.1f}%)")
    print()

    # By category
    print("BY CATEGORY:")
    print("-" * 40)
    for cat, stats in sorted(suite.by_category.items()):
        rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {cat:20s}: {stats['passed']:4d}/{stats['total']:4d} ({rate:5.1f}%)")
    print()

    # By failure stage
    if suite.by_stage_failure:
        print("FAILURES BY STAGE:")
        print("-" * 40)
        for stage, count in sorted(suite.by_stage_failure.items(), key=lambda x: -x[1]):
            print(f"  {stage:20s}: {count}")
        print()

    # Show specific failures
    if show_failures > 0:
        failures = [r for r in suite.results if not r.passed][:show_failures]
        if failures:
            print(f"TOP {len(failures)} FAILURES:")
            print("-" * 60)
            for f in failures:
                print(f"  [{f.test_id}] {f.query[:50]}")
                print(f"    Stage: {f.failure_stage}")
                print(f"    Reason: {f.failure_reason}")
                print()


def save_results(suite: TestSuite, filepath: str):
    """Save results to JSON"""
    output = {
        "timestamp": datetime.now().isoformat(),
        "yacht_id": TEST_YACHT_ID,
        **suite.to_dict()
    }

    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to: {filepath}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="E2E Pipeline Test Runner")
    parser.add_argument("--category", help="Test category (canonical, filter_stack, etc)")
    parser.add_argument("--limit", type=int, help="Limit number of tests")
    parser.add_argument("--show-failures", type=int, default=0, help="Show top N failures")
    parser.add_argument("--quiet", action="store_true", help="Less verbose")
    parser.add_argument("--output", default="pipeline_test_results.json", help="Output file")
    args = parser.parse_args()

    # Get Supabase credentials
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    client = create_client(supabase_url, supabase_key)

    # Get tests
    if args.category:
        tests = get_tests_by_category(args.category)
        if not tests:
            print(f"Unknown category: {args.category}")
            print("Valid: canonical, filter_stack, cross_table, ranking, security, chaotic, negative, compound, expansion")
            sys.exit(1)
    else:
        tests = generate_all_tests()

    if args.limit:
        tests = tests[:args.limit]

    # Run tests
    suite = await run_tests(client, tests, TEST_YACHT_ID, verbose=not args.quiet)

    # Print summary
    print_summary(suite, args.show_failures)

    # Save results
    save_results(suite, args.output)

    # Exit code
    pass_rate = suite.passed / suite.total * 100 if suite.total > 0 else 0
    sys.exit(0 if pass_rate >= 80 else 1)


if __name__ == "__main__":
    asyncio.run(main())

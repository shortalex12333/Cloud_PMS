#!/usr/bin/env python3
"""
CelesteOS E2E Test Harness
==========================

Full end-to-end testing of the COMPLETE execution chain:
User Input -> Intent Parsing -> Action Routing -> Handler Execution -> Response

NO MOCKS. REAL PIPELINE. PRODUCTION DATABASE.

Run: python3 e2e_test_harness.py
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client

# Production credentials
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"


@dataclass
class ExecutionTrace:
    """Full execution trace for a single query."""
    query: str
    timestamp: str

    # Stage 1: Intent Parsing
    intent_parser_used: bool
    intent: Optional[str]
    intent_category: Optional[str]
    intent_confidence: float
    query_type: Optional[str]
    requires_mutation: bool

    # Stage 2: Action Detection (Module A)
    actions_detected: List[Dict]
    best_action: Optional[str]
    action_confidence: float

    # Stage 3: Entity Extraction (Module B)
    entities_extracted: List[Dict]
    canonical_entities: List[Dict]
    entity_confidence: float

    # Stage 4: Handler Routing
    handler_selected: Optional[str]
    handler_category: Optional[str]  # P0, P1, P2, P3, Situation
    requires_confirmation: bool

    # Stage 5: Execution
    execution_status: str  # success, error, gated, skipped
    execution_latency_ms: int
    db_effects: List[str]  # What was read/written

    # Stage 6: Response
    response_status: Optional[str]
    response_data: Optional[Dict]
    error_message: Optional[str]

    # Validation
    expected_intent: Optional[str]
    expected_action: Optional[str]
    intent_match: Optional[bool]
    action_match: Optional[bool]

    def to_dict(self) -> Dict:
        return asdict(self)


class E2ETestHarness:
    """
    End-to-end test harness for the full CelesteOS pipeline.

    Tests the COMPLETE execution chain from natural language to database effects.
    """

    def __init__(self):
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.traces: List[ExecutionTrace] = []
        self.test_ids: Dict[str, str] = {}

        # Load pipeline components
        self._load_components()

    def _load_components(self):
        """Load all pipeline components."""
        print("\n[INIT] Loading pipeline components...")

        # Intent Parser (GPT-based)
        try:
            from intent_parser import IntentParser
            self.intent_parser = IntentParser()
            print("  + IntentParser loaded (GPT-based)")
        except Exception as e:
            self.intent_parser = None
            print(f"  - IntentParser FAILED: {e}")

        # Unified Extraction Pipeline (Module A/B/C)
        try:
            from unified_extraction_pipeline import get_pipeline
            self.pipeline = get_pipeline()
            print("  + UnifiedExtractionPipeline loaded")
        except Exception as e:
            self.pipeline = None
            print(f"  - UnifiedExtractionPipeline FAILED: {e}")

        # Module A direct (for comparison)
        try:
            from module_a_action_detector import get_detector
            self.action_detector = get_detector()
            print("  + Module A (ActionDetector) loaded")
        except Exception as e:
            self.action_detector = None
            print(f"  - Module A FAILED: {e}")

        # Module B direct (for comparison)
        try:
            from module_b_entity_extractor import get_extractor
            self.entity_extractor = get_extractor()
            print("  + Module B (EntityExtractor) loaded")
        except Exception as e:
            self.entity_extractor = None
            print(f"  - Module B FAILED: {e}")

        # Handlers
        try:
            from handlers.p2_mutation_light_handlers import get_p2_mutation_light_handlers
            from handlers.p3_read_only_handlers import get_p3_read_only_handlers
            from handlers.situation_handlers import get_situation_handlers

            self.p2_handlers = get_p2_mutation_light_handlers(self.client)
            self.p3_handlers = get_p3_read_only_handlers(self.client)
            self.situation_handlers = get_situation_handlers(self.client)
            print("  + Handlers loaded (P2, P3, Situations)")
        except Exception as e:
            self.p2_handlers = {}
            self.p3_handlers = {}
            self.situation_handlers = {}
            print(f"  - Handlers FAILED: {e}")

        print("[INIT] Component loading complete\n")

    async def get_test_ids(self):
        """Fetch test entity IDs from database."""
        print("[SETUP] Fetching test entity IDs...")

        tables = [
            ("pms_faults", "fault_id"),
            ("pms_work_orders", "work_order_id"),
            ("pms_equipment", "equipment_id"),
            ("pms_parts", "part_id"),
            ("documents", "document_id"),
            ("pms_handover", "handover_id"),
            ("pms_purchase_orders", "purchase_order_id"),
        ]

        for table, key in tables:
            try:
                r = self.client.table(table).select("id").eq("yacht_id", TEST_YACHT_ID).limit(1).execute()
                if r.data:
                    self.test_ids[key] = r.data[0]["id"]
                    print(f"  Found {key}: {self.test_ids[key][:8]}...")
            except Exception as e:
                print(f"  No {key}: {str(e)[:30]}")

        print(f"[SETUP] {len(self.test_ids)} test IDs found\n")

    async def execute_query(
        self,
        query: str,
        expected_intent: Optional[str] = None,
        expected_action: Optional[str] = None,
        skip_mutation: bool = True
    ) -> ExecutionTrace:
        """
        Execute a query through the FULL pipeline and capture trace.

        Args:
            query: Natural language user input
            expected_intent: Expected intent for validation
            expected_action: Expected action for validation
            skip_mutation: If True, skip actual mutations (safe mode)

        Returns:
            ExecutionTrace with full pipeline execution details
        """
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Initialize trace
        trace = ExecutionTrace(
            query=query,
            timestamp=timestamp,
            intent_parser_used=False,
            intent=None,
            intent_category=None,
            intent_confidence=0.0,
            query_type=None,
            requires_mutation=False,
            actions_detected=[],
            best_action=None,
            action_confidence=0.0,
            entities_extracted=[],
            canonical_entities=[],
            entity_confidence=0.0,
            handler_selected=None,
            handler_category=None,
            requires_confirmation=False,
            execution_status="pending",
            execution_latency_ms=0,
            db_effects=[],
            response_status=None,
            response_data=None,
            error_message=None,
            expected_intent=expected_intent,
            expected_action=expected_action,
            intent_match=None,
            action_match=None
        )

        try:
            # ============================================================
            # STAGE 1: Intent Parsing (GPT-based)
            # ============================================================
            if self.intent_parser:
                try:
                    # IntentParser.parse() is synchronous, not async
                    parsed = self.intent_parser.parse(query)
                    trace.intent_parser_used = True
                    trace.intent = parsed.intent
                    trace.intent_category = parsed.intent_category
                    trace.intent_confidence = parsed.confidence
                    trace.query_type = parsed.query_type
                    trace.requires_mutation = parsed.requires_mutation
                except Exception as e:
                    trace.error_message = f"Intent parsing failed: {e}"

            # ============================================================
            # STAGE 2: Action Detection (Module A)
            # ============================================================
            if self.action_detector:
                try:
                    actions = self.action_detector.detect_actions(query)
                    trace.actions_detected = [
                        {"action": a.action, "confidence": a.confidence, "verb": a.verb}
                        for a in actions
                    ]
                    if actions:
                        best = actions[0]
                        trace.best_action = best.action
                        trace.action_confidence = best.confidence
                except Exception as e:
                    trace.error_message = f"Action detection failed: {e}"

            # ============================================================
            # STAGE 3: Entity Extraction (Module B)
            # ============================================================
            if self.entity_extractor:
                try:
                    entities = self.entity_extractor.extract_entities(query)
                    trace.entities_extracted = [
                        {"type": e.type, "value": e.value, "canonical": e.canonical, "confidence": e.confidence}
                        for e in entities
                    ]
                    if entities:
                        trace.entity_confidence = sum(e.confidence for e in entities) / len(entities)
                except Exception as e:
                    trace.error_message = f"Entity extraction failed: {e}"

            # ============================================================
            # STAGE 4: Unified Pipeline (combines Module A/B/C)
            # ============================================================
            if self.pipeline:
                try:
                    pipeline_result = self.pipeline.extract(query)
                    trace.canonical_entities = pipeline_result.get("canonical_entities", [])
                except Exception as e:
                    pass  # Non-critical

            # ============================================================
            # STAGE 5: Handler Routing + Execution
            # ============================================================
            handler_result = await self._route_and_execute(trace, skip_mutation)

            if handler_result:
                trace.response_status = handler_result.get("status")
                trace.response_data = handler_result
                if handler_result.get("status") == "error":
                    trace.error_message = handler_result.get("message")
                trace.execution_status = "success" if handler_result.get("status") == "success" else "error"
            else:
                trace.execution_status = "no_handler"

        except Exception as e:
            trace.execution_status = "exception"
            trace.error_message = str(e)

        # Calculate latency
        trace.execution_latency_ms = int((time.time() - start_time) * 1000)

        # Validation
        if expected_intent and trace.intent:
            trace.intent_match = trace.intent == expected_intent
        if expected_action and trace.best_action:
            trace.action_match = trace.best_action == expected_action

        self.traces.append(trace)
        return trace

    async def _route_and_execute(self, trace: ExecutionTrace, skip_mutation: bool) -> Optional[Dict]:
        """Route to handler and execute (or skip if mutation)."""

        # Determine handler based on intent/action
        intent = trace.intent
        action = trace.best_action

        # P3 Read-Only handlers (safe to execute)
        p3_intent_map = {
            "view_fault_history": "view_fault_history",
            "view_work_order_history": "view_work_order_history",
            "view_equipment_details": "view_equipment_details",
            "view_equipment_history": "view_equipment_history",
            "view_part_stock": "view_part_stock",
            "view_compliance_status": "view_compliance_status",
            "view_worklist": "view_worklist",
            "view_fleet_summary": "view_fleet_summary",
            "view_smart_summary": "view_smart_summary",
            "suggest_parts": "suggest_parts",
            "track_delivery": "track_delivery",
        }

        # P2 Mutation-Light handlers
        p2_intent_map = {
            "add_fault_note": "add_fault_note",
            "add_work_order_note": "add_work_order_note",
            "acknowledge_fault": "acknowledge_fault",
            "mark_checklist_item_complete": "mark_checklist_item_complete",
            "add_to_handover": "add_to_handover",
            "log_hours_of_rest": "log_hours_of_rest",
        }

        # Check P3 first (safe)
        if intent in p3_intent_map or action in p3_intent_map:
            handler_key = p3_intent_map.get(intent) or p3_intent_map.get(action)
            if handler_key and handler_key in self.p3_handlers:
                trace.handler_selected = handler_key
                trace.handler_category = "P3"
                trace.db_effects.append(f"READ:{handler_key}")

                # Execute with test data
                kwargs = self._build_handler_kwargs(handler_key)
                try:
                    result = await self.p3_handlers[handler_key](**kwargs)
                    return result
                except Exception as e:
                    return {"status": "error", "message": str(e)}

        # Check P2 (mutations - respect skip_mutation flag)
        if intent in p2_intent_map or action in p2_intent_map:
            handler_key = p2_intent_map.get(intent) or p2_intent_map.get(action)
            if handler_key and handler_key in self.p2_handlers:
                trace.handler_selected = handler_key
                trace.handler_category = "P2"
                trace.requires_confirmation = True

                if skip_mutation:
                    trace.execution_status = "gated"
                    return {"status": "gated", "message": "Mutation skipped in safe mode"}

                # Would execute mutation here
                trace.db_effects.append(f"WRITE:{handler_key}")

        # Check situations
        situation_map = {
            "diagnose_fault": "fault_situation",
            "view_fault": "fault_situation",
            "view_work_order": "work_order_situation",
            "view_equipment": "equipment_situation",
            "view_part": "part_situation",
        }

        if intent in situation_map:
            handler_key = situation_map[intent]
            if handler_key in self.situation_handlers:
                trace.handler_selected = handler_key
                trace.handler_category = "Situation"
                trace.db_effects.append(f"READ:{handler_key}")

                kwargs = self._build_situation_kwargs(handler_key)
                try:
                    result = await self.situation_handlers[handler_key](**kwargs)
                    return result
                except Exception as e:
                    return {"status": "error", "message": str(e)}

        return None

    def _build_handler_kwargs(self, handler_key: str) -> Dict:
        """Build kwargs for handler based on available test IDs."""
        kwargs = {"yacht_id": TEST_YACHT_ID}

        # Add user_id for handlers that need it
        user_handlers = ["view_worklist", "view_fleet_summary", "view_smart_summary", "export_handover"]
        if handler_key in user_handlers:
            kwargs["user_id"] = TEST_USER_ID

        # Add entity IDs
        if "fault" in handler_key and "fault_id" in self.test_ids:
            kwargs["fault_id"] = self.test_ids["fault_id"]
        if "work_order" in handler_key and "work_order_id" in self.test_ids:
            kwargs["work_order_id"] = self.test_ids["work_order_id"]
        if "equipment" in handler_key and "equipment_id" in self.test_ids:
            kwargs["equipment_id"] = self.test_ids["equipment_id"]
        if "part" in handler_key and "part_id" in self.test_ids:
            kwargs["part_id"] = self.test_ids["part_id"]
        if "document" in handler_key and "document_id" in self.test_ids:
            kwargs["document_id"] = self.test_ids["document_id"]
        if "purchase" in handler_key and "purchase_order_id" in self.test_ids:
            kwargs["purchase_order_id"] = self.test_ids["purchase_order_id"]

        return kwargs

    def _build_situation_kwargs(self, handler_key: str) -> Dict:
        """Build kwargs for situation handlers."""
        kwargs = {"yacht_id": TEST_YACHT_ID}

        if handler_key == "fault_situation" and "fault_id" in self.test_ids:
            kwargs["fault_id"] = self.test_ids["fault_id"]
        elif handler_key == "work_order_situation" and "work_order_id" in self.test_ids:
            kwargs["work_order_id"] = self.test_ids["work_order_id"]
        elif handler_key == "equipment_situation" and "equipment_id" in self.test_ids:
            kwargs["equipment_id"] = self.test_ids["equipment_id"]
        elif handler_key == "part_situation" and "part_id" in self.test_ids:
            kwargs["part_id"] = self.test_ids["part_id"]
        elif handler_key == "compliance_situation":
            kwargs["user_id"] = TEST_USER_ID

        return kwargs

    def print_trace(self, trace: ExecutionTrace):
        """Pretty print a single execution trace."""
        print(f"\n{'='*70}")
        print(f"QUERY: \"{trace.query}\"")
        print(f"{'='*70}")

        # Intent Parsing
        print(f"\n[1] INTENT PARSING {'(GPT)' if trace.intent_parser_used else '(Fallback)'}")
        print(f"    Intent: {trace.intent or 'None'}")
        print(f"    Category: {trace.intent_category or 'None'}")
        print(f"    Confidence: {trace.intent_confidence:.2f}")
        print(f"    Query Type: {trace.query_type or 'None'}")
        print(f"    Mutation: {'Yes' if trace.requires_mutation else 'No'}")

        # Action Detection
        print(f"\n[2] ACTION DETECTION (Module A)")
        print(f"    Best Action: {trace.best_action or 'None'}")
        print(f"    Confidence: {trace.action_confidence:.2f}")
        if trace.actions_detected:
            print(f"    All Actions: {[a['action'] for a in trace.actions_detected[:3]]}")

        # Entity Extraction
        print(f"\n[3] ENTITY EXTRACTION (Module B)")
        print(f"    Entities: {len(trace.entities_extracted)}")
        print(f"    Avg Confidence: {trace.entity_confidence:.2f}")
        for e in trace.entities_extracted[:5]:
            print(f"      - {e['type']}: {e['value']} -> {e['canonical']}")

        # Handler Routing
        print(f"\n[4] HANDLER ROUTING")
        print(f"    Handler: {trace.handler_selected or 'None'}")
        print(f"    Category: {trace.handler_category or 'None'}")
        print(f"    Confirmation: {'Required' if trace.requires_confirmation else 'Not required'}")

        # Execution
        print(f"\n[5] EXECUTION")
        print(f"    Status: {trace.execution_status}")
        print(f"    Latency: {trace.execution_latency_ms}ms")
        print(f"    DB Effects: {trace.db_effects or ['None']}")

        # Response
        print(f"\n[6] RESPONSE")
        print(f"    Status: {trace.response_status or 'None'}")
        if trace.error_message:
            print(f"    Error: {trace.error_message[:80]}")

        # Validation
        if trace.intent_match is not None or trace.action_match is not None:
            print(f"\n[7] VALIDATION")
            if trace.intent_match is not None:
                icon = "PASS" if trace.intent_match else "FAIL"
                print(f"    Intent: {icon} (expected={trace.expected_intent}, got={trace.intent})")
            if trace.action_match is not None:
                icon = "PASS" if trace.action_match else "FAIL"
                print(f"    Action: {icon} (expected={trace.expected_action}, got={trace.best_action})")


async def run_e2e_tests():
    """Run comprehensive E2E tests."""
    harness = E2ETestHarness()
    await harness.get_test_ids()

    print("\n" + "=" * 70)
    print("E2E TEST SUITE - FULL PIPELINE EXECUTION")
    print("=" * 70)

    # Test cases: (query, expected_intent, expected_action)
    test_cases = [
        # P3 Read-Only - Should route to handlers
        ("show me the equipment history", "view_equipment_history", "show_equipment_history"),
        ("view compliance status", "view_compliance_status", None),
        ("what's my worklist", "view_worklist", None),

        # Action Detection - Verb-first patterns
        ("create work order for bilge pump", "create_work_order", "create_work_order"),
        ("diagnose E047 on main engine", "diagnose_fault", "diagnose_fault"),
        ("open work order for generator maintenance", "create_work_order", "create_work_order"),

        # Entity Extraction - Maritime terms
        ("MTU 16V4000 engine overheating", None, None),
        ("sea water pump pressure low", None, None),
        ("24V generator failure alarm", None, None),

        # Ambiguous - Should show confidence
        ("bilge manifold", None, None),  # Entity only, no action
        ("tell me about the pump", None, None),  # Informal, no verb

        # Mutations - Should be gated
        ("add note to work order: checked oil level", "add_work_order_note", "add_note_to_work_order"),
        ("acknowledge the fault", "acknowledge_fault", "acknowledge_fault"),

        # Search queries
        ("find documents about fire safety", "search_documents", "search_documents"),
        ("search for bilge pump manual", "search_documents", "search_documents"),
    ]

    results = {"pass": 0, "fail": 0, "no_handler": 0, "gated": 0}

    for query, expected_intent, expected_action in test_cases:
        trace = await harness.execute_query(
            query,
            expected_intent=expected_intent,
            expected_action=expected_action,
            skip_mutation=True
        )
        harness.print_trace(trace)

        # Tally results
        if trace.execution_status == "success":
            results["pass"] += 1
        elif trace.execution_status == "gated":
            results["gated"] += 1
        elif trace.execution_status == "no_handler":
            results["no_handler"] += 1
        else:
            results["fail"] += 1

    # Summary
    print("\n" + "=" * 70)
    print("E2E TEST SUMMARY")
    print("=" * 70)
    print(f"PASSED: {results['pass']}")
    print(f"GATED (mutations skipped): {results['gated']}")
    print(f"NO HANDLER: {results['no_handler']}")
    print(f"FAILED: {results['fail']}")
    print(f"TOTAL: {len(test_cases)}")

    # Export traces
    traces_json = [t.to_dict() for t in harness.traces]
    with open("e2e_traces.json", "w") as f:
        json.dump(traces_json, f, indent=2, default=str)
    print(f"\nTraces exported to: e2e_traces.json")

    return results["fail"] == 0


if __name__ == "__main__":
    success = asyncio.run(run_e2e_tests())
    sys.exit(0 if success else 1)

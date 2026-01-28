#!/usr/bin/env python3
"""
CelesteOS E2E Production Sandbox
================================

Single CLI entrypoint for full pipeline execution.
Accepts raw user text, runs complete pipeline, outputs structured JSON trace.

Usage:
    python3 e2e_sandbox.py "create work order for bilge pump"
    python3 e2e_sandbox.py --batch scenarios.txt
    python3 e2e_sandbox.py --interactive

Exit codes:
    0 = Success
    1 = Routing failure
    2 = Execution failure
    3 = Gating blocked (unsafe mutation)
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client

# Production credentials
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"

# =============================================================================
# CONFIGURATION - ROUTING AND GATING
# =============================================================================

# Module A takes precedence when confidence >= this threshold
MODULE_A_PRECEDENCE_THRESHOLD = 0.85

# Auto-execute threshold - below this, require confirmation
AUTO_EXECUTE_THRESHOLD = 0.80

# Actions that ALWAYS require confirmation (mutations)
GATED_ACTIONS = {
    # P0 - Heavy mutations
    "create_work_order",
    "update_work_order",
    "close_work_order",
    "report_fault",
    "order_parts",
    "create_purchase_request",
    "approve_purchase_order",

    # P1 - Purchasing/Compliance
    "receive_delivery",
    "confirm_purchase",

    # P2 - Light mutations
    "add_fault_note",
    "add_work_order_note",
    "acknowledge_fault",
    "mark_checklist_item_complete",
    "add_to_handover",
    "log_hours_of_rest",
    "consume_part",
    "adjust_part_stock",
}

# Actions that are safe to auto-execute (read-only)
SAFE_ACTIONS = {
    "diagnose_fault",  # Situation - read-only diagnosis
    "view_fault_history",
    "view_work_order_history",
    "view_work_order_checklist",
    "view_equipment_details",
    "view_equipment_history",
    "view_equipment_parts",
    "view_linked_faults",
    "view_equipment_manual",
    "view_part_stock",
    "view_part_location",
    "view_part_usage",
    "view_linked_equipment",
    "view_document",
    "view_related_documents",
    "view_document_section",
    "view_hours_of_rest",
    "view_compliance_status",
    "view_checklist",
    "view_worklist",
    "view_fleet_summary",
    "view_smart_summary",
    "view_handover",
    "export_handover",
    "export_hours_of_rest",
    "export_worklist",
    "export_fleet_summary",
    "track_delivery",
    "suggest_parts",
    "scan_part_barcode",
    "request_predictive_insight",
    "search_documents",
    "find_document",
}

# Intent to handler mapping
INTENT_HANDLER_MAP = {
    # P3 Read-only
    "view_fault_history": ("view_fault_history", "P3"),
    "view_work_order_history": ("view_work_order_history", "P3"),
    "view_equipment_details": ("view_equipment_details", "P3"),
    "view_equipment_history": ("view_equipment_history", "P3"),
    "view_part_stock": ("view_part_stock", "P3"),
    "view_compliance_status": ("view_compliance_status", "P3"),
    "view_worklist": ("view_worklist", "P3"),
    "view_fleet_summary": ("view_fleet_summary", "P3"),
    "view_smart_summary": ("view_smart_summary", "P3"),
    "suggest_parts": ("suggest_parts", "P3"),
    "track_delivery": ("track_delivery", "P3"),
    "view_handover": ("view_handover", "P3"),
    "export_handover": ("export_handover", "P3"),
    "view_document": ("view_document", "P3"),
    "search_documents": ("search_documents", "P3"),
    "find_document": ("find_document", "P3"),

    # P2 Light mutations
    "add_fault_note": ("add_fault_note", "P2"),
    "add_work_order_note": ("add_work_order_note", "P2"),
    "acknowledge_fault": ("acknowledge_fault", "P2"),
    "mark_checklist_item_complete": ("mark_checklist_item_complete", "P2"),
    "add_to_handover": ("add_to_handover", "P2"),
    "log_hours_of_rest": ("log_hours_of_rest", "P2"),

    # Situations
    "diagnose_fault": ("fault_situation", "Situation"),
    "view_fault": ("fault_situation", "Situation"),

    # Module A action mappings (different names)
    "create_work_order": ("create_work_order", "P0"),
    "list_work_orders": ("view_worklist", "P3"),
    "update_work_order": ("update_work_order", "P0"),
    "close_work_order": ("close_work_order", "P0"),
    "view_history": ("view_equipment_history", "P3"),
    "show_equipment_history": ("view_equipment_history", "P3"),
    "report_fault": ("report_fault", "P0"),
    "check_stock": ("view_part_stock", "P3"),
    "order_parts": ("order_parts", "P0"),
    "show_manual_section": ("view_document_section", "P3"),
}


@dataclass
class RoutingDecision:
    """Captures the routing arbitration decision."""
    module_a_action: Optional[str]
    module_a_confidence: float
    intent_parser_intent: Optional[str]
    intent_parser_confidence: float
    final_action: Optional[str]
    source: str  # "module_a", "intent_parser", "fallback", "none"
    reason: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class GatingDecision:
    """Captures the gating decision."""
    action: str
    is_gated: bool
    is_safe: bool
    confidence: float
    requires_confirmation: bool
    auto_execute_allowed: bool
    reason: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ExecutionTrace:
    """Full structured execution trace."""
    query: str
    timestamp: str

    # Routing
    routing: Dict

    # Gating
    gating: Dict

    # Execution
    handler_selected: Optional[str]
    handler_category: Optional[str]
    executed: bool
    execution_status: str
    execution_latency_ms: int

    # Entities
    entities: List[Dict]

    # Response
    response: Optional[Dict]
    error: Optional[str]

    # Validation
    success: bool

    def to_dict(self) -> Dict:
        return asdict(self)


class E2ESandbox:
    """Production E2E sandbox with corrected routing arbitration."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.test_ids: Dict[str, str] = {}

        # Load components
        self._load_components()

    def _log(self, msg: str):
        if self.verbose:
            print(f"[SANDBOX] {msg}", file=sys.stderr)

    def _load_components(self):
        """Load pipeline components."""
        self._log("Loading components...")

        # Intent Parser
        try:
            from intent_parser import IntentParser
            self.intent_parser = IntentParser()
            self._log("IntentParser loaded")
        except Exception as e:
            self.intent_parser = None
            self._log(f"IntentParser FAILED: {e}")

        # Module A - Action Detector
        try:
            from module_a_action_detector import get_detector
            self.action_detector = get_detector()
            self._log("Module A loaded")
        except Exception as e:
            self.action_detector = None
            self._log(f"Module A FAILED: {e}")

        # Module B - Entity Extractor
        try:
            from module_b_entity_extractor import get_extractor
            self.entity_extractor = get_extractor()
            self._log("Module B loaded")
        except Exception as e:
            self.entity_extractor = None
            self._log(f"Module B FAILED: {e}")

        # Handlers
        try:
            from handlers.p2_mutation_light_handlers import get_p2_mutation_light_handlers
            from handlers.p3_read_only_handlers import get_p3_read_only_handlers
            from handlers.situation_handlers import get_situation_handlers

            self.p2_handlers = get_p2_mutation_light_handlers(self.client)
            self.p3_handlers = get_p3_read_only_handlers(self.client)
            self.situation_handlers = get_situation_handlers(self.client)
            self._log("Handlers loaded")
        except Exception as e:
            self.p2_handlers = {}
            self.p3_handlers = {}
            self.situation_handlers = {}
            self._log(f"Handlers FAILED: {e}")

    def fetch_test_ids(self):
        """Fetch test entity IDs from database."""
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
            except:
                pass

    def arbitrate_routing(self, query: str) -> RoutingDecision:
        """
        CRITICAL: Routing arbitration logic.

        Module A takes precedence when confidence >= MODULE_A_PRECEDENCE_THRESHOLD.
        IntentParser is fallback only.
        """
        module_a_action = None
        module_a_confidence = 0.0
        intent_parser_intent = None
        intent_parser_confidence = 0.0

        # Get Module A result
        if self.action_detector:
            actions = self.action_detector.detect_actions(query)
            if actions:
                best = actions[0]
                module_a_action = best.action
                module_a_confidence = best.confidence

        # Get IntentParser result
        if self.intent_parser:
            try:
                parsed = self.intent_parser.parse(query)
                intent_parser_intent = parsed.intent
                intent_parser_confidence = parsed.confidence
            except:
                pass

        # ARBITRATION LOGIC
        # Rule 1: Module A takes precedence when confident
        if module_a_action and module_a_confidence >= MODULE_A_PRECEDENCE_THRESHOLD:
            return RoutingDecision(
                module_a_action=module_a_action,
                module_a_confidence=module_a_confidence,
                intent_parser_intent=intent_parser_intent,
                intent_parser_confidence=intent_parser_confidence,
                final_action=module_a_action,
                source="module_a",
                reason=f"Module A confidence {module_a_confidence:.2f} >= threshold {MODULE_A_PRECEDENCE_THRESHOLD}"
            )

        # Rule 2: IntentParser used if Module A below threshold but IntentParser is confident
        if intent_parser_intent and intent_parser_confidence >= 0.7:
            # But NOT if it's the default "find_document" with low confidence
            if intent_parser_intent != "find_document" or intent_parser_confidence >= 0.8:
                return RoutingDecision(
                    module_a_action=module_a_action,
                    module_a_confidence=module_a_confidence,
                    intent_parser_intent=intent_parser_intent,
                    intent_parser_confidence=intent_parser_confidence,
                    final_action=intent_parser_intent,
                    source="intent_parser",
                    reason=f"IntentParser confidence {intent_parser_confidence:.2f}, Module A below threshold"
                )

        # Rule 3: Module A used even if below threshold (better than nothing)
        if module_a_action and module_a_confidence >= 0.4:
            return RoutingDecision(
                module_a_action=module_a_action,
                module_a_confidence=module_a_confidence,
                intent_parser_intent=intent_parser_intent,
                intent_parser_confidence=intent_parser_confidence,
                final_action=module_a_action,
                source="module_a",
                reason=f"Module A fallback (confidence {module_a_confidence:.2f})"
            )

        # Rule 4: IntentParser as last resort (excluding find_document with 0.5)
        if intent_parser_intent and intent_parser_intent != "find_document":
            return RoutingDecision(
                module_a_action=module_a_action,
                module_a_confidence=module_a_confidence,
                intent_parser_intent=intent_parser_intent,
                intent_parser_confidence=intent_parser_confidence,
                final_action=intent_parser_intent,
                source="intent_parser",
                reason="IntentParser last resort"
            )

        # Rule 5: Keyword-based fallback for common patterns
        query_lower = query.lower()
        keyword_routes = [
            (["worklist", "my tasks", "my work", "assigned to me"], "view_worklist"),
            (["work order history", "wo history"], "view_work_order_history"),
            (["fault history"], "view_fault_history"),
            (["equipment history"], "view_equipment_history"),
            (["track delivery", "delivery status", "shipping status"], "track_delivery"),
            (["fleet summary", "fleet status"], "view_fleet_summary"),
            (["smart summary"], "view_smart_summary"),
            (["compliance", "hours of rest"], "view_compliance_status"),
        ]

        for keywords, action in keyword_routes:
            if any(kw in query_lower for kw in keywords):
                return RoutingDecision(
                    module_a_action=module_a_action,
                    module_a_confidence=module_a_confidence,
                    intent_parser_intent=intent_parser_intent,
                    intent_parser_confidence=intent_parser_confidence,
                    final_action=action,
                    source="keyword_fallback",
                    reason=f"Keyword match -> {action}"
                )

        # Rule 6: Entity-based routing for search queries
        # If we have entities but no action, route to search/lookup
        if self.entity_extractor:
            entities = self.entity_extractor.extract_entities(query)
            if entities:
                # Determine best search action based on entity types
                entity_types = {e.type for e in entities}
                if "fault_code" in entity_types or "symptom" in entity_types:
                    return RoutingDecision(
                        module_a_action=module_a_action,
                        module_a_confidence=module_a_confidence,
                        intent_parser_intent=intent_parser_intent,
                        intent_parser_confidence=intent_parser_confidence,
                        final_action="diagnose_fault",
                        source="entity_inference",
                        reason=f"Entity-based: detected fault_code/symptom -> diagnose_fault"
                    )
                elif "equipment" in entity_types:
                    return RoutingDecision(
                        module_a_action=module_a_action,
                        module_a_confidence=module_a_confidence,
                        intent_parser_intent=intent_parser_intent,
                        intent_parser_confidence=intent_parser_confidence,
                        final_action="view_equipment_details",
                        source="entity_inference",
                        reason=f"Entity-based: detected equipment -> view_equipment_details"
                    )
                elif "part" in entity_types:
                    return RoutingDecision(
                        module_a_action=module_a_action,
                        module_a_confidence=module_a_confidence,
                        intent_parser_intent=intent_parser_intent,
                        intent_parser_confidence=intent_parser_confidence,
                        final_action="view_part_stock",
                        source="entity_inference",
                        reason=f"Entity-based: detected part -> view_part_stock"
                    )
                elif "document_type" in entity_types:
                    return RoutingDecision(
                        module_a_action=module_a_action,
                        module_a_confidence=module_a_confidence,
                        intent_parser_intent=intent_parser_intent,
                        intent_parser_confidence=intent_parser_confidence,
                        final_action="search_documents",
                        source="entity_inference",
                        reason=f"Entity-based: detected document_type -> search_documents"
                    )
                elif "measurement" in entity_types or "measurement_term" in entity_types:
                    return RoutingDecision(
                        module_a_action=module_a_action,
                        module_a_confidence=module_a_confidence,
                        intent_parser_intent=intent_parser_intent,
                        intent_parser_confidence=intent_parser_confidence,
                        final_action="diagnose_fault",
                        source="entity_inference",
                        reason=f"Entity-based: detected measurement -> diagnose_fault"
                    )
                elif "brand" in entity_types or "model" in entity_types:
                    return RoutingDecision(
                        module_a_action=module_a_action,
                        module_a_confidence=module_a_confidence,
                        intent_parser_intent=intent_parser_intent,
                        intent_parser_confidence=intent_parser_confidence,
                        final_action="search_documents",
                        source="entity_inference",
                        reason=f"Entity-based: detected brand/model -> search_documents"
                    )

        # Rule 6: No confident routing
        return RoutingDecision(
            module_a_action=module_a_action,
            module_a_confidence=module_a_confidence,
            intent_parser_intent=intent_parser_intent,
            intent_parser_confidence=intent_parser_confidence,
            final_action=None,
            source="none",
            reason="No confident routing available"
        )

    def decide_gating(self, action: str, confidence: float) -> GatingDecision:
        """
        CRITICAL: Gating decision logic.

        Never allow mutation actions without confirmation.
        """
        if not action:
            return GatingDecision(
                action="",
                is_gated=False,
                is_safe=False,
                confidence=0.0,
                requires_confirmation=False,
                auto_execute_allowed=False,
                reason="No action to gate"
            )

        is_gated = action in GATED_ACTIONS
        is_safe = action in SAFE_ACTIONS

        # Gated actions ALWAYS require confirmation
        if is_gated:
            return GatingDecision(
                action=action,
                is_gated=True,
                is_safe=False,
                confidence=confidence,
                requires_confirmation=True,
                auto_execute_allowed=False,
                reason=f"Action '{action}' is in GATED_ACTIONS - mutation requires confirmation"
            )

        # Safe actions with high confidence can auto-execute
        if is_safe and confidence >= AUTO_EXECUTE_THRESHOLD:
            return GatingDecision(
                action=action,
                is_gated=False,
                is_safe=True,
                confidence=confidence,
                requires_confirmation=False,
                auto_execute_allowed=True,
                reason=f"Safe action with confidence {confidence:.2f} >= {AUTO_EXECUTE_THRESHOLD}"
            )

        # Safe actions with low confidence still need confirmation
        if is_safe and confidence < AUTO_EXECUTE_THRESHOLD:
            return GatingDecision(
                action=action,
                is_gated=False,
                is_safe=True,
                confidence=confidence,
                requires_confirmation=True,
                auto_execute_allowed=False,
                reason=f"Safe action but confidence {confidence:.2f} < {AUTO_EXECUTE_THRESHOLD} - confirm intent"
            )

        # Unknown action - require confirmation
        return GatingDecision(
            action=action,
            is_gated=False,
            is_safe=False,
            confidence=confidence,
            requires_confirmation=True,
            auto_execute_allowed=False,
            reason=f"Unknown action '{action}' - requires confirmation"
        )

    async def execute(self, query: str, force_execute: bool = False) -> ExecutionTrace:
        """
        Execute query through full pipeline.

        Args:
            query: Raw user input
            force_execute: If True, execute even gated actions (for testing)
        """
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Extract entities
        entities = []
        if self.entity_extractor:
            try:
                raw_entities = self.entity_extractor.extract_entities(query)
                entities = [
                    {"type": e.type, "value": e.value, "canonical": e.canonical, "confidence": e.confidence}
                    for e in raw_entities
                ]
            except:
                pass

        # Routing arbitration
        routing = self.arbitrate_routing(query)

        # Gating decision
        confidence = routing.module_a_confidence if routing.source == "module_a" else routing.intent_parser_confidence
        gating = self.decide_gating(routing.final_action, confidence)

        # Determine handler
        handler_key = None
        handler_category = None

        if routing.final_action and routing.final_action in INTENT_HANDLER_MAP:
            handler_key, handler_category = INTENT_HANDLER_MAP[routing.final_action]

        # Execute or gate
        executed = False
        execution_status = "pending"
        response = None
        error = None

        if gating.requires_confirmation and not force_execute:
            execution_status = "gated"
            response = {
                "status": "gated",
                "action": routing.final_action,
                "message": f"Action requires confirmation: {gating.reason}",
                "confirmation_required": True
            }
        elif handler_key:
            # Attempt execution
            try:
                result = await self._execute_handler(handler_key, handler_category)
                executed = True
                execution_status = "success" if result.get("status") == "success" else "error"
                response = result
                if result.get("status") == "error":
                    error = result.get("message")
            except Exception as e:
                executed = True
                execution_status = "exception"
                error = str(e)
        else:
            execution_status = "no_handler"
            error = f"No handler mapped for action: {routing.final_action}"

        latency = int((time.time() - start_time) * 1000)

        return ExecutionTrace(
            query=query,
            timestamp=timestamp,
            routing=routing.to_dict(),
            gating=gating.to_dict(),
            handler_selected=handler_key,
            handler_category=handler_category,
            executed=executed,
            execution_status=execution_status,
            execution_latency_ms=latency,
            entities=entities,
            response=response,
            error=error,
            success=(execution_status in ["success", "gated"])
        )

    async def _execute_handler(self, handler_key: str, category: str) -> Dict:
        """Execute handler with test data."""
        kwargs = self._build_kwargs(handler_key)

        if category == "P3" and handler_key in self.p3_handlers:
            return await self.p3_handlers[handler_key](**kwargs)
        elif category == "P2" and handler_key in self.p2_handlers:
            return await self.p2_handlers[handler_key](**kwargs)
        elif category == "Situation" and handler_key in self.situation_handlers:
            return await self.situation_handlers[handler_key](**kwargs)
        else:
            return {"status": "error", "message": f"Handler '{handler_key}' not found in {category}"}

    def _build_kwargs(self, handler_key: str) -> Dict:
        """Build handler kwargs."""
        kwargs = {"yacht_id": TEST_YACHT_ID}

        user_handlers = ["view_worklist", "view_fleet_summary", "view_smart_summary", "export_handover", "log_hours_of_rest"]
        if handler_key in user_handlers:
            kwargs["user_id"] = TEST_USER_ID

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


async def run_single(query: str, verbose: bool = False, force: bool = False) -> int:
    """Run single query and output JSON trace."""
    sandbox = E2ESandbox(verbose=verbose)
    sandbox.fetch_test_ids()

    trace = await sandbox.execute(query, force_execute=force)

    # Output JSON to stdout
    print(json.dumps(trace.to_dict(), indent=2, default=str))

    # Return exit code based on status
    if trace.execution_status == "success":
        return 0
    elif trace.execution_status == "gated":
        return 3
    elif trace.execution_status == "no_handler":
        return 1
    else:
        return 2


async def run_batch(file_path: str, verbose: bool = False) -> int:
    """Run batch of queries from file."""
    sandbox = E2ESandbox(verbose=verbose)
    sandbox.fetch_test_ids()

    with open(file_path, 'r') as f:
        queries = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    traces = []
    for query in queries:
        trace = await sandbox.execute(query)
        traces.append(trace.to_dict())

    # Output all traces
    print(json.dumps(traces, indent=2, default=str))

    # Return success if all succeeded or gated
    failures = sum(1 for t in traces if t["execution_status"] not in ["success", "gated"])
    return 0 if failures == 0 else 1


async def run_interactive(verbose: bool = False):
    """Run interactive mode."""
    sandbox = E2ESandbox(verbose=True)
    sandbox.fetch_test_ids()

    print("CelesteOS E2E Sandbox - Interactive Mode")
    print("Type queries, 'quit' to exit")
    print("-" * 50)

    while True:
        try:
            query = input("\n> ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            if not query:
                continue

            trace = await sandbox.execute(query)

            # Pretty print key info
            print(f"\nRouting: {trace.routing['source']} -> {trace.routing['final_action']}")
            print(f"Confidence: {max(trace.routing['module_a_confidence'], trace.routing['intent_parser_confidence']):.2f}")
            print(f"Gating: {'BLOCKED' if trace.gating['requires_confirmation'] else 'OK'}")
            print(f"Status: {trace.execution_status}")

            if trace.entities:
                print(f"Entities: {[e['canonical'] for e in trace.entities]}")

            if trace.error:
                print(f"Error: {trace.error}")

        except KeyboardInterrupt:
            break
        except EOFError:
            break

    print("\nExiting.")


def main():
    parser = argparse.ArgumentParser(description="CelesteOS E2E Production Sandbox")
    parser.add_argument("query", nargs="?", help="Query to execute")
    parser.add_argument("--batch", "-b", help="File with queries to run in batch")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--force", "-f", action="store_true", help="Force execute gated actions")

    args = parser.parse_args()

    if args.interactive:
        asyncio.run(run_interactive(args.verbose))
        sys.exit(0)
    elif args.batch:
        exit_code = asyncio.run(run_batch(args.batch, args.verbose))
        sys.exit(exit_code)
    elif args.query:
        exit_code = asyncio.run(run_single(args.query, args.verbose, args.force))
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

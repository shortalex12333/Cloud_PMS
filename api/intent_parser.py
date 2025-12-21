"""
Intent Parser (Module A)
========================

Uses GPT to classify user intent and extract entities semantically.

This replaces pure regex extraction for complex queries like:
- "what machines are failing the most" → analytics aggregation
- "who hasn't completed HOR" → compliance check
- "create work order for stabilizer" → mutation

Output:
{
    "intent": "view_equipment_history",
    "intent_category": "manage_equipment",
    "query_type": "search|aggregation|mutation|compliance",
    "entities": {...},
    "parameters": {...},
    "confidence": 0.92
}
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# INTENT TAXONOMY (67 actions grouped by category)
# =============================================================================

INTENT_CATEGORIES = {
    "fix_something": [
        "diagnose_fault",
        "report_fault",
        "show_manual_section",
        "view_fault_history",
        "suggest_parts",
        "create_work_order_from_fault",
        "add_fault_note",
        "add_fault_photo",
        "link_equipment_to_fault",
    ],
    "do_maintenance": [
        "create_work_order",
        "view_work_order_history",
        "mark_work_order_complete",
        "complete_work_order",
        "add_work_order_note",
        "add_work_order_photo",
        "add_parts_to_work_order",
        "link_parts_to_work_order",
        "view_work_order_checklist",
        "assign_work_order",
        "edit_work_order_details",
        "view_checklist",
        "mark_checklist_item_complete",
    ],
    "manage_equipment": [
        "view_equipment_details",
        "view_equipment_history",
        "view_equipment_parts",
        "view_linked_faults",
        "view_equipment_manual",
        "add_equipment_note",
        "request_predictive_insight",
        "view_smart_summary",
    ],
    "control_inventory": [
        "view_part_stock",
        "add_part",
        "order_part",
        "view_part_location",
        "view_part_usage",
        "log_part_usage",
        "edit_part_quantity",
        "scan_part_barcode",
        "view_linked_equipment",
    ],
    "communicate_status": [
        "add_to_handover",
        "add_document_to_handover",
        "add_predictive_insight_to_handover",
        "edit_handover_section",
        "export_handover",
        "regenerate_handover_summary",
        "upload_photo",
        "record_voice_note",
    ],
    "comply_audit": [
        "view_hours_of_rest",
        "update_hours_of_rest",
        "export_hours_of_rest",
        "view_compliance_status",
        "tag_for_survey",
    ],
    "procure_suppliers": [
        "create_purchase_request",
        "add_item_to_purchase",
        "approve_purchase",
        "upload_invoice",
        "track_delivery",
        "log_delivery_received",
        "update_purchase_status",
    ],
    "search_documents": [
        "find_document",
        "view_document",
        "view_related_documents",
        "view_document_section",
    ],
    "analytics": [
        "view_failure_stats",
        "view_maintenance_stats",
        "view_inventory_stats",
        "view_compliance_stats",
    ],
}

# Flatten for validation
ALL_INTENTS = []
for category, intents in INTENT_CATEGORIES.items():
    ALL_INTENTS.extend(intents)


# =============================================================================
# QUERY TYPES
# =============================================================================

class QueryType(Enum):
    SEARCH = "search"           # Find documents, equipment, parts
    AGGREGATION = "aggregation" # Stats, counts, "most/least" queries
    MUTATION = "mutation"       # Create, update, delete
    COMPLIANCE = "compliance"   # HOR, certificates, audits
    LOOKUP = "lookup"           # Simple lookups (inventory location, stock)


# Mutation intents (route to n8n)
MUTATION_INTENTS = {
    "create_work_order", "create_work_order_from_fault",
    "mark_work_order_complete", "complete_work_order",
    "add_work_order_note", "add_work_order_photo",
    "add_fault_note", "add_fault_photo", "report_fault",
    "order_part", "add_part", "log_part_usage", "edit_part_quantity",
    "add_to_handover", "edit_handover_section",
    "update_hours_of_rest",
    "create_purchase_request", "approve_purchase", "log_delivery_received",
    "assign_work_order", "edit_work_order_details",
}

# Aggregation keywords
AGGREGATION_KEYWORDS = [
    "most", "least", "failing", "common", "frequent", "stats",
    "how many", "count", "total", "average", "summary", "trend",
    "overdue", "due today", "due this week", "pending",
]


# =============================================================================
# GPT PROMPT
# =============================================================================

SYSTEM_PROMPT = """You are a yacht PMS (Planned Maintenance System) intent parser.

Given a user query, you must:
1. Classify the intent (what action does the user want?)
2. Extract entities (equipment, parts, people, dates, locations)
3. Determine query type (search, aggregation, mutation, compliance, lookup)
4. Extract parameters for the query

INTENT CATEGORIES:
- fix_something: diagnose faults, view manuals, create WO from fault
- do_maintenance: create/complete work orders, checklists
- manage_equipment: view equipment details, history, parts
- control_inventory: check stock, order parts, view locations
- communicate_status: handover, notes, exports
- comply_audit: hours of rest, certificates, compliance
- procure_suppliers: purchase orders, deliveries, invoices
- search_documents: find manuals, documents
- analytics: stats, trends, aggregations

QUERY TYPES:
- search: finding documents, equipment, faults
- aggregation: "most failing", "how many", "overdue count"
- mutation: create, update, complete, add
- compliance: HOR checks, certificate expiry
- lookup: inventory location, stock check

OUTPUT FORMAT (JSON only, no markdown):
{
  "intent": "the_specific_intent",
  "intent_category": "category_name",
  "query_type": "search|aggregation|mutation|compliance|lookup",
  "entities": {
    "equipment": "extracted equipment name or null",
    "brand": "brand name or null",
    "part": "part name or null",
    "fault_code": "fault code or null",
    "person": "crew member or null",
    "location": "location reference or null",
    "time_range": "today|this_week|this_month|overdue or null",
    "measurement": "any measurement or null"
  },
  "parameters": {
    "filter_by": "field to filter by or null",
    "filter_value": "value to filter or null",
    "group_by": "field to group by for aggregations or null",
    "order": "asc|desc or null",
    "limit": number or null
  },
  "confidence": 0.0-1.0,
  "requires_mutation": true/false
}

EXAMPLES:

Query: "what machines are failing the most"
{
  "intent": "view_failure_stats",
  "intent_category": "analytics",
  "query_type": "aggregation",
  "entities": {},
  "parameters": {
    "group_by": "equipment",
    "order": "desc",
    "metric": "fault_count"
  },
  "confidence": 0.95,
  "requires_mutation": false
}

Query: "create work order for stabilizer not leveling"
{
  "intent": "create_work_order",
  "intent_category": "do_maintenance",
  "query_type": "mutation",
  "entities": {
    "equipment": "stabilizer",
    "fault_description": "not leveling"
  },
  "parameters": {},
  "confidence": 0.92,
  "requires_mutation": true
}

Query: "who hasn't completed their hours of rest"
{
  "intent": "view_compliance_status",
  "intent_category": "comply_audit",
  "query_type": "compliance",
  "entities": {
    "compliance_type": "hours_of_rest"
  },
  "parameters": {
    "filter_by": "status",
    "filter_value": "incomplete"
  },
  "confidence": 0.90,
  "requires_mutation": false
}

Query: "show me box 3d contents"
{
  "intent": "view_part_location",
  "intent_category": "control_inventory",
  "query_type": "lookup",
  "entities": {
    "location": "box 3d"
  },
  "parameters": {
    "filter_by": "location",
    "filter_value": "box 3d"
  },
  "confidence": 0.88,
  "requires_mutation": false
}

Query: "MTU 16V4000 engine overheating manual"
{
  "intent": "show_manual_section",
  "intent_category": "fix_something",
  "query_type": "search",
  "entities": {
    "brand": "MTU",
    "model": "16V4000",
    "equipment": "engine",
    "symptom": "overheating"
  },
  "parameters": {},
  "confidence": 0.94,
  "requires_mutation": false
}
"""


# =============================================================================
# INTENT PARSER CLASS
# =============================================================================

@dataclass
class ParsedIntent:
    """Result of intent parsing."""
    intent: str
    intent_category: str
    query_type: str
    entities: Dict
    parameters: Dict
    confidence: float
    requires_mutation: bool
    raw_query: str

    def to_dict(self) -> Dict:
        return {
            "intent": self.intent,
            "intent_category": self.intent_category,
            "query_type": self.query_type,
            "entities": self.entities,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "requires_mutation": self.requires_mutation,
        }


class IntentParser:
    """
    Parses user queries to extract intent and entities using GPT.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def parse(self, query: str) -> ParsedIntent:
        """
        Parse a user query to extract intent and entities.

        Args:
            query: The user's natural language query

        Returns:
            ParsedIntent with classified intent and extracted entities
        """
        if not self.api_key:
            # Fallback to simple heuristics if no API key
            return self._fallback_parse(query)

        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,
                max_tokens=500,
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            result = json.loads(result_text)

            return ParsedIntent(
                intent=result.get("intent", "search_documents"),
                intent_category=result.get("intent_category", "search_documents"),
                query_type=result.get("query_type", "search"),
                entities=result.get("entities", {}),
                parameters=result.get("parameters", {}),
                confidence=result.get("confidence", 0.5),
                requires_mutation=result.get("requires_mutation", False),
                raw_query=query,
            )

        except Exception as e:
            print(f"GPT parsing error: {e}")
            return self._fallback_parse(query)

    def _fallback_parse(self, query: str) -> ParsedIntent:
        """
        Simple heuristic fallback when GPT unavailable.
        """
        query_lower = query.lower()

        # Detect query type from keywords
        query_type = "search"
        intent = "find_document"
        intent_category = "search_documents"
        requires_mutation = False

        # Check compliance FIRST (before mutations - "completed HOR" is not a mutation)
        if any(kw in query_lower for kw in ["hor", "hours of rest", "compliance", "certificate"]):
            query_type = "compliance"
            intent = "view_compliance_status"
            intent_category = "comply_audit"
            # Check if it's an update action
            if any(kw in query_lower for kw in ["update", "log", "enter", "submit"]):
                intent = "update_hours_of_rest"
                query_type = "mutation"
                requires_mutation = True

        # Aggregation keywords (check before mutations - "what is failing most" is not a mutation)
        elif any(kw in query_lower for kw in AGGREGATION_KEYWORDS):
            query_type = "aggregation"
            intent = "view_failure_stats"
            intent_category = "analytics"

        # Inventory keywords
        elif any(kw in query_lower for kw in ["box", "stock", "inventory", "where is", "location"]):
            query_type = "lookup"
            intent = "view_part_location"
            intent_category = "control_inventory"

        # Mutation keywords (work orders, ordering parts)
        # Note: Many words are ambiguous - "order" can be noun or verb, "update" can be info or action
        # Only trigger mutation for clear command patterns
        elif not any(kw in query_lower for kw in ["hor", "hours of rest", "compliance"]):
            # "order" as command (not "work order", "in order", "what order")
            is_order_mutation = (
                query_lower.startswith("order ") or  # "order 2 filters"
                re.search(r'\border \d+', query_lower) or  # "order 5 parts"
                re.search(r'\border (a|some|more|new)\b', query_lower)  # "order a new filter"
            ) and not re.search(r'(what|which|in) order', query_lower)  # Exclude "what order", "in order"

            # "update" as command (not "update from", "received update")
            is_update_mutation = (
                query_lower.startswith("update ") or
                re.search(r'^(please |can you |i want to )update', query_lower)
            ) and "update from" not in query_lower and "received update" not in query_lower

            # "create/add" as command (typically at start or after please/can you)
            is_create_mutation = re.search(r'^(please |can you |i want to )?(create|add)\b', query_lower)

            # "mark" as command
            is_mark_mutation = re.search(r'^(please |can you )?mark\b', query_lower)

            # "complete" as command (not "completed" in past tense)
            has_complete_command = re.search(r'\bcomplete\b', query_lower) and not re.search(r'\bcompleted\b', query_lower)

            is_mutation = is_order_mutation or is_update_mutation or is_create_mutation or is_mark_mutation or has_complete_command

            if is_mutation:
                query_type = "mutation"
                requires_mutation = True
                if "work order" in query_lower and is_create_mutation:
                    intent = "create_work_order"
                    intent_category = "do_maintenance"
                elif is_order_mutation:
                    intent = "order_part"
                    intent_category = "control_inventory"
                elif has_complete_command or is_mark_mutation:
                    intent = "mark_work_order_complete"
                    intent_category = "do_maintenance"
                elif is_update_mutation:
                    intent = "update_hours_of_rest"  # Default update action
                    intent_category = "comply_audit"
                elif is_create_mutation and "add" in query_lower:
                    intent = "add_work_order_note"
                    intent_category = "do_maintenance"
                elif is_create_mutation:
                    intent = "create_work_order"
                    intent_category = "do_maintenance"

        return ParsedIntent(
            intent=intent,
            intent_category=intent_category,
            query_type=query_type,
            entities={},
            parameters={},
            confidence=0.5,
            requires_mutation=requires_mutation,
            raw_query=query,
        )


# =============================================================================
# ROUTER
# =============================================================================

def route_query(parsed: ParsedIntent) -> Dict:
    """
    Determine how to handle the parsed query.

    Returns routing info:
    {
        "handler": "render|n8n",
        "endpoint": "specific endpoint",
        "method": "GET|POST",
    }
    """
    if parsed.requires_mutation:
        # Mutations go to n8n for workflow control
        return {
            "handler": "n8n",
            "webhook": f"/webhook/{parsed.intent}",
            "method": "POST",
            "payload": {
                "intent": parsed.intent,
                "entities": parsed.entities,
                "parameters": parsed.parameters,
            }
        }

    elif parsed.query_type == "aggregation":
        # Aggregations need SQL generation
        return {
            "handler": "render",
            "endpoint": "/api/analytics",
            "method": "POST",
            "payload": {
                "intent": parsed.intent,
                "parameters": parsed.parameters,
            }
        }

    elif parsed.query_type == "compliance":
        # Compliance checks
        return {
            "handler": "render",
            "endpoint": "/api/compliance",
            "method": "GET",
            "payload": {
                "check_type": parsed.entities.get("compliance_type", "hours_of_rest"),
                "filter": parsed.parameters,
            }
        }

    elif parsed.query_type == "lookup":
        # Simple lookups (inventory, etc)
        return {
            "handler": "render",
            "endpoint": "/api/inventory/lookup",
            "method": "GET",
            "payload": {
                "location": parsed.entities.get("location"),
                "part": parsed.entities.get("part"),
            }
        }

    else:
        # Default: document/knowledge search
        return {
            "handler": "render",
            "endpoint": "/api/search",
            "method": "POST",
            "payload": {
                "query": parsed.raw_query,
                "entities": parsed.entities,
                "intent": parsed.intent,
            }
        }


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def parse_and_route(query: str) -> Dict:
    """
    Main entry point: parse query and determine routing.

    Returns:
    {
        "parsed": {...},
        "routing": {...},
    }
    """
    parser = IntentParser()
    parsed = parser.parse(query)
    routing = route_query(parsed)

    return {
        "parsed": parsed.to_dict(),
        "routing": routing,
    }


if __name__ == "__main__":
    # Test the intent parser
    test_queries = [
        "MTU 16V4000 engine overheating",
        "what machines are failing the most",
        "who hasn't completed their hours of rest",
        "create work order for stabilizer fault",
        "show me box 3d contents",
        "order 2 MTU fuel filters",
        "what work is due today",
    ]

    print("Intent Parser Test")
    print("=" * 70)

    parser = IntentParser()

    for query in test_queries:
        print(f"\nQuery: \"{query}\"")

        # Use fallback if no API key
        parsed = parser.parse(query)
        routing = route_query(parsed)

        print(f"  Intent: {parsed.intent} ({parsed.intent_category})")
        print(f"  Type: {parsed.query_type}")
        print(f"  Mutation: {parsed.requires_mutation}")
        print(f"  Route to: {routing['handler']} → {routing.get('endpoint') or routing.get('webhook')}")
        if parsed.entities:
            print(f"  Entities: {parsed.entities}")

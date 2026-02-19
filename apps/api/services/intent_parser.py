"""
Intent Parser (Module A)
========================

PURPOSE: Understand WHAT the user wants to do with their query.

This is different from Module B (entity extraction):
- Module B extracts WHAT the user is talking about (equipment, parts, symptoms)
- Module A (this file) extracts WHAT ACTION the user wants (create, view, update)

WHY THIS MATTERS:
A query like "MTU engine overheating" could mean:
- SEARCH: "Show me documents about MTU engine overheating"
- TROUBLESHOOT: "Help me diagnose MTU engine overheating"
- CREATE: "Create a work order for MTU engine overheating"

This parser figures out which one the user wants.

HOW IT WORKS:
1. Uses GPT to understand natural language queries
2. Falls back to keyword matching if GPT unavailable
3. Returns intent, query type, entities, and routing info

QUERY TYPES:
- search: Find documents, equipment, parts (default)
- aggregation: Statistics and counts ("how many", "most failing")
- mutation: Create, update, delete (needs confirmation)
- compliance: Hours of rest, certificates, audits
- lookup: Simple lookups (inventory location, stock)

OUTPUT EXAMPLE:
{
    "intent": "view_equipment_history",      # What action
    "intent_category": "manage_equipment",   # Which category
    "query_type": "search",                  # How to handle
    "entities": {"equipment": "generator"},  # What's mentioned
    "parameters": {},                        # Any filters
    "confidence": 0.92,                      # How sure
    "requires_mutation": false               # Changes data?
}
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os      # For reading environment variables (API keys)
import re      # For regex pattern matching in fallback
import json    # For parsing JSON responses from GPT
from typing import Dict, List, Optional, Tuple  # Type hints
from dataclasses import dataclass  # Easy class creation
from enum import Enum  # For fixed option lists


# =============================================================================
# INTENT TAXONOMY (67 actions grouped by category)
# =============================================================================
# This defines ALL possible actions a user might want to do.
# Each category represents a different area of the PMS system.
#
# WHY CATEGORIZE?
# - Helps route queries to the right handler
# - Helps GPT understand the domain
# - Makes it easier to add new intents

INTENT_CATEGORIES = {
    # =========================================================================
    # FIX SOMETHING - Actions related to faults and troubleshooting
    # =========================================================================
    "fix_something": [
        "diagnose_fault",              # "What's wrong with the generator?"
        "report_fault",                # "Report a fault on the bilge pump"
        "show_manual_section",         # "Show me the overheating section"
        "view_fault_history",          # "What faults has this equipment had?"
        "suggest_parts",               # "What parts do I need for this fix?"
        "create_work_order_from_fault",# "Create a WO for this fault"
        "add_fault_note",              # "Add a note to this fault"
        "add_fault_photo",             # "Add a photo to this fault"
        "link_equipment_to_fault",     # "Link this fault to the generator"
    ],

    # =========================================================================
    # DO MAINTENANCE - Actions related to work orders
    # =========================================================================
    "do_maintenance": [
        "create_work_order",           # "Create work order for oil change"
        "view_work_order_history",     # "Show me past work orders"
        "mark_work_order_complete",    # "Mark WO-123 as complete"
        "complete_work_order",         # Same as above
        "add_work_order_note",         # "Add a note to this work order"
        "add_work_order_photo",        # "Add a photo to this work order"
        "add_parts_to_work_order",     # "Add filter to work order"
        "link_parts_to_work_order",    # Same as above
        "view_work_order_checklist",   # "Show the checklist for this WO"
        "assign_work_order",           # "Assign this to 2nd engineer"
        "edit_work_order_details",     # "Change the priority to high"
        "view_checklist",              # "Show the inspection checklist"
        "mark_checklist_item_complete",# "Mark step 3 as done"
    ],

    # =========================================================================
    # MANAGE EQUIPMENT - Actions related to equipment records
    # =========================================================================
    "manage_equipment": [
        "view_equipment_details",      # "Show me the generator details"
        "view_equipment_history",      # "What work has been done on this?"
        "view_equipment_parts",        # "What parts are linked to this?"
        "view_linked_faults",          # "What faults has this had?"
        "view_equipment_manual",       # "Show me the generator manual"
        "add_equipment_note",          # "Add a note to this equipment"
        "request_predictive_insight",  # "When will this likely fail?"
        "view_smart_summary",          # "Give me a summary of this equipment"
    ],

    # =========================================================================
    # CONTROL INVENTORY - Actions related to parts and stock
    # =========================================================================
    "control_inventory": [
        "view_part_stock",             # "How many oil filters do we have?"
        "add_part",                    # "Add a new part to inventory"
        "order_part",                  # "Order 2 MTU fuel filters"
        "view_part_location",          # "Where is the impeller stored?"
        "view_part_usage",             # "How many have we used?"
        "log_part_usage",              # "Log that I used 2 filters"
        "edit_part_quantity",          # "Update stock to 5"
        "scan_part_barcode",           # "Scan this barcode"
        "view_linked_equipment",       # "What equipment uses this part?"
    ],

    # =========================================================================
    # COMMUNICATE STATUS - Actions related to handover and notes
    # =========================================================================
    "communicate_status": [
        "add_to_handover",             # "Add this to the handover"
        "add_document_to_handover",    # "Add this document to handover"
        "add_predictive_insight_to_handover",  # "Add this insight to handover"
        "edit_handover_section",       # "Edit the engine room section"
        "export_handover",             # "Export the handover as PDF"
        "regenerate_handover_summary", # "Regenerate the AI summary"
        "upload_photo",                # "Upload a photo"
        "record_voice_note",           # "Record a voice note"
    ],

    # =========================================================================
    # COMPLY AUDIT - Actions related to compliance and regulations
    # =========================================================================
    "comply_audit": [
        "view_hours_of_rest",          # "Show my hours of rest"
        "update_hours_of_rest",        # "Log my hours for today"
        "export_hours_of_rest",        # "Export HOR for the month"
        "view_compliance_status",      # "Who hasn't completed HOR?"
        "tag_for_survey",              # "Flag this for next survey"
    ],

    # =========================================================================
    # PROCURE SUPPLIERS - Actions related to purchasing
    # =========================================================================
    "procure_suppliers": [
        "create_purchase_request",     # "Start a purchase request"
        "add_item_to_purchase",        # "Add filters to the order"
        "approve_purchase",            # "Approve this purchase"
        "upload_invoice",              # "Upload the invoice"
        "track_delivery",              # "Where is my order?"
        "log_delivery_received",       # "Mark the delivery as received"
        "update_purchase_status",      # "Update purchase status"
    ],

    # =========================================================================
    # SEARCH DOCUMENTS - Actions related to finding documents
    # =========================================================================
    "search_documents": [
        "find_document",               # "Find the MTU manual"
        "view_document",               # "Open the maintenance schedule"
        "view_related_documents",      # "Show related documents"
        "view_document_section",       # "Show the overheating section"
    ],

    # =========================================================================
    # ANALYTICS - Actions related to statistics and reports
    # =========================================================================
    "analytics": [
        "view_failure_stats",          # "What machines fail the most?"
        "view_maintenance_stats",      # "How many WOs this month?"
        "view_inventory_stats",        # "What parts are low on stock?"
        "view_compliance_stats",       # "How is our compliance?"
    ],

    # =========================================================================
    # MANAGE CERTIFICATES - Actions related to vessel and crew certificates
    # =========================================================================
    "manage_certificates": [
        # READ OPERATIONS
        "list_vessel_certificates",    # "Show all vessel certificates"
        "list_crew_certificates",      # "Show all crew certificates"
        "get_certificate_details",     # "Show ISM certificate details"
        "view_certificate_history",    # "Show certificate history"
        "find_expiring_certificates",  # "What certificates expire this month?"

        # WRITE OPERATIONS (gated/confirmation required)
        "create_vessel_certificate",   # "Create new class certificate"
        "create_crew_certificate",     # "Create STCW certificate for John"
        "update_certificate",          # "Update certificate expiry date"
        "link_document_to_certificate",# "Link PDF to ISM certificate"
        "supersede_certificate",       # "Supersede class certificate" (SIGNED)
        "delete_certificate",          # "Delete certificate" (Manager-only)
    ],
}

# Create a flat list of all intents for validation
# This is used to check if a GPT response is valid
ALL_INTENTS = []
for category, intents in INTENT_CATEGORIES.items():
    ALL_INTENTS.extend(intents)
# Result: ALL_INTENTS = ["diagnose_fault", "report_fault", ..., "view_compliance_stats"]


# =============================================================================
# QUERY TYPES
# =============================================================================
# Query types determine HOW to handle the query.
# Different types are routed to different endpoints.

class QueryType(Enum):
    """
    The type of query determines how it should be processed.
    """
    SEARCH = "search"           # Find documents, equipment, parts
                                # → Route to: /api/search

    AGGREGATION = "aggregation" # Stats, counts, "most/least" queries
                                # → Route to: /api/analytics
                                # Example: "what fails the most"

    MUTATION = "mutation"       # Create, update, delete
                                # → Route to: n8n workflow
                                # Requires confirmation before executing

    COMPLIANCE = "compliance"   # HOR, certificates, audits
                                # → Route to: /api/compliance
                                # Example: "who hasn't completed HOR"

    LOOKUP = "lookup"           # Simple lookups (inventory location, stock)
                                # → Route to: /api/inventory/lookup
                                # Example: "where is box 3d"


# =============================================================================
# MUTATION INTENTS - Actions that change data
# =============================================================================
# These intents modify the database and require special handling:
# - Route to n8n workflow (not direct API call)
# - May require user confirmation
# - Logged for audit trail

MUTATION_INTENTS = {
    # Work order mutations
    "create_work_order",               # Creates a new work order
    "create_work_order_from_fault",    # Creates WO linked to a fault
    "mark_work_order_complete",        # Marks WO as done
    "complete_work_order",             # Same as above
    "add_work_order_note",             # Adds a note to WO
    "add_work_order_photo",            # Adds a photo to WO
    "assign_work_order",               # Assigns WO to crew member
    "edit_work_order_details",         # Edits WO fields

    # Fault mutations
    "add_fault_note",                  # Adds note to fault
    "add_fault_photo",                 # Adds photo to fault
    "report_fault",                    # Creates new fault report

    # Inventory mutations
    "order_part",                      # Creates purchase request
    "add_part",                        # Adds new part to inventory
    "log_part_usage",                  # Logs part consumption
    "edit_part_quantity",              # Updates stock count

    # Handover mutations
    "add_to_handover",                 # Adds item to handover
    "edit_handover_section",           # Edits handover content

    # Compliance mutations
    "update_hours_of_rest",            # Logs crew rest hours

    # Procurement mutations
    "create_purchase_request",         # Starts new purchase
    "approve_purchase",                # Approves purchase
    "log_delivery_received",           # Marks delivery complete

    # Certificate mutations (compliance-critical)
    "create_vessel_certificate",       # Creates vessel certificate
    "create_crew_certificate",         # Creates crew certificate
    "update_certificate",              # Updates certificate details
    "link_document_to_certificate",    # Links document to certificate
    "supersede_certificate",           # Supersedes certificate (SIGNED action)
    "delete_certificate",              # Deletes certificate (Manager-only)
}


# =============================================================================
# AGGREGATION KEYWORDS
# =============================================================================
# When a query contains these words, it's likely asking for statistics.
# Example: "what fails the MOST" → aggregation

AGGREGATION_KEYWORDS = [
    "most",         # "what fails most"
    "least",        # "what fails least"
    "failing",      # "what is failing"
    "common",       # "most common fault"
    "frequent",     # "most frequent issue"
    "stats",        # "show me stats"
    "how many",     # "how many work orders"
    "count",        # "count of faults"
    "total",        # "total this month"
    "average",      # "average time"
    "summary",      # "summary of failures"
    "trend",        # "trend over time"
    "overdue",      # "what is overdue"
    "due today",    # "what is due today"
    "due this week",# "what is due this week"
    "pending",      # "pending work orders"
]


# =============================================================================
# GPT SYSTEM PROMPT
# =============================================================================
# This is the instruction given to GPT that tells it how to parse queries.
# It includes:
# - Role description
# - What to extract
# - Categories and types
# - Output format
# - Examples

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
- comply_audit: hours of rest, compliance
- manage_certificates: vessel/crew certificates (ISM, ISPS, STCW, MLC, ENG1, class)
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
    "measurement": "any measurement or null",
    "certificate_type": "ISM|ISPS|STCW|MLC|CLASS|ENG1|SOLAS|GMDSS or null"
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

Query: "show ISM certificate expiry"
{
  "intent": "get_certificate_details",
  "intent_category": "manage_certificates",
  "query_type": "compliance",
  "entities": {
    "certificate_type": "ISM"
  },
  "parameters": {
    "filter_by": "certificate_type",
    "filter_value": "ISM"
  },
  "confidence": 0.91,
  "requires_mutation": false
}

Query: "what certificates expire next month"
{
  "intent": "find_expiring_certificates",
  "intent_category": "manage_certificates",
  "query_type": "compliance",
  "entities": {
    "time_range": "next_month"
  },
  "parameters": {
    "filter_by": "expiry_date",
    "filter_value": "next_month"
  },
  "confidence": 0.90,
  "requires_mutation": false
}

Query: "create STCW certificate for John Smith"
{
  "intent": "create_crew_certificate",
  "intent_category": "manage_certificates",
  "query_type": "mutation",
  "entities": {
    "certificate_type": "STCW",
    "person": "John Smith"
  },
  "parameters": {},
  "confidence": 0.93,
  "requires_mutation": true
}

Query: "supersede class certificate with renewal"
{
  "intent": "supersede_certificate",
  "intent_category": "manage_certificates",
  "query_type": "mutation",
  "entities": {
    "certificate_type": "CLASS"
  },
  "parameters": {
    "action": "supersede",
    "reason": "renewal"
  },
  "confidence": 0.92,
  "requires_mutation": true
}
"""


# =============================================================================
# PARSED INTENT DATA CLASS
# =============================================================================
# Container for the result of intent parsing.
# Uses @dataclass for automatic __init__ and other methods.

@dataclass
class ParsedIntent:
    """
    Result of intent parsing.

    Attributes:
        intent: The specific action detected (e.g., "create_work_order")
        intent_category: The category of action (e.g., "do_maintenance")
        query_type: How to process the query (search, aggregation, etc.)
        entities: Extracted entities (equipment, parts, people, etc.)
        parameters: Query parameters (filters, limits, etc.)
        confidence: How confident we are (0.0 to 1.0)
        requires_mutation: True if this changes data
        raw_query: The original query text
    """
    intent: str              # e.g., "create_work_order"
    intent_category: str     # e.g., "do_maintenance"
    query_type: str          # e.g., "mutation"
    entities: Dict           # e.g., {"equipment": "stabilizer"}
    parameters: Dict         # e.g., {"filter_by": "status"}
    confidence: float        # e.g., 0.92
    requires_mutation: bool  # e.g., True
    raw_query: str           # e.g., "create work order for stabilizer"

    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all fields except raw_query
        """
        return {
            "intent": self.intent,
            "intent_category": self.intent_category,
            "query_type": self.query_type,
            "entities": self.entities,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "requires_mutation": self.requires_mutation,
        }


# =============================================================================
# INTENT PARSER CLASS
# =============================================================================

class IntentParser:
    """
    Parses user queries to extract intent and entities.

    METHODS:
        parse(query) - Parse a query using GPT (or fallback)
        _fallback_parse(query) - Simple keyword-based parsing

    USAGE:
        parser = IntentParser()
        result = parser.parse("create work order for generator")
        print(result.intent)  # "create_work_order"
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the intent parser.

        Args:
            model: Which GPT model to use (default: gpt-4o-mini)
                   gpt-4o-mini is fast and cheap, good for intent parsing
        """
        self.model = model
        # Get OpenAI API key from environment variable
        # If not set, we'll use fallback parsing
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def parse(self, query: str) -> ParsedIntent:
        """
        Parse a user query to extract intent and entities.

        HOW IT WORKS:
        1. If no API key, use fallback (keyword matching)
        2. Call GPT with the query and system prompt
        3. Parse the JSON response
        4. Return structured ParsedIntent

        Args:
            query: The user's natural language query

        Returns:
            ParsedIntent with classified intent and extracted entities
        """
        # Check if we have API key
        if not self.api_key:
            # No API key - use simple keyword matching
            return self._fallback_parse(query)

        try:
            # Import OpenAI and create client
            import openai
            client = openai.OpenAI(api_key=self.api_key)

            # Call GPT API
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},  # Instructions
                    {"role": "user", "content": query}              # User's query
                ],
                temperature=0.1,   # Low temperature = consistent results
                max_tokens=500,    # Limit response length (saves money)
            )

            # Extract response text
            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            result = json.loads(result_text)

            # Build and return ParsedIntent
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
            # If GPT fails, fall back to keyword matching
            print(f"GPT parsing error: {e}")
            return self._fallback_parse(query)

    def _fallback_parse(self, query: str) -> ParsedIntent:
        """
        Simple heuristic fallback when GPT unavailable.

        This uses keyword matching to determine intent.
        Less accurate than GPT but works without API key.

        PRIORITY ORDER:
        1. Compliance (hours of rest, certificates)
        2. Aggregation (statistics queries)
        3. Inventory lookup
        4. Mutations (create, update, delete)
        5. Default to search

        Args:
            query: The user's query

        Returns:
            ParsedIntent with best-guess intent
        """
        query_lower = query.lower()

        # Start with defaults
        query_type = "search"
        intent = "find_document"
        intent_category = "search_documents"
        requires_mutation = False

        # =====================================================================
        # CHECK 1: CERTIFICATE QUERIES (check first - compliance-critical)
        # =====================================================================
        # Certificate queries have specific intents in manage_certificates
        certificate_keywords = [
            "certificate", "cert", "ism", "isps", "stcw", "mlc", "solas",
            "eng1", "eng 1", "class cert", "gmdss", "coc", "bst"
        ]
        if any(kw in query_lower for kw in certificate_keywords):
            query_type = "compliance"
            intent_category = "manage_certificates"

            # Determine specific certificate intent
            if any(kw in query_lower for kw in ["expir", "due", "renew"]):
                intent = "find_expiring_certificates"
            elif any(kw in query_lower for kw in ["list", "show all", "all cert"]):
                if any(kw in query_lower for kw in ["crew", "stcw", "eng1", "gmdss", "coc"]):
                    intent = "list_crew_certificates"
                else:
                    intent = "list_vessel_certificates"
            elif any(kw in query_lower for kw in ["history", "audit", "log"]):
                intent = "view_certificate_history"
            elif any(kw in query_lower for kw in ["supersede", "replace"]):
                intent = "supersede_certificate"
                query_type = "mutation"
                requires_mutation = True
            elif re.search(r'^(please |can you |i want to )?(create|add)\b', query_lower):
                if any(kw in query_lower for kw in ["crew", "stcw", "eng1", "gmdss", "coc"]):
                    intent = "create_crew_certificate"
                else:
                    intent = "create_vessel_certificate"
                query_type = "mutation"
                requires_mutation = True
            elif any(kw in query_lower for kw in ["update", "edit", "change"]):
                intent = "update_certificate"
                query_type = "mutation"
                requires_mutation = True
            elif any(kw in query_lower for kw in ["link", "attach"]):
                intent = "link_document_to_certificate"
                query_type = "mutation"
                requires_mutation = True
            elif any(kw in query_lower for kw in ["delete", "remove"]):
                intent = "delete_certificate"
                query_type = "mutation"
                requires_mutation = True
            else:
                intent = "get_certificate_details"

        # =====================================================================
        # CHECK 2: COMPLIANCE QUERIES (HOR and general compliance)
        # =====================================================================
        # "who hasn't completed HOR" should NOT trigger mutation just because
        # "completed" is in the query. Check compliance keywords first.
        elif any(kw in query_lower for kw in ["hor", "hours of rest", "compliance"]):
            query_type = "compliance"
            intent = "view_compliance_status"
            intent_category = "comply_audit"

            # But if they explicitly say "update" or "log", it IS a mutation
            if any(kw in query_lower for kw in ["update", "log", "enter", "submit"]):
                intent = "update_hours_of_rest"
                query_type = "mutation"
                requires_mutation = True

        # =====================================================================
        # CHECK 3: AGGREGATION QUERIES
        # =====================================================================
        # "what is failing most" is aggregation, not mutation
        elif any(kw in query_lower for kw in AGGREGATION_KEYWORDS):
            query_type = "aggregation"
            intent = "view_failure_stats"
            intent_category = "analytics"

        # =====================================================================
        # CHECK 4: INVENTORY LOOKUP
        # =====================================================================
        # "where is box 3d" or "check stock" are lookups
        elif any(kw in query_lower for kw in ["box", "stock", "inventory", "where is", "location"]):
            query_type = "lookup"
            intent = "view_part_location"
            intent_category = "control_inventory"

        # =====================================================================
        # CHECK 5: MUTATION QUERIES (create, update, delete)
        # =====================================================================
        # CAUTION: Words like "order" and "update" are ambiguous
        # "order" can be noun ("work order") or verb ("order parts")
        # "update" can be noun ("received update") or verb ("update the record")
        # Only trigger mutation for clear command patterns
        elif not any(kw in query_lower for kw in ["hor", "hours of rest", "compliance"]):

            # ------------------------------------
            # "order" as command (not "work order")
            # ------------------------------------
            # GOOD: "order 2 filters" → mutation
            # BAD: "what work order" → not mutation
            is_order_mutation = (
                query_lower.startswith("order ") or           # "order 2 filters"
                re.search(r'\border \d+', query_lower) or     # "order 5 parts"
                re.search(r'\border (a|some|more|new)\b', query_lower)  # "order a new filter"
            ) and not re.search(r'(what|which|in) order', query_lower)  # Exclude "what order", "in order"

            # ------------------------------------
            # "update" as command
            # ------------------------------------
            # GOOD: "update the hours" → mutation
            # BAD: "received an update" → not mutation
            is_update_mutation = (
                query_lower.startswith("update ") or
                re.search(r'^(please |can you |i want to )update', query_lower)
            ) and "update from" not in query_lower and "received update" not in query_lower

            # ------------------------------------
            # "create/add" as command
            # ------------------------------------
            # Usually at start or after "please", "can you"
            is_create_mutation = re.search(r'^(please |can you |i want to )?(create|add)\b', query_lower)

            # ------------------------------------
            # "mark" as command
            # ------------------------------------
            is_mark_mutation = re.search(r'^(please |can you )?mark\b', query_lower)

            # ------------------------------------
            # "complete" as command (not "completed" past tense)
            # ------------------------------------
            # GOOD: "complete the work order" → mutation
            # BAD: "who hasn't completed HOR" → not mutation (query about completion)
            has_complete_command = re.search(r'\bcomplete\b', query_lower) and not re.search(r'\bcompleted\b', query_lower)

            # Combine all mutation checks
            is_mutation = is_order_mutation or is_update_mutation or is_create_mutation or is_mark_mutation or has_complete_command

            if is_mutation:
                query_type = "mutation"
                requires_mutation = True

                # Determine specific intent based on what kind of mutation
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

        # Return the parsed result
        return ParsedIntent(
            intent=intent,
            intent_category=intent_category,
            query_type=query_type,
            entities={},          # Fallback doesn't extract entities
            parameters={},        # Fallback doesn't extract parameters
            confidence=0.5,       # Lower confidence for fallback
            requires_mutation=requires_mutation,
            raw_query=query,
        )


# =============================================================================
# ROUTER FUNCTION
# =============================================================================
# Determines WHERE to send the query based on parsed intent

def route_query(parsed: ParsedIntent) -> Dict:
    """
    Determine how to handle the parsed query.

    ROUTING LOGIC:
    - Mutations → n8n (workflow engine for complex operations)
    - Aggregations → /api/analytics (SQL query generation)
    - Compliance → /api/compliance (HOR checks, certificates)
    - Lookups → /api/inventory/lookup (simple database lookup)
    - Everything else → /api/search (document/knowledge search)

    Args:
        parsed: The ParsedIntent from the parser

    Returns:
        Dict with routing information:
        {
            "handler": "render|n8n",      # Which system handles it
            "endpoint": "/api/...",        # Which endpoint (if render)
            "webhook": "/webhook/...",     # Which webhook (if n8n)
            "method": "GET|POST",          # HTTP method
            "payload": {...}               # Data to send
        }
    """
    # =========================================================================
    # MUTATIONS → n8n
    # =========================================================================
    # Mutations need workflow control:
    # - Validation before execution
    # - Confirmation from user
    # - Audit logging
    # - Complex multi-step operations
    if parsed.requires_mutation:
        return {
            "handler": "n8n",                      # Route to n8n workflow engine
            "webhook": f"/webhook/{parsed.intent}", # Specific webhook for this intent
            "method": "POST",                       # POST = send data
            "payload": {
                "intent": parsed.intent,
                "entities": parsed.entities,
                "parameters": parsed.parameters,
            }
        }

    # =========================================================================
    # AGGREGATIONS → /api/analytics
    # =========================================================================
    # Statistics queries need SQL generation
    elif parsed.query_type == "aggregation":
        return {
            "handler": "render",
            "endpoint": "/api/analytics",
            "method": "POST",
            "payload": {
                "intent": parsed.intent,
                "parameters": parsed.parameters,
            }
        }

    # =========================================================================
    # COMPLIANCE → /api/compliance
    # =========================================================================
    # Hours of rest, certificate checks, etc.
    elif parsed.query_type == "compliance":
        return {
            "handler": "render",
            "endpoint": "/api/compliance",
            "method": "GET",
            "payload": {
                "check_type": parsed.entities.get("compliance_type", "hours_of_rest"),
                "filter": parsed.parameters,
            }
        }

    # =========================================================================
    # LOOKUPS → /api/inventory/lookup
    # =========================================================================
    # Simple database lookups (inventory location, stock)
    elif parsed.query_type == "lookup":
        return {
            "handler": "render",
            "endpoint": "/api/inventory/lookup",
            "method": "GET",
            "payload": {
                "location": parsed.entities.get("location"),
                "part": parsed.entities.get("part"),
            }
        }

    # =========================================================================
    # DEFAULT: SEARCH → /api/search
    # =========================================================================
    # Document and knowledge search (most common)
    else:
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
# MAIN ENTRY POINT
# =============================================================================

def parse_and_route(query: str) -> Dict:
    """
    Main entry point: parse query and determine routing.

    This is the function that other modules call.

    USAGE:
        result = parse_and_route("create work order for generator")
        # result = {
        #     "parsed": {...},   # ParsedIntent as dict
        #     "routing": {...},  # Routing info
        # }

    Args:
        query: The user's natural language query

    Returns:
        Dict with parsed intent and routing information
    """
    # Create parser
    parser = IntentParser()

    # Parse the query
    parsed = parser.parse(query)

    # Determine routing
    routing = route_query(parsed)

    # Return combined result
    return {
        "parsed": parsed.to_dict(),
        "routing": routing,
    }


# =============================================================================
# TEST CODE - Runs when file is executed directly
# =============================================================================
# Usage: python intent_parser.py

if __name__ == "__main__":
    # Test queries covering different intent types
    test_queries = [
        "MTU 16V4000 engine overheating",         # search
        "what machines are failing the most",      # aggregation
        "who hasn't completed their hours of rest",# compliance
        "create work order for stabilizer fault",  # mutation
        "show me box 3d contents",                 # lookup
        "order 2 MTU fuel filters",                # mutation
        "what work is due today",                  # aggregation
        # Certificate queries
        "show ISM certificate",                    # certificate read
        "what certificates expire next month",     # certificate expiry
        "list all crew certificates",              # certificate list
        "create STCW certificate for John",        # certificate mutation
        "supersede class certificate",             # certificate supersede (signed)
    ]

    print("Intent Parser Test")
    print("=" * 70)

    # Create parser
    parser = IntentParser()

    # Test each query
    for query in test_queries:
        print(f"\nQuery: \"{query}\"")

        # Parse the query
        parsed = parser.parse(query)
        routing = route_query(parsed)

        # Show results
        print(f"  Intent: {parsed.intent} ({parsed.intent_category})")
        print(f"  Type: {parsed.query_type}")
        print(f"  Mutation: {parsed.requires_mutation}")
        print(f"  Route to: {routing['handler']} → {routing.get('endpoint') or routing.get('webhook')}")
        if parsed.entities:
            print(f"  Entities: {parsed.entities}")

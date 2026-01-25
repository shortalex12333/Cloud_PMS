"""
Module A: Strict Micro-Action & Intent Detector
================================================

=== PLAIN ENGLISH SUMMARY ===
This file detects WHAT THE USER WANTS TO DO (their action/intent).
It looks for VERBS at the start of queries to identify actions.

=== THE KEY DIFFERENCE FROM MODULE B ===
- Module B (entity_extractor): Finds THINGS mentioned (brands, equipment, symptoms)
- Module A (this file): Finds ACTIONS requested (create, view, update, diagnose)

Example:
  Query: "Create work order for bilge pump"
  - Module A detects: ACTION = "create_work_order" (verb: "create")
  - Module B detects: ENTITY = "bilge pump" (equipment)

=== STRICT DESIGN RULES ===
1. ONLY match if query starts with an explicit VERB (create, show, update, etc.)
2. NEVER match on maritime terms alone (pumps, valves, engines)
3. NEVER let fault codes trigger actions (E047 is an entity, not an action)
4. Confidence scores show how sure we are about the detection

=== WHY STRICT RULES? ===
Without these rules, we'd have false positives:
- BAD: "bilge manifold" → interpreted as action (it's just equipment!)
- BAD: "E047 engine fault" → interpreted as action (it's a fault code!)
- GOOD: "create work order" → correctly detected as action
- GOOD: "diagnose E047" → correctly detected as action (starts with "diagnose" verb)

=== SUPPORTED ACTIONS ===
This module detects 31+ specific actions in 8 categories:
1. Work Orders: create, list, update, close, add_note
2. History: view_history, show_equipment_history
3. Handover: add_to, export, view
4. Faults: report, diagnose, acknowledge
5. Inventory: check_stock, order_parts
6. Documents: upload, search, show_manual_section
7. Hours of Rest: log
8. Certificates: create_vessel, create_crew, update, supersede, link_document, list, find_expiring, view_history

STRICT RULES:
- Only verb-based action patterns
- NO phrasal regex ("find the", "tell me", "where is")
- NO patterns that could match maritime terms
- Confidence scoring required
- Maritime nouns CANNOT trigger actions
- Fault codes NEVER trigger actions

This module detects what the user WANTS TO DO, not what they're talking about.
"""

# =============================================================================
# IMPORTS
# =============================================================================

# re: Python's regular expression library for pattern matching
# Used to match verb patterns like "create work order", "show history"
import re

# typing: Type hints for better code documentation
# List = array, Dict = dictionary, Optional = can be None
from typing import List, Dict, Optional

# dataclass: Shortcut for creating simple data-holding classes
from dataclasses import dataclass


# =============================================================================
# DATA CLASS - ActionDetection
# =============================================================================

@dataclass
class ActionDetection:
    """
    Represents a detected action from the user's query.

    === WHAT THIS STORES ===
    When we detect "create work order for bilge pump", we create:
    - action: "create_work_order" (the standardized action name)
    - confidence: 0.95 (how sure we are)
    - matched_text: "create work order" (what we actually matched)
    - verb: "create" (the verb that triggered the match)

    === WHY TRACK ALL THIS? ===
    - action: To route the query to the right handler (n8n for mutations)
    - confidence: To decide if we should act or ask for clarification
    - matched_text: For debugging - what part of query triggered this
    - verb: For analytics and understanding user patterns
    """

    # The standardized action name
    # Examples: "create_work_order", "view_history", "diagnose_fault"
    action: str

    # How confident we are about this detection (0.0 to 1.0)
    # 0.95+ = very confident, 0.8-0.95 = confident, <0.8 = less sure
    confidence: float

    # The exact text that matched our pattern
    # Useful for debugging: "create work order", "show history"
    matched_text: str

    # The verb that triggered the match
    # Examples: "create", "show", "update", "diagnose"
    verb: str

    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with action, confidence, matched_text, verb
        """
        return {
            "action": self.action,
            "confidence": self.confidence,
            "matched_text": self.matched_text,
            "verb": self.verb
        }


# =============================================================================
# MAIN CLASS - StrictMicroActionDetector
# =============================================================================

class StrictMicroActionDetector:
    """
    Detects micro-actions from user queries using STRICT verb-based patterns.

    === DESIGN PHILOSOPHY ===
    We use STRICT matching because:
    1. False positives are worse than false negatives
       - Better to not detect an action than to incorrectly detect one
    2. Maritime terms should never accidentally trigger actions
       - "bilge pump" should NOT trigger any action
       - "create work order for bilge pump" SHOULD trigger create_work_order
    3. Verbs are the key indicator of user intent
       - Nouns describe things, verbs describe actions
       - We only match on verbs

    === HOW IT WORKS ===
    1. User types query: "create work order for generator"
    2. We check query against verb patterns: "^create work order" matches!
    3. We calculate confidence based on pattern specificity
    4. We return ActionDetection with action="create_work_order", confidence=0.95

    === PATTERN FORMAT ===
    Each action has multiple patterns, each with:
    - Regex pattern (using ^ for start-of-string when needed)
    - Base confidence (how specific this pattern is)
    - Verb (the verb that triggers this pattern)

    Design principles:
    1. Actions must start with explicit verbs
    2. No ambiguous phrases
    3. No patterns that could match entity descriptions
    4. Confidence based on pattern specificity
    """

    def __init__(self):
        """
        Initialize the detector with all action patterns.

        === PATTERN STRUCTURE ===
        self.action_patterns is a dictionary:
        - Key: action name (e.g., "create_work_order")
        - Value: list of (pattern, confidence, verb) tuples

        Each pattern tuple contains:
        - pattern: Regex string to match (e.g., "^create\\s+work\\s*order")
        - confidence: Base confidence if matched (e.g., 0.95)
        - verb: The verb that triggers this (e.g., "create")
        """

        # =================================================================
        # ACTION PATTERNS DICTIONARY
        # =================================================================
        # Format: action_name -> [(pattern, base_confidence, verb), ...]
        #
        # REGEX SYNTAX EXPLAINED:
        # ^        = Must be at START of query
        # \\s+     = One or more whitespace characters
        # \\s*     = Zero or more whitespace characters
        # (a\\s+)? = Optional "a " (question mark = optional)
        # word1|word2 = Either word1 OR word2

        self.action_patterns = {

            # =============================================================
            # WORK ORDER ACTIONS - Create, List, Update, Close
            # =============================================================
            # These actions modify work orders in the database.
            # Detected mutations are routed to n8n for processing.

            "create_work_order": [
                # "create work order" or "create a work order" or "create a new work order"
                # ^ = must start with "create"
                # (a\\s+)? = optional "a " in the middle
                # (new\\s+)? = optional "new " in the middle
                # work\\s*order = "work order" or "workorder"
                (r"^create\s+(a\s+)?(new\s+)?work\s*order", 0.95, "create"),

                # "open work order" - same structure as create
                (r"^open\s+(a\s+)?(new\s+)?work\s*order", 0.95, "open"),

                # "raise work order" - British English style
                (r"^raise\s+(a\s+)?work\s*order", 0.92, "raise"),

                # "generate work order" - more formal
                (r"^generate\s+work\s*order", 0.90, "generate"),

                # "add work order" - less common but valid
                (r"^add\s+(a\s+)?work\s*order", 0.88, "add"),

                # "log work order" - alternative phrasing
                (r"^log\s+(a\s+)?work\s*order", 0.88, "log"),
            ],

            "list_work_orders": [
                # "show work orders" or "show all work orders" or "show open work orders"
                # (all\\s+)? = optional "all "
                # (open\\s+|pending\\s+|active\\s+)? = optional status word
                (r"^show\s+(all\s+)?(open\s+|pending\s+|active\s+)?work\s*orders", 0.93, "show"),

                # "list work orders" - straightforward
                (r"^list\s+(all\s+)?(open\s+)?work\s*orders", 0.93, "list"),

                # "view work orders"
                (r"^view\s+(all\s+)?work\s*orders", 0.90, "view"),

                # "display work orders"
                (r"^display\s+work\s*orders", 0.90, "display"),
            ],

            "update_work_order": [
                # "update work order" or "update the work order"
                # (the\\s+)? = optional "the "
                (r"^update\s+(the\s+)?work\s*order", 0.93, "update"),

                # "edit work order"
                (r"^edit\s+(the\s+)?work\s*order", 0.93, "edit"),

                # "modify work order"
                (r"^modify\s+(the\s+)?work\s*order", 0.90, "modify"),

                # "change work order" - less common
                (r"^change\s+(the\s+)?work\s*order", 0.88, "change"),
            ],

            "close_work_order": [
                # "close work order" - most direct
                (r"^close\s+(the\s+)?work\s*order", 0.95, "close"),

                # "complete work order" - marks as done
                (r"^complete\s+(the\s+)?work\s*order", 0.93, "complete"),

                # "finish work order" - alternative
                (r"^finish\s+(the\s+)?work\s*order", 0.90, "finish"),
            ],

            # =============================================================
            # HISTORY/DATA ACTIONS - View Past Records
            # =============================================================
            # Users want to see historical data about equipment/maintenance.

            "view_history": [
                # "show me the history" or "show historic data" or "show historical records"
                # (me\\s+)? = optional "me "
                # historic|history|historical = any of these words
                # (data|records?)? = optional "data" or "record(s)"
                (r"^show\s+(me\s+)?(the\s+)?(historic|history|historical)(\s+(data|records?))?", 0.93, "show"),

                # FIX #2: REMOVED mid-sentence pattern
                # OLD: (r"show\s+(historic|history)...", 0.90, "show")
                # This violated strict verb-first rule since it lacked ^ anchor
                # Now using match() instead of search(), all patterns must start at index 0

                # "view history"
                (r"^view\s+(the\s+)?(historic|history|historical)", 0.92, "view"),

                # "display history"
                (r"^display\s+(the\s+)?history", 0.90, "display"),

                # "get history"
                (r"^get\s+(the\s+)?history", 0.88, "get"),
            ],

            # =============================================================
            # HANDOVER ACTIONS - Shift Handover Notes
            # =============================================================
            # Handover = notes passed between crew shifts.
            # Critical for maritime operations continuity.

            "add_to_handover": [
                # "add this to handover" or "add it to the handover"
                # (this\\s+|it\\s+)? = optional "this " or "it "
                (r"^add\s+(this\s+|it\s+)?to\s+(the\s+)?handover", 0.95, "add"),

                # "put in handover"
                (r"^put\s+in\s+handover", 0.90, "put"),

                # "include in handover"
                (r"^include\s+in\s+handover", 0.88, "include"),
            ],

            "export_handover": [
                # "export handover" - download as file
                (r"^export\s+(the\s+)?handover", 0.95, "export"),

                # "download handover"
                (r"^download\s+(the\s+)?handover", 0.93, "download"),

                # "generate handover" - create document
                (r"^generate\s+(the\s+)?handover", 0.90, "generate"),
            ],

            "view_handover": [
                # "view handover"
                (r"^view\s+(the\s+)?handover", 0.92, "view"),

                # "show handover"
                (r"^show\s+(the\s+)?handover", 0.92, "show"),

                # "display handover"
                (r"^display\s+handover", 0.90, "display"),
            ],

            # =============================================================
            # FAULT ACTIONS - Report, Diagnose, Acknowledge
            # =============================================================
            # Faults = equipment problems that need attention.
            # These actions manage the fault lifecycle.

            "report_fault": [
                # "report fault" - new fault detected
                (r"^report\s+(a\s+)?fault", 0.95, "report"),

                # "log fault" - record in system
                (r"^log\s+(a\s+)?fault", 0.93, "log"),

                # "raise fault" - British English
                (r"^raise\s+(a\s+)?fault", 0.90, "raise"),
            ],

            "diagnose_fault": [
                # "diagnose fault" - troubleshoot
                (r"^diagnose\s+(the\s+)?fault", 0.95, "diagnose"),

                # "diagnose E047" or "diagnose P0420" - fault code patterns
                # [EePp]\\d{3,4} = E or P followed by 3-4 digits
                # IMPORTANT: This matches "diagnose" + fault code
                # The fault code alone (E047) does NOT trigger this - only with verb!
                (r"^diagnose\s+[EePp]\d{3,4}", 0.93, "diagnose"),

                # "diagnose SPN" - SAE J1939 diagnostic codes
                (r"^diagnose\s+SPN", 0.93, "diagnose"),

                # "diagnose <anything>" - generic catch-all (lower confidence)
                (r"^diagnose\s+\w+", 0.85, "diagnose"),

                # "troubleshoot fault"
                (r"^troubleshoot\s+(the\s+)?fault", 0.93, "troubleshoot"),

                # "investigate fault"
                (r"^investigate\s+(the\s+)?fault", 0.90, "investigate"),
            ],

            "acknowledge_fault": [
                # "acknowledge fault" - mark as seen/reviewed
                (r"^acknowledge\s+(the\s+)?fault", 0.95, "acknowledge"),

                # "ack fault" - shorthand
                (r"^ack\s+(the\s+)?fault", 0.93, "ack"),
            ],

            # =============================================================
            # INVENTORY ACTIONS - Stock Levels, Ordering
            # =============================================================
            # Manage spare parts and consumables inventory.

            "check_stock": [
                # "check stock" - view stock levels
                (r"^check\s+stock", 0.95, "check"),

                # "check inventory"
                (r"^check\s+inventory", 0.93, "check"),

                # "view stock levels"
                (r"^view\s+stock\s+levels", 0.90, "view"),
            ],

            "order_parts": [
                # "order parts" or "order part"
                (r"^order\s+parts?", 0.95, "order"),

                # "request spares" or "request spare"
                (r"^request\s+spares?", 0.93, "request"),

                # "purchase parts"
                (r"^purchase\s+parts?", 0.90, "purchase"),
            ],

            # =============================================================
            # DOCUMENT ACTIONS - Upload, Search
            # =============================================================
            # Manage technical documentation (manuals, procedures, etc.)

            "upload_document": [
                # "upload document/manual/file/pdf"
                # (document|manual|file|pdf) = any of these words
                (r"^upload\s+(a\s+)?(document|manual|file|pdf)", 0.95, "upload"),

                # "add document/manual"
                (r"^add\s+(a\s+)?(document|manual)", 0.90, "add"),

                # "attach document/manual"
                (r"^attach\s+(a\s+)?(document|manual)", 0.88, "attach"),
            ],

            "search_documents": [
                # "search for documents/manuals/procedures"
                # (for\\s+)? = optional "for "
                (r"^search\s+(for\s+)?(documents?|manuals?|procedures?)", 0.93, "search"),

                # "find documents/manuals/procedures"
                (r"^find\s+(documents?|manuals?|procedures?)", 0.90, "find"),
            ],

            # =============================================================
            # PURCHASING ACTIONS - Purchase Requests/Orders
            # =============================================================
            # Manage procurement workflow.

            "create_purchase_request": [
                # "create purchase request"
                (r"^create\s+(a\s+)?purchase\s+request", 0.95, "create"),

                # "raise purchase request"
                (r"^raise\s+(a\s+)?purchase\s+request", 0.90, "raise"),
            ],

            "approve_purchase_order": [
                # "approve purchase order"
                (r"^approve\s+(the\s+)?purchase\s+order", 0.95, "approve"),

                # "authorize purchase"
                (r"^authorize\s+(the\s+)?purchase", 0.90, "authorize"),
            ],

            # =============================================================
            # HOURS OF REST - Crew Work/Rest Compliance
            # =============================================================
            # Maritime Labor Convention (MLC) requires tracking crew hours.
            # Critical for safety and compliance.

            "log_hours_of_rest": [
                # "log my hours of rest"
                (r"^log\s+(my\s+)?hours\s+of\s+rest", 0.95, "log"),

                # "record my hours of rest"
                (r"^record\s+(my\s+)?hours\s+of\s+rest", 0.93, "record"),

                # "enter hours of rest"
                (r"^enter\s+hours\s+of\s+rest", 0.90, "enter"),
            ],

            # =============================================================
            # MANUAL/DOCUMENTATION LOOKUP - View Sections
            # =============================================================
            # Users want to look up specific sections in manuals.

            "show_manual_section": [
                # "show me the manual for X" or "show manual for X"
                (r"^show\s+(me\s+)?(the\s+)?manual\s+(for|on|about)", 0.93, "show"),

                # "open manual for X"
                (r"^open\s+(the\s+)?manual\s+(for|on|about)", 0.92, "open"),

                # "find in manual" or "find manual section"
                (r"^find\s+(in\s+)?(the\s+)?manual", 0.90, "find"),

                # "lookup manual" or "look up manual"
                (r"^look\s*up\s+(the\s+)?manual", 0.90, "lookup"),

                # "what does the manual say about X"
                (r"^what\s+does\s+(the\s+)?manual\s+say", 0.88, "what"),

                # "show service manual" or "show parts manual"
                (r"^show\s+(the\s+)?(service|parts|operator|technical)\s+manual", 0.92, "show"),
            ],

            # =============================================================
            # EQUIPMENT HISTORY - View Equipment-Specific History
            # =============================================================
            # Users want history for a SPECIFIC piece of equipment.

            "show_equipment_history": [
                # "show history for ME1" or "show history for generator"
                (r"^show\s+(the\s+)?history\s+(for|of|on)", 0.93, "show"),

                # "view history for X"
                (r"^view\s+(the\s+)?history\s+(for|of|on)", 0.92, "view"),

                # "get history for X"
                (r"^get\s+(the\s+)?history\s+(for|of|on)", 0.90, "get"),

                # "what is the history for X" or "what's the history of X"
                (r"^what('s|\s+is)\s+the\s+history\s+(for|of|on)", 0.88, "what"),

                # "show maintenance history for X"
                (r"^show\s+(the\s+)?maintenance\s+history\s+(for|of|on)", 0.93, "show"),

                # "show work order history for X"
                (r"^show\s+(the\s+)?work\s*order\s+history\s+(for|of|on)", 0.93, "show"),
            ],

            # =============================================================
            # WORK ORDER NOTES - Add Notes to Existing Work Orders
            # =============================================================
            # Users want to add notes/comments to existing work orders.

            "add_note_to_work_order": [
                # "add note to work order" or "add a note to the work order"
                (r"^add\s+(a\s+)?note\s+to\s+(the\s+)?work\s*order", 0.95, "add"),

                # "add comment to work order"
                (r"^add\s+(a\s+)?comment\s+to\s+(the\s+)?work\s*order", 0.93, "add"),

                # "note on work order" - shorthand
                (r"^note\s+on\s+(the\s+)?work\s*order", 0.90, "note"),

                # "update work order with note"
                (r"^update\s+(the\s+)?work\s*order\s+with\s+(a\s+)?note", 0.90, "update"),

                # "log note on work order"
                (r"^log\s+(a\s+)?note\s+on\s+(the\s+)?work\s*order", 0.92, "log"),
            ],

            # =============================================================
            # CERTIFICATE ACTIONS - Vessel & Crew Certificates
            # =============================================================
            # Manage compliance certificates (Class, ISM, ISPS, STCW, ENG1, etc.)
            # Critical for maritime regulatory compliance.

            "create_vessel_certificate": [
                # "create vessel certificate" or "create a certificate"
                (r"^create\s+(a\s+)?(new\s+)?(vessel\s+)?certificate", 0.95, "create"),

                # "add vessel certificate" or "add certificate"
                (r"^add\s+(a\s+)?(new\s+)?(vessel\s+)?certificate", 0.93, "add"),

                # "register certificate"
                (r"^register\s+(a\s+)?(new\s+)?certificate", 0.90, "register"),

                # "create class certificate" or "create ISM certificate"
                (r"^create\s+(a\s+)?(class|ISM|ISPS|SOLAS|MLC|flag|safety)\s+certificate", 0.95, "create"),

                # "add class certificate"
                (r"^add\s+(a\s+)?(class|ISM|ISPS|SOLAS|MLC|flag|safety)\s+certificate", 0.93, "add"),
            ],

            "create_crew_certificate": [
                # "create crew certificate"
                (r"^create\s+(a\s+)?(new\s+)?crew\s+certificate", 0.95, "create"),

                # "add crew certificate"
                (r"^add\s+(a\s+)?(new\s+)?crew\s+certificate", 0.93, "add"),

                # "create STCW certificate" or "create ENG1"
                (r"^create\s+(a\s+)?(STCW|ENG1|GMDSS|medical|license)\s+(certificate)?", 0.95, "create"),

                # "add STCW" etc.
                (r"^add\s+(a\s+)?(STCW|ENG1|GMDSS|medical|license)\s+(certificate)?", 0.93, "add"),

                # "register crew certificate for [name]"
                (r"^register\s+(a\s+)?crew\s+certificate\s+for", 0.92, "register"),
            ],

            "update_certificate": [
                # "update certificate"
                (r"^update\s+(the\s+)?certificate", 0.93, "update"),

                # "edit certificate"
                (r"^edit\s+(the\s+)?certificate", 0.92, "edit"),

                # "modify certificate"
                (r"^modify\s+(the\s+)?certificate", 0.90, "modify"),

                # "update expiry" for certificate
                (r"^update\s+(the\s+)?certificate\s+expiry", 0.93, "update"),
            ],

            "supersede_certificate": [
                # "supersede certificate" - replace with new version (SIGNED action)
                (r"^supersede\s+(the\s+)?certificate", 0.95, "supersede"),

                # "replace certificate"
                (r"^replace\s+(the\s+)?certificate", 0.93, "replace"),

                # "renew certificate" (implies supersession)
                (r"^renew\s+(the\s+)?certificate", 0.92, "renew"),

                # "supersede ISM certificate" etc.
                (r"^supersede\s+(the\s+)?(class|ISM|ISPS|STCW)\s+certificate", 0.95, "supersede"),
            ],

            "link_document_to_certificate": [
                # "link document to certificate"
                (r"^link\s+(a\s+)?document\s+to\s+(the\s+)?certificate", 0.95, "link"),

                # "attach document to certificate"
                (r"^attach\s+(a\s+)?document\s+to\s+(the\s+)?certificate", 0.93, "attach"),

                # "add document to certificate"
                (r"^add\s+(a\s+)?document\s+to\s+(the\s+)?certificate", 0.92, "add"),

                # "upload certificate document"
                (r"^upload\s+(a\s+)?certificate\s+document", 0.92, "upload"),
            ],

            "list_vessel_certificates": [
                # "show certificates" or "list certificates"
                (r"^show\s+(all\s+)?(vessel\s+)?certificates", 0.93, "show"),
                (r"^list\s+(all\s+)?(vessel\s+)?certificates", 0.93, "list"),

                # "view certificates"
                (r"^view\s+(all\s+)?(vessel\s+)?certificates", 0.92, "view"),

                # "display certificates"
                (r"^display\s+(vessel\s+)?certificates", 0.90, "display"),
            ],

            "list_crew_certificates": [
                # "show crew certificates"
                (r"^show\s+(all\s+)?crew\s+certificates", 0.93, "show"),

                # "list crew certificates"
                (r"^list\s+(all\s+)?crew\s+certificates", 0.93, "list"),

                # "view crew certificates"
                (r"^view\s+(all\s+)?crew\s+certificates", 0.92, "view"),

                # "show certificates for [crew member]"
                (r"^show\s+certificates\s+for\s+", 0.92, "show"),
            ],

            "find_expiring_certificates": [
                # "show expiring certificates"
                (r"^show\s+(all\s+)?expiring\s+certificates", 0.95, "show"),

                # "find expiring certificates"
                (r"^find\s+(all\s+)?expiring\s+certificates", 0.95, "find"),

                # "list certificates expiring"
                (r"^list\s+certificates\s+expiring", 0.93, "list"),

                # "check certificate expiry"
                (r"^check\s+certificate\s+expir(y|ation|ing)", 0.93, "check"),

                # "which certificates expire"
                (r"^which\s+certificates\s+(are\s+)?expir(ing|e)", 0.90, "which"),

                # "certificates due for renewal"
                (r"^(show\s+|list\s+|find\s+)?certificates\s+due\s+(for\s+)?renewal", 0.92, "show"),
            ],

            "view_certificate_history": [
                # "show certificate history"
                (r"^show\s+(the\s+)?certificate\s+history", 0.93, "show"),

                # "view certificate history"
                (r"^view\s+(the\s+)?certificate\s+history", 0.92, "view"),

                # "get certificate audit trail"
                (r"^(show|view|get)\s+(the\s+)?certificate\s+audit\s+trail", 0.93, "show"),
            ],

            "get_certificate_details": [
                # "show certificate" (singular - implies details)
                (r"^show\s+(the\s+)?certificate\s+details", 0.93, "show"),

                # "view certificate"
                (r"^view\s+(the\s+)?certificate$", 0.90, "view"),

                # "get certificate details"
                (r"^get\s+(the\s+)?certificate\s+(details|info)", 0.92, "get"),

                # "open certificate"
                (r"^open\s+(the\s+)?certificate", 0.90, "open"),
            ],
        }

        # =================================================================
        # COMPILE ALL PATTERNS
        # =================================================================
        # Pre-compile regex patterns for performance.
        # Compiled patterns are faster than compiling on each query.

        self.compiled_patterns = {}

        # Loop through each action and its patterns
        for action, patterns in self.action_patterns.items():
            # For each action, create a list of (compiled_regex, confidence, verb)
            self.compiled_patterns[action] = [
                # re.compile() converts string pattern to compiled regex object
                # re.IGNORECASE makes matching case-insensitive
                (re.compile(pattern, re.IGNORECASE), confidence, verb)
                for pattern, confidence, verb in patterns
            ]

    def detect_actions(self, query: str) -> List[ActionDetection]:
        """
        Detect all micro-actions in query using STRICT verb-based patterns.

        === STRICT MATCHING (FIX #1) ===
        Uses .match() instead of .search() to ensure patterns ONLY match
        at the START of the query. This enforces "verb-first" rule.

        Example:
        - "create work order" → MATCHES (starts with verb)
        - "I want to create work order" → DOES NOT MATCH (verb not at start)

        === ORIGINAL CASE PRESERVED (FIX #4) ===
        matched_text uses original query casing for UI/logging.

        === TIE-BREAKING (FIX #5) ===
        When sorting multiple matches, we consider:
        1. Start position (prefer index 0)
        2. Match length (prefer longer/more specific)
        3. Confidence (prefer higher)

        Args:
            query: The user's input text

        Returns:
            List of ActionDetection objects (may be empty), sorted by priority
        """

        # Handle empty/whitespace-only queries
        if not query or not query.strip():
            return []

        # FIX #4: Keep original query for matched_text
        query_original = query.strip()

        # Normalize for matching only (case-insensitive)
        query_norm = query_original.lower()

        # List to store all detected actions
        detections = []

        # Check every action's patterns
        for action_name, patterns in self.compiled_patterns.items():

            # Check each pattern for this action
            for pattern, base_confidence, verb in patterns:

                # FIX #1: Use .match() for STRICT start-of-string matching
                # .match() only matches at position 0
                # .search() would match anywhere (violates strict verb-first)
                match = pattern.match(query_norm)

                # If pattern matched at start
                if match:
                    # Start with the base confidence for this pattern
                    confidence = base_confidence

                    # Get match details
                    start_pos = match.start()  # Always 0 for match()
                    end_pos = match.end()
                    match_length = end_pos - start_pos

                    # === CONFIDENCE BOOST: Longer Match ===
                    # Longer matches are more specific, so more confident
                    if match_length > 20:
                        # Multiply by 1.03 (3% boost)
                        confidence = min(confidence * 1.03, 1.0)

                    # FIX #4: Extract matched text from ORIGINAL query (preserves case)
                    matched_text = query_original[start_pos:end_pos]

                    # Create detection with sort keys for tie-breaking
                    detections.append(ActionDetection(
                        action=action_name,           # e.g., "create_work_order"
                        confidence=confidence,        # e.g., 0.95
                        matched_text=matched_text,    # e.g., "Create Work Order" (original case)
                        verb=verb                     # e.g., "create"
                    ))

        # FIX #5: Sort with proper tie-breaking
        # Priority: (1) higher confidence, (2) longer match, (3) alphabetical action name
        detections.sort(
            key=lambda x: (
                -x.confidence,           # Higher confidence first (negative for descending)
                -len(x.matched_text),    # Longer match first
                x.action                 # Alphabetical as final tiebreaker
            )
        )

        return detections

    def get_best_action(self, query: str, min_confidence: float = 0.4) -> Optional[ActionDetection]:
        """
        Get the single best action detection above confidence threshold.

        === WHEN TO USE THIS ===
        When you only need ONE action (most common case).
        Returns the highest-confidence match, or None if:
        - No matches found
        - Best match is below min_confidence threshold

        Args:
            query: The user's input text
            min_confidence: Minimum confidence to accept (default 0.4 = 40%)

        Returns:
            Best ActionDetection, or None if nothing qualifies
        """

        # Get all detections
        detections = self.detect_actions(query)

        # If nothing detected, return None
        if not detections:
            return None

        # Sort by confidence, highest first
        # key=lambda x: x.confidence means "sort by the confidence attribute"
        # reverse=True means descending order (highest first)
        detections.sort(key=lambda x: x.confidence, reverse=True)

        # Get the best (first after sorting)
        best = detections[0]

        # Check if it meets minimum confidence threshold
        if best.confidence < min_confidence:
            return None  # Too uncertain, don't commit

        return best

    def detect_intent(self, query: str) -> Optional[str]:
        """
        Detect high-level intent from query.

        === INTENT VS ACTION ===
        - Action: Specific micro-action (e.g., "create_work_order")
        - Intent: High-level category of what user wants

        === INTENT CATEGORIES ===
        - create: User wants to CREATE something new
        - update: User wants to MODIFY existing data
        - view: User wants to SEE/READ information
        - action: User wants to PERFORM an operation
        - search: User wants to FIND something

        This is useful for routing at a high level before
        drilling down to specific actions.

        Args:
            query: The user's input text

        Returns:
            Intent string, or None if no action detected
        """

        # First, get the best action
        best_action = self.get_best_action(query)

        # If no action detected, no intent either
        if not best_action:
            return None

        # Map specific actions to high-level intents
        # This groups related actions together
        #
        # FIX #3: Aligned mappings to ACTUAL action names
        # - Removed "edit_work_order" (doesn't exist, action is "update_work_order")
        # - Removed "find_manual" (doesn't exist, action is "search_documents")
        # - Added missing actions to appropriate intents
        intent_map = {
            # "create" intent = making something new
            "create": [
                "create_work_order",
                "create_purchase_request",
                "report_fault",        # Creating a new fault report
                "upload_document",     # Creating/uploading new document
            ],

            # "update" intent = modifying existing data
            "update": [
                "update_work_order",
                "add_to_handover",     # Adding to existing handover
                "log_hours_of_rest",   # Recording/updating hours
                "add_note_to_work_order",  # Adding notes to work orders
            ],

            # "view" intent = reading/displaying information
            "view": [
                "list_work_orders",
                "view_handover",
                "view_history",
                "check_stock",
                "export_handover",     # Viewing/exporting handover
                "show_manual_section", # Looking up manual sections
                "show_equipment_history",  # Viewing equipment history
            ],

            # "action" intent = performing operations (not CRUD)
            "action": [
                "close_work_order",
                "approve_purchase_order",
                "diagnose_fault",
                "acknowledge_fault",
                "order_parts",         # Triggering an order
            ],

            # "search" intent = finding things
            "search": [
                "search_documents",
            ],
        }

        # Find which intent this action belongs to
        for intent, actions in intent_map.items():
            if best_action.action in actions:
                return intent

        # Default intent if not in map
        return "action"


# =============================================================================
# SINGLETON PATTERN
# =============================================================================

# Singleton = Only one instance of StrictMicroActionDetector exists.
# This avoids re-compiling regex patterns multiple times.

# Module-level variable to store the single instance
_detector_instance = None

def get_detector() -> StrictMicroActionDetector:
    """
    Get or create the singleton detector instance.

    === WHY SINGLETON? ===
    1. Regex compilation is expensive
    2. We only need one instance of these patterns
    3. Consistent behavior across all uses

    Returns:
        The singleton StrictMicroActionDetector instance
    """
    global _detector_instance

    # Create instance if it doesn't exist
    if _detector_instance is None:
        _detector_instance = StrictMicroActionDetector()

    return _detector_instance


# =============================================================================
# TEST / MAIN
# =============================================================================

# This block runs when you execute the file directly:
# python module_a_action_detector.py
#
# It runs some quick tests to verify the detector works correctly.

if __name__ == "__main__":
    # Create a detector instance
    detector = StrictMicroActionDetector()

    # Test cases: (query, should_detect)
    # True = we SHOULD detect an action
    # False = we should NOT detect an action (would be a false positive)
    test_cases = [
        # === SHOULD DETECT ===
        ("create work order for bilge pump", True),
        # Starts with "create work order" - clear action

        ("diagnose E047 on ME1", True),
        # Starts with "diagnose" + fault code - clear action

        ("open work order", True),
        # Starts with "open work order" - clear action

        # === SHOULD NOT DETECT ===
        ("bilge manifold", False),
        # Just equipment name - no action verb

        ("sea water pump", False),
        # Just equipment name - no action verb

        ("tell me bilge pump", False),
        # "tell me" is NOT a recognized action verb

        ("find coolant temp", False),
        # "find" alone is ambiguous (not "find documents")
    ]

    print("Module A: Strict Micro-Action Detector - Quick Tests")
    print("=" * 60)

    # Run each test case
    for query, should_detect in test_cases:
        # Try to detect an action
        detection = detector.get_best_action(query)

        # Check if we detected something
        detected = detection is not None

        # Check if result matches expectation
        status = "✅" if detected == should_detect else "❌"

        # Print result
        if detection:
            print(f"{status} '{query}'")
            print(f"   → Action: {detection.action}, Confidence: {detection.confidence:.2f}, Verb: {detection.verb}")
        else:
            print(f"{status} '{query}'")
            print(f"   → No action detected")
        print()

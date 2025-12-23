#!/usr/bin/env python3
"""
Pattern Library V1
==================
Structured patterns extracted from V3 audit failures.
Each pattern includes trigger rules, disambiguation cues, and test case templates.

Based on analysis:
- 130 action collisions
- 59 false negatives
- Key issues: verb ambiguity, noise prefixes, context resolution
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class RiskClass(Enum):
    HARD_FP = "hard_fp"           # State-changing action triggered incorrectly
    SOFT_MISROUTE = "soft_misroute"  # Read-only wrong action
    FN_RISK = "fn_risk"           # Might fail to trigger when should
    SAFE = "safe"                 # Low risk of any error


@dataclass
class Pattern:
    """A failure pattern with rules for testing."""
    pattern_id: str
    name: str
    category: str  # collision, noise_prefix, unrecognized_verb, entity_miss
    description: str

    # Why this pattern causes failures
    trigger_rule: str

    # Words/phrases that should disambiguate
    disambiguation_cues: List[str]

    # Actions involved in this pattern
    primary_actions: List[str]
    collision_actions: List[str] = field(default_factory=list)

    # Negative control signals (should NOT trigger)
    negative_signals: List[str] = field(default_factory=list)

    # Risk classification
    default_risk: RiskClass = RiskClass.SOFT_MISROUTE

    # How many cases in V3 audit
    v3_failure_count: int = 0

    # Priority for testing (higher = more important)
    priority: int = 5


# =============================================================================
# COLLISION PATTERNS (verb ambiguity)
# =============================================================================

COLLISION_PATTERNS = [
    Pattern(
        pattern_id="COL_ADD",
        name="Add Verb Collision",
        category="collision",
        description="'add' routes to add_to_handover by default, but context may need add_note_to_work_order, add_note, or add_part_to_work_order",
        trigger_rule="First token 'add' without clear target context",
        disambiguation_cues=[
            "handover", "note to work order", "note to WO", "part to work order",
            "part to WO", "checklist item", "note about", "comment"
        ],
        primary_actions=["add_to_handover", "add_note_to_work_order", "add_note", "add_part_to_work_order", "add_checklist_item"],
        collision_actions=["add_to_handover"],
        negative_signals=["can you add", "please add", "i need to add"],
        default_risk=RiskClass.HARD_FP,  # add_to_handover is state-changing
        v3_failure_count=32,
        priority=10,
    ),

    Pattern(
        pattern_id="COL_SHOW",
        name="Show Verb Collision",
        category="collision",
        description="'show' routes based on object context but often misses specific action types",
        trigger_rule="First token 'show' with ambiguous object",
        disambiguation_cues=[
            "linked", "entities", "tasks", "due", "overdue", "certificates",
            "expiring", "manual", "history", "status", "handover", "hours of rest"
        ],
        primary_actions=["view_linked_entities", "show_tasks_due", "show_certificates", "show_equipment_overview", "show_manual_section", "show_equipment_history"],
        collision_actions=["show_equipment_overview"],
        negative_signals=["can you show", "please show"],
        default_risk=RiskClass.SOFT_MISROUTE,  # show actions are read-only
        v3_failure_count=33,
        priority=8,
    ),

    Pattern(
        pattern_id="COL_EXPORT",
        name="Export Verb Collision",
        category="collision",
        description="'export' defaults to export_summary but may need export_handover or export_compliance_logs",
        trigger_rule="First token 'export' without explicit target",
        disambiguation_cues=[
            "handover", "compliance", "logs", "hours of rest", "HOR",
            "work order history", "summary", "report"
        ],
        primary_actions=["export_handover", "export_summary", "export_compliance_logs", "export_work_order_history"],
        collision_actions=["export_summary"],
        negative_signals=["can you export", "please export"],
        default_risk=RiskClass.SOFT_MISROUTE,  # exports are read-only
        v3_failure_count=12,
        priority=7,
    ),

    Pattern(
        pattern_id="COL_OPEN",
        name="Open Verb Collision",
        category="collision",
        description="'open' routes to open_equipment_card but may need open_document",
        trigger_rule="First token 'open' without clear doc/equipment distinction",
        disambiguation_cues=[
            "document", "manual", "PDF", "file", "equipment card", "card for"
        ],
        primary_actions=["open_document", "open_equipment_card"],
        collision_actions=["open_equipment_card"],
        negative_signals=["can you open", "please open"],
        default_risk=RiskClass.SOFT_MISROUTE,
        v3_failure_count=9,
        priority=6,
    ),

    Pattern(
        pattern_id="COL_GENERATE",
        name="Generate/Summarise Collision",
        category="collision",
        description="'generate'/'summarise' defaults to generate_summary but may need generate_audit_pack",
        trigger_rule="First token 'generate' or 'summarise' without audit context",
        disambiguation_cues=[
            "audit", "audit pack", "compliance pack", "summary", "report"
        ],
        primary_actions=["generate_summary", "generate_audit_pack"],
        collision_actions=["generate_summary"],
        negative_signals=["can you generate", "please summarise"],
        default_risk=RiskClass.SOFT_MISROUTE,
        v3_failure_count=12,
        priority=5,
    ),

    Pattern(
        pattern_id="COL_UPDATE",
        name="Update Verb Collision",
        category="collision",
        description="'update' defaults to update_work_order but may need update_stock_level or update_certificate_metadata",
        trigger_rule="First token 'update' without target type",
        disambiguation_cues=[
            "work order", "WO", "stock", "inventory", "certificate", "metadata"
        ],
        primary_actions=["update_work_order", "update_stock_level", "update_certificate_metadata"],
        collision_actions=["update_work_order"],
        negative_signals=["can you update", "please update"],
        default_risk=RiskClass.HARD_FP,  # update actions are state-changing
        v3_failure_count=6,
        priority=8,
    ),

    Pattern(
        pattern_id="COL_UPLOAD",
        name="Upload Verb Collision",
        category="collision",
        description="'upload' defaults to upload_document but may need upload_certificate_document or upload_invoice",
        trigger_rule="First token 'upload' without document type",
        disambiguation_cues=[
            "certificate", "invoice", "document", "PDF", "manual"
        ],
        primary_actions=["upload_document", "upload_certificate_document", "upload_invoice"],
        collision_actions=["upload_document"],
        negative_signals=["can you upload", "please upload"],
        default_risk=RiskClass.HARD_FP,  # upload is state-changing
        v3_failure_count=5,
        priority=7,
    ),

    Pattern(
        pattern_id="COL_ATTACH",
        name="Attach Verb Collision",
        category="collision",
        description="'attach' defaults to attach_document_to_work_order but may need attach_photo_to_work_order or attach_document_to_handover",
        trigger_rule="First token 'attach' without attachment type",
        disambiguation_cues=[
            "photo", "image", "picture", "document", "PDF", "handover"
        ],
        primary_actions=["attach_document_to_work_order", "attach_photo_to_work_order", "attach_document_to_handover"],
        collision_actions=["attach_document_to_work_order"],
        negative_signals=["can you attach", "please attach"],
        default_risk=RiskClass.HARD_FP,
        v3_failure_count=3,
        priority=6,
    ),
]

# =============================================================================
# NOISE PREFIX PATTERNS (cause FN)
# =============================================================================

NOISE_PREFIX_PATTERNS = [
    Pattern(
        pattern_id="NOISE_SO",
        name="'So/Like' Prefix",
        category="noise_prefix",
        description="Casual speech prefixes 'so', 'so like' cause verb to be missed",
        trigger_rule="First token 'so' or 'so like' hides actual verb",
        disambiguation_cues=["so", "like", "so like"],
        primary_actions=["create_work_order", "diagnose_fault", "check_stock_level"],
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=15,
        priority=9,
    ),

    Pattern(
        pattern_id="NOISE_EMAIL_FW",
        name="Email Forward Prefix",
        category="noise_prefix",
        description="Email prefix 'FW:' or 'Fw:' causes verb to be missed",
        trigger_rule="First token matches email forward pattern",
        disambiguation_cues=["FW:", "Fw:", "fw:", "Fwd:", "fwd:"],
        primary_actions=["check_stock_level", "diagnose_fault"],
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=7,
        priority=8,
    ),

    Pattern(
        pattern_id="NOISE_EMAIL_RE",
        name="Email Reply Prefix",
        category="noise_prefix",
        description="Email prefix 'RE:' or 'Re:' causes verb to be missed",
        trigger_rule="First token matches email reply pattern",
        disambiguation_cues=["RE:", "Re:", "re:"],
        primary_actions=["show_manual_section", "diagnose_fault"],
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=3,
        priority=7,
    ),

    Pattern(
        pattern_id="NOISE_OK",
        name="'OK/Right' Prefix",
        category="noise_prefix",
        description="Confirmation words 'ok', 'right' as prefixes",
        trigger_rule="First token is filler confirmation",
        disambiguation_cues=["ok", "okay", "right"],
        primary_actions=["check_stock_level", "diagnose_fault"],
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=7,
        priority=7,
    ),

    Pattern(
        pattern_id="NOISE_QUOTE",
        name="Quote Marker Prefix",
        category="noise_prefix",
        description="Quote markers '>>>' or '>' from email/forum copy-paste",
        trigger_rule="First chars are quote markers",
        disambiguation_cues=[">>>", ">>", ">"],
        primary_actions=["diagnose_fault"],
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=4,
        priority=6,
    ),

    Pattern(
        pattern_id="NOISE_BULLET",
        name="Bullet Point Prefix",
        category="noise_prefix",
        description="Bullet points or dashes from list copy-paste",
        trigger_rule="First char is bullet or dash",
        disambiguation_cues=["-", "•", "–", "—", "*"],
        primary_actions=["create_work_order"],
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=3,
        priority=5,
    ),
]

# =============================================================================
# UNRECOGNIZED VERB PATTERNS
# =============================================================================

UNRECOGNIZED_VERB_PATTERNS = [
    Pattern(
        pattern_id="VERB_TAG",
        name="'Tag' Verb Unrecognized",
        category="unrecognized_verb",
        description="'tag' not in trigger verb list",
        trigger_rule="Verb 'tag' not recognized as trigger",
        disambiguation_cues=["tag"],
        primary_actions=["none_search_only"],  # Currently falls through
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=2,
        priority=4,
    ),

    Pattern(
        pattern_id="VERB_EXTRACT",
        name="'Extract' Verb Unrecognized",
        category="unrecognized_verb",
        description="'extract' not in trigger verb list",
        trigger_rule="Verb 'extract' not recognized as trigger",
        disambiguation_cues=["extract"],
        primary_actions=["none_search_only"],
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=2,
        priority=4,
    ),
]

# =============================================================================
# SAFETY RAIL PATTERNS (should NEVER trigger state-changing)
# =============================================================================

SAFETY_RAIL_PATTERNS = [
    Pattern(
        pattern_id="SAFETY_POLITE",
        name="Polite Prefix Safety",
        category="safety_rail",
        description="Polite prefixes should NEVER trigger any action",
        trigger_rule="Query starts with 'can you', 'could you', 'please', 'I need to'",
        disambiguation_cues=[
            "can you", "could you", "would you", "please",
            "i need to", "i want to", "help me"
        ],
        primary_actions=["none_search_only"],
        negative_signals=[],
        default_risk=RiskClass.HARD_FP,  # Critical if triggered
        v3_failure_count=0,  # Already handled
        priority=10,
    ),

    Pattern(
        pattern_id="SAFETY_APPROVE",
        name="Approval Action Safety",
        category="safety_rail",
        description="'approve' actions should require explicit confirmation context",
        trigger_rule="Verb 'approve' should not trigger on ambiguous queries",
        disambiguation_cues=["approve", "authorize", "sign off"],
        primary_actions=["approve_purchase_order"],
        negative_signals=["looking at", "reviewing", "checking"],
        default_risk=RiskClass.HARD_FP,
        v3_failure_count=0,
        priority=10,
    ),

    Pattern(
        pattern_id="SAFETY_DELETE",
        name="Delete Action Safety",
        category="safety_rail",
        description="Delete/archive actions require explicit intent",
        trigger_rule="Destructive verbs should have high threshold",
        disambiguation_cues=["delete", "remove", "archive", "close"],
        primary_actions=["archive_document", "close_work_order"],
        negative_signals=["show", "view", "find"],
        default_risk=RiskClass.HARD_FP,
        v3_failure_count=0,
        priority=10,
    ),
]

# =============================================================================
# INTERNATIONAL CREW PATTERNS (non-native English)
# =============================================================================

INTERNATIONAL_PATTERNS = [
    Pattern(
        pattern_id="INTL_MAKE",
        name="'Make' Instead of 'Create'",
        category="international",
        description="Non-native speakers often use 'make' instead of 'create'",
        trigger_rule="Verb 'make' not recognized for work order creation",
        disambiguation_cues=["make", "make work order", "make WO", "make task"],
        primary_actions=["create_work_order", "create_task"],
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=0,  # Not yet tested
        priority=6,
    ),

    Pattern(
        pattern_id="INTL_DO",
        name="'Do' Instead of 'Create/Add'",
        category="international",
        description="Non-native speakers use 'do' for various actions",
        trigger_rule="Verb 'do' not recognized",
        disambiguation_cues=["do", "do handover", "do note"],
        primary_actions=["add_to_handover", "add_note"],
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=0,
        priority=5,
    ),

    Pattern(
        pattern_id="INTL_PUT",
        name="'Put' Instead of 'Add'",
        category="international",
        description="Non-native speakers use 'put' for adding items",
        trigger_rule="Verb 'put' not recognized",
        disambiguation_cues=["put", "put in handover", "put note"],
        primary_actions=["add_to_handover", "add_note_to_work_order"],
        negative_signals=[],
        default_risk=RiskClass.FN_RISK,
        v3_failure_count=0,
        priority=5,
    ),
]

# =============================================================================
# TWO-STEP INTENT PATTERNS
# =============================================================================

TWO_STEP_PATTERNS = [
    Pattern(
        pattern_id="TWO_STEP_OPEN_ADD",
        name="Open Then Add",
        category="two_step",
        description="Combined intent: open X then add to handover",
        trigger_rule="Query contains both 'open' and 'add' intents",
        disambiguation_cues=[
            "open and add", "open then add", "view and include",
            "show and add to handover"
        ],
        primary_actions=["open_equipment_card", "add_to_handover"],
        collision_actions=[],
        negative_signals=[],
        default_risk=RiskClass.SOFT_MISROUTE,  # Should pick safe primary
        v3_failure_count=0,
        priority=4,
    ),

    Pattern(
        pattern_id="TWO_STEP_DIAGNOSE_CREATE",
        name="Diagnose Then Create WO",
        category="two_step",
        description="Combined intent: diagnose fault then create work order",
        trigger_rule="Query contains both diagnostic and WO creation intent",
        disambiguation_cues=[
            "diagnose and create", "investigate and raise WO",
            "troubleshoot then create work order"
        ],
        primary_actions=["diagnose_fault", "create_work_order"],
        collision_actions=[],
        negative_signals=[],
        default_risk=RiskClass.SOFT_MISROUTE,
        v3_failure_count=0,
        priority=4,
    ),
]

# =============================================================================
# COMBINED PATTERN LIBRARY
# =============================================================================

ALL_PATTERNS = (
    COLLISION_PATTERNS +
    NOISE_PREFIX_PATTERNS +
    UNRECOGNIZED_VERB_PATTERNS +
    SAFETY_RAIL_PATTERNS +
    INTERNATIONAL_PATTERNS +
    TWO_STEP_PATTERNS
)

PATTERN_BY_ID = {p.pattern_id: p for p in ALL_PATTERNS}


def get_patterns_by_category(category: str) -> List[Pattern]:
    """Get all patterns in a category."""
    return [p for p in ALL_PATTERNS if p.category == category]


def get_patterns_by_priority(min_priority: int = 5) -> List[Pattern]:
    """Get patterns at or above priority threshold."""
    return sorted(
        [p for p in ALL_PATTERNS if p.priority >= min_priority],
        key=lambda p: -p.priority
    )


def get_high_risk_patterns() -> List[Pattern]:
    """Get patterns that risk hard FPs."""
    return [p for p in ALL_PATTERNS if p.default_risk == RiskClass.HARD_FP]


if __name__ == "__main__":
    print("=" * 70)
    print("PATTERN LIBRARY V1")
    print("=" * 70)

    print(f"\nTotal patterns: {len(ALL_PATTERNS)}")
    print(f"\nBy category:")
    for cat in ["collision", "noise_prefix", "unrecognized_verb", "safety_rail", "international", "two_step"]:
        patterns = get_patterns_by_category(cat)
        total_failures = sum(p.v3_failure_count for p in patterns)
        print(f"  {cat}: {len(patterns)} patterns, {total_failures} V3 failures")

    print(f"\nHigh risk (hard FP) patterns:")
    for p in get_high_risk_patterns():
        print(f"  {p.pattern_id}: {p.name} (priority {p.priority})")

    print(f"\nTop priority patterns (>= 7):")
    for p in get_patterns_by_priority(7):
        print(f"  {p.pattern_id}: {p.name} (priority {p.priority}, {p.v3_failure_count} failures)")

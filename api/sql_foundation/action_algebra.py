"""
Action Algebra
==============

First-class typed actions for the constraint compiler.

THEORY:
    An Action is a typed operation over objects with constraints:

        Action = (verb, object, filters, scope, constraints, execution_class)

    Actions are NOT "intents" - they're LITERAL operations that can be:
    - Planned (compile to execution plan)
    - Validated (check schema compatibility)
    - Composed (chain multiple actions)
    - Gated (require confirmation for writes)

VERBS (closed set):
    READ verbs:   SHOW, LIST, FIND, GET, LOOKUP
    WRITE verbs:  CREATE, UPDATE, DELETE, LOG, SCHEDULE
    META verbs:   EXPLAIN, COMPARE, EXPORT

OBJECTS (from capability registry):
    inventory, work_orders, equipment, parts, faults, documents, purchase_orders

EXECUTION CLASSES:
    AUTO:     Execute immediately, no confirmation
    SUGGEST:  Show what would happen, require confirmation
    CONFIRM:  Require explicit user confirmation before execution
    BLOCKED:  Cannot execute (security, schema mismatch)

COMPOSITION:
    Actions can be chained via clause splitting:
    "show inventory box 2d and create work order"
    → [SHOW(inventory, location=2d), CREATE(work_order)] with gate on CREATE

ALGEBRAIC PROPERTIES:
    - Actions are idempotent for READ verbs
    - Actions are NOT idempotent for WRITE verbs
    - Actions compose sequentially (not parallel for writes)
    - Action validation is deterministic
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any, Union
from enum import Enum

from .constraint_algebra import (
    Constraint, ConstraintSet, ConstraintOp, Hardness,
    SemanticPredicate, analyze_constraints, ConstraintAnalysisResult
)


# =============================================================================
# ACTION VERBS
# =============================================================================

class ActionVerb(str, Enum):
    """
    Closed set of action verbs.

    READ verbs return data without modification.
    WRITE verbs modify data (require confirmation gate).
    META verbs provide analysis or export.
    """
    # READ verbs
    SHOW = "show"       # Display specific item(s)
    LIST = "list"       # Enumerate items matching filters
    FIND = "find"       # Search with fuzzy matching
    GET = "get"         # Fetch by exact ID
    LOOKUP = "lookup"   # Exact code/reference lookup

    # WRITE verbs
    CREATE = "create"   # Create new record
    UPDATE = "update"   # Modify existing record
    DELETE = "delete"   # Remove record
    LOG = "log"         # Add log entry
    SCHEDULE = "schedule"  # Schedule maintenance/task

    # META verbs
    EXPLAIN = "explain"   # Explain a code/fault/procedure
    COMPARE = "compare"   # Compare multiple items
    EXPORT = "export"     # Export data to file


# Verb classifications
READ_VERBS: Set[ActionVerb] = {
    ActionVerb.SHOW, ActionVerb.LIST, ActionVerb.FIND,
    ActionVerb.GET, ActionVerb.LOOKUP
}

WRITE_VERBS: Set[ActionVerb] = {
    ActionVerb.CREATE, ActionVerb.UPDATE, ActionVerb.DELETE,
    ActionVerb.LOG, ActionVerb.SCHEDULE
}

META_VERBS: Set[ActionVerb] = {
    ActionVerb.EXPLAIN, ActionVerb.COMPARE, ActionVerb.EXPORT
}


# =============================================================================
# ACTION OBJECTS (from capability registry)
# =============================================================================

class ActionObject(str, Enum):
    """
    Objects that actions can operate on.

    Each maps to one or more database tables.
    """
    INVENTORY = "inventory"
    WORK_ORDERS = "work_orders"
    EQUIPMENT = "equipment"
    PARTS = "parts"
    FAULTS = "faults"
    DOCUMENTS = "documents"
    PURCHASE_ORDERS = "purchase_orders"
    SUPPLIERS = "suppliers"
    LOGS = "logs"


# Object → Table mapping
OBJECT_TABLES: Dict[ActionObject, List[str]] = {
    ActionObject.INVENTORY: ["v_inventory", "pms_parts"],
    ActionObject.WORK_ORDERS: ["pms_work_orders"],
    ActionObject.EQUIPMENT: ["pms_equipment", "graph_nodes"],
    ActionObject.PARTS: ["pms_parts"],
    ActionObject.FAULTS: ["pms_faults", "search_fault_code_catalog", "symptom_aliases"],
    ActionObject.DOCUMENTS: ["search_document_chunks", "doc_metadata"],
    ActionObject.PURCHASE_ORDERS: ["pms_purchase_orders"],
    ActionObject.SUPPLIERS: ["pms_suppliers"],
    ActionObject.LOGS: ["pms_logs"],
}


# =============================================================================
# EXECUTION CLASS
# =============================================================================

class ExecutionClass(str, Enum):
    """
    Execution gating for actions.

    Determines whether action executes immediately or requires confirmation.
    """
    AUTO = "auto"         # Execute immediately
    SUGGEST = "suggest"   # Show preview, suggest confirmation
    CONFIRM = "confirm"   # Require explicit confirmation
    BLOCKED = "blocked"   # Cannot execute


# Default execution class by verb
VERB_EXECUTION_CLASS: Dict[ActionVerb, ExecutionClass] = {
    # READ verbs - auto execute
    ActionVerb.SHOW: ExecutionClass.AUTO,
    ActionVerb.LIST: ExecutionClass.AUTO,
    ActionVerb.FIND: ExecutionClass.AUTO,
    ActionVerb.GET: ExecutionClass.AUTO,
    ActionVerb.LOOKUP: ExecutionClass.AUTO,

    # WRITE verbs - require confirmation
    ActionVerb.CREATE: ExecutionClass.CONFIRM,
    ActionVerb.UPDATE: ExecutionClass.CONFIRM,
    ActionVerb.DELETE: ExecutionClass.CONFIRM,
    ActionVerb.LOG: ExecutionClass.SUGGEST,      # Logging is lower risk
    ActionVerb.SCHEDULE: ExecutionClass.CONFIRM,

    # META verbs - auto for read-like, suggest for export
    ActionVerb.EXPLAIN: ExecutionClass.AUTO,
    ActionVerb.COMPARE: ExecutionClass.AUTO,
    ActionVerb.EXPORT: ExecutionClass.SUGGEST,
}


# =============================================================================
# VERB RECOGNITION PATTERNS
# =============================================================================

# Surface forms → canonical verbs
VERB_PATTERNS: Dict[str, ActionVerb] = {
    # SHOW variants
    "show": ActionVerb.SHOW,
    "display": ActionVerb.SHOW,
    "view": ActionVerb.SHOW,
    "see": ActionVerb.SHOW,
    "pull up": ActionVerb.SHOW,

    # LIST variants
    "list": ActionVerb.LIST,
    "all": ActionVerb.LIST,
    "enumerate": ActionVerb.LIST,
    "show all": ActionVerb.LIST,
    "show me all": ActionVerb.LIST,

    # FIND variants
    "find": ActionVerb.FIND,
    "search": ActionVerb.FIND,
    "search for": ActionVerb.FIND,
    "look for": ActionVerb.FIND,
    "locate": ActionVerb.FIND,
    "where is": ActionVerb.FIND,
    "where are": ActionVerb.FIND,

    # GET variants
    "get": ActionVerb.GET,
    "fetch": ActionVerb.GET,
    "retrieve": ActionVerb.GET,

    # LOOKUP variants
    "lookup": ActionVerb.LOOKUP,
    "look up": ActionVerb.LOOKUP,
    "check": ActionVerb.LOOKUP,

    # CREATE variants
    "create": ActionVerb.CREATE,
    "add": ActionVerb.CREATE,
    "new": ActionVerb.CREATE,
    "make": ActionVerb.CREATE,
    "open": ActionVerb.CREATE,  # "open a work order"

    # UPDATE variants
    "update": ActionVerb.UPDATE,
    "change": ActionVerb.UPDATE,
    "modify": ActionVerb.UPDATE,
    "edit": ActionVerb.UPDATE,
    "set": ActionVerb.UPDATE,
    "adjust": ActionVerb.UPDATE,

    # DELETE variants
    "delete": ActionVerb.DELETE,
    "remove": ActionVerb.DELETE,
    "cancel": ActionVerb.DELETE,
    "close": ActionVerb.DELETE,  # "close work order" = mark completed

    # LOG variants
    "log": ActionVerb.LOG,
    "record": ActionVerb.LOG,
    "note": ActionVerb.LOG,
    "add note": ActionVerb.LOG,

    # SCHEDULE variants
    "schedule": ActionVerb.SCHEDULE,
    "plan": ActionVerb.SCHEDULE,
    "book": ActionVerb.SCHEDULE,

    # EXPLAIN variants
    "explain": ActionVerb.EXPLAIN,
    "what is": ActionVerb.EXPLAIN,
    "what does": ActionVerb.EXPLAIN,
    "how to": ActionVerb.EXPLAIN,
    "describe": ActionVerb.EXPLAIN,

    # COMPARE variants
    "compare": ActionVerb.COMPARE,
    "vs": ActionVerb.COMPARE,
    "versus": ActionVerb.COMPARE,
    "difference": ActionVerb.COMPARE,

    # EXPORT variants
    "export": ActionVerb.EXPORT,
    "download": ActionVerb.EXPORT,
    "extract": ActionVerb.EXPORT,
}


# Object recognition patterns
OBJECT_PATTERNS: Dict[str, ActionObject] = {
    # INVENTORY
    "inventory": ActionObject.INVENTORY,
    "inv": ActionObject.INVENTORY,
    "stock": ActionObject.INVENTORY,
    "spare": ActionObject.INVENTORY,
    "spares": ActionObject.INVENTORY,

    # WORK_ORDERS
    "work order": ActionObject.WORK_ORDERS,
    "work orders": ActionObject.WORK_ORDERS,
    "wo": ActionObject.WORK_ORDERS,
    "task": ActionObject.WORK_ORDERS,
    "tasks": ActionObject.WORK_ORDERS,
    "job": ActionObject.WORK_ORDERS,
    "jobs": ActionObject.WORK_ORDERS,
    "maintenance": ActionObject.WORK_ORDERS,

    # EQUIPMENT
    "equipment": ActionObject.EQUIPMENT,
    "equip": ActionObject.EQUIPMENT,
    "machine": ActionObject.EQUIPMENT,
    "system": ActionObject.EQUIPMENT,
    "engine": ActionObject.EQUIPMENT,
    "generator": ActionObject.EQUIPMENT,

    # PARTS
    "part": ActionObject.PARTS,
    "parts": ActionObject.PARTS,
    "component": ActionObject.PARTS,
    "components": ActionObject.PARTS,
    "filter": ActionObject.PARTS,
    "filters": ActionObject.PARTS,

    # FAULTS
    "fault": ActionObject.FAULTS,
    "faults": ActionObject.FAULTS,
    "error": ActionObject.FAULTS,
    "alarm": ActionObject.FAULTS,
    "warning": ActionObject.FAULTS,

    # DOCUMENTS
    "document": ActionObject.DOCUMENTS,
    "documents": ActionObject.DOCUMENTS,
    "doc": ActionObject.DOCUMENTS,
    "docs": ActionObject.DOCUMENTS,
    "manual": ActionObject.DOCUMENTS,
    "manuals": ActionObject.DOCUMENTS,
    "procedure": ActionObject.DOCUMENTS,

    # PURCHASE_ORDERS
    "purchase order": ActionObject.PURCHASE_ORDERS,
    "purchase orders": ActionObject.PURCHASE_ORDERS,
    "po": ActionObject.PURCHASE_ORDERS,
    "order": ActionObject.PURCHASE_ORDERS,
    "orders": ActionObject.PURCHASE_ORDERS,

    # SUPPLIERS
    "supplier": ActionObject.SUPPLIERS,
    "suppliers": ActionObject.SUPPLIERS,
    "vendor": ActionObject.SUPPLIERS,
    "vendors": ActionObject.SUPPLIERS,
}


# =============================================================================
# ACTION DATA STRUCTURE
# =============================================================================

@dataclass
class Action:
    """
    A typed action over an object with constraints.

    Actions are NOT "intents" - they're literal operations.
    """
    verb: ActionVerb
    object: ActionObject
    constraints: ConstraintSet
    scope: Optional[str] = None  # e.g., "main engine", "deck 2"
    execution_class: Optional[ExecutionClass] = None
    source_text: str = ""  # Original query fragment

    # Computed
    target_tables: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Set default execution class from verb
        if self.execution_class is None:
            self.execution_class = VERB_EXECUTION_CLASS.get(
                self.verb, ExecutionClass.AUTO
            )

        # Set target tables from object
        if not self.target_tables:
            self.target_tables = OBJECT_TABLES.get(self.object, [])

    @property
    def is_read(self) -> bool:
        return self.verb in READ_VERBS

    @property
    def is_write(self) -> bool:
        return self.verb in WRITE_VERBS

    @property
    def is_meta(self) -> bool:
        return self.verb in META_VERBS

    @property
    def requires_confirmation(self) -> bool:
        return self.execution_class in (ExecutionClass.CONFIRM, ExecutionClass.SUGGEST)

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate action against schema and constraints.

        Returns: (is_valid, list of validation errors)
        """
        errors = []

        # Check constraints
        analysis = analyze_constraints(self.constraints)
        if analysis.status == ConstraintAnalysisResult.CONTRADICTORY:
            errors.append(f"Contradictory constraints: {analysis.reason}")
        elif analysis.status == ConstraintAnalysisResult.UNDERCONSTRAINED:
            # Underconstrained is warning for LIST, error for WRITE
            if self.is_write:
                errors.append(f"Write action requires constraints: {analysis.reason}")

        # Check object has tables
        if not self.target_tables:
            errors.append(f"Unknown object: {self.object}")

        # Check write actions have target identification
        if self.is_write and self.verb != ActionVerb.CREATE:
            # UPDATE/DELETE need to identify target rows
            has_id = any(
                c.variable in ("id", "wo_id", "po_number", "part_number")
                for c in self.constraints.constraints
            )
            if not has_id:
                errors.append("Write action requires target identification (id or code)")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict:
        return {
            "verb": self.verb.value,
            "object": self.object.value,
            "execution_class": self.execution_class.value,
            "is_read": self.is_read,
            "is_write": self.is_write,
            "requires_confirmation": self.requires_confirmation,
            "target_tables": self.target_tables,
            "constraints": self.constraints.to_dict(),
            "source_text": self.source_text,
        }


# =============================================================================
# ACTION PLAN (multiple actions)
# =============================================================================

@dataclass
class ActionPlan:
    """
    A plan consisting of one or more actions.

    Multi-action queries are decomposed into sequential actions
    with appropriate gating.
    """
    actions: List[Action]
    yacht_id: str
    source_query: str
    decomposition_reason: Optional[str] = None

    @property
    def has_writes(self) -> bool:
        return any(a.is_write for a in self.actions)

    @property
    def requires_confirmation(self) -> bool:
        return any(a.requires_confirmation for a in self.actions)

    @property
    def is_single_action(self) -> bool:
        return len(self.actions) == 1

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate all actions in plan."""
        errors = []
        for i, action in enumerate(self.actions):
            valid, action_errors = action.validate()
            if not valid:
                errors.extend([f"Action {i+1}: {e}" for e in action_errors])
        return len(errors) == 0, errors

    def to_dict(self) -> Dict:
        return {
            "action_count": len(self.actions),
            "has_writes": self.has_writes,
            "requires_confirmation": self.requires_confirmation,
            "actions": [a.to_dict() for a in self.actions],
            "decomposition_reason": self.decomposition_reason,
        }


# =============================================================================
# ACTION PARSER
# =============================================================================

import re


class ActionParser:
    """
    Parse natural language into typed Actions.

    NOT intent guessing - literal extraction of verbs and objects.
    """

    # Clause splitting patterns (literal, not semantic)
    CLAUSE_SPLITTERS = [
        r'\s+and\s+(?=(?:create|update|delete|log|schedule|add|make|open))',
        r'\s+then\s+',
        r'\s+also\s+',
        r';\s*',
    ]

    def __init__(self):
        self._clause_pattern = re.compile(
            '|'.join(self.CLAUSE_SPLITTERS),
            re.IGNORECASE
        )

    def parse(self, query: str, yacht_id: str, constraints: ConstraintSet) -> ActionPlan:
        """
        Parse query into ActionPlan.

        Args:
            query: Natural language query
            yacht_id: Required yacht scope
            constraints: Pre-extracted constraints from constraint parser

        Returns:
            ActionPlan with one or more actions
        """
        # Split into clauses
        clauses = self._split_clauses(query)

        # Parse each clause
        actions = []
        for clause in clauses:
            action = self._parse_single_clause(clause, yacht_id, constraints)
            if action:
                actions.append(action)

        # If no actions found, create default FIND action
        if not actions:
            actions.append(Action(
                verb=ActionVerb.FIND,
                object=self._infer_object(query),
                constraints=constraints,
                source_text=query,
            ))

        decomposition_reason = None
        if len(clauses) > 1:
            decomposition_reason = f"Split on clause boundary ({len(clauses)} clauses)"

        return ActionPlan(
            actions=actions,
            yacht_id=yacht_id,
            source_query=query,
            decomposition_reason=decomposition_reason,
        )

    def _split_clauses(self, query: str) -> List[str]:
        """
        Split query into clauses.

        Only split when each clause has at least one verb/object.
        """
        # Find split points
        parts = self._clause_pattern.split(query)

        # Validate each part has content
        valid_clauses = []
        for part in parts:
            part = part.strip()
            if len(part) >= 3:  # Minimum meaningful clause
                valid_clauses.append(part)

        # If only one clause or splitting produced garbage, return original
        if len(valid_clauses) <= 1:
            return [query]

        return valid_clauses

    def _parse_single_clause(
        self,
        clause: str,
        yacht_id: str,
        constraints: ConstraintSet
    ) -> Optional[Action]:
        """Parse a single clause into an Action."""
        clause_lower = clause.lower()

        # Extract verb
        verb = self._extract_verb(clause_lower)

        # Extract object
        obj = self._extract_object(clause_lower)

        # If neither found, return None
        if verb is None and obj is None:
            return None

        # Default verb based on context
        if verb is None:
            verb = ActionVerb.FIND  # Default to search

        # Default object based on verb
        if obj is None:
            obj = self._default_object_for_verb(verb)

        return Action(
            verb=verb,
            object=obj,
            constraints=constraints,
            source_text=clause,
        )

    def _extract_verb(self, text: str) -> Optional[ActionVerb]:
        """Extract verb from text (longest match first)."""
        # Sort patterns by length (longest first) for greedy matching
        sorted_patterns = sorted(
            VERB_PATTERNS.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for pattern, verb in sorted_patterns:
            if pattern in text:
                return verb

        return None

    def _extract_object(self, text: str) -> Optional[ActionObject]:
        """Extract object from text (longest match first)."""
        sorted_patterns = sorted(
            OBJECT_PATTERNS.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for pattern, obj in sorted_patterns:
            if pattern in text:
                return obj

        return None

    def _infer_object(self, text: str) -> ActionObject:
        """Infer object from text, or default to INVENTORY."""
        obj = self._extract_object(text.lower())
        return obj if obj else ActionObject.INVENTORY

    def _default_object_for_verb(self, verb: ActionVerb) -> ActionObject:
        """Default object for a verb when object is ambiguous."""
        defaults = {
            ActionVerb.LOG: ActionObject.LOGS,
            ActionVerb.SCHEDULE: ActionObject.WORK_ORDERS,
            ActionVerb.EXPLAIN: ActionObject.FAULTS,
        }
        return defaults.get(verb, ActionObject.INVENTORY)


# =============================================================================
# CAPABILITY REGISTRY
# =============================================================================

@dataclass
class ActionCapability:
    """What an action can do for an object."""
    verb: ActionVerb
    object: ActionObject
    supported_filters: List[str]  # Filter predicates this action supports
    required_columns: List[str]   # Columns that must exist
    output_card: str              # Card type for results


# Action capability registry
ACTION_CAPABILITIES: Dict[Tuple[ActionVerb, ActionObject], ActionCapability] = {
    (ActionVerb.SHOW, ActionObject.INVENTORY): ActionCapability(
        verb=ActionVerb.SHOW,
        object=ActionObject.INVENTORY,
        supported_filters=["out_of_stock", "low_stock", "in_stock", "location"],
        required_columns=["id", "name", "qty", "location"],
        output_card="inventory_card",
    ),
    (ActionVerb.LIST, ActionObject.WORK_ORDERS): ActionCapability(
        verb=ActionVerb.LIST,
        object=ActionObject.WORK_ORDERS,
        supported_filters=["pending", "in_progress", "completed", "overdue", "due_this_week"],
        required_columns=["id", "title", "status", "priority"],
        output_card="work_order_card",
    ),
    (ActionVerb.FIND, ActionObject.PARTS): ActionCapability(
        verb=ActionVerb.FIND,
        object=ActionObject.PARTS,
        supported_filters=["manufacturer", "category", "location"],
        required_columns=["id", "part_number", "name", "manufacturer"],
        output_card="part_card",
    ),
    (ActionVerb.LOOKUP, ActionObject.FAULTS): ActionCapability(
        verb=ActionVerb.LOOKUP,
        object=ActionObject.FAULTS,
        supported_filters=["severity", "equipment"],
        required_columns=["id", "fault_code", "title", "severity"],
        output_card="fault_card",
    ),
    (ActionVerb.FIND, ActionObject.DOCUMENTS): ActionCapability(
        verb=ActionVerb.FIND,
        object=ActionObject.DOCUMENTS,
        supported_filters=["type", "equipment", "system"],
        required_columns=["id", "title", "content", "source"],
        output_card="document_card",
    ),
    # Add more capabilities as needed
}


def get_capability(verb: ActionVerb, obj: ActionObject) -> Optional[ActionCapability]:
    """Get capability for action, or None if not supported."""
    return ACTION_CAPABILITIES.get((verb, obj))


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Action Algebra - Test Suite")
    print("=" * 60)

    from constraint_algebra import ConstraintSet, Constraint, ConstraintOp, Hardness, SemanticPredicate

    # Test 1: Simple read action
    print("\nTest 1: Simple read action")
    cs1 = ConstraintSet(
        yacht_id="test-yacht-001",
        constraints=[
            Constraint(
                variable="location",
                operator=ConstraintOp.ILIKE,
                value="%4%c%",
                hardness=Hardness.SOFT,
            ),
        ]
    )
    action1 = Action(
        verb=ActionVerb.SHOW,
        object=ActionObject.INVENTORY,
        constraints=cs1,
        source_text="show inventory in box 4c",
    )
    print(f"  Verb: {action1.verb.value}")
    print(f"  Object: {action1.object.value}")
    print(f"  Is Read: {action1.is_read}")
    print(f"  Execution: {action1.execution_class.value}")
    valid, errors = action1.validate()
    print(f"  Valid: {valid}")

    # Test 2: Write action (requires confirmation)
    print("\nTest 2: Write action")
    cs2 = ConstraintSet(
        yacht_id="test-yacht-001",
        constraints=[
            Constraint(
                variable="equipment",
                operator=ConstraintOp.ILIKE,
                value="%main engine%",
                hardness=Hardness.HARD,
            ),
        ]
    )
    action2 = Action(
        verb=ActionVerb.CREATE,
        object=ActionObject.WORK_ORDERS,
        constraints=cs2,
        source_text="create work order for main engine",
    )
    print(f"  Verb: {action2.verb.value}")
    print(f"  Is Write: {action2.is_write}")
    print(f"  Execution: {action2.execution_class.value}")
    print(f"  Requires Confirmation: {action2.requires_confirmation}")

    # Test 3: Action parser
    print("\nTest 3: Action parser")
    parser = ActionParser()

    test_queries = [
        "show inventory in box 4c",
        "list pending work orders",
        "find oil filter for main engine",
        "create work order for generator maintenance",
        "show inventory and create work order",  # Multi-action
    ]

    for query in test_queries:
        cs = ConstraintSet(yacht_id="test-yacht-001")
        plan = parser.parse(query, "test-yacht-001", cs)
        print(f"\n  Query: {query!r}")
        print(f"  Actions: {len(plan.actions)}")
        for i, a in enumerate(plan.actions):
            print(f"    [{i+1}] {a.verb.value} {a.object.value} ({a.execution_class.value})")
        if plan.decomposition_reason:
            print(f"  Decomposition: {plan.decomposition_reason}")

"""
Decision Engine Service
========================

Phase 11.1 Implementation: Turns Phase 10 policy specs into runtime decisions.

Policy Sources:
- E017_TRIGGER_CONTRACTS.yaml (trigger contracts)
- E018_THRESHOLD_MODEL.md (confidence scoring: intent 0.4 + entity 0.4 + situation 0.2)
- E019_STATE_GUARDS.yaml (mutual exclusion / state machine)

Output: ActionDecision[] for each action in the 30 action registry.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ActionTier(str, Enum):
    PRIMARY = "primary"
    CONDITIONAL = "conditional"
    RARE = "rare"


class BlockedByType(str, Enum):
    STATE_GUARD = "state_guard"
    MISSING_TRIGGER = "missing_trigger"
    THRESHOLD = "threshold"
    PERMISSION = "permission"
    FORBIDDEN = "forbidden"


@dataclass
class ConfidenceBreakdown:
    intent: float = 0.0
    entity: float = 0.0
    situation: float = 0.0


@dataclass
class BlockedBy:
    type: BlockedByType
    detail: str


@dataclass
class ActionDecision:
    action: str
    allowed: bool
    tier: ActionTier
    confidence: float
    reasons: List[str]
    breakdown: ConfidenceBreakdown
    blocked_by: Optional[BlockedBy] = None
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "action": self.action,
            "allowed": self.allowed,
            "tier": self.tier.value,
            "confidence": round(self.confidence, 3),
            "reasons": self.reasons,
            "breakdown": {
                "intent": round(self.breakdown.intent, 3),
                "entity": round(self.breakdown.entity, 3),
                "situation": round(self.breakdown.situation, 3),
            },
            "explanation": self.explanation,
        }
        if self.blocked_by:
            result["blocked_by"] = {
                "type": self.blocked_by.type.value,
                "detail": self.blocked_by.detail,
            }
        return result


@dataclass
class DecisionContext:
    """Input context for decision engine."""
    yacht_id: str
    user_id: str
    user_role: str
    detected_intents: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    situation: Dict[str, Any] = field(default_factory=dict)
    environment: str = "at_sea"

    # Entity shortcuts
    @property
    def work_order(self) -> Optional[Dict]:
        for e in self.entities:
            if e.get("type") == "work_order":
                return e
        return None

    @property
    def fault(self) -> Optional[Dict]:
        for e in self.entities:
            if e.get("type") == "fault":
                return e
        return None

    @property
    def equipment(self) -> Optional[Dict]:
        for e in self.entities:
            if e.get("type") == "equipment":
                return e
        return None


class DecisionEngine:
    """
    Core Decision Engine.

    Loads policy files (E017, E019) and evaluates decisions for all 30 actions.
    """

    # Tier thresholds per E018
    TIER_THRESHOLDS = {
        ActionTier.PRIMARY: 0.50,
        ActionTier.CONDITIONAL: 0.60,
        ActionTier.RARE: 0.70,
    }

    # HOD roles per E017/E019
    HOD_ROLES = frozenset(["chief_engineer", "eto", "captain", "manager", "hod"])

    def __init__(self, policy_dir: Optional[Path] = None):
        """
        Initialize Decision Engine with policy files.

        Args:
            policy_dir: Directory containing E017/E019 YAML files.
                       Defaults to apps/api/config/
        """
        if policy_dir is None:
            # Default: config/ directory relative to apps/api/
            # This works both locally and on Render (where root is apps/api/)
            policy_dir = Path(__file__).parent.parent / "config"

        self.policy_dir = policy_dir
        self.trigger_contracts: Dict[str, Dict] = {}
        self.state_guards: Dict[str, Dict] = {}
        self._load_policies()

    def _load_policies(self):
        """Load E017 and E019 YAML files."""
        e017_path = self.policy_dir / "E017_TRIGGER_CONTRACTS.yaml"
        e019_path = self.policy_dir / "E019_STATE_GUARDS.yaml"

        # Load E017 Trigger Contracts
        if e017_path.exists():
            with open(e017_path, 'r') as f:
                raw = yaml.safe_load(f)
                # Filter out meta keys (start with _)
                self.trigger_contracts = {
                    k: v for k, v in raw.items()
                    if not k.startswith('_') and isinstance(v, dict)
                }
            logger.info(f"Loaded {len(self.trigger_contracts)} trigger contracts from E017")
        else:
            logger.error(f"E017 not found at {e017_path}")
            self.trigger_contracts = {}

        # Load E019 State Guards
        if e019_path.exists():
            with open(e019_path, 'r') as f:
                self.state_guards = yaml.safe_load(f) or {}
            logger.info(f"Loaded state guards from E019")
        else:
            logger.error(f"E019 not found at {e019_path}")
            self.state_guards = {}

    def evaluate(self, context: DecisionContext) -> List[ActionDecision]:
        """
        Evaluate all actions and return decisions.

        Args:
            context: DecisionContext with intent, entities, situation

        Returns:
            List of ActionDecision for all 30 actions
        """
        decisions = []

        for action_name, contract in self.trigger_contracts.items():
            decision = self._evaluate_action(action_name, contract, context)
            decisions.append(decision)

        return decisions

    def _evaluate_action(
        self,
        action_name: str,
        contract: Dict,
        context: DecisionContext
    ) -> ActionDecision:
        """Evaluate a single action against its contract."""

        # Get tier
        tier_str = contract.get("tier", "conditional")
        tier = ActionTier(tier_str)

        # Get threshold for this tier
        threshold = self.TIER_THRESHOLDS[tier]

        # Build reasons list
        reasons: List[str] = []

        # 1. Check forbidden contexts first (hard block)
        forbidden_check = self._check_forbidden(action_name, contract, context)
        if forbidden_check:
            return ActionDecision(
                action=action_name,
                allowed=False,
                tier=tier,
                confidence=0.0,
                reasons=[forbidden_check],
                breakdown=ConfidenceBreakdown(),
                blocked_by=BlockedBy(BlockedByType.FORBIDDEN, forbidden_check),
                explanation=contract.get("explanation_template", action_name),
            )

        # 2. Check state guards (mutual exclusion)
        guard_check = self._check_state_guards(action_name, context)
        if guard_check:
            return ActionDecision(
                action=action_name,
                allowed=False,
                tier=tier,
                confidence=0.0,
                reasons=[guard_check],
                breakdown=ConfidenceBreakdown(),
                blocked_by=BlockedBy(BlockedByType.STATE_GUARD, guard_check),
                explanation=contract.get("explanation_template", action_name),
            )

        # 3. Check permission (role-based)
        permission_check = self._check_permission(action_name, contract, context)
        if permission_check:
            return ActionDecision(
                action=action_name,
                allowed=False,
                tier=tier,
                confidence=0.0,
                reasons=[permission_check],
                breakdown=ConfidenceBreakdown(),
                blocked_by=BlockedBy(BlockedByType.PERMISSION, permission_check),
                explanation=contract.get("explanation_template", action_name),
            )

        # 4. Calculate confidence scores per E018
        intent_score = self._score_intent(contract, context, reasons)
        entity_score = self._score_entity(contract, context, reasons)
        situation_score = self._score_situation(contract, context, reasons)

        # Weighted sum: intent 0.4 + entity 0.4 + situation 0.2
        total_confidence = (intent_score * 0.4) + (entity_score * 0.4) + (situation_score * 0.2)

        breakdown = ConfidenceBreakdown(
            intent=intent_score,
            entity=entity_score,
            situation=situation_score,
        )

        # 5. Check threshold
        allowed = total_confidence >= threshold
        if not allowed:
            reasons.append(f"Confidence {total_confidence:.2f} below threshold {threshold}")
            blocked_by = BlockedBy(BlockedByType.THRESHOLD, f"Score {total_confidence:.2f} < {threshold}")
        else:
            blocked_by = None

        # 6. Build explanation
        explanation = self._build_explanation(contract, context)

        return ActionDecision(
            action=action_name,
            allowed=allowed,
            tier=tier,
            confidence=total_confidence,
            reasons=reasons,
            breakdown=breakdown,
            blocked_by=blocked_by,
            explanation=explanation,
        )

    def _check_forbidden(
        self,
        action_name: str,
        contract: Dict,
        context: DecisionContext
    ) -> Optional[str]:
        """Check forbidden contexts. Returns reason string if blocked."""
        forbidden_list = contract.get("forbidden", [])

        for forbidden in forbidden_list:
            # Map forbidden context to check
            if forbidden == "work_order_closed":
                wo = context.work_order
                if wo and wo.get("status") == "closed":
                    return "Work order is closed"

            elif forbidden == "work_order_cancelled":
                wo = context.work_order
                if wo and wo.get("status") == "cancelled":
                    return "Work order was cancelled"

            elif forbidden == "fault_closed":
                fault = context.fault
                if fault and fault.get("status") == "closed":
                    return "Fault is already resolved"

            elif forbidden == "fault_has_work_order":
                fault = context.fault
                if fault and fault.get("has_work_order"):
                    return "A work order already exists for this fault"

            elif forbidden == "no_work_order":
                if not context.work_order:
                    return "No work order selected"

            elif forbidden == "no_equipment":
                if not context.equipment:
                    return "No equipment selected"

            elif forbidden == "no_fault":
                if not context.fault:
                    return "No fault selected"

            elif forbidden == "no_entity_context":
                if not context.entities:
                    return "No entity context"

            elif forbidden == "user_not_hod":
                if context.user_role.lower() not in self.HOD_ROLES:
                    return "Requires supervisor permissions"

            elif forbidden == "not_in_shipyard":
                if context.environment != "shipyard":
                    return "Only available in shipyard mode"

            elif forbidden == "work_order_open":
                wo = context.work_order
                if wo and wo.get("status") == "open":
                    return "Work order must be started first"

            elif forbidden == "fault_has_active_work_order":
                fault = context.fault
                if fault and fault.get("has_work_order"):
                    wo = context.work_order
                    if wo and wo.get("status") not in ("closed", "completed", "cancelled"):
                        return "Fault has active work order"

        return None

    def _check_state_guards(
        self,
        action_name: str,
        context: DecisionContext
    ) -> Optional[str]:
        """Check state guards from E019. Returns reason string if blocked."""
        # Check work order state machine
        wo_guards = self.state_guards.get("work_order", {}).get("state_guards", {})
        if action_name in wo_guards:
            guard = wo_guards[action_name]
            required_state = guard.get("requires_state")
            wo = context.work_order

            if required_state and wo:
                current_status = wo.get("status", "").lower()
                if isinstance(required_state, list):
                    if current_status not in required_state:
                        return f"Work order status must be {' or '.join(required_state)}, currently {current_status}"
                elif current_status != required_state:
                    return f"Work order status must be {required_state}, currently {current_status}"

        # Check fault state machine
        fault_guards = self.state_guards.get("fault", {}).get("state_guards", {})
        if action_name in fault_guards:
            guard = fault_guards[action_name]
            required_state = guard.get("requires_state")
            fault = context.fault

            if required_state and fault:
                current_status = fault.get("status", "").lower()
                if isinstance(required_state, list):
                    if current_status not in required_state:
                        return f"Fault status must be {' or '.join(required_state)}, currently {current_status}"
                elif current_status != required_state:
                    return f"Fault status must be {required_state}, currently {current_status}"

        return None

    def _check_permission(
        self,
        action_name: str,
        contract: Dict,
        context: DecisionContext
    ) -> Optional[str]:
        """Check role-based permissions. Returns reason string if blocked."""
        forbidden_list = contract.get("forbidden", [])

        # Check if action requires HOD and user is not HOD
        if "user_not_hod" in forbidden_list:
            if context.user_role.lower() not in self.HOD_ROLES:
                return "This action requires supervisor permissions"

        # Check requires section for explicit role requirements
        requires = contract.get("requires", {})
        situation_required = requires.get("situation", [])

        if "user_is_hod" in situation_required:
            if context.user_role.lower() not in self.HOD_ROLES:
                return "This action requires supervisor permissions"

        return None

    def _score_intent(
        self,
        contract: Dict,
        context: DecisionContext,
        reasons: List[str]
    ) -> float:
        """Score intent match per E018."""
        required_intents = contract.get("requires", {}).get("intent", [])

        if not required_intents:
            reasons.append("No intent requirement (1.0)")
            return 1.0

        if not context.detected_intents:
            reasons.append("No intent detected (0.0)")
            return 0.0

        # Check for exact match
        for detected in context.detected_intents:
            detected_lower = detected.lower()
            for required in required_intents:
                if detected_lower == required.lower():
                    reasons.append(f"Intent match: {detected}")
                    return 1.0

        # Check for partial/semantic match
        for detected in context.detected_intents:
            detected_lower = detected.lower()
            for required in required_intents:
                # Substring match
                if required.lower() in detected_lower or detected_lower in required.lower():
                    reasons.append(f"Partial intent match: {detected} ~ {required}")
                    return 0.7

        # No match
        reasons.append(f"Intent mismatch: {context.detected_intents} not in {required_intents}")
        return 0.0

    def _score_entity(
        self,
        contract: Dict,
        context: DecisionContext,
        reasons: List[str]
    ) -> float:
        """Score entity match per E018."""
        requires = contract.get("requires", {})
        entity_req = requires.get("entities", {})

        min_required = entity_req.get("min", [])
        min_one_of = entity_req.get("min_one_of", [])

        # No entity requirement
        if not min_required and not min_one_of:
            reasons.append("No entity requirement (1.0)")
            return 1.0

        entity_types = {e.get("type", "").lower() for e in context.entities}

        # Check min (all required)
        if min_required:
            min_required_lower = [r.lower() for r in min_required]
            missing = [r for r in min_required_lower if r not in entity_types]
            if missing:
                reasons.append(f"Missing required entities: {missing}")
                return 0.0
            else:
                # Check if entities have IDs (higher quality)
                has_ids = all(
                    e.get("id") for e in context.entities
                    if e.get("type", "").lower() in min_required_lower
                )
                if has_ids:
                    reasons.append(f"All required entities with IDs: {min_required}")
                    return 1.0
                else:
                    reasons.append(f"Required entities present (no IDs): {min_required}")
                    return 0.7

        # Check min_one_of (at least one)
        if min_one_of:
            min_one_lower = [r.lower() for r in min_one_of]
            found = [r for r in min_one_lower if r in entity_types]
            if found:
                reasons.append(f"Found one of required entities: {found}")
                return 1.0
            else:
                reasons.append(f"None of required entities present: {min_one_of}")
                return 0.0

        return 1.0

    def _score_situation(
        self,
        contract: Dict,
        context: DecisionContext,
        reasons: List[str]
    ) -> float:
        """Score situation match per E018."""
        requires = contract.get("requires", {})
        situation_required = requires.get("situation", [])

        if not situation_required:
            reasons.append("No situation requirement (1.0)")
            return 1.0

        matched = 0
        total = len(situation_required)

        for sit in situation_required:
            if self._check_situation(sit, context):
                matched += 1
                reasons.append(f"Situation met: {sit}")
            else:
                reasons.append(f"Situation not met: {sit}")

        score = matched / total if total > 0 else 1.0
        return score

    def _check_situation(self, situation: str, context: DecisionContext) -> bool:
        """Check a single situation condition."""
        sit_lower = situation.lower()

        if sit_lower == "work_order_active":
            wo = context.work_order
            return wo and wo.get("status") in ("open", "in_progress")

        elif sit_lower == "work_order_open":
            wo = context.work_order
            return wo and wo.get("status") == "open"

        elif sit_lower == "work_order_in_progress":
            wo = context.work_order
            return wo and wo.get("status") == "in_progress"

        elif sit_lower == "fault_open":
            fault = context.fault
            return fault and fault.get("status") != "closed"

        elif sit_lower == "fault_closed":
            fault = context.fault
            return fault and fault.get("status") == "closed"

        elif sit_lower == "fault_has_no_work_order":
            fault = context.fault
            return fault and not fault.get("has_work_order")

        elif sit_lower == "fault_not_acknowledged":
            fault = context.fault
            return fault and not fault.get("acknowledged")

        elif sit_lower == "equipment_identified":
            return context.equipment is not None

        elif sit_lower == "equipment_has_manual":
            eq = context.equipment
            return eq and eq.get("has_manual")

        elif sit_lower == "user_is_hod":
            return context.user_role.lower() in self.HOD_ROLES

        elif sit_lower == "environment_shipyard":
            return context.environment == "shipyard"

        elif sit_lower == "active_work_context":
            return bool(context.entities)

        elif sit_lower == "work_order_has_checklist":
            wo = context.work_order
            return wo and wo.get("has_checklist")

        elif sit_lower in ("fault_exists", "fault_identified"):
            return context.fault is not None

        elif sit_lower == "in_shipyard_or_has_worklist":
            return context.environment == "shipyard" or context.work_order is not None

        # Default: not matched
        return False

    def _build_explanation(self, contract: Dict, context: DecisionContext) -> str:
        """Build human-readable explanation from template."""
        template = contract.get("explanation_template", "")

        if not template:
            return ""

        # Simple variable substitution
        explanation = template

        # Replace entity references
        if context.work_order:
            explanation = explanation.replace(
                "{work_order.title}",
                context.work_order.get("title", context.work_order.get("name", "Work Order"))
            )

        if context.fault:
            explanation = explanation.replace(
                "{fault.title}",
                context.fault.get("title", context.fault.get("name", "Fault"))
            )

        if context.equipment:
            explanation = explanation.replace(
                "{equipment.name}",
                context.equipment.get("name", "Equipment")
            )

        # Generic entity reference
        if context.entities:
            primary = context.entities[0]
            explanation = explanation.replace(
                "{entity.summary}",
                primary.get("name", primary.get("title", "Item"))
            )

        return explanation


# Global instance (loaded once at module import)
_engine: Optional[DecisionEngine] = None


def get_decision_engine() -> DecisionEngine:
    """Get or create the global Decision Engine instance."""
    global _engine
    if _engine is None:
        _engine = DecisionEngine()
    return _engine


def evaluate_decisions(
    yacht_id: str,
    user_id: str,
    user_role: str,
    detected_intents: List[str],
    entities: List[Dict[str, Any]],
    situation: Dict[str, Any],
    environment: str = "at_sea",
) -> Dict[str, Any]:
    """
    Main entry point for decision evaluation.

    Returns:
        Dict with execution_id and decisions list
    """
    engine = get_decision_engine()

    context = DecisionContext(
        yacht_id=yacht_id,
        user_id=user_id,
        user_role=user_role,
        detected_intents=detected_intents,
        entities=entities,
        situation=situation,
        environment=environment,
    )

    decisions = engine.evaluate(context)

    execution_id = str(uuid.uuid4())

    return {
        "execution_id": execution_id,
        "yacht_id": yacht_id,
        "user_id": user_id,
        "decisions": [d.to_dict() for d in decisions],
        "allowed_count": sum(1 for d in decisions if d.allowed),
        "blocked_count": sum(1 for d in decisions if not d.allowed),
    }

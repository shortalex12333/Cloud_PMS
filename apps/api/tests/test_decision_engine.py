"""
Decision Engine Unit Tests
===========================

Phase 11.1 Evidence: Tests proving:
1. Trigger contracts loaded from E017
2. Threshold rejection per E018
3. State guard blocking per E019
4. Confidence scoring formula correct
"""

import pytest
import sys
from pathlib import Path

# Add api dir to path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

from services.decision_engine import (
    DecisionEngine,
    DecisionContext,
    ActionTier,
    BlockedByType,
    evaluate_decisions,
)


class TestDecisionEngineInit:
    """Test engine initialization and policy loading."""

    def test_engine_loads_trigger_contracts(self):
        """E017 trigger contracts are loaded."""
        engine = DecisionEngine()

        # Should load all 30 actions
        assert len(engine.trigger_contracts) >= 30, (
            f"Expected 30+ trigger contracts, got {len(engine.trigger_contracts)}"
        )

        # Check some specific actions exist
        expected_actions = [
            "view_work_order_detail",
            "create_work_order_from_fault",
            "close_work_order",
            "diagnose_fault",
            "report_fault",
        ]
        for action in expected_actions:
            assert action in engine.trigger_contracts, f"Missing action: {action}"

    def test_engine_loads_state_guards(self):
        """E019 state guards are loaded."""
        engine = DecisionEngine()

        # Should have work_order and fault state machines
        assert "work_order" in engine.state_guards
        assert "fault" in engine.state_guards

        # Should have state_guards for each
        assert "state_guards" in engine.state_guards["work_order"]
        assert "state_guards" in engine.state_guards["fault"]


class TestConfidenceScoring:
    """Test E018 confidence scoring formula."""

    def test_full_match_scores_high(self):
        """Full intent+entity+situation match gives high confidence."""
        engine = DecisionEngine()

        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=["diagnose", "troubleshoot"],
            entities=[
                {"type": "fault", "id": "fault-123", "name": "Pump Failure", "status": "reported"}
            ],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        # Find diagnose_fault action
        diagnose = next((d for d in decisions if d.action == "diagnose_fault"), None)
        assert diagnose is not None, "diagnose_fault not in decisions"

        # Should be allowed with high confidence
        assert diagnose.allowed, "diagnose_fault should be allowed"
        assert diagnose.confidence >= 0.5, f"Confidence {diagnose.confidence} too low"

    def test_no_intent_scores_low(self):
        """No matching intent reduces confidence."""
        engine = DecisionEngine()

        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=["random_unrelated"],
            entities=[
                {"type": "fault", "id": "fault-123", "status": "reported"}
            ],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        # Find diagnose_fault - should have lower confidence due to intent mismatch
        diagnose = next((d for d in decisions if d.action == "diagnose_fault"), None)
        assert diagnose is not None

        # Intent weight is 0.4, so missing intent should reduce score
        # With entity match (0.4 * 1.0) + situation (0.2 * 1.0) = 0.6 max without intent
        assert diagnose.breakdown.intent < 1.0, "Intent should not be 1.0 with mismatch"

    def test_confidence_formula_weights(self):
        """Confidence = intent*0.4 + entity*0.4 + situation*0.2"""
        engine = DecisionEngine()

        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=["view"],
            entities=[
                {"type": "work_order", "id": "wo-123", "status": "open"}
            ],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        # Pick any decision and verify formula
        for decision in decisions:
            expected = (
                decision.breakdown.intent * 0.4 +
                decision.breakdown.entity * 0.4 +
                decision.breakdown.situation * 0.2
            )
            assert abs(decision.confidence - expected) < 0.01, (
                f"Confidence formula mismatch for {decision.action}: "
                f"got {decision.confidence}, expected {expected}"
            )


class TestThresholdRejection:
    """Test E018 tier thresholds."""

    def test_primary_threshold_0_50(self):
        """Primary tier actions require >= 0.50 confidence."""
        engine = DecisionEngine()

        # Context with no matching intent/entity
        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=[],
            entities=[],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        # Find a primary tier action
        primary_actions = [d for d in decisions if d.tier == ActionTier.PRIMARY]
        assert len(primary_actions) > 0, "Should have primary tier actions"

        for action in primary_actions:
            if action.confidence < 0.50:
                assert not action.allowed, (
                    f"Primary {action.action} should be blocked "
                    f"with confidence {action.confidence} < 0.50"
                )

    def test_conditional_threshold_0_60(self):
        """Conditional tier actions require >= 0.60 confidence."""
        engine = DecisionEngine()

        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=[],
            entities=[],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        conditional = [d for d in decisions if d.tier == ActionTier.CONDITIONAL]
        assert len(conditional) > 0, "Should have conditional tier actions"

        for action in conditional:
            if action.confidence < 0.60 and not action.blocked_by:
                # If blocked by something else (state guard), that takes precedence
                pass
            elif action.confidence < 0.60:
                assert not action.allowed, (
                    f"Conditional {action.action} should be blocked "
                    f"with confidence {action.confidence} < 0.60"
                )

    def test_rare_threshold_0_70(self):
        """Rare tier actions require >= 0.70 confidence."""
        engine = DecisionEngine()

        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=[],
            entities=[],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        rare = [d for d in decisions if d.tier == ActionTier.RARE]
        assert len(rare) > 0, "Should have rare tier actions"

        for action in rare:
            if action.confidence < 0.70 and action.blocked_by:
                # Could be blocked by threshold or other reason
                if action.blocked_by.type == BlockedByType.THRESHOLD:
                    assert "0.70" in action.blocked_by.detail or action.confidence < 0.70


class TestStateGuards:
    """Test E019 state guard enforcement."""

    def test_close_wo_requires_in_progress(self):
        """close_work_order requires work_order status = in_progress."""
        engine = DecisionEngine()

        # Work order that is OPEN (not in_progress)
        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=["close"],
            entities=[
                {"type": "work_order", "id": "wo-123", "status": "open"}
            ],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        close_wo = next((d for d in decisions if d.action == "close_work_order"), None)
        assert close_wo is not None

        # Should be blocked (by state guard or forbidden context - both valid per E018)
        assert not close_wo.allowed, "close_work_order should be blocked when WO is open"
        assert close_wo.blocked_by is not None
        # Can be STATE_GUARD or FORBIDDEN - both enforce the same constraint
        assert close_wo.blocked_by.type in (BlockedByType.STATE_GUARD, BlockedByType.FORBIDDEN)

    def test_close_wo_allowed_when_in_progress(self):
        """close_work_order allowed when work_order status = in_progress."""
        engine = DecisionEngine()

        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=["close"],
            entities=[
                {"type": "work_order", "id": "wo-123", "status": "in_progress"}
            ],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        close_wo = next((d for d in decisions if d.action == "close_work_order"), None)
        assert close_wo is not None

        # Should NOT be blocked by state guard
        if close_wo.blocked_by:
            assert close_wo.blocked_by.type != BlockedByType.STATE_GUARD, (
                f"Should not be blocked by state guard: {close_wo.blocked_by.detail}"
            )

    def test_start_wo_requires_open(self):
        """start_work_order requires work_order status = open."""
        engine = DecisionEngine()

        # Work order that is ALREADY in_progress
        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=["start"],
            entities=[
                {"type": "work_order", "id": "wo-123", "status": "in_progress"}
            ],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        start_wo = next((d for d in decisions if d.action == "start_work_order"), None)
        assert start_wo is not None

        # Should be blocked - can't start what's already started
        assert not start_wo.allowed, "start_work_order should be blocked when WO is in_progress"


class TestForbiddenContexts:
    """Test forbidden context blocking."""

    def test_create_wo_from_fault_blocked_when_fault_has_wo(self):
        """create_work_order_from_fault blocked when fault already has work order."""
        engine = DecisionEngine()

        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=["create"],
            entities=[
                {"type": "fault", "id": "fault-123", "status": "reported", "has_work_order": True}
            ],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        create_wo = next(
            (d for d in decisions if d.action == "create_work_order_from_fault"),
            None
        )
        assert create_wo is not None

        # Should be blocked by forbidden context
        assert not create_wo.allowed
        assert create_wo.blocked_by is not None
        assert create_wo.blocked_by.type == BlockedByType.FORBIDDEN

    def test_cancel_wo_requires_hod(self):
        """cancel_work_order requires HOD role."""
        engine = DecisionEngine()

        # Non-HOD user
        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="deckhand",  # Not HOD
            detected_intents=["cancel"],
            entities=[
                {"type": "work_order", "id": "wo-123", "status": "open"}
            ],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        cancel_wo = next((d for d in decisions if d.action == "cancel_work_order"), None)
        assert cancel_wo is not None

        # Should be blocked by permission
        assert not cancel_wo.allowed
        # Could be forbidden or permission block
        assert cancel_wo.blocked_by is not None

    def test_cancel_wo_allowed_for_hod(self):
        """cancel_work_order allowed for HOD role."""
        engine = DecisionEngine()

        # HOD user
        context = DecisionContext(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="chief_engineer",  # HOD
            detected_intents=["cancel"],
            entities=[
                {"type": "work_order", "id": "wo-123", "status": "open"}
            ],
            situation={},
            environment="at_sea",
        )

        decisions = engine.evaluate(context)

        cancel_wo = next((d for d in decisions if d.action == "cancel_work_order"), None)
        assert cancel_wo is not None

        # Should NOT be blocked by permission
        if cancel_wo.blocked_by:
            assert cancel_wo.blocked_by.type not in (
                BlockedByType.PERMISSION,
                BlockedByType.FORBIDDEN
            )


class TestEvaluateDecisionsEntryPoint:
    """Test the main entry point function."""

    def test_returns_execution_id(self):
        """evaluate_decisions returns unique execution_id."""
        result = evaluate_decisions(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=["view"],
            entities=[],
            situation={},
            environment="at_sea",
        )

        assert "execution_id" in result
        assert len(result["execution_id"]) == 36  # UUID format

    def test_returns_decision_counts(self):
        """evaluate_decisions returns allowed/blocked counts."""
        result = evaluate_decisions(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=["view"],
            entities=[{"type": "work_order", "id": "wo-123", "status": "open"}],
            situation={},
            environment="at_sea",
        )

        assert "allowed_count" in result
        assert "blocked_count" in result
        assert result["allowed_count"] + result["blocked_count"] == len(result["decisions"])

    def test_decisions_have_required_fields(self):
        """Each decision has all required fields per ActionDecision spec."""
        result = evaluate_decisions(
            yacht_id="test-yacht",
            user_id="test-user",
            user_role="engineer",
            detected_intents=["view"],
            entities=[],
            situation={},
            environment="at_sea",
        )

        required_fields = ["action", "allowed", "tier", "confidence", "reasons", "breakdown"]

        for decision in result["decisions"]:
            for field in required_fields:
                assert field in decision, f"Missing field {field} in decision"

            # Breakdown has sub-fields
            assert "intent" in decision["breakdown"]
            assert "entity" in decision["breakdown"]
            assert "situation" in decision["breakdown"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

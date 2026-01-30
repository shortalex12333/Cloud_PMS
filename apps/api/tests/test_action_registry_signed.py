"""
Unit Tests for Action Registry SIGNED Variant

Tests SIGNED action variant functionality including:
- Enum definition
- allowed_roles field
- Validation logic
- to_dict() serialization
- Helper methods (is_signed())

Run:
    pytest apps/api/tests/test_action_registry_signed.py -v
"""

import pytest
from actions.action_registry import (
    Action,
    ActionRegistry,
    ActionVariant,
    ActionUI,
    ActionExecution,
    ActionMutation,
    ActionAudit,
    AuditLevel,
)


# =============================================================================
# Enum Tests
# =============================================================================

def test_action_variant_has_signed():
    """Test SIGNED variant exists in enum"""
    assert hasattr(ActionVariant, 'SIGNED')
    assert ActionVariant.SIGNED == "SIGNED"
    assert ActionVariant.SIGNED.value == "SIGNED"


def test_action_variant_all_values():
    """Test all three variants exist"""
    variants = [v.value for v in ActionVariant]
    assert "READ" in variants
    assert "MUTATE" in variants
    assert "SIGNED" in variants
    assert len(variants) == 3


# =============================================================================
# Action Dataclass Tests
# =============================================================================

def test_action_has_allowed_roles_field():
    """Test Action dataclass has allowed_roles field"""
    action = Action(
        action_id="test_action",
        label="Test",
        variant=ActionVariant.READ,
        domain="test"
    )
    assert hasattr(action, 'allowed_roles')
    assert action.allowed_roles == []


def test_signed_action_requires_allowed_roles():
    """Test SIGNED action must have allowed_roles"""
    with pytest.raises(ValueError, match="must specify allowed_roles"):
        Action(
            action_id="test_signed",
            label="Test Signed",
            variant=ActionVariant.SIGNED,
            domain="test",
            allowed_roles=[]  # Empty list should fail
        )


def test_signed_action_with_allowed_roles_succeeds():
    """Test SIGNED action with allowed_roles is valid"""
    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.SIGNED,
        domain="test",
        allowed_roles=["captain", "chief_engineer"]
    )
    assert action.variant == ActionVariant.SIGNED
    assert action.allowed_roles == ["captain", "chief_engineer"]


def test_signed_action_implies_requires_signature():
    """Test SIGNED action automatically sets requires_signature=True"""
    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.SIGNED,
        domain="test",
        allowed_roles=["captain"]
    )
    assert action.mutation is not None
    assert action.mutation.requires_signature is True


def test_signed_action_implies_dropdown_only():
    """Test SIGNED action automatically sets dropdown_only=True"""
    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.SIGNED,
        domain="test",
        allowed_roles=["captain"]
    )
    assert action.ui.dropdown_only is True


def test_signed_action_implies_full_audit():
    """Test SIGNED action automatically sets audit level to FULL"""
    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.SIGNED,
        domain="test",
        allowed_roles=["captain"]
    )
    assert action.audit.level == AuditLevel.FULL


def test_signed_action_cannot_be_primary():
    """Test SIGNED action cannot be primary"""
    with pytest.raises(ValueError, match="must be READ"):
        Action(
            action_id="test_signed",
            label="Test Signed",
            variant=ActionVariant.SIGNED,
            domain="test",
            allowed_roles=["captain"],
            ui=ActionUI(primary=True)
        )


# =============================================================================
# Registry Validation Tests
# =============================================================================

def test_registry_validates_signed_has_allowed_roles():
    """Test registry.validate() catches SIGNED without allowed_roles"""
    registry = ActionRegistry()

    # Create action bypassing __post_init__ validation
    # (simulates corrupted state)
    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.READ,  # Start as READ
        domain="test"
    )
    action.variant = ActionVariant.SIGNED  # Manually change to SIGNED
    action.allowed_roles = []  # Empty

    registry._actions["test_signed"] = action

    errors = registry.validate()
    assert any("has no allowed_roles" in err for err in errors)


def test_registry_validates_signed_has_signature_required():
    """Test registry.validate() catches SIGNED without requires_signature"""
    registry = ActionRegistry()

    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.SIGNED,
        domain="test",
        allowed_roles=["captain"]
    )
    # Manually break the invariant
    action.mutation.requires_signature = False

    registry._actions["test_signed"] = action

    errors = registry.validate()
    assert any("must have requires_signature=True" in err for err in errors)


def test_registry_validates_signed_action_passes():
    """Test properly configured SIGNED action passes validation"""
    registry = ActionRegistry()

    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.SIGNED,
        domain="test",
        allowed_roles=["captain", "chief_engineer"]
    )

    registry.register(action)
    errors = registry.validate()

    # Should have no errors related to this action
    signed_errors = [e for e in errors if "test_signed" in e]
    assert len(signed_errors) == 0


# =============================================================================
# to_dict() Serialization Tests
# =============================================================================

def test_to_dict_includes_allowed_roles():
    """Test to_dict() includes allowed_roles field"""
    registry = ActionRegistry()

    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.SIGNED,
        domain="test",
        allowed_roles=["captain", "chief_engineer", "manager"]
    )

    registry.register(action)
    result = registry.to_dict()

    assert "test_signed" in result["actions"]
    assert "allowed_roles" in result["actions"]["test_signed"]
    assert result["actions"]["test_signed"]["allowed_roles"] == ["captain", "chief_engineer", "manager"]


def test_to_dict_read_action_has_empty_allowed_roles():
    """Test READ action has empty allowed_roles in to_dict()"""
    registry = ActionRegistry()

    action = Action(
        action_id="test_read",
        label="Test Read",
        variant=ActionVariant.READ,
        domain="test"
    )

    registry.register(action)
    result = registry.to_dict()

    assert result["actions"]["test_read"]["allowed_roles"] == []


def test_to_dict_signed_action_serialization():
    """Test SIGNED action full serialization"""
    registry = ActionRegistry()

    action = Action(
        action_id="reassign_work_order",
        label="Reassign",
        variant=ActionVariant.SIGNED,
        domain="work_orders",
        entity_types=["work_order"],
        allowed_roles=["captain", "chief_engineer"],
        ui=ActionUI(dropdown_only=True, icon="user-switch"),
        execution=ActionExecution(handler="reassign_work_order"),
        description="Reassign work order to different crew member"
    )

    registry.register(action)
    result = registry.to_dict()

    action_dict = result["actions"]["reassign_work_order"]
    assert action_dict["variant"] == "SIGNED"
    assert action_dict["allowed_roles"] == ["captain", "chief_engineer"]
    assert action_dict["requires_signature"] is True
    assert action_dict["dropdown_only"] is True


# =============================================================================
# Helper Method Tests
# =============================================================================

def test_is_signed_method_exists():
    """Test registry has is_signed() method"""
    registry = ActionRegistry()
    assert hasattr(registry, 'is_signed')
    assert callable(registry.is_signed)


def test_is_signed_returns_true_for_signed_action():
    """Test is_signed() returns True for SIGNED action"""
    registry = ActionRegistry()

    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.SIGNED,
        domain="test",
        allowed_roles=["captain"]
    )

    registry.register(action)
    assert registry.is_signed("test_signed") is True


def test_is_signed_returns_false_for_read_action():
    """Test is_signed() returns False for READ action"""
    registry = ActionRegistry()

    action = Action(
        action_id="test_read",
        label="Test Read",
        variant=ActionVariant.READ,
        domain="test"
    )

    registry.register(action)
    assert registry.is_signed("test_read") is False


def test_is_signed_returns_false_for_mutate_action():
    """Test is_signed() returns False for MUTATE action"""
    registry = ActionRegistry()

    action = Action(
        action_id="test_mutate",
        label="Test Mutate",
        variant=ActionVariant.MUTATE,
        domain="test"
    )

    registry.register(action)
    assert registry.is_signed("test_mutate") is False


def test_is_signed_returns_false_for_nonexistent_action():
    """Test is_signed() returns False for action that doesn't exist"""
    registry = ActionRegistry()
    assert registry.is_signed("nonexistent") is False


# =============================================================================
# Integration Tests
# =============================================================================

def test_signed_action_full_workflow():
    """Test complete SIGNED action registration and retrieval"""
    registry = ActionRegistry()

    # Register SIGNED action
    action = Action(
        action_id="archive_work_order",
        label="Archive",
        variant=ActionVariant.SIGNED,
        domain="work_orders",
        entity_types=["work_order"],
        allowed_roles=["captain", "chief_engineer", "manager"],
        ui=ActionUI(dropdown_only=True, icon="archive"),
        execution=ActionExecution(handler="archive_work_order"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Archive this work order? This cannot be undone."
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Archive work order (captain/HOD signature required)"
    )

    registry.register(action)

    # Retrieve and verify
    retrieved = registry.get_action("archive_work_order")
    assert retrieved is not None
    assert retrieved.variant == ActionVariant.SIGNED
    assert retrieved.allowed_roles == ["captain", "chief_engineer", "manager"]
    assert retrieved.mutation.requires_signature is True
    assert retrieved.ui.dropdown_only is True

    # Verify helper methods
    assert registry.is_signed("archive_work_order") is True
    assert registry.is_mutate("archive_work_order") is False
    assert registry.is_read("archive_work_order") is False

    # Verify to_dict() output
    result = registry.to_dict()
    action_dict = result["actions"]["archive_work_order"]
    assert action_dict["variant"] == "SIGNED"
    assert action_dict["allowed_roles"] == ["captain", "chief_engineer", "manager"]
    assert action_dict["requires_signature"] is True


def test_multiple_signed_actions_in_registry():
    """Test multiple SIGNED actions can coexist"""
    registry = ActionRegistry()

    actions = [
        Action(
            action_id="reassign_work_order",
            label="Reassign",
            variant=ActionVariant.SIGNED,
            domain="work_orders",
            allowed_roles=["captain", "chief_engineer"]
        ),
        Action(
            action_id="archive_work_order",
            label="Archive",
            variant=ActionVariant.SIGNED,
            domain="work_orders",
            allowed_roles=["captain"]
        ),
        Action(
            action_id="supersede_certificate",
            label="Supersede",
            variant=ActionVariant.SIGNED,
            domain="certificates",
            allowed_roles=["captain"]
        ),
    ]

    for action in actions:
        registry.register(action)

    # Verify all registered
    assert registry.is_signed("reassign_work_order") is True
    assert registry.is_signed("archive_work_order") is True
    assert registry.is_signed("supersede_certificate") is True

    # Verify validation passes
    errors = registry.validate()
    signed_errors = [e for e in errors if any(
        action_id in e for action_id in ["reassign_work_order", "archive_work_order", "supersede_certificate"]
    )]
    assert len(signed_errors) == 0


# =============================================================================
# Edge Cases
# =============================================================================

def test_signed_action_with_single_role():
    """Test SIGNED action with only one allowed role"""
    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.SIGNED,
        domain="test",
        allowed_roles=["captain"]  # Only one role
    )
    assert action.allowed_roles == ["captain"]


def test_signed_action_allowed_roles_preserved():
    """Test allowed_roles list is not mutated during registration"""
    original_roles = ["captain", "chief_engineer", "manager"]
    action = Action(
        action_id="test_signed",
        label="Test Signed",
        variant=ActionVariant.SIGNED,
        domain="test",
        allowed_roles=original_roles.copy()
    )

    # Verify roles preserved
    assert action.allowed_roles == original_roles

    # Modify original list
    original_roles.append("crew")

    # Action's list should be unchanged
    assert "crew" not in action.allowed_roles


def test_read_and_mutate_actions_unaffected():
    """Test READ and MUTATE actions still work as before"""
    # READ action
    read_action = Action(
        action_id="view_item",
        label="View",
        variant=ActionVariant.READ,
        domain="test"
    )
    assert read_action.allowed_roles == []
    assert read_action.mutation is None

    # MUTATE action
    mutate_action = Action(
        action_id="update_item",
        label="Update",
        variant=ActionVariant.MUTATE,
        domain="test"
    )
    assert mutate_action.allowed_roles == []
    assert mutate_action.mutation is not None
    assert mutate_action.mutation.requires_signature is True

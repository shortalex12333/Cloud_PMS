"""
Base Microaction Infrastructure
================================

Base classes and schemas for lens-specific action suggestions.

Each lens creates a subclass that:
1. Defines which entity types it handles
2. Implements action suggestion logic
3. Filters actions by entity state and user role
4. Provides prefill data for actions

Auto-discovered by MicroactionRegistry at startup.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


# =============================================================================
# PYDANTIC MODELS - Type-safe action suggestions
# =============================================================================

class ActionVariant(str, Enum):
    """Action variant types (from action router)."""
    READ = "READ"        # View-only actions (no data changes)
    MUTATE = "MUTATE"    # Data-changing actions (normal permissions)
    SIGNED = "SIGNED"    # Data-changing actions requiring signature (Captain/Manager only)


class ActionSuggestion(BaseModel):
    """
    Single action suggestion for an entity.

    Example:
        ActionSuggestion(
            action_id="receive_part",
            label="Receive Part",
            variant="MUTATE",
            entity_id="uuid-1234",
            entity_type="part",
            prefill_data={
                "part_id": "uuid-1234",
                "part_name": "Engine Oil Filter",
                "current_stock": 10
            },
            priority=3
        )
    """
    action_id: str = Field(
        ...,
        description="Action identifier from action router (e.g., 'receive_part')",
        min_length=1
    )
    label: str = Field(
        ...,
        description="Human-readable action label (e.g., 'Receive Part')",
        min_length=1
    )
    variant: ActionVariant = Field(
        ...,
        description="Action variant (READ, MUTATE, SIGNED)"
    )
    entity_id: str = Field(
        ...,
        description="UUID of the entity this action applies to"
    )
    entity_type: str = Field(
        ...,
        description="Type of entity (e.g., 'part', 'certificate')"
    )
    prefill_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pre-filled form data for this action"
    )
    priority: int = Field(
        default=1,
        description="Priority for ordering (1=low, 5=high). Higher priority shown first.",
        ge=1,
        le=5
    )
    requires_confirmation: bool = Field(
        default=False,
        description="Whether this action requires user confirmation"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "action_id": self.action_id,
            "label": self.label,
            "variant": self.variant.value,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "prefill_data": self.prefill_data,
            "priority": self.priority,
            "requires_confirmation": self.requires_confirmation
        }


# =============================================================================
# BASE MICROACTION CLASS
# =============================================================================

class BaseLensMicroactions(ABC):
    """
    Abstract base class for lens-specific microaction logic.

    Each lens creates one microaction class that:
    - Defines which entity types it handles
    - Implements action suggestion logic
    - Filters actions by entity state and user role
    - Provides prefill data for actions

    Example:
        class PartLensMicroactions(BaseLensMicroactions):
            lens_name = "part_lens"
            entity_types = ["part", "inventory_stock", "shopping_list_item"]

            async def get_suggestions(
                self,
                entity_type,
                entity_id,
                entity_data,
                user_role,
                yacht_id,
                query_intent=None
            ):
                # Get all part actions for user role
                all_actions = get_actions_for_domain("parts", user_role)

                # Fetch current stock state
                stock_info = await self._get_stock_info(entity_id, yacht_id)

                # Filter actions based on stock state
                suggestions = []
                for action in all_actions:
                    if stock_info["on_hand"] == 0 and action.action_id in ["consume_part"]:
                        continue  # Can't consume if no stock

                    suggestions.append(ActionSuggestion(
                        action_id=action.action_id,
                        label=action.label,
                        variant=action.variant,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        prefill_data=await self._get_prefill(action.action_id, entity_id),
                        priority=3 if action.action_id == query_intent else 1
                    ))

                return suggestions
    """

    @property
    @abstractmethod
    def lens_name(self) -> str:
        """
        Lens identifier (e.g., 'part_lens', 'certificate_lens').

        Must match the lens_name in corresponding capability class.
        """
        pass

    @property
    @abstractmethod
    def entity_types(self) -> List[str]:
        """
        Entity types this lens handles.

        Example:
            ["part", "inventory_stock", "shopping_list_item"]

        These should match result types from capability searches.
        """
        pass

    @abstractmethod
    async def get_suggestions(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str] = None
    ) -> List[ActionSuggestion]:
        """
        Get context-valid actions for an entity.

        This method:
        1. Fetches all actions for this domain and user role
        2. Filters actions based on entity state (e.g., stock level, expiry)
        3. Filters actions based on user role (e.g., SIGNED actions for Captain only)
        4. Prioritizes actions based on query intent
        5. Fetches prefill data for each action
        6. Returns sorted list of action suggestions

        Args:
            entity_type: Type of entity (e.g., "part", "certificate")
            entity_id: UUID of the entity
            entity_data: Full entity data from search result
            user_role: User's role ("crew", "chief_engineer", "captain", etc.)
            yacht_id: Tenant isolation UUID
            query_intent: Optional intent from query (e.g., "receive_part")

        Returns:
            List of ActionSuggestion objects, sorted by priority

        Example Implementation:
            async def get_suggestions(self, ...):
                # Get all actions for domain
                from apps.api.action_router.registry import get_actions_for_domain
                all_actions = get_actions_for_domain("parts", user_role)

                # Fetch entity state
                stock_info = await self._get_stock_info(entity_id, yacht_id)

                # Filter and build suggestions
                suggestions = []
                for action in all_actions:
                    # State-based filtering
                    if stock_info["on_hand"] == 0 and action.action_id == "consume_part":
                        continue

                    # Build suggestion
                    priority = 3 if action.action_id == query_intent else 1
                    prefill = await self._get_prefill_data(action.action_id, entity_id, yacht_id)

                    suggestions.append(ActionSuggestion(
                        action_id=action.action_id,
                        label=action.label,
                        variant=action.variant.value,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        prefill_data=prefill,
                        priority=priority
                    ))

                # Sort by priority
                suggestions.sort(key=lambda s: s.priority, reverse=True)
                return suggestions
        """
        pass


# =============================================================================
# EXCEPTIONS - Clear error reporting
# =============================================================================

class MicroactionError(Exception):
    """Base exception for microaction errors."""
    pass


class MicroactionExecutionError(MicroactionError):
    """Raised when microaction execution fails."""
    def __init__(
        self,
        lens_name: str,
        entity_type: str,
        entity_id: str,
        error: Exception
    ):
        self.lens_name = lens_name
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.original_error = error

        super().__init__(
            f"{lens_name}: Failed to get suggestions for {entity_type} ({entity_id})\n"
            f"  Error: {str(error)}\n"
            f"  Fix: Check microaction implementation"
        )

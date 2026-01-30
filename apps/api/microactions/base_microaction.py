"""
Base Microaction Framework
===========================
Provides base classes for lens-specific action suggestions.

Components:
- ActionSuggestion: Pydantic model for action data
- BaseLensMicroactions: Abstract base for action generation
- ActionVariant: Enum for action types (READ, MUTATE, SIGNED)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from supabase import Client


class ActionVariant(str, Enum):
    """
    Action execution types.

    READ: View/display action (no data modification)
    MUTATE: Standard write action (crew/engineer permission)
    SIGNED: Restricted action requiring captain/manager permission
    """
    READ = "READ"
    MUTATE = "MUTATE"
    SIGNED = "SIGNED"


class ActionSuggestion(BaseModel):
    """
    Standardized action suggestion format.

    Represents a suggested action the user can take on an entity.
    """
    action_id: str = Field(..., description="Unique action identifier")
    label: str = Field(..., description="Human-readable action label")
    variant: ActionVariant = Field(..., description="Action type (READ/MUTATE/SIGNED)")
    entity_id: str = Field(..., description="Entity this action applies to")
    entity_type: str = Field(..., description="Type of entity (part, crew, etc.)")
    prefill_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pre-populated form data"
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Action priority (1=low, 5=high)"
    )

    class Config:
        use_enum_values = True


class MicroactionExecutionError(Exception):
    """
    Raised when microaction generation fails.
    """
    def __init__(
        self,
        lens_name: str,
        entity_type: str,
        entity_id: str,
        original_error: Exception
    ):
        self.lens_name = lens_name
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.original_error = original_error

        super().__init__(
            f"[{lens_name}] Microaction generation failed for {entity_type}/{entity_id}: "
            f"{type(original_error).__name__}: {original_error}"
        )


class BaseLensMicroactions(ABC):
    """
    Abstract base class for lens-specific microactions.

    Each lens implements action suggestion logic with:
    1. Stock-based filtering (hide actions if stock is 0)
    2. Role-based filtering (hide SIGNED actions from crew)
    3. Intent-based prioritization (boost priority if query intent matches action)
    4. Prefill data generation (pre-populate form fields)

    Usage:
        class PartLensMicroactions(BaseLensMicroactions):
            lens_name = "part_lens"
            entity_types = ["part", "inventory_stock"]

            async def get_suggestions(self, entity_type, entity_id, ...):
                # Implementation...
    """

    def __init__(self, db: Client):
        """
        Initialize microactions with Supabase client.

        Args:
            db: Supabase client instance
        """
        self.db = db

    @property
    @abstractmethod
    def lens_name(self) -> str:
        """
        Unique identifier for this lens (must match capabilities lens_name).
        """
        pass

    @property
    @abstractmethod
    def entity_types(self) -> List[str]:
        """
        List of entity types this lens provides actions for.
        (e.g., ["part", "inventory_stock", "shopping_list_item"])
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
        Generate action suggestions for an entity.

        Args:
            entity_type: Type of entity (e.g., "part")
            entity_id: Entity ID
            entity_data: Entity data from search result
            user_role: User's role (for role-based filtering)
            yacht_id: Yacht ID
            query_intent: Optional query intent for prioritization

        Returns:
            List of ActionSuggestion objects

        Raises:
            MicroactionExecutionError: If action generation fails
        """
        pass

    def validate(self) -> bool:
        """
        Validate microaction configuration.
        Called by registry during discovery.

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Check lens_name is set
        if not self.lens_name or not isinstance(self.lens_name, str):
            raise ValueError(f"Invalid lens_name: {self.lens_name}")

        # Check entity_types is defined
        if not self.entity_types or not isinstance(self.entity_types, list):
            raise ValueError(f"No entity_types defined for {self.lens_name}")

        return True

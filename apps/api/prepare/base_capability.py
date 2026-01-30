"""
Base Capability Infrastructure
===============================

Base classes and schemas for lens search capabilities.

Each lens creates a subclass of BaseLensCapability that:
1. Defines entity-to-capability mappings
2. Implements search query methods
3. Validates at startup

Auto-discovered by CapabilityRegistry at startup.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


# =============================================================================
# PYDANTIC MODELS - Type-safe configuration
# =============================================================================

class CapabilityMapping(BaseModel):
    """
    Single entity-to-capability mapping.

    Example:
        CapabilityMapping(
            entity_type="PART_NUMBER",
            capability_name="part_by_part_number_or_name",
            table_name="pms_parts",
            search_column="part_number",
            result_type="part",
            priority=3
        )
    """
    entity_type: str = Field(
        ...,
        description="Entity type from extraction (e.g., 'PART_NUMBER', 'CERTIFICATE_TYPE')",
        min_length=1
    )
    capability_name: str = Field(
        ...,
        description="Method name in lens capability class (e.g., 'part_by_part_number_or_name')",
        min_length=1
    )
    table_name: str = Field(
        ...,
        description="Database table queried (e.g., 'pms_parts')",
        min_length=1
    )
    search_column: str = Field(
        ...,
        description="Column to search (e.g., 'part_number', 'name')",
        min_length=1
    )
    result_type: str = Field(
        ...,
        description="Type of result returned (e.g., 'part', 'certificate')",
        min_length=1
    )
    priority: int = Field(
        default=1,
        description="Priority for ranking (1=low, 3=high). Higher priority results shown first.",
        ge=1,
        le=5
    )

    @validator('entity_type')
    def entity_type_uppercase(cls, v):
        """Entity types should be UPPERCASE for consistency."""
        if not v.isupper():
            raise ValueError(f"Entity type must be UPPERCASE: '{v}'")
        return v

    @validator('capability_name')
    def capability_name_snake_case(cls, v):
        """Capability names should be snake_case."""
        if not v.islower() and '_' in v:
            raise ValueError(f"Capability name must be snake_case: '{v}'")
        return v


class SearchResult(BaseModel):
    """
    Standardized search result from any capability.

    All lens capabilities return results in this format for consistency.
    """
    id: str = Field(..., description="UUID of the record")
    type: str = Field(..., description="Result type (e.g., 'part', 'certificate')")
    title: str = Field(..., description="Human-readable title")
    score: float = Field(default=0.0, description="Relevance score (0.0-1.0)", ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional result data")
    lens_name: str = Field(..., description="Which lens produced this result")
    source_table: str = Field(..., description="Database table this result came from")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "score": self.score,
            "metadata": self.metadata,
            "lens_name": self.lens_name,
            "source_table": self.source_table
        }


# =============================================================================
# BASE CAPABILITY CLASS
# =============================================================================

class BaseLensCapability(ABC):
    """
    Abstract base class for all lens capabilities.

    Each lens creates one capability class that:
    - Defines entity-to-capability mappings
    - Implements search methods for its entities
    - Validates configuration at startup

    Example:
        class PartLensCapability(BaseLensCapability):
            lens_name = "part_lens"
            enabled = True

            def get_entity_mappings(self) -> List[CapabilityMapping]:
                return [
                    CapabilityMapping(
                        entity_type="PART_NUMBER",
                        capability_name="part_by_part_number_or_name",
                        table_name="pms_parts",
                        search_column="part_number",
                        result_type="part",
                        priority=3
                    ),
                    ...
                ]

            async def execute_capability(self, capability_name, yacht_id, search_term, limit):
                method = getattr(self, capability_name)
                results = await method(yacht_id, search_term, limit)
                return [SearchResult(**r) for r in results]

            async def part_by_part_number_or_name(self, yacht_id, search_term, limit):
                # SQL query implementation
                ...
    """

    @property
    @abstractmethod
    def lens_name(self) -> str:
        """
        Lens identifier (e.g., 'part_lens', 'certificate_lens').

        Used for:
        - Registry identification
        - Error tracing
        - Result attribution
        """
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """
        Whether this lens is enabled.

        Set to False to disable a lens without deleting the file.
        Disabled lenses are skipped during auto-discovery.
        """
        return True

    @abstractmethod
    def get_entity_mappings(self) -> List[CapabilityMapping]:
        """
        Return all entity-to-capability mappings for this lens.

        Each mapping defines:
        - Which entity type triggers which capability
        - Which table and column to search
        - Result priority for ranking

        Returns:
            List of CapabilityMapping objects

        Example:
            [
                CapabilityMapping(
                    entity_type="PART_NUMBER",
                    capability_name="part_by_part_number_or_name",
                    table_name="pms_parts",
                    search_column="part_number",
                    result_type="part",
                    priority=3
                ),
                ...
            ]
        """
        pass

    @abstractmethod
    async def execute_capability(
        self,
        capability_name: str,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Execute a capability and return standardized results.

        This method:
        1. Routes to the correct capability method (e.g., part_by_part_number_or_name)
        2. Executes the SQL query
        3. Wraps results in SearchResult models
        4. Returns standardized format

        Args:
            capability_name: Name of the capability method to call
            yacht_id: Tenant isolation UUID
            search_term: User's search query
            limit: Maximum results to return

        Returns:
            List of SearchResult objects

        Raises:
            ValueError: If capability_name doesn't exist
            RuntimeError: If query execution fails
        """
        pass

    def validate(self) -> None:
        """
        Validate lens configuration at startup.

        Checks:
        1. No duplicate entity types within lens
        2. All capability methods are implemented
        3. All mappings have valid Pydantic schemas

        Called by CapabilityRegistry during auto-discovery.

        Raises:
            ValueError: If validation fails
        """
        mappings = self.get_entity_mappings()

        # Check for duplicate entity types
        entity_types = [m.entity_type for m in mappings]
        if len(entity_types) != len(set(entity_types)):
            duplicates = [e for e in entity_types if entity_types.count(e) > 1]
            raise ValueError(
                f"{self.lens_name}: Duplicate entity types found: {set(duplicates)}"
            )

        # Check all capabilities are implemented
        for mapping in mappings:
            if not hasattr(self, mapping.capability_name):
                raise ValueError(
                    f"{self.lens_name}: Capability '{mapping.capability_name}' "
                    f"not implemented for entity '{mapping.entity_type}'. "
                    f"Add method: async def {mapping.capability_name}(self, yacht_id, search_term, limit) -> List[Dict]"
                )

        # Validate Pydantic models (will raise if invalid)
        for mapping in mappings:
            try:
                mapping.dict()  # Test serialization
            except Exception as e:
                raise ValueError(
                    f"{self.lens_name}: Invalid mapping for entity '{mapping.entity_type}': {str(e)}"
                )


# =============================================================================
# EXCEPTIONS - Clear error reporting
# =============================================================================

class CapabilityError(Exception):
    """Base exception for capability errors."""
    pass


class CapabilityNotFoundError(CapabilityError):
    """Raised when a capability method doesn't exist."""
    def __init__(self, lens_name: str, capability_name: str):
        self.lens_name = lens_name
        self.capability_name = capability_name
        super().__init__(
            f"{lens_name}: Capability '{capability_name}' not found. "
            f"Check if method is implemented in capability class."
        )


class CapabilityExecutionError(CapabilityError):
    """Raised when a capability execution fails."""
    def __init__(
        self,
        lens_name: str,
        capability_name: str,
        table_name: str,
        column_name: str,
        error: Exception
    ):
        self.lens_name = lens_name
        self.capability_name = capability_name
        self.table_name = table_name
        self.column_name = column_name
        self.original_error = error

        super().__init__(
            f"{lens_name}: Capability '{capability_name}' failed\n"
            f"  Table: {table_name}\n"
            f"  Column: {column_name}\n"
            f"  Error: {str(error)}\n"
            f"  Fix: Check SQL query in capability method"
        )

"""
Base Capability Framework for Lens-Based Search
===============================================
Provides base classes for implementing lens-specific search capabilities.

Architecture:
- BaseLensCapability: Abstract base for all lens implementations
- CapabilityMapping: Pydantic model for entity → capability mappings
- SearchResult: Standardized result format
- CapabilityExecutionError: Typed exceptions with lens context
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from supabase import Client


class CapabilityMapping(BaseModel):
    """
    Maps entity types to search capabilities.

    Example:
        PART_NUMBER → part_by_part_number (searches pms_parts table)
    """
    entity_type: str = Field(..., description="Entity type (e.g., PART_NUMBER, CREW_NAME)")
    capability_name: str = Field(..., description="Method name to execute (e.g., part_by_part_number)")
    table_name: str = Field(..., description="Primary table to query")
    search_column: str = Field(..., description="Column to search in")
    result_type: str = Field(..., description="Type of result (e.g., 'part', 'crew')")
    priority: int = Field(default=1, ge=1, le=5, description="Search priority (1=low, 5=high)")

    @validator('capability_name')
    def validate_capability_name(cls, v):
        """Ensure capability name is a valid Python identifier."""
        if not v.isidentifier():
            raise ValueError(f"Invalid capability name: {v}")
        return v

    @validator('entity_type')
    def validate_entity_type(cls, v):
        """Ensure entity type is uppercase."""
        return v.upper()


class SearchResult(BaseModel):
    """
    Standardized search result format for all lenses.
    """
    id: str = Field(..., description="Entity ID")
    result_type: str = Field(..., description="Type of result (part, crew, certificate, etc.)")
    title: str = Field(..., description="Primary display text")
    subtitle: Optional[str] = Field(None, description="Secondary display text")
    score: int = Field(default=1, ge=0, le=100, description="Relevance score")
    source_table: str = Field(..., description="Source table name")
    source_capability: str = Field(..., description="Capability that generated this result")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional entity data")

    class Config:
        frozen = False


class CapabilityExecutionError(Exception):
    """
    Raised when a capability fails to execute.
    Includes lens and table context for debugging.
    """
    def __init__(
        self,
        lens_name: str,
        capability_name: str,
        table_name: str,
        original_error: Exception
    ):
        self.lens_name = lens_name
        self.capability_name = capability_name
        self.table_name = table_name
        self.original_error = original_error

        super().__init__(
            f"[{lens_name}] Capability '{capability_name}' failed on table '{table_name}': "
            f"{type(original_error).__name__}: {original_error}"
        )


class BaseLensCapability(ABC):
    """
    Abstract base class for all lens capabilities.

    Each lens (Part, Crew, Certificate, Work Order) extends this class
    and implements:
    1. lens_name property
    2. get_entity_mappings() method
    3. Individual capability methods (e.g., part_by_part_number)
    4. execute_capability() method to route searches

    Usage:
        class PartLensCapability(BaseLensCapability):
            lens_name = "part_lens"

            def get_entity_mappings(self) -> List[CapabilityMapping]:
                return [
                    CapabilityMapping(
                        entity_type="PART_NUMBER",
                        capability_name="part_by_part_number",
                        table_name="pms_parts",
                        search_column="part_number",
                        result_type="part",
                        priority=3
                    )
                ]

            async def execute_capability(self, capability_name, yacht_id, search_term, limit):
                if capability_name == "part_by_part_number":
                    return await self.part_by_part_number(yacht_id, search_term, limit)

            async def part_by_part_number(self, yacht_id, search_term, limit):
                # Implementation...
    """

    def __init__(self, db: Client):
        """
        Initialize lens with Supabase client.

        Args:
            db: Supabase client instance
        """
        self.db = db

    @property
    @abstractmethod
    def lens_name(self) -> str:
        """
        Unique identifier for this lens (e.g., "part_lens", "crew_lens").
        Must match the filename pattern: {lens_name}_capabilities.py
        """
        pass

    @property
    def enabled(self) -> bool:
        """
        Whether this lens is enabled. Override to disable a lens.
        Default: True
        """
        return True

    @abstractmethod
    def get_entity_mappings(self) -> List[CapabilityMapping]:
        """
        Return entity type → capability mappings for this lens.

        Returns:
            List of CapabilityMapping objects defining search capabilities
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
        Execute a capability by name and return standardized results.

        Args:
            capability_name: Name of capability to execute (from CapabilityMapping)
            yacht_id: Yacht ID for RLS filtering
            search_term: Search query
            limit: Maximum results to return

        Returns:
            List of SearchResult objects

        Raises:
            CapabilityExecutionError: If capability execution fails
        """
        pass

    def validate(self) -> bool:
        """
        Validate lens configuration.
        Called by registry during discovery.

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Check lens_name is set
        if not self.lens_name or not isinstance(self.lens_name, str):
            raise ValueError(f"Invalid lens_name: {self.lens_name}")

        # Check entity mappings are defined
        mappings = self.get_entity_mappings()
        if not mappings:
            raise ValueError(f"No entity mappings defined for {self.lens_name}")

        # Check no duplicate entity types
        entity_types = [m.entity_type for m in mappings]
        if len(entity_types) != len(set(entity_types)):
            duplicates = [t for t in entity_types if entity_types.count(t) > 1]
            raise ValueError(f"Duplicate entity types: {duplicates}")

        return True

    def _format_results(
        self,
        raw_results: List[Dict[str, Any]],
        result_type: str,
        capability_name: str,
        table_name: str,
        title_fn: callable,
        subtitle_fn: callable = None,
        score_fn: callable = None
    ) -> List[SearchResult]:
        """
        Helper to convert raw database results to SearchResult objects.

        Args:
            raw_results: List of dicts from Supabase
            result_type: Type of result (e.g., 'part')
            capability_name: Name of capability that generated results
            table_name: Source table name
            title_fn: Function to extract title from row
            subtitle_fn: Optional function to extract subtitle
            score_fn: Optional function to calculate score

        Returns:
            List of SearchResult objects
        """
        results = []
        for row in raw_results:
            results.append(SearchResult(
                id=row["id"],
                result_type=result_type,
                title=title_fn(row),
                subtitle=subtitle_fn(row) if subtitle_fn else None,
                score=score_fn(row) if score_fn else 1,
                source_table=table_name,
                source_capability=capability_name,
                metadata=row
            ))
        return results

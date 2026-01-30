"""
Base Capability Framework for Lens-Based Search
===============================================
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from supabase import Client


class CapabilityMapping(BaseModel):
    entity_type: str
    capability_name: str
    table_name: str
    search_column: str
    result_type: str
    priority: int = Field(default=1, ge=1, le=5)

    @field_validator('entity_type')
    @classmethod
    def validate_entity_type(cls, v):
        return v.upper()


class SearchResult(BaseModel):
    id: str
    result_type: str
    title: str
    subtitle: Optional[str] = None
    score: int = Field(default=1, ge=0, le=100)
    source_table: str
    source_capability: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CapabilityExecutionError(Exception):
    pass


class BaseLensCapability(ABC):
    def __init__(self, db: Client):
        self.db = db

    @property
    @abstractmethod
    def lens_name(self) -> str:
        pass

    @property
    def enabled(self) -> bool:
        return True

    @abstractmethod
    def get_entity_mappings(self) -> List[CapabilityMapping]:
        pass

    @abstractmethod
    async def execute_capability(
        self, capability_name: str, yacht_id: str, search_term: str, limit: int = 20
    ) -> List[SearchResult]:
        pass

    def validate(self) -> bool:
        if not self.lens_name:
            raise ValueError(f"Invalid lens_name: {self.lens_name}")
        mappings = self.get_entity_mappings()
        if not mappings:
            raise ValueError(f"No entity mappings for {self.lens_name}")
        return True

    def _format_results(
        self, raw_results: List[Dict], result_type: str, capability_name: str,
        table_name: str, title_fn: callable, subtitle_fn: callable = None, score_fn: callable = None
    ) -> List[SearchResult]:
        results = []
        for row in raw_results:
            results.append(SearchResult(
                id=row["id"], result_type=result_type, title=title_fn(row),
                subtitle=subtitle_fn(row) if subtitle_fn else None,
                score=score_fn(row) if score_fn else 1,
                source_table=table_name, source_capability=capability_name, metadata=row
            ))
        return results

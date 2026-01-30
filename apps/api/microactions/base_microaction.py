"""Base Microaction Framework"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from supabase import Client


class ActionVariant(str, Enum):
    READ = "READ"
    MUTATE = "MUTATE"
    SIGNED = "SIGNED"


class ActionSuggestion(BaseModel):
    action_id: str
    label: str
    variant: ActionVariant
    entity_id: str
    entity_type: str
    prefill_data: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, ge=1, le=5)

    class Config:
        use_enum_values = True


class BaseLensMicroactions(ABC):
    def __init__(self, db: Client):
        self.db = db

    @property
    @abstractmethod
    def lens_name(self) -> str:
        pass

    @property
    @abstractmethod
    def entity_types(self) -> List[str]:
        pass

    @abstractmethod
    async def get_suggestions(self, entity_type: str, entity_id: str, entity_data: Dict[str, Any],
                              user_role: str, yacht_id: str, query_intent: Optional[str] = None) -> List[ActionSuggestion]:
        pass

    def validate(self) -> bool:
        if not self.lens_name:
            raise ValueError(f"Invalid lens_name: {self.lens_name}")
        if not self.entity_types:
            raise ValueError(f"No entity_types for {self.lens_name}")
        return True

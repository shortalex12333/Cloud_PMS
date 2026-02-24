"""
CelesteOS - Field Metadata Schema
==================================

Defines the metadata structure for auto-populating fields from NLP-extracted entities.

This module extends the existing FieldMetadata from action_router.registry with additional
properties for the prefill engine.

Field classification:
- REQUIRED: Must be provided by user
- OPTIONAL: May be provided by user
- BACKEND_AUTO: Computed by backend (prefill engine)
- CONTEXT: From auth/session context (yacht_id, user_id)

Auto-population sources:
- equipment: Extract from EQUIPMENT_NAME entity
- symptom: Extract from SYMPTOM entity
- query_text: Use raw query text
- part: Extract from PART_NAME or PART_NUMBER entity
- stock_calculation: Compute from inventory levels

Templates:
- compose_template: Template string for composing values from multiple entities
  Example: "{equipment} - {symptom}" or "{part_name} ({part_number})"

Lookup:
- lookup_required: Whether to resolve entity name to UUID via DB lookup
- Returns single UUID if 1 match, List[Dict] with dropdown options if 2+, None if 0

Value mapping:
- value_map: Dict for translating extracted values to canonical form
  Example: {"urgent": "critical", "asap": "critical", "low": "low"}

Default values:
- default: Default value if entity not extracted
  Example: "medium" for priority field
"""

from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass, field as dataclass_field


# Field classification (matches action_router.registry.FieldClassification)
FieldClassification = Literal["REQUIRED", "OPTIONAL", "BACKEND_AUTO", "CONTEXT"]


@dataclass
class FieldMetadata:
    """
    Enhanced field metadata for auto-population from NLP entities.

    Attributes:
        name: Field name in the mutation payload
        classification: Field classification (REQUIRED, OPTIONAL, BACKEND_AUTO, CONTEXT)
        auto_populate_from: Entity type to extract from NLP results
            - "equipment": EQUIPMENT_NAME entity
            - "symptom": SYMPTOM entity
            - "query_text": Raw query text
            - "part": PART_NAME or PART_NUMBER entity
            - "fault": FAULT_CODE entity
            - "work_order": WORK_ORDER_ID entity
            - "stock_calculation": Compute from inventory levels
        compose_template: Template string for composing values from multiple entities
            - Use {entity_type} placeholders
            - Example: "{equipment} - {symptom}"
        lookup_required: Whether to resolve entity name to UUID via DB lookup
            - True: Query DB and return UUID or dropdown options
            - False: Use raw entity value
        value_map: Dict for translating extracted values to canonical form
            - Example: {"urgent": "critical", "asap": "critical"}
        default: Default value if entity not extracted or lookup fails
        description: Human-readable description for UI hints
        options: Valid options for enum fields (static dropdown)
        validator: Optional validation function name (for custom validation)
    """
    name: str
    classification: FieldClassification
    auto_populate_from: Optional[str] = None
    compose_template: Optional[str] = None
    lookup_required: bool = False
    value_map: Optional[Dict[str, str]] = None
    default: Optional[Any] = None
    description: Optional[str] = None
    options: Optional[List[str]] = None
    validator: Optional[str] = None

    def __post_init__(self):
        """Validate field metadata consistency."""
        # If lookup_required is True, auto_populate_from should be specified
        if self.lookup_required and not self.auto_populate_from:
            raise ValueError(
                f"Field '{self.name}': lookup_required=True requires auto_populate_from"
            )

        # If compose_template is provided, auto_populate_from should be specified
        if self.compose_template and not self.auto_populate_from:
            raise ValueError(
                f"Field '{self.name}': compose_template requires auto_populate_from"
            )

        # BACKEND_AUTO fields should have auto_populate_from or default
        if self.classification == "BACKEND_AUTO" and not (
            self.auto_populate_from or self.default is not None
        ):
            raise ValueError(
                f"Field '{self.name}': BACKEND_AUTO requires auto_populate_from or default"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "classification": self.classification,
            "auto_populate_from": self.auto_populate_from,
            "compose_template": self.compose_template,
            "lookup_required": self.lookup_required,
            "value_map": self.value_map,
            "default": self.default,
            "description": self.description,
            "options": self.options,
            "validator": self.validator,
        }


@dataclass
class LookupResult:
    """
    Result of a yacht-scoped entity lookup.

    Attributes:
        success: Whether lookup succeeded
        value: UUID if single match, None if no match
        options: List of options if multiple matches (for dropdown)
        count: Number of matches found
        error: Error message if lookup failed
    """
    success: bool
    value: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "value": self.value,
            "options": self.options,
            "count": self.count,
            "error": self.error,
        }


# Entity type constants for auto_populate_from
ENTITY_EQUIPMENT = "equipment"
ENTITY_SYMPTOM = "symptom"
ENTITY_QUERY_TEXT = "query_text"
ENTITY_PART = "part"
ENTITY_FAULT = "fault"
ENTITY_WORK_ORDER = "work_order"
ENTITY_STOCK_CALCULATION = "stock_calculation"

# Valid entity types for validation
VALID_ENTITY_TYPES = {
    ENTITY_EQUIPMENT,
    ENTITY_SYMPTOM,
    ENTITY_QUERY_TEXT,
    ENTITY_PART,
    ENTITY_FAULT,
    ENTITY_WORK_ORDER,
    ENTITY_STOCK_CALCULATION,
}


__all__ = [
    "FieldMetadata",
    "FieldClassification",
    "LookupResult",
    "ENTITY_EQUIPMENT",
    "ENTITY_SYMPTOM",
    "ENTITY_QUERY_TEXT",
    "ENTITY_PART",
    "ENTITY_FAULT",
    "ENTITY_WORK_ORDER",
    "ENTITY_STOCK_CALCULATION",
    "VALID_ENTITY_TYPES",
]

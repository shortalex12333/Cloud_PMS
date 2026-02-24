"""
CelesteOS - Common Utilities
=============================

Shared utilities for auto-population, lookups, and mutation previews.

This package provides:
- field_metadata: Schema for field auto-population rules
- lookup_functions: Yacht-scoped entity lookups (equipment, parts, faults)
- prefill_engine: Core mutation preview builder

Usage:
    from common.field_metadata import FieldMetadata
    from common.prefill_engine import build_mutation_preview
    from common.lookup_functions import lookup_entity
"""

from common.field_metadata import (
    FieldMetadata,
    FieldClassification,
    LookupResult,
    ENTITY_EQUIPMENT,
    ENTITY_SYMPTOM,
    ENTITY_QUERY_TEXT,
    ENTITY_PART,
    ENTITY_FAULT,
    ENTITY_WORK_ORDER,
    ENTITY_STOCK_CALCULATION,
)

from common.prefill_engine import (
    build_mutation_preview,
    validate_mutation_preview,
    extract_entity_value,
    apply_compose_template,
    apply_value_map,
)

from common.lookup_functions import (
    lookup_equipment_by_name,
    lookup_equipment_by_id,
    lookup_fault_by_symptom,
    lookup_fault_by_code,
    lookup_part_by_name,
    lookup_part_by_number,
    lookup_work_order_by_number,
    lookup_entity,
)

__all__ = [
    # field_metadata
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
    # prefill_engine
    "build_mutation_preview",
    "validate_mutation_preview",
    "extract_entity_value",
    "apply_compose_template",
    "apply_value_map",
    # lookup_functions
    "lookup_equipment_by_name",
    "lookup_equipment_by_id",
    "lookup_fault_by_symptom",
    "lookup_fault_by_code",
    "lookup_part_by_name",
    "lookup_part_by_number",
    "lookup_work_order_by_number",
    "lookup_entity",
]

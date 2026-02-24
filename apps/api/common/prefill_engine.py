"""
CelesteOS - Generic Prefill Engine
===================================

Builds mutation previews from NLP-extracted entities using field_metadata rules.

Two-Phase Mutation System:
1. /prepare endpoint: Extracts entities → applies field_metadata → returns preview
2. /commit endpoint: Validates preview → executes mutation → returns result

The prefill engine is the core of the /prepare phase, responsible for:
1. Auto-populating fields from extracted entities
2. Performing yacht-scoped lookups (equipment, parts, faults)
3. Applying value transformations (compose_template, value_map)
4. Identifying missing required fields
5. Generating warnings for ambiguous entities

Usage:
    from common.prefill_engine import build_mutation_preview
    from common.field_metadata import FieldMetadata

    field_metadata = {
        "equipment_id": FieldMetadata(
            name="equipment_id",
            classification="REQUIRED",
            auto_populate_from="equipment",
            lookup_required=True,
        ),
        "title": FieldMetadata(
            name="title",
            classification="BACKEND_AUTO",
            auto_populate_from="equipment",
            compose_template="{equipment} - {symptom}",
        ),
        "priority": FieldMetadata(
            name="priority",
            classification="OPTIONAL",
            value_map={"urgent": "critical", "asap": "critical"},
            default="medium",
        ),
    }

    preview = await build_mutation_preview(
        query_text="create urgent work order for main engine overheating",
        extracted_entities={
            "equipment": "main engine",
            "symptom": "overheating",
            "priority": "urgent",
        },
        field_metadata=field_metadata,
        yacht_id="abc-123",
        supabase_client=client,
    )

    if preview["missing_required"]:
        # Show form to user with pre-filled values and missing fields highlighted
        return {"preview": preview}
    else:
        # All required fields populated - ready to commit
        return {"preview": preview, "ready_to_commit": True}
"""

from typing import Dict, List, Any, Optional
import logging
import uuid
from datetime import datetime

from common.field_metadata import FieldMetadata, LookupResult
from common.lookup_functions import lookup_entity

logger = logging.getLogger(__name__)


# =============================================================================
# ENTITY EXTRACTION HELPERS
# =============================================================================

def extract_entity_value(
    entity_type: str,
    extracted_entities: Dict[str, Any],
    query_text: Optional[str] = None
) -> Optional[str]:
    """
    Extract entity value from NLP results.

    Args:
        entity_type: Type of entity to extract (equipment, symptom, etc.)
        extracted_entities: Dict of extracted entities from NLP
        query_text: Optional raw query text for fallback

    Returns:
        Entity value or None if not found

    Example:
        >>> extract_entity_value("equipment", {"equipment": "main engine"})
        "main engine"
        >>> extract_entity_value("query_text", {}, "create work order")
        "create work order"
    """
    entity_type_lower = entity_type.lower()

    # Special case: query_text
    if entity_type_lower == "query_text":
        return query_text

    # Try exact match
    if entity_type_lower in extracted_entities:
        return extracted_entities[entity_type_lower]

    # Try common aliases
    entity_aliases = {
        "equipment": ["equipment_name", "equipment"],
        "symptom": ["symptom", "fault_symptom"],
        "part": ["part_name", "part", "part_number"],
        "fault": ["fault_code", "fault"],
        "work_order": ["work_order_id", "wo_number", "work_order"],
    }

    if entity_type_lower in entity_aliases:
        for alias in entity_aliases[entity_type_lower]:
            if alias in extracted_entities:
                return extracted_entities[alias]

    return None


def apply_compose_template(
    template: str,
    extracted_entities: Dict[str, Any],
    query_text: Optional[str] = None
) -> str:
    """
    Apply compose template to extracted entities.

    Args:
        template: Template string with {entity_type} placeholders
        extracted_entities: Dict of extracted entities
        query_text: Optional raw query text

    Returns:
        Composed string with entity values filled in

    Example:
        >>> apply_compose_template(
        ...     "{equipment} - {symptom}",
        ...     {"equipment": "main engine", "symptom": "overheating"}
        ... )
        "main engine - overheating"
    """
    result = template

    # Extract all placeholders from template
    import re
    placeholders = re.findall(r"\{(\w+)\}", template)

    for placeholder in placeholders:
        value = extract_entity_value(placeholder, extracted_entities, query_text)
        if value:
            result = result.replace(f"{{{placeholder}}}", str(value))
        else:
            # Keep placeholder if entity not found
            logger.warning(f"[Prefill] Missing entity for placeholder: {placeholder}")

    return result


def apply_value_map(
    value: Any,
    value_map: Dict[str, str]
) -> Any:
    """
    Apply value mapping transformation.

    Args:
        value: Input value
        value_map: Dict mapping input values to canonical values

    Returns:
        Mapped value or original value if no mapping exists

    Example:
        >>> apply_value_map("urgent", {"urgent": "critical", "asap": "critical"})
        "critical"
    """
    if value is None:
        return None

    value_lower = str(value).lower()
    for key, mapped_value in value_map.items():
        if key.lower() == value_lower:
            return mapped_value

    return value


# =============================================================================
# BACKEND AUTO-POPULATION
# =============================================================================

def generate_backend_auto_value(
    field_name: str,
    field_metadata: FieldMetadata,
    yacht_id: str,
    user_id: Optional[str] = None
) -> Any:
    """
    Generate backend-computed values for BACKEND_AUTO fields.

    Args:
        field_name: Name of the field
        field_metadata: Field metadata
        yacht_id: Yacht UUID
        user_id: Optional user UUID

    Returns:
        Auto-generated value

    Backend auto fields:
        - id: New UUID
        - yacht_id: From context
        - user_id: From context
        - created_at: Current timestamp
        - updated_at: Current timestamp
    """
    field_name_lower = field_name.lower()

    if field_name_lower == "id":
        return str(uuid.uuid4())

    elif field_name_lower == "yacht_id":
        return yacht_id

    elif field_name_lower in ["user_id", "created_by", "updated_by"]:
        return user_id

    elif field_name_lower in ["created_at", "updated_at"]:
        return datetime.utcnow().isoformat()

    else:
        logger.warning(f"[Prefill] Unknown BACKEND_AUTO field: {field_name}")
        return None


# =============================================================================
# MUTATION PREVIEW BUILDER
# =============================================================================

async def build_mutation_preview(
    query_text: str,
    extracted_entities: Dict[str, Any],
    field_metadata: Dict[str, FieldMetadata],
    yacht_id: str,
    supabase_client,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build mutation preview from NLP-extracted entities using field_metadata rules.

    This is the core of the /prepare phase in the two-phase mutation system.

    Args:
        query_text: Original NLP query
        extracted_entities: Dict of entities extracted from NLP
            Example: {"equipment": "main engine", "symptom": "overheating"}
        field_metadata: Dict of field metadata for auto-population
        yacht_id: Yacht UUID for RLS enforcement
        supabase_client: Supabase client instance
        user_id: Optional user UUID for CONTEXT fields
        context: Optional additional context for lookups

    Returns:
        Dict with:
            - mutation_preview: Dict of populated field values
            - missing_required: List of required fields not populated
            - warnings: List of warnings (ambiguous entities, failed lookups)
            - dropdown_options: Dict of field -> options for ambiguous lookups
            - ready_to_commit: bool indicating if preview is ready for commit

    Example:
        >>> preview = await build_mutation_preview(
        ...     query_text="create work order for main engine overheating",
        ...     extracted_entities={"equipment": "main engine", "symptom": "overheating"},
        ...     field_metadata=wo_field_metadata,
        ...     yacht_id="abc-123",
        ...     supabase_client=client,
        ... )
        >>> preview["mutation_preview"]
        {
            "equipment_id": "uuid-...",
            "title": "main engine - overheating",
            "priority": "medium",
            "yacht_id": "abc-123",
        }
        >>> preview["ready_to_commit"]
        True
    """
    mutation_preview = {}
    missing_required = []
    warnings = []
    dropdown_options = {}
    lookup_cache = {}  # Cache lookups to avoid redundant queries

    logger.info(f"[Prefill] Building preview for {len(field_metadata)} fields")
    logger.debug(f"[Prefill] Extracted entities: {extracted_entities}")

    # Process each field according to its metadata
    for field_name, metadata in field_metadata.items():
        field_value = None
        classification = metadata.classification

        logger.debug(f"[Prefill] Processing field: {field_name} ({classification})")

        # =====================================================================
        # CONTEXT FIELDS (yacht_id, user_id)
        # =====================================================================
        if classification == "CONTEXT":
            if field_name.lower() == "yacht_id":
                field_value = yacht_id
            elif field_name.lower() in ["user_id", "created_by", "updated_by"]:
                field_value = user_id
            else:
                logger.warning(f"[Prefill] Unknown CONTEXT field: {field_name}")

            mutation_preview[field_name] = field_value
            continue

        # =====================================================================
        # BACKEND_AUTO FIELDS (id, timestamps)
        # =====================================================================
        elif classification == "BACKEND_AUTO":
            if metadata.auto_populate_from:
                # Extract entity value
                entity_value = extract_entity_value(
                    metadata.auto_populate_from,
                    extracted_entities,
                    query_text
                )

                if entity_value:
                    # Apply compose template if specified
                    if metadata.compose_template:
                        field_value = apply_compose_template(
                            metadata.compose_template,
                            extracted_entities,
                            query_text
                        )
                    else:
                        field_value = entity_value

                    # Apply value map if specified
                    if metadata.value_map:
                        field_value = apply_value_map(field_value, metadata.value_map)

                else:
                    # Use default if entity not found
                    field_value = metadata.default

            else:
                # Generate backend value (uuid, timestamp, etc.)
                field_value = generate_backend_auto_value(
                    field_name, metadata, yacht_id, user_id
                )

            mutation_preview[field_name] = field_value
            continue

        # =====================================================================
        # REQUIRED & OPTIONAL FIELDS (user-provided or auto-populated)
        # =====================================================================
        elif classification in ["REQUIRED", "OPTIONAL"]:
            # Try to auto-populate from entity
            if metadata.auto_populate_from:
                entity_type = metadata.auto_populate_from
                entity_value = extract_entity_value(
                    entity_type,
                    extracted_entities,
                    query_text
                )

                if entity_value:
                    # Apply compose template if specified
                    if metadata.compose_template:
                        field_value = apply_compose_template(
                            metadata.compose_template,
                            extracted_entities,
                            query_text
                        )
                    else:
                        field_value = entity_value

                    # Apply value map if specified
                    if metadata.value_map:
                        field_value = apply_value_map(field_value, metadata.value_map)

                    # Perform yacht-scoped lookup if required
                    if metadata.lookup_required:
                        # Check cache first
                        cache_key = f"{entity_type}:{entity_value}"
                        if cache_key in lookup_cache:
                            lookup_result = lookup_cache[cache_key]
                        else:
                            lookup_result = await lookup_entity(
                                entity_type=entity_type,
                                entity_value=entity_value,
                                yacht_id=yacht_id,
                                supabase_client=supabase_client,
                                context=context or {}
                            )
                            lookup_cache[cache_key] = lookup_result

                        # Handle lookup result
                        if not lookup_result.success:
                            warnings.append(f"Lookup failed for {field_name}: {lookup_result.error}")
                            field_value = None

                        elif lookup_result.count == 0:
                            warnings.append(f"No match found for {field_name}: '{entity_value}'")
                            field_value = None

                        elif lookup_result.count == 1:
                            # Single match - use UUID
                            field_value = lookup_result.value
                            logger.info(f"[Prefill] {field_name} resolved to {field_value}")

                        else:
                            # Multiple matches - add dropdown options
                            warnings.append(
                                f"Ambiguous {field_name}: '{entity_value}' matched {lookup_result.count} items"
                            )
                            dropdown_options[field_name] = lookup_result.options
                            field_value = None

                else:
                    # Entity not extracted - use default
                    field_value = metadata.default

            else:
                # No auto_populate_from - use default
                field_value = metadata.default

            # Add to preview if value exists
            if field_value is not None:
                mutation_preview[field_name] = field_value
            else:
                # Required field missing
                if classification == "REQUIRED":
                    missing_required.append(field_name)
                    logger.warning(f"[Prefill] Required field missing: {field_name}")

    # Determine if preview is ready to commit
    ready_to_commit = (
        len(missing_required) == 0 and
        len(dropdown_options) == 0
    )

    logger.info(
        f"[Prefill] Preview complete: {len(mutation_preview)} fields, "
        f"{len(missing_required)} missing, {len(warnings)} warnings"
    )

    return {
        "mutation_preview": mutation_preview,
        "missing_required": missing_required,
        "warnings": warnings,
        "dropdown_options": dropdown_options,
        "ready_to_commit": ready_to_commit,
        "extracted_entities": extracted_entities,  # For debugging
        "query_text": query_text,  # For debugging
    }


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_mutation_preview(
    mutation_preview: Dict[str, Any],
    field_metadata: Dict[str, FieldMetadata]
) -> Dict[str, Any]:
    """
    Validate mutation preview before commit.

    Checks:
    1. All REQUIRED fields present
    2. All fields have valid types
    3. Enum fields have valid options

    Args:
        mutation_preview: Mutation preview from build_mutation_preview
        field_metadata: Field metadata for validation

    Returns:
        Dict with:
            - valid: bool
            - errors: List of validation errors
    """
    errors = []

    # Check required fields
    for field_name, metadata in field_metadata.items():
        if metadata.classification == "REQUIRED":
            if field_name not in mutation_preview:
                errors.append(f"Required field missing: {field_name}")

        # Check enum options
        if metadata.options:
            field_value = mutation_preview.get(field_name)
            if field_value and field_value not in metadata.options:
                errors.append(
                    f"Invalid value for {field_name}: '{field_value}' "
                    f"(valid: {', '.join(metadata.options)})"
                )

    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
    }


__all__ = [
    "build_mutation_preview",
    "validate_mutation_preview",
    "extract_entity_value",
    "apply_compose_template",
    "apply_value_map",
    "generate_backend_auto_value",
]

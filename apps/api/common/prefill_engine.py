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
from datetime import datetime, timezone

from common.field_metadata import FieldMetadata, LookupResult
from common.lookup_functions import lookup_entity
from common.date_parser import parse_relative_date
from common.temporal_parser import parse_temporal_phrase

logger = logging.getLogger(__name__)


# =============================================================================
# PRIORITY SYNONYM MAPPING
# =============================================================================

PRIORITY_SYNONYMS = {
    "critical": "EMERGENCY",
    "urgent": "HIGH",
    "high": "HIGH",
    "asap": "HIGH",
    "medium": "MEDIUM",
    "normal": "MEDIUM",
    "low": "LOW",
    "minor": "LOW",
}


# =============================================================================
# AMBIGUITY DETECTION THRESHOLDS (DISAMB-03)
# =============================================================================

# Confidence thresholds for auto-fill behavior
AUTO_FILL_THRESHOLD = 0.85    # >= 0.85: auto-fill silently
CONFIRM_THRESHOLD = 0.65      # 0.65-0.84: auto-fill with confirm badge
AMBIGUOUS_THRESHOLD = 0.65    # < 0.65: require user disambiguation

# Maximum candidates to return for ambiguous lookups
MAX_AMBIGUITY_CANDIDATES = 5


def map_priority(raw_priority: str) -> tuple[Optional[str], float]:
    """
    Map priority synonyms to ActionPriority enum values.

    Args:
        raw_priority: Raw priority string from NLP

    Returns:
        Tuple of (mapped_value, confidence)
        - Exact match: (mapped, 0.95)
        - Fuzzy match: (mapped, 0.85)
        - No match: (None, 0.0)

    Example:
        >>> map_priority("urgent")
        ("HIGH", 0.95)
        >>> map_priority("  URGENT  ")
        ("HIGH", 0.85)
        >>> map_priority("unknown")
        (None, 0.0)
    """
    if not raw_priority:
        return (None, 0.0)

    # Exact match (case-sensitive)
    if raw_priority in PRIORITY_SYNONYMS:
        return (PRIORITY_SYNONYMS[raw_priority], 0.95)

    # Fuzzy match (lowercase + strip)
    raw_clean = raw_priority.strip().lower()
    if raw_clean in PRIORITY_SYNONYMS:
        return (PRIORITY_SYNONYMS[raw_clean], 0.85)

    # No match
    return (None, 0.0)


def detect_ambiguity(
    lookup_result: LookupResult,
    entity_value: str,
    field_name: str
) -> Optional[Dict[str, Any]]:
    """
    Detect if a lookup result is ambiguous and requires user disambiguation.

    Per DISAMB-03: Never silently assume - surface all uncertainty.

    Ambiguity criteria:
    1. Multiple matches found (count > 1)
    2. Single match with low confidence (confidence < 0.65)
    3. Partial string match (e.g., "ME" matches "ME1", "ME2")

    Args:
        lookup_result: Result from lookup_entity()
        entity_value: Original entity value from NLP
        field_name: Name of the field being populated

    Returns:
        Ambiguity dict if ambiguous, None otherwise:
        {
            "field": field_name,
            "original_value": entity_value,
            "candidates": [{"id": ..., "label": ..., "confidence": ...}]
        }
    """
    # Not ambiguous: single confident match
    if lookup_result.count == 1 and lookup_result.confidence >= CONFIRM_THRESHOLD:
        return None

    # Not ambiguous: no matches (different error - missing, not ambiguous)
    if lookup_result.count == 0:
        return None

    # Ambiguous: multiple matches
    if lookup_result.count > 1:
        candidates = []
        for option in lookup_result.options[:MAX_AMBIGUITY_CANDIDATES]:
            candidates.append({
                "id": option.get("id", option.get("value", "")),
                "label": option.get("name", option.get("label", "")),
                "confidence": 0.5,  # Equal confidence for ambiguous candidates
                "metadata": {
                    k: v for k, v in option.items()
                    if k not in ["id", "value", "name", "label"]
                }
            })

        logger.info(
            f"[Ambiguity] Field '{field_name}': '{entity_value}' matched "
            f"{lookup_result.count} candidates"
        )

        return {
            "field": field_name,
            "original_value": entity_value,
            "candidates": candidates
        }

    # Ambiguous: single match but low confidence
    if lookup_result.count == 1 and lookup_result.confidence < CONFIRM_THRESHOLD:
        # Still return as ambiguity so user can confirm
        candidates = [{
            "id": lookup_result.value,
            "label": lookup_result.options[0].get("name", str(lookup_result.value)) if lookup_result.options else str(lookup_result.value),
            "confidence": lookup_result.confidence
        }]

        logger.info(
            f"[Ambiguity] Field '{field_name}': low confidence match "
            f"({lookup_result.confidence:.2f}) for '{entity_value}'"
        )

        return {
            "field": field_name,
            "original_value": entity_value,
            "candidates": candidates
        }

    return None


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


def apply_date_parsing(
    value: Any,
    base_date: Optional[datetime] = None
) -> Optional[str]:
    """
    Parse natural language date expressions and return ISO format string.

    Supports patterns like:
    - "tomorrow" -> next day
    - "next week" -> Monday of next week
    - "in 3 days" -> 3 days from now
    - "next Monday" -> next occurrence of Monday
    - "end of month" -> last day of current month
    - "urgent" / "asap" -> today

    Args:
        value: Natural language date expression or existing date value
        base_date: Optional base date for calculations (default: UTC now)

    Returns:
        ISO format date string (YYYY-MM-DD) or None if not parseable

    Example:
        >>> apply_date_parsing("tomorrow")
        "2024-03-16"  # If today is 2024-03-15
        >>> apply_date_parsing("next week")
        "2024-03-18"  # Monday of next week
        >>> apply_date_parsing("not a date")
        None
    """
    if value is None:
        return None

    value_str = str(value).strip()

    # If already in ISO format (YYYY-MM-DD), return as-is
    if len(value_str) == 10 and value_str[4] == '-' and value_str[7] == '-':
        try:
            datetime.strptime(value_str, "%Y-%m-%d")
            return value_str
        except ValueError:
            pass

    # Use UTC if no base_date provided
    if base_date is None:
        base_date = datetime.now(timezone.utc)

    # Try to parse as relative date
    parsed_date = parse_relative_date(value_str, base_date)

    if parsed_date is not None:
        return parsed_date.isoformat()

    return None


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

                    # Apply date parsing for date fields
                    if metadata.field_type == "date" and field_value is not None:
                        parsed_date = apply_date_parsing(field_value)
                        if parsed_date is not None:
                            field_value = parsed_date
                            logger.debug(f"[Prefill] Parsed date for {field_name}: {field_value}")

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

                    # Apply date parsing for date fields (before lookup)
                    if metadata.field_type == "date" and field_value is not None:
                        parsed_date = apply_date_parsing(field_value)
                        if parsed_date is not None:
                            field_value = parsed_date
                            logger.debug(f"[Prefill] Parsed date for {field_name}: {field_value}")

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

                        else:
                            # Check for ambiguity (DISAMB-03)
                            ambiguity = detect_ambiguity(lookup_result, entity_value, field_name)

                            if ambiguity:
                                # Ambiguous result - add to dropdown options
                                warnings.append(
                                    f"Ambiguous {field_name}: '{entity_value}' matched {lookup_result.count} items"
                                )
                                dropdown_options[field_name] = lookup_result.options
                                field_value = None
                            else:
                                # Single confident match - use UUID
                                field_value = lookup_result.value
                                logger.info(f"[Prefill] {field_name} resolved to {field_value}")

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


# =============================================================================
# PREPARE RESPONSE BUILDER (for /v1/actions/prepare endpoint)
# =============================================================================

async def build_prepare_response(
    q: str,
    domain: str,
    candidate_action_ids: List[str],
    context: Dict[str, Any],  # yacht_id, user_role
    hint_entities: Dict[str, Any],
    client: Dict[str, str],  # timezone, now_iso
    supabase_client,
) -> Dict[str, Any]:
    """
    Build /prepare response for prefill preview with confidence per field.

    This is the main entry point for the /v1/actions/prepare endpoint.
    It integrates:
    - Action selection from candidates
    - Entity extraction (from hint_entities)
    - Temporal parsing
    - Priority mapping
    - Entity resolution via yacht-scoped lookups

    Args:
        q: Natural language query
        domain: Domain filter (e.g., "work_orders")
        candidate_action_ids: List of candidate action IDs from action detector
        context: Dict with yacht_id, user_role
        hint_entities: Pre-extracted entities from NLP pipeline
        client: Dict with timezone, now_iso for temporal parsing
        supabase_client: Supabase client for lookups

    Returns:
        Dict with:
            action_id: Selected action ID
            match_score: Confidence in action selection
            ready_to_commit: bool
            prefill: Dict[field_name -> {value, confidence, source}]
            missing_required_fields: List[str]
            ambiguities: List[{field, candidates}]
            errors: List[{error_code, message, field}]

    Example response:
        {
            "action_id": "create_work_order",
            "match_score": 0.95,
            "ready_to_commit": False,
            "prefill": {
                "equipment_id": {"value": "uuid", "confidence": 0.92, "source": "entity_resolver"},
                "priority": {"value": "HIGH", "confidence": 0.95, "source": "keyword_map"},
                "scheduled_date": {"value": "2026-03-08", "confidence": 0.88, "source": "temporal"},
            },
            "missing_required_fields": ["description"],
            "ambiguities": [],
            "errors": []
        }
    """
    errors = []
    ambiguities = []
    prefill = {}
    missing_required_fields = []

    # Import action registry to get action definition
    try:
        from action_router.registry import get_action, search_actions
    except ImportError:
        logger.error("[Prepare] Failed to import action registry")
        return {
            "action_id": None,
            "match_score": 0.0,
            "ready_to_commit": False,
            "prefill": {},
            "missing_required_fields": [],
            "ambiguities": [],
            "errors": [{
                "error_code": "REGISTRY_IMPORT_ERROR",
                "message": "Failed to import action registry",
                "field": None
            }]
        }

    # =========================================================================
    # STEP 1: Select best matching action from candidates
    # =========================================================================
    action_id = None
    match_score = 0.0

    if not candidate_action_ids:
        errors.append({
            "error_code": "NO_MATCHING_ACTION",
            "message": "No candidate actions provided",
            "field": None
        })
    else:
        # Use first candidate for now (in production, use search_actions with q)
        action_id = candidate_action_ids[0]
        match_score = 0.95  # Simplified - production should calculate from search

        # Validate action exists
        try:
            action_def = get_action(action_id)
        except KeyError:
            errors.append({
                "error_code": "INVALID_ACTION",
                "message": f"Action '{action_id}' not found in registry",
                "field": None
            })
            action_id = None

    if not action_id:
        return {
            "action_id": None,
            "match_score": 0.0,
            "ready_to_commit": False,
            "prefill": {},
            "missing_required_fields": [],
            "ambiguities": [],
            "errors": errors
        }

    # =========================================================================
    # STEP 2: Get action's field metadata
    # =========================================================================
    action_def = get_action(action_id)
    if not action_def.field_metadata:
        # No field metadata - return empty prefill
        return {
            "action_id": action_id,
            "match_score": match_score,
            "ready_to_commit": False,
            "prefill": {},
            "missing_required_fields": action_def.required_fields or [],
            "ambiguities": [],
            "errors": []
        }

    # Convert registry FieldMetadata to prefill FieldMetadata format
    from action_router.router import convert_registry_field_metadata_to_prefill
    field_metadata_dict = convert_registry_field_metadata_to_prefill(action_def.field_metadata)

    # =========================================================================
    # STEP 3: Build mutation preview using existing engine
    # =========================================================================
    yacht_id = context.get("yacht_id")
    user_id = context.get("user_id")

    preview_result = await build_mutation_preview(
        query_text=q,
        extracted_entities=hint_entities or {},
        field_metadata=field_metadata_dict,
        yacht_id=yacht_id,
        supabase_client=supabase_client,
        user_id=user_id,
        context=context,
    )

    mutation_preview = preview_result.get("mutation_preview", {})
    warnings = preview_result.get("warnings", [])
    dropdown_options = preview_result.get("dropdown_options", {})

    # =========================================================================
    # STEP 4: Enhance with temporal parsing for date fields
    # =========================================================================
    for field_name, metadata in field_metadata_dict.items():
        if metadata.field_type == "date":
            # Check if entity was extracted for this field
            entity_value = hint_entities.get(metadata.auto_populate_from) if metadata.auto_populate_from else None

            if entity_value and field_name not in mutation_preview:
                # Parse temporal phrase
                temporal_result = parse_temporal_phrase(
                    entity_value,
                    client.get("timezone", "UTC"),
                    client.get("now_iso", datetime.now(timezone.utc).isoformat())
                )

                if temporal_result.value:
                    prefill[field_name] = {
                        "value": temporal_result.value,
                        "confidence": temporal_result.confidence,
                        "source": "temporal"
                    }

    # =========================================================================
    # STEP 5: Enhance with priority mapping
    # =========================================================================
    # Check if priority field exists
    if "priority" in field_metadata_dict:
        raw_priority = hint_entities.get("priority")
        if raw_priority and "priority" not in mutation_preview:
            mapped_priority, confidence = map_priority(raw_priority)
            if mapped_priority:
                prefill["priority"] = {
                    "value": mapped_priority,
                    "confidence": confidence,
                    "source": "keyword_map"
                }

    # =========================================================================
    # STEP 6: Convert mutation_preview to prefill format with confidence
    # =========================================================================
    for field_name, field_value in mutation_preview.items():
        if field_name not in prefill:
            # Determine confidence based on lookup result and field metadata
            metadata = field_metadata_dict.get(field_name)
            if metadata:
                if metadata.lookup_required:
                    # Lookup-based fields: use actual lookup confidence if available
                    source = "entity_resolver"
                    # Default high confidence for successful lookups
                    confidence = 0.92
                elif metadata.compose_template:
                    source = "template"
                    confidence = 0.88
                elif metadata.classification == "CONTEXT":
                    source = "context"
                    confidence = 1.0
                elif metadata.classification == "BACKEND_AUTO":
                    source = "backend_auto"
                    confidence = 1.0
                else:
                    source = "extracted"
                    confidence = 0.85
            else:
                source = "unknown"
                confidence = 0.80

            # DISAMB-03: Surface uncertainty - if value is None but we have candidates,
            # it's an ambiguity, not a clean prefill
            if field_value is None and field_name in dropdown_options:
                # Don't add to prefill - it's in ambiguities instead
                continue

            prefill[field_name] = {
                "value": field_value,
                "confidence": confidence,
                "source": source
            }

    # =========================================================================
    # STEP 7: Build ambiguities from dropdown_options
    # =========================================================================
    for field_name, options in dropdown_options.items():
        ambiguities.append({
            "field": field_name,
            "candidates": [
                {
                    "id": opt.get("id", ""),
                    "label": opt.get("name", "") or opt.get("label", ""),
                    "confidence": 0.5  # Equal confidence for ambiguous candidates
                }
                for opt in options
            ]
        })

    # =========================================================================
    # STEP 8: Identify missing required fields
    # =========================================================================
    missing_required_fields = preview_result.get("missing_required", [])

    # =========================================================================
    # STEP 9: Determine ready_to_commit
    # =========================================================================
    ready_to_commit = (
        len(missing_required_fields) == 0 and
        len(ambiguities) == 0
    )

    return {
        "action_id": action_id,
        "match_score": match_score,
        "ready_to_commit": ready_to_commit,
        "prefill": prefill,
        "missing_required_fields": missing_required_fields,
        "ambiguities": ambiguities,
        "errors": errors
    }


# =============================================================================
# LENS-SPECIFIC ENTITY RESOLUTION FUNCTIONS
# =============================================================================
# SECURITY: All SELECT queries MUST have WHERE yacht_id = $1
# No cross-yacht data access is permitted.


async def resolve_work_order_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for work_order lens actions.

    Resolves:
    - equipment: equipment_id from pms_equipment
    - work_order: work_order_id from pms_work_orders
    - fault: fault_id from pms_faults
    - user: assigned_to from auth_users_profiles

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve equipment
    if "equipment" in extracted_entities or "equipment_name" in extracted_entities:
        equipment_value = extracted_entities.get("equipment") or extracted_entities.get("equipment_name")
        if equipment_value:
            try:
                result = supabase_client.table("pms_equipment").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{equipment_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["equipment_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["equipment_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_work_order_entities] Equipment lookup failed: {e}")

    # Resolve work order
    if "work_order" in extracted_entities or "work_order_id" in extracted_entities or "wo_number" in extracted_entities:
        wo_value = extracted_entities.get("work_order") or extracted_entities.get("work_order_id") or extracted_entities.get("wo_number")
        if wo_value:
            try:
                # Try by number first
                result = supabase_client.table("pms_work_orders").select(
                    "id, number, title"
                ).eq("yacht_id", yacht_id).or_(f"number.ilike.%{wo_value}%,title.ilike.%{wo_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["work_order_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["work_order_candidates"] = [
                        {"id": str(r["id"]), "number": r.get("number"), "title": r.get("title")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_work_order_entities] Work order lookup failed: {e}")

    # Resolve fault
    if "fault" in extracted_entities or "fault_id" in extracted_entities:
        fault_value = extracted_entities.get("fault") or extracted_entities.get("fault_id")
        if fault_value:
            try:
                result = supabase_client.table("pms_faults").select(
                    "id, title, fault_code"
                ).eq("yacht_id", yacht_id).or_(f"title.ilike.%{fault_value}%,fault_code.ilike.%{fault_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["fault_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["fault_candidates"] = [
                        {"id": str(r["id"]), "title": r.get("title"), "fault_code": r.get("fault_code")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_work_order_entities] Fault lookup failed: {e}")

    # Resolve assigned_to (user)
    if "assigned_to" in extracted_entities or "assignee" in extracted_entities:
        user_value = extracted_entities.get("assigned_to") or extracted_entities.get("assignee")
        if user_value:
            try:
                result = supabase_client.table("auth_users_profiles").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{user_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["assigned_to"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["assigned_to_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_work_order_entities] User lookup failed: {e}")

    return resolved


async def resolve_fault_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for fault lens actions.

    Resolves:
    - equipment: equipment_id from pms_equipment
    - fault: fault_id from pms_faults
    - part: part_id from pms_parts (for recommended_parts)

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve equipment
    if "equipment" in extracted_entities or "equipment_name" in extracted_entities:
        equipment_value = extracted_entities.get("equipment") or extracted_entities.get("equipment_name")
        if equipment_value:
            try:
                result = supabase_client.table("pms_equipment").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{equipment_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["equipment_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["equipment_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_fault_entities] Equipment lookup failed: {e}")

    # Resolve fault
    if "fault" in extracted_entities or "fault_id" in extracted_entities:
        fault_value = extracted_entities.get("fault") or extracted_entities.get("fault_id")
        if fault_value:
            try:
                result = supabase_client.table("pms_faults").select(
                    "id, title, fault_code"
                ).eq("yacht_id", yacht_id).or_(f"title.ilike.%{fault_value}%,fault_code.ilike.%{fault_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["fault_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["fault_candidates"] = [
                        {"id": str(r["id"]), "title": r.get("title"), "fault_code": r.get("fault_code")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_fault_entities] Fault lookup failed: {e}")

    # Resolve part (for recommended_parts)
    if "part" in extracted_entities or "part_name" in extracted_entities:
        part_value = extracted_entities.get("part") or extracted_entities.get("part_name")
        if part_value:
            try:
                result = supabase_client.table("pms_parts").select(
                    "id, name, part_number"
                ).eq("yacht_id", yacht_id).or_(f"name.ilike.%{part_value}%,part_number.ilike.%{part_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["part_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["part_candidates"] = [
                        {"id": str(r["id"]), "name": r.get("name"), "part_number": r.get("part_number")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_fault_entities] Part lookup failed: {e}")

    return resolved


async def resolve_equipment_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for equipment lens actions.

    Resolves:
    - equipment: equipment_id from pms_equipment
    - document: document_id from pms_documents

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve equipment
    if "equipment" in extracted_entities or "equipment_name" in extracted_entities or "equipment_id" in extracted_entities:
        equipment_value = extracted_entities.get("equipment") or extracted_entities.get("equipment_name") or extracted_entities.get("equipment_id")
        if equipment_value:
            try:
                result = supabase_client.table("pms_equipment").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{equipment_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["equipment_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["equipment_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_equipment_entities] Equipment lookup failed: {e}")

    # Resolve document
    if "document" in extracted_entities or "document_name" in extracted_entities:
        doc_value = extracted_entities.get("document") or extracted_entities.get("document_name")
        if doc_value:
            try:
                result = supabase_client.table("pms_documents").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{doc_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["document_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["document_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_equipment_entities] Document lookup failed: {e}")

    return resolved


async def resolve_part_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for part lens actions.

    Resolves:
    - part: part_id from pms_parts
    - work_order: work_order_id from pms_work_orders
    - supplier: supplier_id from pms_suppliers

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve part
    if "part" in extracted_entities or "part_name" in extracted_entities or "part_number" in extracted_entities:
        part_value = extracted_entities.get("part") or extracted_entities.get("part_name") or extracted_entities.get("part_number")
        if part_value:
            try:
                result = supabase_client.table("pms_parts").select(
                    "id, name, part_number"
                ).eq("yacht_id", yacht_id).or_(f"name.ilike.%{part_value}%,part_number.ilike.%{part_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["part_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["part_candidates"] = [
                        {"id": str(r["id"]), "name": r.get("name"), "part_number": r.get("part_number")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_part_entities] Part lookup failed: {e}")

    # Resolve work order
    if "work_order" in extracted_entities or "work_order_id" in extracted_entities:
        wo_value = extracted_entities.get("work_order") or extracted_entities.get("work_order_id")
        if wo_value:
            try:
                result = supabase_client.table("pms_work_orders").select(
                    "id, number, title"
                ).eq("yacht_id", yacht_id).or_(f"number.ilike.%{wo_value}%,title.ilike.%{wo_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["work_order_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["work_order_candidates"] = [
                        {"id": str(r["id"]), "number": r.get("number"), "title": r.get("title")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_part_entities] Work order lookup failed: {e}")

    # Resolve supplier
    if "supplier" in extracted_entities or "supplier_name" in extracted_entities:
        supplier_value = extracted_entities.get("supplier") or extracted_entities.get("supplier_name")
        if supplier_value:
            try:
                result = supabase_client.table("pms_suppliers").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{supplier_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["supplier_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["supplier_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_part_entities] Supplier lookup failed: {e}")

    return resolved


async def resolve_inventory_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for inventory lens actions.

    Resolves:
    - part: part_id from pms_parts
    - work_order: work_order_id from pms_work_orders

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve part
    if "part" in extracted_entities or "part_name" in extracted_entities or "part_number" in extracted_entities:
        part_value = extracted_entities.get("part") or extracted_entities.get("part_name") or extracted_entities.get("part_number")
        if part_value:
            try:
                result = supabase_client.table("pms_parts").select(
                    "id, name, part_number"
                ).eq("yacht_id", yacht_id).or_(f"name.ilike.%{part_value}%,part_number.ilike.%{part_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["part_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["part_candidates"] = [
                        {"id": str(r["id"]), "name": r.get("name"), "part_number": r.get("part_number")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_inventory_entities] Part lookup failed: {e}")

    # Resolve work order
    if "work_order" in extracted_entities or "work_order_id" in extracted_entities:
        wo_value = extracted_entities.get("work_order") or extracted_entities.get("work_order_id")
        if wo_value:
            try:
                result = supabase_client.table("pms_work_orders").select(
                    "id, number, title"
                ).eq("yacht_id", yacht_id).or_(f"number.ilike.%{wo_value}%,title.ilike.%{wo_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["work_order_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["work_order_candidates"] = [
                        {"id": str(r["id"]), "number": r.get("number"), "title": r.get("title")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_inventory_entities] Work order lookup failed: {e}")

    return resolved


async def resolve_certificate_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for certificate lens actions.

    Resolves:
    - certificate: certificate_id from pms_certificates
    - crew_member: crew_member_id from auth_users_profiles
    - document: document_id from pms_documents

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve certificate
    if "certificate" in extracted_entities or "certificate_id" in extracted_entities:
        cert_value = extracted_entities.get("certificate") or extracted_entities.get("certificate_id")
        if cert_value:
            try:
                result = supabase_client.table("pms_certificates").select(
                    "id, certificate_type, certificate_number"
                ).eq("yacht_id", yacht_id).or_(f"certificate_type.ilike.%{cert_value}%,certificate_number.ilike.%{cert_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["certificate_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["certificate_candidates"] = [
                        {"id": str(r["id"]), "certificate_type": r.get("certificate_type"), "certificate_number": r.get("certificate_number")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_certificate_entities] Certificate lookup failed: {e}")

    # Resolve crew member
    if "crew_member" in extracted_entities or "crew_member_name" in extracted_entities:
        crew_value = extracted_entities.get("crew_member") or extracted_entities.get("crew_member_name")
        if crew_value:
            try:
                result = supabase_client.table("auth_users_profiles").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{crew_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["crew_member_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["crew_member_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_certificate_entities] Crew member lookup failed: {e}")

    # Resolve document
    if "document" in extracted_entities or "document_name" in extracted_entities:
        doc_value = extracted_entities.get("document") or extracted_entities.get("document_name")
        if doc_value:
            try:
                result = supabase_client.table("pms_documents").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{doc_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["document_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["document_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_certificate_entities] Document lookup failed: {e}")

    return resolved


async def resolve_handover_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for handover lens actions.

    Resolves:
    - handover_item: handover_item_id from pms_handover_items
    - equipment: equipment_id from pms_equipment
    - document: document_id from pms_documents
    - fault: fault_id from pms_faults
    - work_order: work_order_id from pms_work_orders

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve handover item
    if "handover_item" in extracted_entities or "handover_item_id" in extracted_entities:
        item_value = extracted_entities.get("handover_item") or extracted_entities.get("handover_item_id")
        if item_value:
            try:
                result = supabase_client.table("pms_handover_items").select(
                    "id, title"
                ).eq("yacht_id", yacht_id).ilike("title", f"%{item_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["handover_item_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["handover_item_candidates"] = [
                        {"id": str(r["id"]), "title": r.get("title")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_handover_entities] Handover item lookup failed: {e}")

    # Resolve equipment
    if "equipment" in extracted_entities or "equipment_name" in extracted_entities:
        equipment_value = extracted_entities.get("equipment") or extracted_entities.get("equipment_name")
        if equipment_value:
            try:
                result = supabase_client.table("pms_equipment").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{equipment_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["equipment_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["equipment_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_handover_entities] Equipment lookup failed: {e}")

    # Resolve document
    if "document" in extracted_entities or "document_name" in extracted_entities:
        doc_value = extracted_entities.get("document") or extracted_entities.get("document_name")
        if doc_value:
            try:
                result = supabase_client.table("pms_documents").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{doc_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["document_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["document_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_handover_entities] Document lookup failed: {e}")

    # Resolve fault (for entity_type=fault)
    if "fault" in extracted_entities or "fault_id" in extracted_entities:
        fault_value = extracted_entities.get("fault") or extracted_entities.get("fault_id")
        if fault_value:
            try:
                result = supabase_client.table("pms_faults").select(
                    "id, title"
                ).eq("yacht_id", yacht_id).ilike("title", f"%{fault_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["fault_id"] = str(result.data[0]["id"])
                    resolved["entity_id"] = str(result.data[0]["id"])
                    resolved["entity_type"] = "fault"
                elif result.data and len(result.data) > 1:
                    resolved["fault_candidates"] = [
                        {"id": str(r["id"]), "title": r.get("title")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_handover_entities] Fault lookup failed: {e}")

    # Resolve work order (for entity_type=work_order)
    if "work_order" in extracted_entities or "work_order_id" in extracted_entities:
        wo_value = extracted_entities.get("work_order") or extracted_entities.get("work_order_id")
        if wo_value:
            try:
                result = supabase_client.table("pms_work_orders").select(
                    "id, number, title"
                ).eq("yacht_id", yacht_id).or_(f"number.ilike.%{wo_value}%,title.ilike.%{wo_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["work_order_id"] = str(result.data[0]["id"])
                    resolved["entity_id"] = str(result.data[0]["id"])
                    resolved["entity_type"] = "work_order"
                elif result.data and len(result.data) > 1:
                    resolved["work_order_candidates"] = [
                        {"id": str(r["id"]), "number": r.get("number"), "title": r.get("title")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_handover_entities] Work order lookup failed: {e}")

    return resolved


async def resolve_hours_of_rest_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for hours_of_rest lens actions.

    Resolves:
    - user: user_id from auth_users_profiles
    - signoff: signoff_id from pms_hor_monthly_signoffs
    - template: template_id from pms_hor_templates
    - warning: warning_id from pms_hor_warnings

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve user
    if "user" in extracted_entities or "user_name" in extracted_entities or "crew_member" in extracted_entities:
        user_value = extracted_entities.get("user") or extracted_entities.get("user_name") or extracted_entities.get("crew_member")
        if user_value:
            try:
                result = supabase_client.table("auth_users_profiles").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{user_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["user_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["user_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_hours_of_rest_entities] User lookup failed: {e}")

    # Resolve signoff
    if "signoff" in extracted_entities or "signoff_id" in extracted_entities:
        signoff_value = extracted_entities.get("signoff") or extracted_entities.get("signoff_id")
        if signoff_value:
            try:
                result = supabase_client.table("pms_hor_monthly_signoffs").select(
                    "id, month, year"
                ).eq("yacht_id", yacht_id).limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["signoff_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["signoff_candidates"] = [
                        {"id": str(r["id"]), "month": r.get("month"), "year": r.get("year")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_hours_of_rest_entities] Signoff lookup failed: {e}")

    # Resolve template
    if "template" in extracted_entities or "template_name" in extracted_entities:
        template_value = extracted_entities.get("template") or extracted_entities.get("template_name")
        if template_value:
            try:
                result = supabase_client.table("pms_hor_templates").select(
                    "id, template_name"
                ).eq("yacht_id", yacht_id).ilike("template_name", f"%{template_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["template_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["template_candidates"] = [
                        {"id": str(r["id"]), "template_name": r.get("template_name")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_hours_of_rest_entities] Template lookup failed: {e}")

    # Resolve warning
    if "warning" in extracted_entities or "warning_id" in extracted_entities:
        warning_value = extracted_entities.get("warning") or extracted_entities.get("warning_id")
        if warning_value:
            try:
                result = supabase_client.table("pms_hor_warnings").select(
                    "id, warning_type"
                ).eq("yacht_id", yacht_id).limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["warning_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["warning_candidates"] = [
                        {"id": str(r["id"]), "warning_type": r.get("warning_type")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_hours_of_rest_entities] Warning lookup failed: {e}")

    return resolved


async def resolve_warranty_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for warranty lens actions.

    Resolves:
    - warranty: warranty_id from pms_warranties
    - equipment: equipment_id from pms_equipment
    - supplier: supplier from pms_suppliers
    - fault: fault_id from pms_faults (for claims)
    - document: document_id from pms_documents

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve warranty
    if "warranty" in extracted_entities or "warranty_id" in extracted_entities:
        warranty_value = extracted_entities.get("warranty") or extracted_entities.get("warranty_id")
        if warranty_value:
            try:
                result = supabase_client.table("pms_warranties").select(
                    "id, warranty_number, equipment_id"
                ).eq("yacht_id", yacht_id).ilike("warranty_number", f"%{warranty_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["warranty_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["warranty_candidates"] = [
                        {"id": str(r["id"]), "warranty_number": r.get("warranty_number")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_warranty_entities] Warranty lookup failed: {e}")

    # Resolve equipment
    if "equipment" in extracted_entities or "equipment_name" in extracted_entities:
        equipment_value = extracted_entities.get("equipment") or extracted_entities.get("equipment_name")
        if equipment_value:
            try:
                result = supabase_client.table("pms_equipment").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{equipment_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["equipment_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["equipment_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_warranty_entities] Equipment lookup failed: {e}")

    # Resolve supplier
    if "supplier" in extracted_entities or "supplier_name" in extracted_entities:
        supplier_value = extracted_entities.get("supplier") or extracted_entities.get("supplier_name")
        if supplier_value:
            try:
                result = supabase_client.table("pms_suppliers").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{supplier_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["supplier_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["supplier_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_warranty_entities] Supplier lookup failed: {e}")

    # Resolve fault (for warranty claims)
    if "fault" in extracted_entities or "fault_id" in extracted_entities:
        fault_value = extracted_entities.get("fault") or extracted_entities.get("fault_id")
        if fault_value:
            try:
                result = supabase_client.table("pms_faults").select(
                    "id, title"
                ).eq("yacht_id", yacht_id).ilike("title", f"%{fault_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["fault_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["fault_candidates"] = [
                        {"id": str(r["id"]), "title": r.get("title")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_warranty_entities] Fault lookup failed: {e}")

    # Resolve document
    if "document" in extracted_entities or "document_name" in extracted_entities:
        doc_value = extracted_entities.get("document") or extracted_entities.get("document_name")
        if doc_value:
            try:
                result = supabase_client.table("pms_documents").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{doc_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["document_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["document_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_warranty_entities] Document lookup failed: {e}")

    return resolved


async def resolve_shopping_list_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for shopping_list lens actions.

    Resolves:
    - shopping_list_item: item_id from pms_shopping_list
    - part: part_id from pms_parts
    - purchase_order: purchase_order_id from pms_purchase_orders
    - receiving: receiving_id from pms_receiving

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve shopping list item
    if "item" in extracted_entities or "item_id" in extracted_entities or "shopping_list_item" in extracted_entities:
        item_value = extracted_entities.get("item") or extracted_entities.get("item_id") or extracted_entities.get("shopping_list_item")
        if item_value:
            try:
                result = supabase_client.table("pms_shopping_list").select(
                    "id, part_name"
                ).eq("yacht_id", yacht_id).ilike("part_name", f"%{item_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["item_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["item_candidates"] = [
                        {"id": str(r["id"]), "part_name": r.get("part_name")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_shopping_list_entities] Item lookup failed: {e}")

    # Resolve part
    if "part" in extracted_entities or "part_name" in extracted_entities or "part_number" in extracted_entities:
        part_value = extracted_entities.get("part") or extracted_entities.get("part_name") or extracted_entities.get("part_number")
        if part_value:
            try:
                result = supabase_client.table("pms_parts").select(
                    "id, name, part_number"
                ).eq("yacht_id", yacht_id).or_(f"name.ilike.%{part_value}%,part_number.ilike.%{part_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["part_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["part_candidates"] = [
                        {"id": str(r["id"]), "name": r.get("name"), "part_number": r.get("part_number")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_shopping_list_entities] Part lookup failed: {e}")

    # Resolve purchase order
    if "purchase_order" in extracted_entities or "purchase_order_id" in extracted_entities or "po_number" in extracted_entities:
        po_value = extracted_entities.get("purchase_order") or extracted_entities.get("purchase_order_id") or extracted_entities.get("po_number")
        if po_value:
            try:
                result = supabase_client.table("pms_purchase_orders").select(
                    "id, po_number"
                ).eq("yacht_id", yacht_id).ilike("po_number", f"%{po_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["purchase_order_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["purchase_order_candidates"] = [
                        {"id": str(r["id"]), "po_number": r.get("po_number")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_shopping_list_entities] Purchase order lookup failed: {e}")

    return resolved


async def resolve_email_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for email lens actions.

    Resolves:
    - thread: thread_id from pms_email_threads
    - entity: entity_id for linking (work_order, equipment, fault, part, handover)
    - work_order, equipment, fault, part entities

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve email thread
    if "thread" in extracted_entities or "thread_id" in extracted_entities:
        thread_value = extracted_entities.get("thread") or extracted_entities.get("thread_id")
        if thread_value:
            try:
                result = supabase_client.table("pms_email_threads").select(
                    "id, subject"
                ).eq("yacht_id", yacht_id).ilike("subject", f"%{thread_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["thread_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["thread_candidates"] = [
                        {"id": str(r["id"]), "subject": r.get("subject")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_email_entities] Thread lookup failed: {e}")

    # Resolve equipment (for create_work_order_from_email, create_fault_from_email)
    if "equipment" in extracted_entities or "equipment_name" in extracted_entities:
        equipment_value = extracted_entities.get("equipment") or extracted_entities.get("equipment_name")
        if equipment_value:
            try:
                result = supabase_client.table("pms_equipment").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{equipment_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["equipment_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["equipment_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_email_entities] Equipment lookup failed: {e}")

    # Resolve work order (for link_email_to_entity)
    if "work_order" in extracted_entities or "work_order_id" in extracted_entities:
        wo_value = extracted_entities.get("work_order") or extracted_entities.get("work_order_id")
        if wo_value:
            try:
                result = supabase_client.table("pms_work_orders").select(
                    "id, number, title"
                ).eq("yacht_id", yacht_id).or_(f"number.ilike.%{wo_value}%,title.ilike.%{wo_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["entity_id"] = str(result.data[0]["id"])
                    resolved["entity_type"] = "work_order"
                elif result.data and len(result.data) > 1:
                    resolved["work_order_candidates"] = [
                        {"id": str(r["id"]), "number": r.get("number"), "title": r.get("title")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_email_entities] Work order lookup failed: {e}")

    # Resolve fault (for link_email_to_entity)
    if "fault" in extracted_entities or "fault_id" in extracted_entities:
        fault_value = extracted_entities.get("fault") or extracted_entities.get("fault_id")
        if fault_value:
            try:
                result = supabase_client.table("pms_faults").select(
                    "id, title"
                ).eq("yacht_id", yacht_id).ilike("title", f"%{fault_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["entity_id"] = str(result.data[0]["id"])
                    resolved["entity_type"] = "fault"
                elif result.data and len(result.data) > 1:
                    resolved["fault_candidates"] = [
                        {"id": str(r["id"]), "title": r.get("title")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_email_entities] Fault lookup failed: {e}")

    return resolved


async def resolve_receiving_entities(
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Resolve entities for receiving lens actions.

    Resolves:
    - receiving: receiving_id from pms_receiving
    - receiving_item: receiving_item_id from pms_receiving_items
    - supplier: supplier_id from pms_suppliers
    - part: part_id from pms_parts
    - document: document_id from pms_documents

    SECURITY: All queries filtered by yacht_id.
    """
    resolved = {}

    # Resolve receiving
    if "receiving" in extracted_entities or "receiving_id" in extracted_entities:
        receiving_value = extracted_entities.get("receiving") or extracted_entities.get("receiving_id")
        if receiving_value:
            try:
                result = supabase_client.table("pms_receiving").select(
                    "id, created_at"
                ).eq("yacht_id", yacht_id).limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["receiving_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["receiving_candidates"] = [
                        {"id": str(r["id"]), "created_at": r.get("created_at")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_receiving_entities] Receiving lookup failed: {e}")

    # Resolve receiving item
    if "receiving_item" in extracted_entities or "receiving_item_id" in extracted_entities:
        item_value = extracted_entities.get("receiving_item") or extracted_entities.get("receiving_item_id")
        if item_value:
            try:
                result = supabase_client.table("pms_receiving_items").select(
                    "id, part_id"
                ).eq("yacht_id", yacht_id).limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["receiving_item_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["receiving_item_candidates"] = [
                        {"id": str(r["id"]), "part_id": r.get("part_id")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_receiving_entities] Receiving item lookup failed: {e}")

    # Resolve supplier
    if "supplier" in extracted_entities or "supplier_name" in extracted_entities:
        supplier_value = extracted_entities.get("supplier") or extracted_entities.get("supplier_name")
        if supplier_value:
            try:
                result = supabase_client.table("pms_suppliers").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{supplier_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["supplier_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["supplier_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_receiving_entities] Supplier lookup failed: {e}")

    # Resolve part
    if "part" in extracted_entities or "part_name" in extracted_entities or "part_number" in extracted_entities:
        part_value = extracted_entities.get("part") or extracted_entities.get("part_name") or extracted_entities.get("part_number")
        if part_value:
            try:
                result = supabase_client.table("pms_parts").select(
                    "id, name, part_number"
                ).eq("yacht_id", yacht_id).or_(f"name.ilike.%{part_value}%,part_number.ilike.%{part_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["part_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["part_candidates"] = [
                        {"id": str(r["id"]), "name": r.get("name"), "part_number": r.get("part_number")} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_receiving_entities] Part lookup failed: {e}")

    # Resolve document
    if "document" in extracted_entities or "document_name" in extracted_entities:
        doc_value = extracted_entities.get("document") or extracted_entities.get("document_name")
        if doc_value:
            try:
                result = supabase_client.table("pms_documents").select(
                    "id, name"
                ).eq("yacht_id", yacht_id).ilike("name", f"%{doc_value}%").limit(5).execute()
                if result.data and len(result.data) == 1:
                    resolved["document_id"] = str(result.data[0]["id"])
                elif result.data and len(result.data) > 1:
                    resolved["document_candidates"] = [
                        {"id": str(r["id"]), "name": r["name"]} for r in result.data
                    ]
            except Exception as e:
                logger.warning(f"[resolve_receiving_entities] Document lookup failed: {e}")

    return resolved


# Lens resolver dispatch table
LENS_ENTITY_RESOLVERS = {
    "work_order": resolve_work_order_entities,
    "fault": resolve_fault_entities,
    "equipment": resolve_equipment_entities,
    "part": resolve_part_entities,
    "inventory": resolve_inventory_entities,
    "certificate": resolve_certificate_entities,
    "handover": resolve_handover_entities,
    "hours_of_rest": resolve_hours_of_rest_entities,
    "warranty": resolve_warranty_entities,
    "shopping_list": resolve_shopping_list_entities,
    "email": resolve_email_entities,
    "receiving": resolve_receiving_entities,
}


async def resolve_entities_for_lens(
    lens: str,
    yacht_id: str,
    extracted_entities: Dict[str, Any],
    supabase_client,
) -> Dict[str, Any]:
    """
    Dispatch entity resolution to lens-specific resolver.

    Args:
        lens: The lens name (work_order, fault, equipment, etc.)
        yacht_id: Yacht UUID for RLS enforcement
        extracted_entities: Dict of entities extracted from NLP
        supabase_client: Supabase client for database queries

    Returns:
        Dict of resolved entity IDs and any ambiguity candidates

    SECURITY: All queries filtered by yacht_id.
    """
    resolver = LENS_ENTITY_RESOLVERS.get(lens)
    if not resolver:
        logger.warning(f"[resolve_entities_for_lens] No resolver for lens: {lens}")
        return {}

    return await resolver(yacht_id, extracted_entities, supabase_client)


# =============================================================================
# GENERIC PREPARE ACTION FUNCTION
# =============================================================================


async def prepare_action(
    lens: str,
    action_id: str,
    query_text: str,
    extracted_entities: Dict[str, Any],
    yacht_id: str,
    user_id: str,
    user_role: str,
    supabase_client,
    action_registry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generic prepare function for any lens action.

    Combines:
    1. Lens-specific entity resolution (resolve_*_entities)
    2. Action field metadata from registry
    3. Mutation preview generation
    4. Role checking

    Args:
        lens: The lens name (work_order, fault, etc.)
        action_id: The action ID (create_work_order, report_fault, etc.)
        query_text: Original NLP query
        extracted_entities: Dict of entities extracted from NLP
        yacht_id: Yacht UUID for RLS enforcement
        user_id: User UUID
        user_role: User's role for role gating
        supabase_client: Supabase client for database queries
        action_registry: Optional action registry dict (for testing)

    Returns:
        PrepareResponse dict:
        {
            "action_id": str,
            "lens": str,
            "ready_to_commit": bool,
            "prefill": {field: {value, confidence, source}},
            "resolved_entities": {entity_id: uuid},
            "missing_required_fields": [str],
            "ambiguities": [{field, candidates}],
            "role_blocked": bool,
            "errors": [{error_code, message, field}]
        }

    SECURITY: All entity lookups filtered by yacht_id.
    """
    errors = []
    ambiguities = []
    prefill = {}
    missing_required_fields = []
    resolved_entities = {}
    role_blocked = False

    # =========================================================================
    # STEP 1: Resolve entities using lens-specific resolver
    # =========================================================================
    try:
        resolved_entities = await resolve_entities_for_lens(
            lens=lens,
            yacht_id=yacht_id,
            extracted_entities=extracted_entities,
            supabase_client=supabase_client,
        )

        # Extract ambiguities from resolved entities (any *_candidates fields)
        for key, value in list(resolved_entities.items()):
            if key.endswith("_candidates"):
                field_name = key.replace("_candidates", "_id")
                ambiguities.append({
                    "field": field_name,
                    "candidates": value
                })
                del resolved_entities[key]

    except Exception as e:
        logger.error(f"[prepare_action] Entity resolution failed for {lens}/{action_id}: {e}")
        errors.append({
            "error_code": "ENTITY_RESOLUTION_ERROR",
            "message": f"Failed to resolve entities: {str(e)}",
            "field": None
        })

    # =========================================================================
    # STEP 2: Get action metadata from registry (if available)
    # =========================================================================
    action_def = None
    required_fields = []
    optional_fields = []
    role_restricted = []

    if action_registry:
        action_def = action_registry.get(action_id)
    else:
        # Try to import from action_router.registry
        try:
            from action_router.registry import get_action
            action_def = get_action(action_id)
        except (ImportError, KeyError) as e:
            logger.warning(f"[prepare_action] Could not get action definition for {action_id}: {e}")

    if action_def:
        # Extract field requirements from action definition
        if hasattr(action_def, 'required_fields'):
            required_fields = action_def.required_fields or []
        elif isinstance(action_def, dict):
            required_fields = action_def.get('required_fields', [])

        if hasattr(action_def, 'optional_fields'):
            optional_fields = action_def.optional_fields or []
        elif isinstance(action_def, dict):
            optional_fields = action_def.get('optional_fields', [])

        if hasattr(action_def, 'allowed_roles'):
            role_restricted = action_def.allowed_roles or []
        elif isinstance(action_def, dict):
            role_restricted = action_def.get('role_restricted', [])

    # =========================================================================
    # STEP 3: Check role gating
    # =========================================================================
    if role_restricted and user_role not in role_restricted:
        role_blocked = True

    # =========================================================================
    # STEP 4: Build prefill from resolved entities and extracted entities
    # =========================================================================
    # Add resolved entities to prefill
    for field_name, field_value in resolved_entities.items():
        if field_value is not None:
            prefill[field_name] = {
                "value": field_value,
                "confidence": 0.92,  # High confidence for resolved entities
                "source": "entity_resolver"
            }

    # Add extracted entities that weren't resolved (direct values)
    for entity_type, entity_value in extracted_entities.items():
        # Map entity type to field name
        field_name = entity_type
        if entity_type in ["equipment", "equipment_name"]:
            field_name = "equipment_id"
        elif entity_type == "fault":
            field_name = "fault_id"
        elif entity_type == "work_order":
            field_name = "work_order_id"
        elif entity_type in ["part", "part_name"]:
            field_name = "part_id"
        elif entity_type == "supplier":
            field_name = "supplier_id"

        # Only add if not already in prefill (resolved takes precedence)
        if field_name not in prefill and entity_value:
            # Check if it's a UUID (already resolved) or needs resolution
            if isinstance(entity_value, str) and len(entity_value) == 36 and "-" in entity_value:
                prefill[field_name] = {
                    "value": entity_value,
                    "confidence": 0.95,
                    "source": "extracted_uuid"
                }
            else:
                # Add as extracted value (might need user confirmation)
                prefill[entity_type] = {
                    "value": entity_value,
                    "confidence": 0.80,
                    "source": "nlp_extracted"
                }

    # Apply priority mapping if priority extracted
    if "priority" in extracted_entities or "priority_indicator" in extracted_entities:
        raw_priority = extracted_entities.get("priority") or extracted_entities.get("priority_indicator")
        if raw_priority:
            mapped_priority, confidence = map_priority(raw_priority)
            if mapped_priority:
                prefill["priority"] = {
                    "value": mapped_priority,
                    "confidence": confidence,
                    "source": "keyword_map"
                }

    # =========================================================================
    # STEP 5: Identify missing required fields
    # =========================================================================
    for field in required_fields:
        if field not in prefill and field not in resolved_entities:
            # Check if it's an _id field that might be in resolved entities without _id suffix
            base_field = field.replace("_id", "")
            if base_field not in prefill:
                missing_required_fields.append(field)

    # =========================================================================
    # STEP 6: Determine readiness
    # =========================================================================
    ready_to_commit = (
        len(missing_required_fields) == 0 and
        len(ambiguities) == 0 and
        not role_blocked and
        len(errors) == 0
    )

    return {
        "action_id": action_id,
        "lens": lens,
        "ready_to_commit": ready_to_commit,
        "prefill": prefill,
        "resolved_entities": resolved_entities,
        "missing_required_fields": missing_required_fields,
        "ambiguities": ambiguities,
        "role_blocked": role_blocked,
        "errors": errors,
        "extracted_entities": extracted_entities,  # For debugging
        "query_text": query_text,  # For debugging
    }


__all__ = [
    "build_mutation_preview",
    "build_prepare_response",
    "validate_mutation_preview",
    "extract_entity_value",
    "apply_compose_template",
    "apply_value_map",
    "apply_date_parsing",
    "generate_backend_auto_value",
    "map_priority",
    "PRIORITY_SYNONYMS",
    # Lens-specific entity resolvers
    "resolve_work_order_entities",
    "resolve_fault_entities",
    "resolve_equipment_entities",
    "resolve_part_entities",
    "resolve_inventory_entities",
    "resolve_certificate_entities",
    "resolve_handover_entities",
    "resolve_hours_of_rest_entities",
    "resolve_warranty_entities",
    "resolve_shopping_list_entities",
    "resolve_email_entities",
    "resolve_receiving_entities",
    "resolve_entities_for_lens",
    "LENS_ENTITY_RESOLVERS",
    # Generic prepare function
    "prepare_action",
]

"""
JSON Schema Validator

Validates action payloads against JSON schemas.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from .validation_result import ValidationResult

try:
    import jsonschema
    from jsonschema import validate, ValidationError as JSONSchemaValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


def validate_schema(
    payload: Dict[str, Any],
    schema_file: Optional[str],
    action_id: str,
) -> ValidationResult:
    """
    Validate payload against JSON schema if schema_file is defined.

    Args:
        payload: Action payload to validate
        schema_file: Name of JSON schema file (optional)
        action_id: ID of the action being validated

    Returns:
        ValidationResult indicating success or failure
    """
    # If no schema file specified, skip validation
    if not schema_file:
        return ValidationResult.success()

    # Check if jsonschema library is available
    if not JSONSCHEMA_AVAILABLE:
        # Log warning but don't fail - schema validation is optional
        return ValidationResult.success(
            context={"warning": "jsonschema library not available, schema validation skipped"}
        )

    try:
        # Construct path to schema file
        schema_dir = Path(__file__).parent.parent / "schemas"
        schema_path = schema_dir / schema_file

        # Check if schema file exists
        if not schema_path.exists():
            # Log warning but don't fail - missing schema shouldn't block actions
            return ValidationResult.success(
                context={"warning": f"Schema file {schema_file} not found, validation skipped"}
            )

        # Load schema
        with open(schema_path, "r") as f:
            schema = json.load(f)

        # Validate payload against schema
        validate(instance=payload, schema=schema)

        # Validation passed
        return ValidationResult.success()

    except JSONSchemaValidationError as e:
        # Schema validation failed
        return ValidationResult.failure(
            error_code="schema_validation_failed",
            message=f"Payload validation failed for action '{action_id}': {e.message}",
            details={
                "schema_file": schema_file,
                "validation_error": e.message,
                "failed_path": list(e.path) if e.path else None,
            },
        )

    except json.JSONDecodeError as e:
        # Schema file is invalid JSON
        return ValidationResult.failure(
            error_code="invalid_schema",
            message=f"Schema file {schema_file} contains invalid JSON: {str(e)}",
        )

    except Exception as e:
        # Other unexpected errors
        return ValidationResult.failure(
            error_code="schema_validation_error",
            message=f"Schema validation error: {str(e)}",
        )


__all__ = ["validate_schema"]

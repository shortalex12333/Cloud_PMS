"""
Schema Validator
================

Validates pipeline responses against JSON schema contract.

Usage:
    validator = SchemaValidator()
    result = validator.validate(response_data)
    if not result.valid:
        log_validation_failure(result.errors)
"""

import json
import jsonschema
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of schema validation."""
    valid: bool
    errors: List[str]
    schema_version: str


class SchemaValidator:
    """
    Validates responses against JSON schema contracts.

    Schemas are loaded from /contracts directory.
    """

    def __init__(self, contracts_dir: str = None):
        if contracts_dir is None:
            # Default: <repo>/contracts
            contracts_dir = Path(__file__).parent.parent.parent / "contracts"
        self.contracts_dir = Path(contracts_dir)
        self._schemas: Dict[str, dict] = {}
        self._load_schemas()

    def _load_schemas(self):
        """Load all schema files from contracts directory."""
        if not self.contracts_dir.exists():
            logger.warning(f"Contracts directory not found: {self.contracts_dir}")
            return

        for schema_file in self.contracts_dir.glob("*.schema.json"):
            schema_name = schema_file.stem.replace(".schema", "")
            try:
                with open(schema_file) as f:
                    self._schemas[schema_name] = json.load(f)
                logger.info(f"Loaded schema: {schema_name}")
            except Exception as e:
                logger.error(f"Failed to load schema {schema_file}: {e}")

    def validate(self, data: Dict, schema_name: str = "pipeline_response") -> ValidationResult:
        """
        Validate data against a named schema.

        Args:
            data: Response data to validate
            schema_name: Name of schema (e.g., "pipeline_response")

        Returns:
            ValidationResult with valid flag and any errors
        """
        if schema_name not in self._schemas:
            return ValidationResult(
                valid=False,
                errors=[f"Schema not found: {schema_name}"],
                schema_version="unknown"
            )

        schema = self._schemas[schema_name]
        schema_version = schema.get("$id", "unknown")

        try:
            jsonschema.validate(instance=data, schema=schema)
            return ValidationResult(
                valid=True,
                errors=[],
                schema_version=schema_version
            )
        except jsonschema.ValidationError as e:
            # Collect all errors
            validator = jsonschema.Draft202012Validator(schema)
            errors = [
                f"{'.'.join(str(p) for p in error.absolute_path)}: {error.message}"
                for error in validator.iter_errors(data)
            ]
            return ValidationResult(
                valid=False,
                errors=errors[:10],  # Limit to first 10 errors
                schema_version=schema_version
            )

    def validate_pipeline_response(self, data: Dict) -> ValidationResult:
        """Convenience method for pipeline response validation."""
        return self.validate(data, "pipeline_response")


# Singleton instance
_validator: Optional[SchemaValidator] = None


def get_validator() -> SchemaValidator:
    """Get or create schema validator instance."""
    global _validator
    if _validator is None:
        _validator = SchemaValidator()
    return _validator

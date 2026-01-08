"""
Validation Result Types

Defines the result types for validation operations in the Action Router.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error."""

    error_code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.field:
            result["field"] = self.field
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class ValidationResult:
    """
    Result of a validation operation.

    Attributes:
        valid: Whether validation passed
        error: Error details if validation failed
        context: Additional context extracted during validation
    """

    valid: bool
    error: Optional[ValidationError] = None
    context: Optional[Dict[str, Any]] = None

    @classmethod
    def success(cls, context: Optional[Dict[str, Any]] = None) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(valid=True, context=context or {})

    @classmethod
    def failure(
        cls,
        error_code: str,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(
            valid=False,
            error=ValidationError(
                error_code=error_code,
                message=message,
                field=field,
                details=details,
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"valid": self.valid}
        if self.error:
            result["error"] = self.error.to_dict()
        if self.context:
            result["context"] = self.context
        return result


__all__ = ["ValidationResult", "ValidationError"]

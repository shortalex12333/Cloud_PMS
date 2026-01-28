"""
CelesteOS API Validators
========================

Centralized validation libraries for security-critical operations.

Modules:
- ownership: Entity ownership validation (yacht isolation)
"""

from .ownership import (
    OwnershipValidator,
    ensure_owned,
    ensure_all_owned,
    NotFoundError,
    OwnershipValidationError,
)

__all__ = [
    'OwnershipValidator',
    'ensure_owned',
    'ensure_all_owned',
    'NotFoundError',
    'OwnershipValidationError',
]

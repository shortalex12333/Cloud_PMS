"""
Custom exceptions for CelesteOS Cloud API
Standardized error responses
"""

from fastapi import status
from typing import Optional, Dict, Any


class CelesteAPIException(Exception):
    """Base exception for all CelesteOS API errors"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


# Authentication Errors

class AuthenticationError(CelesteAPIException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_FAILED",
            details=details
        )


class TokenExpiredError(CelesteAPIException):
    """Raised when JWT token has expired"""

    def __init__(self):
        super().__init__(
            message="Token has expired",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_EXPIRED"
        )


class TokenInvalidError(CelesteAPIException):
    """Raised when JWT token is invalid"""

    def __init__(self):
        super().__init__(
            message="Invalid token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_INVALID"
        )


class YachtSignatureError(CelesteAPIException):
    """Raised when yacht signature is invalid"""

    def __init__(self):
        super().__init__(
            message="Invalid yacht signature",
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="YACHT_SIGNATURE_INVALID"
        )


# Authorization Errors

class PermissionDeniedError(CelesteAPIException):
    """Raised when user lacks required permissions"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED"
        )


# Resource Errors

class ResourceNotFoundError(CelesteAPIException):
    """Raised when requested resource doesn't exist"""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "id": resource_id}
        )


class ResourceAlreadyExistsError(CelesteAPIException):
    """Raised when resource already exists"""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} already exists",
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_EXISTS",
            details={"resource": resource, "identifier": identifier}
        )


# Validation Errors

class ValidationError(CelesteAPIException):
    """Raised when request validation fails"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details
        )


class SHA256MismatchError(CelesteAPIException):
    """Raised when SHA256 hash doesn't match"""

    def __init__(self, expected: str, computed: str):
        super().__init__(
            message="SHA256 hash mismatch",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="SHA256_MISMATCH",
            details={"expected": expected, "computed": computed}
        )


# Upload Errors

class UploadSessionNotFoundError(CelesteAPIException):
    """Raised when upload session doesn't exist"""

    def __init__(self, upload_id: str):
        super().__init__(
            message="Upload session not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="UPLOAD_SESSION_NOT_FOUND",
            details={"upload_id": upload_id}
        )


class IncompleteUploadError(CelesteAPIException):
    """Raised when upload is incomplete"""

    def __init__(self, chunks_uploaded: int, total_chunks: int):
        super().__init__(
            message="Upload incomplete",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="UPLOAD_INCOMPLETE",
            details={
                "chunks_uploaded": chunks_uploaded,
                "total_chunks": total_chunks
            }
        )


class DuplicateFileError(CelesteAPIException):
    """Raised when file with same SHA256 already exists"""

    def __init__(self, document_id: str):
        super().__init__(
            message="File already exists",
            status_code=status.HTTP_200_OK,  # Not an error, but signals duplicate
            error_code="DUPLICATE_FILE",
            details={"document_id": document_id}
        )


# Rate Limiting

class RateLimitExceededError(CelesteAPIException):
    """Raised when rate limit is exceeded"""

    def __init__(self, retry_after: int):
        super().__init__(
            message="Rate limit exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after_seconds": retry_after}
        )


# Storage Errors

class StorageError(CelesteAPIException):
    """Raised when storage operation fails"""

    def __init__(self, message: str):
        super().__init__(
            message=f"Storage error: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="STORAGE_ERROR"
        )

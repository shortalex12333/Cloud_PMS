"""
Authentication and authorization middleware for CelesteOS Ingestion API
"""
import jwt
from typing import Optional
from uuid import UUID
from fastapi import Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
import logging

from config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()


class YachtAuth:
    """Handles yacht signature and user authentication"""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    async def validate_yacht_signature(
        self,
        x_yacht_signature: str = Header(..., alias="X-Yacht-Signature")
    ) -> UUID:
        """
        Validate yacht signature and return yacht_id

        Raises:
            HTTPException: If signature is invalid or yacht not found
        """
        try:
            # Look up yacht by signature in yachts table
            result = self.supabase.table("yachts").select("id, status").eq(
                "signature", x_yacht_signature
            ).execute()

            if not result.data or len(result.data) == 0:
                logger.warning(f"Invalid yacht signature attempted: {x_yacht_signature[:8]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid yacht signature"
                )

            yacht = result.data[0]

            # Check yacht status
            if yacht.get("status") != "active":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Yacht account is not active"
                )

            yacht_id = UUID(yacht["id"])
            logger.info(f"Yacht authenticated: {yacht_id}")
            return yacht_id

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating yacht signature: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error validating yacht signature"
            )

    async def validate_jwt_token(
        self,
        authorization: Optional[str] = Header(None)
    ) -> Optional[dict]:
        """
        Validate JWT token (optional for some endpoints like init)

        Returns:
            Dict with user_id, yacht_id, role if valid, None if no token provided
        """
        if not authorization:
            return None

        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )

        token = authorization.replace("Bearer ", "")

        try:
            # Decode JWT using Supabase JWT secret
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": True}
            )

            user_id = payload.get("sub")
            yacht_id = payload.get("yacht_id")
            role = payload.get("role")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )

            return {
                "user_id": user_id,
                "yacht_id": yacht_id,
                "role": role,
                "payload": payload
            }

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Error validating JWT: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error validating token"
            )

    async def validate_upload_headers(
        self,
        upload_id: str = Header(..., alias="Upload-ID"),
        chunk_index: int = Header(..., alias="Chunk-Index"),
        chunk_sha256: str = Header(..., alias="Chunk-SHA256")
    ) -> dict:
        """
        Validate upload-specific headers

        Returns:
            Dict with validated header values
        """
        # Validate upload_id is valid UUID
        try:
            upload_uuid = UUID(upload_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Upload-ID format"
            )

        # Validate chunk_index
        if chunk_index < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chunk-Index must be non-negative"
            )

        # Validate chunk_sha256 format
        if len(chunk_sha256) != 64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Chunk-SHA256 format"
            )

        return {
            "upload_id": upload_uuid,
            "chunk_index": chunk_index,
            "chunk_sha256": chunk_sha256.lower()
        }


def check_file_extension(filename: str) -> bool:
    """Check if file extension is allowed"""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in settings.ALLOWED_FILE_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other attacks
    """
    import os
    # Get just the filename, no path components
    filename = os.path.basename(filename)
    # Remove or replace dangerous characters
    filename = filename.replace("..", "")
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    return filename

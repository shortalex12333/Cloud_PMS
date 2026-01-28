"""
CelesteOS API - Idempotency Middleware
======================================

Ensures MUTATE/SIGNED/ADMIN actions are idempotent.

Security invariants:
1. Idempotency keys are scoped to yacht_id (no cross-tenant collisions)
2. Request hash prevents replay attacks with different payloads
3. Same key + same hash = return cached response
4. Same key + different hash = error (409 Conflict)
5. TTL-based expiry (24 hours default)

Usage:
    from middleware.idempotency import IdempotencyManager, require_idempotency_key

    # In handler
    idempotency = IdempotencyManager(master_client)

    # Check for existing result
    prior = idempotency.check(
        key=request.idempotency_key,
        yacht_id=ctx.yacht_id,
        action_id="create_work_order",
        request_hash=hash_request(request.payload)
    )
    if prior.completed:
        return prior.response

    # Execute action
    result = do_action()

    # Record result
    idempotency.complete(
        key=request.idempotency_key,
        yacht_id=ctx.yacht_id,
        status=200,
        response_summary={"id": result.id}
    )
"""

from typing import Any, Dict, Optional, NamedTuple
from dataclasses import dataclass
import hashlib
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ActionGroup(Enum):
    """Action groups that require idempotency."""
    READ = "READ"           # No idempotency required
    MUTATE = "MUTATE"       # Requires idempotency
    SIGNED = "SIGNED"       # Requires idempotency + signature
    ADMIN = "ADMIN"         # Requires idempotency + elevated permissions


@dataclass
class IdempotencyCheckResult:
    """Result of idempotency check."""
    found: bool             # Key exists in database
    completed: bool         # Action has completed
    hash_mismatch: bool     # Different request with same key
    response_status: Optional[int] = None
    response_summary: Optional[Dict] = None

    @property
    def should_execute(self) -> bool:
        """Should the action be executed?"""
        return not self.found or (self.found and not self.completed and not self.hash_mismatch)

    @property
    def is_replay(self) -> bool:
        """Is this a replay of a completed request?"""
        return self.found and self.completed and not self.hash_mismatch


class IdempotencyConflictError(Exception):
    """
    Raised when same idempotency key is used with different request.

    Returns 409 Conflict.
    """
    def __init__(self, key: str, message: str = None):
        self.key = key
        self.message = message or f"Idempotency key '{key}' already used with different request"
        super().__init__(self.message)


class IdempotencyKeyMissingError(Exception):
    """
    Raised when idempotency key is required but not provided.

    Returns 400 Bad Request.
    """
    def __init__(self, action_id: str):
        self.action_id = action_id
        self.message = f"Idempotency-Key header required for action '{action_id}'"
        super().__init__(self.message)


class IdempotencyManager:
    """
    Manages idempotency records for MUTATE/SIGNED/ADMIN actions.

    All operations are yacht-scoped to prevent cross-tenant collisions.
    """

    DEFAULT_TTL_HOURS = 24

    def __init__(self, master_client: Any):
        """
        Initialize with MASTER database client.

        Idempotency records are stored in MASTER DB, not tenant DB,
        to ensure consistency across tenant operations.
        """
        if not master_client:
            raise ValueError("master_client is required")
        self.db = master_client

    def check(
        self,
        key: str,
        yacht_id: str,
        action_id: str,
        request_hash: str,
    ) -> IdempotencyCheckResult:
        """
        Check if idempotent request already exists.

        Args:
            key: Idempotency key from request header
            yacht_id: Yacht UUID (from ctx.yacht_id)
            action_id: Action being executed
            request_hash: Hash of request payload

        Returns:
            IdempotencyCheckResult with check outcome

        Raises:
            IdempotencyConflictError: Same key with different request (409)
        """
        if not key:
            # No key = no idempotency check
            return IdempotencyCheckResult(
                found=False,
                completed=False,
                hash_mismatch=False,
            )

        try:
            # Query existing record
            result = self.db.rpc(
                'check_idempotency',
                {
                    'p_key': key,
                    'p_yacht_id': yacht_id,
                    'p_action_id': action_id,
                    'p_request_hash': request_hash,
                }
            ).execute()

            if not result.data or len(result.data) == 0:
                return IdempotencyCheckResult(
                    found=False,
                    completed=False,
                    hash_mismatch=False,
                )

            row = result.data[0]

            if row.get('hash_mismatch'):
                logger.warning(
                    f"[Idempotency] Hash mismatch: key={key[:8]}..., "
                    f"yacht={yacht_id[:8]}..., action={action_id}"
                )
                raise IdempotencyConflictError(key)

            check_result = IdempotencyCheckResult(
                found=row.get('found', False),
                completed=row.get('completed', False),
                hash_mismatch=False,
                response_status=row.get('response_status'),
                response_summary=row.get('response_summary'),
            )

            if check_result.is_replay:
                logger.info(
                    f"[Idempotency] Replay detected: key={key[:8]}..., "
                    f"yacht={yacht_id[:8]}..., action={action_id}"
                )

            return check_result

        except IdempotencyConflictError:
            raise
        except Exception as e:
            # Log but don't fail - idempotency is best-effort
            logger.error(f"[Idempotency] Check failed: {e}")
            return IdempotencyCheckResult(
                found=False,
                completed=False,
                hash_mismatch=False,
            )

    def create(
        self,
        key: str,
        yacht_id: str,
        action_id: str,
        user_id: str,
        request_hash: str,
        ttl_hours: int = None,
    ) -> bool:
        """
        Create idempotency record at request start.

        Args:
            key: Idempotency key
            yacht_id: Yacht UUID
            action_id: Action being executed
            user_id: User UUID
            request_hash: Hash of request payload
            ttl_hours: TTL in hours (default 24)

        Returns:
            True if record created, False if already exists
        """
        if not key:
            return False

        ttl = ttl_hours or self.DEFAULT_TTL_HOURS

        try:
            result = self.db.rpc(
                'create_idempotency_record',
                {
                    'p_key': key,
                    'p_yacht_id': yacht_id,
                    'p_action_id': action_id,
                    'p_user_id': user_id,
                    'p_request_hash': request_hash,
                    'p_ttl_hours': ttl,
                }
            ).execute()

            created = result.data if result.data else False
            logger.debug(
                f"[Idempotency] Create: key={key[:8]}..., created={created}"
            )
            return created

        except Exception as e:
            logger.error(f"[Idempotency] Create failed: {e}")
            return False

    def complete(
        self,
        key: str,
        yacht_id: str,
        status: int,
        response_summary: Dict[str, Any],
        response_hash: str = None,
    ) -> None:
        """
        Mark idempotency record as completed.

        Args:
            key: Idempotency key
            yacht_id: Yacht UUID
            status: HTTP status code
            response_summary: Safe subset of response (no sensitive data)
            response_hash: Optional hash of full response
        """
        if not key:
            return

        try:
            self.db.rpc(
                'complete_idempotency_record',
                {
                    'p_key': key,
                    'p_yacht_id': yacht_id,
                    'p_status': status,
                    'p_summary': response_summary,
                    'p_response_hash': response_hash,
                }
            ).execute()

            logger.debug(
                f"[Idempotency] Completed: key={key[:8]}..., status={status}"
            )

        except Exception as e:
            logger.error(f"[Idempotency] Complete failed: {e}")

    def cleanup_expired(self) -> int:
        """
        Remove expired idempotency records.

        Should be called periodically (e.g., daily cron).

        Returns:
            Number of records deleted
        """
        try:
            result = self.db.rpc('cleanup_expired_idempotency_records').execute()
            count = result.data if result.data else 0
            logger.info(f"[Idempotency] Cleanup: deleted {count} expired records")
            return count
        except Exception as e:
            logger.error(f"[Idempotency] Cleanup failed: {e}")
            return 0


# ============================================================================
# Helper Functions
# ============================================================================


def hash_request(payload: Dict[str, Any], exclude_keys: list = None) -> str:
    """
    Create deterministic hash of request payload.

    Args:
        payload: Request payload dict
        exclude_keys: Keys to exclude from hash (e.g., timestamps)

    Returns:
        SHA256 hash (first 32 chars)
    """
    # Remove excluded keys
    exclude = set(exclude_keys or [])
    exclude.add('idempotency_key')  # Never include key in hash

    filtered = {k: v for k, v in payload.items() if k not in exclude}

    # Sort keys for deterministic ordering
    serialized = json.dumps(filtered, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:32]


def require_idempotency_key(
    idempotency_key: Optional[str],
    action_id: str,
    action_group: ActionGroup,
) -> str:
    """
    Validate that idempotency key is provided for mutating actions.

    Args:
        idempotency_key: Key from Idempotency-Key header
        action_id: Action being executed
        action_group: Group of action (READ, MUTATE, SIGNED, ADMIN)

    Returns:
        The idempotency key

    Raises:
        IdempotencyKeyMissingError: Key required but not provided (400)
    """
    # READ actions don't require idempotency
    if action_group == ActionGroup.READ:
        return idempotency_key or ""

    # MUTATE, SIGNED, ADMIN require idempotency key
    if not idempotency_key:
        raise IdempotencyKeyMissingError(action_id)

    # Validate key format (UUID or reasonable string)
    if len(idempotency_key) < 8 or len(idempotency_key) > 128:
        raise IdempotencyKeyMissingError(action_id)

    return idempotency_key


def safe_response_summary(response: Dict[str, Any], max_depth: int = 3) -> Dict[str, Any]:
    """
    Create safe summary of response for idempotency storage.

    Removes potentially sensitive fields and limits depth.
    """
    SENSITIVE_KEYS = {
        'token', 'password', 'secret', 'key', 'auth',
        'signature', 'credential', 'signed_url',
    }

    def sanitize(obj, depth=0):
        if depth > max_depth:
            return "[truncated]"

        if isinstance(obj, dict):
            return {
                k: sanitize(v, depth + 1)
                for k, v in obj.items()
                if not any(s in k.lower() for s in SENSITIVE_KEYS)
            }
        elif isinstance(obj, list):
            if len(obj) > 10:
                return [sanitize(x, depth + 1) for x in obj[:10]] + [f"...{len(obj) - 10} more"]
            return [sanitize(x, depth + 1) for x in obj]
        elif isinstance(obj, str) and len(obj) > 200:
            return obj[:200] + "..."
        return obj

    return sanitize(response)

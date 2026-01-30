"""
Document Comment Handlers
==========================

Handlers for document comment actions (Document Lens v2).

ACTIONS:
- add_document_comment: Add comment to document
- update_document_comment: Edit own comment
- delete_document_comment: Soft-delete comment
- list_document_comments: Get comments for document (with threading)

PATTERN: Mirrors pms_attachment_comments handlers from Work Order Lens.
MVP SCOPE: Document-level comments only (no page/section-specific).
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class DocumentCommentHandlers:
    """Document comment domain handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def add_document_comment(
        self,
        document_id: str,
        yacht_id: str,
        user_id: str,
        comment: str,
        parent_comment_id: Optional[str] = None,
    ) -> Dict:
        """
        Add comment to document.

        Args:
            document_id: UUID of document
            yacht_id: UUID of yacht
            user_id: UUID of user
            comment: Comment text
            parent_comment_id: Optional parent comment for threading

        Returns:
            Response dict with comment_id or error
        """
        try:
            # Validate comment not empty
            if not comment or not comment.strip():
                return {
                    "status": "error",
                    "error_code": "VALIDATION_ERROR",
                    "message": "Comment cannot be empty",
                }

            # Validate document exists and not deleted
            doc_result = (
                self.db.table("doc_metadata")
                .select("id, deleted_at")
                .eq("id", document_id)
                .eq("yacht_id", yacht_id)
                .maybe_single()
                .execute()
            )

            if not doc_result or not doc_result.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Document not found: {document_id}",
                }

            if doc_result.data.get("deleted_at"):
                return {
                    "status": "error",
                    "error_code": "INVALID_STATE",
                    "message": "Cannot comment on deleted document",
                }

            # Validate parent comment if provided
            if parent_comment_id:
                parent_result = (
                    self.db.table("doc_metadata_comments")
                    .select("id")
                    .eq("id", parent_comment_id)
                    .eq("document_id", document_id)
                    .is_("deleted_at", "null")
                    .maybe_single()
                    .execute()
                )

                if not parent_result or not parent_result.data:
                    return {
                        "status": "error",
                        "error_code": "NOT_FOUND",
                        "message": f"Parent comment not found: {parent_comment_id}",
                    }

            # Create comment
            now = datetime.now(timezone.utc).isoformat()
            comment_data = {
                "yacht_id": yacht_id,
                "document_id": document_id,
                "comment": comment.strip(),
                "created_by": user_id,
                "created_at": now,
                "parent_comment_id": parent_comment_id,
            }

            result = self.db.table("doc_metadata_comments").insert(comment_data).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "INSERT_FAILED",
                    "message": "Failed to create comment",
                }

            comment_id = result.data[0]["id"]
            author_department = result.data[0].get("author_department")

            logger.info(f"Document comment created: {comment_id} on document {document_id}")

            return {
                "status": "success",
                "comment_id": comment_id,
                "document_id": document_id,
                "author_department": author_department,
                "created_at": now,
            }

        except Exception as e:
            logger.error(f"add_document_comment failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    async def update_document_comment(
        self,
        comment_id: str,
        yacht_id: str,
        user_id: str,
        comment: str,
    ) -> Dict:
        """
        Update comment text.

        Args:
            comment_id: UUID of comment
            yacht_id: UUID of yacht
            user_id: UUID of user (must be owner or admin)
            comment: New comment text

        Returns:
            Response dict with success or error
        """
        try:
            # Validate comment not empty
            if not comment or not comment.strip():
                return {
                    "status": "error",
                    "error_code": "VALIDATION_ERROR",
                    "message": "Comment cannot be empty",
                }

            # Get existing comment
            existing = (
                self.db.table("doc_metadata_comments")
                .select("id, created_by, deleted_at")
                .eq("id", comment_id)
                .eq("yacht_id", yacht_id)
                .maybe_single()
                .execute()
            )

            if not existing or not existing.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Comment not found: {comment_id}",
                }

            if existing.data.get("deleted_at"):
                return {
                    "status": "error",
                    "error_code": "INVALID_STATE",
                    "message": "Cannot edit deleted comment",
                }

            # Check ownership (RLS also enforces this, but explicit check for better error message)
            if existing.data.get("created_by") != user_id:
                # Check if user is admin/captain/chief_engineer
                role_result = (
                    self.db.table("auth_users_roles")
                    .select("role")
                    .eq("user_id", user_id)
                    .eq("yacht_id", yacht_id)
                    .maybe_single()
                    .execute()
                )

                role = role_result.data.get("role") if role_result and role_result.data else None
                if role not in ("admin", "captain", "chief_engineer", "manager"):
                    return {
                        "status": "error",
                        "error_code": "FORBIDDEN",
                        "message": "Can only edit your own comments",
                    }

            # Update comment
            now = datetime.now(timezone.utc).isoformat()
            update_result = (
                self.db.table("doc_metadata_comments")
                .update({
                    "comment": comment.strip(),
                    "updated_by": user_id,
                    "updated_at": now,
                })
                .eq("id", comment_id)
                .execute()
            )

            if not update_result.data:
                return {
                    "status": "error",
                    "error_code": "UPDATE_FAILED",
                    "message": "Failed to update comment",
                }

            logger.info(f"Document comment updated: {comment_id}")

            return {
                "status": "success",
                "comment_id": comment_id,
                "updated_at": now,
            }

        except Exception as e:
            logger.error(f"update_document_comment failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    async def delete_document_comment(
        self,
        comment_id: str,
        yacht_id: str,
        user_id: str,
    ) -> Dict:
        """
        Soft-delete comment.

        Args:
            comment_id: UUID of comment
            yacht_id: UUID of yacht
            user_id: UUID of user (must be owner or admin)

        Returns:
            Response dict with success or error
        """
        try:
            # Get existing comment
            existing = (
                self.db.table("doc_metadata_comments")
                .select("id, created_by, deleted_at")
                .eq("id", comment_id)
                .eq("yacht_id", yacht_id)
                .maybe_single()
                .execute()
            )

            if not existing or not existing.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Comment not found: {comment_id}",
                }

            if existing.data.get("deleted_at"):
                return {
                    "status": "error",
                    "error_code": "INVALID_STATE",
                    "message": "Comment already deleted",
                }

            # Check ownership
            if existing.data.get("created_by") != user_id:
                role_result = (
                    self.db.table("auth_users_roles")
                    .select("role")
                    .eq("user_id", user_id)
                    .eq("yacht_id", yacht_id)
                    .maybe_single()
                    .execute()
                )

                role = role_result.data.get("role") if role_result and role_result.data else None
                if role not in ("admin", "captain", "chief_engineer", "manager"):
                    return {
                        "status": "error",
                        "error_code": "FORBIDDEN",
                        "message": "Can only delete your own comments",
                    }

            # Soft delete
            now = datetime.now(timezone.utc).isoformat()
            delete_result = (
                self.db.table("doc_metadata_comments")
                .update({
                    "deleted_by": user_id,
                    "deleted_at": now,
                })
                .eq("id", comment_id)
                .execute()
            )

            if not delete_result.data:
                return {
                    "status": "error",
                    "error_code": "DELETE_FAILED",
                    "message": "Failed to delete comment",
                }

            logger.info(f"Document comment deleted: {comment_id}")

            return {
                "status": "success",
                "comment_id": comment_id,
                "deleted_at": now,
            }

        except Exception as e:
            logger.error(f"delete_document_comment failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    async def list_document_comments(
        self,
        document_id: str,
        yacht_id: str,
        include_threads: bool = True,
    ) -> Dict:
        """
        List comments for document.

        Args:
            document_id: UUID of document
            yacht_id: UUID of yacht
            include_threads: If True, structure as threaded tree

        Returns:
            Response dict with comments array
        """
        try:
            # Verify document exists
            doc_result = (
                self.db.table("doc_metadata")
                .select("id")
                .eq("id", document_id)
                .eq("yacht_id", yacht_id)
                .maybe_single()
                .execute()
            )

            if not doc_result or not doc_result.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Document not found: {document_id}",
                }

            # Get all comments for document
            result = (
                self.db.table("doc_metadata_comments")
                .select("id, comment, created_by, created_at, updated_at, parent_comment_id, author_department")
                .eq("document_id", document_id)
                .eq("yacht_id", yacht_id)
                .is_("deleted_at", "null")
                .order("created_at", desc=False)
                .execute()
            )

            comments = result.data or []

            # Build threaded structure if requested
            if include_threads and comments:
                comments = self._build_comment_tree(comments)

            return {
                "status": "success",
                "document_id": document_id,
                "comments": comments,
                "total_count": len(result.data or []),
            }

        except Exception as e:
            logger.error(f"list_document_comments failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    def _build_comment_tree(self, comments: List[Dict]) -> List[Dict]:
        """Build threaded comment tree from flat list."""
        # Create lookup map
        comment_map = {c["id"]: {**c, "replies": []} for c in comments}
        root_comments = []

        for comment in comments:
            parent_id = comment.get("parent_comment_id")
            if parent_id and parent_id in comment_map:
                # Add as reply to parent
                comment_map[parent_id]["replies"].append(comment_map[comment["id"]])
            else:
                # Root-level comment
                root_comments.append(comment_map[comment["id"]])

        return root_comments


# =============================================================================
# ACTION ROUTER ADAPTERS
# =============================================================================

def _add_document_comment_adapter(handlers: DocumentCommentHandlers):
    """Adapter for add_document_comment action."""
    async def handler(params: Dict, context: Dict) -> Dict:
        return await handlers.add_document_comment(
            document_id=params["document_id"],
            yacht_id=context["yacht_id"],
            user_id=context["user_id"],
            comment=params["comment"],
            parent_comment_id=params.get("parent_comment_id"),
        )
    return handler


def _update_document_comment_adapter(handlers: DocumentCommentHandlers):
    """Adapter for update_document_comment action."""
    async def handler(params: Dict, context: Dict) -> Dict:
        return await handlers.update_document_comment(
            comment_id=params["comment_id"],
            yacht_id=context["yacht_id"],
            user_id=context["user_id"],
            comment=params["comment"],
        )
    return handler


def _delete_document_comment_adapter(handlers: DocumentCommentHandlers):
    """Adapter for delete_document_comment action."""
    async def handler(params: Dict, context: Dict) -> Dict:
        return await handlers.delete_document_comment(
            comment_id=params["comment_id"],
            yacht_id=context["yacht_id"],
            user_id=context["user_id"],
        )
    return handler


def _list_document_comments_adapter(handlers: DocumentCommentHandlers):
    """Adapter for list_document_comments action."""
    async def handler(params: Dict, context: Dict) -> Dict:
        return await handlers.list_document_comments(
            document_id=params["document_id"],
            yacht_id=context["yacht_id"],
            include_threads=params.get("include_threads", True),
        )
    return handler


def get_document_comment_handlers(supabase_client) -> Dict:
    """
    Get document comment handler functions for action router registration.

    Returns:
        Dict mapping action_id to handler function
    """
    handlers = DocumentCommentHandlers(supabase_client)

    return {
        "add_document_comment": _add_document_comment_adapter(handlers),
        "update_document_comment": _update_document_comment_adapter(handlers),
        "delete_document_comment": _delete_document_comment_adapter(handlers),
        "list_document_comments": _list_document_comments_adapter(handlers),
    }

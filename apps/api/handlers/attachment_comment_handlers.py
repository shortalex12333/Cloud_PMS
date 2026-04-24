"""
Attachment Comment Handlers
============================

Handlers for pms_attachment_comments — threaded comments on images / files
attached via pms_attachments (polymorphic across work_orders, equipment,
faults, handovers, etc).

ACTIONS:
    add_attachment_comment    — Append a comment to an attachment (optionally a reply)
    update_attachment_comment — Edit own comment (HOD+ can edit any)
    delete_attachment_comment — Soft-delete (owner or HOD+)
    list_attachment_comments  — Threaded fetch for rendering

Pattern mirrors DocumentCommentHandlers (handlers/document_comment_handlers.py)
verbatim — same method surface, same RLS-backed ownership rules, same
thread-tree assembly. Rename map: document → attachment, doc_metadata →
pms_attachments, doc_metadata_comments → pms_attachment_comments,
document_id → attachment_id.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AttachmentCommentHandlers:
    """Attachment comment domain handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    # ── add_attachment_comment ────────────────────────────────────────────

    async def add_attachment_comment(
        self,
        attachment_id: str,
        yacht_id: str,
        user_id: str,
        comment: str,
        parent_comment_id: Optional[str] = None,
    ) -> Dict:
        try:
            if not comment or not comment.strip():
                return {
                    "status": "error",
                    "error_code": "VALIDATION_ERROR",
                    "message": "Comment cannot be empty",
                }

            att_result = (
                self.db.table("pms_attachments")
                .select("id, deleted_at")
                .eq("id", attachment_id)
                .eq("yacht_id", yacht_id)
                .maybe_single()
                .execute()
            )

            if not att_result or not att_result.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Attachment not found: {attachment_id}",
                }

            if att_result.data.get("deleted_at"):
                return {
                    "status": "error",
                    "error_code": "INVALID_STATE",
                    "message": "Cannot comment on deleted attachment",
                }

            if parent_comment_id:
                parent_result = (
                    self.db.table("pms_attachment_comments")
                    .select("id")
                    .eq("id", parent_comment_id)
                    .eq("attachment_id", attachment_id)
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

            now = datetime.now(timezone.utc).isoformat()
            comment_data = {
                "yacht_id": yacht_id,
                "attachment_id": attachment_id,
                "comment": comment.strip(),
                "created_by": user_id,
                "created_at": now,
                "parent_comment_id": parent_comment_id,
            }

            result = (
                self.db.table("pms_attachment_comments")
                .insert(comment_data)
                .execute()
            )

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "INSERT_FAILED",
                    "message": "Failed to create comment",
                }

            comment_id = result.data[0]["id"]
            author_department = result.data[0].get("author_department")

            logger.info(
                f"Attachment comment created: {comment_id} on attachment {attachment_id}"
            )

            return {
                "status": "success",
                "comment_id": comment_id,
                "attachment_id": attachment_id,
                "author_department": author_department,
                "created_at": now,
            }

        except Exception as e:
            logger.error(f"add_attachment_comment failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # ── update_attachment_comment ─────────────────────────────────────────

    async def update_attachment_comment(
        self,
        comment_id: str,
        yacht_id: str,
        user_id: str,
        comment: str,
    ) -> Dict:
        try:
            if not comment or not comment.strip():
                return {
                    "status": "error",
                    "error_code": "VALIDATION_ERROR",
                    "message": "Comment cannot be empty",
                }

            existing = (
                self.db.table("pms_attachment_comments")
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

            if existing.data.get("created_by") != user_id:
                role_result = (
                    self.db.table("auth_users_roles")
                    .select("role")
                    .eq("user_id", user_id)
                    .eq("yacht_id", yacht_id)
                    .maybe_single()
                    .execute()
                )
                role = (
                    role_result.data.get("role")
                    if role_result and role_result.data
                    else None
                )
                if role not in ("admin", "captain", "chief_engineer", "manager"):
                    return {
                        "status": "error",
                        "error_code": "FORBIDDEN",
                        "message": "Can only edit your own comments",
                    }

            now = datetime.now(timezone.utc).isoformat()
            update_result = (
                self.db.table("pms_attachment_comments")
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

            logger.info(f"Attachment comment updated: {comment_id}")

            return {
                "status": "success",
                "comment_id": comment_id,
                "updated_at": now,
            }

        except Exception as e:
            logger.error(f"update_attachment_comment failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # ── delete_attachment_comment ─────────────────────────────────────────

    async def delete_attachment_comment(
        self,
        comment_id: str,
        yacht_id: str,
        user_id: str,
    ) -> Dict:
        try:
            existing = (
                self.db.table("pms_attachment_comments")
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

            if existing.data.get("created_by") != user_id:
                role_result = (
                    self.db.table("auth_users_roles")
                    .select("role")
                    .eq("user_id", user_id)
                    .eq("yacht_id", yacht_id)
                    .maybe_single()
                    .execute()
                )
                role = (
                    role_result.data.get("role")
                    if role_result and role_result.data
                    else None
                )
                if role not in ("admin", "captain", "chief_engineer", "manager"):
                    return {
                        "status": "error",
                        "error_code": "FORBIDDEN",
                        "message": "Can only delete your own comments",
                    }

            now = datetime.now(timezone.utc).isoformat()
            delete_result = (
                self.db.table("pms_attachment_comments")
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

            logger.info(f"Attachment comment deleted: {comment_id}")

            return {
                "status": "success",
                "comment_id": comment_id,
                "deleted_at": now,
            }

        except Exception as e:
            logger.error(f"delete_attachment_comment failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # ── list_attachment_comments ──────────────────────────────────────────

    async def list_attachment_comments(
        self,
        attachment_id: str,
        yacht_id: str,
        include_threads: bool = True,
    ) -> Dict:
        try:
            att_result = (
                self.db.table("pms_attachments")
                .select("id")
                .eq("id", attachment_id)
                .eq("yacht_id", yacht_id)
                .maybe_single()
                .execute()
            )

            if not att_result or not att_result.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Attachment not found: {attachment_id}",
                }

            result = (
                self.db.table("pms_attachment_comments")
                .select(
                    "id, comment, created_by, created_at, updated_at, "
                    "parent_comment_id, author_department"
                )
                .eq("attachment_id", attachment_id)
                .eq("yacht_id", yacht_id)
                .is_("deleted_at", "null")
                .order("created_at", desc=False)
                .execute()
            )

            comments = result.data or []

            if include_threads and comments:
                comments = self._build_comment_tree(comments)

            return {
                "status": "success",
                "attachment_id": attachment_id,
                "comments": comments,
                "total_count": len(result.data or []),
            }

        except Exception as e:
            logger.error(f"list_attachment_comments failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    def _build_comment_tree(self, comments: List[Dict]) -> List[Dict]:
        """Build threaded comment tree from flat list."""
        comment_map = {c["id"]: {**c, "replies": []} for c in comments}
        root_comments = []
        for c in comments:
            parent_id = c.get("parent_comment_id")
            if parent_id and parent_id in comment_map:
                comment_map[parent_id]["replies"].append(comment_map[c["id"]])
            else:
                root_comments.append(comment_map[c["id"]])
        return root_comments


# =============================================================================
# ACTION ROUTER ADAPTERS
# =============================================================================


def _add_attachment_comment_adapter(handlers: AttachmentCommentHandlers):
    async def handler(params: Dict, context: Dict) -> Dict:
        return await handlers.add_attachment_comment(
            attachment_id=params["attachment_id"],
            yacht_id=context["yacht_id"],
            user_id=context["user_id"],
            comment=params["comment"],
            parent_comment_id=params.get("parent_comment_id"),
        )
    return handler


def _update_attachment_comment_adapter(handlers: AttachmentCommentHandlers):
    async def handler(params: Dict, context: Dict) -> Dict:
        return await handlers.update_attachment_comment(
            comment_id=params["comment_id"],
            yacht_id=context["yacht_id"],
            user_id=context["user_id"],
            comment=params["comment"],
        )
    return handler


def _delete_attachment_comment_adapter(handlers: AttachmentCommentHandlers):
    async def handler(params: Dict, context: Dict) -> Dict:
        return await handlers.delete_attachment_comment(
            comment_id=params["comment_id"],
            yacht_id=context["yacht_id"],
            user_id=context["user_id"],
        )
    return handler


def _list_attachment_comments_adapter(handlers: AttachmentCommentHandlers):
    async def handler(params: Dict, context: Dict) -> Dict:
        return await handlers.list_attachment_comments(
            attachment_id=params["attachment_id"],
            yacht_id=context["yacht_id"],
            include_threads=params.get("include_threads", True),
        )
    return handler


def get_attachment_comment_handlers(supabase_client) -> Dict:
    """Action-router registration map for attachment-comment actions."""
    handlers = AttachmentCommentHandlers(supabase_client)
    return {
        "add_attachment_comment":    _add_attachment_comment_adapter(handlers),
        "update_attachment_comment": _update_attachment_comment_adapter(handlers),
        "delete_attachment_comment": _delete_attachment_comment_adapter(handlers),
        "list_attachment_comments":  _list_attachment_comments_adapter(handlers),
    }

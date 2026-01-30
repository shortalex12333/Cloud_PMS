"""
Work Order Domain Handlers
==========================

Group 3: READ handlers for work order actions.

Handlers:
- view_work_order: Work order details with equipment and assignee
- view_work_order_history: Audit history of changes
- view_work_order_checklist: Checklist items with progress
- open_work_order: Navigate to work order (alias)

All handlers return standardized ActionResponseEnvelope.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import (
    ResponseBuilder,
    FileReference,
    AvailableAction,
    SignedUrlGenerator,
    WorkOrderStatus
)

from .schema_mapping import get_table, map_work_order_select, normalize_work_order

logger = logging.getLogger(__name__)


class WorkOrderHandlers:
    """
    Work order domain READ handlers.
    """

    # Status flow for validation
    STATUS_FLOW = {
        "draft": ["open"],
        "open": ["in_progress", "cancelled"],
        "in_progress": ["pending_parts", "completed", "cancelled"],
        "pending_parts": ["in_progress", "cancelled"],
        "completed": ["closed"],
        "closed": [],
        "cancelled": [],
    }

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    async def view_work_order(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View work order details.

        Returns:
        - Work order data with equipment and assignee info
        - Attached files (photos, documents)
        - Available actions based on status
        """
        builder = ResponseBuilder("view_work_order", entity_id, "work_order", yacht_id)

        try:
            # Query work order using actual table (pms_work_orders)
            result = self.db.table(get_table("work_orders")).select(
                map_work_order_select()
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Work order not found: {entity_id}")
                return builder.build()

            # Normalize to handler expected format
            wo = normalize_work_order(result.data)

            # Add computed fields
            wo["is_overdue"] = self._is_overdue(wo)
            wo["days_open"] = self._days_open(wo)
            wo["allowed_transitions"] = self.STATUS_FLOW.get(wo.get("status"), [])

            # Get checklist progress
            checklist_progress = await self._get_checklist_progress(entity_id)
            wo["checklist_progress"] = checklist_progress

            # Get parts count
            parts_count = await self._get_parts_count(entity_id)
            wo["parts_count"] = parts_count

            builder.set_data(wo)

            # Get attached files
            files = await self._get_work_order_files(entity_id)
            if files:
                builder.add_files(files)

            # Add available actions based on status
            builder.add_available_actions(self._get_wo_actions(wo))

            return builder.build()

        except Exception as e:
            logger.error(f"view_work_order failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_work_order_history(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View work order audit history.

        Returns:
        - List of changes/events for this work order
        - Who made changes and when
        """
        builder = ResponseBuilder("view_work_order_history", entity_id, "work_order", yacht_id)

        try:
            offset = (params or {}).get("offset", 0)
            limit = (params or {}).get("limit", 50)

            # Try to query audit log (table may not exist yet)
            history = []
            total_count = 0
            try:
                result = self.db.table(get_table("audit_log")).select(
                    "id, action, old_values, new_values, created_at, user_id",
                    count="exact"
                ).eq("entity_type", "work_order").eq(
                    "entity_id", entity_id
                ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

                entries = result.data or []
                total_count = result.count or len(entries)

                # Format history entries
                for entry in entries:
                    history.append({
                        "id": entry.get("id"),
                        "action": entry.get("action"),
                        "changes": self._format_changes(entry.get("old_values"), entry.get("new_values")),
                        "user_name": "System",  # Simplified - no FK join
                        "timestamp": entry.get("created_at")
                    })
            except Exception as table_err:
                # Table doesn't exist - return empty history
                logger.debug(f"audit_log table not available: {table_err}")

            builder.set_data({
                "work_order_id": entity_id,
                "history": history,
                "message": "Audit log not configured" if not history else None
            })

            builder.set_pagination(offset, limit, total_count)

            return builder.build()

        except Exception as e:
            logger.error(f"view_work_order_history failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_work_order_checklist(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View work order checklist items.

        Returns:
        - List of checklist items with completion status
        - Progress summary
        """
        builder = ResponseBuilder("view_work_order_checklist", entity_id, "work_order", yacht_id)

        try:
            # Try to query checklist items (table may not exist yet)
            items = []
            try:
                result = self.db.table(get_table("checklist_items")).select(
                    "id, description, is_completed, completed_at, completed_by, notes, sequence"
                ).eq("work_order_id", entity_id).order("sequence").execute()
                items = result.data or []
            except Exception as table_err:
                # Table doesn't exist - return empty checklist
                logger.debug(f"checklist_items table not available: {table_err}")

            completed = len([i for i in items if i.get("is_completed")])
            total = len(items)

            builder.set_data({
                "work_order_id": entity_id,
                "checklist": items,
                "progress": {
                    "completed": completed,
                    "total": total,
                    "percent": round((completed / total * 100) if total > 0 else 0, 1)
                },
                "message": "Checklists not configured" if not items else None
            })

            # Add actions (even if no items, user can add)
            builder.add_available_action(AvailableAction(
                action_id="mark_checklist_item_complete",
                label="Mark Complete",
                variant="MUTATE",
                icon="check"
            ))
            builder.add_available_action(AvailableAction(
                action_id="add_checklist_note",
                label="Add Note",
                variant="MUTATE",
                icon="message"
            ))
            builder.add_available_action(AvailableAction(
                action_id="add_checklist_photo",
                label="Add Photo",
                variant="MUTATE",
                icon="camera"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_work_order_checklist failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def open_work_order(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Open/navigate to work order (alias for view_work_order).
        Used when navigating from search results or notifications.
        """
        return await self.view_work_order(entity_id, yacht_id, params)

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _is_overdue(self, wo: Dict) -> bool:
        """Check if work order is overdue"""
        if wo.get("status") in ("completed", "closed", "cancelled"):
            return False

        due_date = wo.get("due_date")
        if not due_date:
            return False

        try:
            due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) > due
        except Exception:
            return False

    def _days_open(self, wo: Dict) -> int:
        """Calculate days work order has been open"""
        created_at = wo.get("created_at")
        if not created_at:
            return 0

        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

            if wo.get("completed_at"):
                end = datetime.fromisoformat(wo["completed_at"].replace("Z", "+00:00"))
            else:
                end = datetime.now(timezone.utc)

            return (end - created).days
        except Exception:
            return 0

    async def _get_checklist_progress(self, work_order_id: str) -> Dict:
        """Get checklist completion progress"""
        try:
            result = self.db.table("checklist_items").select(
                "is_completed"
            ).eq("work_order_id", work_order_id).execute()

            items = result.data or []
            completed = len([i for i in items if i.get("is_completed")])
            total = len(items)

            return {
                "completed": completed,
                "total": total,
                "percent": round((completed / total * 100) if total > 0 else 0, 1)
            }
        except Exception:
            return {"completed": 0, "total": 0, "percent": 0}

    async def _get_parts_count(self, work_order_id: str) -> int:
        """Get count of parts assigned to work order"""
        try:
            result = self.db.table("pms_work_order_parts").select(
                "id", count="exact"
            ).eq("work_order_id", work_order_id).execute()
            return result.count or 0
        except Exception:
            return 0

    def _get_bucket_for_attachment(self, entity_type: str, category: str, mime_type: str) -> str:
        """
        Determine storage bucket based on entity type and attachment category.

        CRITICAL: Table name is pms_attachments (NOT attachments).
        DO NOT change to table("attachments"). Linter guard enforced.

        Bucket strategy until pms_attachments.bucket column added:
        - work_order + photo/image → pms-work-order-photos
        - fault + photo/image → pms-discrepancy-photos
        - equipment + photo/image → pms-work-order-photos (shared)
        - manual/document/pdf → documents
        - Default → attachments
        """
        category = (category or "").lower()
        mime_type = (mime_type or "").lower()

        # Photo/image categories - route by entity type
        if category in ("photo", "image") or mime_type.startswith("image/"):
            if entity_type == "fault":
                return "pms-discrepancy-photos"
            elif entity_type in ("work_order", "equipment"):
                return "pms-work-order-photos"

        # Manuals and documents
        if category in ("manual", "document", "pdf") or mime_type == "application/pdf":
            return "documents"

        # Default: generic attachments bucket
        return "attachments"

    async def _get_work_order_files(self, work_order_id: str) -> List[Dict]:
        """Get files attached to work order"""
        files = []

        if not self.url_generator:
            return files

        try:
            # CRITICAL: Use pms_attachments (NOT attachments) - see soft delete migration
            result = self.db.table("pms_attachments").select(
                "id, filename, mime_type, storage_path, category, uploaded_at"
            ).eq("entity_type", "work_order").eq("entity_id", work_order_id).is_(
                "deleted_at", "null"  # Soft delete filter required
            ).execute()

            for att in (result.data or []):
                # Determine bucket based on entity type and category
                bucket = self._get_bucket_for_attachment(
                    entity_type="work_order",
                    category=att.get("category"),
                    mime_type=att.get("mime_type")
                )

                file_ref = self.url_generator.create_file_reference(
                    bucket=bucket,
                    path=att.get("storage_path", ""),
                    filename=att.get("filename", "file"),
                    file_id=att["id"],
                    mime_type=att.get("mime_type"),
                    expires_in_minutes=30
                )
                if file_ref:
                    files.append(file_ref.to_dict())

        except Exception as e:
            logger.warning(f"Failed to get work order files: {e}")

        return files

    def _format_changes(self, old_values: Dict, new_values: Dict) -> List[Dict]:
        """Format change diff for display"""
        if not old_values and not new_values:
            return []

        changes = []
        old = old_values or {}
        new = new_values or {}

        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            if old.get(key) != new.get(key):
                changes.append({
                    "field": key,
                    "from": old.get(key),
                    "to": new.get(key)
                })

        return changes

    def _get_wo_actions(self, wo: Dict) -> List[AvailableAction]:
        """Get available actions based on work order status"""
        status = wo.get("status", "draft")
        allowed_transitions = wo.get("allowed_transitions", [])

        actions = []

        # View actions always available
        actions.append(AvailableAction(
            action_id="view_work_order_checklist",
            label="View Checklist",
            variant="READ",
            icon="list"
        ))

        # Status transitions
        if "in_progress" in allowed_transitions:
            actions.append(AvailableAction(
                action_id="update_work_order_status",
                label="Start Work",
                variant="MUTATE",
                icon="play",
                requires_signature=True
            ))

        if "completed" in allowed_transitions:
            actions.append(AvailableAction(
                action_id="mark_work_order_complete",
                label="Mark Complete",
                variant="MUTATE",
                icon="check-circle",
                requires_signature=True,
                is_primary=True
            ))

        # Always available mutations
        if status not in ("completed", "closed", "cancelled"):
            actions.extend([
                AvailableAction(
                    action_id="add_work_order_note",
                    label="Add Note",
                    variant="MUTATE",
                    icon="message"
                ),
                AvailableAction(
                    action_id="add_work_order_photo",
                    label="Add Photo",
                    variant="MUTATE",
                    icon="camera"
                ),
                AvailableAction(
                    action_id="add_parts_to_work_order",
                    label="Add Parts",
                    variant="MUTATE",
                    icon="package"
                ),
                AvailableAction(
                    action_id="assign_work_order",
                    label="Assign",
                    variant="MUTATE",
                    icon="user"
                ),
            ])

        return actions


def get_work_order_handlers(supabase_client) -> Dict[str, callable]:
    """Get work order handler functions for registration."""
    handlers = WorkOrderHandlers(supabase_client)

    return {
        "view_work_order": handlers.view_work_order,
        "view_work_order_history": handlers.view_work_order_history,
        "view_work_order_checklist": handlers.view_work_order_checklist,
        "open_work_order": handlers.open_work_order,
    }

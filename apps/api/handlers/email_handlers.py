"""
Email Handlers
==============

Email lens actions for searching, viewing, and linking emails.

Actions:
- search_emails: Search emails by query
- view_email_thread: View full email thread
- extract_entities: Extract entities from email content
- link_to_work_order: Link thread to work order
- link_to_equipment: Link thread to equipment
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging
import re

logger = logging.getLogger(__name__)


class EmailHandlers:
    """
    Handlers for Email Lens.

    Implements email search, viewing, and linking capabilities.
    Per doctrine: metadata-only, no bodies stored.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # SEARCH EMAILS
    # =========================================================================

    async def search_emails(
        self,
        yacht_id: str,
        user_id: str,
        query: str = "",
        folder: str = "inbox",
        limit: int = 20,
        offset: int = 0,
    ) -> Dict:
        """
        Search emails by query string.

        Searches across email threads and messages by subject and participant.
        Returns metadata only (no bodies per doctrine).
        """
        try:
            # Validate limit
            if limit > 100:
                limit = 100
            if limit < 1:
                limit = 20

            # Build query for email threads
            threads_query = self.db.table("email_threads").select(
                """
                id,
                latest_subject,
                message_count,
                has_attachments,
                source,
                first_message_at,
                last_activity_at,
                created_at
                """
            ).eq("yacht_id", yacht_id).order(
                "last_activity_at", desc=True
            ).range(offset, offset + limit - 1)

            # Apply search filter if query provided
            if query and len(query.strip()) > 0:
                # Search in latest_subject using ilike
                threads_query = threads_query.ilike("latest_subject", f"%{query}%")

            result = threads_query.execute()

            threads = result.data if result.data else []

            # Get message counts by folder if needed
            folder_counts = {}
            if folder != "all":
                # Get counts per folder
                counts_result = self.db.table("email_messages").select(
                    "folder", options={"count": "exact", "head": True}
                ).eq("yacht_id", yacht_id).execute()

                folder_counts = {"total": counts_result.count if counts_result.count else 0}

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="search_emails",
                entity_type="email_thread",
                entity_id=None,
                user_id=user_id,
                new_values={"query": query, "folder": folder, "result_count": len(threads)},
            )

            return {
                "status": "success",
                "action": "search_emails",
                "result": {
                    "threads": threads,
                    "count": len(threads),
                    "query": query,
                    "folder": folder,
                    "limit": limit,
                    "offset": offset,
                },
                "message": f"Found {len(threads)} email threads",
            }

        except Exception as e:
            logger.error(f"search_emails failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # VIEW EMAIL THREAD
    # =========================================================================

    async def view_email_thread(
        self,
        yacht_id: str,
        user_id: str,
        thread_id: str,
    ) -> Dict:
        """
        Get full email thread with all messages.

        Returns thread metadata and message list.
        Per doctrine: no bodies stored, content fetched on-demand from Graph.
        """
        try:
            # Get thread
            thread_result = self.db.table("email_threads").select(
                """
                id,
                provider_conversation_id,
                latest_subject,
                message_count,
                has_attachments,
                participant_hashes,
                source,
                first_message_at,
                last_activity_at,
                last_inbound_at,
                last_outbound_at,
                created_at
                """
            ).eq("id", thread_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not thread_result.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Email thread not found: {thread_id}",
                }

            thread = thread_result.data

            # Get messages in thread
            messages_result = self.db.table("email_messages").select(
                """
                id,
                provider_message_id,
                internet_message_id,
                direction,
                from_display_name,
                subject,
                sent_at,
                received_at,
                has_attachments,
                attachments,
                folder
                """
            ).eq("thread_id", thread_id).eq("yacht_id", yacht_id).order(
                "sent_at", desc=False
            ).execute()

            messages = messages_result.data if messages_result.data else []

            # Get linked objects
            links_result = self.db.table("email_links").select(
                """
                id,
                object_type,
                object_id,
                confidence,
                suggested_reason,
                suggested_at,
                accepted_at,
                is_active
                """
            ).eq("thread_id", thread_id).eq("yacht_id", yacht_id).eq(
                "is_active", True
            ).execute()

            links = links_result.data if links_result.data else []

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="view_email_thread",
                entity_type="email_thread",
                entity_id=thread_id,
                user_id=user_id,
                new_values={"message_count": len(messages)},
            )

            return {
                "status": "success",
                "action": "view_email_thread",
                "result": {
                    "thread": thread,
                    "messages": messages,
                    "links": links,
                    "message_count": len(messages),
                },
                "message": f"Thread with {len(messages)} messages",
            }

        except Exception as e:
            logger.error(f"view_email_thread failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # EXTRACT ENTITIES
    # =========================================================================

    async def extract_entities(
        self,
        yacht_id: str,
        user_id: str,
        thread_id: str,
    ) -> Dict:
        """
        Extract equipment/work order/part entities from email.

        Analyzes thread subject and metadata to find potential entity references.
        Returns suggestions for linking.
        """
        try:
            # Get thread with subject
            thread_result = self.db.table("email_threads").select(
                "id, latest_subject, provider_conversation_id"
            ).eq("id", thread_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not thread_result.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Email thread not found: {thread_id}",
                }

            thread = thread_result.data
            subject = thread.get("latest_subject", "") or ""

            # Extract potential entity references from subject
            entities = {
                "work_orders": [],
                "equipment": [],
                "parts": [],
                "faults": [],
            }

            # Pattern matching for work orders (WO-XXXXX, WO#XXXXX, Work Order XXXXX)
            wo_patterns = [
                r"WO[-#]?\s*(\d{4,})",
                r"Work\s*Order\s*#?\s*(\d{4,})",
            ]
            for pattern in wo_patterns:
                matches = re.findall(pattern, subject, re.IGNORECASE)
                for match in matches:
                    entities["work_orders"].append({
                        "pattern": match,
                        "confidence": "suggested",
                        "reason": "wo_pattern",
                    })

            # Pattern matching for part numbers (P/N, Part#, PN:)
            pn_patterns = [
                r"P/?N\s*[:# ]?\s*([A-Z0-9-]+)",
                r"Part\s*#?\s*[:# ]?\s*([A-Z0-9-]+)",
            ]
            for pattern in pn_patterns:
                matches = re.findall(pattern, subject, re.IGNORECASE)
                for match in matches:
                    entities["parts"].append({
                        "pattern": match,
                        "confidence": "suggested",
                        "reason": "part_number",
                    })

            # Pattern matching for serial numbers (S/N, Serial#)
            sn_patterns = [
                r"S/?N\s*[:# ]?\s*([A-Z0-9-]+)",
                r"Serial\s*#?\s*[:# ]?\s*([A-Z0-9-]+)",
            ]
            for pattern in sn_patterns:
                matches = re.findall(pattern, subject, re.IGNORECASE)
                for match in matches:
                    entities["equipment"].append({
                        "pattern": match,
                        "confidence": "suggested",
                        "reason": "serial_match",
                    })

            # Look up actual entities in database if patterns found
            suggestions = []

            # Look up work orders
            if entities["work_orders"]:
                for wo_ref in entities["work_orders"]:
                    wo_result = self.db.table("pms_work_orders").select(
                        "id, wo_number, title"
                    ).eq("yacht_id", yacht_id).ilike(
                        "wo_number", f"%{wo_ref['pattern']}%"
                    ).limit(5).execute()

                    if wo_result.data:
                        for wo in wo_result.data:
                            suggestions.append({
                                "object_type": "work_order",
                                "object_id": wo["id"],
                                "display": f"{wo['wo_number']} - {wo['title']}",
                                "confidence": "suggested",
                                "reason": wo_ref["reason"],
                            })

            # Look up parts
            if entities["parts"]:
                for part_ref in entities["parts"]:
                    part_result = self.db.table("pms_parts").select(
                        "id, part_number, name"
                    ).eq("yacht_id", yacht_id).ilike(
                        "part_number", f"%{part_ref['pattern']}%"
                    ).limit(5).execute()

                    if part_result.data:
                        for part in part_result.data:
                            suggestions.append({
                                "object_type": "part",
                                "object_id": part["id"],
                                "display": f"{part['part_number']} - {part['name']}",
                                "confidence": "suggested",
                                "reason": part_ref["reason"],
                            })

            # Look up equipment by serial
            if entities["equipment"]:
                for eq_ref in entities["equipment"]:
                    eq_result = self.db.table("pms_equipment").select(
                        "id, serial_number, name"
                    ).eq("yacht_id", yacht_id).ilike(
                        "serial_number", f"%{eq_ref['pattern']}%"
                    ).limit(5).execute()

                    if eq_result.data:
                        for eq in eq_result.data:
                            suggestions.append({
                                "object_type": "equipment",
                                "object_id": eq["id"],
                                "display": f"{eq['serial_number']} - {eq['name']}",
                                "confidence": "suggested",
                                "reason": eq_ref["reason"],
                            })

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="extract_entities",
                entity_type="email_thread",
                entity_id=thread_id,
                user_id=user_id,
                new_values={"suggestion_count": len(suggestions)},
            )

            return {
                "status": "success",
                "action": "extract_entities",
                "result": {
                    "thread_id": thread_id,
                    "subject": subject,
                    "raw_patterns": entities,
                    "suggestions": suggestions,
                },
                "message": f"Found {len(suggestions)} potential entity matches",
            }

        except Exception as e:
            logger.error(f"extract_entities failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # LINK TO WORK ORDER
    # =========================================================================

    async def link_to_work_order(
        self,
        yacht_id: str,
        user_id: str,
        thread_id: str,
        work_order_id: str,
        confidence: str = "user_confirmed",
    ) -> Dict:
        """
        Link email thread to work order.

        Creates a relationship between the email thread and a work order.
        Per doctrine: linking is a conscious act, all changes ledgered.
        """
        try:
            # Validate thread exists
            thread_result = self.db.table("email_threads").select(
                "id, latest_subject"
            ).eq("id", thread_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not thread_result.data:
                return {
                    "status": "error",
                    "error_code": "THREAD_NOT_FOUND",
                    "message": f"Email thread not found: {thread_id}",
                }

            thread = thread_result.data

            # Validate work order exists
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, title"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "WORK_ORDER_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}",
                }

            work_order = wo_result.data

            # Check for existing active link
            existing_result = self.db.table("email_links").select(
                "id"
            ).eq("thread_id", thread_id).eq("object_type", "work_order").eq(
                "object_id", work_order_id
            ).eq("is_active", True).maybe_single().execute()

            if existing_result.data:
                return {
                    "status": "error",
                    "error_code": "LINK_EXISTS",
                    "message": "Link already exists between this thread and work order",
                }

            # Create link
            now = datetime.now(timezone.utc).isoformat()
            link_data = {
                "yacht_id": yacht_id,
                "thread_id": thread_id,
                "object_type": "work_order",
                "object_id": work_order_id,
                "confidence": confidence,
                "suggested_reason": "manual",
                "suggested_at": now,
                "accepted_at": now if confidence == "user_confirmed" else None,
                "accepted_by": user_id if confidence == "user_confirmed" else None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }

            result = self.db.table("email_links").insert(link_data).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create email link",
                }

            link = result.data[0]

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="link_to_work_order",
                entity_type="email_link",
                entity_id=link["id"],
                user_id=user_id,
                new_values={
                    "thread_id": thread_id,
                    "work_order_id": work_order_id,
                    "work_order_number": work_order["wo_number"],
                },
            )

            return {
                "status": "success",
                "action": "link_to_work_order",
                "result": {
                    "link_id": link["id"],
                    "thread_id": thread_id,
                    "thread_subject": thread.get("latest_subject"),
                    "work_order_id": work_order_id,
                    "work_order_number": work_order["wo_number"],
                    "confidence": confidence,
                },
                "message": f"Linked thread to work order {work_order['wo_number']}",
            }

        except Exception as e:
            logger.error(f"link_to_work_order failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # LINK TO EQUIPMENT
    # =========================================================================

    async def link_to_equipment(
        self,
        yacht_id: str,
        user_id: str,
        thread_id: str,
        equipment_id: str,
        confidence: str = "user_confirmed",
    ) -> Dict:
        """
        Link email thread to equipment.

        Creates a relationship between the email thread and equipment.
        Per doctrine: linking is a conscious act, all changes ledgered.
        """
        try:
            # Validate thread exists
            thread_result = self.db.table("email_threads").select(
                "id, latest_subject"
            ).eq("id", thread_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not thread_result.data:
                return {
                    "status": "error",
                    "error_code": "THREAD_NOT_FOUND",
                    "message": f"Email thread not found: {thread_id}",
                }

            thread = thread_result.data

            # Validate equipment exists
            eq_result = self.db.table("pms_equipment").select(
                "id, name, serial_number"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not eq_result.data:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}",
                }

            equipment = eq_result.data

            # Check for existing active link
            existing_result = self.db.table("email_links").select(
                "id"
            ).eq("thread_id", thread_id).eq("object_type", "equipment").eq(
                "object_id", equipment_id
            ).eq("is_active", True).maybe_single().execute()

            if existing_result.data:
                return {
                    "status": "error",
                    "error_code": "LINK_EXISTS",
                    "message": "Link already exists between this thread and equipment",
                }

            # Create link
            now = datetime.now(timezone.utc).isoformat()
            link_data = {
                "yacht_id": yacht_id,
                "thread_id": thread_id,
                "object_type": "equipment",
                "object_id": equipment_id,
                "confidence": confidence,
                "suggested_reason": "manual",
                "suggested_at": now,
                "accepted_at": now if confidence == "user_confirmed" else None,
                "accepted_by": user_id if confidence == "user_confirmed" else None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }

            result = self.db.table("email_links").insert(link_data).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create email link",
                }

            link = result.data[0]

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="link_to_equipment",
                entity_type="email_link",
                entity_id=link["id"],
                user_id=user_id,
                new_values={
                    "thread_id": thread_id,
                    "equipment_id": equipment_id,
                    "equipment_name": equipment["name"],
                },
            )

            return {
                "status": "success",
                "action": "link_to_equipment",
                "result": {
                    "link_id": link["id"],
                    "thread_id": thread_id,
                    "thread_subject": thread.get("latest_subject"),
                    "equipment_id": equipment_id,
                    "equipment_name": equipment["name"],
                    "equipment_serial": equipment.get("serial_number"),
                    "confidence": confidence,
                },
                "message": f"Linked thread to equipment: {equipment['name']}",
            }

        except Exception as e:
            logger.error(f"link_to_equipment failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _create_audit_log(
        self,
        yacht_id: str,
        action: str,
        entity_type: str,
        entity_id: Optional[str],
        user_id: str,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        signature: Optional[Dict] = None,
    ) -> Optional[str]:
        """Create audit log entry."""
        try:
            audit_data = {
                "yacht_id": yacht_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "old_values": old_values,
                "new_values": new_values,
                "signature": signature or {},  # INVARIANT: never None
                "metadata": {"source": "lens", "lens": "email"},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            result = self.db.table("pms_audit_log").insert(audit_data).execute()

            return result.data[0]["id"] if result.data else None

        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")
            return None


# =============================================================================
# HANDLER REGISTRATION
# =============================================================================

def get_email_handlers(supabase_client) -> Dict[str, callable]:
    """Get email handler functions for registration."""
    handlers = EmailHandlers(supabase_client)

    return {
        "search_emails": handlers.search_emails,
        "view_email_thread": handlers.view_email_thread,
        "extract_entities": handlers.extract_entities,
        "link_to_work_order": handlers.link_to_work_order,
        "link_to_equipment": handlers.link_to_equipment,
    }


__all__ = [
    "EmailHandlers",
    "get_email_handlers",
]

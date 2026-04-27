"""
Receiving — supplier email draft handler (Phase 5).

Builds a discrepancy email and saves it to the user's Outlook Drafts folder
via Microsoft Graph. Never auto-sends. Crew reviews and sends manually.

Token lookup: auth_microsoft_tokens is on TENANT DB — get_service_db(yacht_id) suffices.
No separate master client needed.
"""
import logging
import os
from datetime import datetime, timezone, timedelta

from supabase import Client
from handlers.db_client import get_service_db
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)

_REASON_TEXT = {
    "short":      "items short — we received fewer units than ordered",
    "damaged":    "items arrived damaged and cannot be accepted",
    "wrong_item": "items received do not match the order specification",
    "over":       "items received in excess of ordered quantity",
}

# Dispositions that constitute a discrepancy requiring supplier contact
_DISCREPANCY_DISPOSITIONS = ["short", "damaged", "wrong_item"]


def _build_email_body(
    supplier_name: str,
    po_number: str,
    received_date,
    disc_items: list,
    user_name: str,
    yacht_name: str,
    custom_note: str,
) -> str:
    lines_html = ""
    for item in disc_items:
        desc = item.get("description") or "Item"
        exp = item.get("quantity_expected") or "?"
        rcvd = item.get("quantity_received") or 0
        disp = item.get("disposition") or "short"
        reason = _REASON_TEXT.get(disp, disp)
        lines_html += f"""
        <tr>
            <td style="padding:4px 8px;">{desc}</td>
            <td style="padding:4px 8px; text-align:center;">{exp}</td>
            <td style="padding:4px 8px; text-align:center;">{rcvd}</td>
            <td style="padding:4px 8px;">{reason}</td>
        </tr>"""

    date_str = str(received_date) if received_date else "recently"
    custom_section = f"<p>{custom_note}</p>" if custom_note else ""

    return f"""
<p>Dear {supplier_name},</p>

<p>We are writing regarding our order <strong>{po_number or "reference pending"}</strong>, received on {date_str}.</p>

<p>Upon inspection, we have identified the following discrepancies:</p>

<table style="border-collapse:collapse; width:100%; font-family:Arial,sans-serif; font-size:14px;">
  <thead>
    <tr style="background:#f5f5f5;">
      <th style="padding:6px 8px; text-align:left; border-bottom:1px solid #ddd;">Item</th>
      <th style="padding:6px 8px; text-align:center; border-bottom:1px solid #ddd;">Ordered</th>
      <th style="padding:6px 8px; text-align:center; border-bottom:1px solid #ddd;">Received</th>
      <th style="padding:6px 8px; text-align:left; border-bottom:1px solid #ddd;">Issue</th>
    </tr>
  </thead>
  <tbody>
    {lines_html}
  </tbody>
</table>

{custom_section}

<p>Please advise on how you intend to resolve these discrepancies at your earliest convenience.</p>

<p>Kind regards,<br>
<strong>{user_name}</strong><br>
{yacht_name}</p>
"""


def _draft_supplier_email_adapter():
    async def _fn(**params):
        receiving_id = params.get("receiving_id")
        user_id = params.get("user_id")
        yacht_id = params.get("yacht_id")
        cc_emails = params.get("cc_emails") or []
        custom_note = (params.get("custom_note") or "").strip()
        force = params.get("force", False)

        if not receiving_id:
            return {"status": "error", "error_code": "MISSING_FIELD",
                    "message": "receiving_id is required"}

        db = get_service_db(yacht_id)

        # Idempotency: check for existing draft within 24h
        if not force:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            prev = db.table("ledger_events").select("created_at").eq(
                "entity_id", receiving_id
            ).eq("action", "draft_supplier_email").gte("created_at", cutoff).limit(1).execute()
            if prev.data:
                age_str = prev.data[0].get("created_at", "")
                return {
                    "status": "info",
                    "error_code": "ALREADY_DRAFTED",
                    "message": f"A draft was already created recently. Open your Outlook Drafts. "
                               f"Pass force=true to create another.",
                    "previous_draft_at": age_str,
                }

        # Fetch receiving record
        recv = db.table("pms_receiving").select(
            "id, vendor_name, vendor_reference, po_id, received_date"
        ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()
        if not recv.data:
            return {"status": "error", "error_code": "NOT_FOUND",
                    "message": "Receiving record not found"}

        recv_data = recv.data
        supplier_name = recv_data.get("vendor_name") or "Supplier"
        po_number = recv_data.get("vendor_reference") or ""
        po_id = recv_data.get("po_id")

        # Resolve supplier email via po_id → pms_purchase_orders → pms_suppliers
        supplier_email = None
        if po_id:
            po = db.table("pms_purchase_orders").select(
                "supplier_id"
            ).eq("id", po_id).maybe_single().execute()
            if po.data and po.data.get("supplier_id"):
                sup = db.table("pms_suppliers").select(
                    "name, email"
                ).eq("id", po.data["supplier_id"]).maybe_single().execute()
                if sup.data:
                    supplier_email = sup.data.get("email")
                    supplier_name = sup.data.get("name") or supplier_name

        # Fetch discrepancy items (only dispositions that warrant supplier contact)
        items_res = db.table("pms_receiving_items").select(
            "description, quantity_expected, quantity_received, quantity_rejected, disposition"
        ).eq("receiving_id", receiving_id).eq("yacht_id", yacht_id).in_(
            "disposition", _DISCREPANCY_DISPOSITIONS
        ).execute()
        disc_items = items_res.data or []

        if not disc_items:
            return {"status": "error", "error_code": "NO_DISCREPANCIES",
                    "message": "No discrepancy items found on this receiving"}

        # Fetch user name + yacht name
        user_res = db.table("auth_users_profiles").select("name").eq(
            "id", user_id
        ).maybe_single().execute()
        user_name = (user_res.data or {}).get("name") or "Crew Member"

        yacht_res = db.table("yacht_registry").select("name").eq(
            "id", yacht_id
        ).maybe_single().execute()
        yacht_name = (yacht_res.data or {}).get("name") or "Vessel"

        subject = f"Receiving Discrepancy — Order {po_number or 'Unknown'}"
        body = _build_email_body(
            supplier_name=supplier_name,
            po_number=po_number,
            received_date=recv_data.get("received_date"),
            disc_items=disc_items,
            user_name=user_name,
            yacht_name=yacht_name,
            custom_note=custom_note,
        )

        # Create Outlook draft via Graph (tokens on TENANT DB)
        from integrations.graph_client import GraphWriteClient, TokenNotFoundError
        try:
            write_client = GraphWriteClient(db, user_id, yacht_id)
            to_list = [supplier_email] if supplier_email else []
            draft = await write_client.create_draft(
                to=to_list,
                subject=subject,
                body=body,
                body_type="HTML",
            )
        except TokenNotFoundError:
            return {
                "status": "error",
                "error_code": "NO_EMAIL_TOKEN",
                "message": "Connect your Outlook account under Settings to use this feature",
            }
        except Exception as graph_err:
            logger.error(f"[draft_supplier_email] Graph error: {graph_err}")
            return {
                "status": "error",
                "error_code": "GRAPH_ERROR",
                "message": "Failed to create Outlook draft. Try again later.",
            }

        # Log to ledger
        try:
            ledger_row = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="email_drafted",
                entity_type="receiving",
                entity_id=receiving_id,
                action="draft_supplier_email",
                change_summary=f"Supplier email drafted: {len(disc_items)} discrepancy item(s)",
                metadata={
                    "draft_id": draft.get("id") if isinstance(draft, dict) else None,
                    "supplier_email": supplier_email,
                    "discrepancy_count": len(disc_items),
                    "idempotency_key": f"email_draft:{receiving_id}:{user_id}",
                },
            )
            db.table("ledger_events").insert(ledger_row).execute()
        except Exception as e:
            logger.warning(f"[draft_supplier_email] Ledger event failed (non-fatal): {e}")

        return {
            "status": "success",
            "draft_created": True,
            "supplier_email": supplier_email,
            "no_recipient": supplier_email is None,
            "message": (
                "Draft created in your Outlook. Open and review before sending."
                if supplier_email
                else "Draft created with no recipient — please add the supplier email before sending."
            ),
        }

    return _fn

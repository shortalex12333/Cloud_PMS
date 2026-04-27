"""
Receiving label PDF — Phase 6.

Utility printout: one page per accepted item, sized to user selection.
Plain PDF — no sealing, no HMAC masking. The evidence trail is the
receiving receipt generated via the Receipt Layer (HMAC branch).

The labels_generated ledger event fired here appears in the receiving
single receipt's event timeline automatically.

GET /v1/receiving/{receiving_id}/labels
    ?yacht_id=<uuid>
    &size=A4            (A4 | A5 | label_62 | label_36 | custom)
    &w=<mm>             (required if size=custom)
    &h=<mm>             (required if size=custom)
    &item_ids=<uuid>,…  (optional — defaults to all accepted items)
    &user_id=<uuid>     (optional — needed to fire ledger event)
"""
import fitz
import logging
from pathlib import Path

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response

from handlers.db_client import get_service_db
from routes.handlers.ledger_utils import build_ledger_event

router = APIRouter()
logger = logging.getLogger(__name__)

MM_TO_PT = 2.8346
_FONT_DIR = Path(__file__).parent.parent / "evidence" / "fonts"

SIZE_MAP = {
    "A4":       (210, 297),
    "A5":       (148, 210),
    "label_62": (62,  100),
    "label_36": (36,   89),
}


@router.get("/v1/receiving/{receiving_id}/labels")
async def generate_labels(
    receiving_id: str,
    yacht_id: str   = Query(...),
    size: str       = Query("A4"),
    w: float        = Query(None),
    h: float        = Query(None),
    item_ids: str   = Query(None),
    user_id: str    = Query(None),
):
    db = get_service_db(yacht_id)

    recv = db.table("pms_receiving").select(
        "id, vendor_name, vendor_reference, received_date"
    ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not recv.data:
        raise HTTPException(404, "Receiving not found")

    yacht = db.table("yacht_registry").select("name").eq(
        "id", yacht_id
    ).maybe_single().execute()
    yacht_name = (yacht.data or {}).get("name") or "Vessel"

    q = db.table("pms_receiving_items").select(
        "id, description, part_id, quantity_accepted, "
        "pms_parts(part_number, location, name)"
    ).eq("receiving_id", receiving_id).eq("yacht_id", yacht_id).gt(
        "quantity_accepted", 0
    )
    if item_ids:
        ids = [x.strip() for x in item_ids.split(",") if x.strip()]
        if ids:
            q = q.in_("id", ids)
    items = q.execute().data or []

    if not items:
        raise HTTPException(400, "No accepted items to print labels for")

    # Resolve page dimensions
    if size == "custom":
        if not w or not h:
            raise HTTPException(400, "w and h (in mm) are required for custom size")
        page_w_pt = w * MM_TO_PT
        page_h_pt = h * MM_TO_PT
    else:
        dims = SIZE_MAP.get(size, SIZE_MAP["A4"])
        page_w_pt = dims[0] * MM_TO_PT
        page_h_pt = dims[1] * MM_TO_PT

    is_compact = size in ("label_62", "label_36")

    doc = fitz.open()
    for item in items:
        page = doc.new_page(width=page_w_pt, height=page_h_pt)
        _load_fonts(page)
        _draw_label(page, item, recv.data, yacht_name, is_compact, page_w_pt, page_h_pt)

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()

    if user_id:
        try:
            ledger_row = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="export",
                entity_type="receiving",
                entity_id=receiving_id,
                action="generate_labels",
                change_summary=f"{len(items)} label(s) printed for receiving {receiving_id[:8]}",
                metadata={"item_count": len(items), "label_size": size},
            )
            db.table("ledger_events").insert(ledger_row).execute()
        except Exception as e:
            logger.warning(f"[generate_labels] Ledger event failed (non-fatal): {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="labels_{receiving_id[:8]}.pdf"'
        },
    )


def _load_fonts(page: fitz.Page) -> None:
    page.insert_font(fontname="Inter",     fontfile=str(_FONT_DIR / "Inter-Regular.ttf"))
    page.insert_font(fontname="InterBold", fontfile=str(_FONT_DIR / "Inter-Bold.ttf"))


def _draw_label(
    page: fitz.Page,
    item: dict,
    recv: dict,
    yacht_name: str,
    is_compact: bool,
    w_pt: float,
    h_pt: float,
) -> None:
    part = item.get("pms_parts") or {}
    part_number = part.get("part_number") or "—"
    location    = part.get("location") or "Unassigned"
    description = item.get("description") or part.get("name") or "Item"
    qty         = item.get("quantity_accepted", 0)
    date_str    = str(recv.get("received_date") or "")
    ref         = recv.get("vendor_reference") or "—"
    margin      = 8 * MM_TO_PT

    def txt(x, y, text, size=10, bold=False, color=(0.08, 0.08, 0.08)):
        page.insert_text(
            fitz.Point(x, y),
            str(text),
            fontsize=size,
            fontname="InterBold" if bold else "Inter",
            color=color,
        )

    if is_compact:
        y = margin + 10
        txt(margin, y, description[:30], size=8, bold=True)
        y += 12
        barcode_rect = fitz.Rect(margin, y, w_pt - margin, y + 9 * MM_TO_PT)
        page.draw_rect(barcode_rect, color=(0.75, 0.75, 0.75), fill=(0.94, 0.94, 0.94))
        txt(margin + 2, barcode_rect.y0 + 7, f"[{part_number}]", size=6, color=(0.4, 0.4, 0.4))
        y = barcode_rect.y1 + 4
        txt(margin, y, f"Qty: {qty}  |  {location}", size=7)
    else:
        y = margin + 16
        barcode_rect = fitz.Rect(margin, y, w_pt - margin, y + 18 * MM_TO_PT)
        page.draw_rect(barcode_rect, color=(0.75, 0.75, 0.75), fill=(0.94, 0.94, 0.94))
        txt(
            margin + 4,
            barcode_rect.y0 + 13 * MM_TO_PT,
            f"[BARCODE — {part_number}]",
            size=9,
            color=(0.4, 0.4, 0.4),
        )
        y = barcode_rect.y1 + 8 * MM_TO_PT

        for label, value in [
            ("Part No",      part_number),
            ("Description",  description),
            ("Qty Accepted", str(qty)),
            ("Location",     location),
            ("Vessel",       yacht_name),
            ("Date",         date_str),
            ("Ref",          ref),
        ]:
            txt(margin,       y, f"{label}:", size=8, color=(0.5, 0.5, 0.5))
            txt(margin + 72,  y, value,       size=10)
            y += 7 * MM_TO_PT

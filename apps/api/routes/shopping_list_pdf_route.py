"""
Shopping List PDF Export
========================
GET /v1/shopping-list/{list_id}/pdf

Produces a clean A4 PDF of the shopping list requisition document.
Available at status: draft, submitted, hod_approved, converted_to_po.

PDF structure:
  - Teal header bar + document title + list number
  - Meta block: vessel, department, currency, status, submitted by, dates
  - Line items table: # / Part / Part No. / Qty / Unit / Unit Price / Total / Status / Notes
  - Candidate parts flagged with ⚠
  - Subtotal + estimated total
  - HOD approval chain (if hod_approved or converted_to_po)
  - Footer: generated timestamp + system label
"""

import logging
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import io

from integrations.supabase import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/shopping-list", tags=["shopping-list-pdf"])

# A4 points
PAGE_W = 595
PAGE_H = 842
MARGIN = 40
COL_X = MARGIN

# Teal brand colour (matches --mark token)
TEAL = (0.17, 0.48, 0.64)
TEAL_LIGHT = (0.12, 0.72, 0.9)
GREY = (0.55, 0.55, 0.55)
DARK = (0.08, 0.08, 0.08)
MID = (0.25, 0.25, 0.25)
BORDER = (0.88, 0.88, 0.88)

STATUS_LABELS = {
    "draft": "DRAFT",
    "submitted": "SUBMITTED — PENDING HOD REVIEW",
    "hod_approved": "HOD APPROVED",
    "converted_to_po": "CONVERTED TO PURCHASE ORDER",
}

ITEM_STATUS_LABELS = {
    "candidate": "candidate",
    "under_review": "pending",
    "approved": "approved",
    "rejected": "rejected",
    "ordered": "ordered",
    "partially_fulfilled": "part. fulfilled",
    "fulfilled": "fulfilled",
    "installed": "installed",
}


def _now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _fmt_price(val, currency: str) -> str:
    if val is None:
        return "—"
    try:
        return f"{currency} {float(val):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_qty(val) -> str:
    if val is None:
        return "—"
    try:
        n = float(val)
        return str(int(n)) if n == int(n) else f"{n:.2f}"
    except (TypeError, ValueError):
        return "—"


def _build_shopping_list_pdf(sl: dict, items: list, vessel_name: str) -> bytes:
    import fitz  # PyMuPDF

    _FONT_DIR = Path(__file__).parent.parent / "evidence" / "fonts"
    inter_regular = str(_FONT_DIR / "Inter-Regular.ttf")
    inter_bold    = str(_FONT_DIR / "Inter-Bold.ttf")

    doc = fitz.open()

    # -------------------------------------------------------------------------
    # PAGE 1 — Cover + items table
    # -------------------------------------------------------------------------
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.insert_font(fontname="Inter",     fontfile=inter_regular)
    page.insert_font(fontname="InterBold", fontfile=inter_bold)

    y = 0

    # Header bar
    page.draw_rect(fitz.Rect(0, 0, PAGE_W, 5), color=None, fill=TEAL)
    y = 28

    def text(txt: str, size: int = 10, bold: bool = False,
             color=DARK, x: int = MARGIN, wrap_w: int = None):
        nonlocal y
        fn = "InterBold" if bold else "Inter"
        if wrap_w:
            # Simple manual wrapping via fitz.TextWriter not needed — use insert_textbox
            page.insert_textbox(
                fitz.Rect(x, y, x + wrap_w, y + size * 4),
                txt, fontsize=size, fontname=fn, color=color,
                align=0
            )
            y += size * 1.55
        else:
            page.insert_text(fitz.Point(x, y), txt, fontsize=size,
                             fontname=fn, color=color)
            y += size * 1.55

    def label_value(lbl: str, val: str, size: int = 9):
        nonlocal y
        page.insert_text(fitz.Point(MARGIN, y), lbl,
                         fontsize=7, fontname="InterBold", color=GREY)
        y += 9
        page.insert_text(fitz.Point(MARGIN, y), val,
                         fontsize=size, fontname="Inter", color=MID)
        y += size * 1.5 + 4

    def hrule(lw: float = 0.5, col=BORDER):
        nonlocal y
        page.draw_line(fitz.Point(MARGIN, y), fitz.Point(PAGE_W - MARGIN, y),
                       color=col, width=lw)
        y += 8

    # Title block
    text("Shopping List Requisition", size=20, bold=True, color=DARK)
    y -= 4
    text(sl.get("list_number", ""), size=13, color=TEAL_LIGHT)
    y += 4

    status_label = STATUS_LABELS.get(sl.get("status", "draft"), sl.get("status", "").upper())
    text(status_label, size=9, color=GREY)
    y += 12

    hrule(lw=1.0, col=TEAL)

    # Meta block — two-column layout
    meta_y_start = y
    left_x = MARGIN
    right_x = PAGE_W // 2 + 10

    # Left column
    def meta_left(lbl, val, size=9):
        nonlocal y
        page.insert_text(fitz.Point(left_x, y), lbl, fontsize=7, fontname="InterBold", color=GREY)
        y += 9
        page.insert_text(fitz.Point(left_x, y), val or "—", fontsize=size, fontname="Inter", color=MID)
        y += size * 1.5 + 3

    def meta_right(lbl, val, y_pos, size=9):
        page.insert_text(fitz.Point(right_x, y_pos), lbl, fontsize=7, fontname="InterBold", color=GREY)
        page.insert_text(fitz.Point(right_x, y_pos + 9), val or "—", fontsize=size, fontname="Inter", color=MID)

    meta_left("VESSEL", vessel_name)
    r1 = meta_y_start
    meta_right("DEPARTMENT", (sl.get("department") or "general").capitalize(), r1)

    meta_left("LIST NAME", sl.get("name", ""))
    r2 = r1 + 9 + 9 * 1.5 + 3
    meta_right("CURRENCY", sl.get("currency", "EUR"), int(r2))

    created_at = sl.get("created_at", "")[:10] if sl.get("created_at") else "—"
    meta_left("CREATED", created_at)
    r3 = r2 + 9 + 9 * 1.5 + 3
    submitted_at = (sl.get("submitted_at", "") or "")[:10] or "—"
    meta_right("SUBMITTED", submitted_at, int(r3))

    if sl.get("notes"):
        y += 4
        page.insert_text(fitz.Point(MARGIN, y), "NOTES", fontsize=7, fontname="InterBold", color=GREY)
        y += 9
        page.insert_textbox(
            fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 30),
            sl["notes"], fontsize=9, fontname="Inter", color=MID, align=0
        )
        y += 24

    y += 8
    hrule()

    # -------------------------------------------------------------------------
    # Items table
    # -------------------------------------------------------------------------
    currency = sl.get("currency", "EUR")

    # Column layout (points from left margin, total usable = 515)
    # #(20) | Part Name(150) | Part#(60) | Qty(35) | Unit(35) | Unit Price(70) | Total(70) | Status(55) | Notes(rest)
    COL_NUM    = MARGIN
    COL_PART   = COL_NUM + 22
    COL_PARTNO = COL_PART + 152
    COL_QTY    = COL_PARTNO + 62
    COL_UNIT   = COL_QTY + 37
    COL_UP     = COL_UNIT + 37
    COL_TOT    = COL_UP + 72
    COL_STA    = COL_TOT + 72
    COL_NOTES  = COL_STA + 57
    RIGHT_EDGE = PAGE_W - MARGIN

    def th(txt: str, x: int):
        page.insert_text(fitz.Point(x, y), txt, fontsize=7, fontname="InterBold", color=GREY)

    # Table header
    th("#",          COL_NUM)
    th("PART NAME",  COL_PART)
    th("PART NO.",   COL_PARTNO)
    th("QTY",        COL_QTY)
    th("UNIT",       COL_UNIT)
    th("UNIT PRICE", COL_UP)
    th("TOTAL",      COL_TOT)
    th("STATUS",     COL_STA)
    th("NOTES",      COL_NOTES)
    y += 10
    hrule()

    estimated_total = 0.0
    has_candidate = False
    ROW_H = 14

    def _new_page():
        nonlocal page, y
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        page.insert_font(fontname="Inter",     fontfile=inter_regular)
        page.insert_font(fontname="InterBold", fontfile=inter_bold)
        page.draw_rect(fitz.Rect(0, 0, PAGE_W, 5), color=None, fill=TEAL)
        y = 28
        # Continuation header
        page.insert_text(fitz.Point(MARGIN, y),
                         f"Shopping List {sl.get('list_number', '')} — continued",
                         fontsize=9, fontname="InterBold", color=GREY)
        y += 18
        # Re-draw column headers
        th("#",          COL_NUM)
        th("PART NAME",  COL_PART)
        th("PART NO.",   COL_PARTNO)
        th("QTY",        COL_QTY)
        th("UNIT",       COL_UNIT)
        th("UNIT PRICE", COL_UP)
        th("TOTAL",      COL_TOT)
        th("STATUS",     COL_STA)
        th("NOTES",      COL_NOTES)
        y += 10
        page.draw_line(fitz.Point(MARGIN, y), fitz.Point(RIGHT_EDGE, y), color=BORDER, width=0.5)
        y += 8

    for idx, item in enumerate(items, start=1):
        if y > PAGE_H - 80:
            _new_page()

        is_candidate = bool(item.get("is_candidate_part"))
        if is_candidate:
            has_candidate = True

        qty_req  = item.get("quantity_requested")
        qty_appr = item.get("quantity_approved") or qty_req
        up       = item.get("estimated_unit_price") or item.get("unit_price")
        row_total = None
        if qty_appr is not None and up is not None:
            try:
                row_total = float(qty_appr) * float(up)
                estimated_total += row_total
            except (TypeError, ValueError):
                pass

        # Alternate row background for readability
        if idx % 2 == 0:
            page.draw_rect(fitz.Rect(MARGIN - 2, y - ROW_H + 3, RIGHT_EDGE + 2, y + 3),
                           color=None, fill=(0.97, 0.97, 0.97))

        part_name = item.get("part_name", "")
        if is_candidate:
            part_name = f"⚠ {part_name}"

        item_color = DARK if not is_candidate else (0.6, 0.4, 0.0)
        status_str = ITEM_STATUS_LABELS.get(item.get("status", ""), item.get("status", ""))

        def td(txt: str, x: int, col=None, bold: bool = False):
            page.insert_text(fitz.Point(x, y), str(txt) if txt is not None else "—",
                             fontsize=8,
                             fontname="InterBold" if bold else "Inter",
                             color=col or DARK)

        td(str(idx),                    COL_NUM)
        # Part name — may be long, truncate
        pn_display = part_name[:28] + "…" if len(part_name) > 28 else part_name
        td(pn_display,                  COL_PART, col=item_color)
        td(item.get("part_number") or "—", COL_PARTNO, col=GREY)
        # Show approved qty if differs from requested
        qty_display = _fmt_qty(qty_appr)
        if qty_appr != qty_req and qty_req is not None:
            qty_display = f"{_fmt_qty(qty_appr)} ({_fmt_qty(qty_req)})"
        td(qty_display,                 COL_QTY)
        td(item.get("unit") or "—",     COL_UNIT, col=GREY)
        td(_fmt_price(up, ""),          COL_UP)
        td(_fmt_price(row_total, ""),   COL_TOT)
        td(status_str,                  COL_STA, col=GREY)
        notes_display = (item.get("notes") or "")[:20]
        td(notes_display,               COL_NOTES, col=GREY)

        y += ROW_H

    # -------------------------------------------------------------------------
    # Totals
    # -------------------------------------------------------------------------
    y += 4
    hrule()
    page.insert_text(fitz.Point(COL_TOT - 60, y), "ESTIMATED TOTAL",
                     fontsize=8, fontname="InterBold", color=GREY)
    total_str = _fmt_price(estimated_total, currency) if estimated_total else "—"
    page.insert_text(fitz.Point(COL_TOT, y), total_str,
                     fontsize=9, fontname="InterBold", color=DARK)
    y += 14

    if has_candidate:
        page.insert_text(fitz.Point(MARGIN, y),
                         "⚠  Items marked with ⚠ are candidate parts not yet in the parts catalogue.",
                         fontsize=7, fontname="Inter", color=(0.6, 0.4, 0.0))
        y += 12

    # -------------------------------------------------------------------------
    # HOD Approval chain (if applicable)
    # -------------------------------------------------------------------------
    hod_status = sl.get("status", "")
    if hod_status in ("hod_approved", "converted_to_po"):
        y += 8
        hrule(lw=0.5, col=TEAL)
        page.insert_text(fitz.Point(MARGIN, y), "HOD APPROVAL",
                         fontsize=8, fontname="InterBold", color=TEAL_LIGHT)
        y += 12
        approved_at = (sl.get("approved_at") or "")[:16] or "—"
        page.insert_text(fitz.Point(MARGIN, y),
                         f"Approved at: {approved_at} UTC",
                         fontsize=9, fontname="Inter", color=MID)
        y += 12
        if hod_status == "converted_to_po":
            converted_at = (sl.get("converted_at") or "")[:16] or "—"
            po_id = sl.get("converted_to_po_id", "")
            page.insert_text(fitz.Point(MARGIN, y),
                             f"Converted to PO: {po_id[:8]}…  at {converted_at} UTC",
                             fontsize=9, fontname="Inter", color=MID)
            y += 12

    # -------------------------------------------------------------------------
    # Footer
    # -------------------------------------------------------------------------
    footer_y = PAGE_H - 28
    page.draw_line(fitz.Point(MARGIN, footer_y - 8),
                   fitz.Point(PAGE_W - MARGIN, footer_y - 8),
                   color=BORDER, width=0.4)
    page.insert_text(fitz.Point(MARGIN, footer_y),
                     f"Generated {_now_label()} · CelesteOS PMS · Requisition {sl.get('list_number', '')}",
                     fontsize=7, fontname="Inter", color=GREY)

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@router.get("")
async def list_shopping_lists(
    yacht_id: str = Query(...),
    status: str = Query(None),
    department: str = Query(None),
):
    """Return all shopping lists for a vessel, newest first."""
    supabase = get_supabase_client()
    q = supabase.table("pms_shopping_lists").select(
        "id, list_number, name, department, status, currency, "
        "estimated_total, created_by, created_at, submitted_at, "
        "approved_at, converted_at, converted_to_po_id, notes"
    ).eq("yacht_id", yacht_id).order("created_at", desc=True)

    if status:
        q = q.eq("status", status)
    if department:
        q = q.eq("department", department)

    r = q.execute()
    rows = r.data or []

    # Count items per list in one shot
    items_r = supabase.table("pms_shopping_list_items").select(
        "shopping_list_id"
    ).eq("yacht_id", yacht_id).neq("status", "deleted").execute()
    item_counts: dict[str, int] = {}
    for it in (items_r.data or []):
        lid = it.get("shopping_list_id")
        if lid:
            item_counts[lid] = item_counts.get(lid, 0) + 1

    for row in rows:
        row["item_count"] = item_counts.get(row["id"], 0)

    return {"status": "success", "data": rows}


@router.get("/{list_id}")
async def get_shopping_list(
    list_id: str,
    yacht_id: str = Query(...),
):
    """Return a shopping list header + all its items."""
    supabase = get_supabase_client()

    sl_r = supabase.table("pms_shopping_lists").select("*") \
        .eq("id", list_id).eq("yacht_id", yacht_id).single().execute()

    if not sl_r.data:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    sl = sl_r.data

    items_r = supabase.table("pms_shopping_list_items").select("*") \
        .eq("shopping_list_id", list_id).eq("yacht_id", yacht_id) \
        .neq("status", "deleted") \
        .order("created_at", desc=False) \
        .execute()

    sl["items"] = items_r.data or []
    return {"status": "success", "data": sl}


@router.get("/{list_id}/pdf")
async def export_shopping_list_pdf(
    list_id: str,
    yacht_id: str = Query(...),
):
    """
    Export a shopping list as a PDF requisition document.
    Available for: draft, submitted, hod_approved, converted_to_po.
    """
    supabase = get_supabase_client()

    # Fetch list header
    sl_r = supabase.table("pms_shopping_lists").select("*") \
        .eq("id", list_id).eq("yacht_id", yacht_id).single().execute()

    if not sl_r.data:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    sl = sl_r.data

    # Fetch items (exclude soft-deleted)
    items_r = supabase.table("pms_shopping_list_items").select("*") \
        .eq("shopping_list_id", list_id).eq("yacht_id", yacht_id) \
        .neq("status", "deleted") \
        .order("created_at", desc=False) \
        .execute()

    items = items_r.data or []

    # Resolve vessel name
    vessel_name = "Vessel"
    try:
        v_r = supabase.table("fleet_vessels").select("name") \
            .eq("id", yacht_id).single().execute()
        if v_r.data:
            vessel_name = v_r.data.get("name", "Vessel")
    except Exception:
        pass

    try:
        pdf_bytes = _build_shopping_list_pdf(sl, items, vessel_name)
    except ImportError:
        raise HTTPException(status_code=500, detail="PyMuPDF not available on this worker")
    except Exception as exc:
        logger.error(f"[sl_pdf] build failed for {list_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="PDF generation failed")

    list_number = sl.get("list_number", list_id[:8])
    filename = f"shopping-list-{list_number}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

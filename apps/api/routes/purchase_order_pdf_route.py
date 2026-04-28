"""
Purchase Order PDF Export
=========================
GET /v1/purchase-order/{po_id}/pdf

Produces a clean A4 PDF of the purchase order for shore-side procurement.

PDF structure:
  - Teal header bar + PO number + vessel name
  - Meta block: status, supplier, ordered by, dates, tracking
  - Accepted line items table: # / Description / Part No. / Qty / Unit Price / Total
  - Denied items section (with denial reasons)
  - Totals (accepted items only)
  - Footer: generated timestamp + system label
"""

import logging
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from db import get_supabase_client
from routes.auth import get_authenticated_user
from utils.yacht_resolver import resolve_yacht_id
from handlers.purchase_order_handlers import fetch_po_for_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/purchase-order", tags=["purchase-order-pdf"])

PAGE_W = 595
PAGE_H = 842
MARGIN = 40

TEAL       = (0.17, 0.48, 0.64)
TEAL_LIGHT = (0.12, 0.72, 0.9)
GREY       = (0.55, 0.55, 0.55)
DARK       = (0.08, 0.08, 0.08)
MID        = (0.25, 0.25, 0.25)
BORDER     = (0.88, 0.88, 0.88)
RED        = (0.76, 0.15, 0.15)
RED_BG     = (0.99, 0.95, 0.95)


def _now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _fmt_price(val, currency: str = "") -> str:
    if val is None:
        return "—"
    try:
        sym = {"EUR": "€", "GBP": "£"}.get(currency, "$")
        return f"{sym}{float(val):,.2f}"
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


def _fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    return iso[:10]


def _build_po_pdf(po: dict, items: list, vessel_name: str) -> bytes:
    import fitz  # PyMuPDF

    from pathlib import Path
    font_dir = Path(__file__).parent.parent / "assets" / "fonts"
    inter_regular = str(font_dir / "Inter-Regular.ttf") if (font_dir / "Inter-Regular.ttf").exists() else None
    inter_bold    = str(font_dir / "Inter-Bold.ttf")    if (font_dir / "Inter-Bold.ttf").exists()    else None

    currency = po.get("currency", "USD")
    po_number = po.get("po_number") or "PO"
    status = (po.get("status") or "draft").upper()
    supplier = po.get("supplier_name") or po.get("supplier") or "—"
    ordered_by = po.get("ordered_by_name") or "—"
    ordered_at = _fmt_date(po.get("ordered_at") or po.get("created_at") or "")
    tracking_number = po.get("tracking_number") or ""
    carrier = po.get("carrier") or ""
    delivery_start = _fmt_date(po.get("expected_delivery_start") or "")
    delivery_end = _fmt_date(po.get("expected_delivery_end") or "")

    accepted = [i for i in items if (i.get("line_status") or "accepted") != "denied"]
    denied   = [i for i in items if (i.get("line_status") or "accepted") == "denied"]

    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)

    if inter_regular:
        page.insert_font(fontname="Inter",     fontfile=inter_regular)
        page.insert_font(fontname="InterBold", fontfile=inter_bold)
    font      = "InterBold" if inter_bold else "helv"
    font_reg  = "Inter"     if inter_regular else "helv"

    def hrule(y_pos, lw=0.4, col=BORDER):
        page.draw_line(fitz.Point(MARGIN, y_pos), fitz.Point(PAGE_W - MARGIN, y_pos), color=col, width=lw)

    # ── Header bar ───────────────────────────────────────────────────────────
    page.draw_rect(fitz.Rect(0, 0, PAGE_W, 5), color=None, fill=TEAL)
    y = 28
    page.insert_text(fitz.Point(MARGIN, y), "PURCHASE ORDER",
                     fontsize=7, fontname=font, color=GREY)
    page.insert_text(fitz.Point(MARGIN, y + 14), po_number,
                     fontsize=18, fontname=font, color=DARK)
    page.insert_text(fitz.Point(PAGE_W - MARGIN - 80, y + 14), status,
                     fontsize=9, fontname=font,
                     color=TEAL if status not in ("CANCELLED", "DRAFT") else GREY)
    y += 38

    # ── Vessel + supplier ────────────────────────────────────────────────────
    hrule(y)
    y += 10
    half = (PAGE_W - 2 * MARGIN) / 2
    page.insert_text(fitz.Point(MARGIN, y), "VESSEL", fontsize=7, fontname=font, color=GREY)
    page.insert_text(fitz.Point(MARGIN + half, y), "SUPPLIER", fontsize=7, fontname=font, color=GREY)
    y += 10
    page.insert_text(fitz.Point(MARGIN, y), vessel_name[:36], fontsize=10, fontname=font, color=DARK)
    page.insert_text(fitz.Point(MARGIN + half, y), supplier[:36], fontsize=10, fontname=font_reg, color=DARK)
    y += 16

    # ── Meta row ────────────────────────────────────────────────────────────
    hrule(y)
    y += 10
    meta_cols = [
        ("ORDERED BY", ordered_by[:20]),
        ("ORDER DATE", ordered_at),
        ("CURRENCY",   currency),
    ]
    col_w = (PAGE_W - 2 * MARGIN) / len(meta_cols)
    for i, (lbl, val) in enumerate(meta_cols):
        x = MARGIN + i * col_w
        page.insert_text(fitz.Point(x, y), lbl, fontsize=7, fontname=font, color=GREY)
        page.insert_text(fitz.Point(x, y + 10), val, fontsize=9, fontname=font_reg, color=DARK)
    y += 26

    # ── Tracking block (only if present) ─────────────────────────────────────
    if tracking_number or delivery_start:
        hrule(y, col=(0.85, 0.85, 0.85))
        y += 8
        page.insert_text(fitz.Point(MARGIN, y), "TRACKING / DELIVERY",
                         fontsize=7, fontname=font, color=TEAL)
        y += 10
        if tracking_number:
            page.insert_text(fitz.Point(MARGIN, y),
                             f"Tracking: {tracking_number}" + (f"  via {carrier}" if carrier else ""),
                             fontsize=9, fontname=font_reg, color=DARK)
            y += 12
        if delivery_start and delivery_end:
            page.insert_text(fitz.Point(MARGIN, y),
                             f"Expected delivery: {delivery_start} – {delivery_end}",
                             fontsize=9, fontname=font_reg, color=DARK)
            y += 12
        elif delivery_start:
            page.insert_text(fitz.Point(MARGIN, y),
                             f"Expected from: {delivery_start}",
                             fontsize=9, fontname=font_reg, color=DARK)
            y += 12

    # ── Line items table ──────────────────────────────────────────────────────
    y += 6
    hrule(y, lw=0.8, col=TEAL)
    y += 10

    # Column positions
    C_NUM  = MARGIN
    C_DESC = MARGIN + 20
    C_PART = MARGIN + 230
    C_QTY  = MARGIN + 310
    C_UP   = MARGIN + 350
    C_TOT  = MARGIN + 420
    RIGHT  = PAGE_W - MARGIN

    def th(txt, x):
        page.insert_text(fitz.Point(x, y), txt, fontsize=7, fontname=font, color=GREY)

    th("#",          C_NUM)
    th("DESCRIPTION",C_DESC)
    th("PART NO.",   C_PART)
    th("QTY",        C_QTY)
    th("UNIT PRICE", C_UP)
    th("TOTAL",      C_TOT)
    y += 4
    hrule(y, lw=0.4)
    y += 8

    ROW_H = 14
    accepted_total = 0.0

    for idx, item in enumerate(accepted, start=1):
        if y > PAGE_H - 120:
            # New page
            page = doc.new_page(width=PAGE_W, height=PAGE_H)
            if inter_regular:
                page.insert_font(fontname="Inter",     fontfile=inter_regular)
                page.insert_font(fontname="InterBold", fontfile=inter_bold)
            page.draw_rect(fitz.Rect(0, 0, PAGE_W, 5), color=None, fill=TEAL)
            y = 22
            th("#",          C_NUM)
            th("DESCRIPTION",C_DESC)
            th("PART NO.",   C_PART)
            th("QTY",        C_QTY)
            th("UNIT PRICE", C_UP)
            th("TOTAL",      C_TOT)
            y += 4
            page.draw_line(fitz.Point(MARGIN, y), fitz.Point(RIGHT, y), color=BORDER, width=0.4)
            y += 8

        if idx % 2 == 0:
            page.draw_rect(fitz.Rect(MARGIN - 2, y - ROW_H + 3, RIGHT + 2, y + 3),
                           color=None, fill=(0.97, 0.97, 0.97))

        qty = item.get("quantity_ordered") or item.get("quantity") or 0
        up  = item.get("unit_price")
        row_total = None
        if qty and up is not None:
            try:
                row_total = float(qty) * float(up)
                accepted_total += row_total
            except (TypeError, ValueError):
                pass

        desc = (item.get("description") or item.get("name") or item.get("part_name") or "")[:32]
        partno = (item.get("part_number") or "—")[:14]

        def td(txt, x, bold=False, col=None):
            page.insert_text(fitz.Point(x, y), str(txt) if txt is not None else "—",
                             fontsize=8, fontname=font if bold else font_reg, color=col or DARK)

        td(str(idx),              C_NUM,  bold=True)
        td(desc,                  C_DESC)
        td(partno,                C_PART, col=GREY)
        td(_fmt_qty(qty),         C_QTY)
        td(_fmt_price(up, ""),    C_UP)
        td(_fmt_price(row_total, ""), C_TOT, bold=True)
        y += ROW_H

    # ── Totals ────────────────────────────────────────────────────────────────
    y += 4
    hrule(y)
    y += 10
    denied_count = len(denied)
    if denied_count:
        page.insert_text(fitz.Point(C_UP - 40, y),
                         f"({denied_count} line(s) denied — excluded from total)",
                         fontsize=7, fontname=font_reg, color=RED)
        y += 12
    page.insert_text(fitz.Point(C_UP - 20, y), "ORDER TOTAL",
                     fontsize=8, fontname=font, color=GREY)
    page.insert_text(fitz.Point(C_TOT, y), _fmt_price(accepted_total, currency),
                     fontsize=10, fontname=font, color=DARK)
    y += 18

    # ── Denied items section ──────────────────────────────────────────────────
    if denied:
        if y > PAGE_H - 100:
            page = doc.new_page(width=PAGE_W, height=PAGE_H)
            if inter_regular:
                page.insert_font(fontname="Inter",     fontfile=inter_regular)
                page.insert_font(fontname="InterBold", fontfile=inter_bold)
            page.draw_rect(fitz.Rect(0, 0, PAGE_W, 5), color=None, fill=TEAL)
            y = 30

        hrule(y, lw=0.6, col=RED)
        y += 10
        page.insert_text(fitz.Point(MARGIN, y), "DENIED LINE ITEMS — NOT ORDERED",
                         fontsize=8, fontname=font, color=RED)
        y += 12

        for item in denied:
            if y > PAGE_H - 60:
                page = doc.new_page(width=PAGE_W, height=PAGE_H)
                if inter_regular:
                    page.insert_font(fontname="Inter",     fontfile=inter_regular)
                    page.insert_font(fontname="InterBold", fontfile=inter_bold)
                page.draw_rect(fitz.Rect(0, 0, PAGE_W, 5), color=None, fill=TEAL)
                y = 30

            desc = (item.get("description") or item.get("name") or "")[:40]
            reason = (item.get("denial_reason") or "No reason given")[:60]
            page.draw_rect(fitz.Rect(MARGIN - 2, y - 10, PAGE_W - MARGIN + 2, y + 14),
                           color=None, fill=RED_BG)
            page.insert_text(fitz.Point(MARGIN, y), desc,
                             fontsize=9, fontname=font, color=RED)
            page.insert_text(fitz.Point(MARGIN, y + 11), f"Reason: {reason}",
                             fontsize=8, fontname=font_reg, color=MID)
            y += 26

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_y = PAGE_H - 28
    page.draw_line(fitz.Point(MARGIN, footer_y - 8),
                   fitz.Point(PAGE_W - MARGIN, footer_y - 8), color=BORDER, width=0.4)
    page.insert_text(fitz.Point(MARGIN, footer_y),
                     f"Generated {_now_label()} · CelesteOS PMS · {po_number}",
                     fontsize=7, fontname=font_reg, color=GREY)

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@router.get("/{po_id}/pdf")
async def export_purchase_order_pdf(
    po_id: str,
    auth: dict = Depends(get_authenticated_user),
    yacht_id: str = Query(None, description="Vessel scope (fleet users)"),
):
    """Export a purchase order as A4 PDF for shore-side procurement."""
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_supabase_client()

        pdf_data = fetch_po_for_pdf(supabase, po_id, yacht_id)
        po = pdf_data["po"]
        items = pdf_data["items"]
        vessel_name = pdf_data["vessel_name"]

        pdf_bytes = _build_po_pdf(po, items, vessel_name)
        filename = f"{po.get('po_number', po_id)}.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate PO PDF for {po_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

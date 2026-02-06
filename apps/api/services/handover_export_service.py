"""
Handover Export Service
=======================

Generates professional handover reports from handover items.

Schema: Consolidated (2026-02-05)
- handover_items: standalone draft notes (no parent container)
- handover_exports: exported documents with signoff tracking

Pipeline:
1. Fetch items from v_handover_export_items (unified view) or handover_items directly
2. Group by section/category
3. Enrich with entity details (equipment names, fault codes, etc.)
4. Generate formatted HTML with hyperlinks
5. Record export in handover_exports table (draft_id is now nullable)
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone, date
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HandoverItem:
    """Single handover item for export."""
    id: str
    yacht_id: str
    entity_type: str
    entity_id: Optional[str]
    summary_text: str  # Maps from 'summary' column
    category: Optional[str]
    priority: int
    status: str
    added_by: str
    added_at: datetime  # Maps from 'created_at' column
    source_table: str
    section: Optional[str] = None  # Department/section
    handover_id: Optional[str] = None  # Legacy, now nullable
    is_critical: bool = False
    requires_action: bool = False
    action_summary: Optional[str] = None
    risk_tags: List[str] = field(default_factory=list)
    entity_url: Optional[str] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)
    # Enriched fields
    entity_name: Optional[str] = None
    entity_link: Optional[str] = None
    added_by_name: Optional[str] = None


@dataclass
class HandoverSection:
    """Section of grouped handover items."""
    name: str
    display_title: str
    items: List[HandoverItem]
    critical_count: int = 0
    high_priority_count: int = 0


@dataclass
class HandoverExportResult:
    """Result of export generation."""
    export_id: str
    draft_id: Optional[str]
    html: str
    total_items: int
    sections: List[HandoverSection]
    generated_at: datetime
    document_hash: str


# Section ordering and display names
SECTION_CONFIG = {
    'urgent': ('Urgent Items', 1, True),
    'Outstanding Issues': ('Outstanding Issues', 2, True),
    'Issues': ('Issues', 3, True),
    'In Progress': ('Work In Progress', 4, False),
    'in_progress': ('Work In Progress', 4, False),
    'Equipment Status': ('Equipment Status', 5, False),
    'Notes': ('Notes & Instructions', 6, False),
    'watch': ('Watch Items', 7, False),
    'fyi': ('For Your Information', 8, False),
    'completed': ('Completed', 9, False),
    None: ('General', 10, False),
    '': ('General', 10, False),
}


class HandoverExportService:
    """
    Service for generating handover exports.

    Uses the unified view v_handover_export_items or queries handover_items directly.
    Schema: Consolidated (2026-02-05) - handover_items is standalone.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def generate_export(
        self,
        yacht_id: str,
        user_id: str,
        handover_id: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        export_type: str = "html",
        include_completed: bool = False
    ) -> HandoverExportResult:
        """
        Generate a handover export.

        Args:
            yacht_id: The yacht to export for
            user_id: User generating the export
            handover_id: Specific handover to export (optional)
            date_from: Start date filter (optional)
            date_to: End date filter (optional)
            export_type: Format type (html, pdf, email)
            include_completed: Whether to include completed items

        Returns:
            HandoverExportResult with HTML and metadata
        """
        # 1. Fetch items from unified view
        items = await self._fetch_items(
            yacht_id=yacht_id,
            handover_id=handover_id,
            date_from=date_from,
            date_to=date_to,
            include_completed=include_completed
        )

        if not items:
            return self._empty_export(yacht_id, user_id)

        # 2. Extract content_hash (post-consolidation: items are standalone, no draft hash)
        # TODO: If draft-based workflow is restored, fetch content_hash from handover_drafts table
        content_hash = None  # No longer stored in items after consolidation migration

        # 3. Enrich with entity details
        items = await self._enrich_items(items, yacht_id)

        # 4. Group by section
        sections = self._group_by_section(items)

        # 5. Pre-create export record (without document_hash)
        export_id = str(uuid.uuid4())

        # 6. Generate HTML with content_hash and export_id for footer
        html = self._generate_html(sections, yacht_id, date_from, date_to, content_hash, export_id)

        # 7. Calculate document hash from generated HTML
        document_hash = hashlib.sha256(html.encode()).hexdigest()

        # 8. Create export record with both hashes
        await self._create_export_record(
            yacht_id=yacht_id,
            user_id=user_id,
            handover_id=handover_id,
            export_type=export_type,
            document_hash=document_hash,
            total_items=len(items),
            export_id=export_id,
            content_hash=content_hash
        )

        return HandoverExportResult(
            export_id=export_id,
            draft_id=handover_id,
            html=html,
            total_items=len(items),
            sections=sections,
            generated_at=datetime.now(timezone.utc),
            document_hash=document_hash
        )

    async def _fetch_items(
        self,
        yacht_id: str,
        handover_id: Optional[str],
        date_from: Optional[date],
        date_to: Optional[date],
        include_completed: bool
    ) -> List[HandoverItem]:
        """Fetch items from unified view."""

        query = self.db.table("v_handover_export_items").select("*").eq("yacht_id", yacht_id)

        if handover_id:
            query = query.eq("handover_id", handover_id)

        if date_from:
            query = query.gte("shift_date", date_from.isoformat())

        if date_to:
            query = query.lte("shift_date", date_to.isoformat())

        if not include_completed:
            query = query.neq("status", "completed")

        query = query.order("priority", desc=True).order("added_at", desc=True)

        result = query.execute()

        if not result.data:
            return []

        return [
            HandoverItem(
                id=row["id"],
                yacht_id=row["yacht_id"],
                handover_id=row.get("handover_id"),  # Legacy, now nullable
                entity_type=row.get("entity_type") or "",
                entity_id=row.get("entity_id"),
                summary_text=row.get("summary_text") or row.get("summary") or "",
                section=row.get("section"),
                category=row.get("category"),
                priority=row.get("priority", 0),
                status=row.get("status", "pending"),
                is_critical=row.get("is_critical", False),
                requires_action=row.get("requires_action", False),
                action_summary=row.get("action_summary"),
                risk_tags=row.get("risk_tags") or [],
                entity_url=row.get("entity_url"),
                added_by=row.get("added_by") or "",
                added_at=row.get("added_at") or row.get("created_at") or "",
                acknowledged_by=row.get("acknowledged_by"),
                acknowledged_at=row.get("acknowledged_at"),
                metadata=row.get("metadata", {}),
                source_table=row.get("source_table") or "handover_items"
            )
            for row in result.data
        ]

    async def _enrich_items(self, items: List[HandoverItem], yacht_id: str) -> List[HandoverItem]:
        """Enrich items with entity names, links, and user names."""

        # Collect IDs to fetch
        user_ids = set()
        entity_lookups = {
            'fault': set(),
            'work_order': set(),
            'equipment': set(),
            'part': set(),
            'document': set(),
        }

        for item in items:
            user_ids.add(item.added_by)
            if item.acknowledged_by:
                user_ids.add(item.acknowledged_by)
            if item.entity_id and item.entity_type in entity_lookups:
                entity_lookups[item.entity_type].add(item.entity_id)

        # Fetch user names
        user_names = {}
        if user_ids:
            users_result = self.db.table("auth_users_profiles").select(
                "id, name"
            ).in_("id", list(user_ids)).execute()
            if users_result.data:
                user_names = {u["id"]: u["name"] for u in users_result.data}

        # Fetch entity details
        entity_details = {}

        # Faults
        if entity_lookups['fault']:
            faults = self.db.table("pms_faults").select(
                "id, fault_code, title, equipment:equipment_id(name)"
            ).in_("id", list(entity_lookups['fault'])).execute()
            if faults.data:
                for f in faults.data:
                    equip = f.get("equipment", {}) or {}
                    entity_details[f["id"]] = {
                        "name": f"{equip.get('name', '')} - {f.get('fault_code', '')}",
                        "link": f"/faults/{f['id']}"
                    }

        # Work orders
        if entity_lookups['work_order']:
            wos = self.db.table("pms_work_orders").select(
                "id, wo_number, title"
            ).in_("id", list(entity_lookups['work_order'])).execute()
            if wos.data:
                for wo in wos.data:
                    entity_details[wo["id"]] = {
                        "name": f"WO-{wo.get('wo_number', '')} {wo.get('title', '')}",
                        "link": f"/work-orders/{wo['id']}"
                    }

        # Equipment
        if entity_lookups['equipment']:
            equip = self.db.table("pms_equipment").select(
                "id, name, location"
            ).in_("id", list(entity_lookups['equipment'])).execute()
            if equip.data:
                for e in equip.data:
                    entity_details[e["id"]] = {
                        "name": f"{e.get('name', '')} ({e.get('location', '')})",
                        "link": f"/equipment/{e['id']}"
                    }

        # Parts
        if entity_lookups['part']:
            parts = self.db.table("pms_parts").select(
                "id, name, part_number"
            ).in_("id", list(entity_lookups['part'])).execute()
            if parts.data:
                for p in parts.data:
                    entity_details[p["id"]] = {
                        "name": f"{p.get('name', '')} ({p.get('part_number', '')})",
                        "link": f"/parts/{p['id']}"
                    }

        # Enrich items
        for item in items:
            item.added_by_name = user_names.get(item.added_by, "Unknown")
            if item.entity_id and item.entity_id in entity_details:
                item.entity_name = entity_details[item.entity_id]["name"]
                item.entity_link = entity_details[item.entity_id]["link"]

        return items

    def _group_by_section(self, items: List[HandoverItem]) -> List[HandoverSection]:
        """Group items by section/category."""

        sections_map: Dict[str, List[HandoverItem]] = {}

        for item in items:
            section_key = item.category or ''
            if section_key not in sections_map:
                sections_map[section_key] = []
            sections_map[section_key].append(item)

        # Build sections with config
        sections = []
        for section_key, section_items in sections_map.items():
            config = SECTION_CONFIG.get(section_key, ('General', 10, False))
            display_title, order, is_critical = config

            critical_count = sum(1 for i in section_items if i.priority >= 3)
            high_count = sum(1 for i in section_items if i.priority == 2)

            sections.append(HandoverSection(
                name=section_key or 'general',
                display_title=display_title,
                items=sorted(section_items, key=lambda x: (-x.priority, x.added_at)),
                critical_count=critical_count,
                high_priority_count=high_count
            ))

        # Sort sections by configured order
        def section_order(s):
            config = SECTION_CONFIG.get(s.name, SECTION_CONFIG.get('', ('', 10, False)))
            return config[1]

        return sorted(sections, key=section_order)

    def _generate_html(
        self,
        sections: List[HandoverSection],
        yacht_id: str,
        date_from: Optional[date],
        date_to: Optional[date],
        content_hash: Optional[str] = None,
        export_id: Optional[str] = None
    ) -> str:
        """Generate HTML report."""

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Calculate totals
        total_items = sum(len(s.items) for s in sections)
        critical_total = sum(s.critical_count for s in sections)

        # Date range display
        date_display = ""
        if date_from and date_to:
            date_display = f"{date_from.strftime('%d %b %Y')} - {date_to.strftime('%d %b %Y')}"
        elif date_from:
            date_display = f"From {date_from.strftime('%d %b %Y')}"
        elif date_to:
            date_display = f"Until {date_to.strftime('%d %b %Y')}"
        else:
            date_display = "Current Period"

        # Generate sections HTML
        sections_html = ""
        for section in sections:
            items_html = ""
            for item in section.items:
                priority_class = self._priority_class(item.priority)
                status_badge = self._status_badge(item.status)

                # Entity link
                entity_display = ""
                if item.entity_name:
                    if item.entity_link:
                        entity_display = f'<a href="{item.entity_link}" class="entity-link">{item.entity_name}</a>'
                    else:
                        entity_display = f'<span class="entity-name">{item.entity_name}</span>'

                # Critical/action badges
                critical_badge = '<span class="critical-flag">CRITICAL</span>' if item.is_critical else ''
                action_badge = '<span class="action-flag">ACTION REQUIRED</span>' if item.requires_action else ''

                items_html += f'''
                <div class="handover-item {priority_class}{' critical-item' if item.is_critical else ''}">
                    <div class="item-header">
                        <span class="priority-badge {priority_class}">{self._priority_label(item.priority)}</span>
                        {critical_badge}
                        {action_badge}
                        {status_badge}
                        <span class="entity-type">{item.entity_type.upper() if item.entity_type else ''}</span>
                    </div>
                    {f'<div class="entity-ref">{entity_display}</div>' if entity_display else ''}
                    <div class="summary">{item.summary_text}</div>
                    {f'<div class="action-summary"><strong>Action:</strong> {item.action_summary}</div>' if item.action_summary else ''}
                    <div class="meta">
                        Added by {item.added_by_name} &bull; {item.added_at[:16] if isinstance(item.added_at, str) else item.added_at.strftime('%Y-%m-%d %H:%M') if item.added_at else 'Unknown'}
                    </div>
                </div>
                '''

            critical_badge = f'<span class="critical-badge">{section.critical_count} CRITICAL</span>' if section.critical_count > 0 else ''

            sections_html += f'''
            <div class="section">
                <div class="section-header">
                    <h2>{section.display_title}</h2>
                    <span class="item-count">{len(section.items)} items</span>
                    {critical_badge}
                </div>
                <div class="section-items">
                    {items_html}
                </div>
            </div>
            '''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Handover Report - {date_display}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 24px;
            background: #f5f5f5;
            color: #1a1a1a;
        }}
        .report-header {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            color: white;
            padding: 32px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        .report-header h1 {{
            font-size: 28px;
            margin-bottom: 8px;
        }}
        .report-meta {{
            display: flex;
            gap: 24px;
            margin-top: 16px;
            font-size: 14px;
            opacity: 0.9;
        }}
        .stat {{
            background: rgba(255,255,255,0.15);
            padding: 8px 16px;
            border-radius: 6px;
        }}
        .stat-value {{ font-weight: 600; font-size: 18px; }}
        .section {{
            background: white;
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .section-header {{
            background: #f8f9fa;
            padding: 16px 20px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .section-header h2 {{
            font-size: 16px;
            font-weight: 600;
            color: #1e3a5f;
        }}
        .item-count {{
            font-size: 13px;
            color: #6c757d;
        }}
        .critical-badge {{
            background: #dc3545;
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .section-items {{
            padding: 12px;
        }}
        .handover-item {{
            padding: 16px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            margin-bottom: 12px;
            border-left: 4px solid #6c757d;
        }}
        .handover-item:last-child {{ margin-bottom: 0; }}
        .handover-item.critical {{ border-left-color: #dc3545; background: #fff5f5; }}
        .handover-item.high {{ border-left-color: #fd7e14; background: #fff8f0; }}
        .handover-item.normal {{ border-left-color: #0d6efd; }}
        .item-header {{
            display: flex;
            gap: 8px;
            align-items: center;
            margin-bottom: 8px;
        }}
        .priority-badge {{
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .priority-badge.critical {{ background: #dc3545; color: white; }}
        .priority-badge.high {{ background: #fd7e14; color: white; }}
        .priority-badge.normal {{ background: #0d6efd; color: white; }}
        .priority-badge.low {{ background: #6c757d; color: white; }}
        .status-badge {{
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            background: #e9ecef;
        }}
        .status-badge.acknowledged {{ background: #d4edda; color: #155724; }}
        .status-badge.completed {{ background: #cce5ff; color: #004085; }}
        .entity-type {{
            font-size: 10px;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .entity-ref {{
            margin-bottom: 8px;
        }}
        .entity-link {{
            color: #0d6efd;
            text-decoration: none;
            font-weight: 500;
        }}
        .entity-link:hover {{ text-decoration: underline; }}
        .summary {{
            font-size: 14px;
            line-height: 1.5;
            color: #333;
            white-space: pre-wrap;
        }}
        .meta {{
            margin-top: 12px;
            font-size: 12px;
            color: #6c757d;
        }}
        .source-tag {{
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
        }}
        .footer {{
            text-align: center;
            padding: 24px;
            color: #6c757d;
            font-size: 12px;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .section {{ box-shadow: none; border: 1px solid #ddd; }}
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>HANDOVER REPORT</h1>
        <div>{date_display}</div>
        <div class="report-meta">
            <div class="stat">
                <div class="stat-value">{total_items}</div>
                <div>Total Items</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(sections)}</div>
                <div>Sections</div>
            </div>
            {f'<div class="stat" style="background:rgba(220,53,69,0.3)"><div class="stat-value">{critical_total}</div><div>Critical</div></div>' if critical_total > 0 else ''}
        </div>
    </div>

    {sections_html}

    <div class="footer">
        <div style="margin-bottom: 12px;">Generated {generated_at} &bull; CelesteOS Handover Export</div>
        {f'''<div class="verification-hashes">
            <div style="font-size: 11px; color: #6c757d; margin-top: 8px;">
                <div><strong>Content Hash:</strong> <code>sha256:{content_hash[:16]}...</code></div>
                <div style="margin-top: 4px;"><strong>Verify:</strong> <a href="/handover/{export_id}/verify" style="color: #0d6efd;">View Verification Details</a></div>
            </div>
        </div>''' if content_hash and export_id else ''}
    </div>
</body>
</html>'''

    def _priority_class(self, priority: int) -> str:
        """Get CSS class for priority."""
        if priority >= 3:
            return "critical"
        elif priority == 2:
            return "high"
        elif priority == 1:
            return "normal"
        return "low"

    def _priority_label(self, priority: int) -> str:
        """Get label for priority."""
        if priority >= 3:
            return "CRITICAL"
        elif priority == 2:
            return "HIGH"
        elif priority == 1:
            return "NORMAL"
        return "LOW"

    def _status_badge(self, status: str) -> str:
        """Get status badge HTML."""
        status_class = status.lower() if status else "pending"
        status_label = status.replace("_", " ").title() if status else "Pending"
        return f'<span class="status-badge {status_class}">{status_label}</span>'

    async def _create_export_record(
        self,
        yacht_id: str,
        user_id: str,
        handover_id: Optional[str],
        export_type: str,
        document_hash: str,
        total_items: int,
        export_id: str,
        content_hash: Optional[str] = None,
        department: Optional[str] = None
    ) -> str:
        """
        Create record in handover_exports table.

        Schema: Consolidated (2026-02-05)
        - draft_id is now nullable (handover_drafts table was dropped)
        - Items are standalone in handover_items
        - content_hash links to finalized draft
        - document_hash is SHA256 of generated export artifact
        """
        # Insert export record with both hashes
        self.db.table("handover_exports").insert({
            "id": export_id,
            "draft_id": handover_id,  # Can be None now
            "yacht_id": yacht_id,
            "export_type": export_type,
            "department": department,
            "exported_by_user_id": user_id,
            "document_hash": document_hash,
            "content_hash": content_hash,
            "export_status": "completed",
            "exported_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return export_id

    def _empty_export(self, yacht_id: str, user_id: str) -> HandoverExportResult:
        """Return empty export result."""
        html = '''<!DOCTYPE html>
<html><head><title>Handover Report</title></head>
<body style="font-family: sans-serif; padding: 40px; text-align: center;">
<h1>No Handover Items</h1>
<p>No items found for the selected criteria.</p>
</body></html>'''

        return HandoverExportResult(
            export_id="",
            draft_id=None,
            html=html,
            total_items=0,
            sections=[],
            generated_at=datetime.now(timezone.utc),
            document_hash=hashlib.sha256(html.encode()).hexdigest()[:16]
        )


__all__ = ["HandoverExportService", "HandoverExportResult"]

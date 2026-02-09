# Hyperlink System

## Deep Links to Emails, Entities, and Documents

This document defines how handover exports embed clickable links to source materials.

---

## Core Principle

Every item in a handover export should be traceable to its origin.

Links serve three purposes:
1. **Verification** - Reader can confirm source accuracy
2. **Context** - Reader can access full details
3. **Audit** - Investigators can trace decisions

---

## Link Types

### 1. Celeste App Links

Links to entities within the Celeste application.

**Format:** `https://app.celeste7.ai/{entity_type}/{entity_id}`

| Entity Type | URL Pattern | Example |
|-------------|-------------|---------|
| Fault | `/faults/{id}` | `/faults/abc123-...` |
| Work Order | `/work-orders/{id}` | `/work-orders/def456-...` |
| Equipment | `/equipment/{id}` | `/equipment/ghi789-...` |
| Part | `/parts/{id}` | `/parts/jkl012-...` |
| Document | `/documents/{id}` | `/documents/mno345-...` |
| Certificate | `/certificates/{id}` | `/certificates/pqr678-...` |

**Display format in export:**

```html
<a href="https://app.celeste7.ai/faults/abc123" class="entity-link">
  F-2024-0031: Generator 2 cooling fault
</a>
```

---

### 2. Outlook Email Links

Deep links to specific emails in Microsoft Outlook.

**Web format (Outlook Web Access):**
```
https://outlook.office365.com/owa/?ItemID={message_id}&exvsurl=1&viewmodel=ReadMessageItem
```

**Desktop format (Windows):**
```
outlook://message/{message_id}
```

**Extraction from Microsoft Graph:**

```python
def extract_outlook_link(message: dict) -> str:
    """
    Extract Outlook deep link from Graph API message.

    message.webLink provides the OWA URL directly.
    """
    web_link = message.get("webLink")

    if web_link:
        return web_link

    # Fallback: construct from message ID
    message_id = message.get("id")
    return f"https://outlook.office365.com/owa/?ItemID={message_id}&exvsurl=1&viewmodel=ReadMessageItem"
```

**Display format in export:**

```html
<a href="https://outlook.office365.com/owa/?ItemID=..." class="email-link" target="_blank">
  📧 Re: Generator cooling issue - from supplier@vendor.com
</a>
```

---

### 3. Document Storage Links

Links to documents stored in Supabase Storage.

**Format:** Signed URL with expiration

```python
def generate_document_link(storage_path: str, expires_in: int = 86400) -> str:
    """
    Generate time-limited signed URL for document access.

    Args:
        storage_path: Path in Supabase storage
        expires_in: Expiration in seconds (default 24 hours)

    Returns:
        Signed URL string
    """
    response = supabase.storage.from_("documents").create_signed_url(
        storage_path,
        expires_in=expires_in
    )
    return response.get("signedURL")
```

**Display format in export:**

```html
<a href="https://...supabase.co/storage/v1/object/sign/..." class="doc-link" target="_blank">
  📄 Generator Service Manual.pdf
</a>
```

---

### 4. Manual/Technical Reference Links

Links to embedded technical documents and manuals.

**Format:** Document chunk deep link

```
https://app.celeste7.ai/documents/{document_id}?chunk={chunk_id}&highlight=true
```

**Display format:**

```html
<a href="https://app.celeste7.ai/documents/abc123?chunk=def456" class="manual-link">
  📘 Service Manual - Chapter 4.2: Cooling System
</a>
```

---

## Link Resolution Pipeline

When generating exports, links are resolved in this order:

```
┌─────────────────┐
│  Draft Item     │
│  entity_type    │
│  entity_id      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                  ENTITY ENRICHMENT                       │
│                                                          │
│  1. Fetch entity details from relevant table            │
│  2. Extract display name (fault_code, wo_number, etc.)  │
│  3. Build app URL                                       │
│  4. Fetch related sources (emails, documents)           │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│               RELATED SOURCES                            │
│                                                          │
│  Emails:                                                │
│    - Query email_messages by linked_entity_id           │
│    - Extract webLink for each                           │
│                                                          │
│  Documents:                                             │
│    - Query doc_metadata by entity_id                    │
│    - Generate signed URLs                               │
│                                                          │
│  Manual references:                                     │
│    - Query search_document_chunks by entity match       │
│    - Build chunk deep links                             │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│               LINK OBJECT OUTPUT                         │
│                                                          │
│  {                                                      │
│    "primary": {                                         │
│      "type": "fault",                                   │
│      "display": "F-2024-0031",                         │
│      "url": "https://app.celeste7.ai/faults/..."       │
│    },                                                   │
│    "emails": [                                          │
│      {                                                  │
│        "subject": "Re: Generator issue",               │
│        "from": "supplier@vendor.com",                  │
│        "url": "https://outlook.office365.com/..."     │
│      }                                                  │
│    ],                                                   │
│    "documents": [                                       │
│      {                                                  │
│        "name": "Service Manual.pdf",                   │
│        "url": "https://...supabase.co/..."            │
│      }                                                  │
│    ],                                                   │
│    "references": [                                      │
│      {                                                  │
│        "title": "Cooling System - Chapter 4.2",        │
│        "url": "https://app.celeste7.ai/documents/..." │
│      }                                                  │
│    ]                                                    │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
```

---

## Enrichment Service

```python
class LinkEnricher:
    """Enriches handover items with hyperlinks to sources."""

    async def enrich_item(self, item: HandoverItem) -> EnrichedItem:
        """
        Enrich a single handover item with links.

        Fetches:
        - Entity details (name, code, status)
        - Related emails
        - Related documents
        - Manual references
        """

        links = {
            "primary": None,
            "emails": [],
            "documents": [],
            "references": []
        }

        if item.entity_id:
            # Fetch primary entity
            entity = await self._fetch_entity(item.entity_type, item.entity_id)
            if entity:
                links["primary"] = {
                    "type": item.entity_type,
                    "display": self._get_display_name(entity, item.entity_type),
                    "url": f"https://app.celeste7.ai/{item.entity_type}s/{item.entity_id}"
                }

                # Fetch related emails
                emails = await self._fetch_related_emails(item.entity_id)
                links["emails"] = [
                    {
                        "subject": e["subject"],
                        "from": e["from_address"],
                        "date": e["received_at"],
                        "url": e["web_link"]
                    }
                    for e in emails
                ]

                # Fetch related documents
                docs = await self._fetch_related_documents(item.entity_id)
                links["documents"] = [
                    {
                        "name": d["filename"],
                        "url": await self._generate_signed_url(d["storage_path"])
                    }
                    for d in docs
                ]

        return EnrichedItem(
            **item.dict(),
            links=links
        )

    def _get_display_name(self, entity: dict, entity_type: str) -> str:
        """Generate display name for entity."""

        if entity_type == "fault":
            return f"{entity.get('fault_code', 'F-???')}: {entity.get('title', 'Unknown')}"

        if entity_type == "work_order":
            return f"WO-{entity.get('number', '???')}: {entity.get('title', 'Unknown')}"

        if entity_type == "equipment":
            return f"{entity.get('name', 'Unknown')} ({entity.get('location', '')})"

        return entity.get("name", entity.get("title", "Unknown"))
```

---

## HTML Rendering

```html
<!-- Item with links -->
<div class="handover-item critical">
    <div class="item-header">
        <span class="priority-badge critical">CRITICAL</span>
        <span class="entity-type">FAULT</span>
    </div>

    <!-- Primary entity link -->
    <div class="entity-ref">
        <a href="https://app.celeste7.ai/faults/abc123" class="entity-link">
            F-2024-0031: Generator 2 cooling fault
        </a>
    </div>

    <!-- Summary text -->
    <div class="summary">
        Generator 2 showing elevated coolant temperature. Vendor contacted,
        awaiting parts delivery expected Monday.
    </div>

    <!-- Related sources -->
    <div class="sources">
        <div class="source-group emails">
            <span class="source-label">📧 Related emails:</span>
            <ul>
                <li>
                    <a href="https://outlook.office365.com/..." target="_blank">
                        Re: Generator cooling issue - supplier@vendor.com
                    </a>
                </li>
            </ul>
        </div>

        <div class="source-group documents">
            <span class="source-label">📄 Documents:</span>
            <ul>
                <li>
                    <a href="https://...supabase.co/..." target="_blank">
                        Generator Service Manual.pdf
                    </a>
                </li>
            </ul>
        </div>

        <div class="source-group references">
            <span class="source-label">📘 References:</span>
            <ul>
                <li>
                    <a href="https://app.celeste7.ai/documents/..." target="_blank">
                        Cooling System - Chapter 4.2
                    </a>
                </li>
            </ul>
        </div>
    </div>

    <!-- Metadata -->
    <div class="meta">
        Added by John Smith • 2026-02-03 10:30
    </div>
</div>
```

---

## Link Expiration

| Link Type | Expiration | Notes |
|-----------|------------|-------|
| App links | Never | Permanent URLs |
| Outlook links | Never | Tied to message ID |
| Storage signed URLs | 24 hours | Regenerated on export access |
| Document chunk links | Never | Permanent URLs |

**For PDF exports:** All links are embedded at generation time. Signed URLs should use longer expiration (7 days) for PDFs intended for distribution.

---

## Offline Handling

When export is viewed offline:
- App links show destination URL as fallback text
- Email links show subject line and sender
- Document links show filename

```html
<noscript>
    <style>
        .entity-link::after { content: " (" attr(href) ")"; font-size: 10px; }
    </style>
</noscript>
```

---

## Non-Negotiable

- Every entity reference must have a clickable link
- Email links must use webLink from Graph API (not constructed)
- Document links must be signed URLs
- Links must remain visible in printed versions (URL shown)
- No link shorteners or redirects

---

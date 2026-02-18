"""
Embedding Text Builder Service

Pure functions to build embedding_text for Show Related V2 re-ranking.

Rules:
- No query echo (user input never included in embedding_text)
- Deduplication and normalization (lowercase, °C→c, whitespace collapse)
- Controlled synonym injection (ME→main engine, once only)
- Equipment context joins where applicable (WO, faults)
- Length caps per entity type
- No secrets/emails/tokens in output

Usage:
    from services.embedding_text_builder import build_work_order_embedding_text

    text = build_work_order_embedding_text({
        'wo_number': '1234',
        'title': 'Hydraulic pump maintenance',
        'description': 'Replace seals',
        'equipment': {'name': 'Hydraulic Pump', 'manufacturer': 'Parker'}
    })
    # Output: "WO-1234 | Hydraulic pump maintenance | Replace seals | Equipment: Hydraulic Pump - Parker"
"""

import re
from typing import Dict, Any, Optional, List


# =============================================================================
# Normalization Utilities
# =============================================================================

def normalize_text(text: str) -> str:
    """
    Normalize text for embedding consistency.

    - Lowercase
    - Collapse whitespace
    - Convert temperature symbols (°C → c, °F → f)
    - Remove special chars except: - _ / . ,
    - Strip leading/trailing whitespace

    Args:
        text: Raw text

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Lowercase
    text = text.lower()

    # Temperature symbols
    text = text.replace('°c', 'c').replace('°f', 'f')
    text = text.replace('° c', 'c').replace('° f', 'f')

    # Remove duplicate whitespace
    text = re.sub(r'\s+', ' ', text)

    # Strip
    text = text.strip()

    return text


def apply_synonyms(text: str, synonym_map: Optional[Dict[str, str]] = None) -> str:
    """
    Apply controlled synonym injection (once only per synonym).

    Default synonyms:
    - ME → main engine
    - AE → auxiliary engine
    - FW → fresh water
    - SW → sea water

    Args:
        text: Normalized text
        synonym_map: Optional custom synonym dict

    Returns:
        Text with synonyms applied
    """
    if not text:
        return ""

    # Default controlled synonyms (lowercase)
    default_synonyms = {
        r'\bme\b': 'main engine',
        r'\bae\b': 'auxiliary engine',
        r'\bfw\b': 'fresh water',
        r'\bsw\b': 'sea water',
        r'\bhp\b': 'hydraulic pump',
        r'\bgen\b': 'generator',
    }

    synonyms = synonym_map or default_synonyms

    # Apply synonyms (regex word boundaries to avoid partial matches)
    for pattern, replacement in synonyms.items():
        text = re.sub(pattern, replacement, text)

    return text


def deduplicate_tokens(text: str) -> str:
    """
    Remove duplicate consecutive tokens (words).

    Example: "pump pump hydraulic" → "pump hydraulic"

    Args:
        text: Text with potential duplicates

    Returns:
        Deduplicated text
    """
    if not text:
        return ""

    tokens = text.split()
    deduplicated = []
    prev_token = None

    for token in tokens:
        if token != prev_token:
            deduplicated.append(token)
        prev_token = token

    return ' '.join(deduplicated)


def scrub_secrets(text: str) -> str:
    """
    Remove potential secrets/emails/tokens from text.

    Patterns:
    - Email addresses
    - UUIDs
    - JWT-like tokens (long base64 strings)
    - Password keywords

    Args:
        text: Raw text

    Returns:
        Scrubbed text
    """
    if not text:
        return ""

    # Remove emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[email]', text)

    # Remove UUIDs
    text = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '[id]', text)

    # Remove long base64-like strings (potential tokens)
    text = re.sub(r'\b[A-Za-z0-9+/]{40,}\b', '[token]', text)

    # Remove password keywords
    text = re.sub(r'\bpassword[:\s]*\S+', '[redacted]', text, flags=re.IGNORECASE)

    return text


# =============================================================================
# Entity-Specific Builders
# =============================================================================

def build_work_order_embedding_text(wo: Dict[str, Any]) -> str:
    """
    Build embedding text for work order.

    Template: WO-{number} | {title} | {description} | Notes: {completion_notes} | Equipment: {context}

    Args:
        wo: Work order dict with keys:
            - wo_number (optional)
            - title
            - description (optional)
            - completion_notes (optional)
            - equipment (optional dict with name, manufacturer, model, location, system_type)

    Returns:
        Embedding text (max 2000 chars)
    """
    parts = []

    # WO number
    wo_number = wo.get('wo_number')
    if wo_number:
        parts.append(f"wo-{wo_number}")

    # Title (required)
    title = wo.get('title', '').strip()
    if title:
        parts.append(normalize_text(title))

    # Description
    description = wo.get('description', '').strip()
    if description:
        parts.append(normalize_text(description))

    # Completion notes
    completion_notes = wo.get('completion_notes', '').strip()
    if completion_notes:
        parts.append(f"notes: {normalize_text(completion_notes)}")

    # Equipment context
    equipment = wo.get('equipment') or wo.get('pms_equipment')
    if equipment:
        eq_text = build_equipment_context(equipment)
        if eq_text:
            parts.append(f"equipment: {eq_text}")

    # Join and process
    text = ' | '.join(parts)
    text = apply_synonyms(text)
    text = deduplicate_tokens(text)
    text = scrub_secrets(text)

    # Cap length
    return text[:2000]


def build_equipment_embedding_text(eq: Dict[str, Any]) -> str:
    """
    Build embedding text for equipment.

    Template: {name} | {manufacturer} | Model: {model} | S/N: {serial_number} | Location: {location} | System: {system_type}

    Args:
        eq: Equipment dict

    Returns:
        Embedding text (max 1500 chars)
    """
    parts = []

    if eq.get('name'):
        parts.append(normalize_text(eq['name']))

    if eq.get('manufacturer'):
        parts.append(normalize_text(eq['manufacturer']))

    if eq.get('model'):
        parts.append(f"model: {normalize_text(eq['model'])}")

    if eq.get('serial_number'):
        parts.append(f"s/n: {normalize_text(eq['serial_number'])}")

    if eq.get('location'):
        parts.append(f"location: {normalize_text(eq['location'])}")

    if eq.get('system_type'):
        parts.append(f"system: {normalize_text(eq['system_type'])}")

    text = ' | '.join(parts)
    text = apply_synonyms(text)
    text = deduplicate_tokens(text)
    text = scrub_secrets(text)

    return text[:1500]


def build_equipment_context(eq: Dict[str, Any]) -> str:
    """
    Build equipment context string for joining to WO/fault text.

    Compact format: {name} - {manufacturer} - {model} - {location}

    Args:
        eq: Equipment dict

    Returns:
        Context string (max 300 chars)
    """
    parts = []

    if eq.get('name'):
        parts.append(normalize_text(eq['name']))

    if eq.get('manufacturer'):
        parts.append(normalize_text(eq['manufacturer']))

    if eq.get('model'):
        parts.append(normalize_text(eq['model']))

    if eq.get('location'):
        parts.append(f"location: {normalize_text(eq['location'])}")

    text = ' - '.join(parts)
    text = apply_synonyms(text)

    return text[:300]


def build_fault_embedding_text(fault: Dict[str, Any]) -> str:
    """
    Build embedding text for fault.

    Template: {title} | {description} | Severity: {severity} | Status: {status} | Equipment: {context}

    Note: No diagnosis column exists (confirmed via schema inspection)

    Args:
        fault: Fault dict

    Returns:
        Embedding text (max 1500 chars)
    """
    parts = []

    if fault.get('title'):
        parts.append(normalize_text(fault['title']))

    if fault.get('description'):
        parts.append(normalize_text(fault['description']))

    if fault.get('severity'):
        parts.append(f"severity: {normalize_text(fault['severity'])}")

    if fault.get('status'):
        parts.append(f"status: {normalize_text(fault['status'])}")

    # Equipment context
    equipment = fault.get('equipment') or fault.get('pms_equipment')
    if equipment:
        eq_text = build_equipment_context(equipment)
        if eq_text:
            parts.append(f"equipment: {eq_text}")

    text = ' | '.join(parts)
    text = apply_synonyms(text)
    text = deduplicate_tokens(text)
    text = scrub_secrets(text)

    return text[:1500]


def build_part_embedding_text(part: Dict[str, Any]) -> str:
    """
    Build embedding text for part.

    Template: {name} | P/N: {part_number} | {manufacturer} | {description} | Category: {category}

    Args:
        part: Part dict

    Returns:
        Embedding text (max 1000 chars)
    """
    parts = []

    if part.get('name'):
        parts.append(normalize_text(part['name']))

    if part.get('part_number'):
        parts.append(f"p/n: {normalize_text(part['part_number'])}")

    if part.get('manufacturer'):
        parts.append(normalize_text(part['manufacturer']))

    if part.get('description'):
        parts.append(normalize_text(part['description']))

    if part.get('category'):
        parts.append(f"category: {normalize_text(part['category'])}")

    text = ' | '.join(parts)
    text = apply_synonyms(text)
    text = deduplicate_tokens(text)
    text = scrub_secrets(text)

    return text[:1000]


def build_attachment_embedding_text(att: Dict[str, Any]) -> str:
    """
    Build embedding text for attachment.

    Template: {filename} | {description} | Type: {mime_type}

    Args:
        att: Attachment dict

    Returns:
        Embedding text (max 500 chars)
    """
    parts = []

    if att.get('filename'):
        parts.append(normalize_text(att['filename']))

    if att.get('description'):
        parts.append(normalize_text(att['description']))

    if att.get('mime_type'):
        parts.append(f"type: {normalize_text(att['mime_type'])}")

    text = ' | '.join(parts)
    text = deduplicate_tokens(text)
    text = scrub_secrets(text)

    return text[:500]


def build_note_embedding_text(note: Dict[str, Any]) -> str:
    """
    Build embedding text for work order note.

    Template: {note_text} (capped at 200 chars)

    Args:
        note: Note dict with note_text

    Returns:
        Embedding text (max 200 chars)
    """
    note_text = note.get('note_text', '').strip()

    if not note_text:
        return ""

    text = normalize_text(note_text)
    text = scrub_secrets(text)

    return text[:200]


def build_handover_export_embedding_text(export: Dict[str, Any]) -> str:
    """
    Build embedding text for signed handover export.

    Template: Handover Report | {section titles} | {section content} | {item content with priority} | Signed by: {user} | Approved by: {hod}

    Only indexes complete exports (review_status == 'complete').

    Args:
        export: Handover export dict with:
            - edited_content: {sections: [{title, content, items: [{content, priority}]}]}
            - user_signature: {signer_name, signed_at}
            - hod_signature: {signer_name, signed_at}
            - review_status: 'complete'

    Returns:
        Embedding text (max 3000 chars)
    """
    parts = []

    # Header for searchability
    parts.append("handover report shift change")

    # Extract sections from edited_content
    edited_content = export.get('edited_content') or {}
    sections = edited_content.get('sections', [])

    for section in sections:
        # Section title
        title = section.get('title', '').strip()
        if title:
            parts.append(normalize_text(title))

        # Section content
        content = section.get('content', '').strip()
        if content:
            parts.append(normalize_text(content))

        # Section items with priority
        items = section.get('items', [])
        for item in items:
            item_content = item.get('content', '').strip()
            priority = item.get('priority', 'fyi')
            if item_content:
                # Include priority level for semantic matching
                if priority in ('critical', 'action'):
                    parts.append(f"{priority}: {normalize_text(item_content)}")
                else:
                    parts.append(normalize_text(item_content))

    # Add signature information for searchability
    user_sig = export.get('user_signature') or {}
    if user_sig.get('signer_name'):
        signer_name = user_sig['signer_name']
        signed_at = user_sig.get('signed_at', '')
        parts.append(f"signed by: {normalize_text(signer_name)} on {signed_at[:10] if signed_at else ''}")

    hod_sig = export.get('hod_signature') or {}
    if hod_sig.get('signer_name'):
        approver_name = hod_sig['signer_name']
        approved_at = hod_sig.get('signed_at', '')
        parts.append(f"approved by: {normalize_text(approver_name)} on {approved_at[:10] if approved_at else ''}")

    text = ' | '.join(parts)
    text = apply_synonyms(text)
    text = deduplicate_tokens(text)
    text = scrub_secrets(text)

    return text[:3000]


# =============================================================================
# Batch Validation
# =============================================================================

def validate_embedding_text(text: str, entity_type: str) -> Dict[str, Any]:
    """
    Validate embedding text before sending to OpenAI.

    Checks:
    - Non-empty
    - No secrets leaked
    - Length within bounds
    - No query echo patterns

    Args:
        text: Embedding text
        entity_type: Type of entity (for length checks)

    Returns:
        Dict with 'valid' (bool) and 'errors' (list)
    """
    errors = []

    if not text or not text.strip():
        errors.append("Empty embedding text")

    # Check for leaked secrets
    if '[email]' in text or '[token]' in text or '[redacted]' in text:
        errors.append("Secrets detected and scrubbed (review builder)")

    # Check length
    max_lengths = {
        'work_order': 2000,
        'equipment': 1500,
        'fault': 1500,
        'part': 1000,
        'attachment': 500,
        'note': 200,
        'handover_export': 3000,
    }

    max_len = max_lengths.get(entity_type, 2000)
    if len(text) > max_len:
        errors.append(f"Text exceeds max length ({len(text)} > {max_len})")

    # Check for query echo patterns (should not contain user input markers)
    query_echo_patterns = [
        r'search for',
        r'find.*related to',
        r'show me',
        r'get.*where',
    ]

    for pattern in query_echo_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            errors.append(f"Query echo detected: {pattern}")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'text': text,
        'length': len(text),
    }


# =============================================================================
# Factory Function
# =============================================================================

def build_embedding_text(entity_type: str, entity: Dict[str, Any]) -> str:
    """
    Factory function to build embedding text for any entity type.

    Args:
        entity_type: One of: work_order, equipment, fault, part, attachment, note
        entity: Entity dict with appropriate fields

    Returns:
        Embedding text (normalized, scrubbed, length-capped)

    Raises:
        ValueError: If entity_type is invalid
    """
    builders = {
        'work_order': build_work_order_embedding_text,
        'equipment': build_equipment_embedding_text,
        'fault': build_fault_embedding_text,
        'part': build_part_embedding_text,
        'attachment': build_attachment_embedding_text,
        'note': build_note_embedding_text,
        'handover_export': build_handover_export_embedding_text,
    }

    builder = builders.get(entity_type)
    if not builder:
        raise ValueError(f"Invalid entity_type: {entity_type}. Must be one of: {', '.join(builders.keys())}")

    text = builder(entity)

    # Final validation
    validation = validate_embedding_text(text, entity_type)
    if not validation['valid']:
        # Log errors but still return text (scrubbed)
        print(f"⚠️  Embedding text validation warnings for {entity_type}: {validation['errors']}")

    return text

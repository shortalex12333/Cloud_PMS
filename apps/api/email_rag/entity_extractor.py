#!/usr/bin/env python3
"""
Email Entity Extraction Module

Extracts entities (work orders, equipment, parts, suppliers) from email content
and matches them against database records for auto-linking.
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


async def extract_email_entities(
    message_id: str,
    subject: str,
    preview_text: str,
    yacht_id: str,
    supabase
) -> Dict[str, Any]:
    """
    Extract entities from email content and match against database.

    Args:
        message_id: UUID of email_messages record
        subject: Email subject line
        preview_text: Email preview text (first 200 chars)
        yacht_id: UUID of yacht (for RLS)
        supabase: Supabase client

    Returns:
        Dictionary with extracted_entities and entity_matches
    """
    try:
        # Import extraction pipeline (reuse existing code)
        from extraction.orchestrator import ExtractionOrchestrator

        # Combine subject + preview for better entity detection
        full_text = f"{subject}\n\n{preview_text}"

        # Run entity extraction
        orchestrator = ExtractionOrchestrator()
        extraction_result = orchestrator.extract(full_text)

        entities = extraction_result.get('entities', [])

        # Match entities against database
        entity_matches = await match_entities_to_db(entities, yacht_id, supabase)

        # Store in database
        supabase.table('email_messages').update({
            'extracted_entities': {'raw': entities},
            'entity_matches': entity_matches
        }).eq('id', message_id).eq('yacht_id', yacht_id).execute()

        return {
            'entities': entities,
            'matches': entity_matches
        }

    except Exception as e:
        print(f"❌ Entity extraction failed for message {message_id}: {e}")
        return {
            'entities': [],
            'matches': {}
        }


async def match_entities_to_db(
    entities: List[Dict[str, Any]],
    yacht_id: str,
    supabase
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Match extracted entities against database records.

    Args:
        entities: List of extracted entities
        yacht_id: UUID of yacht
        supabase: Supabase client

    Returns:
        Dictionary mapping entity types to matched database records
    """
    matches = {
        'work_orders': [],
        'equipment': [],
        'parts': [],
        'suppliers': []
    }

    try:
        for entity in entities:
            entity_type = entity.get('type', '').lower()
            entity_value = entity.get('value', '')

            if not entity_value:
                continue

            # Match work orders (by ID or title)
            if entity_type in ['work_order', 'wo', 'task']:
                # Try matching by ID (e.g., "WO-1234" or "#1234")
                wo_id_match = re.search(r'(?:WO-?|#)(\d+)', entity_value, re.IGNORECASE)
                if wo_id_match:
                    wo_id = wo_id_match.group(1)
                    result = supabase.table('pms_work_orders').select(
                        'id, title, status'
                    ).eq('yacht_id', yacht_id).ilike('title', f'%{wo_id}%').execute()

                    if result.data:
                        matches['work_orders'].extend(result.data)

                # Try matching by title
                else:
                    result = supabase.table('pms_work_orders').select(
                        'id, title, status'
                    ).eq('yacht_id', yacht_id).ilike('title', f'%{entity_value}%').limit(5).execute()

                    if result.data:
                        matches['work_orders'].extend(result.data)

            # Match equipment (by name or code)
            elif entity_type in ['equipment', 'asset', 'device']:
                result = supabase.table('pms_equipment').select(
                    'id, name, code, location'
                ).eq('yacht_id', yacht_id).or_(
                    f'name.ilike.%{entity_value}%,code.ilike.%{entity_value}%'
                ).limit(5).execute()

                if result.data:
                    matches['equipment'].extend(result.data)

            # Match parts (by name or part number)
            elif entity_type in ['part', 'spare', 'component']:
                result = supabase.table('pms_parts').select(
                    'id, name, part_number, stock_quantity'
                ).eq('yacht_id', yacht_id).or_(
                    f'name.ilike.%{entity_value}%,part_number.ilike.%{entity_value}%'
                ).limit(5).execute()

                if result.data:
                    matches['parts'].extend(result.data)

            # Match suppliers (by name)
            elif entity_type in ['supplier', 'vendor', 'manufacturer']:
                # Note: Add suppliers table when available
                pass

        # Deduplicate matches by ID
        for entity_type in matches:
            seen_ids = set()
            unique_matches = []
            for match in matches[entity_type]:
                if match['id'] not in seen_ids:
                    seen_ids.add(match['id'])
                    unique_matches.append(match)
            matches[entity_type] = unique_matches

        return matches

    except Exception as e:
        print(f"❌ Entity matching failed: {e}")
        return matches


def extract_work_order_references(text: str) -> List[str]:
    """
    Extract work order references from text.

    Args:
        text: Text to search

    Returns:
        List of work order IDs/references
    """
    # Match patterns like: WO-1234, WO1234, #1234, Work Order 1234
    patterns = [
        r'WO-?(\d+)',
        r'#(\d+)',
        r'work\s+order\s+(\d+)',
        r'task\s+(\d+)'
    ]

    references = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        references.extend([m.group(1) for m in matches])

    return list(set(references))  # Deduplicate


def extract_equipment_mentions(text: str) -> List[str]:
    """
    Extract equipment mentions from text.

    Args:
        text: Text to search

    Returns:
        List of equipment names/codes
    """
    # Common equipment keywords
    equipment_keywords = [
        'engine', 'generator', 'pump', 'compressor', 'hvac',
        'motor', 'valve', 'tank', 'battery', 'thruster',
        'windlass', 'anchor', 'radar', 'autopilot', 'navigation'
    ]

    mentions = []
    for keyword in equipment_keywords:
        if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
            mentions.append(keyword)

    return mentions


if __name__ == '__main__':
    # Test entity extraction
    test_text = """
    Subject: Engine Maintenance Required

    Work order #1234 needs attention. The main engine (PORT-ENG-01) requires
    new oil filters (part #ABC-123). Please contact ACME Marine Supplies for pricing.
    """

    print("Testing entity extraction...")

    # Test work order references
    wo_refs = extract_work_order_references(test_text)
    print(f"✅ Work order references: {wo_refs}")

    # Test equipment mentions
    equipment = extract_equipment_mentions(test_text)
    print(f"✅ Equipment mentions: {equipment}")

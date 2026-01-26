#!/usr/bin/env python3
"""
Email RAG Entity Extraction Module

Single-lane regex-based entity extraction for email search queries.
Copied from /apps/api/extraction/regex_extractor.py patterns.

Architecture:
- Input text → Regex patterns → Extracted entities
- No AI fallback (all text goes through embeddings)
- Used at query-time to generate p_entity_keywords for hybrid search
"""

import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class Entity:
    """Extracted entity with metadata."""
    text: str
    entity_type: str
    confidence: float
    span: Tuple[int, int] = None


class EmailEntityExtractor:
    """
    Regex-based entity extractor for email search queries.

    Extracts 17 entity types optimized for maritime domain:
    - equipment, subcomponent, system, location_on_board
    - action, status, symptom
    - measurement, fault_code, model, marine_brand
    - part_number, document_id, time, date
    - network_id, identifier, document_type
    """

    def __init__(self):
        self.patterns = self._load_patterns()
        self.gazetteer = self._load_gazetteer()

    def extract(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from text.

        Args:
            text: Input text (email body or search query)

        Returns:
            Dict mapping entity types to lists of extracted values
        """
        if not text or not text.strip():
            return {}

        results = {}
        text_lower = text.lower()

        # 1. Pattern-based extraction (measurements, fault codes, models, etc.)
        for entity_type, patterns in self.patterns.items():
            matches = set()
            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Get the full match or first group
                    value = match.group(1) if match.groups() else match.group(0)
                    if value:
                        matches.add(value.strip())
            if matches:
                results[entity_type] = list(matches)

        # 2. Gazetteer-based extraction (equipment, actions, etc.)
        for entity_type, terms in self.gazetteer.items():
            matches = set()
            for term in terms:
                # Word boundary match
                pattern = rf'\b{re.escape(term)}\b'
                if re.search(pattern, text_lower):
                    matches.add(term)
            if matches:
                if entity_type in results:
                    results[entity_type].extend(matches)
                else:
                    results[entity_type] = list(matches)

        # Deduplicate all results
        for entity_type in results:
            results[entity_type] = list(set(results[entity_type]))

        return results

    def extract_keywords_for_search(self, text: str) -> List[str]:
        """
        Extract keywords for hybrid search p_entity_keywords parameter.

        Flattens all extracted entities into a single keyword list,
        prioritizing equipment, models, and fault codes.

        Args:
            text: Search query text

        Returns:
            List of keywords for hybrid search
        """
        entities = self.extract(text)

        # Priority order for keywords
        priority_types = [
            'equipment', 'model', 'fault_code', 'marine_brand',
            'part_number', 'measurement', 'subcomponent', 'system',
            'action', 'status', 'symptom'
        ]

        keywords = []
        for entity_type in priority_types:
            if entity_type in entities:
                keywords.extend(entities[entity_type])

        # Add remaining types
        for entity_type, values in entities.items():
            if entity_type not in priority_types:
                keywords.extend(values)

        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                unique_keywords.append(kw)

        return unique_keywords

    def _load_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load regex patterns for each entity type."""
        return {
            # === MEASUREMENTS ===
            'measurement': [
                # Temperature
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*°\s*([CF])\b', re.I),
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(degrees?|deg\.?)\s*([CF])\b', re.I),
                # Voltage
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(VDC|VAC|VCC)\b', re.I),
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*V(?:\s*(DC|AC))?\b'),
                # Current
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(AMP|AMPS|AMPERE|AMPERES)\b', re.I),
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*[mM]?A\b'),
                # Pressure
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(bar|psi|kPa|Pa|mbar|MPa)\b', re.I),
                # Frequency
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(Hz|kHz|MHz)\b', re.I),
                # RPM
                re.compile(r'\b(\d{1,5})\s*(RPM|rev/min)\b', re.I),
                # Power
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(kVA|kW|MW|VA|W|HP|hp|BHP|bhp)\b', re.I),
                # Flow rate
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(L/min|lpm|gpm|m³/h|lph)\b', re.I),
                # Percentage
                re.compile(r'\b(\d{1,3}(?:[.,]\d{1,2})?)\s*(%|percent)\b', re.I),
                # Dimensions
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*mm\b', re.I),
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*cm\b', re.I),
            ],

            # === FAULT CODES (comprehensive maritime/industrial) ===
            'fault_code': [
                # J1939 / OBD / Heavy Engine
                re.compile(r"\bSPN[-_/: ]?\d{1,5}[-_/: ]?FMI[-_/: ]?\d{1,2}\b", re.I),
                re.compile(r"\b(MID|SPN|FMI|PID|SID|CID)\s*[-/:]?\s*\d{1,5}\b", re.I),
                re.compile(r"\b(P|B|C|U)\d{4}\b"),  # OBD codes
                re.compile(r"\bDTC[-_:]?[A-Z0-9]{3,8}\b", re.I),
                # BMS / Energy Systems
                re.compile(r"\b(BMS|CELL|PACK|INV|DCBUS)[-_ ]?(ERR|WARN|TRIP|OV|UV)\b", re.I),
                # PLC / Automation
                re.compile(r"\b(PLC|CPU|IO)[-_]?(ERR|FAULT|FAIL)[-_]?\d{0,3}\b", re.I),
                # VFD / Drives
                re.compile(r"\b([FAW]\d{1,4}(?:[-_]\d{1,3})?)\b"),
                re.compile(r"\b(TRIP|ALARM|WARN|FAULT)[-_ ]?\d{1,4}\b", re.I),
                # NMEA / Navigation
                re.compile(r"\b(ERR[-_]?NAV|GPS[-_ ]?ERR|RADAR[-_ ]?FLT)[-_ ]?\d{0,6}\b", re.I),
                # User-defined Alarms
                re.compile(r"\b(AL|SHDN|WARN|FLT|FAIL)[-_]?\d{1,3}\b", re.I),
            ],

            # === MODEL NUMBERS ===
            'model': [
                # Letter + digits + letters (C32B, D13B, QSM11)
                re.compile(r'\b([A-Za-z]{1,3}\d{1,4}[A-Za-z]?)\b'),
                # Digits + letters (3512C, 3516B)
                re.compile(r'\b(\d{3,4}[A-Za-z]{1,2})\b'),
                # Complex models (6068TFM75, 4045HFM85)
                re.compile(r'\b(\d{3,4}[A-Za-z]{2,4}\d{2,4})\b'),
                # V-engine format (16V4000, 12V-2000)
                re.compile(r'\b(\d{1,2}[Vv]\s*-?\s*\d{3,4})\b'),
            ],

            # === MARINE BRANDS ===
            'marine_brand': [
                re.compile(r'\b(Caterpillar|CAT|Cummins|MTU|Volvo\s+Penta|Yanmar)\b', re.I),
                re.compile(r'\b(Kohler|Northern\s+Lights|Onan|Fischer\s+Panda)\b', re.I),
                re.compile(r'\b(Wärtsilä|Wartsila|MAN|Scania|Perkins)\b', re.I),
                re.compile(r'\b(Raymarine|Furuno|Garmin|Simrad|Navico|B&G)\b', re.I),
                re.compile(r'\b(Victron|Mastervolt|Outback|Magnum)\b', re.I),
            ],

            # === PART NUMBERS ===
            'part_number': [
                re.compile(r'\b[A-Z]{2,4}[-_ ]?\d{3,7}[-_ ]?[A-Z0-9]{1,4}\b'),
                re.compile(r'\b(SN|S/N|SERIAL)\s*[:#]?\s*[A-Z0-9\-]{5,20}\b', re.I),
                re.compile(r'\b(FILTER|OIL|KIT|SEAL|GASKET|BELT)[-_]\d{2,6}\b', re.I),
                re.compile(r'\b\d{3,6}[-_]\d{3,6}(?:[-_][A-Z0-9]{1,3})?\b'),
            ],

            # === DOCUMENT IDs ===
            'document_id': [
                re.compile(r'\b(WO|WORK[-_ ]?ORDER)[-_ #:]?\d{3,8}\b', re.I),
                re.compile(r'\b(SR|SERVICE[-_ ]?REQ)[-_ #:]?\d{3,8}\b', re.I),
                re.compile(r'\b(PO|P/O|PURCHASE[-_ ]?ORDER)[-_ #:]?\d{3,8}\b', re.I),
                re.compile(r'\b(INV|INVOICE)[-_ #:]?\d{3,8}\b', re.I),
                re.compile(r'\b#(\d{4,8})\b'),
            ],

            # === TIME/DATE ===
            'time': [
                re.compile(r'\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\b', re.I),
            ],
            'date': [
                re.compile(r'\b(\d{4}-\d{2}-\d{2})\b'),  # ISO format
                re.compile(r'\b(\d{1,2}/\d{1,2}/\d{4})\b'),  # US format
                re.compile(r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})\b', re.I),
            ],

            # === NETWORK IDs ===
            'network_id': [
                re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'),  # IP
                re.compile(r'\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'),  # MAC
            ],

            # === PROTOCOLS ===
            'marine_protocol': [
                re.compile(r'\b(NMEA\s*0183|NMEA\s*2000|NMEA)\b', re.I),
                re.compile(r'\b(SeaTalk|CANbus|J1939|Modbus)\b', re.I),
                re.compile(r'\b(AIS|GPS|GLONASS|VHF|SSB|VSAT)\b'),
            ],
        }

    def _load_gazetteer(self) -> Dict[str, Set[str]]:
        """Load gazetteer for keyword-based extraction."""
        return {
            'equipment': {
                # Propulsion & Power
                'engine', 'motor', 'generator', 'pump', 'compressor', 'turbine',
                'thruster', 'bow thruster', 'stern thruster', 'propeller', 'shaft',
                'gearbox', 'transmission', 'clutch', 'bearing', 'seal',
                'valve', 'actuator', 'sensor', 'transducer', 'gauge', 'meter',
                'filter', 'strainer', 'cooler', 'heat exchanger', 'radiator',
                'battery', 'battery bank', 'charger', 'inverter', 'converter',
                'breaker', 'circuit', 'switch', 'relay', 'contactor', 'controller',
                # Navigation & Electronics
                'radar', 'gps', 'chart plotter', 'chartplotter', 'vhf', 'ais', 'epirb',
                'autopilot', 'gyro', 'compass', 'echo sounder', 'depth sounder',
                'transponder', 'transceiver',
                # HVAC & Refrigeration
                'refrigerator', 'fridge', 'freezer', 'air conditioner', 'hvac', 'heater', 'chiller',
                # Deck Equipment
                'winch', 'windlass', 'anchor', 'davit', 'crane', 'passerelle',
                # Plumbing
                'toilet', 'head', 'water maker', 'watermaker', 'holding tank', 'bilge pump',
            },

            'subcomponent': {
                'cylinder', 'piston', 'liner', 'crankshaft', 'camshaft',
                'injector', 'turbocharger', 'turbo', 'intercooler',
                'oil pump', 'water pump', 'fuel pump', 'cooling pump',
                'gasket', 'head gasket', 'seal', 'o-ring',
                'belt', 'timing belt', 'v-belt',
                'fuse', 'circuit breaker', 'relay', 'cable', 'wire', 'terminal',
                'oil filter', 'fuel filter', 'air filter', 'water filter',
            },

            'system': {
                'propulsion', 'electrical', 'hydraulic', 'pneumatic', 'fuel',
                'cooling', 'cooling system', 'lubrication', 'exhaust', 'ventilation',
                'navigation', 'communication', 'safety', 'fire suppression',
                'bilge', 'ballast', 'steering', 'power management', 'automation',
            },

            'location_on_board': {
                'bridge', 'flybridge', 'wheelhouse', 'helm', 'engine room',
                'machinery space', 'pump room', 'generator room', 'battery room',
                'deck', 'main deck', 'upper deck', 'lower deck', 'foredeck', 'aft deck',
                'bow', 'stern', 'port', 'starboard', 'midship',
                'cabin', 'master cabin', 'guest cabin', 'saloon', 'galley',
                'crew quarters', 'laundry', 'bilge', 'tank', 'fuel tank', 'water tank',
            },

            'status': {
                'fault', 'alarm', 'warning', 'error', 'trip', 'tripped',
                'failure', 'failed', 'normal', 'running', 'stopped', 'standby',
                'online', 'offline', 'active', 'inactive', 'open', 'closed',
                'scheduled', 'pending', 'in progress', 'completed', 'overdue',
            },

            'symptom': {
                'vibration', 'noise', 'leak', 'leaking', 'overheating', 'smoke',
                'corrosion', 'wear', 'damage', 'crack', 'cracked', 'broken',
                'intermittent', 'fluctuation', 'unstable', 'high', 'low',
                'excessive', 'insufficient', 'abnormal', 'grinding', 'knocking',
            },

            'action': {
                'start', 'stop', 'reset', 'restart', 'reboot',
                'check', 'inspect', 'test', 'calibrate', 'adjust',
                'replace', 'repair', 'service', 'maintain', 'maintenance',
                'clean', 'flush', 'purge', 'prime', 'bleed', 'drain', 'fill',
                'install', 'configure', 'remove', 'troubleshoot', 'diagnose',
                'order', 'purchase', 'schedule', 'approve', 'review',
            },

            'document_type': {
                'manual', 'handbook', 'guide', 'instructions', 'specification',
                'procedure', 'checklist', 'report', 'log', 'diagram', 'schematic',
                'invoice', 'receipt', 'pdf', 'maintenance manual', 'service manual',
            },
        }


# === BACKWARDS COMPATIBILITY FUNCTIONS ===
# These match the original API used by tests

def extract_work_order_references(text: str) -> List[str]:
    """
    Extract work order references from text.

    Args:
        text: Text to search

    Returns:
        List of work order IDs/numbers
    """
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

    return list(set(references))


def extract_equipment_mentions(text: str) -> List[str]:
    """
    Extract equipment mentions from text.

    Args:
        text: Text to search

    Returns:
        List of equipment names
    """
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


def extract_keywords_for_search(text: str) -> List[str]:
    """
    Module-level convenience function to extract keywords for hybrid search.

    Args:
        text: Search query text

    Returns:
        List of keywords for hybrid search p_entity_keywords parameter
    """
    extractor = EmailEntityExtractor()
    return extractor.extract_keywords_for_search(text)


# === ASYNC FUNCTIONS FOR EMAIL PROCESSING ===

async def extract_email_entities(
    message_id: str,
    subject: str,
    preview_text: str,
    yacht_id: str,
    supabase
) -> Dict[str, Any]:
    """
    Extract entities from email content.

    Args:
        message_id: UUID of email_messages record
        subject: Email subject line
        preview_text: Email preview text
        yacht_id: UUID of yacht (for RLS)
        supabase: Supabase client

    Returns:
        Dictionary with extracted entities
    """
    try:
        # Combine subject + preview
        full_text = f"{subject}\n\n{preview_text}"

        # Extract entities using our regex-based extractor
        extractor = EmailEntityExtractor()
        entities = extractor.extract(full_text)

        # Store in email_messages
        await store_extraction_results(
            message_id=message_id,
            yacht_id=yacht_id,
            entities=entities,
            supabase=supabase
        )

        return {'entities': entities}

    except Exception as e:
        print(f"Entity extraction failed for message {message_id}: {e}")
        return {'entities': {}}


async def store_extraction_results(
    message_id: str,
    yacht_id: str,
    entities: Dict[str, List[str]],
    supabase
) -> None:
    """
    Store extraction results in email_extraction_results table.

    Args:
        message_id: UUID of email_messages record
        yacht_id: UUID of yacht
        entities: Dict of entity_type -> list of values
        supabase: Supabase client
    """
    try:
        # Delete existing results for this message
        supabase.table('email_extraction_results').delete().eq(
            'message_id', message_id
        ).execute()

        results_to_insert = []

        # Map entity types to DB-compatible types
        type_mapping = {
            'equipment': 'equipment',
            'subcomponent': 'equipment',
            'system': 'equipment',
            'model': 'equipment',
            'marine_brand': 'supplier',
            'part_number': 'part',
            'document_id': 'work_order',
            'fault_code': 'fault',
            'measurement': 'other',
            'location_on_board': 'other',
            'status': 'other',
            'symptom': 'other',
            'action': 'other',
        }

        for entity_type, values in entities.items():
            mapped_type = type_mapping.get(entity_type, 'other')
            for value in values:
                if value:
                    results_to_insert.append({
                        'yacht_id': yacht_id,
                        'message_id': message_id,
                        'entity_type': mapped_type,
                        'entity_value': str(value)[:255],
                        'confidence': 0.8,  # Regex confidence
                        'found_in': 'body'
                    })

        if results_to_insert:
            # Deduplicate
            seen = set()
            unique_results = []
            for r in results_to_insert:
                key = (r['message_id'], r['entity_type'], r['entity_value'])
                if key not in seen:
                    seen.add(key)
                    unique_results.append(r)

            supabase.table('email_extraction_results').insert(unique_results).execute()
            print(f"Stored {len(unique_results)} extraction results")

    except Exception as e:
        print(f"Failed to store extraction results: {e}")


# === MAIN / TEST ===

if __name__ == '__main__':
    # Test the extractor
    extractor = EmailEntityExtractor()

    test_queries = [
        "engine maintenance 3512C oil change",
        "WO-1234 generator fault code SPN-1234",
        "Caterpillar main engine overheating 95°C",
        "Check the bilge pump in engine room",
        "Yanmar 6LY3-ETP fuel filter replacement",
    ]

    print("Testing EmailEntityExtractor:\n")

    for query in test_queries:
        print(f"Query: {query}")
        entities = extractor.extract(query)
        print(f"  Entities: {entities}")
        keywords = extractor.extract_keywords_for_search(query)
        print(f"  Keywords: {keywords}")
        print()

    # Test backwards compatibility
    print("Testing backwards compatibility:")
    print(f"  WO refs: {extract_work_order_references('WO-1234 and #5678')}")
    print(f"  Equipment: {extract_equipment_mentions('Check the engine and generator')}")

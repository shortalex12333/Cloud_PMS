#!/usr/bin/env python3
"""
Stage 1: Deterministic Extraction (Regex + Gazetteer) - FIXED VERSION
Handles ~85% of extraction through patterns and lookups
Fixed issues:
- Negation scope limited to relevant entity types
- Setpoint/limit patterns extract values only
- Time ranges detected as single entities
- Duration patterns cleaned up
- Tolerance extraction fixed
- Multi-word entity capture improved
"""

import re
import json
import unicodedata
import logging
from typing import Dict, List, Tuple, Set, Optional
from pathlib import Path

# Configure logger
logger = logging.getLogger(__name__)

# Import handling for both direct execution and module import
try:
    from api.regex_production_data import load_manufacturers, load_equipment_terms
    from api.entity_extraction_loader import (
        get_equipment_gazetteer,
        get_diagnostic_patterns,
        calculate_weight as calculate_entity_weight,
        get_pattern_metadata,
        CORE_BRANDS,
        CORE_EQUIPMENT,
        CORE_FUZZY_TERMS,  # Phase 2 Fix: Extended fuzzy matching
        BRAND_ALIASES,     # Phase 2 (2026-02-03): Brand alias normalization
    )
except ModuleNotFoundError:
    from regex_production_data import load_manufacturers, load_equipment_terms
    from entity_extraction_loader import (
        get_equipment_gazetteer,
        get_diagnostic_patterns,
        calculate_weight as calculate_entity_weight,
        get_pattern_metadata,
        CORE_BRANDS,
        CORE_EQUIPMENT,
        CORE_FUZZY_TERMS,  # Phase 2 Fix: Extended fuzzy matching
        BRAND_ALIASES,     # Phase 2 (2026-02-03): Brand alias normalization
    )

# Fuzzy matching for brand misspellings (Fix #4 - 2026-02-02)
try:
    from rapidfuzz import process as fuzz_process, fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not available - fuzzy brand matching disabled")

# Text normalizer for intelligent matching (Phase 2 - 2026-02-03)
try:
    from extraction.text_normalizer import TextNormalizer
    TEXT_NORMALIZER = TextNormalizer()
    NORMALIZER_AVAILABLE = True
except ImportError:
    try:
        from text_normalizer import TextNormalizer
        TEXT_NORMALIZER = TextNormalizer()
        NORMALIZER_AVAILABLE = True
    except ImportError:
        TEXT_NORMALIZER = None
        NORMALIZER_AVAILABLE = False
        logger.warning("text_normalizer not available - using basic matching")

# spaCy/NER removed - system uses regex + gazetteer + AI only
# Reason: Reduces memory footprint, eliminates import errors, simplifies deployment


class Entity:
    """Entity with confidence and source tracking."""
    def __init__(self, text: str, entity_type: str, confidence: float,
                 source: str, span: Tuple[int, int] = None, negated: bool = False,
                 qualifier: str = None, tolerance: str = None, approx: bool = False,
                 metadata: Dict = None):
        self.text = text
        self.type = entity_type
        self.confidence = confidence
        self.source = source  # 'regex', 'gazetteer', or 'ai'
        self.span = span  # (start, end) in normalized text
        self.negated = negated  # True if entity is negated
        self.qualifier = qualifier  # 'above', 'below', 'limit', 'setpoint', etc.
        self.tolerance = tolerance  # '±10V', '±2°C', etc.
        self.approx = approx  # True if approximate value (~, about, circa)
        self.metadata = metadata or {}  # Domain/subdomain/group metadata for weight calculation


class RegexExtractor:
    """Deterministic extraction via regex patterns and gazetteer."""

    # Negation patterns for safety-critical detection
    NEGATION_PATTERNS = [
        r'\bdo\s+not\b',
        r'\bdon\'t\b',
        r'\bdoes\s+not\b',
        r'\bdoesn\'t\b',
        r'\bdid\s+not\b',
        r'\bdidn\'t\b',
        r'\bnever\b',
        r'\bno\b',
        r'\bnot\b',
        r'\bwithout\b',
        r'\bunless\b',
        r'\bavoid\b',
        r'\bprevent\b'
    ]

    # Entity types that should check for negation
    NEGATION_RELEVANT_TYPES = {
        'action', 'status', 'symptom', 'equipment', 'system'
    }

    # Qualifier patterns for measurements
    QUALIFIER_PATTERNS = {
        'above': r'\b(above|over|exceeds?|greater\s+than|more\s+than|>\s*)\b',
        'below': r'\b(below|under|less\s+than|lower\s+than|<\s*)\b',
        'at_least': r'\b(at\s+least|minimum|min|≥|>=)\b',
        'at_most': r'\b(at\s+most|maximum|max|≤|<=)\b',
        'exactly': r'\b(exactly|precisely|=)\b',
        'approximately': r'\b(approximately|approx|about|around|circa|~|≈)\b',
        'limit': r'\b(limit)\b',
        'setpoint': r'\b(setpoint|target|reference)\b'
    }

    # Context patterns for confidence scoring (per entity type)
    CONTEXT_PATTERNS = {
        'fault_code': {
            'positive': re.compile(
                r'\b(code|error|fault|alarm|warning|trip|dtc|spn|fmi|mid|obd|j1939|'
                r'ecu|tcm|bcm|pcm|module|controller|diagnostic|plc|cpu|assert|panic|'
                r'exception|errno|fail|timeout|event)\b', re.I
            ),
            'negative': re.compile(
                r'\b(HTTP|SMTP|IMAP|POP3|DNS|URL|JPEG|JPG|PNG|GIF|MP4|MP3|PDF|'
                r'UTC|GMT|EST|CST|PST|MST|AES|RSA|SHA|MD5|TLS|SSL|'
                r'www\.|\.com|\.org|\.net|@)\b', re.I
            )
        },
        'part_number': {
            'positive': re.compile(
                r'\b(part|pn|p/n|serial|sn|s/n|component|module|assembly|assy|'
                r'kit|filter|oil|gasket|seal|belt|hose|sensor|cable|board|'
                r'pcb|fuse|breaker|battery|inverter|pump|valve|bearing)\b', re.I
            ),
            'negative': re.compile(
                r'\b(http|www|\.com|\.org|@|year|date|time|january|february|march|'
                r'april|may|june|july|august|september|october|november|december)\b', re.I
            )
        },
        'model': {
            'positive': re.compile(
                r'\b(engine|genset|generator|model|mtu|cat|caterpillar|cummins|yanmar|'
                r'man|volvo|deere|scania|perkins|john deere)\b', re.I
            ),
            'negative': None
        },
        'version': {
            'positive': re.compile(
                r'\b(firmware|software|version|build|release|update|patch|commit|git|sw|fw)\b', re.I
            ),
            'negative': None
        },
        'smart_systems': {
            'positive': re.compile(
                r'\b(cloud|iot|edge|gateway|bms|battery|inverter|ai|ml|model|'
                r'auth|login|certificate|satellite|gps|comms|link)\b', re.I
            ),
            'negative': None
        },
        'hidden_entities': {
            'positive': re.compile(
                r'\b(hash|crc|checksum|uuid|guid|device|firmware|build|memory|register)\b', re.I
            ),
            'negative': None
        }
    }

    # Precedence order for extraction (highest to lowest priority)
    # NEW: Added po_number, designation, product_name, descriptor
    # CRITICAL FIX: Model MUST come before part_number to prevent misclassification
    # "3512C" should match model first, not part_number pattern
    PRECEDENCE_ORDER = [
        'fault_code',          # CRITICAL: Must be before po_number to prevent "SPN-1234" being extracted as PO
        'location_on_board',   # LOCATION: Multi-word locations (engine room) before equipment names
        'certificate_type',    # NEW: Extract "class certificates" before "class" becomes generic
        'voyage_type',         # NEW: Extract "at sea", "in port" for crew queries
        'work_order_type',     # NEW: Extract "corrective maintenance" before "corrective"
        'equipment',           # NEW: Extract "gen 1", "genset 2" numbered equipment
        'work_order_status',   # WORK ORDERS: Extract "open work orders" BEFORE "open" becomes symptom
        'rest_compliance',     # CREW: Extract "non-compliant" BEFORE "compliant" becomes status
        'warning_severity',    # CREW: Extract "critical warning" BEFORE "critical" becomes symptom
        'delivery_date',       # RECEIVING: Extract "recent deliveries" as single phrase
        'receiving_status',    # RECEIVING: Extract "pending receipt" vs generic "pending"
        'stock_status',        # INVENTORY: Must be before measurements to catch "low stock" before "low" as symptom
        'equipment_status',    # NEW: Equipment operational status (operational, failed, degraded)
        'exclusion',           # NEW: Exclusion patterns (except, excluding)
        'quantity_comparison', # NEW: Quantity comparisons (below 5, more than 10)
        'measurement',         # MOVED UP: Process measurements (230V, 50Hz, 45W) BEFORE model patterns
        'measurement_range',   # MOVED UP: Process ranges before models
        'setpoint',            # MOVED UP: Setpoints before models
        'limit',               # MOVED UP: Limits before models
        'document_id',         # DOCUMENT LENS: Extract document IDs (CERT-, IMO-, DNV-) BEFORE part_number
        'document_type',       # DOCUMENT LENS: Extract document types BEFORE generic terms
        'model',               # Model codes after measurements to prevent false matches
        'part_number_prefix',  # NEW: Extract "starting with FLT" before generic patterns
        'part_number',         # After model and document_id to avoid matching doc IDs as parts
        'serial_number',       # Serial numbers should be before po_number
        'designation',         # Manual/doc codes (SEBU6250-30)
        'po_number',           # Business docs - but lower priority than parts/faults
        'smart_systems',       # Cloud/IoT/BMS/AI systems
        'hidden_entities',     # Technical IDs, hashes, firmware builds
        'product_name',        # Multi-word product names (AH Maxx CW)
        'version',
        'descriptor',          # Descriptors (smart, mini, digital)
        'time',
        'date',
        'network_id',
        'identifier',
        'email_search',
        'time_ref',
        'duration',
        'time_range'
    ]

    def __init__(self):
        self.patterns = self._load_patterns()
        self.gazetteer = self._load_gazetteer()
        self.negation_regex = re.compile('|'.join(self.NEGATION_PATTERNS), re.IGNORECASE)
        self.qualifier_regex = {k: re.compile(v, re.IGNORECASE)
                                for k, v in self.QUALIFIER_PATTERNS.items()}

        # Load ENTITY_EXTRACTION_EXPORT patterns (1,955 patterns)
        print("🔧 Loading ENTITY_EXTRACTION_EXPORT patterns...")
        self.entity_extraction_gazetteer = get_equipment_gazetteer()
        self.entity_extraction_patterns = get_diagnostic_patterns()
        print(f"   ✅ Loaded {len(self.entity_extraction_gazetteer['equipment_brand']):,} equipment brands")
        print(f"   ✅ Loaded {sum(len(p) for p in self.entity_extraction_patterns.values())} diagnostic patterns")

    def _load_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load regex patterns for each entity type."""
        patterns = {
            # Inventory stock status patterns (HIGH PRIORITY - extract before symptoms)
            # Location phrases - both multi-word AND single-word locations (Fix 2026-02-03)
            # Must extract BEFORE equipment patterns claim spans like "galley refrigerator"
            'location_on_board': [
                # Multi-word location phrases (must extract as complete phrases)
                re.compile(r'\b(engine\s+room|machinery\s+space|pump\s+room|generator\s+room|battery\s+room|control\s+room|chart\s+table|helm\s+station|nav\s+station|wing\s+station|main\s+deck|upper\s+deck|lower\s+deck|sun\s+deck|boat\s+deck|aft\s+deck|fore\s+deck|crew\s+quarters|crew\s+mess|anchor\s+locker|chain\s+locker|bilge\s+area|swim\s+platform|tender\s+garage|port\s+side|starboard\s+side|master\s+cabin|guest\s+cabin|vip\s+cabin|crew\s+cabin|cold\s+room|steering\s+gear\s+room|bow\s+thruster\s+room)\b', re.IGNORECASE),
                # Single-word locations (Fix 2026-02-03 - were only in gazetteer, not regex)
                re.compile(r'\b(galley|bridge|bilge|bow|stern|foredeck|flybridge|wheelhouse|helm|cockpit|salon|saloon|pantry|laundry|lazarette|forepeak|afterpeak|midship|midships|locker|storage|gangway|passerelle|transom)\b', re.IGNORECASE),
                # Directional terms as standalone locations (but NOT when part of equipment like "port engine")
                # Use negative lookahead to avoid matching "port engine", "starboard generator", etc.
                re.compile(r'\b(port|starboard|fore|aft)(?!\s+(?:engine|generator|thruster|pump|side\s+(?:engine|generator)))\b', re.IGNORECASE),
            ],
            'stock_status': [
                # Multi-word stock status phrases (must come BEFORE single-word patterns)
                # Fix: Added optional "to" in "needs? to reorder" pattern
                # Phase 2 (2026-02-03): Added negative stock patterns
                re.compile(r'\b(low\s+stock|out\s+of\s+stock|below\s+minimum|critically\s+low|needs?\s+(?:to\s+)?reorder|reorder\s+needed|minimum\s+stock|stock\s+level|running\s+low|need\s+restocking|needs?\s+restocking|restock|below\s+reorder\s+point|reorder\s+point)\b', re.IGNORECASE),
                # NEW: Negative stock patterns
                re.compile(r'\b(not\s+in\s+stock|no\s+stock|zero\s+stock|empty\s+stock|depleted|exhausted|none\s+(?:in\s+)?stock)\b', re.IGNORECASE),
                # NEW: Stock availability positive
                re.compile(r'\b(in\s+stock|available|on\s+hand|stocked)\b', re.IGNORECASE),
                # Single keyword variants (only if not part of equipment name)
                re.compile(r'\b(inventory|stock)\b(?!\s+(?:pump|valve|filter|sensor))', re.IGNORECASE),
            ],
            # Crew Lens - Hours of Rest & Warnings (PR #64)
            # Phase 2 (2026-02-03): Enhanced compliance patterns
            'rest_compliance': [
                re.compile(r'\b(non-compliant|non\s+compliant|compliant|rest\s+hours|work\s+hours|hours\s+of\s+rest|duty\s+hours|fatigue|rest\s+period)\b', re.IGNORECASE),
                # NEW: Violation patterns
                re.compile(r'\b(violation|violations|breach|breaches|infringement|non-compliance|noncompliance)\b', re.IGNORECASE),
                # NEW: MLC compliance terms
                re.compile(r'\b(mlc|mlc\s+2006|mlc\s+compliant|stcw|stcw\s+compliant)\b', re.IGNORECASE),
            ],
            'warning_severity': [
                re.compile(r'\b(critical\s+warning|warning|alert|severe|moderate\s+warning)\b', re.IGNORECASE),
            ],
            # Phase 2 (2026-02-03): Numbered equipment abbreviations
            # Extracts "gen 1" → "generator 1", "eng 2" → "engine 2"
            'equipment': [
                re.compile(r'\b(gen(?:erator)?\s*[#]?\s*[12])\b', re.IGNORECASE),  # gen 1, gen 2, generator 1
                re.compile(r'\b(eng(?:ine)?\s*[#]?\s*[12])\b', re.IGNORECASE),     # eng 1, engine 1
                re.compile(r'\b(genset\s*[#]?\s*[12])\b', re.IGNORECASE),          # genset 1, genset 2
                re.compile(r'\b(aux\s*[#]?\s*[12])\b', re.IGNORECASE),             # aux 1, aux 2
                re.compile(r'\b(chiller\s*[#]?\s*[12])\b', re.IGNORECASE),         # chiller 1, chiller 2
                re.compile(r'\b(pump\s*[#]?\s*[12])\b', re.IGNORECASE),            # pump 1, pump 2
            ],

            # Phase 2 (2026-02-03): Voyage type patterns
            # For crew hours of rest queries: "at sea", "in port"
            'voyage_type': [
                re.compile(r'\b(at\s+sea|at\s+anchor|in\s+port|underway|moored|docked|berthed|alongside)\b', re.IGNORECASE),
                re.compile(r'\b(sea\s+passage|coastal\s+waters|port\s+stay)\b', re.IGNORECASE),
            ],

            # Phase 2 (2026-02-03): Certificate type patterns
            # For document queries: "class certificates", "environmental certificates"
            'certificate_type': [
                re.compile(r'\b(class|classification)\s+certificate', re.IGNORECASE),
                re.compile(r'\b(safety)\s+certificate', re.IGNORECASE),
                re.compile(r'\b(environmental)\s+certificate', re.IGNORECASE),
                re.compile(r'\b(loadline|load\s+line)\s+certificate', re.IGNORECASE),
                re.compile(r'\b(manning)\s+certificate', re.IGNORECASE),
                re.compile(r'\b(ism|isps|iopp|ispp|solas)\s+certificate', re.IGNORECASE),
                # Standalone certificate types (must be followed by "certificate" context in query)
                re.compile(r'\b(class|environmental|safety|loadline|manning|registration)\b(?=.*certificate)', re.IGNORECASE),
            ],

            # Phase 2 (2026-02-03): Work order type patterns
            'work_order_type': [
                re.compile(r'\b(corrective|preventive|scheduled|emergency|planned|unplanned)\s+(?:maintenance|work|task)', re.IGNORECASE),
                re.compile(r'\b(pm|cm)\b', re.IGNORECASE),  # PM = preventive maintenance, CM = corrective
            ],

            # Work Order Lens (PR #64) - Must extract BEFORE symptom patterns
            # FIX Issue #2: Require "work" keyword for order phrases to prevent capturing shopping list queries
            # Phase 2 (2026-02-03): Added negative status patterns
            'work_order_status': [
                re.compile(r'\b(open\s+work\s+orders?|closed\s+work\s+orders?|in\s+progress|overdue\s+(?:tasks?|work\s+orders?)|completed\s+work\s+orders?|pending\s+work\s+orders?)\b', re.IGNORECASE),
                re.compile(r'\b(work\s+orders?)\b', re.IGNORECASE),
                # NEW: Negative completion patterns (expanded for systemic coverage)
                re.compile(r'\b(not\s+(?:completed|complete|finished|done)|incomplete|unfinished|uncompleted|unfinished|pending)\b', re.IGNORECASE),
                # NEW: Status patterns
                re.compile(r'\b(planned|scheduled|in_progress|cancelled|deferred)\b', re.IGNORECASE),
            ],
            # NEW: Equipment operational status (Phase 2 - 2026-02-03)
            'equipment_status': [
                re.compile(r'\b(operational|not\s+operational|inoperative|non-operational|out\s+of\s+service|in\s+service)\b', re.IGNORECASE),
                re.compile(r'\b(failed|failing|degraded|under\s+maintenance|being\s+serviced|offline|online)\b', re.IGNORECASE),
            ],
            # NEW: Exclusion patterns (Phase 2 - 2026-02-03)
            # For queries like "all parts except filters", "everything but pumps"
            'exclusion': [
                re.compile(r'\b(?:except|excluding|except\s+for|not\s+including|other\s+than|but\s+not)\s+(\w+(?:\s+\w+)?)\b', re.IGNORECASE),
                re.compile(r'\b(?:without|minus)\s+(\w+(?:\s+\w+)?)\b', re.IGNORECASE),
            ],
            # NEW: Quantity comparison patterns (Phase 2 - 2026-02-03)
            # For queries like "parts with quantity below 5", "more than 10 in stock"
            'quantity_comparison': [
                re.compile(r'\b(?:below|under|less\s+than|fewer\s+than|<)\s*(\d+)\b', re.IGNORECASE),
                re.compile(r'\b(?:above|over|more\s+than|greater\s+than|>)\s*(\d+)\b', re.IGNORECASE),
                re.compile(r'\b(?:at\s+least|minimum|>=)\s*(\d+)\b', re.IGNORECASE),
                re.compile(r'\b(?:at\s+most|maximum|<=)\s*(\d+)\b', re.IGNORECASE),
                re.compile(r'\b(zero|0)\s*(?:stock|quantity|in\s+stock|on\s+hand)?\b', re.IGNORECASE),
            ],
            # Receiving Lens (PR #64)
            'delivery_date': [
                re.compile(r'\b(recent\s+deliver(?:y|ies)|last\s+deliver(?:y|ies)|deliver(?:y|ies)\s+(?:today|yesterday|this\s+week))\b', re.IGNORECASE),
            ],
            'receiving_status': [
                re.compile(r'\b(pending\s+receipt|received|in\s+transit|delivered|awaiting\s+delivery)\b', re.IGNORECASE),
            ],
            'measurement': [
                # Temperature patterns
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*°\s*([CF])\b', re.IGNORECASE),
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(degrees?|deg\.?)\s*([CF])\b', re.IGNORECASE),

                # Voltage patterns (enhanced for VDC/VAC and multi-voltage)
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(VDC|VAC|VCC)\b', re.I),  # 27.6 VDC, 120 VAC
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*V(?:\s*(DC|AC|CC))?\b'),  # 27.6V, 27.6 V DC
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(k|m)?V\b'),  # 12V, 24V
                re.compile(r'\b(\d+(?:[.,]\d+)?)/(\d+(?:[.,]\d+)?)\s*V(?:AC|DC)?\b'),  # Multi-value like 230V/400V, 24/12VDC
                re.compile(r'\b(\d+(?:[.,]\d+)?)-(\d+(?:[.,]\d+)?)\s*V(?:AC|DC)?\b'),  # Range like 380-480VAC

                # Current patterns (enhanced - fixed to catch "45A")
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(AMP|AMPS|AMPERE|AMPERES)\b', re.I),  # 12.5 AMP
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*[mM]?A\b'),  # 12.5 A, 500 mA, 45A
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(amp(?:ere)?s?)\b', re.IGNORECASE),

                # Pressure patterns (including EU format)
                re.compile(r'\b(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s*(bar|psi|kPa|Pa|mbar|MPa)\b', re.IGNORECASE),

                # Frequency
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(Hz|kHz|MHz)\b', re.I),

                # RPM (enhanced - now captures as single unit)
                re.compile(r'\b(\d{1,5}(?:[.,]\d{3})*)\s*(RPM|rev/min)\b', re.I),  # 1800 RPM, 1,800 RPM

                # Power (enhanced with kVA, VA support)
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(kVA|kW|MW|VA|W|HP|hp|BHP|bhp)\b', re.I),

                # Flow rate
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(L/min|lpm|gpm|m³/h|lph)\b', re.IGNORECASE),

                # Percentage
                re.compile(r'\b(\d{1,3}(?:[.,]\d{1,2})?)\s*(%|percent)\b', re.I),

                # Dimensions (length, diameter, etc.)
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*mm\b', re.IGNORECASE),
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*cm\b', re.IGNORECASE),
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*m\b(?!in)', re.IGNORECASE),  # meters, not "min"
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*inch(?:es)?\b', re.IGNORECASE),
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*ft\b', re.IGNORECASE),
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*["\']', re.IGNORECASE),  # inches/feet marks

                # Count/Quantity
                re.compile(r'\b(\d+)\s*(?:cylinders?|pistons?|units?)\b', re.IGNORECASE),
            ],

            # COMPREHENSIVE FAULT CODES (maritime, PLC, automation, BMS, energy, IoT, IT systems)
            # IMPORTANT: Ordered by specificity - most specific patterns FIRST to avoid partial matches
            'fault_code': [
                # --- BMS / Energy / Hybrid Systems (HIGH PRIORITY - SPECIFIC) ---
                # Flexible pattern to handle: BMS-OV-001, CELL-UV-TRIP, INV-DC-OV, DCBUS-ERR
                re.compile(r"\b(BMS|CELL|PACK|INV|DCBUS|INVERTER|FUELCELL|H2|HYBRID)[-_ ]?(DC[-_ ]?)?(ERR|WARN|TRIP|OV|UV|OVR|UND|COMM|TEMP)([-_ ]?(ERR|WARN|TRIP|OV|UV|OVR|UND|COMM|TEMP))?([-_ ]?\d{1,3})?\b", re.I),

                # --- Predictive Maintenance / Service Codes (HIGH PRIORITY - SPECIFIC) ---
                re.compile(r"\b(PM|MAINT|SRV|SERVICE|RUNTIME|TBO|REM)[-_]?\d{2,5}(H|HR|HRS|%)?\b", re.I),
                re.compile(r"\b(INSPECT|REPLACE|CLEAN|OVERHAUL)[-_ ]?(INTERVAL|SCHD|DUE|500H)?\b", re.I),

                # --- J1939 / OBD / Heavy Engine (SPECIFIC PATTERNS FIRST) ---
                # Full compound codes (MUST come before individual components)
                re.compile(r"\bSPN[-_/: ]?\d{1,5}[-_/: ]?FMI[-_/: ]?\d{1,2}\b", re.I),  # SPN-1234-FMI-5, SPN:1234:FMI:5
                re.compile(r"\bMID\s*\d+\s*(PSID|PPID|PID|SID|CID)\s*\d+\s*FMI\s*\d+\b", re.I),
                re.compile(r"\b(PID|SID|CID)\s*[-/:]?\s*\d{1,4}\s*FMI\s*[-:]?\s*\d{1,2}\b", re.I),
                # Then individual components
                re.compile(r"\b(MID|SPN|FMI|PID|SID|CID)\s*[-/:]?\s*\d{1,5}\b", re.I),
                re.compile(r"\b(P|B|C|U)\d{4}\b"),
                re.compile(r"\bDTC[-_:]?[A-Z0-9]{3,8}\b", re.I),
                re.compile(r"\bE\d{3,4}[-_]\d\b"),
                re.compile(r"\b(0x[0-9A-Fa-f]{3,10})\b"),

                # --- ABB / Danfoss / VFD / Drives ---
                re.compile(r"\b([FAW]\d{1,4}(?:[-_]\d{1,3})?)\b"),
                re.compile(r"\b(TRIP|ALARM|WARN|FAULT)[-_ ]?\d{1,4}\b", re.I),

                # --- PLC / Automation / IO Faults ---
                re.compile(r"\b(I[O/]?[O]?|DI|DO|AI|AO|PLC|CPU)[-_]?(ERR|FAULT|FAIL)[-_]?\d{0,3}\b", re.I),
                re.compile(r"\b(DO|DI|AI|AO|PLC|FB|MOD)[-_ ]?(ERR|FLT|FAIL|TIMEOUT|COMM)[-_ ]?\d{0,3}\b", re.I),

                # --- NMEA / Navigation / Bridge Systems ---
                re.compile(r"\b(ERR[_-]?NAV|NMEA2?000|AIS[-_ ]?ALERT|GPS[-_ ]?ERR|RADAR[-_ ]?FLT)[-_ ]?\d{0,6}\b", re.I),
                re.compile(r"\bPGN\d{5,6}\b"),

                # --- Windows/Linux / System Log Events ---
                re.compile(r"\b(Event\s?ID|Evt|Kernel|Critical|Exception|System\.Exception)[-_ :]*\d{0,6}\b", re.I),
                re.compile(r"\b(Exception|TypeError|Unhandled|Code)\s?:?\s?(\d{1,6}|E\d{3})\b", re.I),

                # --- IoT / Sensor / Device Node Faults ---
                re.compile(r"\b(NODE\d{1,3}[-_ ]?(ERR|FAULT|FAIL|TIMEOUT|ALM)\b)", re.I),
                re.compile(r"\b(SENSOR|DEVICE|SENS|PROBE|UNIT)[-_ ]?\d{1,3}[-_ ]?(ERR|FAIL|TIMEOUT)\b", re.I),

                # --- JSON / REST / API / Software Exceptions ---
                re.compile(r"\b(HTTP|API|REST|JSON|EXC|ERR|SQL|ORA|PG|MYSQL|NET|TLS|SSL)[-_ ]?(ERR|CODE|FAIL|TIMEOUT|STATUS|EXC|ID)?[-_ ]?\d{0,5}\b", re.I),
                re.compile(r"\b(ORA|SQLSTATE|PGERR|PGSQL|EXC_[A-Z_]+)\b", re.I),

                # --- CANopen / Modbus / Profibus ---
                re.compile(r"\b(COB[-_ ]?ID\s*\d{3,4}h?|CAN[-_ ]?ID\s*[0-9A-F]{3,6}|MOD[-_ ]?[A-Za-z0-9]{1,3}\d?)\b", re.I),
                re.compile(r"\b(DM[1-9]):?\s*(SPN\s*\d{1,5})\b", re.I),

                # --- Manufacturer-specific "C" Series (Volvo / Bosch / DDEC) ---
                re.compile(r"\bC\d{3,5}[A-Z0-9]{0,2}\b"),

                # --- User-defined Alarms / Electrical Panels ---
                re.compile(r"\b(AL|SHDN|WARN|FLT|FAIL)[-_]?\d{1,3}\b", re.I),
                re.compile(r"\b(CB|FUSE|ISO)[-_ ]?(TRIP|OPEN|FLT|FAIL)[-_ ]?\d{1,3}\b", re.I),

                # --- Diesel / CAN DM Messages ---
                re.compile(r"\b(DM[1-9])[:\s-]*(SPN|FMI|PID|SID)\s*\d{1,5}\b", re.I),

                # --- Sensor Diagnostic Flags ---
                re.compile(r"\b(SENS|SIG|TEMP|PRESS|FLOW|LEVEL|VOLT|AMP)[-_ ]?(LOSS|FAIL|HI|LOW|LO|DEVIATION|OUT|RANGE|ERR)\b", re.I),

                # --- Firmware / Assert / Stack ---
                re.compile(r"\b(ASSERT|PANIC|STACK|OVERFLOW|MEM|EXC)[-_ ]?[A-Z0-9]{1,8}\b", re.I),

                # --- Telemetry / Gateway / OTA ---
                re.compile(r"\b(GW|TX|RX|LINK|COMM)[-_ ]?(ERR|FAIL|TIMEOUT|DROP|RESET)[-_ ]?\d{0,3}\b", re.I),

                # --- Network / Ethernet / VLAN ---
                re.compile(r"\b(ARP|IP|NIC|LAN|WIFI|SW|ETH|NET)[-_ ]?(DUP|COLL|ERR|FAIL|DOWN|UP)[-_ ]?\d{0,3}\b", re.I),

                # --- Database / Logging / IT Layer ---
                re.compile(r"\b(SQLSTATE|ORA|PGERR|DB|LOG|EVENT)[-_ ]?\d{2,6}\b", re.I),

                # --- Alert Levels / Group IDs ---
                re.compile(r"\b(AL\d{1,2})\b"),
            ],

            # Diagnostic phrase patterns (natural language fault descriptions) (PRIORITY 3 - NEW)
            'fault_phrase': [
                # Sensor/device disconnection
                re.compile(r"\b(sensor|transducer|probe)\s+(disconnected|offline|missing)\b", re.I),
                # Communication failures
                re.compile(r"\b(no\s+response|no\s+comm|not\s+responding|timeout)\b", re.I),
                # Data integrity issues
                re.compile(r"\b(invalid|bad|corrupt)\s+(checksum|packet|data)\b", re.I),
                # Range violations
                re.compile(r"\b(out\s?of\s?range|beyond\s?limit|over\s?limit)\b", re.I),
                # Electrical faults
                re.compile(r"\b(short\s?circuit|open\s?circuit|to\s?ground|earth\s?fault)\b", re.I),
                # Thermal issues
                re.compile(r"\b(over[- ]?temp(?:erature)?|over[- ]?heat|thermal\s?trip)\b", re.I),
                # Parameter deviations
                re.compile(r"\b(voltage|pressure|current|load|flow)\s+(deviation|fluctuation|instability|drop|rise)\b", re.I),
            ],

            'time': [
                re.compile(r'\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\b', re.IGNORECASE),
                re.compile(r'\b(\d{1,2}:\d{2}(?::\d{2})?\s*Z)\b'),  # Zulu time
                re.compile(r'\b(\d{1,2})\s*(am|pm)\b', re.IGNORECASE),
            ],

            'date': [
                re.compile(r'\b(\d{4}-\d{2}-\d{2})\b'),  # ISO format
                re.compile(r'\b(\d{1,2}/\d{1,2}/\d{4})\b'),  # US format
                re.compile(r'\b(\d{1,2}\.\d{1,2}\.\d{4})\b'),  # EU format
                re.compile(r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})\b', re.IGNORECASE),
            ],

            'network_id': [
                # IP addresses
                re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'),
                # MAC addresses
                re.compile(r'\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'),
                # Port numbers
                re.compile(r'\bport\s+(\d{1,5})\b', re.IGNORECASE),
            ],

            'document_id': [
                # NOTE: PO, WO, SR, Invoice patterns moved to 'po_number' section
                # Document Lens v2 - Enhanced patterns for maritime document references

                # Original patterns
                re.compile(r'\b(DOC-[A-Z]-\d{2,4})\b'),  # Generic documents
                re.compile(r'\b(REF-\d{5,8})\b'),  # Reference numbers

                # Certificate Reference Numbers
                re.compile(r'\b(CERT[-/]?\d{4,8})\b', re.IGNORECASE),
                re.compile(r'\b(CRT[-/]?\d{4,8})\b', re.IGNORECASE),

                # Maritime Authority Document Numbers (7-digit IMO is standard)
                re.compile(r'\b(IMO[-/]?\d{7})\b', re.IGNORECASE),
                re.compile(r'\b(USCG[-/]?\d{4,10})\b', re.IGNORECASE),
                re.compile(r'\b(MCA[-/]?\d{4,8})\b', re.IGNORECASE),
                re.compile(r'\b(MARAD[-/]?\d{4,8})\b', re.IGNORECASE),

                # Class Society Document References
                re.compile(r'\b(LR[-/]?\d{4,8})\b', re.IGNORECASE),
                re.compile(r'\b(DNV[-/]?[A-Z]?\d{4,8})\b', re.IGNORECASE),
                re.compile(r'\b(ABS[-/]?\d{4,8})\b', re.IGNORECASE),
                re.compile(r'\b(BV[-/]?\d{4,8})\b', re.IGNORECASE),
                re.compile(r'\b(RINA[-/]?\d{4,8})\b', re.IGNORECASE),
                re.compile(r'\b(NK[-/]?\d{4,8})\b', re.IGNORECASE),
                re.compile(r'\b(CCS[-/]?\d{4,8})\b', re.IGNORECASE),

                # Safety Management Document References
                re.compile(r'\b(ISM[-/]?\d{4,8})\b', re.IGNORECASE),
                re.compile(r'\b(ISPS[-/]?\d{4,8})\b', re.IGNORECASE),
                re.compile(r'\b(SMC[-/]?\d{4,8})\b', re.IGNORECASE),

                # Document Revision/Version References
                re.compile(r'\b(REV[-.]?\d{1,3}(?:\.\d{1,2})?)\b', re.IGNORECASE),
                re.compile(r'\b(ISSUE[-.]?\d{1,3})\b', re.IGNORECASE),

                # Generic Document Reference Patterns
                re.compile(r'\b([A-Z]{2,4}-\d{4}-\d{2,4})\b'),
            ],


            # NEW COMPREHENSIVE MODEL PATTERNS (ordered by specificity)
            'model': [
                # A) letter + 3 digits + 2-3 letters → v100NX, V100NX, a123AB
                re.compile(r'\b([A-Za-z]\d{3}[A-Za-z]{2,3})\b'),

                # B) 1-2 letters + 2-4 digits + 1 letter (C32B, D13B, Q7a)
                re.compile(r'\b([A-Za-z]{1,2}\d{2,4}[A-Za-z])\b'),

                # C) 1-3 letters + 1-4 digits (QSM11, QSC83, D13, C32, A3, A4)
                re.compile(r'\b([A-Za-z]{1,3}\d{1,4})\b'),

                # C2) 2-3 digits + 2-4 letters (34DF, 64H, 16V) - NEW for Wärtsilä models
                re.compile(r'\b(\d{2,3}[A-Za-z]{2,4})\b'),

                # C3) 3-4 digits + 1-2 letters (3516C, 3516c, 1800B, 2000A) - Caterpillar/Cummins models
                re.compile(r'\b(\d{3,4}[A-Za-z]{1,2})\b'),

                # D) digits + letters + digits (6068TFM75, 4045HFM85)
                re.compile(r'\b(\d{3,4}[A-Za-z]{2,4}\d{2,4})\b'),

                # E) digit + letters + digit + dash + letters → 6LY3-ETP
                re.compile(r'\b(\d{1,2}[A-Za-z]{1,3}\d{1,2}-[A-Za-z]{2,4})\b'),

                # G) models with slash → 8/9, 10/12, 6/22 (not dates)
                re.compile(r'\b(\d{1,2}/\d{1,2})\b'),

                # V-engine format (MTU/Detroit Diesel)
                re.compile(r'\b(\d{1,2}[Vv]\s*-?\s*\d{3,4})\b'),  # 16V4000, 12V-2000

                # NOTE: SEBU6250-30 pattern removed - now only in 'designation' to avoid duplicates
            ],

            # Marine equipment brands (Gospel high-frequency terms)
            'marine_brand': [
                # Top brand names from Gospel analysis (Gospel FN: raymarine=26x, furuno=29x, wartsila=34x)
                re.compile(r'\b(Raymarine|Furuno|Garmin|Simrad|Navico|B&G)\b', re.I),
                re.compile(r'\b(Wärtsilä|Wartsila)\b', re.I),  # With and without umlaut
                re.compile(r'\b(Caterpillar|Cummins|MTU|Volvo\s+Penta|Yanmar)\b', re.I),
                re.compile(r'\b(Kohler|Northern\s+Lights|Onan|Fischer\s+Panda)\b', re.I),
                re.compile(r'\b(Victron|Mastervolt|Outback|Magnum)\b', re.I),
                re.compile(r'\b(Icom|Standard\s+Horizon|Uniden)\b', re.I),
                re.compile(r'\b(4GConnect|Pepwave|Cradlepoint|Sierra\s+Wireless)\b', re.I),
            ],

            # Marine technical protocols and standards (Gospel high-frequency terms)
            'marine_protocol': [
                # Top protocols from Gospel analysis (Gospel FN: nmea=92x, nmea2000=30x, nmea0183=8x)
                re.compile(r'\b(NMEA\s*0183|NMEA0183|NMEA-0183)\b', re.I),
                re.compile(r'\b(NMEA\s*2000|NMEA2000|NMEA-2000)\b', re.I),
                re.compile(r'\b(NMEA)\b', re.I),  # Generic NMEA (after specific versions)
                re.compile(r'\b(SeaTalk|SeaTalkNG|SeaTalk-NG)\b', re.I),
                re.compile(r'\b(CANbus|CAN\s+bus|CAN-bus)\b', re.I),
                re.compile(r'\b(J1939)\b'),
                re.compile(r'\b(Modbus|ModbusTCP|Modbus-TCP|Modbus\s+RTU)\b', re.I),
                re.compile(r'\b(AIS|GPS|GLONASS|Galileo)\b'),
                re.compile(r'\b(VHF|UHF|SSB|VSAT)\b'),
            ],

            # Software/Firmware/Build versions
            'version': [
                # Semantic versioning (v1.2.3, 5.11.9, v2.5.1-beta)
                re.compile(r'\bv?(\d+\.\d+(?:\.\d+)?(?:-[A-Za-z0-9]+)?)\b'),

                # Prefixed versions (SW-2.5.1, FW 5.11.9, VER 1.0.0)
                re.compile(r'\b(SW|FW|VER|VERSION|REL|REV)[-_ ]?(\d+(?:\.\d+){0,3})\b', re.I),

                # Build numbers (BUILD 0421, BUILD-20231015)
                re.compile(r'\bBUILD[-_ ]?(\d{3,12})\b', re.I),
            ],

            # COMPREHENSIVE PART NUMBERS (mechanical + electrical + IT hardware)
            # IMPORTANT: Most specific patterns FIRST to avoid partial matches
            'part_number': [
                # --- Generic supplier/manufacturer SKUs (HIGHEST PRIORITY - must match before generic patterns) ---
                re.compile(r'\b[A-Z]{2,4}[-_ ]?\d{3,7}[-_ ]?[A-Z0-9]{1,4}\b'),  # MTU-12345-XYZ, VOL-861123-9

                # --- Electronic S/N with explicit labels (HIGH PRIORITY) ---
                re.compile(r'\b(SN|S/N|SERIAL|ID#?)\s*[:#]?\s*[A-Z0-9\-]{5,20}\b', re.I),  # SN 1234A567, S/N: MT1234567X

                # --- Accessory/consumable variations (HIGH PRIORITY) ---
                # FIX: Require separator for suffix
                re.compile(r'\b(FILT(ER)?|OIL|KIT|SEAL|GASKET|BELT|HOSE)[-_]\d{2,6}(?:[-_][A-Z0-9]{1,3})?\b', re.I),  # FILTER-12345, OIL-9876-KIT

                # --- Classic Engine / OEM ---
                re.compile(r"\b\d{1,3}[A-Z]?-\d{3,4}\b"),  # Dash required to avoid matching bare 7-digit PO numbers
                re.compile(r"\b\d{2,3}[.\-]?\d{4,6}[-_]?\d{3,5}\b"),
                re.compile(r"\b\d{6,7}[-_][A-Z0-9]\b"),
                re.compile(r"\b\d{6,8}[A-Z]{1,2}\b"),  # Requires at least 1 letter to avoid matching bare PO numbers
                re.compile(r"\b\d{3,6}[-_]\d{3,6}(?:[-_][A-Z0-9]{1,3})?\b"),
                re.compile(r"\b([A-Z]{2,5}-\d{3,7}[A-Z0-9]{0,3})\b"),
                re.compile(r"\b\d{3,7}[-_][A-Z0-9]{1,3}\b"),

                # --- Electrical / Electronics ---
                # FIX: Require separators
                re.compile(r"\b(PCB|ELECTR|BOARD|MODULE|PSU|DRV|CARD)[-_]\d{3,6}(?:[-_][A-Z0-9]{1,4})*\b", re.I),
                re.compile(r"\b(REV|VER|BOARD)[-_][A-Z]?\d{1,3}\b", re.I),
                re.compile(r"\b(MODULE|PSU|CTRL)[-_][A-Z0-9]{2,6}\b", re.I),

                # --- Sensors / Transducers ---
                # FIX: Require separators
                re.compile(r"\b(PT|LM|TSP|PRS|TEMP|SENS)[-_][A-Z0-9]{0,3}[-_]?\d{2,6}\b", re.I),

                # --- Cables / Connectors ---
                # FIX: Require separators
                re.compile(r"\b(CABL|CONN|M12|HARN|WIRE|PLUG|SOCK)[-_]\d{2,5}(?:[-_][A-Z0-9]{0,3})?\b", re.I),

                # --- Switchgear / Breakers ---
                # FIX: Require separators
                re.compile(r"\b(CBR|MCB|FUSE|BREAKER|ISO)[-_]\d{2,6}(?:[A-Z0-9-]{0,3})?\b", re.I),

                # --- Consumables / Fluids ---
                # FIX: Require separators
                re.compile(r"\b(OIL|LUBE|COOL|HYD|FLUID|GREASE)[-_]\d{1,4}(?:[A-Z0-9/%]{0,4})?\b", re.I),

                # --- Kits / Assemblies / Service ---
                # FIX: Require separators
                re.compile(r"\b(KIT|SERV|ASSY|SET|PARAM|CFG|CONFIG|BUILD)[-_][A-Z0-9]{1,8}\b", re.I),

                # --- Filters / Pumps ---
                # FIX: Require separators
                re.compile(r"\b(FIL|FILT(ER)?|FLTR|PMP|PUMP|FUEL|WTR)[-_][A-Z0-9]{1,8}\b", re.I),

                # --- Nav / Comms Equipment ---
                # FIX: Require separator if suffix present, or match acronym alone
                re.compile(r"\b(AIS|GPS|RADAR|ICOM|SAT|VSAT|VHF|NAV|COMP|PLOTTER)(?:[-_][A-Z0-9]{2,8})?\b", re.I),

                # --- Batteries / Power ---
                # FIX: Require separators
                re.compile(r"\b(BAT|INV|CHG|UPS|ALT|RECT|PSU)[-_]\d{2,5}(?:[A-Z0-9]{0,4})?\b", re.I),
                re.compile(r"\b(\d{2,3}[Vv][-_/ ]?\d{1,4}[AaHhWw]{1,2})\b"),

                # --- Hydraulics / Pneumatics ---
                # FIX: Require separators
                re.compile(r"\b(VALVE|ACT|CYL|HYD|PNEU)[-_]\d{2,5}(?:[A-Z0-9-]{0,4})?\b", re.I),

                # --- HVAC / Environment ---
                # FIX: Require separators
                re.compile(r"\b(COMP|FAN|THERM|TEMPCTRL|CHILL|VENT|AIR)[-_]\d{2,5}(?:[A-Z0-9-]{0,3})?\b", re.I),

                # --- Safety / Alarms ---
                # FIX: Require separators
                re.compile(r"\b(FIRE|ALRM|BELL|HORN|GAS|SENS|SMK|EMERG)[-_]\d{2,5}(?:[A-Z0-9]{0,3})?\b", re.I),

                # --- IT / Server / Network Hardware ---
                # FIX: Require separators
                re.compile(r"\b(RAM|SSD|HDD|NIC|SFP|SW|LAN|SRV|CPU|GPU|FPGA)[-_]\d{2,5}(?:[A-Z0-9-]{0,4})?\b", re.I),

                # NOTE: Generic supplier SKUs, S/N labels, and accessory patterns moved to TOP of list for priority
            ],

            # Part number prefix patterns (ID-007 fix - 2026-02-03)
            # For queries like "parts starting with FLT", "part numbers beginning with CAT"
            'part_number_prefix': [
                re.compile(r'\b(?:starting|beginning|starts?|begins?)\s+with\s+([A-Z]{2,5})\b', re.IGNORECASE),
                re.compile(r'\bprefix\s+([A-Z]{2,5})\b', re.IGNORECASE),
                re.compile(r'\b([A-Z]{2,5})\s+(?:prefix|prefixed)\b', re.IGNORECASE),
            ],

            # Serial numbers (SN, S/N, Serial No.)
            'serial_number': [
                re.compile(r"\b(SN|S/N|SERIAL)\s*[:#]?\s*[A-Z0-9\-]{5,20}\b", re.I),
            ],

            # Hidden technical IDs (hashes, addresses, device IDs, firmware builds)
            'hidden_entities': [
                re.compile(r"\b(CRC32|MD5|SHA1|HASH)[:=]?[A-Fa-f0-9]{8,32}\b", re.I),
                re.compile(r"\b0x[0-9A-Fa-f]{2,10}\b"),
                re.compile(r"\b0b[01]{6,16}\b"),
                re.compile(r"\b(DevID|HWID|DeviceID|UID|GUID|UUID|SN|SERIAL)[:=#]?\s?[A-Z0-9\-]{5,20}\b", re.I),
                re.compile(r"\b\d{8}[_-]\d{4}\b"),
                re.compile(r"\b\d{2}[-_/]\d{2}[-_/]\d{2,4}[-_]\d{2,4}[Hh]?\b"),
            ],

            # Smart systems (cloud, IoT, BMS, AI/ML, auth, satellite)
            'smart_systems': [
                re.compile(r"\b(AWS|AZURE|EDGE|IOT|THINGID|HUB|GATEWAY)[-_ ]?(ERR|FAIL|TIMEOUT|ID|403|502|504)?\b", re.I),
                re.compile(r"\b(AI|ML|MODEL|DATA|PRED|DL|NN|ANALYTICS)[-_ ]?(MOD|SRV|PROC|V|VER|ID)?[-_ ]?\d{0,5}\b", re.I),
                # BMS codes moved to fault_code category (line 318) for better precedence
                re.compile(r"\b(AUTH|LOGIN|CERT|TLS|SSL)[-_ ]?(FAIL|EXPIRED|ERR|DENIED|403|401)\b", re.I),
                re.compile(r"\b(SAT|VSAT|LINK|GPS|SIG|COMMS|NET)[-_ ]?(LOSS|ERR|DOWN|UP|DROP)\b", re.I),
            ],

            'identifier': [
                # Technology identifiers (4G, 5G, LTE, WiFi)
                re.compile(r'\b([345]G|LTE|Wi-?Fi)\b', re.IGNORECASE),
                # Generic identifiers (less specific)
                re.compile(r'\b([A-Z]{3}\d{3}-\d{3}-[A-Z0-9]{3})\b'),  # Generic IDs
                # Phase 2 Fix: Pure numeric identifiers (2026-02-02)
                # 4-8 digit numbers that could be part_number, work_order_id, po_number
                re.compile(r'^(\d{4,8})$'),  # Standalone 4-8 digit numbers
                re.compile(r'\b(0\d{2,7})\b'),  # Numbers with leading zeros
            ],

            'document_type': [
                # Multi-word document types (must be first to prevent word-by-word extraction)
                re.compile(r'\b(ballast\s+water\s+record\s+book)\b', re.IGNORECASE),
                re.compile(r'\b(continuous\s+synopsis\s+record)\b', re.IGNORECASE),
                re.compile(r'\b(cargo\s+record\s+book)\b', re.IGNORECASE),
                re.compile(r'\b(oil\s+record\s+book)\b', re.IGNORECASE),
                re.compile(r'\b(garbage\s+record\s+book)\b', re.IGNORECASE),
                re.compile(r'\b(fire\s+control\s+plan)\b', re.IGNORECASE),
                re.compile(r'\b(damage\s+control\s+plan)\b', re.IGNORECASE),
                re.compile(r'\b(safety\s+management\s+certificate)\b', re.IGNORECASE),
                re.compile(r'\b(loadline\s+certificate)\b', re.IGNORECASE),
                re.compile(r'\b(loadline)\b', re.IGNORECASE),  # Fix 2026-02-03: Single word loadline
                re.compile(r'\b(class\s+certificate)\b', re.IGNORECASE),  # Fix 2026-02-03: DNV class certificate
                re.compile(r'\b(annual\s+survey)\b', re.IGNORECASE),
                re.compile(r'\b(special\s+survey)\b', re.IGNORECASE),
                re.compile(r'\b(class\s+survey)\b', re.IGNORECASE),

                # Compound document types
                re.compile(r'\b(maintenance\s+(?:manual|guide|schedule|log))\b', re.IGNORECASE),
                re.compile(r'\b(user\s+(?:manual|guide))\b', re.IGNORECASE),
                re.compile(r'\b(service\s+(?:manual|bulletin|report))\b', re.IGNORECASE),
                re.compile(r'\b(installation\s+(?:manual|guide))\b', re.IGNORECASE),
                re.compile(r'\b(operating\s+(?:manual|instructions))\b', re.IGNORECASE),
                re.compile(r'\b(technical\s+(?:manual|specification|data))\b', re.IGNORECASE),
                re.compile(r'\b(parts\s+(?:manual|catalog|list))\b', re.IGNORECASE),
                re.compile(r'\b(safety\s+(?:certificate|plan))\b', re.IGNORECASE),
                re.compile(r'\b(survey\s+report)\b', re.IGNORECASE),
                re.compile(r'\b(inspection\s+report)\b', re.IGNORECASE),

                # Single-word document types (last, as fallback)
                re.compile(r'\b(manual|manuals|handbook|handbooks|guide|guides|instructions|documentation|spec|specs|specification|specifications|procedure|procedures|checklist|checklists|report|reports|log|logs|diagram|diagrams|schematic|schematics|invoice|invoices|receipt|receipts|certificate|certificates|pdf|xlsx|docx|csv|txt|xls|doc)\b', re.IGNORECASE),
            ],

            # Email search patterns (evidence transport layer)
            'email_search': [
                re.compile(r'\b(emails?|e-?mails?)\b', re.IGNORECASE),
                re.compile(r'\b(email\s+(?:thread|threads|chain|chains|conversation|conversations))\b', re.IGNORECASE),
                re.compile(r'\b(correspondence|messages?)\b', re.IGNORECASE),
                re.compile(r'\b(inbox|sent\s+items?|mailbox)\b', re.IGNORECASE),
                re.compile(r'\b(email\s+(?:from|to|about|regarding))\b', re.IGNORECASE),
                re.compile(r'\b(vendor\s+email|supplier\s+email)\b', re.IGNORECASE),
            ],

            # Phase 1 additions: Temporal extensions
            # Phase 2 enhancements (2026-02-03): Added overdue, expiring, due, future refs
            'time_ref': [
                # Basic day references
                re.compile(r'\b(yesterday\s*(?:morning|afternoon|evening)?)\b', re.IGNORECASE),
                re.compile(r'\b(today)\b', re.IGNORECASE),
                re.compile(r'\b(tomorrow)\b', re.IGNORECASE),

                # Relative past periods
                re.compile(r'\b(last\s+(?:night|week|month|year))\b', re.IGNORECASE),
                re.compile(r'\b(this\s+(?:morning|afternoon|evening|week|month|year))\b', re.IGNORECASE),
                re.compile(r'\b(\d+\s+(?:hours?|minutes?|days?|weeks?|months?)\s+ago)\b', re.IGNORECASE),

                # NEW: "last N days/weeks" patterns (e.g., "last 7 days", "last 30 days")
                re.compile(r'\b(last\s+\d+\s+(?:days?|weeks?|months?))\b', re.IGNORECASE),

                # NEW: Overdue/late patterns for work orders and certificates
                re.compile(r'\b(overdue)\b', re.IGNORECASE),
                re.compile(r'\b(past\s+due)\b', re.IGNORECASE),
                re.compile(r'\b(late)\b', re.IGNORECASE),

                # NEW: Expiring/expiration patterns for certificates
                re.compile(r'\b(expiring\s+soon)\b', re.IGNORECASE),
                re.compile(r'\b(expiring\s+in\s+\d+\s+(?:days?|weeks?|months?))\b', re.IGNORECASE),
                re.compile(r'\b(expires?\s+(?:in\s+)?\d+\s+(?:days?|weeks?|months?))\b', re.IGNORECASE),
                re.compile(r'\b(expir(?:es?|ing|ation)\s+(?:this|next)\s+(?:week|month|year))\b', re.IGNORECASE),

                # NEW: Future period references
                re.compile(r'\b(next\s+(?:week|month|year))\b', re.IGNORECASE),
                re.compile(r'\b(in\s+\d+\s+(?:days?|weeks?|months?))\b', re.IGNORECASE),
                re.compile(r'\b(within\s+\d+\s+(?:days?|weeks?|months?))\b', re.IGNORECASE),

                # NEW: Due date patterns
                re.compile(r'\b(due\s+(?:today|tomorrow|this\s+week|this\s+month|next\s+week))\b', re.IGNORECASE),
            ],

            'duration': [
                # Extract just the duration, not "for"
                re.compile(r'\bfor\s+(\d+(?:\.\d+)?\s+(?:sec(?:ond)?s?|min(?:ute)?s?|hours?|days?|weeks?|months?))\b', re.IGNORECASE),
                re.compile(r'\b(\d+(?:\.\d+)?\s+(?:sec(?:ond)?s?|min(?:ute)?s?|hours?|days?|weeks?|months?))\s+duration\b', re.IGNORECASE),
                re.compile(r'\bevery\s+(\d+(?:\.\d+)?\s+(?:sec(?:ond)?s?|min(?:ute)?s?|hours?))\b', re.IGNORECASE),
            ],

            'time_range': [
                # Capture the whole range as one entity
                re.compile(r'\b(\d{1,2}:\d{2}(?::\d{2})?)\s*(?:[-–]|to)\s*(\d{1,2}:\d{2}(?::\d{2})?)\b'),
                re.compile(r'\bbetween\s+(\d{1,2}:\d{2})\s+and\s+(\d{1,2}:\d{2})\b', re.IGNORECASE),
            ],

            # Measurement ranges
            'measurement_range': [
                re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(?:[-–]|to)\s*(\d+(?:[.,]\d+)?)\s*(°?[CF]|V|A|Hz|RPM|bar|psi|kPa)\b'),
            ],

            # Setpoints (extract just value+unit, not the keyword)
            'setpoint': [
                re.compile(r'\b(?:setpoint|target|reference)\s+(\d+(?:[.,]\d+)?\s*(?:°?[CF]|[kmM]?V|[mM]?A|[kM]?Hz|RPM|bar|psi|kPa|MPa|%)?)\b', re.IGNORECASE),
            ],

            # Limits (extract just value+unit, not the keyword)
            'limit': [
                re.compile(r'\b(?:limit|max(?:imum)?|min(?:imum)?)\s+(\d+(?:[.,]\d+)?\s*(?:°?[CF]|[kmM]?V|[mM]?A|[kM]?Hz|RPM|bar|psi|kPa|MPa|%)?)\b', re.IGNORECASE),
            ],

            # Business document IDs (PO, Invoice, Quote, WO, SR, Job numbers)
            # Captures: LETTERS + SEPARATOR + NUMBERS with flexible formatting
            'po_number': [
                # COMPREHENSIVE: 1-10 letters + optional separator + 3-8 digits + optional sub-number
                # Matches: PO-12345, P/O12784, INV-2024-001, INVOICE #12345, WO-43242, SR-98765, etc.
                # Separators: /, -, #, :, space (or none)
                re.compile(r'\b([A-Z]{1,10}[/\-#:\s]?\d{3,8}(?:-\d{1,3})?)\b', re.I),

                # Specific common patterns (higher confidence)
                # PO/Purchase Order: "PO #2345", "P.O.-12345", "P/O12784", "PO-2432"
                re.compile(r'\b((?:PO|P[./]O\.?)\s*[#:\-/]?\s?\d{3,8}(?:-\d{1,3})?)\b', re.I),

                # Invoice: "INV-12345", "INVOICE #12345", "Invoice-2024-001"
                re.compile(r'\b(INV(?:OICE)?\s*[#:\-\s]?\d{3,8}(?:-\d{1,4})?)\b', re.I),

                # Quote: "QUOTE-12345", "Q-98765", "Quote #12345"
                re.compile(r'\b((?:QUOTE|Q)\s*[#:\-\s]?\d{3,8}(?:-\d{1,3})?)\b', re.I),

                # Work Order: "WO-12345", "WORK-ORDER-12345"
                re.compile(r'\b((?:WO|WORK[- ]?ORDER)\s*[#:\-\s]?\d{3,8}(?:-\d{1,3})?)\b', re.I),

                # Service Request: "SR-12345", "SERVICE-REQ-12345"
                re.compile(r'\b((?:SR|SERVICE[- ]?REQ(?:UEST)?)\s*[#:\-\s]?\d{3,8}(?:-\d{1,3})?)\b', re.I),

                # Job Number: "JOB-12345", "J-98765", "Job #12345"
                re.compile(r'\b((?:JOB|J)\s*[#:\-\s]?\d{3,8}(?:-\d{1,3})?)\b', re.I),

                # Long-form natural language WITH digits
                re.compile(r'\b(purchase\s+order\s*[:#-]?\s?\d{3,8}(?:-\d{1,3})?)\b', re.I),
                re.compile(r'\b(work\s+order\s*[:#-]?\s?\d{3,8}(?:-\d{1,3})?)\b', re.I),
                re.compile(r'\b(invoice\s+(?:number|#)?\s*[:#-]?\s?\d{3,8}(?:-\d{1,4})?)\b', re.I),

                # P0 FIX: REMOVED literal patterns that extracted question keywords
                # These were matching "invoice number" as an entity even when it was part of the question
                # Old patterns extracted: "What is the invoice number?" → po_number: ["invoice number"]
                # This was wrong because "invoice number" is REQUEST syntax, not an entity value
                # Only extract when followed by actual number (patterns at lines 653-655 handle this)
                #
                # REMOVED:
                # re.compile(r'\b(purchase\s+order)\b', re.I),
                # re.compile(r'\b(work\s+order)\b', re.I),
                # re.compile(r'\b(invoice\s+number)\b', re.I),
                # re.compile(r'\b(PO\s+number)\b', re.I),
                # re.compile(r'\b(quote\s+number)\b', re.I),
                # re.compile(r'\b(job\s+number)\b', re.I),
            ],

            # Multi-word product names (AH Maxx CW, WLN10 Smart, Force 10)
            'product_name': [
                # Brand (2-5 caps) + Model (Camel/Pascal/Mixed) + Optional Suffix (1-4 caps or descriptor)
                re.compile(r'\b([A-Z]{2,5}\s+[A-Z][A-Za-z0-9]+(?:\s+(?:[A-Z0-9]{1,4}|Smart|Mini|Digital|PMS))?)\b'),
                # Brand word (Capitalized) + ALLCAPS/Alnum model + optional descriptor
                re.compile(r'\b([A-Z][a-z]{2,20}\s+[A-Z0-9]{2,10}(?:\s+(?:Smart|Mini|Digital|PMS))?)\b'),

                # PHASE 3: CamelCase products (iNavHub, iKonvert, AISnode, AISnet)
                # Pattern: [i/a] + CapitalizedWord + CapitalizedWord
                re.compile(r'\b([ia][A-Z][a-z]+[A-Z][a-z]+)\b'),  # iNavHub, iKonvert, aNavHub
                # Pattern: ACRONYM + lowercase + CapitalizedWord
                re.compile(r'\b([A-Z]{2,5}[a-z]+[A-Z][a-z]+)\b'),  # AISnode, AISnet, GPSlink
            ],

            # PHASE 2: ACRONYM + EQUIPMENT patterns (NMEA interface, AIS receiver, GPS antenna)
            # Extracts compound equipment with technical acronyms
            'system': [
                # Acronym (2-5 caps) + equipment word
                re.compile(r'\b([A-Z]{2,5})\s+(interface|gateway|receiver|transponder|antenna|controller|module|hub|network|bridge|converter)\b', re.IGNORECASE),
                # Acronym + numeric + equipment (NMEA 0183 interface, NMEA 2000 gateway)
                re.compile(r'\b([A-Z]{2,5}\s+\d{1,4})\s+(interface|gateway|receiver|transponder|antenna|network)\b', re.IGNORECASE),
            ],

            # Designation/manual codes (SEBU6250-30, MTU-16V2000, EVC-5020)
            'designation': [
                re.compile(r'\b([A-Z]{3,6}\d{3,6}-\d{1,3})\b'),   # SEBU6250-30
                re.compile(r'\b([A-Z]{2,6}[-_]\d{3,6})\b'),       # MTU-16V2000, EVC-5020
            ],

            # Descriptors (smart, mini, digital, pms, etc.)
            'descriptor': [
                re.compile(r'\b(mini|compact|smart|digital|pms|xl|pro|lite|micro|nano|hd|uhd|ka|ku)\b', re.I),
            ]
        }

        return patterns

    def _load_gazetteer(self) -> Dict[str, Set[str]]:
        """Load gazetteer for multi-token entity lookup."""

        # Load REGEX_PRODUCTION data (32,293 manufacturers, 1,141 equipment terms)
        regex_prod_manufacturers = load_manufacturers()
        regex_prod_equipment = load_equipment_terms()

        gazetteer = {
            'equipment': {
                # Propulsion & Power (existing + expansions)
                'engine', 'engines', 'motor', 'motors', 'generator', 'generators',
                'pump', 'pumps', 'compressor', 'compressors', 'turbine', 'turbines',
                'thruster', 'thrusters', 'bow thruster', 'stern thruster', 'propeller', 'propellers', 'shaft', 'shafts',
                'gear', 'gears', 'gearbox', 'gearboxes', 'transmission', 'clutch', 'bearing', 'bearings', 'seal', 'seals',
                'valve', 'valves', 'safety valve', 'actuator', 'actuators', 'sensor', 'sensors', 'transducer', 'transducers', 'gauge', 'gauges', 'meter', 'meters',
                'filter', 'filters', 'strainer', 'strainers', 'cooler', 'coolers', 'heat exchanger', 'radiator', 'radiators', 'coolant', 'engine coolant',
                'battery', 'batteries', 'battery bank', 'charger', 'chargers', 'inverter', 'inverters', 'converter', 'converters', 'transformer', 'transformers',
                'breaker', 'breakers', 'circuit', 'circuits', 'switch', 'switches', 'relay', 'relays', 'contactor', 'contactors', 'controller', 'controllers', 'plc',

                # Navigation & Electronics (existing + expansions)
                'radar', 'gps', 'chart plotter', 'chartplotter', 'vhf', 'vhf radio', 'ais', 'epirb', 'sart', 'navtex',
                'autopilot', 'gyro', 'compass', 'echo sounder', 'depth sounder', 'fishfinder',
                'transponder', 'transceiver', 'binoculars', 'searchlight', 'spotlight',

                # Digital Yacht Products (HIGH PRIORITY - fixes 5 failures - ADDED 2025-10-20)
                'lanlink', 'inavhub', 'ikonvert', 'inavconnect',
                'aisnode', 'aisnet', 'aisserver', 'gpslink',
                'wl70', '4gxtream', 'nomad', 'smartertrack',

                # Refrigeration & HVAC (NEW - addresses "fridge" issue)
                'refrigerator', 'fridge', 'freezer', 'ice maker', 'ice box', 'icebox',
                'air conditioning', 'air conditioner', 'ac unit', 'hvac', 'heater', 'chiller',

                # Galley & Interior (NEW - cross-department)
                'stove', 'oven', 'cooktop', 'microwave', 'dishwasher', 'washer', 'dryer',
                'coffee maker', 'espresso machine', 'grill', 'bbq',

                # Entertainment & Comfort (NEW - guest areas)
                'television', 'tv', 'stereo', 'speaker', 'satellite', 'wifi', 'router',
                'antenna', 'sound system',

                # Safety & Emergency (NEW)
                'life raft', 'life jacket', 'pfd', 'fire extinguisher', 'fire suppression',
                'smoke detector', 'co detector', 'flare', 'horn', 'bell',
                'resqlink', 'lifeguard',  # ACR beacon, AIS safety - ADDED 2025-10-20

                # Deck & Exterior (NEW)
                'winch', 'windlass', 'anchor', 'davit', 'crane', 'passerelle', 'gangway',
                'tender', 'jet ski', 'kayak', 'paddleboard',

                # Plumbing & Sanitation (NEW)
                'toilet', 'head', 'shower', 'sink', 'faucet', 'water maker', 'watermaker',
                'holding tank', 'black water tank', 'grey water tank', 'freshwater tank',
                'y-valve', 'seacock', 'thru-hull', 'bilge pump',

                # Lighting (NEW)
                'navigation light', 'nav light', 'anchor light', 'deck light', 'underwater light',
                'searchlight', 'courtesy light'
            },

            'subcomponent': {
                # Engine components
                'cylinder', 'cylinders', 'piston', 'pistons', 'liner', 'liners', 'cylinder liner',
                'crankshaft', 'camshaft', 'connecting rod', 'con rod', 'valve', 'valves',
                'injector', 'injectors', 'turbocharger', 'turbo', 'intercooler',
                'oil pump', 'water pump', 'fuel pump', 'cooling pump',
                'gasket', 'head gasket', 'seal', 'seals', 'o-ring', 'o-rings',
                'belt', 'belts', 'timing belt', 'v-belt', 'serpentine belt',

                # Piping & Valves
                'pipe', 'pipes', 'piping', 'balance pipe', 'feed pipe', 'return pipe',
                'supply pipe', 'drain pipe', 'vent pipe', 'overflow pipe',
                'ball valve', 'gate valve', 'butterfly valve', 'check valve', 'relief valve',
                'globe valve', 'needle valve', 'solenoid valve',
                'flange', 'flanges', 'coupling', 'couplings', 'elbow', 'elbows',
                'reducer', 'tee', 't-piece', 'union',

                # Electrical components
                'fuse', 'fuses', 'circuit breaker', 'breaker', 'relay', 'relays',
                'contactor', 'contactors', 'cable', 'cables', 'wire', 'wiring',
                'terminal', 'terminals', 'connector', 'connectors', 'busbar', 'busbars',
                'resistor', 'capacitor', 'diode', 'transistor', 'mosfet',

                # Mechanical components
                'bearing', 'bearings', 'bushing', 'bushings', 'shaft', 'shafts',
                'gear', 'gears', 'sprocket', 'sprockets', 'chain', 'chains',
                'bolt', 'bolts', 'nut', 'nuts', 'washer', 'washers',
                'spring', 'springs', 'pin', 'pins', 'key', 'keyway',

                # Filters & Strainers
                'oil filter', 'fuel filter', 'air filter', 'water filter',
                'strainer', 'strainers', 'screen', 'screens',

                # Sensors & Instruments
                'temperature sensor', 'pressure sensor', 'level sensor', 'flow sensor',
                'speed sensor', 'position sensor', 'proximity sensor',
                'thermocouple', 'rtd', 'transducer', 'transmitter',
                'gauge', 'pressure gauge', 'temperature gauge', 'level gauge',

                # Measurement properties (for technical queries)
                'diameter', 'bore', 'stroke', 'length', 'width', 'height', 'thickness',
                'clearance', 'tolerance', 'gap', 'pressure', 'temperature', 'voltage',
                'current', 'resistance', 'capacity', 'volume', 'flow', 'rpm', 'speed'
            },

            'system': {
                'propulsion', 'electrical', 'hydraulic', 'hydraulic system', 'pneumatic', 'fuel',
                'cooling', 'cooling system', 'lubrication', 'oil', 'exhaust', 'ventilation', 'hvac',
                'navigation', 'navigation system', 'communication', 'safety', 'fire', 'fire suppression',
                'bilge', 'bilge system', 'ballast', 'steering', 'steering system',
                'power management', 'automation', 'monitoring', 'alarm system',
                'network', 'ethernet', 'connection', 'wiring', 'cabling',

                # NEW - Cross-department systems
                'air conditioning system', 'refrigeration system', 'freshwater system',
                'wastewater system', 'sanitation system', 'entertainment system',
                'security system', 'cctv', 'intercom', 'lighting system'
            },

            'location_on_board': {
                # Bridge & Navigation (existing + expansions)
                'bridge', 'flybridge', 'wheelhouse', 'helm', 'helm station', 'nav station',
                'chart table', 'wing station', 'control room',

                # Engineering spaces (existing + expansions)
                'engine room', 'machinery space', 'pump room', 'generator room',
                'battery room', 'e/r', 'er',

                # Deck areas (existing + expansions)
                'deck', 'main deck', 'upper deck', 'lower deck', 'sun deck', 'boat deck',
                'foredeck', 'aft deck', 'side deck', 'bow', 'stern',
                'port', 'port side', 'starboard', 'starboard side', 'fore', 'aft', 'midship',
                'cockpit', 'swim platform', 'bathing platform', 'transom',

                # Guest & Living areas (NEW - cross-department)
                'cabin', 'master cabin', 'master suite', 'owner suite', 'owners cabin',
                'vip cabin', 'vip suite', 'guest cabin', 'stateroom',
                'saloon', 'salon', 'sky lounge', 'main salon', 'upper salon',
                'dining room', 'galley', 'pantry', 'wine cellar',

                # Crew areas (NEW)
                'crew quarters', 'crew cabin', 'crew mess', 'crew galley',
                'crew lounge', 'laundry', 'laundry room',

                # Service & Storage (existing + expansions)
                'cargo hold', 'tank', 'fuel tank', 'water tank', 'storage',
                'locker', 'chain locker', 'anchor locker', 'lazarette',
                'bilge', 'void space', 'cofferdams'
            },

            'status': {
                # Equipment states
                'fault', 'alarm', 'alarms', 'warning', 'error', 'trip', 'tripped', 'tripping',
                'failure', 'failed', 'normal', 'running', 'stopped', 'standby',
                'online', 'offline', 'active', 'inactive', 'enabled', 'disabled',
                'open', 'closed', 'locked', 'unlocked', 'engaged', 'disengaged',
                'priming', 'operational', 'inoperative', 'out of service',
                'available', 'unavailable', 'ready', 'not ready', 'idle', 'busy',

                # Workflow/Task states
                'scheduled', 'pending', 'in progress', 'in-progress', 'ongoing',
                'completed', 'complete', 'finished', 'done',
                'deferred', 'postponed', 'delayed', 'overdue', 'due',
                'cancelled', 'canceled', 'aborted', 'terminated',
                'approved', 'rejected', 'awaiting approval', 'under review',
                'assigned', 'unassigned', 'open', 'closed',

                # Condition states
                'good', 'fair', 'poor', 'critical', 'degraded', 'optimal',
                'satisfactory', 'unsatisfactory', 'acceptable', 'unacceptable',

                # Qualifiers/Limits (for queries like "minimum diameter")
                'minimum', 'maximum', 'nominal', 'standard', 'rated', 'specified',
                'recommended', 'required', 'allowable', 'permissible'
            },

            'symptom': {
                'vibration', 'noise', 'leak', 'leaks', 'leaking', 'overheating', 'smoke',
                'sparks', 'corrosion', 'wear', 'damage', 'crack', 'cracked', 'broken',
                'intermittent', 'fluctuation', 'unstable', 'high', 'low',
                'excessive', 'insufficient', 'abnormal', 'unusual', 'grinding',
                'knocking', 'rattling', 'squealing', 'humming', 'buzzing'
            },

            'action': {
                # Mechanical/Physical actions
                'start', 'starting', 'stop', 'stopping', 'reset', 'resetting', 'restart', 'restarting',
                'reboot', 'rebooting', 'check', 'checking', 'inspect', 'inspecting', 'test', 'testing',
                'calibrate', 'calibrating', 'calibration', 'adjust', 'adjusting', 'adjustment', 'replace', 'replacing', 'replacement', 'repair', 'repairing',
                'service', 'servicing', 'maintain', 'maintaining', 'maintenance',
                'clean', 'cleaning', 'flush', 'flushing', 'purge', 'purging', 'prime', 'priming',
                'bleed', 'bleeding', 'drain', 'draining', 'fill', 'filling', 'refill', 'refilling',
                'tighten', 'tightening', 'loosen', 'loosening', 'torque', 'torquing',
                'open', 'opening', 'close', 'closing', 'shut', 'shutting',
                'enable', 'enabling', 'disable', 'disabling', 'engage', 'engaging', 'disengage', 'disengaging',
                'lock', 'locking', 'unlock', 'unlocking', 'bypass', 'bypassing', 'override', 'overriding',
                'monitor', 'monitoring', 'measure', 'measuring', 'read', 'reading',
                'install', 'installing', 'installation', 'setup', 'set up', 'configure', 'configuring', 'configuration', 'remove', 'removing', 'assemble', 'assembling', 'disassemble', 'disassembling',

                # Administrative/Planning actions
                'schedule', 'scheduling', 'plan', 'planning', 'organize', 'organizing',
                'coordinate', 'coordinating', 'arrange', 'arranging', 'book', 'booking', 'reserve', 'reserving',
                'defer', 'deferring', 'postpone', 'postponing', 'reschedule', 'rescheduling',
                'prioritize', 'prioritizing', 'assign', 'assigning', 'allocate', 'allocating',

                # Documentation actions
                'document', 'documenting', 'log', 'logging', 'note', 'noting', 'record', 'recording',
                'register', 'registering', 'file', 'filing', 'report', 'reporting', 'write', 'writing',
                'update', 'updating', 'revise', 'revising', 'review', 'reviewing',

                # Communication actions
                'notify', 'notifying', 'alert', 'alerting', 'inform', 'informing', 'advise', 'advising',
                'contact', 'contacting', 'call', 'calling', 'radio', 'email', 'message', 'messaging',
                'communicate', 'communicating', 'announce', 'announcing', 'broadcast', 'broadcasting',

                # Investigation/Diagnosis actions
                'investigate', 'investigating', 'diagnose', 'diagnosing', 'troubleshoot', 'troubleshooting',
                'analyze', 'analyzing', 'assess', 'assessing', 'evaluate', 'evaluating', 'examine', 'examining',
                'trace', 'tracing', 'isolate', 'isolating', 'identify', 'identifying', 'determine', 'determining',
                'find', 'finding', 'locate', 'locating', 'search', 'searching', 'look', 'looking',

                # Procurement actions
                'order', 'ordering', 'request', 'requesting', 'purchase', 'purchasing',
                'procure', 'procuring', 'requisition', 'requisitioning', 'buy', 'buying', 'source', 'sourcing',
                # Phase 2 (2026-02-03): Added inventory actions
                'restock', 'restocking', 'replenish', 'replenishing', 'resupply', 'resupplying',

                # Approval/Authorization actions
                'approve', 'approving', 'authorize', 'authorizing', 'certify', 'certifying',
                'validate', 'validating', 'verify', 'verifying', 'confirm', 'confirming', 'accept', 'accepting',
                'reject', 'rejecting', 'decline', 'declining',

                # Tracking/Monitoring actions
                'track', 'tracking', 'follow', 'following', 'watch', 'watching', 'observe', 'observing',

                # Completion actions
                'complete', 'completing', 'finish', 'finishing', 'finalize', 'finalizing',
                'cancel', 'canceling', 'cancelling', 'abort', 'aborting', 'terminate', 'terminating'
            },

            # Information/measurement concepts (cost, location, etc)
            'information': {
                'cost', 'price', 'pricing', 'value', 'expense', 'budget',
                'location', 'position', 'coordinates', 'address',
                'specification', 'specifications', 'rating', 'capacity',
                'dimension', 'dimensions', 'size', 'weight', 'length', 'width', 'height', 'depth'
            },

            # Equipment qualifiers (main, primary, backup, etc)
            'qualifier': {
                'main', 'primary', 'secondary', 'backup', 'auxiliary', 'emergency', 'standby',
                'port', 'starboard', 'forward', 'aft', 'upper', 'lower',
                'new', 'old', 'original', 'replacement', 'spare'
            },

            # ROLE TITLES ONLY - no personal names (per user instruction)
            'person': {
                # Bridge/Deck Officers
                'captain', 'master', 'chief officer', 'first officer', 'first mate',
                'second officer', 'second mate', 'third officer', 'third mate',
                'deck officer', 'officer of the watch', 'ow', 'mate',

                # Engineering
                'chief engineer', 'first engineer', 'second engineer', 'third engineer',
                'fourth engineer', 'engineer', 'eto', 'electro technical officer',
                'electrician', 'fitter', 'mechanic', 'oiler', 'wiper',

                # Interior/Hospitality (NEW - cross-department)
                'chief stewardess', 'chief stew', 'stewardess', 'stew', 'purser',
                'chef', 'head chef', 'sous chef', 'cook', 'galley hand',
                'housekeeper', 'laundry', 'butler',

                # Deck Crew
                'bosun', 'deckhand', 'able seaman', 'ab', 'ordinary seaman', 'os',
                'helmsman', 'watchkeeper', 'lookout',

                # Generic
                'crew', 'crew member', 'technician', 'operator', 'supervisor',
                'guest', 'owner', 'passenger'
            },

            'org': {
                # Engine manufacturers & Generators
                'caterpillar', 'cat', 'man', 'wartsila', 'wärtsilä', 'rolls royce', 'mtu',
                'volvo', 'volvo penta', 'penta', 'yanmar', 'cummins', 'deutz', 'perkins',
                'john deere', 'scania', 'iveco', 'detroit diesel', 'fischer panda',
                'kohler', 'onan', 'northern lights',  # Generators - ADDED 2025-10-20

                # Electrical/Electronics
                'abb', 'siemens', 'schneider', 'schneider electric', 'danfoss',
                'emerson', 'honeywell', 'victron', 'mastervolt', 'outback',

                # Navigation/Electronics/VSAT
                'kongsberg', 'furuno', 'simrad', 'garmin', 'raymarine', 'b&g',
                'navico', 'lowrance', 'northrop grumman', 'raytheon',
                'intellian',  # Maritime VSAT antenna, radar, navigation systems
                'digital yacht', 'humminbird',  # Marine electronics - ADDED 2025-10-20

                # HVAC/Refrigeration (NEW)
                'dometic', 'vitrifrigo', 'webasto', 'eberspacher', 'cruisair',
                'marine air', 'climma', 'isotherm',  # ADDED 2025-10-20

                # Watermakers (NEW - ADDED 2025-10-20)
                'spectra', 'katadyn', 'hro', 'rainman',

                # Galley Equipment (NEW)
                'force 10', 'force10', 'princess', 'eno', 'miele', 'gaggenau',

                # Marine equipment (NEW)
                'lewmar', 'maxwell', 'quick', 'muir', 'lofrans',
                'besenzoni', 'opacmare', 'novurania',

                # Safety Equipment (NEW)
                'viking', 'viking life', 'survitec', 'zodiac', 'avon', 'ocean safety',
                'plastimo', 'revere', 'switlik',
                'acr', 'mcmurdo', 'kannad', 'jotron',  # Emergency beacons - ADDED 2025-10-20

                # Classification societies
                'dnv', 'gl', 'dnv gl', 'abs', 'lr', 'lloyds', 'rina', 'nk', 'bv', 'ccs'
            },

            'model': {
                # Only keep brand-specific named models that won't be caught by regex
                # (mostly branded names, not alphanumeric codes)
                'multiplus', 'quattro', 'skylla', 'phoenix', 'blue power',
                'ips'  # Volvo IPS system
                # Everything else (34df, C32, D13, 16V2000) handled by regex patterns above
            },

            # NEW - Document types (addresses Issue #1)
            'document_type': {
                # Certificates & Registration
                'ships papers', 'ship papers', 'ships papers', 'registration', 'certificate',
                'registration certificate', 'certificate of registry', 'documentation',
                'flag certificate', 'tonnage certificate', 'safety certificate',
                'insurance certificate', 'insurance', 'p&i certificate',

                # Logs & Records
                'logbook', 'log book', 'ships log', 'ship log', 'deck log', 'engine log',
                'radio log', 'oil record book', 'garbage record book', 'maintenance log',
                'crew list', 'crew manifest',

                # Manuals & Technical Docs
                'manual', 'handbook', 'service manual', 'owners manual', 'operators manual',
                'maintenance manual', 'installation manual', 'user guide', 'technical manual',
                'parts manual', 'parts catalog', 'parts list',

                # Plans & Diagrams
                'schematic', 'wiring diagram', 'diagram', 'blueprint', 'drawing',
                'general arrangement', 'ga plan', 'stability booklet',
                'fire control plan', 'damage control plan', 'safety plan',
                'piping diagram', 'electrical diagram', 'hydraulic diagram',

                # Compliance & Safety
                'clearance', 'customs declaration', 'cruising permit', 'fishing license',
                'passport', 'crew passport', 'seamans book', 'medical certificate',
                'solas certificate', 'isps certificate', 'ism certificate',
                'loadline certificate', 'marpol certificate', 'iopp certificate',
                'ballast water certificate', 'safety management certificate',

                # Records & Logs
                'ballast water record book', 'cargo record book',
                'continuous synopsis record', 'csr',

                # Surveys
                'annual survey', 'intermediate survey', 'special survey',
                'class survey', 'psc report', 'sire report', 'vetting report',

                # Operational
                'checklist', 'procedure', 'work order', 'service report', 'inspection report',
                'survey report', 'deficiency list', 'spare parts list',
                'maintenance schedule', 'pms report', 'job card'
            },

            # Inventory Lens - Stock status terms (Added 2026-02-02)
            'stock_status': {
                # Compound stock status phrases (must match BEFORE single words)
                'low stock', 'stock low', 'low inventory', 'inventory low',
                'out of stock', 'stock out', 'out of inventory',
                'critically low', 'critically low stock', 'critically low inventory',
                'below minimum', 'below minimum stock', 'stock below minimum',
                'need to reorder', 'needs to reorder', 'need reorder', 'needs reorder',
                'reorder needed', 'restock needed', 'needs restocking', 'need restocking',
                'running low', 'running low on stock', 'stock running low',
                'stock alert', 'inventory alert', 'low stock alert',
                'reorder point', 'below reorder point', 'at reorder point',
                'minimum stock', 'minimum stock level',
                # Additional stock level descriptors
                'adequate stock', 'sufficient stock', 'well stocked', 'good stock levels',
                'excess stock', 'overstocked', 'surplus stock', 'too much stock',
                'zero stock', 'no stock', 'empty stock', 'depleted', 'exhausted',
                'stock depleted', 'inventory depleted', 'stock exhausted'
            }
        }

        # Union with REGEX_PRODUCTION data
        # Equipment: Add 1,141 equipment terms from REGEX_PRODUCTION
        gazetteer['equipment'] = gazetteer['equipment'] | regex_prod_equipment

        # CONTAMINATION FILTERS: Equipment/document terms that should NOT be classified as brands
        # Apply same filters as entity_extraction_loader.py to prevent contamination
        equipment_indicators = {
            'pump', 'motor', 'valve', 'sensor', 'gauge', 'meter', 'controller', 'switch',
            'panel', 'control panel', 'monitor', 'alarm', 'detector', 'indicator', 'display',
            'relay', 'solenoid', 'actuator', 'transmitter', 'transducer', 'converter',
            'filter', 'strainer', 'separator', 'exchanger', 'cooler', 'heater', 'tank',
            'pipe', 'hose', 'fitting', 'coupling', 'adapter', 'flange', 'gasket', 'seal',
            'bearing', 'shaft', 'gear', 'belt', 'chain', 'pulley', 'sprocket', 'clutch',
            'engine', 'generator', 'compressor', 'blower', 'fan', 'propeller', 'impeller',
            'system', 'unit', 'assembly', 'component', 'device', 'equipment', 'apparatus',
            'automatic', 'manual', 'electric', 'hydraulic', 'pneumatic', 'mechanical',
            'float', 'automatic float', 'float switch', 'control', 'monitoring', 'measurement',
            # Additional equipment types found in contamination analysis
            'transponder', 'circuit breaker', 'breaker', 'circuit', 'cable', 'wire', 'fuse',
            'antenna', 'receiver', 'transmitter', 'amplifier', 'repeater', 'splitter',
            'connector', 'terminal', 'junction', 'bus', 'network', 'module', 'card'
        }

        document_indicators = {
            'requirements', 'standards', 'regulations', 'procedures', 'manual',
            'document', 'guide', 'specification', 'code', 'report', 'schedule',
            'program', 'management', 'safety', 'quality', 'compliance',
            'international', 'maritime', 'protocol', 'checklist', 'certificate',
            'marine', 'naval', 'commercial', 'industrial', 'technical'
        }

        product_descriptors = {
            'oil', 'grease', 'lubricant', 'fuel', 'coolant', 'fluid', 'chemical',
            'paint', 'coating', 'sealant', 'adhesive', 'compound', 'cleaner',
            'room temperature', 'temperature', 'pressure', 'voltage', 'current',
            'temperature monitor', 'pressure gauge', 'level sensor', 'flow meter',
            'engine oil', 'hydraulic oil', 'transmission fluid', 'brake fluid'
        }

        # Common adjectives/descriptors that contaminate manufacturer data
        common_adjectives = {
            'boat', 'best', 'good', 'fast', 'slow', 'hot', 'cold', 'warm', 'wet', 'dry',
            'quick', 'advanced', 'standard', 'test', 'bottom', 'top', 'new', 'old', 'first', 'last',
            'high', 'low', 'big', 'small', 'great', 'simple', 'basic', 'normal', 'special', 'general'
        }

        # Combine all filters
        contamination_filters = equipment_indicators | document_indicators | product_descriptors | common_adjectives

        # Filter manufacturers: Remove equipment/document descriptors
        filtered_manufacturers = set()
        for mfg in regex_prod_manufacturers:
            mfg_lower = mfg.lower()

            # Skip if term matches contamination filter
            if mfg_lower in contamination_filters:
                continue

            # Skip if term contains filtered words
            mfg_words = set(mfg_lower.split())
            if mfg_words & contamination_filters:
                continue

            # Skip single generic words (these are never brands)
            if len(mfg_words) == 1 and len(mfg_lower) < 4:
                continue

            filtered_manufacturers.add(mfg)

        # Org: Add FILTERED manufacturers from REGEX_PRODUCTION
        gazetteer['org'] = gazetteer['org'] | filtered_manufacturers

        # Fix 2026-02-02: Merge entity_extraction_gazetteer for crew/inventory/receiving lens entity types
        # These types (REST_COMPLIANCE, WARNING_STATUS, etc.) are defined in entity_extraction_loader.py
        # but were missing from the manual gazetteer, causing zero-entity extraction for "MLC compliance" etc.
        eeg = get_equipment_gazetteer()
        for key in ['REST_COMPLIANCE', 'WARNING_SEVERITY', 'WARNING_STATUS', 'stock_status',
                    'shopping_list_term', 'approval_status', 'source_type', 'urgency_level',
                    'receiving_status']:  # Added for receiving lens
            if key in eeg:
                if key not in gazetteer:
                    gazetteer[key] = set()
                gazetteer[key] = gazetteer[key] | eeg[key]

        # Convert to lowercase for case-insensitive matching
        for entity_type in gazetteer:
            gazetteer[entity_type] = {term.lower() for term in gazetteer[entity_type]}

        # Phase 2 (2026-02-03): Auto-expand gazetteer with plurals and abbreviations
        # Instead of manually adding "gaskets", we generate it from "gasket"
        if NORMALIZER_AVAILABLE and TEXT_NORMALIZER:
            self._expand_gazetteer_variations(gazetteer)

        return gazetteer

    def _expand_gazetteer_variations(self, gazetteer: Dict[str, Set[str]]):
        """
        Automatically expand gazetteer with plurals and common variations.

        This eliminates the need to manually add:
        - gaskets (plural of gasket)
        - generators (plural of generator)
        - gen, genset (abbreviations of generator)

        Uses TextNormalizer to generate variations intelligently.
        """
        # Types that benefit from plural/variation expansion
        # COMP-007 FIX (2026-02-03): Added 'subcomponent' for gaskets → gasket normalization
        expandable_types = {'equipment', 'equipment_type', 'part', 'brand', 'subcomponent'}

        for entity_type in expandable_types:
            if entity_type not in gazetteer:
                continue

            original_terms = list(gazetteer[entity_type])
            new_terms = set()

            for term in original_terms:
                # Get all variations (plurals, abbreviations, synonyms)
                variations = TEXT_NORMALIZER.get_variations(term)
                new_terms.update(variations)

            # Add new terms to gazetteer
            gazetteer[entity_type] = gazetteer[entity_type] | new_terms

        # Also add common abbreviation patterns
        abbrev_mappings = {
            'equipment': [
                ('gen', 'generator'),
                ('genset', 'generator'),
                ('genny', 'generator'),
                ('watermaker', 'watermaker'),
                ('desalinator', 'watermaker'),
            ],
        }

        for entity_type, mappings in abbrev_mappings.items():
            if entity_type not in gazetteer:
                continue
            for abbrev, canonical in mappings:
                if canonical in gazetteer[entity_type]:
                    gazetteer[entity_type].add(abbrev)

        logger.debug(f"Expanded gazetteer with variations for {expandable_types}")

    def _normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode characters to ASCII equivalents for better pattern matching.

        Handles:
        - Various dash/hyphen characters → standard hyphen
        - Accented characters → ASCII equivalents (ä→a, ö→o, etc.)
        """
        import unicodedata

        # Normalize various Unicode dashes to standard ASCII hyphen
        dash_chars = [
            '\u2013',  # en dash –
            '\u2014',  # em dash —
            '\u2212',  # minus sign −
            '\u2010',  # hyphen ‐
            '\u2011',  # non-breaking hyphen
            '\u2012',  # figure dash
            '\u2015',  # horizontal bar
        ]
        for dash in dash_chars:
            text = text.replace(dash, '-')

        # Normalize accented characters (NFD decomposition removes diacritics)
        # This converts Wärtsilä → Wartsila, etc.
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')

        return text

    def extract(self, text: str) -> Tuple[List[Entity], List[Tuple[int, int]]]:
        """
        Extract entities using regex and gazetteer.
        Returns (entities, covered_spans).
        """
        # Normalize Unicode characters for better pattern matching
        original_text = text
        text = self._normalize_unicode(text)

        entities = []
        covered_spans = []

        # Track what's already extracted to avoid duplicates
        extracted_texts = set()
        extracted_spans = []  # Track spans to prevent overlaps

        # Apply regex patterns IN PRECEDENCE ORDER to ensure compound patterns extract before single words
        # This prevents "invoice" from blocking "invoice number", etc.
        ordered_types = [t for t in self.PRECEDENCE_ORDER if t in self.patterns]
        # Add any types not in precedence order (for backwards compatibility)
        for t in self.patterns:
            if t not in ordered_types:
                ordered_types.append(t)

        # DOCUMENT LENS FIX (2026-02-02): Extract document_id and document_type FIRST
        # These patterns are highly specific (e.g., DNV-123456) and should not be blocked
        # by generic brand extraction (e.g., "DNV" alone)
        # LOCATION FIX (2026-02-02): Extract location_on_board BEFORE equipment_brand gazetteer
        # "engine room" was incorrectly matching equipment_brand instead of location
        # NEG-003 FIX (2026-02-03): Extract work_order_status BEFORE entity_extraction
        # "not completed" must be extracted before "completed" gets matched as fault_classification
        # ID-007 FIX (2026-02-03): Extract part_number_prefix BEFORE brand gazetteer
        # "beginning with CAT" must be extracted before "CAT" gets matched as brand
        # Priority: document patterns → location → status → prefix → entity_extraction → other regex → gazetteer
        doc_priority_types = ['document_id', 'document_type', 'location_on_board', 'work_order_status', 'part_number_prefix']
        for entity_type in doc_priority_types:
            if entity_type in self.patterns:
                patterns = self.patterns[entity_type]
                for pattern in patterns:
                    for match in pattern.finditer(text):
                        span = (match.start(), match.end())
                        matched_text = match.group()

                        if matched_text.lower() in extracted_texts:
                            continue

                        is_overlapping = False
                        for existing_span in extracted_spans:
                            if span[0] < existing_span[1] and existing_span[0] < span[1]:
                                is_overlapping = True
                                break

                        if not is_overlapping:
                            entities.append(Entity(
                                text=matched_text,
                                entity_type=entity_type,
                                confidence=0.85,
                                source='regex',
                                span=span
                            ))
                            extracted_texts.add(matched_text.lower())
                            extracted_spans.append(span)
                            covered_spans.append(span)

        # CREW LENS FIX (2026-01-31): Apply ENTITY_EXTRACTION_EXPORT patterns AFTER doc patterns
        # This ensures compound crew terms (e.g., "critical warnings") are extracted
        # BEFORE single-word regex patterns can claim individual words (e.g., "critical")
        # Priority order: document patterns → entity_extraction → regex → proper_nouns → gazetteer
        ee_entities, ee_spans = self._entity_extraction_extract(text, extracted_texts, extracted_spans)
        entities.extend(ee_entities)
        covered_spans.extend(ee_spans)
        extracted_spans.extend(ee_spans)  # Track ENTITY_EXTRACTION spans to prevent overlaps

        # Apply remaining regex patterns in precedence order (skip document patterns, already processed)
        for entity_type in ordered_types:
            # Skip document patterns - already processed above
            if entity_type in doc_priority_types:
                continue
            patterns = self.patterns[entity_type]
            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Handle special patterns
                    if entity_type == 'time_range':
                        # Combine the two captured groups into a single range
                        if len(match.groups()) >= 2:
                            matched_text = f"{match.group(1)}-{match.group(2)}"
                            span = (match.start(), match.end())
                        else:
                            matched_text = match.group()
                            span = (match.start(), match.end())
                    elif entity_type == 'measurement_range':
                        # Format range properly
                        if len(match.groups()) >= 3:
                            matched_text = f"{match.group(1)}-{match.group(2)} {match.group(3)}"
                            span = (match.start(), match.end())
                        else:
                            matched_text = match.group()
                            span = (match.start(), match.end())
                    elif entity_type in ['setpoint', 'limit']:
                        # Extract just the value, not the keyword
                        matched_text = match.group(1) if match.groups() else match.group()
                        # Adjust span to cover just the value
                        keyword_end = text.find(matched_text, match.start())
                        span = (keyword_end, keyword_end + len(matched_text))
                    else:
                        span = (match.start(), match.end())
                        # Use full match text, not just first group
                        matched_text = match.group()

                    # Normalize the measurement value (EU format to standard)
                    if entity_type == 'measurement':
                        matched_text = self._normalize_measurement(matched_text)

                    # Skip if already extracted
                    if matched_text.lower() in extracted_texts:
                        continue

                    # Check for span overlap with already-extracted entities
                    # This prevents "invoice" from extracting when "invoice number" already captured it
                    is_overlapping = False
                    for existing_span in extracted_spans:
                        # Check if spans overlap: current span overlaps if it shares any position
                        if span[0] < existing_span[1] and existing_span[0] < span[1]:
                            is_overlapping = True
                            break

                    if is_overlapping:
                        continue  # Skip this match, already covered by higher-precedence pattern

                    # Validate special cases
                    if entity_type == 'network_id' and 'IP' in matched_text:
                        if not self._is_valid_ip(matched_text):
                            continue

                    # Apply noise filtering for new entity types
                    if entity_type in ['error_code', 'version', 'part_number', 'serial_number']:
                        if self._is_noise_context(text, span):
                            continue

                    # Check for negation (only for relevant types)
                    negated = False
                    if entity_type in self.NEGATION_RELEVANT_TYPES:
                        negated = self._check_negation(text, span)

                    # Check for qualifiers and tolerance (mainly for measurements)
                    qualifier = None
                    tolerance = None
                    approx = False

                    if entity_type in ['measurement', 'setpoint', 'limit']:
                        qualifier, tolerance = self._detect_qualifier(text, span)
                        # Check if approximate
                        approx = '~' in matched_text or 'approx' in text[max(0, span[0]-20):span[0]].lower()

                    # Attach metadata for weight calculation
                    metadata = {'source_file': 'REGEX_PRODUCTION', 'group': None}

                    entity = Entity(
                        text=matched_text,
                        entity_type=entity_type,
                        confidence=0.99,  # High confidence for regex
                        source='regex',
                        span=span,
                        negated=negated,
                        qualifier=qualifier,
                        tolerance=tolerance,
                        approx=approx,
                        metadata=metadata
                    )

                    entities.append(entity)
                    covered_spans.append(span)
                    extracted_texts.add(matched_text.lower())
                    extracted_spans.append(span)  # Track span to prevent overlaps

        # P2 FIX: Extract proper nouns BEFORE gazetteer to catch compound names
        # Problem: "Gabriel Edward Jewelers" was missed because gazetteer only had "jeweler"
        # Solution: Extract capitalized multi-word sequences as organizations FIRST
        pn_entities, pn_spans = self._proper_noun_extract(text, extracted_texts, extracted_spans)
        entities.extend(pn_entities)
        covered_spans.extend(pn_spans)
        extracted_spans.extend(pn_spans)  # Track proper noun spans to prevent gazetteer overlap

        # Apply gazetteer (multi-token and single-token)
        gaz_entities, gaz_spans = self._gazetteer_extract(text, extracted_texts, extracted_spans)
        entities.extend(gaz_entities)
        covered_spans.extend(gaz_spans)
        extracted_spans.extend(gaz_spans)  # Track gazetteer spans too

        # Fix #4: Fuzzy matching for brand misspellings (2026-02-02)
        # Runs LAST as fallback for tokens that weren't matched exactly
        fuzzy_entities, fuzzy_spans = self._fuzzy_brand_extract(text, extracted_texts, extracted_spans)
        entities.extend(fuzzy_entities)
        covered_spans.extend(fuzzy_spans)

        # spaCy/NER removed - using regex + gazetteer + AI only
        # NOTE: entity_extraction now runs FIRST (moved to line ~1232 for crew lens fix)

        return entities, covered_spans

    def _proper_noun_extract(self, text: str, already_extracted: Set[str], existing_spans: List[Tuple[int, int]]) -> Tuple[List[Entity], List[Tuple[int, int]]]:
        """
        P2 FIX: Extract capitalized multi-word sequences as proper nouns (organizations/vendors).

        Patterns matched:
        - "Gabriel Edward Jewelers" (3 capitalized words)
        - "Fischer Panda" (2 capitalized words)
        - "S&L Wedding Team" (with ampersand)

        Runs BEFORE gazetteer so compound names don't get split into components.
        Example: "Gabriel Edward Jewelers" extracts as ONE entity, not "jeweler" separately.
        """
        entities = []
        spans = []

        # Equipment/process terms that should NEVER be classified as ORG
        equipment_indicators = {
            'automatic', 'float', 'switch', 'system', 'reverse', 'osmosis',
            'membrane', 'hydraulic', 'electric', 'manual', 'monitoring',
            'control', 'cooling', 'heating', 'ventilation', 'air', 'conditioning',
            'pump', 'valve', 'filter', 'engine', 'generator', 'compressor',
            'sensor', 'detector', 'alarm', 'panel', 'display', 'interface',
            'battery', 'charger', 'inverter', 'converter'
        }

        # FIXED: Document/concept terms that should NEVER be classified as ORG
        # Blocks phrases like "Marine Safety Requirements", "International Maritime Standards"
        document_indicators = {
            'requirements', 'standards', 'regulations', 'procedures', 'manual',
            'document', 'guide', 'specification', 'code', 'report', 'schedule',
            'program', 'management', 'safety', 'quality', 'compliance',
            'international', 'maritime', 'protocol', 'checklist', 'certificate'
        }

        # Pattern: 2-5 capitalized words, optionally with ampersand/punctuation
        # Matches: "Gabriel Edward Jewelers", "S&L Wedding Team", "Fischer Panda"
        # Excludes: "What is the" (question words), "The Microsoft Invoice" (starts with article)
        proper_noun_pattern = re.compile(
            r'\b(?!What\b|Where\b|When\b|Who\b|How\b|The\b|A\b|An\b)'  # Exclude question words/articles
            r'([A-Z][a-z]+(?:[&\s][A-Z][a-z]+){1,4})\b'  # 2-5 capitalized words
        )

        for match in proper_noun_pattern.finditer(text):
            matched_text = match.group(1)
            span = (match.start(1), match.end(1))

            # Skip if already extracted
            if matched_text.lower() in already_extracted:
                continue

            # CRITICAL: Skip if contains equipment or document indicators
            matched_words = set(matched_text.lower().split())
            if (matched_words & equipment_indicators) or (matched_words & document_indicators):
                # This is equipment/process/document terminology, not an organization
                continue

            # Check for span overlap
            is_overlapping = False
            for existing_span in existing_spans:
                if span[0] < existing_span[1] and existing_span[0] < span[1]:
                    is_overlapping = True
                    break

            if is_overlapping:
                continue

            # Create entity as organization (vendor/company name)
            metadata = {'source_file': 'PROPER_NOUN_EXTRACTOR', 'group': None}

            entity = Entity(
                text=matched_text,
                entity_type='org',  # Treat as organization
                confidence=0.60,    # FIXED: Lowered from 0.90 - capitalization is weak signal for ORG classification
                source='proper_noun',
                span=span,
                negated=False,
                metadata=metadata
            )

            entities.append(entity)
            spans.append(span)
            already_extracted.add(matched_text.lower())

        return entities, spans

    def _gazetteer_extract(self, text: str, already_extracted: Set[str], existing_spans: List[Tuple[int, int]]) -> Tuple[List[Entity], List[Tuple[int, int]]]:
        """Extract using gazetteer lookup with span overlap checking."""
        entities = []
        spans = []
        text_lower = text.lower()

        for entity_type, terms in self.gazetteer.items():
            # Sort by length (longer terms first for multi-token matching)
            sorted_terms = sorted(terms, key=len, reverse=True)

            for term in sorted_terms:
                if term in already_extracted:
                    continue

                # Find all occurrences
                start = 0
                while True:
                    pos = text_lower.find(term, start)
                    if pos == -1:
                        break

                    # Check word boundaries
                    end_pos = pos + len(term)
                    if (pos == 0 or not text[pos-1].isalnum()) and \
                       (end_pos == len(text) or not text[end_pos].isalnum()):

                        # Check for span overlap with already-extracted entities (CRITICAL FIX)
                        # This prevents "Microsoft Invoice" from overlapping with "invoice number"
                        is_overlapping = False
                        for existing_span in existing_spans:
                            if pos < existing_span[1] and existing_span[0] < end_pos:
                                is_overlapping = True
                                break

                        if is_overlapping:
                            start = pos + 1
                            continue  # Skip this match, already covered

                        # Extract with original casing
                        original_text = text[pos:end_pos]

                        # Check for negation (only for relevant types)
                        negated = False
                        if entity_type in self.NEGATION_RELEVANT_TYPES:
                            negated = self._check_negation(text, (pos, end_pos))

                        # Attach metadata for weight calculation
                        metadata = {'source_file': 'REGEX_PRODUCTION', 'group': None}

                        entity = Entity(
                            text=original_text,
                            entity_type=entity_type,
                            confidence=0.95,  # Slightly lower than regex
                            source='gazetteer',
                            span=(pos, end_pos),
                            negated=negated,
                            metadata=metadata
                        )

                        entities.append(entity)
                        spans.append((pos, end_pos))
                        already_extracted.add(term)
                        break  # Only take first occurrence of each term

                    start = pos + 1

        return entities, spans

    def _fuzzy_brand_extract(self, text: str, already_extracted: Set[str], existing_spans: List[Tuple[int, int]]) -> Tuple[List[Entity], List[Tuple[int, int]]]:
        """
        Fix #4 + Phase 2+3: Fuzzy matching for misspellings (2026-02-02).

        Uses rapidfuzz to match misspelled terms against:
        1. CORE_BRANDS (brand names)
        2. CORE_EQUIPMENT (equipment terms like generator, pump, etc.)
        3. CORE_FUZZY_TERMS (stock, inventory, warning terms, etc.)

        Examples:
        - "Caterpiller" → "caterpillar" (brand)
        - "genaratur" → "generator" (equipment)
        - "stok" → "stock" (stock_status)
        - "warrnings" → "warnings" (WARNING_STATUS)

        Conservative thresholds:
        - Score cutoff: 75-82 (based on word length)
        - Min token length: 4 chars
        """
        if not RAPIDFUZZ_AVAILABLE:
            return [], []

        entities = []
        spans = []

        # Phase 2 (2026-02-03): Pre-process multi-word aliases first
        text_lower = text.lower()
        for alias, canonical in BRAND_ALIASES.items():
            if ' ' in alias and alias in text_lower:
                pos = text_lower.find(alias)
                if pos != -1:
                    span = (pos, pos + len(alias))
                    # Check span overlap
                    is_overlapping = any(span[0] < es[1] and es[0] < span[1] for es in existing_spans)
                    if not is_overlapping:
                        entity = Entity(
                            text=canonical,
                            entity_type='brand',
                            confidence=0.95,  # High confidence for known aliases
                            source='alias',
                            span=span,
                            negated=False,
                            metadata={
                                'source_file': 'BRAND_ALIAS',
                                'original': alias,
                                'matched': canonical
                            }
                        )
                        entities.append(entity)
                        spans.append(span)
                        existing_spans.append(span)  # Add to existing spans to prevent overlaps
                        logger.debug(f"Multi-word brand alias: '{alias}' → '{canonical}'")

        # Tokenize text
        words = re.findall(r'\b\w+\b', text)
        core_brands_list = list(CORE_BRANDS)
        core_equipment_list = list(CORE_EQUIPMENT)
        core_fuzzy_terms_list = list(CORE_FUZZY_TERMS.keys())

        for word in words:
            word_lower = word.lower()

            # Skip if already extracted
            if word_lower in already_extracted:
                continue

            # Skip short words (too many false positives)
            if len(word) < 4:
                continue

            # Skip if exact match exists
            if word_lower in CORE_BRANDS or word_lower in CORE_EQUIPMENT or word_lower in CORE_FUZZY_TERMS:
                continue

            # Phase 2 (2026-02-03): Check BRAND_ALIASES for known misspellings/variations
            if word_lower in BRAND_ALIASES:
                canonical = BRAND_ALIASES[word_lower]
                pos = text.lower().find(word_lower)
                if pos != -1:
                    span = (pos, pos + len(word))
                    # Check span overlap
                    is_overlapping = any(span[0] < es[1] and es[0] < span[1] for es in existing_spans)
                    if not is_overlapping:
                        entity = Entity(
                            text=canonical,
                            entity_type='brand',
                            confidence=0.95,  # High confidence for known aliases
                            source='alias',
                            span=span,
                            negated=False,
                            metadata={
                                'source_file': 'BRAND_ALIAS',
                                'original': word,
                                'matched': canonical
                            }
                        )
                        entities.append(entity)
                        spans.append(span)
                        logger.debug(f"Brand alias: '{word}' → '{canonical}'")
                        continue

            # Find position in text
            pos = text.lower().find(word_lower)
            if pos == -1:
                continue

            end_pos = pos + len(word)
            span = (pos, end_pos)

            # Check for span overlap
            is_overlapping = False
            for existing_span in existing_spans:
                if span[0] < existing_span[1] and existing_span[0] < span[1]:
                    is_overlapping = True
                    break
            if is_overlapping:
                continue

            # Dynamic score cutoff based on word length
            # Longer words can have more typos, so lower threshold
            if len(word) >= 8:
                score_cutoff = 75  # "genaratur" → "generator" (77.8%)
            elif len(word) >= 6:
                score_cutoff = 78
            else:
                score_cutoff = 82  # Stricter for short words

            # Try fuzzy match against brands first
            brand_result = fuzz_process.extractOne(
                word_lower,
                core_brands_list,
                scorer=fuzz.ratio,
                score_cutoff=score_cutoff
            )

            # Try fuzzy match against equipment
            equipment_result = fuzz_process.extractOne(
                word_lower,
                core_equipment_list,
                scorer=fuzz.ratio,
                score_cutoff=score_cutoff
            )

            # Try fuzzy match against CORE_FUZZY_TERMS (stock, warning, compliance terms)
            fuzzy_terms_result = fuzz_process.extractOne(
                word_lower,
                core_fuzzy_terms_list,
                scorer=fuzz.ratio,
                score_cutoff=score_cutoff
            )

            # Pick the best match from all three sources
            matched_term = None
            entity_type = None
            score = 0

            # Collect all results with their scores
            results = []
            if brand_result:
                results.append(('brand', brand_result[0], brand_result[1]))
            if equipment_result:
                results.append(('equipment', equipment_result[0], equipment_result[1]))
            if fuzzy_terms_result:
                # Get entity type from CORE_FUZZY_TERMS mapping
                ft_term = fuzzy_terms_result[0]
                ft_type = CORE_FUZZY_TERMS.get(ft_term, 'unknown')
                results.append((ft_type, ft_term, fuzzy_terms_result[1]))

            # Pick highest scoring result
            if results:
                results.sort(key=lambda x: -x[2])  # Sort by score descending
                entity_type, matched_term, score = results[0]

            if matched_term and entity_type:
                # Additional validation for short words
                if len(word) <= 5 and score < 85:
                    continue

                # Confidence based on entity type
                # Different types have different thresholds, so we set confidence accordingly
                # Note: fuzzy source multiplier is 0.92, so we need to account for that:
                # adjusted_conf = confidence * 0.92 must be >= threshold
                if entity_type == 'brand':
                    fuzzy_confidence = 0.39  # 0.39 * 0.92 = 0.359 >= 0.35 threshold
                elif entity_type == 'equipment':
                    fuzzy_confidence = 0.78  # 0.78 * 0.92 = 0.718 >= 0.70 threshold
                elif entity_type in ('stock_status', 'WARNING_STATUS', 'WARNING_SEVERITY',
                                      'REST_COMPLIANCE', 'receiving_status'):
                    fuzzy_confidence = 0.62  # 0.62 * 0.92 = 0.570 >= 0.55 threshold (raised from 0.58)
                elif entity_type in ('action', 'system'):
                    fuzzy_confidence = 0.78  # Standard confidence for action/system
                else:
                    fuzzy_confidence = 0.78  # Default for unknown types

                metadata = {
                    'source_file': 'FUZZY_MATCH',
                    'original': word,
                    'matched': matched_term,
                    'score': score
                }

                entity = Entity(
                    text=matched_term.title(),
                    entity_type=entity_type,
                    confidence=fuzzy_confidence,
                    source='fuzzy',
                    span=span,
                    negated=False,
                    metadata=metadata
                )

                entities.append(entity)
                spans.append(span)
                already_extracted.add(word_lower)
                logger.debug(f"Fuzzy match: '{word}' → '{matched_term}' ({entity_type}, score={score})")

        return entities, spans

    def _entity_extraction_extract(self, text: str, already_extracted: Set[str], existing_spans: List[Tuple[int, int]]) -> Tuple[List[Entity], List[Tuple[int, int]]]:
        """
        Extract using ENTITY_EXTRACTION_EXPORT patterns (1,955 patterns from Groups 1-16).

        Extracts:
        - Equipment brands (33,682 brands from Groups 1-10)
        - Equipment types (1,306 types)
        - System types (74 types)
        - Diagnostic patterns (485 regex patterns from Groups 11-16)
        """
        entities = []
        spans = []
        text_lower = text.lower()

        # --- Part 1: Gazetteer extraction for equipment/brands (Groups 1-10) ---
        for entity_type, terms in self.entity_extraction_gazetteer.items():
            # Sort by length (longer terms first for multi-token matching)
            sorted_terms = sorted(terms, key=len, reverse=True)

            for term in sorted_terms:
                if term in already_extracted:
                    continue

                # Find all occurrences
                start = 0
                while True:
                    pos = text_lower.find(term, start)
                    if pos == -1:
                        break

                    # Check word boundaries
                    end_pos = pos + len(term)
                    if (pos == 0 or not text[pos-1].isalnum()) and \
                       (end_pos == len(text) or not text[end_pos].isalnum()):

                        # Check for span overlap with already-extracted entities
                        is_overlapping = False
                        for existing_span in existing_spans:
                            if pos < existing_span[1] and existing_span[0] < end_pos:
                                is_overlapping = True
                                break

                        if is_overlapping:
                            start = pos + 1
                            continue  # Skip this match, already covered

                        # Extract with original casing
                        original_text = text[pos:end_pos]

                        # Check for negation (only for relevant types)
                        negated = False
                        if entity_type in self.NEGATION_RELEVANT_TYPES:
                            negated = self._check_negation(text, (pos, end_pos))

                        # Attach metadata for weight calculation
                        metadata = {
                            'source_file': 'ENTITY_EXTRACTION_EXPORT',
                            'domain': None,  # Gazetteers don't have domain/subdomain
                            'subdomain': None,
                            'group': f'01-10'  # Equipment groups
                        }

                        # Calculate weight using entity_extraction weight system
                        weight = calculate_entity_weight(entity_type, metadata, len(original_text))

                        entity = Entity(
                            text=original_text,
                            entity_type=entity_type,
                            confidence=min(weight / 5.0, 0.98),  # Convert weight (0-5.0) to confidence (0-1.0)
                            source='gazetteer',
                            span=(pos, end_pos),
                            negated=negated,
                            metadata=metadata
                        )

                        entities.append(entity)
                        spans.append((pos, end_pos))
                        already_extracted.add(term)
                        break  # Only take first occurrence of each term

                    start = pos + 1

        # --- Part 2: Regex extraction for diagnostic patterns (Groups 11-16) ---
        for entity_type, pattern_list in self.entity_extraction_patterns.items():
            for compiled_pattern, domain, subdomain, canonical_term in pattern_list:
                for match in compiled_pattern.finditer(text):
                    span = (match.start(), match.end())
                    matched_text = match.group()

                    # Skip if already extracted
                    if matched_text.lower() in already_extracted:
                        continue

                    # Check for span overlap with already-extracted entities
                    is_overlapping = False
                    for existing_span in existing_spans:
                        if span[0] < existing_span[1] and existing_span[0] < span[1]:
                            is_overlapping = True
                            break

                    if is_overlapping:
                        continue  # Skip this match, already covered

                    # CRITICAL FIX: Check word boundaries for sensor_reading patterns
                    # This prevents false matches like "PMS" in "PMS digital" or "CO" in "coolant"
                    if entity_type == 'sensor_reading':
                        # Check if match is surrounded by word characters (part of larger word)
                        start_pos = span[0]
                        end_pos = span[1]

                        # Check character before match
                        if start_pos > 0 and text[start_pos - 1].isalnum():
                            continue  # Part of larger word, skip

                        # Check character after match
                        if end_pos < len(text) and text[end_pos].isalnum():
                            continue  # Part of larger word, skip

                        # Additional filter: Skip if matched text is very short abbreviation (< 4 chars)
                        # and appears in descriptive context (not a standalone sensor reading)
                        if len(matched_text) < 4:
                            # Check if surrounded by other descriptive words
                            context_start = max(0, start_pos - 30)
                            context_end = min(len(text), end_pos + 30)
                            context = text[context_start:context_end].lower()

                            # Skip if in descriptive/specification context
                            descriptive_terms = ['mini', 'digital', 'smart', 'pro', 'max', 'lite', 'compact']
                            if any(term in context for term in descriptive_terms):
                                continue

                    # Check for negation (only for relevant types)
                    negated = False
                    if entity_type in self.NEGATION_RELEVANT_TYPES:
                        negated = self._check_negation(text, span)

                    # Attach metadata for weight calculation
                    # Extract group number from domain (e.g., "11: System Symptoms" -> "11")
                    group_num = None
                    if domain:
                        group_match = re.match(r'^(\d+):', domain)
                        if group_match:
                            group_num = group_match.group(1)

                    metadata = {
                        'source_file': 'ENTITY_EXTRACTION_EXPORT',
                        'domain': domain,
                        'subdomain': subdomain,
                        'group': group_num
                    }

                    # Use canonical term if available, otherwise use matched text
                    final_text = canonical_term if canonical_term else matched_text

                    # Calculate weight using entity_extraction weight system
                    weight = calculate_entity_weight(entity_type, metadata, len(final_text))

                    entity = Entity(
                        text=final_text,
                        entity_type=entity_type,
                        confidence=min(weight / 5.0, 0.98),  # Convert weight (0-5.0) to confidence (0-1.0)
                        source='regex',
                        span=span,
                        negated=negated,
                        metadata=metadata
                    )

                    entities.append(entity)
                    spans.append(span)
                    already_extracted.add(matched_text.lower())

        return entities, spans

    def _normalize_measurement(self, text: str) -> str:
        """Normalize EU format numbers and units."""
        # Handle EU number format (1.234,56 → 1234.56)
        eu_pattern = re.compile(r'(\d{1,3})(?:\.(\d{3}))*(?:,(\d+))?')

        def replace_eu_number(match):
            parts = match.groups()
            number = parts[0]
            if parts[1]:  # Has thousands
                number = parts[0] + parts[1]
            if parts[2]:  # Has decimals
                number += '.' + parts[2]
            return number

        # Check if it's EU format (has comma as decimal separator)
        if ',' in text and '.' in text:
            # Likely EU format
            text = eu_pattern.sub(replace_eu_number, text)
        elif ',' in text and not '.' in text:
            # Could be EU decimal or thousands separator
            # If followed by 3 digits, it's thousands; otherwise decimal
            if re.search(r',\d{3}(?:\D|$)', text):
                text = text.replace(',', '')
            else:
                text = text.replace(',', '.')

        # Normalize units with spaces
        text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)

        return text

    def _normalize_text(self, s: str) -> str:
        """
        Normalize Unicode text for matching.
        Handles diacritics (Wärtsilä → Wartsila) while preserving case for models.

        Args:
            s: Input string

        Returns:
            Normalized string with diacritics removed
        """
        # NFC→NFKD normalization
        nfkd = unicodedata.normalize("NFKD", s)

        # Remove combining diacritical marks
        no_diac = "".join(ch for ch in nfkd if not unicodedata.combining(ch))

        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', no_diac).strip()

        return normalized

    def _normalize_filename(self, s: str) -> str:
        """
        Normalize text for filename matching.
        Strips punctuation, diacritics, and folds case.

        Args:
            s: Input string

        Returns:
            Normalized lowercase string suitable for filename comparison
        """
        # Remove diacritics first
        no_diac = self._normalize_text(s)

        # Remove punctuation except hyphens and underscores
        no_punct = re.sub(r'[^\w\s\-_]', '', no_diac)

        # Fold to lowercase for case-insensitive matching
        return no_punct.lower().strip()

    def _is_valid_ip(self, ip_str: str) -> bool:
        """Validate IP address."""
        parts = ip_str.split('.')
        if len(parts) != 4:
            return False

        for part in parts:
            try:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            except ValueError:
                return False

        return True

    def _check_negation(self, text: str, span: Tuple[int, int], window: int = 50) -> bool:
        """
        Check if an entity is negated by looking at surrounding text.

        Args:
            text: Full text
            span: Entity span (start, end)
            window: Characters to check before entity

        Returns:
            True if entity appears to be negated
        """
        if not span:
            return False

        # Check text before the entity (up to 'window' chars)
        start = max(0, span[0] - window)
        before_text = text[start:span[0]]

        # Check if any negation pattern appears before the entity
        if self.negation_regex.search(before_text):
            return True

        return False

    def _detect_qualifier(self, text: str, span: Tuple[int, int], window: int = 30) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect qualifiers (above, below, etc.) and tolerance for measurements.

        Args:
            text: Full text
            span: Entity span
            window: Characters to check around entity

        Returns:
            (qualifier, tolerance) or (None, None)
        """
        if not span:
            return None, None

        # Check before entity for qualifiers
        start = max(0, span[0] - window)
        before_text = text[start:span[0]]

        qualifier = None
        for qual_type, pattern in self.qualifier_regex.items():
            if pattern.search(before_text):
                qualifier = qual_type
                break

        # Check after entity for tolerance (±X)
        end = min(len(text), span[1] + window)
        after_text = text[span[1]:end]

        # Fixed tolerance pattern to capture cleanly without extra space
        tolerance_pattern = r'^\s*([±+\-–])\s*(\d+(?:\.\d+)?)\s*(%|°?[CF]|V|A|bar|psi)'
        tolerance_match = re.search(tolerance_pattern, after_text)

        if tolerance_match:
            # Build clean tolerance string
            sign = tolerance_match.group(1)
            value = tolerance_match.group(2)
            unit = tolerance_match.group(3)
            tolerance = f"{sign}{value}{unit}"
        else:
            tolerance = None

        return qualifier, tolerance

    def _is_noise_context(self, text: str, span: Tuple[int, int], window: int = 50) -> bool:
        """
        Check if a match appears in a noisy context (dates, years, URLs, IPs, protocols).
        Used to filter false positives from error_code, version, part_number patterns.

        Args:
            text: Full text
            span: Entity span
            window: Characters to check around entity

        Returns:
            True if match appears in noise context (should be rejected)
        """
        if not span:
            return False

        # Get context window around the match
        start = max(0, span[0] - window)
        end = min(len(text), span[1] + window)
        context = text[start:end]
        matched_text = text[span[0]:span[1]]

        # Noise patterns (protocol names, network terms)
        noise_pattern = re.compile(r'\b(HTTP|HTTPS|SMTP|DNS|PORT|IP|RFC|UTC|GMT|JPEG|PNG|GIF|PDF|URL|EMAIL|FTP|SSH)\b', re.I)
        if noise_pattern.search(context):
            return True

        # Check if matched text looks like a year (1990-2099)
        if re.match(r'^\d{4}$', matched_text):
            year_val = int(matched_text)
            if 1990 <= year_val <= 2099:
                return True

        # Check if matched text looks like a date (dd/mm/yyyy or mm/dd/yyyy or dd.mm.yyyy)
        date_pattern = re.compile(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$')
        if date_pattern.match(matched_text):
            return True

        # Check if inside URL or email pattern
        url_email_pattern = re.compile(r'(https?://|www\.|@[\w.-]+\.|[\w.-]+@)')
        if url_email_pattern.search(context):
            return True

        return False

    def _context_confidence(self, text: str, span: Tuple[int, int], entity_type: str,
                           base: float = 0.7, window: int = 50) -> float:
        """
        Calculate confidence score based on context window around the match.

        Args:
            text: Full text
            span: Entity span (start, end)
            entity_type: Type of entity (to look up context patterns)
            base: Base confidence score (0-1)
            window: Characters to check around entity

        Returns:
            Confidence score (0-1)
        """
        if not span or entity_type not in self.CONTEXT_PATTERNS:
            return base

        # Get context window
        start = max(0, span[0] - window)
        end = min(len(text), span[1] + window)
        context_window = text[start:end]

        score = base
        context_config = self.CONTEXT_PATTERNS[entity_type]

        # Boost for positive context
        pos_pattern = context_config.get('positive')
        if pos_pattern and pos_pattern.search(context_window):
            score += 0.2

        # Penalize for negative context
        neg_pattern = context_config.get('negative')
        if neg_pattern and neg_pattern.search(context_window):
            score -= 0.3

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, score))
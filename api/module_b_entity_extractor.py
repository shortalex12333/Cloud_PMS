"""
Module B: Maritime Entity Extractor (Enhanced with REGEX_PRODUCTION)
====================================================================

PURPOSE: Extract entities (brands, equipment, parts, symptoms, etc.) from user queries.
         This is the MAIN extraction engine used by the search system.

WHAT IT DOES:
- Takes a query like "MTU 16V4000 engine overheating"
- Returns structured entities: brand=MTU, model=16V4000, equipment=engine, symptom=overheating
- Each entity has a TYPE, VALUE, CANONICAL form, CONFIDENCE score, and WEIGHT

ENTITIES IT EXTRACTS (using 1,955 patterns):
- Equipment (engines, pumps, generators, etc.) - Groups 1-10
- Systems (cooling, fuel, electrical, etc.) - Groups 1-10
- Parts (filters, valves, sensors, etc.) - Groups 1-10
- Symptoms (overheating, vibration, leaks, etc.) - Group 11
- Fault codes (E047, SPN/FMI, OBD-II, etc.) - Group 14
- Sensor readings (temperature, pressure, voltage) - Groups 12, 16
- Actions (replace, inspect, calibrate) - Group 15
- Measurements (24V, 85°C, 3 bar, etc.)

STRICT RULES:
- This module ONLY extracts WHAT the user is talking about
- It does NOT determine WHAT the user wants to do (that's module_a)
- It does NOT interact with micro-action logic
- Returns canonical mappings for consistent search

WHY 1,955 PATTERNS?
- Original version had only 60 patterns (limited coverage)
- Enhanced version has 62,987 terms across 1,955 patterns (32x increase)
- This means better recognition of marine brands, equipment, symptoms, etc.
"""

# =============================================================================
# IMPORTS - Tools we need from Python
# =============================================================================

import re  # Regular expressions - for pattern matching text
from typing import List, Dict, Tuple, Optional, Set  # Type hints - helps catch errors
from dataclasses import dataclass  # Makes it easy to create data containers

# =============================================================================
# IMPORT PATTERN DATA - Load the 1,955 patterns for entity extraction
# =============================================================================
# We try to import from 'api.entity_extraction_loader' first (when running as part of API)
# If that fails, we try 'entity_extraction_loader' (when running the file directly)
# If both fail, we use fallback mode with limited patterns

try:
    # First try: Import as part of the API package
    from api.entity_extraction_loader import (
        get_equipment_gazetteer,    # Function to load brand/equipment lists
        get_diagnostic_patterns,     # Function to load symptom/fault patterns
        calculate_weight,            # Function to calculate entity importance
        extract_entities_from_text,  # Alternative extraction function
        PATTERNS_AVAILABLE           # Boolean: True if patterns loaded successfully
    )
except ImportError:
    try:
        # Second try: Import when running file directly (for testing)
        from entity_extraction_loader import (
            get_equipment_gazetteer,
            get_diagnostic_patterns,
            calculate_weight,
            extract_entities_from_text,
            PATTERNS_AVAILABLE
        )
    except ImportError:
        # Last resort: No patterns available, will use basic fallback
        PATTERNS_AVAILABLE = False
        print("⚠️  Warning: entity_extraction_loader not found. Using fallback patterns.")


# =============================================================================
# HARD vs SOFT ENTITY CLASSIFICATION
# =============================================================================
# WHY THIS MATTERS:
# - HARD entities are specific, reliable, and can trigger automatic actions
#   Example: Fault code E047 is very specific - we know exactly what it means
#
# - SOFT entities are subjective, need context, and may require human validation
#   Example: "vibration" could mean many things - need more context
#
# The search system uses this to decide how much to trust each entity

HARD_ENTITY_TYPES = {
    'fault_code',      # E047, SPN 100 FMI 3 - specific diagnostic codes that map to exact issues
    'measurement',     # 24V, 85°C, 2 bar - concrete numerical values with units
    'model',           # 16V4000, 3512, LB-2800 - specific product identifiers
    'brand',           # MTU, Caterpillar, Furuno - known manufacturers (we have a list)
    'part',            # membrane, impeller - specific replacement components
    'equipment',       # generator, radar, pump - known equipment types (we have a list)
    'equipment_code',  # ME-S-001, GEN-002 - specific PMS asset identifiers
    'part_number',     # ENG-0008-103, FIL-0127-320 - specific PMS part numbers
    'location_code',   # BOX-2A, LOCKER-B1 - specific storage locations
}

SOFT_ENTITY_TYPES = {
    'symptom',       # overheating, vibration - subjective, could mean different things
    'observation',   # "seems hot", "making noise" - human perception, not measured
    'diagnostic',    # "high exhaust temperature" - interpretive statement
    'action',        # replace, inspect - what user wants to do, not a fact
    'person',        # captain, engineer - role reference, not equipment
    'system',        # cooling system - broad category, not specific component
    'location',      # engine room - spatial reference, not equipment
    'maritime_term', # general maritime vocabulary that doesn't fit other categories
}


# =============================================================================
# EntityDetection CLASS - Container for a single detected entity
# =============================================================================
# This is a "dataclass" - Python automatically creates __init__ and other methods
# Each entity we find gets stored in one of these containers

@dataclass
class EntityDetection:
    """
    Container for a single detected entity.

    Example: If we find "MTU" in the query, we create:
        EntityDetection(
            type="brand",           # What kind of entity
            value="MTU",            # Exact text from query
            canonical="MTU",        # Standardized form (for matching)
            confidence=0.95,        # How sure we are (0.0 to 1.0)
            span=(0, 3),           # Position in query (start, end)
            metadata={"source": "core_gazetteer"},  # Extra info
            weight=3.5              # Search importance (1.0 to 5.0)
        )
    """
    type: str                           # Entity type: equipment, brand, symptom, etc.
    value: str                          # Original text exactly as it appeared in query
    canonical: str                      # Normalized form: "mtu" → "MTU", "main engine" → "MAIN_ENGINE"
    confidence: float                   # Confidence score: 0.0 = no confidence, 1.0 = certain
    span: Tuple[int, int]              # Position in query: (start_index, end_index)
    metadata: Optional[Dict] = None     # Extra info: source, domain, subdomain, etc.
    weight: float = 2.0                 # Search weight: higher = more important for ranking

    @property
    def is_hard(self) -> bool:
        """
        Check if this is a 'hard' entity (high confidence, actionable).

        Returns True if entity type is in HARD_ENTITY_TYPES.
        Example: fault_code, brand, model are hard entities
        """
        return self.type in HARD_ENTITY_TYPES

    @property
    def is_soft(self) -> bool:
        """
        Check if this is a 'soft' entity (needs validation/context).

        Returns True if entity type is in SOFT_ENTITY_TYPES or not in HARD.
        Example: symptom, observation, action are soft entities
        """
        return self.type in SOFT_ENTITY_TYPES or self.type not in HARD_ENTITY_TYPES

    @property
    def hardness(self) -> str:
        """Return 'hard' or 'soft' classification as a string."""
        return 'hard' if self.is_hard else 'soft'

    def to_dict(self) -> Dict:
        """
        Convert entity to dictionary for JSON output.

        This is what gets sent to the search system.
        It calculates the final weight based on entity type and value length.

        WEIGHT RANGES (for search boosting - higher = more important):
        - fault_code: 4.5 (highly specific diagnostic code)
        - symptom: 4.0 (key diagnostic signal for troubleshooting)
        - model: 4.0 (specific product identifier)
        - measurement: 3.8 (concrete numerical value)
        - brand: 3.5 (known manufacturer - narrows down search)
        - document_type: 3.2 (manual, schematic - document category)
        - part: 3.0 (specific component)
        - equipment: 2.8 (equipment type - broader than part)
        - action: 2.5 (verb/intent - what user wants to do)
        - system: 2.3 (broad category like "cooling system")
        - location: 2.0 (spatial reference)
        - person: 2.0 (crew role)
        - maritime_term: 2.0 (general vocabulary)

        canonical_weight is 80% of value weight (used for fallback searches)
        """
        # Base weights by entity type - higher = more important for search ranking
        type_weights = {
            'fault_code': 4.5,      # Fault codes are very specific - high weight
            'equipment_code': 4.5,  # Equipment codes (ME-S-001) are specific assets
            'part_number': 4.3,     # Part numbers (ENG-0008-103) are specific parts
            'symptom': 4.0,         # Symptoms are key for diagnosis
            'model': 4.0,           # Model numbers are very specific
            'measurement': 3.8,     # Concrete values like "85°C"
            'brand': 3.5,           # Known brands narrow down results
            'location_code': 3.5,   # Location codes (BOX-2A) are specific
            'document_type': 3.2,   # Manual, schematic, parts list
            'part': 3.0,            # Specific components
            'equipment': 2.8,       # Equipment types (broader than parts)
            'action': 2.5,          # Verbs like replace, inspect
            'system': 2.3,          # Broad categories like "cooling system"
            'location': 2.0,        # Spatial references like "engine room"
            'person': 2.0,          # Crew roles
            'maritime_term': 2.0,   # General vocabulary
        }

        # Get base weight for this entity type (default 2.0 if type not in list)
        base_weight = type_weights.get(self.type, 2.0)

        # BOOST: Longer values are usually more specific, so add 0.5
        # Example: "main engine port side" is more specific than "engine"
        if len(self.value) > 12:
            base_weight += 0.5

        # CAP: Maximum weight is 5.0 (prevents any entity from dominating)
        weight = min(base_weight, 5.0)

        # CANONICAL WEIGHT: 80% of value weight
        # Used when searching by canonical form instead of exact value
        # Example: Searching "MAIN_ENGINE" instead of "main engine"
        canonical_weight = round(weight * 0.8, 1)

        # Return dictionary with all entity info
        return {
            "type": self.type,
            "value": self.value,
            "canonical": self.canonical,
            "weight": weight,
            "canonical_weight": canonical_weight,
        }


# =============================================================================
# MaritimeEntityExtractor CLASS - The main extraction engine
# =============================================================================

class MaritimeEntityExtractor:
    """
    Maritime entity extractor with comprehensive pattern library.

    HOW IT WORKS:
    1. Load 1,955 bundled patterns (brands, equipment, symptoms, etc.)
    2. For each query, run through all patterns to find matches
    3. Assign confidence scores and weights to each match
    4. Remove duplicates and overlapping matches
    5. Return list of EntityDetection objects

    IMPORTANT: This module ONLY identifies WHAT the user is talking about.
    It does NOT determine WHAT they want to do (that's module_a_action_detector).
    """

    def __init__(self):
        """
        Initialize the extractor.

        Sets up:
        - Pattern storage (loaded lazily)
        - Fault code patterns (hardcoded - rarely change)
        - Model number patterns (hardcoded)
        - Measurement patterns (hardcoded)
        - Person/role patterns (hardcoded)
        """
        # These will hold the loaded patterns (None until first use)
        self._gazetteer = None          # Brand/equipment/part lists
        self._diagnostic_patterns = None # Symptom/fault/action patterns
        self._patterns_loaded = False    # Flag: have we loaded patterns yet?

        # =====================================================================
        # FAULT CODE PATTERNS
        # =====================================================================
        # These detect specific error codes like E-15, SPN 100 FMI 3, P0420
        #
        # FORMAT: (regex_pattern, entity_type, confidence)
        # - regex_pattern: The pattern to match
        # - entity_type: What type of entity this is (always "fault_code" here)
        # - confidence: How confident we are when this pattern matches (0.0-1.0)
        #
        # IMPORTANT: \b means "word boundary" - prevents matching inside words
        # Without \b: "temperature 85" would match "e 85" as fault code E85 (WRONG!)
        # With \b: Only matches "E85" when it's a complete word (CORRECT!)

        self.fault_code_patterns = [
            # J1939 SPN/FMI - Standard heavy equipment diagnostic codes
            # Example: "SPN 100 FMI 3" or "SPN100 FMI3" or just "SPN 100"
            # \b = word boundary, \s* = optional spaces, (\d+) = capture numbers
            (r"\bSPN\s*(\d+)(?:\s*FMI\s*(\d+))?\b", "fault_code", 0.98),

            # Generic E-codes - Common format: E-15, E047, E-047
            # \b prevents "temperature 85" from matching as "e 85"
            # [-]? = optional hyphen
            (r"\bE[-]?\d{2,4}\b", "fault_code", 0.95),

            # OBD-II codes - Automotive standard used on some marine engines
            # P = Powertrain, C = Chassis, B = Body, U = Network
            # Example: P0420, B0456, C0789, U0234
            (r"\b[PCBU]\d{4}\b", "fault_code", 0.95),

            # MTU specific codes - MTU engine manufacturer format
            # Example: MTU 0123, MTU0456
            (r"\bMTU\s*\d{3,4}\b", "fault_code", 0.93),

            # CAT/Caterpillar codes - Caterpillar engine format
            # Example: CAT 0123, Caterpillar 456
            (r"\b(?:CAT|Caterpillar)\s*\d{3,4}\b", "fault_code", 0.92),

            # Volvo codes - Volvo uses MID/PID format
            # Example: MID 128 PID 100
            (r"\bMID\s*\d+\s*PID\s*\d+\b", "fault_code", 0.90),

            # Generic alarm codes - Catch-all for other formats
            # Example: alarm 123, error A01, fault code 456
            (r"\b(?:alarm|error|fault)\s*(?:code)?\s*[A-Z]?\d{2,5}\b", "fault_code", 0.88),
        ]

        # =====================================================================
        # MODEL NUMBER PATTERNS
        # =====================================================================
        # These detect specific product model numbers
        # Lower confidence than fault codes because model patterns are broader

        self.model_patterns = [
            # Engine models with V notation: 16V4000, 12V2000, 8V2000
            # \d{1,2} = 1 or 2 digits, V = literal V, \d{3,4} = 3 or 4 digits
            (r"\b\d{1,2}V\d{3,4}[A-Z]?\b", "model", 0.92),

            # 4-digit model numbers: 3512, 3516, 3508 (Caterpillar style)
            # Optional trailing letter: 3512B
            (r"\b\d{4}[A-Z]?\b", "model", 0.85),

            # Letter-number models: C32, C18 (Caterpillar style)
            (r"\b[A-Z]\d{2}[A-Z]?\b", "model", 0.80),

            # Alphanumeric with dash/space: LB-2800, FAR-2127 (electronics style)
            (r"\b[A-Z]{2,4}[-\s]?\d{3,5}[A-Z]?\b", "model", 0.88),
        ]

        # =====================================================================
        # MEASUREMENT PATTERNS
        # =====================================================================
        # These detect specific values with units
        # Important for diagnostics: "85°C" tells us the actual temperature

        self.measurement_patterns = [
            # Voltage: 24V, 27.5V, 230V AC, 12 volts
            # \d+ = one or more digits, (?:\.\d+)? = optional decimal
            (r"\d+(?:\.\d+)?\s*[Vv](?:olts?)?(?:\s*(?:AC|DC))?", "voltage", 0.90),

            # Temperature with degree symbol: 85°C, 100°F
            # [°º] = degree symbol (two common unicode versions)
            (r"\d+(?:\.\d+)?\s*[°º]\s*[CcFf]", "temperature", 0.92),

            # Temperature with word: 85 celsius, 100 fahrenheit
            (r"\d+(?:\.\d+)?\s*(?:celsius|fahrenheit)", "temperature", 0.92),

            # Pressure: 3 bar, 45 psi, 100 kpa
            (r"\d+(?:\.\d+)?\s*(?:bar|psi|kpa|mbar|Pa)", "pressure", 0.92),

            # RPM: 1800 rpm, 3600rpm
            (r"\d+\s*rpm", "rpm", 0.90),

            # Flow rate: 50 l/min, 13 gpm, 10 m³/h
            (r"\d+(?:\.\d+)?\s*(?:l/min|gpm|m³/h|lpm)", "flow", 0.88),

            # Current: 100A, 25 amps
            (r"\d+(?:\.\d+)?\s*[Aa](?:mps?)?", "current", 0.88),

            # Frequency: 60 Hz, 50hz
            (r"\d+(?:\.\d+)?\s*[Hh]z", "frequency", 0.88),

            # Running hours: 10,000 hours, 5000 hrs
            # (?:,\d{3})* handles thousand separators
            (r"\d+(?:,\d{3})*\s*(?:hours?|hrs?|running\s*hours?)", "hours", 0.85),
        ]

        # =====================================================================
        # EQUIPMENT CODE PATTERNS (PMS Asset Identifiers)
        # =====================================================================
        # These detect specific equipment codes from the PMS database
        # These are critical for LOOKUP queries that reference specific assets
        #
        # FORMAT: PREFIX-LOCATION-NUMBER or PREFIX-NUMBER
        # Examples:
        #   ME-S-001  = Main Engine Starboard 001
        #   ME-P-001  = Main Engine Port 001
        #   GEN-001   = Generator 001
        #   THR-B-001 = Thruster Bow 001
        #   HVAC-001  = HVAC system 001
        #   AUX-001   = Auxiliary system 001
        #   DG1, DG2  = Diesel Generator 1/2

        self.equipment_code_patterns = [
            # Main Engine codes: ME-S-001, ME-P-001, ME S 001, MES001
            # Supports various separator styles (dash, space, none)
            (r"\bME[-\s]?[SP][-\s]?\d{3}\b", "equipment_code", 0.98),

            # Generator codes: GEN-001, GEN 001, GEN001
            (r"\bGEN[-\s]?\d{3}\b", "equipment_code", 0.98),

            # Diesel Generator codes: DG1, DG2, DG-1, DG 1
            (r"\bDG[-\s]?\d{1,2}\b", "equipment_code", 0.97),

            # Thruster codes: THR-B-001, THR-S-001 (Bow/Stern)
            (r"\bTHR[-\s]?[BS][-\s]?\d{3}\b", "equipment_code", 0.98),

            # HVAC codes: HVAC-001, HVAC 001
            (r"\bHVAC[-\s]?\d{3}\b", "equipment_code", 0.98),

            # Auxiliary codes: AUX-001, AUX 001
            (r"\bAUX[-\s]?\d{3}\b", "equipment_code", 0.97),

            # Fresh Water codes: FW-P-001, FW-S-001
            (r"\bFW[-\s]?[PS][-\s]?\d{3}\b", "equipment_code", 0.97),

            # Navigation codes: NAV-001, NAV 001
            (r"\bNAV[-\s]?\d{3}\b", "equipment_code", 0.97),

            # Electrical codes: ELEC-001, EL-001
            (r"\b(?:ELEC|EL)[-\s]?\d{3}\b", "equipment_code", 0.96),

            # Generic format: 2-4 uppercase letters, optional location, 3 digits
            # Catches patterns like: PMP-001, HYD-001, SEW-001
            (r"\b[A-Z]{2,4}[-\s]?[A-Z]?[-\s]?\d{3}\b", "equipment_code", 0.90),
        ]

        # =====================================================================
        # PART NUMBER PATTERNS (PMS Part Identifiers)
        # =====================================================================
        # Detect specific part numbers from the PMS inventory
        # Format: PREFIX-XXXX-XXX (e.g., ENG-0008-103, FIL-0127-320)

        self.part_number_patterns = [
            # Standard part numbers: ENG-0008-103, FIL-0127-320
            (r"\b[A-Z]{2,4}[-\s]?\d{4}[-\s]?\d{2,3}\b", "part_number", 0.95),

            # BOX location codes: BOX-2A, BOX 3D, BOX-4
            (r"\bBOX[-\s]?\d[A-Z]?\b", "location_code", 0.93),

            # Locker codes: LOCKER-A1, LOCKER B2
            (r"\bLOCKER[-\s]?[A-Z]\d?\b", "location_code", 0.93),
        ]

        # =====================================================================
        # PERSON/ROLE PATTERNS
        # =====================================================================
        # These detect crew roles mentioned in queries
        # Useful for filtering: "show faults reported by 2nd engineer"

        self.person_patterns = {
            # Key: canonical form, Value: list of patterns that match this role
            "captain": [r"\bcaptain\b", r"\bmaster\b"],
            "chief_engineer": [r"\bchief\s+engineer\b", r"\bce\b", r"\bc\.?e\.?\b"],
            "2nd_engineer": [r"\b2nd\s+engineer\b", r"\bsecond\s+engineer\b", r"\b2e\b"],
            "3rd_engineer": [r"\b3rd\s+engineer\b", r"\bthird\s+engineer\b", r"\b3e\b"],
            "electrician": [r"\belectrician\b", r"\beto\b"],
            "bosun": [r"\bbosun\b", r"\bbo'?sun\b"],
            "1st_officer": [r"\b1st\s+officer\b", r"\bfirst\s+officer\b", r"\bchief\s+officer\b"],
        }

        # Compile all regex patterns for better performance
        # (compiled patterns run faster than compiling each time)
        self._compile_patterns()

        # Load the bundled pattern library (1,955 patterns)
        self._load_bundled_patterns()

    def _load_bundled_patterns(self):
        """
        Load the bundled REGEX_PRODUCTION patterns.

        This loads 1,955 patterns with 62,987 terms for:
        - Brands (MTU, Caterpillar, Furuno, etc.)
        - Equipment (generator, radar, pump, etc.)
        - Parts (membrane, impeller, seal, etc.)
        - Symptoms (overheating, vibration, alarm, etc.)
        - Actions (replace, inspect, calibrate, etc.)

        Called once on first use (lazy loading).
        """
        # Skip if already loaded
        if self._patterns_loaded:
            return

        # Check if pattern loader is available
        if not PATTERNS_AVAILABLE:
            print("⚠️  Bundled patterns not available. Using fallback mode.")
            self._patterns_loaded = True
            return

        try:
            # Load the two main pattern sets:
            # 1. Gazetteer: Lists of brands, equipment, parts, symptoms
            self._gazetteer = get_equipment_gazetteer()

            # 2. Diagnostic patterns: Regex patterns for symptoms, faults, actions
            self._diagnostic_patterns = get_diagnostic_patterns()

            self._patterns_loaded = True

            # Print summary of what was loaded
            brand_count = len(self._gazetteer.get('equipment_brand', set()))
            pattern_count = sum(len(v) for v in self._diagnostic_patterns.values())
            print(f"✅ Loaded bundled patterns: {brand_count} brands, {pattern_count} diagnostic patterns")

        except Exception as e:
            print(f"⚠️  Error loading bundled patterns: {e}")
            self._patterns_loaded = True  # Mark as loaded to prevent retrying

    def _compile_patterns(self):
        """
        Compile regex patterns for better performance.

        WHY COMPILE?
        - Python's re.compile() converts regex string to internal format
        - Compiled patterns run ~10x faster than compiling each time
        - We only compile once at startup, then reuse for every query
        """
        # Compile fault code patterns
        # Result: list of (compiled_pattern, entity_type, confidence) tuples
        self.compiled_fault_codes = [
            (re.compile(pattern, re.IGNORECASE), entity_type, confidence)
            for pattern, entity_type, confidence in self.fault_code_patterns
        ]

        # Compile model patterns (case-sensitive - model numbers have specific casing)
        self.compiled_models = [
            (re.compile(pattern), entity_type, confidence)
            for pattern, entity_type, confidence in self.model_patterns
        ]

        # Compile measurement patterns (case-insensitive)
        self.compiled_measurements = [
            (re.compile(pattern, re.IGNORECASE), entity_type, confidence)
            for pattern, entity_type, confidence in self.measurement_patterns
        ]

        # Compile person patterns
        # Result: dict of {canonical: [compiled_pattern, ...]}
        self.compiled_persons = {
            canonical: [re.compile(p, re.IGNORECASE) for p in patterns]
            for canonical, patterns in self.person_patterns.items()
        }

        # Compile equipment code patterns (case-insensitive)
        self.compiled_equipment_codes = [
            (re.compile(pattern, re.IGNORECASE), entity_type, confidence)
            for pattern, entity_type, confidence in self.equipment_code_patterns
        ]

        # Compile part number patterns (case-insensitive)
        self.compiled_part_numbers = [
            (re.compile(pattern, re.IGNORECASE), entity_type, confidence)
            for pattern, entity_type, confidence in self.part_number_patterns
        ]

    def extract_entities(self, query: str) -> List[EntityDetection]:
        """
        Extract all maritime entities from query.

        THIS IS THE MAIN EXTRACTION METHOD.

        HOW IT WORKS:
        1. Check DIAGNOSTIC_BLACKLIST to skip false positives
        2. Run diagnostic patterns (symptoms, faults, actions)
        3. Run core gazetteer (brands, equipment, parts)
        4. Run context-aware extraction (manual, filter types, locations)
        5. Run specialized patterns (fault codes, models, measurements)
        6. Run person patterns (crew roles)
        7. Remove duplicates and overlapping matches

        Args:
            query: The user's search query (e.g., "MTU 16V4000 engine overheating")

        Returns:
            List of EntityDetection objects, sorted by confidence
        """
        # Handle empty query
        if not query or not query.strip():
            return []

        entities = []                    # List to collect all found entities
        query_lower = query.lower()      # Lowercase for case-insensitive matching

        # Make sure patterns are loaded
        self._load_bundled_patterns()

        # =====================================================================
        # 1. DIAGNOSTIC BLACKLIST - Terms that cause false positives
        # =====================================================================
        # These terms are BLOCKED from diagnostic pattern matching because:
        # 1. They're too short and match inside other words
        # 2. They're common English words with non-maritime meanings
        # 3. They're context-dependent (need special handling)
        #
        # EXAMPLE PROBLEMS WITHOUT BLACKLIST:
        # - "inventory" → matches "vent" inside it (WRONG!)
        # - "temperature 85" → matches "e 85" as fault code (WRONG!)
        # - "co" → matches inside "cooling" (WRONG!)
        # - "manual" → matches as MANUAL_MODE fault (should be document type)

        DIAGNOSTIC_BLACKLIST = {
            # ===== VERY SHORT TERMS (≤3 chars) - Almost always false positives =====
            # These match inside other words too often
            'co',   # Matches in "cooling", "control", "company"
            'hz',   # Too short - need explicit "60 Hz" pattern
            'kw',   # Too short - need explicit "100 kW" pattern
            'pf',   # Power factor - too short
            'pm',   # Too short
            'up', 'if', 'is', 'at', 'in', 'on', 'to', 'as', 'am', 'an',
            'by', 'do', 'go', 'hi', 'id', 'it', 'me', 'my', 'no', 'of',
            'oh', 'ok', 'or', 'so', 'we', 'be',

            # ===== SHORT SENSOR/MEASUREMENT TERMS (≤4 chars) - Need explicit units =====
            'amp',   # Need "100 amps" not just "amp"
            'aqi',   # Air quality index
            'cog',   # Course over ground
            'egt',   # Exhaust gas temperature
            'log',   # Too generic - matches "log book", "catalog"
            'mho',   # Unit of conductance
            'nox',   # Nitrogen oxides
            'odd',   # Common word
            'ohm',   # Need explicit "100 ohm" pattern
            'rpm',   # Handled by measurement patterns with numbers
            'sog',   # Speed over ground
            'thd',   # Total harmonic distortion
            'vac',   # AC voltage - need explicit pattern
            'vdc',   # DC voltage - need explicit pattern
            'yaw',   # Too short
            'amps',  # Handled by measurement patterns
            'flow',  # Too generic without context

            # ===== COMMON VERBS - Not diagnostic terms =====
            'run', 'ran', 'set', 'get', 'put', 'add', 'end', 'use', 'try',
            'see', 'saw', 'let', 'ask', 'say', 'got', 'has', 'had', 'was',

            # ===== COMMON ADJECTIVES - Too generic without context =====
            'low',   # "low pressure" is valid, but "low" alone is not
            'off',   # Common word
            'out',   # Common word
            'hot',   # Common word - need "overheating" for symptom
            'old', 'new', 'bad', 'big', 'red', 'wet', 'dry', 'raw', 'dim', 'dull',

            # ===== COMMON NOUNS THAT CAUSE FALSE POSITIVES =====
            'oil',   # "oil filter" handled specially, "oil" alone is too generic
            'air',   # "air filter" handled specially
            'gas', 'sea', 'sun', 'ice', 'fog', 'mud', 'tar',
            'box', 'can', 'cap', 'cup', 'lid', 'pan', 'pin', 'rod', 'nut',
            'bar', 'bit', 'bug', 'gap', 'hub', 'jam', 'jig', 'key', 'kit',

            # ===== CONTEXT-SENSITIVE TERMS - Need special handling =====
            # "manual" = document type when after brand, fault mode otherwise
            # "filter" = equipment when "oil filter", action when "filter results"
            # "check" = action, not diagnostic
            'manual', 'filter', 'check', 'test', 'start', 'stop', 'open',
            'close', 'normal', 'mode', 'auto', 'reset', 'clear', 'load',

            # ===== DIRECTIONAL/POSITIONAL - Usually not diagnostic =====
            'left', 'right', 'back', 'front', 'top', 'bottom', 'side',
            'up', 'down', 'in', 'out', 'over', 'under',

            # ===== TIME-RELATED - Not diagnostic =====
            'now', 'then', 'soon', 'late', 'last', 'next', 'ago', 'yet',

            # ===== PARTS WITH CONFLICTING DIAGNOSTIC PATTERNS =====
            # These should match as PARTS, not as diagnostic readings
            # Example: "bearing" should be part, not "BEARING_READING"
            'bearing', 'shaft', 'seal', 'gasket', 'ring', 'liner', 'piston',
        }

        # =====================================================================
        # STEP 1: DIAGNOSTIC PATTERNS (Groups 11-16)
        # =====================================================================
        # These patterns detect symptoms, faults, actions, sensor terms
        # Example: "overheating" → symptom:OVERHEAT

        if self._diagnostic_patterns:
            # Loop through each diagnostic type (symptom, sensor_language, etc.)
            for entity_type, pattern_list in self._diagnostic_patterns.items():
                # Loop through each pattern in that type
                for pattern, domain, subdomain, canonical in pattern_list:
                    # Find all matches of this pattern in the query
                    for match in pattern.finditer(query):
                        matched_text = match.group(0).lower().strip()

                        # SKIP if matched text is in blacklist
                        if matched_text in DIAGNOSTIC_BLACKLIST:
                            continue

                        # SKIP very short matches (< 4 chars) - likely false positives
                        if len(matched_text) < 4:
                            continue

                        # Map internal type to output type
                        # Example: 'sensor_reading' → 'measurement_term'
                        output_type = self._map_diagnostic_type(entity_type)

                        # Create canonical form: uppercase, underscores
                        # Example: "high temperature" → "HIGH_TEMPERATURE"
                        canonical_form = canonical.upper().replace(" ", "_") if canonical else subdomain.upper().replace(" ", "_")

                        # Add to entities list
                        entities.append(EntityDetection(
                            type=output_type,
                            value=match.group(0),
                            canonical=canonical_form,
                            confidence=0.90,
                            span=(match.start(), match.end()),
                            metadata={
                                "source": "diagnostic_pattern",
                                "domain": domain,
                                "subdomain": subdomain,
                                "group": entity_type
                            }
                        ))

        # =====================================================================
        # STEP 2: CORE GAZETTEER - Brands, Equipment, Parts, Symptoms
        # =====================================================================
        # These are curated lists of known terms (high priority)

        if self._gazetteer:
            # -----------------------------------------------------------------
            # 2a. BRANDS (MTU, Caterpillar, Furuno, etc.)
            # -----------------------------------------------------------------
            # Highest confidence because these are verified brand names
            # FIX: Skip empty/short brands - \b\b matches every word boundary!
            for brand in self._gazetteer.get('brand', set()):
                if not brand or len(brand) < 2:
                    continue  # Skip empty or single-char brands
                # Create word-boundary pattern: \b = word boundary
                # This ensures "cat" matches "CAT" but not "catalog"
                pattern = re.compile(r'\b' + re.escape(brand) + r'\b', re.IGNORECASE)
                for match in pattern.finditer(query):
                    entities.append(EntityDetection(
                        type="brand",
                        value=match.group(0),
                        canonical=brand.upper().replace(" ", "_"),
                        confidence=0.95,  # High confidence for known brands
                        span=(match.start(), match.end()),
                        metadata={"source": "core_gazetteer", "type": "brand"}
                    ))

            # -----------------------------------------------------------------
            # 2b. EQUIPMENT (generator, radar, pump, etc.)
            # -----------------------------------------------------------------
            for equip in self._gazetteer.get('equipment', set()):
                pattern = re.compile(r'\b' + re.escape(equip) + r'\b', re.IGNORECASE)
                for match in pattern.finditer(query):
                    entities.append(EntityDetection(
                        type="equipment",
                        value=match.group(0),
                        canonical=equip.upper().replace(" ", "_"),
                        confidence=0.90,
                        span=(match.start(), match.end()),
                        metadata={"source": "core_gazetteer", "type": "equipment"}
                    ))

            # -----------------------------------------------------------------
            # 2c. PARTS (membrane, impeller, seal, etc.)
            # -----------------------------------------------------------------
            # Allow short maritime acronyms that are valid part names
            ALLOWED_SHORT_PARTS = {'avr', 'ptu', 'hpu', 'vfd', 'plc', 'ecu', 'ecm', 'pcb'}

            for part in self._gazetteer.get('part', set()):
                # Only match if: length >= 4 OR it's an allowed acronym
                if len(part) >= 4 or part.lower() in ALLOWED_SHORT_PARTS:
                    pattern = re.compile(r'\b' + re.escape(part) + r'\b', re.IGNORECASE)
                    for match in pattern.finditer(query):
                        entities.append(EntityDetection(
                            type="part",
                            value=match.group(0),
                            canonical=part.upper().replace(" ", "_"),
                            confidence=0.85,
                            span=(match.start(), match.end()),
                            metadata={"source": "core_gazetteer", "type": "part"}
                        ))

            # -----------------------------------------------------------------
            # 2d. SYMPTOMS (overheating, vibration, alarm, etc.)
            # -----------------------------------------------------------------
            for symptom in self._gazetteer.get('symptom', set()):
                if len(symptom) >= 4:  # Skip very short symptoms
                    pattern = re.compile(r'\b' + re.escape(symptom) + r'\b', re.IGNORECASE)
                    for match in pattern.finditer(query):
                        entities.append(EntityDetection(
                            type="symptom",
                            value=match.group(0),
                            canonical=symptom.upper().replace(" ", "_"),
                            confidence=0.88,
                            span=(match.start(), match.end()),
                            metadata={"source": "core_gazetteer", "type": "symptom"}
                        ))

            # -----------------------------------------------------------------
            # 2e. SYSTEM TYPES (cooling system, fuel system, etc.)
            # -----------------------------------------------------------------
            # Lower priority - these are broad categories
            # FIX: Use word boundaries instead of substring match
            # OLD: if sys_type in query_lower - would match "cooling" in "precooling"
            # NEW: Use \b word boundaries for proper matching
            for sys_type in self._gazetteer.get('system_type', set()):
                if len(sys_type) > 5:
                    pattern = re.compile(r'\b' + re.escape(sys_type) + r'\b', re.IGNORECASE)
                    for match in pattern.finditer(query):
                        entities.append(EntityDetection(
                            type="system",
                            value=match.group(0),
                            canonical=sys_type.upper().replace(" ", "_"),
                            confidence=0.78,
                            span=(match.start(), match.end()),
                            metadata={"source": "gazetteer", "type": "system_type"}
                        ))

        # =====================================================================
        # STEP 2.5: CONTEXT-AWARE EXTRACTION
        # =====================================================================
        # Handle blacklisted terms that ARE valid in specific contexts
        #
        # "manual" → document_type when it follows a brand/model
        #            Example: "MTU 16V4000 manual" → brand, model, document_type
        #
        # "filter" → equipment when preceded by oil/fuel/air/water
        #            Example: "oil filter" → equipment:OIL_FILTER
        #
        # "box 3d" → location for inventory
        #            Example: "check box 3d" → location:BOX_3D

        # -----------------------------------------------------------------
        # 2.5a. "manual" as DOCUMENT_TYPE (not MANUAL_MODE fault)
        # -----------------------------------------------------------------
        manual_pattern = re.compile(r'\bmanual\b', re.IGNORECASE)
        for match in manual_pattern.finditer(query):
            # Check what comes BEFORE "manual"
            prefix = query_lower[:match.start()].strip()
            # If there's a word before "manual" (not just "the", "a", etc.)
            # then treat it as a document request
            if prefix and not prefix.endswith(('in', 'on', 'the', 'a', 'to')):
                entities.append(EntityDetection(
                    type="document_type",
                    value=match.group(0),
                    canonical="MANUAL",
                    confidence=0.88,
                    span=(match.start(), match.end()),
                    metadata={"source": "context_aware", "context": "document_request"}
                ))

        # -----------------------------------------------------------------
        # 2.5b. FILTER TYPES as EQUIPMENT
        # -----------------------------------------------------------------
        # Match "oil filter", "fuel filter", etc. as single equipment entities
        filter_contexts = [
            (r'\b(oil\s+filter)\b', 'OIL_FILTER'),
            (r'\b(fuel\s+filter)\b', 'FUEL_FILTER'),
            (r'\b(air\s+filter)\b', 'AIR_FILTER'),
            (r'\b(water\s+filter)\b', 'WATER_FILTER'),
            (r'\b(hydraulic\s+filter)\b', 'HYDRAULIC_FILTER'),
            (r'\b(lube\s+(?:oil\s+)?filter)\b', 'LUBE_FILTER'),
            (r'\b(strainer|sea\s*strainer)\b', 'STRAINER'),
        ]
        for pattern_str, canonical in filter_contexts:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type="equipment",
                    value=match.group(0),
                    canonical=canonical,
                    confidence=0.92,
                    span=(match.start(), match.end()),
                    metadata={"source": "context_aware", "context": "filter_type"}
                ))

        # -----------------------------------------------------------------
        # 2.5c. LOCATION PATTERNS for inventory
        # -----------------------------------------------------------------
        # Match storage locations: "box 3d", "locker A2", "bin 5"
        location_patterns = [
            (r'\bbox\s+[a-z0-9]+\b', 'BOX'),
            (r'\blocker\s+[a-z0-9]+\b', 'LOCKER'),
            (r'\bstorage\s+[a-z0-9]+\b', 'STORAGE'),
            (r'\bbin\s+[a-z0-9]+\b', 'BIN'),
            (r'\bdrawer\s+[a-z0-9]+\b', 'DRAWER'),
            (r'\bshelf\s+[a-z0-9]+\b', 'SHELF'),
        ]
        for pattern_str, loc_type in location_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type="location",
                    value=match.group(0),
                    canonical=match.group(0).upper().replace(" ", "_"),
                    confidence=0.90,
                    span=(match.start(), match.end()),
                    metadata={"source": "context_aware", "location_type": loc_type}
                ))

        # =====================================================================
        # STEP 3: FAULT CODES - Specialized patterns
        # =====================================================================
        # Match specific error codes: E-15, SPN 100 FMI 3, P0420, etc.

        for pattern, entity_type, confidence in self.compiled_fault_codes:
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type=entity_type,
                    value=match.group(0),
                    canonical=match.group(0).upper().replace(" ", ""),
                    confidence=confidence,
                    span=(match.start(), match.end()),
                    metadata={"source": "fault_code_pattern"}
                ))

        # =====================================================================
        # STEP 4: MODEL NUMBERS - Specialized patterns
        # =====================================================================
        # Match product model numbers: 16V4000, 3512B, LB-2800, etc.

        for pattern, entity_type, confidence in self.compiled_models:
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type="model",
                    value=match.group(0),
                    canonical=match.group(0).upper().replace(" ", "").replace("-", ""),
                    confidence=confidence,
                    span=(match.start(), match.end()),
                    metadata={"source": "model_pattern"}
                ))

        # =====================================================================
        # STEP 5: MEASUREMENTS - Specialized patterns
        # =====================================================================
        # Match values with units: 24V, 85°C, 3 bar, etc.

        for pattern, entity_type, confidence in self.compiled_measurements:
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type="measurement",
                    value=match.group(0),
                    canonical=match.group(0).upper().replace(" ", ""),
                    confidence=confidence,
                    span=(match.start(), match.end()),
                    metadata={"source": "measurement_pattern", "measurement_type": entity_type}
                ))

        # =====================================================================
        # STEP 5.5: EQUIPMENT CODES - PMS Asset Identifiers
        # =====================================================================
        # Match specific equipment codes: ME-S-001, GEN-002, THR-B-001, etc.
        # These are CRITICAL for LOOKUP queries that reference specific assets
        # Run EARLY because equipment codes should take priority over generic matches

        for pattern, entity_type, confidence in self.compiled_equipment_codes:
            for match in pattern.finditer(query):
                matched_text = match.group(0)
                # Normalize to canonical form: ME-S-001 (uppercase, hyphen-separated)
                canonical = matched_text.upper().replace(" ", "-")
                # Ensure proper hyphen placement for codes like MES001 -> ME-S-001
                if len(canonical) >= 6 and "-" not in canonical:
                    # Try to insert hyphens at common positions
                    if canonical.startswith("ME") and len(canonical) >= 6:
                        canonical = f"{canonical[:2]}-{canonical[2]}-{canonical[3:]}"
                    elif canonical.startswith("GEN") and len(canonical) >= 6:
                        canonical = f"{canonical[:3]}-{canonical[3:]}"
                    elif canonical.startswith("THR") and len(canonical) >= 7:
                        canonical = f"{canonical[:3]}-{canonical[3]}-{canonical[4:]}"

                entities.append(EntityDetection(
                    type=entity_type,
                    value=matched_text,
                    canonical=canonical,
                    confidence=confidence,
                    span=(match.start(), match.end()),
                    metadata={"source": "equipment_code_pattern"}
                ))

        # =====================================================================
        # STEP 5.6: PART NUMBERS - PMS Part/Location Identifiers
        # =====================================================================
        # Match part numbers and location codes: ENG-0008-103, BOX-2A, etc.

        for pattern, entity_type, confidence in self.compiled_part_numbers:
            for match in pattern.finditer(query):
                matched_text = match.group(0)
                canonical = matched_text.upper().replace(" ", "-")
                entities.append(EntityDetection(
                    type=entity_type,
                    value=matched_text,
                    canonical=canonical,
                    confidence=confidence,
                    span=(match.start(), match.end()),
                    metadata={"source": "part_number_pattern"}
                ))

        # =====================================================================
        # STEP 6: PERSONS/ROLES - Crew positions
        # =====================================================================
        # Match crew roles: captain, chief engineer, 2nd engineer, etc.

        for canonical, patterns in self.compiled_persons.items():
            for pattern in patterns:
                for match in pattern.finditer(query):
                    entities.append(EntityDetection(
                        type="person",
                        value=match.group(0),
                        canonical=canonical.upper(),
                        confidence=0.85,
                        span=(match.start(), match.end()),
                        metadata={"source": "person_pattern"}
                    ))

        # =====================================================================
        # STEP 7: REMOVE DUPLICATES AND OVERLAPS
        # =====================================================================
        # Multiple patterns might match the same text
        # Keep the highest confidence match when there's overlap

        entities = self._deduplicate_entities(entities)

        return entities

    def _map_diagnostic_type(self, entity_type: str) -> str:
        """
        Map internal diagnostic pattern types to output entity types.

        WHY MAPPING?
        Internal names (from pattern groups) don't match what the search expects.
        This translates internal names to user-friendly output names.

        Args:
            entity_type: Internal type from diagnostic patterns

        Returns:
            Output type for the entity
        """
        mapping = {
            'symptom': 'symptom',               # Keep as symptom
            'sensor_language': 'diagnostic',    # Sensor terms → diagnostic
            'human_report': 'observation',      # "seems hot" → observation
            'fault_classification': 'fault',    # Fault types → fault
            'action': 'action',                 # Actions stay as actions
            'sensor_reading': 'measurement_term' # Readings → measurement_term
        }
        return mapping.get(entity_type, 'maritime_term')

    def _deduplicate_entities(self, entities: List[EntityDetection]) -> List[EntityDetection]:
        """
        Remove overlapping entities, keeping those with higher confidence.

        PROBLEM:
        Multiple patterns might match the same text:
        - "oil filter" could match as: equipment + "oil" + "filter"
        - We only want: equipment:"oil filter" (the most specific match)

        SOLUTION:
        1. Sort entities by confidence (highest first)
        2. Go through each entity
        3. If it overlaps with an already-kept entity, skip it
        4. If no overlap, keep it and mark its position as "occupied"

        Args:
            entities: List of all detected entities (may have overlaps)

        Returns:
            Filtered list with no overlapping entities
        """
        if not entities:
            return []

        # FILTER 1: Remove very short matches (likely false positives)
        # Unless they have very high confidence (>= 0.9)
        entities = [e for e in entities if len(e.value) >= 2 or e.confidence >= 0.9]

        # SORT: By confidence (highest first), then by length (longest first)
        # This ensures we keep the best, most specific matches
        entities = sorted(entities, key=lambda e: (e.confidence, e.span[1] - e.span[0]), reverse=True)

        filtered = []            # Entities we're keeping
        occupied_spans = []      # Text positions already used

        for entity in entities:
            # Check if this entity overlaps with any we've already kept
            overlaps = False
            for start, end in occupied_spans:
                # Two spans overlap if: NOT (one ends before other starts)
                # entity.span[1] <= start means entity ends before occupied starts
                # entity.span[0] >= end means entity starts after occupied ends
                if not (entity.span[1] <= start or entity.span[0] >= end):
                    overlaps = True
                    break

            if not overlaps:
                # No overlap - keep this entity
                filtered.append(entity)
                occupied_spans.append(entity.span)

        return filtered

    def extract_and_classify(self, query: str) -> Dict[str, List[EntityDetection]]:
        """
        Extract entities and group them by hardness classification.

        USEFUL FOR: Deciding which entities can trigger automatic actions
        vs which need human validation.

        Args:
            query: The user's search query

        Returns:
            {
                'hard': [EntityDetection, ...],  # High confidence, actionable
                'soft': [EntityDetection, ...],  # Need validation
            }
        """
        entities = self.extract_entities(query)
        return {
            'hard': [e for e in entities if e.is_hard],
            'soft': [e for e in entities if e.is_soft],
        }

    def get_extraction_summary(self, query: str) -> Dict:
        """
        Get a summary of extraction results with hard/soft breakdown.

        USEFUL FOR: Debugging and understanding what was extracted.

        Args:
            query: The user's search query

        Returns:
            {
                'query': str,
                'total_entities': int,
                'hard_count': int,
                'soft_count': int,
                'hard_entities': [...],
                'soft_entities': [...],
                'by_type': {'brand': 2, 'symptom': 1, ...}
            }
        """
        classified = self.extract_and_classify(query)

        # Count entities by type
        by_type = {}
        for e in classified['hard'] + classified['soft']:
            by_type[e.type] = by_type.get(e.type, 0) + 1

        return {
            'query': query,
            'total_entities': len(classified['hard']) + len(classified['soft']),
            'hard_count': len(classified['hard']),
            'soft_count': len(classified['soft']),
            'hard_entities': [e.to_dict() for e in classified['hard']],
            'soft_entities': [e.to_dict() for e in classified['soft']],
            'by_type': by_type,
        }

    def extract_with_unknowns(
        self,
        query: str,
        yacht_id: Optional[str] = None,
        log_unknowns: bool = True
    ) -> Dict:
        """
        Extract entities and optionally log unknown terms.

        THIS IS THE RECOMMENDED METHOD FOR PRODUCTION USE.

        WHY LOG UNKNOWNS?
        - Unknown terms reveal gaps in our pattern coverage
        - Over time, we can add patterns for frequently-seen unknowns
        - Helps improve the extraction system

        Args:
            query: The query text
            yacht_id: Optional yacht ID for tracking (which yacht had this issue)
            log_unknowns: Whether to save unknowns to database

        Returns:
            {
                'entities': [...],      # All entities as dicts
                'unknowns': [...],      # Terms not matched by any pattern
            }
        """
        # Try to import unknowns logger (may not be available)
        try:
            from unknowns_logger import get_unknowns_logger
            logger = get_unknowns_logger()
        except ImportError:
            logger = None

        # Extract entities
        entities = self.extract_entities(query)

        # Build entity info for unknowns detection
        entities_with_spans = [
            {'value': e.value, 'span': list(e.span)}
            for e in entities
        ]

        # Find terms not covered by any entity (unknowns)
        unknowns = []
        if logger:
            if log_unknowns:
                unknowns = logger.log_query_unknowns(query, entities_with_spans, yacht_id)
            else:
                unknowns = logger.find_unknowns(query, entities_with_spans)

        return {
            'entities': [e.to_dict() for e in entities],
            'unknowns': [u['term'] for u in unknowns],
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================
# We use a singleton pattern so the extractor is only created once
# and reused for all requests. This is more efficient because:
# 1. Patterns are only loaded once (at startup)
# 2. No repeated compilation of regex patterns
# 3. Lower memory usage

_extractor_instance = None


def get_extractor() -> MaritimeEntityExtractor:
    """
    Get or create singleton extractor instance.

    USAGE:
        extractor = get_extractor()
        entities = extractor.extract_entities("MTU engine overheating")
    """
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = MaritimeEntityExtractor()
    return _extractor_instance


# =============================================================================
# TEST CODE - Runs when file is executed directly
# =============================================================================
# Usage: python module_b_entity_extractor.py

if __name__ == "__main__":
    # Create extractor
    extractor = MaritimeEntityExtractor()

    # Test queries covering different entity types
    test_cases = [
        "MTU 16V4000 engine overheating with high exhaust temperature",
        "watermaker membrane needs replacement, low output flow",
        "Furuno radar display showing error code E-15",
        "fire damper stuck open in engine room",
        "create work order for bilge pump",
        "E047 coolant leak ME1",
        "sea water pump pressure low 2 bar",
        "24V generator failure alarm",
        "captain reported vibration from main engine at 1800 rpm",
    ]

    print("=" * 80)
    print("Module B: Maritime Entity Extractor - Enhanced Tests")
    print("Using REGEX_PRODUCTION bundled patterns (1,955 patterns, 62,987 terms)")
    print("=" * 80)

    for query in test_cases:
        entities = extractor.extract_entities(query)
        print(f"\nQuery: '{query}'")
        print(f"Entities found: {len(entities)}")
        for entity in entities:
            # Show source in metadata if available
            meta_info = ""
            if entity.metadata:
                source = entity.metadata.get('source', '')
                meta_info = f" [{source}]"
            print(f"  - {entity.type}: '{entity.value}' → {entity.canonical} (conf: {entity.confidence:.2f}){meta_info}")

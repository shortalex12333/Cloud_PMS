# Code Review Guide - Plain English Explanations

This document explains every line of code in the entity extraction system in plain English.

---

# FILE 1: intent_parser.py
**Purpose:** Decides what the user wants to do (search, create, update, etc.)

---

## Lines 1-21: File Description
```
Lines 1-21 are comments explaining what this file does:
- It uses AI (GPT) to understand what the user wants
- Examples: "what machines are failing" = analytics, "create work order" = create something
- Output includes: what they want (intent), what type of request, entities found, confidence level
```

## Lines 23-28: Import Tools
```python
import os          # Line 23: Lets us read computer settings (like API keys)
import re          # Line 24: Lets us search text for patterns
import json        # Line 25: Lets us work with JSON data format
from typing import Dict, List, Optional, Tuple  # Line 26: Defines data types for clarity
from dataclasses import dataclass  # Line 27: Makes it easy to create data containers
from enum import Enum  # Line 28: Creates fixed lists of options
```

## Lines 31-127: INTENT CATEGORIES
**What it does:** Defines ALL possible actions a user might want to do (67 total actions)

```
INTENT_CATEGORIES = {
    "fix_something": [           # Category: User wants to fix a problem
        "diagnose_fault",        # Find out what's wrong
        "report_fault",          # Tell the system about a problem
        "show_manual_section",   # Show the manual page for this issue
        "view_fault_history",    # Show past problems
        "suggest_parts",         # Recommend parts needed for fix
        "create_work_order_from_fault",  # Make a work order from the fault
        "add_fault_note",        # Add a comment to the fault
        "add_fault_photo",       # Add a picture to the fault
        "link_equipment_to_fault",  # Connect equipment to this fault
    ],

    "do_maintenance": [          # Category: User wants to do maintenance work
        "create_work_order",     # Create a new work order
        "view_work_order_history",  # See past work orders
        "mark_work_order_complete",  # Mark work as done
        ... etc
    ],

    "manage_equipment": [        # Category: User wants to manage equipment
        "view_equipment_details",    # See equipment info
        "view_equipment_history",    # See equipment past
        ... etc
    ],

    "control_inventory": [       # Category: User wants to manage parts/stock
        "view_part_stock",       # Check how many parts we have
        "add_part",              # Add a new part
        "order_part",            # Order a part
        ... etc
    ],

    "communicate_status": [      # Category: User wants to share information
        "add_to_handover",       # Add to crew handover notes
        ... etc
    ],

    "comply_audit": [            # Category: Compliance and legal stuff
        "view_hours_of_rest",    # See crew rest hours
        ... etc
    ],

    "procure_suppliers": [       # Category: Buying and suppliers
        "create_purchase_request",  # Start a purchase
        ... etc
    ],

    "search_documents": [        # Category: Finding documents
        "find_document",         # Search for a document
        ... etc
    ],

    "analytics": [               # Category: Statistics and reports
        "view_failure_stats",    # See failure statistics
        ... etc
    ],
}
```

## Lines 123-127: Create Flat List
```
ALL_INTENTS = []                 # Line 124: Create empty list
for category, intents in INTENT_CATEGORIES.items():  # Line 125: Go through each category
    ALL_INTENTS.extend(intents)  # Line 126: Add all intents to the flat list
# Result: ALL_INTENTS = ["diagnose_fault", "report_fault", "show_manual_section", ...]
# This makes it easy to check if an intent is valid
```

## Lines 129-138: QUERY TYPES
**What it does:** Defines the 5 types of requests

```python
class QueryType(Enum):
    SEARCH = "search"           # Finding things (documents, equipment, parts)
    AGGREGATION = "aggregation" # Statistics ("how many", "most failing", "overdue count")
    MUTATION = "mutation"       # Changing things (create, update, delete)
    COMPLIANCE = "compliance"   # Legal/safety checks (hours of rest, certificates)
    LOOKUP = "lookup"           # Simple lookups (inventory location, stock check)
```

## Lines 141-152: MUTATION INTENTS
**What it does:** Lists which intents change data (need special handling)

```python
MUTATION_INTENTS = {
    "create_work_order",        # These all CHANGE data
    "mark_work_order_complete", # They get routed to n8n workflow
    "add_fault_note",           # Not just reading, but writing
    "order_part",               # Need confirmation before executing
    ... etc
}
```

## Lines 154-159: AGGREGATION KEYWORDS
**What it does:** Words that indicate the user wants statistics

```python
AGGREGATION_KEYWORDS = [
    "most",           # "what fails MOST"
    "least",          # "what fails LEAST"
    "failing",        # "what is FAILING"
    "how many",       # "HOW MANY work orders"
    "count",          # "COUNT of faults"
    "average",        # "AVERAGE time"
    "overdue",        # "what is OVERDUE"
    "due today",      # "what is DUE TODAY"
    ... etc
]
```

## Lines 162-296: GPT PROMPT (System Instructions for AI)
**What it does:** Tells GPT how to understand user queries

```
This is a large block of instructions given to GPT:
1. What role it plays (yacht maintenance system parser)
2. What it needs to do (classify intent, extract entities)
3. What categories exist (fix, maintain, inventory, etc.)
4. What query types exist (search, aggregation, mutation, etc.)
5. What output format to use (JSON)
6. Examples of queries and correct responses

Examples given:
- "what machines are failing the most"
  → intent: view_failure_stats, query_type: aggregation

- "create work order for stabilizer not leveling"
  → intent: create_work_order, query_type: mutation

- "who hasn't completed their hours of rest"
  → intent: view_compliance_status, query_type: compliance
```

## Lines 303-324: ParsedIntent Class
**What it does:** Container for the parsing result

```python
@dataclass
class ParsedIntent:
    intent: str              # What action? e.g., "create_work_order"
    intent_category: str     # Which category? e.g., "do_maintenance"
    query_type: str          # What type? e.g., "mutation"
    entities: Dict           # What things? e.g., {"equipment": "stabilizer"}
    parameters: Dict         # Any filters? e.g., {"limit": 10}
    confidence: float        # How sure? e.g., 0.92 (92%)
    requires_mutation: bool  # Does it change data? True/False
    raw_query: str           # Original user text

    def to_dict(self):       # Convert to dictionary for easy use
        return {...}
```

## Lines 327-382: IntentParser Class
**What it does:** The main parser that uses GPT to understand queries

```python
class IntentParser:
    def __init__(self):
        self.model = "gpt-4o-mini"  # Which GPT model to use
        self.api_key = os.environ.get("OPENAI_API_KEY")  # Get API key from settings

    def parse(self, query):
        # Step 1: If no API key, use simple backup method
        if not self.api_key:
            return self._fallback_parse(query)

        # Step 2: Send query to GPT
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},  # Instructions
                    {"role": "user", "content": query}             # User's question
                ],
                temperature=0.1,   # Low = more consistent answers
                max_tokens=500,    # Limit response length
            )

            # Step 3: Parse GPT's response as JSON
            result = json.loads(response_text)

            # Step 4: Return structured result
            return ParsedIntent(
                intent=result["intent"],
                intent_category=result["intent_category"],
                ... etc
            )
        except Exception:
            # Step 5: If GPT fails, use backup method
            return self._fallback_parse(query)
```

## Lines 384-478: Fallback Parser (When GPT Unavailable)
**What it does:** Simple keyword-based parsing when GPT is not available

```python
def _fallback_parse(self, query):
    query_lower = query.lower()

    # Start with defaults
    query_type = "search"
    intent = "find_document"
    requires_mutation = False

    # CHECK 1: Is this about compliance (hours of rest)?
    if any(kw in query_lower for kw in ["hor", "hours of rest", "compliance"]):
        query_type = "compliance"
        intent = "view_compliance_status"

        # But if they say "update", it's a mutation
        if "update" in query_lower:
            intent = "update_hours_of_rest"
            requires_mutation = True

    # CHECK 2: Is this asking for statistics?
    elif any(kw in query_lower for kw in ["most", "failing", "how many"]):
        query_type = "aggregation"
        intent = "view_failure_stats"

    # CHECK 3: Is this about inventory?
    elif any(kw in query_lower for kw in ["box", "stock", "inventory", "location"]):
        query_type = "lookup"
        intent = "view_part_location"

    # CHECK 4: Is this a command to change something?
    # This is tricky - "order" can mean "sequence" or "purchase"
    # Only treat as mutation if clearly a command:
    elif query_lower.startswith("order "):     # "order 2 filters" = mutation
        query_type = "mutation"
        intent = "order_part"
        requires_mutation = True

    return ParsedIntent(...)
```

**LOGIC GAP:** The fallback parser is basic. It only handles common cases.
If user says "get me the stabilizer manual", it might not understand correctly.

## Lines 481-556: Query Router
**What it does:** Decides WHERE to send the request after parsing

```python
def route_query(parsed):
    # If it changes data, send to n8n workflow system
    if parsed.requires_mutation:
        return {
            "handler": "n8n",                    # n8n handles workflows
            "webhook": f"/webhook/{parsed.intent}",  # Which webhook
            "method": "POST",                    # POST = send data
        }

    # If it's statistics, send to analytics endpoint
    elif parsed.query_type == "aggregation":
        return {
            "handler": "render",                 # Render handles queries
            "endpoint": "/api/analytics",
        }

    # If it's compliance, send to compliance endpoint
    elif parsed.query_type == "compliance":
        return {
            "handler": "render",
            "endpoint": "/api/compliance",
        }

    # If it's a simple lookup, send to inventory
    elif parsed.query_type == "lookup":
        return {
            "handler": "render",
            "endpoint": "/api/inventory/lookup",
        }

    # Default: send to search
    else:
        return {
            "handler": "render",
            "endpoint": "/api/search",
        }
```

## Lines 559-580: Main Entry Point
**What it does:** Combines parsing and routing into one function

```python
def parse_and_route(query):
    parser = IntentParser()           # Create parser
    parsed = parser.parse(query)      # Parse the query
    routing = route_query(parsed)     # Decide where to send it

    return {
        "parsed": parsed.to_dict(),   # What we understood
        "routing": routing,           # Where to send it
    }
```

---

# FILE 2: module_b_entity_extractor.py
**Purpose:** Finds specific things mentioned in text (brands, equipment, parts, symptoms)

---

## Lines 1-22: File Description
```
This file extracts "entities" from text:
- Equipment: engines, pumps, generators
- Systems: cooling, fuel, electrical
- Parts: filters, valves, sensors
- Symptoms: overheating, vibration, leaks
- Fault codes: E047, SPN/FMI codes
- Measurements: 24V, 85°C, 3 bar
```

## Lines 24-48: Import Required Tools
```python
import re           # For pattern matching
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass

# Try to import pattern data (may not exist)
try:
    from api.entity_extraction_loader import (
        get_equipment_gazetteer,   # List of known equipment terms
        get_diagnostic_patterns,   # Patterns for symptoms, faults
        calculate_weight,          # How important each entity is
        PATTERNS_AVAILABLE         # True if patterns loaded successfully
    )
except ImportError:
    PATTERNS_AVAILABLE = False     # Fallback if patterns missing
```

## Lines 51-74: HARD vs SOFT Entities
**What it does:** Classifies entities by reliability

```python
# HARD entities = high confidence, specific, actionable
HARD_ENTITY_TYPES = {
    'fault_code',    # E047, SPN 100 FMI 3 - specific diagnostic codes
    'measurement',   # 24V, 85°C, 2 bar - concrete values
    'model',         # 16V4000, 3512 - specific model numbers
    'brand',         # MTU, Caterpillar - known manufacturers
    'part',          # membrane, impeller - specific parts
    'equipment',     # generator, radar - known equipment
}

# SOFT entities = may need validation, subjective
SOFT_ENTITY_TYPES = {
    'symptom',       # overheating, vibration - could be interpretation
    'observation',   # "seems hot" - human perception
    'diagnostic',    # "high exhaust temperature" - needs context
    'action',        # replace, inspect - intent, not fact
    'person',        # captain, engineer - role reference
    'system',        # cooling system - broad category
    'location',      # engine room - spatial reference
}
```

**WHY THIS MATTERS:**
- HARD entities can trigger automatic actions
- SOFT entities might need human confirmation

## Lines 77-154: EntityDetection Class
**What it does:** Container for a single detected entity

```python
@dataclass
class EntityDetection:
    type: str           # What kind? "brand", "equipment", etc.
    value: str          # What text? "MTU", "generator"
    canonical: str      # Standard form: "MTU" → "MTU", "mtu" → "MTU"
    confidence: float   # How sure? 0.95 = 95% sure
    span: Tuple[int, int]  # Where in text? (start, end) positions
    metadata: Dict      # Extra info (source, domain, etc.)
    weight: float       # Search importance (1.0-5.0)

    def is_hard(self):
        # Returns True if this is a reliable entity
        return self.type in HARD_ENTITY_TYPES

    def to_dict(self):
        # Converts to dictionary with calculated weights
        type_weights = {
            'fault_code': 4.5,    # Fault codes are very important
            'symptom': 4.0,       # Symptoms are important for diagnosis
            'model': 4.0,         # Model numbers are specific
            'measurement': 3.8,   # Measurements are concrete
            'brand': 3.5,         # Brands help narrow down
            'document_type': 3.2, # Document type helps find right doc
            'part': 3.0,          # Parts are specific
            'equipment': 2.8,     # Equipment is useful context
            'action': 2.5,        # Actions are verbs
            'system': 2.3,        # Systems are broad
            'location': 2.0,      # Locations are context
        }

        weight = type_weights.get(self.type, 2.0)

        # Longer values get slight boost
        if len(self.value) > 12:
            weight += 0.5

        # Cap at 5.0 maximum
        weight = min(weight, 5.0)

        return {
            "type": self.type,
            "value": self.value,
            "canonical": self.canonical,
            "weight": weight,
            "canonical_weight": weight * 0.8,  # 80% for fallback searches
        }
```

**WEIGHT LOGIC:**
- Higher weight = more important for search ranking
- Fault codes (4.5) rank higher than equipment (2.8)
- Longer/more specific values get bonus

## Lines 157-282: MaritimeEntityExtractor Class - Initialization
**What it does:** Sets up all the patterns for detecting entities

```python
class MaritimeEntityExtractor:
    def __init__(self):
        # Load bundled patterns (from entity_extraction_loader.py)
        self._gazetteer = None           # List of known terms
        self._diagnostic_patterns = None  # Regex patterns
        self._patterns_loaded = False

        # FAULT CODE PATTERNS
        # These detect specific error codes like E-15, SPN 100 FMI 3
        self.fault_code_patterns = [
            # J1939 standard: SPN followed by number, optionally FMI
            (r"\bSPN\s*(\d+)(?:\s*FMI\s*(\d+))?\b", "fault_code", 0.98),

            # Generic E-codes: E-15, E047, E-047
            # The \b means "word boundary" - prevents matching "e 85" in "temperature 85"
            (r"\bE[-]?\d{2,4}\b", "fault_code", 0.95),

            # OBD-II codes: P0123, B0456, C0789, U0234
            (r"\b[PCBU]\d{4}\b", "fault_code", 0.95),

            # MTU specific codes: MTU 0123
            (r"\bMTU\s*\d{3,4}\b", "fault_code", 0.93),

            # Caterpillar codes: CAT 0123
            (r"\b(?:CAT|Caterpillar)\s*\d{3,4}\b", "fault_code", 0.92),

            # Volvo codes: MID 128 PID 100
            (r"\bMID\s*\d+\s*PID\s*\d+\b", "fault_code", 0.90),

            # Generic alarm codes: alarm 123, error A01
            (r"\b(?:alarm|error|fault)\s*(?:code)?\s*[A-Z]?\d{2,5}\b", "fault_code", 0.88),
        ]

        # MODEL PATTERNS
        # These detect model numbers like 16V4000, 3512B, LB-2800
        self.model_patterns = [
            (r"\b\d{1,2}V\d{3,4}[A-Z]?\b", "model", 0.92),  # 16V4000, 12V2000
            (r"\b\d{4}[A-Z]?\b", "model", 0.85),           # 3512, 3516B
            (r"\b[A-Z]\d{2}[A-Z]?\b", "model", 0.80),      # C32, C18
            (r"\b[A-Z]{2,4}[-\s]?\d{3,5}[A-Z]?\b", "model", 0.88),  # LB-2800, FAR-2127
        ]

        # MEASUREMENT PATTERNS
        # These detect values with units like 24V, 85°C, 3 bar
        self.measurement_patterns = [
            # Voltage: 24V, 27.5V, 230V AC
            (r"\d+(?:\.\d+)?\s*[Vv](?:olts?)?(?:\s*(?:AC|DC))?", "voltage", 0.90),

            # Temperature: 85°C, 100°F (requires degree symbol or word)
            (r"\d+(?:\.\d+)?\s*[°º]\s*[CcFf]", "temperature", 0.92),

            # Pressure: 3 bar, 45 psi
            (r"\d+(?:\.\d+)?\s*(?:bar|psi|kpa|mbar|Pa)", "pressure", 0.92),

            # RPM: 1800 rpm
            (r"\d+\s*rpm", "rpm", 0.90),

            # Flow rate: 50 l/min, 13 gpm
            (r"\d+(?:\.\d+)?\s*(?:l/min|gpm|m³/h|lpm)", "flow", 0.88),

            # Current: 100A, 25 amps
            (r"\d+(?:\.\d+)?\s*[Aa](?:mps?)?", "current", 0.88),

            # Frequency: 60 Hz
            (r"\d+(?:\.\d+)?\s*[Hh]z", "frequency", 0.88),

            # Running hours: 10,000 hours
            (r"\d+(?:,\d{3})*\s*(?:hours?|hrs?|running\s*hours?)", "hours", 0.85),
        ]

        # PERSON PATTERNS
        # These detect crew roles
        self.person_patterns = {
            "captain": [r"\bcaptain\b", r"\bmaster\b"],
            "chief_engineer": [r"\bchief\s+engineer\b", r"\bce\b"],
            "2nd_engineer": [r"\b2nd\s+engineer\b", r"\bsecond\s+engineer\b"],
            ... etc
        }
```

## Lines 284-590: extract_entities Method (THE MAIN FUNCTION)
**What it does:** Extracts all entities from a query

```python
def extract_entities(self, query):
    if not query:
        return []

    entities = []
    query_lower = query.lower()

    # =========================================================================
    # STEP 1: DIAGNOSTIC BLACKLIST
    # =========================================================================
    # These words cause false positives and should NOT be matched as diagnostics

    DIAGNOSTIC_BLACKLIST = {
        # Very short words that match inside other words
        'co',      # Would match inside "COoling", "eCOnomical"
        'hz',      # Too short without context
        'kw',      # Need explicit units

        # Common verbs - not diagnostic
        'run',     # Would match inside "RUNning"
        'set',     # Would match inside "SETting"

        # Common adjectives - too generic
        'low',     # "low" alone is not diagnostic
        'hot',     # "hot" alone is not diagnostic

        # Context-sensitive words
        'manual',  # Could be document type OR manual mode fault
        'filter',  # Could be equipment OR action
        'bearing', # Could be part OR bearing reading

        # Parts that have conflicting diagnostic patterns
        'bearing', 'shaft', 'seal', 'gasket', 'ring', 'liner', 'piston',
    }

    # =========================================================================
    # STEP 2: DIAGNOSTIC PATTERNS (symptoms, faults, actions)
    # =========================================================================
    if self._diagnostic_patterns:
        for entity_type, pattern_list in self._diagnostic_patterns.items():
            for pattern, domain, subdomain, canonical in pattern_list:
                for match in pattern.finditer(query):
                    matched_text = match.group(0).lower().strip()

                    # Skip if in blacklist
                    if matched_text in DIAGNOSTIC_BLACKLIST:
                        continue

                    # Skip very short matches (< 4 chars)
                    if len(matched_text) < 4:
                        continue

                    entities.append(EntityDetection(
                        type=output_type,
                        value=match.group(0),
                        canonical=canonical.upper(),
                        confidence=0.90,
                        span=(match.start(), match.end()),
                    ))

    # =========================================================================
    # STEP 3: CORE GAZETTEER (brands, equipment, parts, symptoms)
    # =========================================================================
    if self._gazetteer:
        # Check for BRANDS (MTU, Caterpillar, Furuno)
        for brand in self._gazetteer.get('brand', set()):
            pattern = re.compile(r'\b' + re.escape(brand) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type="brand",
                    value=match.group(0),
                    canonical=brand.upper(),
                    confidence=0.95,  # High confidence for known brands
                ))

        # Check for EQUIPMENT (generator, radar, pump)
        for equip in self._gazetteer.get('equipment', set()):
            # Similar matching...

        # Check for PARTS (membrane, impeller)
        for part in self._gazetteer.get('part', set()):
            # Skip short parts unless they're special acronyms
            ALLOWED_SHORT_PARTS = {'avr', 'ptu', 'hpu', 'vfd', 'plc', 'ecu', 'ecm'}
            if len(part) >= 4 or part.lower() in ALLOWED_SHORT_PARTS:
                # Match...

        # Check for SYMPTOMS (overheating, vibration)
        for symptom in self._gazetteer.get('symptom', set()):
            if len(symptom) >= 4:  # Skip very short
                # Match...

    # =========================================================================
    # STEP 4: CONTEXT-AWARE EXTRACTION
    # =========================================================================
    # Some blacklisted terms are valid in specific contexts

    # "manual" after brand = document type, not fault mode
    # Example: "MTU 16V4000 manual" → document_type: MANUAL
    manual_pattern = re.compile(r'\bmanual\b', re.IGNORECASE)
    for match in manual_pattern.finditer(query):
        prefix = query_lower[:match.start()].strip()
        # If there's a brand/model before "manual", it's a document request
        if prefix and not prefix.endswith(('in', 'on', 'the', 'a', 'to')):
            entities.append(EntityDetection(
                type="document_type",
                value=match.group(0),
                canonical="MANUAL",
            ))

    # "oil filter" = equipment, not separate words
    # Example: "oil filter replacement" → equipment: OIL_FILTER
    filter_contexts = [
        (r'\b(oil\s+filter)\b', 'OIL_FILTER'),
        (r'\b(fuel\s+filter)\b', 'FUEL_FILTER'),
        (r'\b(air\s+filter)\b', 'AIR_FILTER'),
        (r'\b(water\s+filter)\b', 'WATER_FILTER'),
    ]
    for pattern_str, canonical in filter_contexts:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        for match in pattern.finditer(query):
            entities.append(EntityDetection(
                type="equipment",
                canonical=canonical,
            ))

    # Location patterns for inventory
    # Example: "box 3d" → location: BOX_3D
    location_patterns = [
        (r'\bbox\s+[a-z0-9]+\b', 'BOX'),
        (r'\blocker\s+[a-z0-9]+\b', 'LOCKER'),
        (r'\bstorage\s+[a-z0-9]+\b', 'STORAGE'),
    ]

    # =========================================================================
    # STEP 5: FAULT CODES
    # =========================================================================
    for pattern, entity_type, confidence in self.compiled_fault_codes:
        for match in pattern.finditer(query):
            entities.append(EntityDetection(
                type="fault_code",
                value=match.group(0),
                canonical=match.group(0).upper(),
                confidence=confidence,
            ))

    # =========================================================================
    # STEP 6: MODEL NUMBERS
    # =========================================================================
    for pattern, entity_type, confidence in self.compiled_models:
        for match in pattern.finditer(query):
            entities.append(EntityDetection(
                type="model",
                value=match.group(0),
            ))

    # =========================================================================
    # STEP 7: MEASUREMENTS
    # =========================================================================
    for pattern, entity_type, confidence in self.compiled_measurements:
        for match in pattern.finditer(query):
            entities.append(EntityDetection(
                type="measurement",
                value=match.group(0),
            ))

    # =========================================================================
    # STEP 8: PERSONS/ROLES
    # =========================================================================
    for canonical, patterns in self.compiled_persons.items():
        for pattern in patterns:
            for match in pattern.finditer(query):
                entities.append(EntityDetection(
                    type="person",
                    canonical=canonical.upper(),
                ))

    # =========================================================================
    # STEP 9: REMOVE DUPLICATES
    # =========================================================================
    # If same text matched multiple patterns, keep highest confidence
    entities = self._deduplicate_entities(entities)

    return entities
```

## Lines 592-602: _map_diagnostic_type Method
**What it does:** Converts internal diagnostic types to output types

```python
def _map_diagnostic_type(self, entity_type):
    mapping = {
        'symptom': 'symptom',              # Keep as symptom
        'sensor_language': 'diagnostic',   # Sensor terms → diagnostic
        'human_report': 'observation',     # Human observations
        'fault_classification': 'fault',   # Fault types
        'action': 'action',                # Actions stay as actions
        'sensor_reading': 'measurement_term'  # Readings → measurement_term
    }
    return mapping.get(entity_type, 'maritime_term')
```

## Lines 604-633: _deduplicate_entities Method
**What it does:** Removes overlapping matches, keeps best ones

```python
def _deduplicate_entities(self, entities):
    if not entities:
        return []

    # Filter out very short matches (probably false positives)
    entities = [e for e in entities if len(e.value) >= 2 or e.confidence >= 0.9]

    # Sort by confidence (highest first), then by length (longest first)
    entities = sorted(entities, key=lambda e: (e.confidence, len(e.value)), reverse=True)

    filtered = []
    occupied_spans = []  # Track which text positions are already used

    for entity in entities:
        # Check if this entity overlaps with any already selected
        overlaps = False
        for start, end in occupied_spans:
            # If this entity's position overlaps with an existing one
            if not (entity.span[1] <= start or entity.span[0] >= end):
                overlaps = True
                break

        if not overlaps:
            filtered.append(entity)
            occupied_spans.append(entity.span)

    return filtered
```

**LOGIC:**
- First filters out very short matches (< 2 chars)
- Sorts by confidence (best first)
- Goes through each entity, only keeps if it doesn't overlap with already-kept entities
- This prevents "oil filter" from also matching "oil" and "filter" separately

---

# FILE 3: entity_extraction_loader.py
**Purpose:** Loads the pattern data used by module_b_entity_extractor

---

## Lines 1-50: File Description and Imports
```
This file loads pre-bundled pattern data for entity extraction.
It provides:
- Equipment gazetteer (brands, equipment types)
- Diagnostic patterns (symptoms, faults, sensor language)
- Same interface for easy replacement
```

## Lines 53-97: CONTAMINATION FILTERS
**What it does:** Lists terms that should NOT be classified as brands

```python
# Equipment terms that are NOT brand names
EQUIPMENT_INDICATORS = {
    'pump',        # "pump" is equipment, not a brand
    'motor',       # "motor" is equipment, not a brand
    'valve',       # etc.
    'sensor',
    'controller',
    'filter',      # "filter" alone is not a brand
    'engine',      # "engine" is equipment type
    'generator',   # etc.
    ... many more
}

# Document terms that are NOT brand names
DOCUMENT_INDICATORS = {
    'requirements',
    'standards',
    'manual',      # "manual" alone is not a brand
    'document',
    ... etc
}

# Product descriptions that are NOT brand names
PRODUCT_DESCRIPTORS = {
    'oil',         # "oil" alone is not a brand
    'grease',
    'lubricant',
    'temperature', # Not a brand
    ... etc
}

# Combine all filters
ALL_FILTERS = EQUIPMENT_INDICATORS | DOCUMENT_INDICATORS | PRODUCT_DESCRIPTORS
```

**WHY THIS MATTERS:**
- Prevents "engine" from being detected as a brand
- Prevents "manual" from being detected as a brand
- Only actual brand names like "MTU", "Caterpillar" should match

## Lines 99-148: CORE BRANDS List
**What it does:** Hardcoded list of known marine brands that MUST be detected

```python
CORE_BRANDS = {
    # Engine Manufacturers
    'mtu', 'caterpillar', 'cat', 'cummins', 'volvo', 'yanmar',
    'john deere', 'man', 'perkins', 'detroit diesel',

    # Navigation/Electronics
    'furuno', 'raymarine', 'garmin', 'simrad', 'navico', 'b&g',

    # Electrical/Power
    'victron', 'mastervolt', 'fischer panda', 'northern lights', 'onan',
    'kohler', 'westerbeke',

    # Watermakers
    'spectra', 'sea recovery', 'village marine', 'katadyn',

    # HVAC
    'marine air', 'cruisair', 'webasto', 'dometic', 'climma',

    # Deck Equipment
    'lewmar', 'maxwell', 'muir', 'lofrans', 'quick', 'vetus',

    # Stabilizers
    'seakeeper', 'naiad', 'wesmar', 'quantum',

    # Pumps
    'jabsco', 'johnson pump', 'rule', 'whale', 'shurflo', 'groco', 'racor',

    # Safety
    'viking', 'zodiac', 'avon', 'fireboy', 'kidde',

    # Hydraulics
    'vickers', 'rexroth', 'parker', 'eaton', 'danfoss',
}
```

## Lines 150-195: CORE EQUIPMENT List
```python
CORE_EQUIPMENT = {
    # Propulsion
    'engine', 'main engine', 'generator', 'genset', 'thruster',
    'bow thruster', 'stern thruster', 'propeller', 'shaft', 'gearbox',

    # Navigation
    'radar', 'chartplotter', 'autopilot', 'gps', 'vhf', 'ais', 'compass',

    # Electrical
    'battery', 'batteries', 'inverter', 'charger', 'alternator',

    # Water Systems
    'watermaker', 'bilge pump', 'fire pump', 'raw water pump',

    # HVAC
    'air conditioner', 'ac unit', 'chiller', 'compressor', 'heater',

    # Deck
    'windlass', 'winch', 'anchor', 'davit', 'crane', 'tender',

    # Stabilizers
    'stabilizer', 'gyro stabilizer', 'fin stabilizer',

    # Safety
    'fire damper', 'fire extinguisher', 'life raft', 'epirb',

    # Tanks
    'fuel tank', 'water tank', 'holding tank', 'day tank',

    # Filters
    'fuel filter', 'oil filter', 'air filter', 'strainer', 'separator',
}
```

## Lines 197-207: CORE PARTS List
```python
CORE_PARTS = {
    'membrane',     # Watermaker membrane
    'impeller',     # Pump impeller
    'seal',         # Various seals
    'gasket',       # Various gaskets
    'bearing',      # Bearings
    'belt',         # Drive belts
    'hose',         # Hoses
    'filter',       # Filter elements
    'sensor',       # Sensors
    'relay',        # Electrical relays
    'fuse',         # Fuses
    'thermostat',   # Thermostats
    'injector',     # Fuel injectors

    # Electrical/Hydraulic acronyms
    'avr',          # Automatic Voltage Regulator
    'ptu',          # Power Take-off Unit
    'hpu',          # Hydraulic Power Unit
    'vfd',          # Variable Frequency Drive
    'plc',          # Programmable Logic Controller
    'ecu',          # Engine Control Unit
    'ecm',          # Engine Control Module
}
```

## Lines 209-219: CORE SYMPTOMS List
```python
CORE_SYMPTOMS = {
    'overheating', 'overheat',     # Temperature issues
    'vibration',                    # Mechanical vibration
    'noise',                        # Unusual sounds
    'leak', 'leaking',             # Fluid leaks
    'failure', 'failed',           # Equipment failure
    'alarm', 'warning',            # Alarms
    'error', 'fault', 'malfunction',  # Errors
    'stuck', 'jammed', 'blocked', 'clogged',  # Blockages
    'corroded', 'worn', 'damaged',  # Wear
    'cracked', 'broken', 'seized', # Physical damage
    'smoking', 'sparking',          # Dangerous conditions
    'tripping', 'cutting out',      # Electrical issues
    'not starting', 'wont start', 'hard starting',  # Start problems
    'stalling', 'surging', 'hunting',  # Running issues
    'knocking', 'rattling', 'grinding',  # Sounds
    'low pressure', 'high pressure',    # Pressure issues
    'low voltage', 'high temperature',  # Electrical/thermal
    'no output', 'reduced output',      # Performance issues
    'intermittent', 'erratic',          # Inconsistent behavior
}
```

## Lines 222-308: load_equipment_gazetteer Function
**What it does:** Builds the complete term list for matching

```python
def load_equipment_gazetteer():
    gazetteer = {
        'brand': set(),          # Brand names
        'equipment': set(),      # Equipment types
        'part': set(),           # Part names
        'symptom': set(),        # Symptoms
        'equipment_brand': set(),  # All brand terms (backward compatibility)
        'equipment_type': set(),   # All equipment terms
        'system_type': set()       # System types (propulsion, navigation, etc.)
    }

    # Step 1: Add all CORE terms (guaranteed to be detected)
    gazetteer['brand'].update(CORE_BRANDS)
    gazetteer['equipment'].update(CORE_EQUIPMENT)
    gazetteer['part'].update(CORE_PARTS)
    gazetteer['symptom'].update(CORE_SYMPTOMS)

    # Step 2: Add compound terms from bundled patterns
    for canonical, pattern_data in EQUIPMENT_PATTERNS.items():
        terms = pattern_data.get('terms', [])

        for term in terms:
            term_lower = term.lower()

            # Skip if term matches a filter (not a brand)
            if term_lower in ALL_FILTERS:
                continue

            # Skip if any word in term is filtered
            term_words = set(term_lower.split())
            if term_words & ALL_FILTERS:
                continue

            # Skip single short words (unless core term)
            if len(term_words) == 1 and len(term_lower) < 4:
                if term_lower not in CORE_BRANDS:
                    continue

            # Add to gazetteer
            gazetteer['equipment_brand'].add(term_lower)

    # Print summary
    print(f"✅ Loaded {total_terms:,} terms")
    print(f"   - {len(gazetteer['brand']):,} core brands")
    print(f"   - {len(gazetteer['equipment']):,} core equipment types")

    return gazetteer
```

## Lines 311-391: load_diagnostic_patterns Function
**What it does:** Loads and compiles regex patterns for symptoms, faults, etc.

```python
def load_diagnostic_patterns():
    # Map group numbers to entity types
    GROUP_TO_TYPE = {
        11: 'symptom',              # Group 11 = symptoms
        12: 'sensor_language',      # Group 12 = sensor terms
        13: 'human_report',         # Group 13 = human observations
        14: 'fault_classification', # Group 14 = fault types
        15: 'action',               # Group 15 = action verbs
        16: 'sensor_reading'        # Group 16 = measurement terms
    }

    patterns = {
        'symptom': [],
        'sensor_language': [],
        'human_report': [],
        'fault_classification': [],
        'action': [],
        'sensor_reading': []
    }

    for canonical, pattern_data in DIAGNOSTIC_PATTERNS.items():
        # Skip blacklisted patterns (known false positive generators)
        if canonical in CANONICAL_BLACKLIST:
            continue

        group = pattern_data.get('group', 0)
        entity_type = GROUP_TO_TYPE.get(group)

        if not entity_type:
            continue

        regex_str = pattern_data.get('regex', '')

        if not regex_str:
            continue

        # CRITICAL FIX: Add word boundaries to prevent false positives
        # This prevents "vent" from matching inside "inVENTory"
        if not regex_str.startswith(r'\b'):
            regex_str = r'\b' + regex_str
        if not regex_str.endswith(r'\b'):
            regex_str = regex_str + r'\b'

        # Compile the regex
        try:
            compiled = re.compile(regex_str, re.IGNORECASE)
            patterns[entity_type].append((compiled, domain, subdomain, canonical))
        except re.error as e:
            print(f"⚠️  Regex error in {canonical}: {e}")
            continue

    return patterns
```

**CRITICAL FIX EXPLAINED:**
- The `\b` is a "word boundary" marker
- Without it: pattern "vent" would match "inVENTory" (wrong!)
- With it: pattern `\bvent\b` only matches "vent" as a whole word

## Lines 394-438: calculate_weight Function
**What it does:** Calculates importance weight for search ranking

```python
def calculate_weight(entity_type, metadata, text_length=0):
    """
    Weight ranges:
    - Specific models/codes: 4.0-5.0 (most important)
    - Brand names: 3.0-3.5
    - Component types: 2.5-3.0
    - Generic terms: 2.0-2.5
    - Symptoms/diagnostics: 3.5-4.5
    - Actions: 2.0-3.0
    """
    type_weights = {
        'fault_code': 4.5,          # Fault codes are very specific
        'symptom': 4.0,             # Symptoms are important for diagnosis
        'model': 4.0,               # Model numbers are specific
        'fault_classification': 3.8,
        'product_name': 3.5,
        'sensor_reading': 3.5,
        'sensor_language': 3.3,
        'equipment_brand': 3.2,
        'human_report': 3.0,
        'equipment_type': 2.8,
        'action': 2.5,
        'system_type': 2.3
    }

    base_weight = type_weights.get(entity_type, 2.0)

    # Longer/more specific text gets higher weight
    if text_length > 15:
        base_weight += 1.0    # Very specific = +1.0
    elif text_length > 8:
        base_weight += 0.5    # Somewhat specific = +0.5

    # Diagnostic groups (11-16) get bonus
    group = metadata.get('group', 0)
    if 11 <= group <= 16:
        base_weight += 0.5

    # Cap at 5.0 maximum
    return min(base_weight, 5.0)
```

## Lines 455-472: Cached Loaders
**What it does:** Loads patterns once and reuses them

```python
_equipment_gazetteer = None
_diagnostic_patterns = None

def get_equipment_gazetteer():
    global _equipment_gazetteer
    # Only load if not already loaded
    if _equipment_gazetteer is None:
        _equipment_gazetteer = load_equipment_gazetteer()
    return _equipment_gazetteer

def get_diagnostic_patterns():
    global _diagnostic_patterns
    if _diagnostic_patterns is None:
        _diagnostic_patterns = load_diagnostic_patterns()
    return _diagnostic_patterns
```

**WHY CACHING MATTERS:**
- Loading patterns is slow (thousands of terms)
- Only do it once, then reuse
- Makes subsequent extractions fast

---

# SUMMARY: KEY LOGIC POINTS

## How Weight Calculation Works
1. Each entity type has a base weight (fault_code=4.5, equipment=2.8, etc.)
2. Longer/more specific values get bonus (+0.5 to +1.0)
3. Maximum weight is capped at 5.0
4. Higher weight = more important in search results

## How False Positives Are Prevented
1. DIAGNOSTIC_BLACKLIST blocks common words ("run", "set", "oil")
2. Word boundaries (`\b`) prevent substring matches ("vent" in "inventory")
3. Minimum length checks skip very short matches (< 4 chars)
4. Deduplication removes overlapping matches

## How Context-Aware Extraction Works
1. "manual" after a brand = document type (not fault mode)
2. "oil filter" as compound = equipment (not separate words)
3. "box 3d" = location (not random words)

## How Priority/Ordering Works
1. Diagnostic patterns are checked first
2. Core gazetteer (brands, equipment, parts) checked second
3. Context-aware patterns checked third
4. Specialized patterns (fault codes, models, measurements) last
5. Deduplication keeps highest confidence when overlapping

---

# FILE 4: gpt_extractor.py
**Purpose:** Uses GPT AI for entity extraction when needed

---

## Lines 1-17: File Description
```
This file uses OpenAI GPT-4o-mini for entity extraction.
Why use GPT instead of regex patterns?
- "motor running hot" can match "engine overheating" (understands meaning)
- "2nd engineer" = "second engineer" (knows abbreviations)
- New equipment names work automatically (no pattern updates needed)
- ~95% precision vs ~70% with regex alone
```

## Lines 35-77: EXTRACTION PROMPT (Instructions for GPT)
```
This tells GPT how to extract entities:

ENTITY TYPES GPT CAN EXTRACT:
1. equipment: Main Engine, Generator, Bilge Pump, etc.
2. part: Oil Filter, Impeller, Gasket, Seal, etc.
3. symptom: overheating, vibration, leak, noise, etc.
4. fault_code: E047, SPN 123 FMI 4, P0420, etc.
5. person: Captain, Chief Engineer, 2nd Engineer, etc.
6. measurement: 24V, 85°C, 3 bar, 1500 RPM, etc.
7. system: Cooling System, Fuel System, Electrical System, etc.

ACTIONS GPT CAN DETECT:
- create_work_order: "create work order", "raise wo"
- view_history: "show history", "past records"
- diagnose_fault: "diagnose", "troubleshoot"
- find_document: "find manual", "show procedure"

GPT OUTPUT FORMAT:
{
    "entities": [
        {"type": "equipment", "value": "Main Engine", "canonical": "MAIN_ENGINE", "confidence": 0.95}
    ],
    "action": "view_history",
    "action_confidence": 0.92
}
```

## Lines 84-116: Data Classes
```python
@dataclass
class ExtractedEntity:
    type: str           # equipment, part, symptom, etc.
    value: str          # Original text from query
    canonical: str      # Standardized name (MAIN_ENGINE)
    confidence: float   # How sure GPT is (0.0 to 1.0)

@dataclass
class ExtractionResult:
    entities: List[ExtractedEntity]  # All extracted entities
    action: str                       # What user wants to do
    action_confidence: float          # How sure about action
    person_filter: Optional[str]      # Filter by crew member
```

## Lines 123-211: GPTExtractor Class
```python
class GPTExtractor:
    def __init__(self):
        # Get API key from environment
        self.api_key = os.getenv("OPENAI_API_KEY")

        # Model settings
        self.extraction_model = "gpt-4o-mini"      # Fast and cheap
        self.embedding_model = "text-embedding-3-small"  # For similarity search
        self.embedding_dimensions = 1536           # Vector size

    def extract(self, query):
        """Send query to GPT and parse response"""

        # Step 1: Call GPT API
        response = self.client.chat.completions.create(
            model=self.extraction_model,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},  # Instructions
                {"role": "user", "content": query}                 # User's query
            ],
            response_format={"type": "json_object"},  # Force JSON output
            temperature=0.1,   # Low = consistent results
            max_tokens=500,    # Limit response size
        )

        # Step 2: Parse JSON response
        raw = json.loads(response.choices[0].message.content)

        # Step 3: Convert to structured entities
        entities = []
        for e in raw.get("entities", []):
            entities.append(ExtractedEntity(
                type=e.get("type"),
                value=e.get("value"),
                canonical=e.get("canonical"),
                confidence=e.get("confidence", 0.9)
            ))

        return ExtractionResult(
            entities=entities,
            action=raw.get("action", "general_search"),
            action_confidence=raw.get("action_confidence", 0.8),
        )

    def embed(self, text):
        """Convert text to a vector for similarity search"""
        # Returns list of 1536 numbers
        # Same model used at index time and query time for consistency
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text.strip()
        )
        return response.data[0].embedding
```

## Lines 273-329: Fallback When GPT Fails
```python
def _fallback_extraction(self, query):
    """Simple keyword matching when GPT is unavailable"""

    entities = []
    query_lower = query.lower()

    # Simple equipment detection
    equipment_keywords = {
        "engine": "MAIN_ENGINE",
        "generator": "GENERATOR",
        "pump": "PUMP",
    }
    for keyword, canonical in equipment_keywords.items():
        if keyword in query_lower:
            entities.append(ExtractedEntity(
                type="equipment",
                value=keyword,
                canonical=canonical,
                confidence=0.6,  # Lower confidence for fallback
            ))

    # Simple action detection
    action = "general_search"
    if "history" in query_lower:
        action = "view_history"
    elif "create" in query_lower and "work" in query_lower:
        action = "create_work_order"

    return ExtractionResult(entities=entities, action=action, confidence=0.5)
```

---

# FILE 5: gpt_fallback.py
**Purpose:** Uses GPT only when regex patterns aren't enough

---

## Lines 1-20: File Description
```
This file uses GPT as a FALLBACK, not primary extraction.

GPT is only called when:
1. Pattern extraction finds few/no entities
2. High number of unknown terms detected
3. Query seems important but wasn't matched well

The "Cage" constraints:
- GPT can only suggest known entity types
- Outputs must be validated
- Results marked as 'gpt_suggested' for review
- GPT cannot invent new entity types
```

**WHY THIS MATTERS:**
- Saves money (GPT costs per API call)
- Keeps patterns as primary source
- GPT fills gaps without taking over

## Lines 27-36: Configuration
```python
# What entity types GPT can suggest (the "cage")
ALLOWED_ENTITY_TYPES = {
    'brand', 'model', 'equipment', 'part', 'symptom',
    'fault_code', 'measurement', 'action', 'system', 'location'
}

# When to call GPT
MIN_ENTITIES_THRESHOLD = 1   # If patterns find <= 1 entity, call GPT
MAX_UNKNOWN_RATIO = 0.5      # If >50% of words are unknown, call GPT
MIN_QUERY_LENGTH = 20        # Don't call GPT for short queries
```

## Lines 50-80: Decision Logic
```python
def should_invoke_gpt(entities, unknowns, query):
    """Decide if we should call GPT"""

    # Too short - not worth the cost
    if len(query) < 20:
        return False, "query_too_short"

    # Already have good coverage from patterns
    if len(entities) > 1:
        return False, "sufficient_coverage"

    # Few entities extracted - GPT might help
    if len(entities) <= 1:
        return True, "few_entities_extracted"

    # Many unknown words - GPT might recognize them
    unknown_ratio = len(unknowns) / len(query.split())
    if unknown_ratio > 0.5:
        return True, "high_unknown_ratio"

    return False, "sufficient_coverage"
```

## Lines 83-115: GPT Prompt with Constraints
```python
def build_gpt_prompt(query, known_entities):
    """Create a prompt that constrains GPT output"""

    prompt = f'''Extract maritime entities from this query.

Query: "{query}"

Already extracted (DO NOT duplicate):
{json.dumps(known_entities)}

RULES:
1. Only use these entity types: brand, model, equipment, part, symptom...
2. Only extract entities NOT already found
3. Be conservative - only clear, specific entities
4. Only include brands you recognize as maritime manufacturers

Output format:
[
  {{"type": "brand", "value": "exact text", "canonical": "NORMALIZED"}}
]
'''
    return prompt
```

## Lines 118-170: Validate GPT Response
```python
def validate_gpt_response(response):
    """Check GPT output is valid and safe"""

    try:
        entities = json.loads(response)

        validated = []
        for e in entities:
            etype = e.get('type', '').lower()

            # ENFORCE THE CAGE - only allowed types
            if etype not in ALLOWED_ENTITY_TYPES:
                continue  # Ignore invalid types

            if not e.get('value') or len(e.get('value', '')) < 2:
                continue  # Ignore empty values

            validated.append({
                'type': etype,
                'value': e['value'],
                'canonical': e.get('canonical'),
                'confidence': 0.70,      # Lower confidence for GPT
                'source': 'gpt_fallback', # Mark the source
                'needs_review': True,     # Flag for human review
            })

        return validated, None

    except json.JSONDecodeError:
        return [], "json_parse_error"
```

---

# FILE 6: module_a_action_detector.py
**Purpose:** Detects what ACTION the user wants (create, view, update, etc.)

---

## Lines 1-14: File Description
```
STRICT RULES:
- Only verb-based patterns (create, show, update)
- NO phrases that could match equipment names
- NO patterns that could false positive on maritime terms
- Maritime nouns CANNOT trigger actions
- Fault codes NEVER trigger actions

This detects WHAT THE USER WANTS TO DO, not what they're talking about.
```

## Lines 21-35: ActionDetection Class
```python
@dataclass
class ActionDetection:
    action: str           # What action? e.g., "create_work_order"
    confidence: float     # How sure? 0.0 to 1.0
    matched_text: str     # What text matched? e.g., "create work order"
    verb: str             # Which verb triggered it? e.g., "create"
```

## Lines 38-182: StrictMicroActionDetector Class
```python
class StrictMicroActionDetector:
    def __init__(self):
        # Define patterns for each action
        # Format: action_name -> [(regex_pattern, confidence, verb), ...]

        self.action_patterns = {
            # WORK ORDER ACTIONS
            "create_work_order": [
                # ^create = MUST start with "create"
                # \s+ = one or more spaces
                # (a\s+)? = optional "a "
                # (new\s+)? = optional "new "
                # work\s*order = "work order" or "workorder"
                (r"^create\s+(a\s+)?(new\s+)?work\s*order", 0.95, "create"),
                (r"^open\s+(a\s+)?(new\s+)?work\s*order", 0.95, "open"),
                (r"^raise\s+(a\s+)?work\s*order", 0.92, "raise"),
            ],

            "list_work_orders": [
                (r"^show\s+(all\s+)?(open\s+)?work\s*orders", 0.93, "show"),
                (r"^list\s+(all\s+)?work\s*orders", 0.93, "list"),
            ],

            # HISTORY/DATA ACTIONS
            "view_history": [
                (r"^show\s+(me\s+)?(the\s+)?(history|historical)", 0.93, "show"),
                (r"^view\s+(the\s+)?history", 0.92, "view"),
            ],

            # HANDOVER ACTIONS
            "add_to_handover": [
                (r"^add\s+(this\s+)?to\s+(the\s+)?handover", 0.95, "add"),
                (r"^put\s+in\s+handover", 0.90, "put"),
            ],

            # FAULT ACTIONS
            "diagnose_fault": [
                (r"^diagnose\s+(the\s+)?fault", 0.95, "diagnose"),
                (r"^diagnose\s+[EePp]\d{3,4}", 0.93, "diagnose"),  # diagnose E047
                (r"^troubleshoot", 0.93, "troubleshoot"),
            ],

            # INVENTORY ACTIONS
            "check_stock": [
                (r"^check\s+stock", 0.95, "check"),
                (r"^check\s+inventory", 0.93, "check"),
            ],

            "order_parts": [
                (r"^order\s+parts?", 0.95, "order"),
                (r"^request\s+spares?", 0.93, "request"),
            ],

            # HOURS OF REST
            "log_hours_of_rest": [
                (r"^log\s+(my\s+)?hours\s+of\s+rest", 0.95, "log"),
                (r"^record\s+(my\s+)?hours\s+of\s+rest", 0.93, "record"),
            ],
        }
```

**KEY DESIGN DECISION:**
All patterns start with `^` meaning they must be at the START of the query.
This prevents "bilge pump" from matching "pump" pattern.

## Lines 184-219: detect_actions Method
```python
def detect_actions(self, query):
    """Find all action matches in query"""

    query = query.strip().lower()
    detections = []

    for action_name, patterns in self.compiled_patterns.items():
        for pattern, base_confidence, verb in patterns:
            match = pattern.search(query)
            if match:
                confidence = base_confidence

                # BOOST: If match is at start of query
                if match.start() == 0:
                    confidence = min(confidence * 1.05, 1.0)

                # BOOST: Longer matches are more specific
                if len(match.group(0)) > 20:
                    confidence = min(confidence * 1.03, 1.0)

                detections.append(ActionDetection(
                    action=action_name,
                    confidence=confidence,
                    matched_text=match.group(0),
                    verb=verb
                ))

    return detections
```

## Lines 221-240: get_best_action Method
```python
def get_best_action(self, query, min_confidence=0.4):
    """Get single best action above threshold"""

    detections = self.detect_actions(query)

    if not detections:
        return None

    # Sort by confidence, highest first
    detections.sort(key=lambda x: x.confidence, reverse=True)
    best = detections[0]

    # Check threshold
    if best.confidence < min_confidence:
        return None

    return best
```

---

# FILE 7: module_c_canonicalizer.py
**Purpose:** Standardizes entity names and assigns importance weights

---

## Lines 1-17: File Description
```
Functions:
- Normalize abbreviations (ME1 → MAIN_ENGINE_1)
- Assign entity weights based on importance
- Merge duplicate entities
- Provide canonical mappings

RULES:
- Preserves all entity detections from Module B
- Only normalizes, does not add/remove
- Weights reflect business importance
```

## Lines 24-80: Canonicalizer Class
```python
class Canonicalizer:
    def __init__(self):
        # Abbreviation mappings
        self.abbreviation_map = {
            # Equipment abbreviations
            "ME": "MAIN_ENGINE",
            "ME1": "MAIN_ENGINE_1",
            "ME2": "MAIN_ENGINE_2",
            "AE": "AUXILIARY_ENGINE",
            "GEN": "GENERATOR",
            "GEN1": "GENERATOR_1",
            "SWP": "SEA_WATER_PUMP",
            "FWP": "FRESH_WATER_PUMP",
            "HX": "HEAT_EXCHANGER",

            # Voltage normalization
            "24V": "24_VDC",
            "110V": "110_VAC",
            "220V": "220_VAC",

            # Common abbreviations
            "TEMP": "TEMPERATURE",
            "PRES": "PRESSURE",
            "RPM": "REVOLUTIONS_PER_MINUTE",
        }

        # Entity type weights (business importance)
        self.entity_weights = {
            "fault_code": 1.0,      # Highest priority
            "equipment": 0.95,      # Critical
            "system": 0.90,         # Important
            "measurement": 0.85,    # Context
            "part": 0.80,           # Specific
            "maritime_term": 0.75,  # Descriptive
        }

        # Category weights for search ranking
        self.category_weights = {
            "main_engine": 1.0,      # Most important equipment
            "generator": 0.95,       # Very important
            "pump": 0.90,            # Important
            "failure": 0.95,         # Critical symptom
            "alarm": 0.93,           # Important symptom
            "leak": 0.90,            # Important symptom
        }
```

## Lines 81-111: canonicalize Method
```python
def canonicalize(self, entities):
    """Normalize entity values and adjust weights"""

    canonical_entities = []

    for entity in entities:
        canonical = entity.canonical

        # Apply abbreviation mapping if exists
        # ME1 → MAIN_ENGINE_1
        if canonical in self.abbreviation_map:
            canonical = self.abbreviation_map[canonical]

        # Adjust confidence based on entity type
        # fault_code (1.0) keeps full confidence
        # maritime_term (0.75) gets reduced
        type_weight = self.entity_weights.get(entity.type, 0.70)
        adjusted_confidence = entity.confidence * type_weight

        # Create new entity with updated values
        canonical_entity = replace(
            entity,
            canonical=canonical,
            confidence=adjusted_confidence
        )

        canonical_entities.append(canonical_entity)

    return canonical_entities
```

## Lines 130-150: merge_duplicates Method
```python
def merge_duplicates(self, entities):
    """Merge entities with same type and canonical, keep highest confidence"""

    entity_map = {}

    for entity in entities:
        key = f"{entity.type}:{entity.canonical}"  # e.g., "equipment:MAIN_ENGINE"

        if key not in entity_map:
            entity_map[key] = entity
        else:
            # Keep the one with higher confidence
            if entity.confidence > entity_map[key].confidence:
                entity_map[key] = entity

    return list(entity_map.values())
```

---

# FILE 8: extraction_config.py
**Purpose:** Central configuration for extraction thresholds and settings

---

## Lines 12-100: ExtractionConfig Class
```python
class ExtractionConfig:
    def __init__(self):
        # SOURCE RELIABILITY MULTIPLIERS
        # How much to trust each extraction source
        self.source_multipliers = {
            'regex': 1.0,        # Pattern matching = full trust
            'gazetteer': 0.95,   # Term lookup = very high trust
            'proper_noun': 0.85, # Capitalized words = high trust
            'spacy': 0.80,       # NLP library = moderate trust
            'ai': 0.70,          # GPT fallback = lower trust
            'fallback_py': 0.90  # Python fallback = high trust
        }

        # MINIMUM CONFIDENCE BY ENTITY TYPE
        # Entity must meet this threshold to be kept
        self.confidence_thresholds = {
            'equipment': 0.70,     # 70% minimum
            'measurement': 0.75,   # 75% minimum
            'fault_code': 0.70,    # 70% minimum
            'model': 0.75,         # 75% minimum
            'org': 0.75,           # 75% for organizations
            'org_ai': 0.85,        # 85% for AI-detected orgs (stricter)
            'symptom': 0.80,       # 80% minimum
            'date': 0.90,          # 90% for dates (high precision needed)
            'time': 0.90,          # 90% for times
        }

        # ENTITY TYPE PRIORITY (for overlap resolution)
        # Higher number = higher priority = kept when overlapping
        self.type_precedence = {
            'fault_code': 100,     # Fault codes win over everything
            'model': 90,           # Model numbers are very specific
            'part_number': 85,     # Part numbers are specific
            'equipment': 80,       # Equipment is important
            'org': 70,             # Organizations
            'measurement': 60,     # Measurements
            'location': 50,        # Locations
            'action': 40,          # Actions
            'other': 10            # Everything else
        }

        # BRAND EXPANSIONS
        # Alternative names for the same brand
        self.brand_expansions = {
            'caterpillar': ['cat', 'cat marine'],
            'cummins': ['qsm', 'cummins marine'],
            'volvo penta': ['volvo', 'vp'],
            'mtu': ['mtu friedrichshafen'],
            'yanmar': ['yanmar marine'],
        }
```

## Lines 113-152: Calculation Methods
```python
def get_threshold(self, entity_type, source=None):
    """Get minimum confidence for entity type"""
    # Special case: ORG detected by AI needs higher confidence
    if entity_type == 'org' and source == 'ai':
        return 0.85
    return self.confidence_thresholds.get(entity_type, 0.75)

def get_source_multiplier(self, source):
    """Get reliability multiplier for extraction source"""
    return self.source_multipliers.get(source, 0.75)

def get_type_precedence(self, entity_type):
    """Get priority score for overlap resolution"""
    return self.type_precedence.get(entity_type, 10)

def calculate_overlap_score(self, entity):
    """Score for deciding which overlapping entity to keep"""
    # Formula:
    # Score = 0.5 * confidence + 0.3 * span_length + 0.2 * type_priority

    adjusted_conf = entity.confidence
    span_length = entity.span[1] - entity.span[0]
    span_norm = min(span_length / 100, 1.0)  # Normalize to 0-1
    type_priority = self.get_type_precedence(entity.type) / 100.0

    score = (0.5 * adjusted_conf) + (0.3 * span_norm) + (0.2 * type_priority)
    return score
```

---

# FILE 9: microaction_config.py
**Purpose:** Configuration for action detection (work orders, handover, etc.)

---

## Lines 20-96: ExtractionConfig Class
```python
@dataclass
class ExtractionConfig:
    # SOURCE RELIABILITY
    source_multipliers = {
        'regex': 1.0,       # Pattern matching = full trust
        'gazetteer': 0.95,  # Term lookup = very high trust
        'ai': 0.70          # GPT fallback = lower trust
    }

    # MINIMUM CONFIDENCE TO ACCEPT
    min_confidence_by_source = {
        'regex': 0.60,      # Accept regex at 60%+
        'gazetteer': 0.70,  # Accept gazetteer at 70%+
        'ai': 0.75          # Accept AI at 75%+ (stricter)
    }

    # WHEN TO CALL GPT
    ai_fallback_threshold = 0.80  # If best match < 80%, try GPT

    # MINIMUM CONFIDENCE TO RETURN TO USER
    min_output_confidence = 0.65

    # CATEGORY WEIGHTS (how important each category is)
    category_weights = {
        'work_orders': 4.5,     # Most common action type
        'handover': 4.2,        # Very common
        'faults': 4.0,          # Common
        'inventory': 3.5,       # Moderately common
        'documents': 3.0,       # Moderately common
        'purchasing': 2.8,      # Less common
        'hours_of_rest': 2.5,   # Less common
        'mobile': 2.0,          # Least common
        'unsupported': 0.0      # Not actionable
    }

    # CATEGORY PRIORITY ORDER
    # When multiple match, use this order to pick winner
    category_priority = [
        'work_orders',      # Highest priority
        'handover',
        'faults',
        'inventory',
        'purchasing',
        'documents',
        'hours_of_rest',
        'mobile'           # Lowest priority
    ]

    # OVERLAP RESOLUTION WEIGHTS
    overlap_resolution_weights = {
        'confidence': 0.5,      # 50% weight
        'span_length': 0.3,     # 30% weight (longer = more specific)
        'category_priority': 0.2  # 20% weight
    }

    # MULTI-ACTION DETECTION
    min_action_distance = 3  # Minimum chars between actions
    conjunction_indicators = ['and', 'then', 'also', '+', ',']
    max_actions_per_query = 5  # Maximum actions to extract

    # PERFORMANCE
    ai_extraction_timeout_ms = 2000  # 2 second timeout
    max_query_length = 500           # Truncate longer queries
```

## Lines 220-247: Preset Configurations
```python
# PRODUCTION: Balanced speed and accuracy
class ProductionConfig(ExtractionConfig):
    ai_fallback_threshold = 0.75
    min_output_confidence = 0.70
    enable_debug_logging = False

# DEVELOPMENT: Full logging
class DevelopmentConfig(ExtractionConfig):
    enable_debug_logging = True
    log_all_matches = True

# PERFORMANCE: Minimize AI calls
class PerformanceConfig(ExtractionConfig):
    ai_fallback_threshold = 0.50   # Rarely call AI
    ai_extraction_timeout_ms = 1000  # Strict 1 second timeout

# ACCURACY: More AI usage
class AccuracyConfig(ExtractionConfig):
    ai_fallback_threshold = 0.85  # Call AI more often
    min_output_confidence = 0.75  # Higher bar
```

## Lines 279-351: Validation Rules
```python
class ValidationRules:
    # CONTEXT REQUIRED
    # Some actions need specific entities to make sense
    CONTEXT_REQUIRED_ACTIONS = {
        'create_work_order': ['part', 'equipment', 'issue'],
        'report_fault': ['fault_code', 'equipment', 'symptom'],
        'create_purchase_request': ['item', 'quantity'],
    }

    # MUTUALLY EXCLUSIVE
    # These actions can't both be in same query
    MUTUALLY_EXCLUSIVE_ACTIONS = [
        ('create_work_order', 'close_work_order'),   # Can't create AND close
        ('approve_purchase_order', 'reject_purchase_order'),  # Can't approve AND reject
    ]

    # COMMON PAIRS
    # Actions that often appear together
    COMMON_PAIRS = [
        ('create_work_order', 'add_to_handover'),    # Common workflow
        ('report_fault', 'create_work_order'),       # Common workflow
        ('check_stock', 'create_purchase_request'),  # If low, order more
    ]

    @staticmethod
    def validate_action_combination(actions):
        """Check if detected actions make sense together"""
        warnings = []

        # Check for mutually exclusive
        for action_a, action_b in MUTUALLY_EXCLUSIVE_ACTIONS:
            if action_a in actions and action_b in actions:
                warnings.append(
                    f"'{action_a}' and '{action_b}' are mutually exclusive."
                )

        # Too many actions
        if len(actions) > 3:
            warnings.append(
                f"Detected {len(actions)} actions. Consider separate queries."
            )

        return {'valid': len(warnings) == 0, 'warnings': warnings}
```

---

# SUMMARY: KEY LOGIC FLOWS

## 1. Entity Extraction Flow
```
User Query: "MTU 16V4000 engine overheating"
     ↓
module_b_entity_extractor.py
     ↓
1. Check DIAGNOSTIC_BLACKLIST (skip "set", "run", etc.)
2. Match diagnostic patterns (symptoms, faults)
3. Match core gazetteer (brands, equipment, parts)
4. Match context-aware patterns ("manual" after brand = document)
5. Match specialized patterns (fault codes, models, measurements)
6. Deduplicate (keep highest confidence)
     ↓
Output: [
    {type: "brand", value: "MTU", weight: 3.5},
    {type: "model", value: "16V4000", weight: 4.0},
    {type: "equipment", value: "engine", weight: 2.8},
    {type: "symptom", value: "overheating", weight: 4.0}
]
```

## 2. Action Detection Flow
```
User Query: "create work order for bilge pump"
     ↓
module_a_action_detector.py
     ↓
1. Convert to lowercase
2. Check each action pattern
3. Pattern "^create\s+(a\s+)?work\s*order" matches at start
4. Calculate confidence (0.95 base + boosts)
5. Return best action
     ↓
Output: {action: "create_work_order", confidence: 0.98, verb: "create"}
```

## 3. Weight Calculation Flow
```
Entity: {type: "brand", value: "MTU"}
     ↓
1. Base weight from type_weights: brand = 3.5
2. Check value length: "MTU" is 3 chars (no bonus)
3. Cap at 5.0 maximum
     ↓
Output: weight = 3.5, canonical_weight = 2.8 (80% of 3.5)
```

## 4. GPT Fallback Flow
```
User Query: "Naiad stabilizer making weird sounds"
     ↓
1. Pattern extraction finds 0 entities
2. should_invoke_gpt() returns True (few entities)
3. Build constrained GPT prompt
4. Call GPT API
5. Validate response (enforce allowed types)
6. Mark as 'gpt_fallback' source, needs_review=True
     ↓
Output: [{type: "brand", value: "Naiad", source: "gpt_fallback"}]
```

---

# POTENTIAL GAPS TO REVIEW

## 1. Weight Consistency
- Different files calculate weights differently
- module_b uses type_weights dict
- module_c uses entity_weights dict
- extraction_config uses type_precedence
- **Question:** Are all these consistent?

## 2. Fallback Logic
- GPT fallback only triggers if < 1 entity found
- What if patterns find 1 wrong entity?
- **Question:** Should we also trigger on low confidence?

## 3. Context-Aware Extraction
- "manual" after brand = document
- But what about "manual mode" (a fault)?
- **Question:** Is the context detection robust enough?

## 4. Blacklist Coverage
- DIAGNOSTIC_BLACKLIST has ~100 terms
- New terms could still cause false positives
- **Question:** Is there a process to add new terms?

## 5. Duplicate Detection
- Deduplication only checks exact span overlap
- What about partial overlaps?
- "oil filter" vs "oil" - are both kept?

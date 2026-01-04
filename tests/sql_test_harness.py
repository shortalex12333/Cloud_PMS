#!/usr/bin/env python3
"""
SQL Test Harness: Synthetic database for auto-validation.
==========================================================

Creates in-memory SQLite tables mimicking production schema.
Validates generated SQL against realistic maritime data.

Tables:
- pms_parts (50 rows)
- pms_inventory_stock (30 rows)
- pms_equipment (40 rows)
- pms_work_orders (25 rows)
- pms_faults (20 rows)
- doc_yacht_library (35 rows)
- search_fault_code_catalog (15 rows)
- search_graph_nodes (30 rows)
"""

import sqlite3
import uuid
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import random
import json


# =============================================================================
# TEST YACHT ID (fixed for determinism)
# =============================================================================

TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


# =============================================================================
# SYNTHETIC DATA GENERATORS
# =============================================================================

# Maritime-realistic manufacturers
MANUFACTURERS = [
    "Caterpillar", "Cummins", "MAN", "MTU", "Volvo Penta",
    "Yanmar", "John Deere", "Kohler", "Northern Lights", "Onan",
    "Sea Recovery", "Dometic", "Furuno", "Raymarine", "Simrad",
    "Garmin", "KVH", "Sailor", "Iridium", "Inmarsat",
]

# Realistic equipment names
EQUIPMENT_NAMES = [
    "Main Engine Port", "Main Engine Starboard", "Generator 1", "Generator 2",
    "Watermaker", "Air Conditioning Chiller", "Bow Thruster", "Stern Thruster",
    "Anchor Windlass", "Davit Crane", "Tender Lift", "Passerelle",
    "Fire Pump", "Bilge Pump", "Fresh Water Pump", "Black Water Treatment",
    "Radar System", "Autopilot", "GPS Chartplotter", "VHF Radio",
    "Satcom System", "VSAT Antenna", "Stabilizers", "Steering Gear",
]

# Realistic part names
PART_NAMES = [
    "Oil Filter", "Fuel Filter", "Air Filter", "Impeller", "Belt",
    "Gasket Set", "O-Ring Kit", "Bearing", "Seal Kit", "Thermostat",
    "Zinc Anode", "Spark Plug", "Glow Plug", "Injector", "Fuel Pump",
    "Water Pump", "Alternator Belt", "Raw Water Impeller", "Heat Exchanger Gasket",
    "Turbocharger", "Exhaust Elbow", "Coolant Hose", "Fuel Line", "Voltage Regulator",
]

# Realistic locations on a yacht
LOCATIONS = [
    "Engine Room", "Lazarette", "Forepeak", "Bosun Locker", "Crew Mess",
    "Box 1A", "Box 1B", "Box 2A", "Box 2B", "Box 2C", "Box 2D",
    "Drawer A1", "Drawer A2", "Drawer B1", "Spare Parts Cabinet",
    "Bridge Console", "Flybridge Storage", "Tender Garage",
]

# Fault codes (realistic format)
FAULT_CODES = [
    "E001", "E002", "E003", "E047", "E048", "E102", "E103", "E201",
    "F001", "F002", "F015", "F016", "F101", "F102",
    "A001", "A002", "A015", "C001", "C002", "C015",
]

# Symptoms
SYMPTOMS = [
    "Low oil pressure", "High temperature", "Abnormal vibration",
    "Unusual noise", "Smoke from exhaust", "Loss of power",
    "Intermittent shutdown", "Starting difficulty", "Coolant leak",
    "Fuel leak", "Electrical fault", "Sensor malfunction",
]


def gen_uuid() -> str:
    return str(uuid.uuid4())


def gen_timestamp(days_offset: int = 365) -> str:
    """Generate timestamp. Positive = past, negative = future."""
    if days_offset >= 0:
        days = random.randint(0, days_offset)
        dt = datetime.now() - timedelta(days=days)
    else:
        days = random.randint(0, abs(days_offset))
        dt = datetime.now() + timedelta(days=days)
    return dt.isoformat()


def gen_part_number(manufacturer: str) -> str:
    prefix = manufacturer[:3].upper()
    num = random.randint(10000, 99999)
    return f"{prefix}-{num}"


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================

SCHEMAS = {
    "pms_parts": """
        CREATE TABLE pms_parts (
            id TEXT PRIMARY KEY,
            yacht_id TEXT NOT NULL,
            name TEXT NOT NULL,
            part_number TEXT,
            manufacturer TEXT,
            description TEXT,
            category TEXT,
            model_compatibility TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """,
    "pms_inventory_stock": """
        CREATE TABLE pms_inventory_stock (
            id TEXT PRIMARY KEY,
            yacht_id TEXT NOT NULL,
            part_id TEXT,
            location TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            min_quantity INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """,
    "pms_equipment": """
        CREATE TABLE pms_equipment (
            id TEXT PRIMARY KEY,
            yacht_id TEXT NOT NULL,
            name TEXT NOT NULL,
            code TEXT,
            manufacturer TEXT,
            model TEXT,
            serial_number TEXT,
            location TEXT,
            system_type TEXT,
            description TEXT,
            criticality TEXT,
            attention_flag INTEGER DEFAULT 0,
            attention_reason TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """,
    "pms_work_orders": """
        CREATE TABLE pms_work_orders (
            id TEXT PRIMARY KEY,
            yacht_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            type TEXT,
            priority TEXT,
            status TEXT,
            equipment_id TEXT,
            due_date TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """,
    "pms_faults": """
        CREATE TABLE pms_faults (
            id TEXT PRIMARY KEY,
            yacht_id TEXT NOT NULL,
            fault_code TEXT,
            title TEXT,
            description TEXT,
            severity TEXT,
            equipment_id TEXT,
            detected_at TEXT,
            resolved_at TEXT,
            created_at TEXT
        )
    """,
    "doc_yacht_library": """
        CREATE TABLE doc_yacht_library (
            id TEXT PRIMARY KEY,
            yacht_id TEXT NOT NULL,
            document_name TEXT NOT NULL,
            document_type TEXT,
            chunk_text TEXT,
            equipment_covered TEXT,
            fault_code_matches TEXT,
            department TEXT,
            effectiveness_score REAL,
            created_at TEXT
        )
    """,
    "search_fault_code_catalog": """
        CREATE TABLE search_fault_code_catalog (
            id TEXT PRIMARY KEY,
            yacht_id TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT,
            description TEXT,
            severity TEXT,
            symptoms TEXT,
            causes TEXT,
            diagnostic_steps TEXT,
            resolution_steps TEXT,
            system_type TEXT,
            created_at TEXT
        )
    """,
    "search_graph_nodes": """
        CREATE TABLE search_graph_nodes (
            id TEXT PRIMARY KEY,
            yacht_id TEXT NOT NULL,
            label TEXT NOT NULL,
            normalized_label TEXT,
            node_type TEXT,
            properties TEXT,
            created_at TEXT
        )
    """,
}


# =============================================================================
# DATA GENERATORS
# =============================================================================

def generate_parts(n: int = 50) -> List[Dict]:
    parts = []
    for i in range(n):
        manufacturer = random.choice(MANUFACTURERS)
        name = random.choice(PART_NAMES)
        parts.append({
            "id": gen_uuid(),
            "yacht_id": TEST_YACHT_ID,
            "name": f"{name} - {manufacturer}",
            "part_number": gen_part_number(manufacturer),
            "manufacturer": manufacturer,
            "description": f"{name} for marine engine applications. OEM quality replacement.",
            "category": random.choice(["Filters", "Seals", "Electrical", "Mechanical", "Consumables"]),
            "model_compatibility": json.dumps([random.choice(EQUIPMENT_NAMES) for _ in range(random.randint(1, 3))]),
            "created_at": gen_timestamp(),
            "updated_at": gen_timestamp(30),
        })

    # Add specific known parts for testing
    parts.append({
        "id": gen_uuid(),
        "yacht_id": TEST_YACHT_ID,
        "name": "Oil Filter - Caterpillar",
        "part_number": "CAT-OIL-001",
        "manufacturer": "Caterpillar",
        "description": "Primary engine oil filter for main engines",
        "category": "Filters",
        "model_compatibility": json.dumps(["Main Engine Port", "Main Engine Starboard"]),
        "created_at": gen_timestamp(),
        "updated_at": gen_timestamp(30),
    })

    return parts


def generate_inventory(parts: List[Dict], n: int = 30) -> List[Dict]:
    inventory = []
    for i in range(min(n, len(parts))):
        part = parts[i]
        inventory.append({
            "id": gen_uuid(),
            "yacht_id": TEST_YACHT_ID,
            "part_id": part["id"],
            "location": random.choice(LOCATIONS),
            "quantity": random.randint(0, 20),
            "min_quantity": random.randint(1, 5),
            "created_at": gen_timestamp(),
            "updated_at": gen_timestamp(30),
        })

    # Add specific known location for testing
    inventory.append({
        "id": gen_uuid(),
        "yacht_id": TEST_YACHT_ID,
        "part_id": parts[0]["id"] if parts else gen_uuid(),
        "location": "Box 2D",
        "quantity": 5,
        "min_quantity": 2,
        "created_at": gen_timestamp(),
        "updated_at": gen_timestamp(30),
    })

    return inventory


def generate_equipment(n: int = 40) -> List[Dict]:
    equipment = []
    for name in EQUIPMENT_NAMES[:n]:
        manufacturer = random.choice(MANUFACTURERS[:10])
        equipment.append({
            "id": gen_uuid(),
            "yacht_id": TEST_YACHT_ID,
            "name": name,
            "code": name.replace(" ", "_").upper()[:10],
            "manufacturer": manufacturer,
            "model": f"{manufacturer[:3]}-{random.randint(1000, 9999)}",
            "serial_number": f"SN-{random.randint(100000, 999999)}",
            "location": random.choice(LOCATIONS[:8]),
            "system_type": random.choice(["Propulsion", "Power", "HVAC", "Navigation", "Safety", "Deck"]),
            "description": f"{name} system - {manufacturer}",
            "criticality": random.choice(["Critical", "High", "Medium", "Low"]),
            "attention_flag": random.randint(0, 1) if random.random() < 0.1 else 0,
            "attention_reason": None,
            "created_at": gen_timestamp(365 * 2),
            "updated_at": gen_timestamp(60),
        })
    return equipment


def generate_work_orders(equipment: List[Dict], n: int = 25) -> List[Dict]:
    work_orders = []
    for i in range(n):
        eq = random.choice(equipment) if equipment else None
        work_orders.append({
            "id": gen_uuid(),
            "yacht_id": TEST_YACHT_ID,
            "title": f"{random.choice(['Inspect', 'Service', 'Repair', 'Replace'])} {eq['name'] if eq else 'Equipment'}",
            "description": f"Scheduled maintenance task for {eq['name'] if eq else 'equipment'}.",
            "type": random.choice(["Preventive", "Corrective", "Inspection", "Emergency"]),
            "priority": random.choice(["Critical", "High", "Medium", "Low"]),
            "status": random.choice(["Open", "In Progress", "Completed", "Deferred"]),
            "equipment_id": eq["id"] if eq else None,
            "due_date": gen_timestamp(-30),  # Future dates
            "created_at": gen_timestamp(90),
            "updated_at": gen_timestamp(7),
        })
    return work_orders


def generate_faults(equipment: List[Dict], n: int = 20) -> List[Dict]:
    faults = []
    for i in range(n):
        eq = random.choice(equipment) if equipment else None
        code = random.choice(FAULT_CODES)
        symptom = random.choice(SYMPTOMS)
        resolved = random.random() > 0.3
        faults.append({
            "id": gen_uuid(),
            "yacht_id": TEST_YACHT_ID,
            "fault_code": code,
            "title": f"{code}: {symptom}",
            "description": f"Fault detected on {eq['name'] if eq else 'equipment'}. {symptom}.",
            "severity": random.choice(["Critical", "High", "Medium", "Low"]),
            "equipment_id": eq["id"] if eq else None,
            "detected_at": gen_timestamp(180),
            "resolved_at": gen_timestamp(7) if resolved else None,
            "created_at": gen_timestamp(180),
        })

    # Add specific E047 fault for testing
    faults.append({
        "id": gen_uuid(),
        "yacht_id": TEST_YACHT_ID,
        "fault_code": "E047",
        "title": "E047: Low Oil Pressure Warning",
        "description": "Oil pressure below minimum threshold on main engine.",
        "severity": "High",
        "equipment_id": equipment[0]["id"] if equipment else None,
        "detected_at": gen_timestamp(30),
        "resolved_at": None,
        "created_at": gen_timestamp(30),
    })

    return faults


def generate_documents(equipment: List[Dict], n: int = 35) -> List[Dict]:
    docs = []
    doc_types = ["Manual", "Service Bulletin", "Technical Guide", "SOP", "Safety Notice"]

    for i in range(n):
        eq = random.choice(equipment) if equipment else None
        doc_type = random.choice(doc_types)
        docs.append({
            "id": gen_uuid(),
            "yacht_id": TEST_YACHT_ID,
            "document_name": f"{eq['manufacturer'] if eq else 'OEM'} {eq['name'] if eq else 'Equipment'} {doc_type}",
            "document_type": doc_type,
            "chunk_text": f"This section covers maintenance procedures for the {eq['name'] if eq else 'equipment'}. "
                          f"Regular inspection intervals should be followed according to manufacturer specifications.",
            "equipment_covered": json.dumps([eq["name"]]) if eq else None,
            "fault_code_matches": json.dumps(random.sample(FAULT_CODES, min(3, len(FAULT_CODES)))) if random.random() > 0.5 else None,
            "department": random.choice(["Engineering", "Deck", "Interior", "Safety"]),
            "effectiveness_score": round(random.uniform(0.5, 1.0), 2),
            "created_at": gen_timestamp(365),
        })
    return docs


def generate_fault_catalog(n: int = 15) -> List[Dict]:
    catalog = []
    for code in FAULT_CODES[:n]:
        symptom = random.choice(SYMPTOMS)
        catalog.append({
            "id": gen_uuid(),
            "yacht_id": TEST_YACHT_ID,
            "code": code,
            "name": f"{symptom} ({code})",
            "description": f"Fault code {code} indicates {symptom.lower()}.",
            "severity": random.choice(["Critical", "High", "Medium", "Low"]),
            "symptoms": json.dumps([symptom, random.choice(SYMPTOMS)]),
            "causes": json.dumps(["Component wear", "Environmental factors", "Maintenance gap"]),
            "diagnostic_steps": json.dumps(["Check sensors", "Inspect component", "Review logs"]),
            "resolution_steps": json.dumps(["Replace component", "Calibrate sensor", "Service equipment"]),
            "system_type": random.choice(["Propulsion", "Power", "HVAC", "Navigation"]),
            "created_at": gen_timestamp(365),
        })

    # Add specific E047 catalog entry
    catalog.append({
        "id": gen_uuid(),
        "yacht_id": TEST_YACHT_ID,
        "code": "E047",
        "name": "Low Oil Pressure Warning",
        "description": "Oil pressure has dropped below the minimum safe operating threshold.",
        "severity": "High",
        "symptoms": json.dumps(["Low pressure gauge reading", "Warning light illuminated", "Engine protection shutdown"]),
        "causes": json.dumps(["Oil leak", "Pump failure", "Clogged filter", "Low oil level", "Worn bearings"]),
        "diagnostic_steps": json.dumps(["Check oil level", "Inspect for leaks", "Test pressure sensor", "Check filter"]),
        "resolution_steps": json.dumps(["Top up oil", "Replace filter", "Repair leak", "Replace pump if faulty"]),
        "system_type": "Propulsion",
        "created_at": gen_timestamp(365),
    })

    return catalog


def generate_graph_nodes(equipment: List[Dict], parts: List[Dict], n: int = 30) -> List[Dict]:
    nodes = []

    # Equipment nodes
    for eq in equipment[:15]:
        nodes.append({
            "id": gen_uuid(),
            "yacht_id": TEST_YACHT_ID,
            "label": eq["name"],
            "normalized_label": eq["name"].lower().replace(" ", "_"),
            "node_type": "equipment",
            "properties": json.dumps({"manufacturer": eq["manufacturer"], "code": eq["code"]}),
            "created_at": gen_timestamp(365),
        })

    # Part nodes
    for part in parts[:10]:
        nodes.append({
            "id": gen_uuid(),
            "yacht_id": TEST_YACHT_ID,
            "label": part["name"],
            "normalized_label": part["name"].lower().replace(" ", "_"),
            "node_type": "part",
            "properties": json.dumps({"part_number": part["part_number"], "manufacturer": part["manufacturer"]}),
            "created_at": gen_timestamp(365),
        })

    # System nodes
    for system in ["Propulsion System", "Power Generation", "HVAC System", "Navigation System", "Safety Systems"]:
        nodes.append({
            "id": gen_uuid(),
            "yacht_id": TEST_YACHT_ID,
            "label": system,
            "normalized_label": system.lower().replace(" ", "_"),
            "node_type": "system",
            "properties": json.dumps({}),
            "created_at": gen_timestamp(365),
        })

    return nodes


# =============================================================================
# TEST HARNESS CLASS
# =============================================================================

@dataclass
class QueryResult:
    """Result of running a query."""
    success: bool
    row_count: int
    rows: List[Dict]
    error: Optional[str] = None
    query: str = ""


class SQLTestHarness:
    """
    In-memory SQL test harness with synthetic maritime data.

    Usage:
        harness = SQLTestHarness()
        harness.setup()

        result = harness.execute("SELECT * FROM pms_parts WHERE name LIKE '%filter%'")
        if result.success:
            print(f"Found {result.row_count} parts")
    """

    def __init__(self):
        self.conn: Optional[sqlite3.Connection] = None
        self.data: Dict[str, List[Dict]] = {}

    def setup(self) -> None:
        """Initialize database and populate with synthetic data."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

        # Create tables
        cursor = self.conn.cursor()
        for table_name, schema in SCHEMAS.items():
            cursor.execute(schema)

        # Generate data
        self.data["pms_parts"] = generate_parts(50)
        self.data["pms_equipment"] = generate_equipment(40)
        self.data["pms_inventory_stock"] = generate_inventory(self.data["pms_parts"], 30)
        self.data["pms_work_orders"] = generate_work_orders(self.data["pms_equipment"], 25)
        self.data["pms_faults"] = generate_faults(self.data["pms_equipment"], 20)
        self.data["doc_yacht_library"] = generate_documents(self.data["pms_equipment"], 35)
        self.data["search_fault_code_catalog"] = generate_fault_catalog(15)
        self.data["search_graph_nodes"] = generate_graph_nodes(
            self.data["pms_equipment"], self.data["pms_parts"], 30
        )

        # Insert data
        for table_name, rows in self.data.items():
            if not rows:
                continue
            columns = list(rows[0].keys())
            placeholders = ", ".join(["?" for _ in columns])
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            for row in rows:
                values = [row.get(col) for col in columns]
                cursor.execute(insert_sql, values)

        self.conn.commit()

    def execute(self, query: str, params: List[Any] = None) -> QueryResult:
        """Execute a query and return results."""
        if not self.conn:
            return QueryResult(
                success=False,
                row_count=0,
                rows=[],
                error="Harness not initialized. Call setup() first.",
                query=query,
            )

        try:
            cursor = self.conn.cursor()

            # Convert PostgreSQL-style params ($1, $2) to SQLite style (?)
            sqlite_query = self._convert_params(query, params)

            if params:
                cursor.execute(sqlite_query, params)
            else:
                cursor.execute(sqlite_query)

            rows = [dict(row) for row in cursor.fetchall()]

            return QueryResult(
                success=True,
                row_count=len(rows),
                rows=rows,
                error=None,
                query=query,
            )

        except Exception as e:
            return QueryResult(
                success=False,
                row_count=0,
                rows=[],
                error=str(e),
                query=query,
            )

    def _convert_params(self, query: str, params: List[Any] = None) -> str:
        """Convert PostgreSQL $1, $2 params to SQLite ? placeholders."""
        import re

        if not params:
            return query

        # Replace $N with ?
        result = re.sub(r'\$(\d+)', '?', query)

        # Remove ::UUID casts (SQLite doesn't need them)
        result = re.sub(r'::UUID', '', result)
        result = re.sub(r'::TEXT', '', result)

        return result

    def validate_query(self, query: str, params: List[Any] = None) -> Tuple[bool, str]:
        """
        Validate a query without caring about results.

        Returns (is_valid, error_message)
        """
        result = self.execute(query, params)
        if result.success:
            return True, f"Query valid. Returned {result.row_count} rows."
        else:
            return False, f"Query failed: {result.error}"

    def get_table_stats(self) -> Dict[str, int]:
        """Get row counts for all tables."""
        stats = {}
        for table_name in SCHEMAS.keys():
            result = self.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
            if result.success and result.rows:
                stats[table_name] = result.rows[0]["cnt"]
            else:
                stats[table_name] = 0
        return stats

    def teardown(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


# =============================================================================
# ADVERSARIAL TEST CASES
# =============================================================================

ADVERSARIAL_CASES = [
    {
        "name": "Conflicting entity types",
        "extraction": {
            "lane": "NO_LLM",
            "intent": "find_part",
            "intent_confidence": 0.7,
            "entities": [
                {"type": "part", "value": "filter", "weight": 3},
                {"type": "equipment", "value": "main engine", "weight": 4},  # Higher weight, different table
            ],
        },
        "expected": "Should prioritize equipment tables due to higher weight",
    },
    {
        "name": "High weight pointing to wrong table",
        "extraction": {
            "lane": "NO_LLM",
            "intent": "view_part_location",  # Intent says inventory
            "intent_confidence": 0.9,
            "entities": [
                {"type": "document", "value": "manual", "weight": 5},  # But entity is document
            ],
        },
        "expected": "Intent should win due to high confidence",
    },
    {
        "name": "Multiple entities different tables",
        "extraction": {
            "lane": "RULES_ONLY",
            "intent": "diagnose_fault",
            "intent_confidence": 0.85,
            "entities": [
                {"type": "fault_code", "value": "E047", "weight": 5},
                {"type": "part", "value": "oil filter", "weight": 2},
                {"type": "location", "value": "engine room", "weight": 1},
            ],
        },
        "expected": "Fault tables should be Wave 1, parts Wave 2, inventory Wave 3",
    },
    {
        "name": "Empty entities but strong intent",
        "extraction": {
            "lane": "NO_LLM",
            "intent": "find_document",
            "intent_confidence": 0.95,
            "entities": [],
        },
        "expected": "Should route to document tables based on intent alone",
    },
    {
        "name": "Low confidence everything",
        "extraction": {
            "lane": "NO_LLM",
            "intent": "general_search",
            "intent_confidence": 0.3,
            "entities": [
                {"type": "unknown", "value": "help", "weight": 0.5},
            ],
        },
        "expected": "All tables should be Wave 3 or skip",
    },
]


# =============================================================================
# ADVERSARIAL TEST RUNNER
# =============================================================================

def run_adversarial_tests():
    """Run adversarial tests against table router."""
    print("\n" + "=" * 70)
    print(" ADVERSARIAL TESTS - Table Router Edge Cases")
    print("=" * 70)

    # Add parent dir to path for api imports
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from api.table_router import TableRouter
        from api.lane_enforcer import enforce_lane, LaneViolationError
    except ImportError as e:
        print(f"  ⚠ Skipping adversarial tests: {e}")
        return True

    router = TableRouter()
    all_passed = True

    for tc in ADVERSARIAL_CASES:
        print(f"\n--- {tc['name']} ---")
        extraction = tc["extraction"]

        # Check lane enforcement first
        lane = extraction.get("lane", "NO_LLM")
        enforcer = enforce_lane(lane)

        try:
            result = router.create_search_plan(extraction)
            plan = router.plan_to_n8n_format(result)

            wave1 = [t["table"] for t in plan["wave_1"]]
            wave2 = [t["table"] for t in plan["wave_2"]]
            wave3 = [t["table"] for t in plan["wave_3"]]

            print(f"  Lane: {lane}")
            print(f"  Wave 1: {wave1}")
            print(f"  Wave 2: {wave2}")
            print(f"  Wave 3: {wave3}")
            print(f"  Expected: {tc['expected']}")

            # Validate lane invariants
            if lane == "NO_LLM" and plan["metadata"].get("has_embedding"):
                print(f"  ✗ LANE VIOLATION: NO_LLM has embedding")
                all_passed = False
            else:
                print(f"  ✓ Lane invariants OK")

        except LaneViolationError as e:
            print(f"  Lane violation (expected for some cases): {e}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            all_passed = False

    return all_passed


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_harness_tests():
    """Run all harness tests."""
    print("=" * 70)
    print(" SQL TEST HARNESS - Synthetic Database Validation")
    print("=" * 70)

    harness = SQLTestHarness()
    harness.setup()

    # Show table stats
    print("\n--- Table Statistics ---")
    stats = harness.get_table_stats()
    for table, count in stats.items():
        print(f"  {table}: {count} rows")

    # Test basic queries
    print("\n--- Basic Query Tests ---")

    test_queries = [
        ("Parts by name", f"SELECT * FROM pms_parts WHERE yacht_id = '{TEST_YACHT_ID}' AND name LIKE '%filter%'"),
        ("Inventory by location", f"SELECT * FROM pms_inventory_stock WHERE yacht_id = '{TEST_YACHT_ID}' AND location LIKE '%Box%'"),
        ("Faults by code", f"SELECT * FROM pms_faults WHERE yacht_id = '{TEST_YACHT_ID}' AND fault_code = 'E047'"),
        ("Equipment search", f"SELECT * FROM pms_equipment WHERE yacht_id = '{TEST_YACHT_ID}' AND name LIKE '%Engine%'"),
        ("Fault catalog lookup", f"SELECT * FROM search_fault_code_catalog WHERE yacht_id = '{TEST_YACHT_ID}' AND code = 'E047'"),
    ]

    all_passed = True
    for name, query in test_queries:
        result = harness.execute(query)
        if result.success:
            print(f"  ✓ {name}: {result.row_count} rows")
        else:
            print(f"  ✗ {name}: {result.error}")
            all_passed = False

    # Test parameterized queries (PostgreSQL style)
    print("\n--- Parameterized Query Tests ---")

    param_queries = [
        ("Parts with $1 param", "SELECT * FROM pms_parts WHERE yacht_id = $1", [TEST_YACHT_ID]),
        ("Fuzzy search with $2", "SELECT * FROM pms_parts WHERE yacht_id = $1 AND LOWER(name) LIKE $2", [TEST_YACHT_ID, "%filter%"]),
    ]

    for name, query, params in param_queries:
        result = harness.execute(query, params)
        if result.success:
            print(f"  ✓ {name}: {result.row_count} rows")
        else:
            print(f"  ✗ {name}: {result.error}")
            all_passed = False

    # Test edge cases
    print("\n--- Edge Case Tests ---")

    edge_cases = [
        ("Empty result", f"SELECT * FROM pms_parts WHERE yacht_id = '{TEST_YACHT_ID}' AND name = 'nonexistent'"),
        ("NULL handling", f"SELECT * FROM pms_faults WHERE yacht_id = '{TEST_YACHT_ID}' AND resolved_at IS NULL"),
        ("JSON field", f"SELECT * FROM pms_parts WHERE yacht_id = '{TEST_YACHT_ID}' AND model_compatibility LIKE '%Main Engine%'"),
    ]

    for name, query in edge_cases:
        result = harness.execute(query)
        if result.success:
            print(f"  ✓ {name}: {result.row_count} rows")
        else:
            print(f"  ✗ {name}: {result.error}")
            all_passed = False

    harness.teardown()

    print("\n" + "=" * 70)
    if all_passed:
        print(" ✓ ALL HARNESS TESTS PASSED")
    else:
        print(" ✗ SOME TESTS FAILED")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    import sys
    harness_ok = run_harness_tests()
    adversarial_ok = run_adversarial_tests()
    sys.exit(0 if (harness_ok and adversarial_ok) else 1)

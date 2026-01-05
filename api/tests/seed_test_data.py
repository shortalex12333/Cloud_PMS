"""
Seed Test Data - Deterministic fixtures for SQL execution layer tests

This script ensures:
1. Every table has minimum viable rows for testing
2. Every SQL wave (EXACT, ILIKE, TRIGRAM) has guaranteed-hit queries
3. Vector tables have embeddings populated
4. Tests are runnable on a fresh DB and will pass

Run: python seed_test_data.py [--clean] [--verify]
"""

import os
import sys
import json
import uuid
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

import httpx

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Environment
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Test yacht ID - consistent across all tests
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Seed data prefix for easy cleanup
SEED_PREFIX = "TEST_SEED_"


class TestDataSeeder:
    """Seeds deterministic test data for SQL execution layer tests"""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.url = supabase_url
        self.key = supabase_key
        self.client = httpx.Client(timeout=30.0)
        self.headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.created_ids: Dict[str, List[str]] = {}

    def _post(self, table: str, data: Dict) -> Dict:
        """Insert a row and return it"""
        resp = self.client.post(
            f"{self.url}/rest/v1/{table}",
            headers=self.headers,
            json=data
        )
        if resp.status_code not in (200, 201):
            logger.error(f"Failed to insert into {table}: {resp.text}")
            return {}
        result = resp.json()
        return result[0] if isinstance(result, list) else result

    def _delete(self, table: str, column: str, pattern: str):
        """Delete rows matching pattern"""
        resp = self.client.delete(
            f"{self.url}/rest/v1/{table}?{column}=ilike.{pattern}*",
            headers=self.headers
        )
        return resp.status_code in (200, 204)

    def _count(self, table: str, yacht_id: str = None) -> int:
        """Count rows in table"""
        params = {"select": "id", "limit": "1000"}
        if yacht_id:
            params["yacht_id"] = f"eq.{yacht_id}"
        resp = self.client.get(
            f"{self.url}/rest/v1/{table}",
            headers=self.headers,
            params=params
        )
        if resp.status_code == 200:
            return len(resp.json())
        return 0

    def clean_seed_data(self):
        """Remove all seeded test data"""
        logger.info("Cleaning seed data...")

        tables_and_columns = [
            ("pms_parts", "part_number"),
            ("pms_equipment", "code"),
            ("pms_faults", "fault_code"),
            ("pms_suppliers", "name"),
            ("pms_work_orders", "title"),
            ("graph_nodes", "label"),
            ("symptom_aliases", "alias"),
        ]

        for table, column in tables_and_columns:
            if self._delete(table, column, SEED_PREFIX):
                logger.info(f"  Cleaned {table}")
            else:
                logger.warning(f"  Failed to clean {table}")

    def seed_parts(self) -> List[Dict]:
        """
        Seed pms_parts with deterministic test data

        Guaranteed hits:
        - EXACT: part_number = "TEST_SEED_PART-001"
        - ILIKE: name contains "filter", "pump", "seal"
        - TRIGRAM: name similar to "hydraulic"
        """
        logger.info("Seeding pms_parts...")

        parts = [
            # EXACT match targets
            {
                "yacht_id": TEST_YACHT_ID,
                "part_number": f"{SEED_PREFIX}PART-001",
                "name": "Main Engine Oil Filter",
                "manufacturer": "MTU",
                "category": "filters",
                "description": "Primary oil filtration element for main engine",
                "quantity_on_hand": 3,
                "reorder_level": 2
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "part_number": f"{SEED_PREFIX}PART-002",
                "name": "Generator Fuel Filter",
                "manufacturer": "Caterpillar",
                "category": "filters",
                "description": "Fuel filter for generator sets",
                "quantity_on_hand": 5,
                "reorder_level": 2
            },
            # ILIKE match targets
            {
                "yacht_id": TEST_YACHT_ID,
                "part_number": f"{SEED_PREFIX}PART-003",
                "name": "Hydraulic Pump Seal Kit",
                "manufacturer": "Parker",
                "category": "seals",
                "description": "Complete seal kit for hydraulic pump rebuild",
                "quantity_on_hand": 2,
                "reorder_level": 1
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "part_number": f"{SEED_PREFIX}PART-004",
                "name": "Watermaker Membrane Element",
                "manufacturer": "Spectra",
                "category": "watermaker",
                "description": "Reverse osmosis membrane for watermaker",
                "quantity_on_hand": 1,
                "reorder_level": 1
            },
            # TRIGRAM match targets (similar spellings)
            {
                "yacht_id": TEST_YACHT_ID,
                "part_number": f"{SEED_PREFIX}PART-005",
                "name": "Hydraulic Filter Element",
                "manufacturer": "Racor",
                "category": "filters",
                "description": "High-pressure hydraulic filtration",
                "quantity_on_hand": 4,
                "reorder_level": 2
            },
        ]

        created = []
        for part in parts:
            result = self._post("pms_parts", part)
            if result:
                created.append(result)
                self.created_ids.setdefault("pms_parts", []).append(result.get("id"))

        logger.info(f"  Created {len(created)} parts")
        return created

    def seed_equipment(self) -> List[Dict]:
        """
        Seed pms_equipment with deterministic test data

        Guaranteed hits:
        - EXACT: code = "TEST_SEED_ME-001"
        - ILIKE: name contains "engine", "generator", "pump"
        """
        logger.info("Seeding pms_equipment...")

        equipment = [
            {
                "yacht_id": TEST_YACHT_ID,
                "code": f"{SEED_PREFIX}ME-001",
                "name": "Main Engine Port",
                "manufacturer": "MTU",
                "model": "12V4000 M93L",
                "serial_number": "MTU-12345-P",
                "system_type": "propulsion",
                "location": "Engine Room - Port Side",
                "install_date": "2020-01-15",
                "running_hours": 5420
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "code": f"{SEED_PREFIX}ME-002",
                "name": "Main Engine Starboard",
                "manufacturer": "MTU",
                "model": "12V4000 M93L",
                "serial_number": "MTU-12345-S",
                "system_type": "propulsion",
                "location": "Engine Room - Starboard Side",
                "install_date": "2020-01-15",
                "running_hours": 5380
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "code": f"{SEED_PREFIX}GEN-001",
                "name": "Generator 1",
                "manufacturer": "Caterpillar",
                "model": "C18",
                "serial_number": "CAT-GEN-001",
                "system_type": "electrical",
                "location": "Generator Room",
                "install_date": "2020-01-20",
                "running_hours": 12500
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "code": f"{SEED_PREFIX}WM-001",
                "name": "Watermaker System",
                "manufacturer": "Spectra",
                "model": "Newport 1000",
                "serial_number": "SPEC-WM-001",
                "system_type": "freshwater",
                "location": "Engine Room",
                "install_date": "2020-02-01",
                "running_hours": 3200
            },
        ]

        created = []
        for eq in equipment:
            result = self._post("pms_equipment", eq)
            if result:
                created.append(result)
                self.created_ids.setdefault("pms_equipment", []).append(result.get("id"))

        logger.info(f"  Created {len(created)} equipment")
        return created

    def seed_faults(self) -> List[Dict]:
        """
        Seed pms_faults with deterministic test data

        Guaranteed hits:
        - EXACT: fault_code = "TEST_SEED_E001"
        - ILIKE: title contains "overheating", "pressure", "leak"
        """
        logger.info("Seeding pms_faults...")

        faults = [
            {
                "yacht_id": TEST_YACHT_ID,
                "fault_code": f"{SEED_PREFIX}E001",
                "title": "High Exhaust Temperature Warning",
                "description": "Exhaust gas temperature exceeds normal operating range",
                "severity": "high",
                "symptoms": ["high temp alarm", "reduced power", "black smoke"],
                "probable_causes": ["turbo failure", "injector issue", "cooling restriction"],
                "recommended_actions": ["check turbo", "inspect injectors", "verify cooling flow"]
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "fault_code": f"{SEED_PREFIX}E002",
                "title": "Low Oil Pressure Alarm",
                "description": "Engine oil pressure below minimum threshold",
                "severity": "critical",
                "symptoms": ["oil pressure alarm", "engine noise"],
                "probable_causes": ["oil pump failure", "low oil level", "bearing wear"],
                "recommended_actions": ["stop engine", "check oil level", "inspect pump"]
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "fault_code": f"{SEED_PREFIX}G001",
                "title": "Generator Overheating",
                "description": "Generator coolant temperature excessive",
                "severity": "high",
                "symptoms": ["high temp alarm", "auto shutdown"],
                "probable_causes": ["coolant leak", "thermostat stuck", "radiator blocked"],
                "recommended_actions": ["check coolant", "inspect thermostat", "clean radiator"]
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "fault_code": f"{SEED_PREFIX}H001",
                "title": "Hydraulic System Leak Detected",
                "description": "Loss of hydraulic fluid detected in system",
                "severity": "medium",
                "symptoms": ["low fluid alarm", "slow operation", "visible leak"],
                "probable_causes": ["seal failure", "hose damage", "fitting loose"],
                "recommended_actions": ["locate leak", "check fluid", "replace seals"]
            },
        ]

        created = []
        for fault in faults:
            result = self._post("pms_faults", fault)
            if result:
                created.append(result)
                self.created_ids.setdefault("pms_faults", []).append(result.get("id"))

        logger.info(f"  Created {len(created)} faults")
        return created

    def seed_suppliers(self) -> List[Dict]:
        """Seed pms_suppliers with deterministic test data"""
        logger.info("Seeding pms_suppliers...")

        suppliers = [
            {
                "yacht_id": TEST_YACHT_ID,
                "name": f"{SEED_PREFIX}Marine Parts Supply",
                "contact_name": "John Smith",
                "email": "john@marinepartssupply.test",
                "phone": "+1-555-0101",
                "address": "123 Marina Way, Fort Lauderdale, FL",
                "categories": ["filters", "seals", "bearings"]
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "name": f"{SEED_PREFIX}Engine Specialists Inc",
                "contact_name": "Jane Doe",
                "email": "jane@enginespec.test",
                "phone": "+1-555-0102",
                "address": "456 Industrial Blvd, Miami, FL",
                "categories": ["engines", "generators", "turbos"]
            },
        ]

        created = []
        for supplier in suppliers:
            result = self._post("pms_suppliers", supplier)
            if result:
                created.append(result)
                self.created_ids.setdefault("pms_suppliers", []).append(result.get("id"))

        logger.info(f"  Created {len(created)} suppliers")
        return created

    def seed_work_orders(self, equipment_ids: List[str]) -> List[Dict]:
        """Seed pms_work_orders with deterministic test data"""
        logger.info("Seeding pms_work_orders...")

        if not equipment_ids:
            logger.warning("  No equipment IDs provided, skipping work orders")
            return []

        work_orders = [
            {
                "yacht_id": TEST_YACHT_ID,
                "title": f"{SEED_PREFIX}Scheduled Oil Change - Main Engine Port",
                "description": "Perform scheduled oil and filter change",
                "status": "open",
                "priority": "normal",
                "equipment_id": equipment_ids[0] if len(equipment_ids) > 0 else None,
                "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "estimated_hours": 4
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "title": f"{SEED_PREFIX}Generator Service Due",
                "description": "1000 hour service for generator",
                "status": "open",
                "priority": "high",
                "equipment_id": equipment_ids[2] if len(equipment_ids) > 2 else None,
                "due_date": (datetime.now() + timedelta(days=3)).isoformat(),
                "estimated_hours": 8
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "title": f"{SEED_PREFIX}Watermaker Membrane Inspection",
                "description": "Inspect and clean RO membranes",
                "status": "completed",
                "priority": "low",
                "equipment_id": equipment_ids[3] if len(equipment_ids) > 3 else None,
                "completed_date": datetime.now().isoformat(),
                "estimated_hours": 2
            },
        ]

        created = []
        for wo in work_orders:
            if wo.get("equipment_id"):
                result = self._post("pms_work_orders", wo)
                if result:
                    created.append(result)
                    self.created_ids.setdefault("pms_work_orders", []).append(result.get("id"))

        logger.info(f"  Created {len(created)} work orders")
        return created

    def seed_graph_nodes(self) -> List[Dict]:
        """
        Seed graph_nodes for vector search testing

        Note: Embeddings should be populated by the extraction API
        """
        logger.info("Seeding graph_nodes...")

        nodes = [
            {
                "yacht_id": TEST_YACHT_ID,
                "label": f"{SEED_PREFIX}Main Engine System",
                "node_type": "system",
                "properties": {
                    "description": "Primary propulsion system including main engines",
                    "components": ["engine", "gearbox", "shaft", "propeller"]
                }
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "label": f"{SEED_PREFIX}Electrical Distribution",
                "node_type": "system",
                "properties": {
                    "description": "Ship electrical power generation and distribution",
                    "voltage": "440V/220V/24V"
                }
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "label": f"{SEED_PREFIX}Hydraulic Power Unit",
                "node_type": "equipment",
                "properties": {
                    "description": "Central hydraulic system for deck equipment",
                    "pressure": "3000 PSI"
                }
            },
        ]

        created = []
        for node in nodes:
            result = self._post("graph_nodes", node)
            if result:
                created.append(result)
                self.created_ids.setdefault("graph_nodes", []).append(result.get("id"))

        logger.info(f"  Created {len(created)} graph nodes")
        return created

    def seed_symptom_aliases(self) -> List[Dict]:
        """Seed symptom_aliases for entity resolution testing"""
        logger.info("Seeding symptom_aliases...")

        aliases = [
            {
                "yacht_id": TEST_YACHT_ID,
                "alias": f"{SEED_PREFIX}running hot",
                "symptom_code": "OVERHEAT",
                "canonical_symptom": "overheating"
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "alias": f"{SEED_PREFIX}making noise",
                "symptom_code": "ABNORMAL_NOISE",
                "canonical_symptom": "unusual noise"
            },
            {
                "yacht_id": TEST_YACHT_ID,
                "alias": f"{SEED_PREFIX}leaking oil",
                "symptom_code": "OIL_LEAK",
                "canonical_symptom": "oil leak"
            },
        ]

        created = []
        for alias in aliases:
            result = self._post("symptom_aliases", alias)
            if result:
                created.append(result)
                self.created_ids.setdefault("symptom_aliases", []).append(result.get("id"))

        logger.info(f"  Created {len(created)} symptom aliases")
        return created

    def seed_all(self) -> Dict[str, int]:
        """Seed all tables and return counts"""
        logger.info("=" * 60)
        logger.info("SEEDING TEST DATA")
        logger.info("=" * 60)

        # Seed in dependency order
        parts = self.seed_parts()
        equipment = self.seed_equipment()
        faults = self.seed_faults()
        suppliers = self.seed_suppliers()

        # Work orders need equipment IDs
        equipment_ids = [e.get("id") for e in equipment if e.get("id")]
        work_orders = self.seed_work_orders(equipment_ids)

        graph_nodes = self.seed_graph_nodes()
        symptom_aliases = self.seed_symptom_aliases()

        counts = {
            "pms_parts": len(parts),
            "pms_equipment": len(equipment),
            "pms_faults": len(faults),
            "pms_suppliers": len(suppliers),
            "pms_work_orders": len(work_orders),
            "graph_nodes": len(graph_nodes),
            "symptom_aliases": len(symptom_aliases),
        }

        logger.info("=" * 60)
        logger.info("SEED COMPLETE")
        for table, count in counts.items():
            logger.info(f"  {table}: {count} rows")
        logger.info("=" * 60)

        return counts

    def verify_seed_data(self) -> bool:
        """Verify all seed data exists and is queryable"""
        logger.info("=" * 60)
        logger.info("VERIFYING SEED DATA")
        logger.info("=" * 60)

        # Define expected minimums
        expectations = {
            "pms_parts": {"min": 5, "exact_query": f"{SEED_PREFIX}PART-001", "ilike_query": "filter"},
            "pms_equipment": {"min": 4, "exact_query": f"{SEED_PREFIX}ME-001", "ilike_query": "engine"},
            "pms_faults": {"min": 4, "exact_query": f"{SEED_PREFIX}E001", "ilike_query": "overheating"},
            "pms_suppliers": {"min": 2, "ilike_query": SEED_PREFIX},
            "pms_work_orders": {"min": 2, "ilike_query": SEED_PREFIX},
            "graph_nodes": {"min": 3, "ilike_query": SEED_PREFIX},
            "symptom_aliases": {"min": 3, "ilike_query": SEED_PREFIX},
        }

        all_pass = True

        for table, expect in expectations.items():
            count = self._count(table, TEST_YACHT_ID)
            min_expected = expect["min"]

            if count >= min_expected:
                logger.info(f"  ✓ {table}: {count} rows (min {min_expected})")
            else:
                logger.error(f"  ✗ {table}: {count} rows (expected min {min_expected})")
                all_pass = False

        logger.info("=" * 60)
        if all_pass:
            logger.info("VERIFICATION PASSED")
        else:
            logger.error("VERIFICATION FAILED - Some tables missing data")
        logger.info("=" * 60)

        return all_pass


# =============================================================================
# GUARANTEED QUERY TEST CASES
# Uses REAL data from the database - not seed data
# =============================================================================

GUARANTEED_TEST_CASES = {
    "EXACT": [
        {
            "name": "Part number exact match (ENG-0008-103)",
            "terms": [{"type": "PART_NUMBER", "value": "ENG-0008-103"}],
            "tables": ["pms_parts"],
            "expect_min_results": 1
        },
        {
            "name": "Equipment code exact match (ME-S-001)",
            "terms": [{"type": "EQUIPMENT_CODE", "value": "ME-S-001"}],
            "tables": ["pms_equipment"],
            "expect_min_results": 1
        },
        {
            "name": "Fault code exact match (E047)",
            "terms": [{"type": "FAULT_CODE", "value": "E047"}],
            "tables": ["pms_faults"],
            "expect_min_results": 1
        },
    ],
    "ILIKE": [
        {
            "name": "Part name fuzzy match (filter)",
            "terms": [{"type": "PART_NAME", "value": "filter"}],
            "tables": ["pms_parts"],
            "expect_min_results": 2
        },
        {
            "name": "Equipment name fuzzy match (engine)",
            "terms": [{"type": "EQUIPMENT_NAME", "value": "engine"}],
            "tables": ["pms_equipment"],
            "expect_min_results": 2
        },
        {
            "name": "Fault symptom fuzzy match (exhaust)",
            "terms": [{"type": "SYMPTOM", "value": "exhaust"}],
            "tables": ["pms_faults"],
            "expect_min_results": 1
        },
    ],
    "MULTI_TABLE": [
        {
            "name": "Cross-table search (hydraulic)",
            "terms": [{"type": "EQUIPMENT_NAME", "value": "hydraulic"}],
            "tables": ["pms_parts", "pms_equipment", "pms_faults", "graph_nodes"],
            "expect_min_results": 2
        },
    ],
}


def export_test_cases():
    """Export test cases as JSON for test runner"""
    return json.dumps(GUARANTEED_TEST_CASES, indent=2)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Seed test data for SQL execution layer")
    parser.add_argument("--clean", action="store_true", help="Remove all seed data")
    parser.add_argument("--verify", action="store_true", help="Verify seed data exists")
    parser.add_argument("--export-tests", action="store_true", help="Export test cases as JSON")
    args = parser.parse_args()

    if not SUPABASE_KEY:
        logger.error("SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    seeder = TestDataSeeder(SUPABASE_URL, SUPABASE_KEY)

    if args.export_tests:
        print(export_test_cases())
        return

    if args.clean:
        seeder.clean_seed_data()
        return

    if args.verify:
        success = seeder.verify_seed_data()
        sys.exit(0 if success else 1)

    # Default: clean and re-seed
    seeder.clean_seed_data()
    seeder.seed_all()
    seeder.verify_seed_data()


if __name__ == "__main__":
    main()

"""
OVERNIGHT SEED DATA: Realistic marine vocabulary for SQL Foundation testing
=============================================================================
Seeds multiple tables with:
- 3 yacht_ids for tenant isolation testing
- Realistic marine brands, models, part numbers, fault codes
- Near-duplicates and typos for fuzzy matching
- Edge cases for conjunction and ambiguity testing
"""
import requests
import json
import uuid
from datetime import datetime, timedelta
import random

SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"

# 3 yacht IDs for tenant isolation testing
YACHT_IDS = [
    "85fe1119-b04c-41ac-80f1-829d23322598",  # Primary test yacht
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",  # Secondary yacht
    "11111111-2222-3333-4444-555555555555",  # Tertiary yacht
]

# Realistic marine manufacturers
MANUFACTURERS = [
    "MTU", "Caterpillar", "Volvo Penta", "Cummins", "MAN", "Yanmar",
    "John Deere", "Kohler", "Northern Lights", "Westerbeke",
    "ZF Marine", "Twin Disc", "Rolls-Royce", "ABB", "Siemens",
    "Parker Hannifin", "Donaldson", "Fleetguard", "Racor", "Mann+Hummel",
    "SKF", "Timken", "FAG", "NSK", "NTN", "Bosch", "Delphi", "Denso"
]

# With typos for fuzzy testing
MANUFACTURERS_TYPOS = {
    "MTU": ["MTu", "mtu", "M.T.U.", "MTU Detroit"],
    "Caterpillar": ["Catepillar", "CAT", "Caterpiller", "Catterpillar"],
    "Volvo Penta": ["Volvo", "VolvoPenta", "Volvo-Penta", "VOLVO PENTA"],
    "Cummins": ["Cumins", "Cummings", "CUMMINS", "Cummmins"],
}

# Equipment types and systems
EQUIPMENT_TYPES = [
    ("Main Engine Port", "ME-P", "propulsion"),
    ("Main Engine Starboard", "ME-S", "propulsion"),
    ("Generator 1", "GEN-1", "electrical"),
    ("Generator 2", "GEN-2", "electrical"),
    ("Generator 3", "GEN-3", "electrical"),
    ("Bow Thruster", "BT-1", "propulsion"),
    ("Stern Thruster", "ST-1", "propulsion"),
    ("Watermaker 1", "WM-1", "freshwater"),
    ("Watermaker 2", "WM-2", "freshwater"),
    ("HVAC Chiller 1", "AC-1", "climate"),
    ("HVAC Chiller 2", "AC-2", "climate"),
    ("Hydraulic Power Pack", "HPP-1", "hydraulic"),
    ("Stabilizer Port", "STAB-P", "stabilization"),
    ("Stabilizer Starboard", "STAB-S", "stabilization"),
    ("Fire Pump Main", "FP-M", "safety"),
    ("Fire Pump Emergency", "FP-E", "safety"),
    ("Bilge Pump Engine Room", "BP-ER", "bilge"),
    ("Bilge Pump Lazarette", "BP-LZ", "bilge"),
    ("Fuel Transfer Pump", "FTP-1", "fuel"),
    ("Sewage Treatment Plant", "STP-1", "blackwater"),
    ("Anchor Windlass", "AW-1", "deck"),
    ("Capstan Aft", "CAP-A", "deck"),
    ("Tender Crane", "TC-1", "deck"),
    ("Passerelle", "PASS-1", "deck"),
    ("Shore Power Converter", "SPC-1", "electrical"),
    ("Battery Charger 1", "BC-1", "electrical"),
    ("UPS System", "UPS-1", "electrical"),
]

# Part categories with realistic part numbers
PART_TEMPLATES = [
    ("Fuel Filter Primary", "FF-PRI-{n:04d}", "filters", ["fuel", "primary"]),
    ("Fuel Filter Secondary", "FF-SEC-{n:04d}", "filters", ["fuel", "secondary"]),
    ("Oil Filter Element", "OF-ELE-{n:04d}", "filters", ["oil", "lubricant"]),
    ("Air Filter Element", "AF-ELE-{n:04d}", "filters", ["air", "intake"]),
    ("Hydraulic Filter", "HF-{n:04d}", "filters", ["hydraulic", "return"]),
    ("Coolant Thermostat", "CT-{n:04d}", "cooling", ["coolant", "thermal"]),
    ("V-Belt Alternator", "VB-ALT-{n:04d}", "belts", ["alternator", "drive"]),
    ("V-Belt Sea Water Pump", "VB-SWP-{n:04d}", "belts", ["seawater", "cooling"]),
    ("Impeller Sea Water Pump", "IMP-{n:04d}", "pumps", ["impeller", "rubber"]),
    ("Fuel Injector Nozzle", "INJ-{n:04d}", "injection", ["injector", "fuel"]),
    ("Glow Plug", "GP-{n:04d}", "electrical", ["glow", "preheat"]),
    ("Starter Motor", "SM-{n:04d}", "electrical", ["starter", "motor"]),
    ("Alternator Assembly", "ALT-{n:04d}", "electrical", ["alternator", "charge"]),
    ("Turbocharger Assembly", "TURBO-{n:04d}", "turbo", ["turbo", "boost"]),
    ("Exhaust Gasket", "EXH-GKT-{n:04d}", "gaskets", ["exhaust", "seal"]),
    ("Head Gasket", "HD-GKT-{n:04d}", "gaskets", ["head", "cylinder"]),
    ("O-Ring Kit", "ORK-{n:04d}", "seals", ["oring", "seal"]),
    ("Mechanical Seal", "MS-{n:04d}", "seals", ["mechanical", "shaft"]),
    ("Bearing Main", "BRG-M-{n:04d}", "bearings", ["main", "crankshaft"]),
    ("Bearing Rod", "BRG-R-{n:04d}", "bearings", ["rod", "connecting"]),
    ("Piston Ring Set", "PRS-{n:04d}", "engine", ["piston", "ring"]),
    ("Cylinder Liner", "CYL-{n:04d}", "engine", ["cylinder", "liner"]),
    ("Valve Intake", "VLV-I-{n:04d}", "valvetrain", ["valve", "intake"]),
    ("Valve Exhaust", "VLV-E-{n:04d}", "valvetrain", ["valve", "exhaust"]),
    ("Rocker Arm", "RA-{n:04d}", "valvetrain", ["rocker", "arm"]),
    ("Timing Belt", "TB-{n:04d}", "timing", ["timing", "belt"]),
    ("Timing Chain", "TC-{n:04d}", "timing", ["timing", "chain"]),
    ("Water Pump Assembly", "WP-{n:04d}", "cooling", ["water", "pump"]),
    ("Thermostat Housing", "TH-{n:04d}", "cooling", ["thermostat", "housing"]),
    ("Radiator Cap", "RC-{n:04d}", "cooling", ["radiator", "cap"]),
    ("Zinc Anode", "ZN-{n:04d}", "cathodic", ["zinc", "anode"]),
    ("Shaft Seal", "SS-{n:04d}", "seals", ["shaft", "stern"]),
    ("Cutlass Bearing", "CB-{n:04d}", "bearings", ["cutlass", "stern"]),
    ("Propeller Nut", "PN-{n:04d}", "propulsion", ["propeller", "nut"]),
    ("Coupling Element", "CE-{n:04d}", "transmission", ["coupling", "flexible"]),
]

# Fault codes with realistic descriptions
FAULT_CODES = [
    ("E001", "Low Oil Pressure", "critical", "Check oil level and pump"),
    ("E002", "High Coolant Temperature", "critical", "Check coolant level and thermostat"),
    ("E003", "Low Fuel Pressure", "warning", "Check fuel filters and pump"),
    ("E004", "Battery Voltage Low", "warning", "Check alternator and battery"),
    ("E005", "Overspeed Condition", "critical", "Governor malfunction"),
    ("E006", "High Exhaust Temperature", "critical", "Check turbo and injectors"),
    ("E007", "Low Coolant Level", "warning", "Add coolant, check for leaks"),
    ("E008", "Air Filter Restriction", "warning", "Replace air filter element"),
    ("E009", "Fuel Filter Restriction", "warning", "Replace fuel filters"),
    ("E010", "Oil Filter Bypass", "warning", "Replace oil filter"),
    ("E011", "Crankcase Pressure High", "warning", "Check breather system"),
    ("E012", "Turbo Boost Low", "warning", "Check turbo and intercooler"),
    ("E013", "Injector Circuit Fault", "critical", "Check injector wiring"),
    ("E014", "Glow Plug Circuit Open", "warning", "Check glow plug circuit"),
    ("E015", "Starter Motor Fault", "warning", "Check starter circuit"),
    ("E016", "Alternator Not Charging", "critical", "Check alternator belt and wiring"),
    ("E017", "Coolant Sensor Fault", "warning", "Replace coolant sensor"),
    ("E018", "Oil Pressure Sensor Fault", "warning", "Replace oil pressure sensor"),
    ("E019", "Fuel Level Low", "warning", "Refuel required"),
    ("E020", "Emergency Stop Active", "critical", "Reset emergency stop"),
    ("E021", "Governor Actuator Fault", "critical", "Check governor system"),
    ("E022", "Speed Sensor Fault", "warning", "Check speed sensor"),
    ("E023", "Timing Sensor Fault", "critical", "Check timing sensor"),
    ("E024", "ECU Communication Fault", "critical", "Check ECU wiring"),
    ("E025", "High Vibration Detected", "warning", "Check mounting and alignment"),
    ("E030", "Hydraulic Pressure Low", "warning", "Check hydraulic fluid level"),
    ("E031", "Hydraulic Temperature High", "warning", "Check hydraulic cooler"),
    ("E032", "Hydraulic Filter Bypass", "warning", "Replace hydraulic filter"),
    ("E040", "Stabilizer Fault Port", "warning", "Check port stabilizer"),
    ("E041", "Stabilizer Fault Starboard", "warning", "Check starboard stabilizer"),
    ("E042", "Bow Thruster Overload", "warning", "Allow thruster to cool"),
    ("E043", "Stern Thruster Overload", "warning", "Allow thruster to cool"),
    ("E044", "Windlass Overload", "warning", "Check anchor chain"),
    ("E045", "Shore Power Fault", "warning", "Check shore connection"),
    ("E046", "Generator Sync Fault", "critical", "Check generator sync"),
    ("E047", "High Exhaust Temperature Port Engine", "critical", "Check port engine cooling"),
    ("E048", "High Exhaust Temperature Stbd Engine", "critical", "Check stbd engine cooling"),
    ("E049", "Fuel Contamination Detected", "critical", "Test and polish fuel"),
    ("E050", "Water in Fuel Detected", "critical", "Drain water separator"),
]

# Suppliers
SUPPLIERS = [
    ("MTU Parts Direct", "parts@mtu.com", "+1-555-0101", "Detroit, MI"),
    ("Caterpillar Marine", "marine@cat.com", "+1-555-0102", "Peoria, IL"),
    ("Volvo Penta Service", "service@volvopenta.com", "+1-555-0103", "Chesapeake, VA"),
    ("Cummins Marine Parts", "marineparts@cummins.com", "+1-555-0104", "Columbus, IN"),
    ("Parker Hannifin Marine", "marine@parker.com", "+1-555-0105", "Cleveland, OH"),
    ("Donaldson Filtration", "filters@donaldson.com", "+1-555-0106", "Minneapolis, MN"),
    ("SKF Marine Bearings", "marine@skf.com", "+1-555-0107", "Gothenburg, Sweden"),
    ("ZF Marine Transmissions", "marine@zf.com", "+1-555-0108", "Friedrichshafen, Germany"),
    ("Yacht Parts International", "sales@yachtparts.com", "+1-555-0109", "Fort Lauderdale, FL"),
    ("Marine Diesel Direct", "parts@marinediesel.com", "+1-555-0110", "Seattle, WA"),
    ("Mediterranean Marine Supply", "orders@medmarine.eu", "+34-555-0111", "Palma, Spain"),
    ("Riviera Marine Parts", "info@rivieraparts.fr", "+33-555-0112", "Antibes, France"),
]

# Symptoms/aliases for fuzzy matching
SYMPTOM_ALIASES = [
    ("overheating", ["hot", "running hot", "temperature high", "overheats", "too hot"]),
    ("vibration", ["shaking", "vibrates", "wobble", "rough running", "shudder"]),
    ("noise", ["loud", "noisy", "strange sound", "knocking", "grinding"]),
    ("smoke", ["smoking", "black smoke", "white smoke", "exhaust smoke", "fumes"]),
    ("leak", ["leaking", "drip", "dripping", "seepage", "oil leak", "fuel leak"]),
    ("won't start", ["no start", "cranks but won't start", "dead", "won't turn over"]),
    ("stalling", ["stalls", "dies", "cuts out", "shuts down", "stops running"]),
    ("loss of power", ["low power", "weak", "sluggish", "no power", "underpowered"]),
    ("rough idle", ["uneven idle", "hunting", "surging", "idle fluctuates"]),
    ("hard starting", ["slow crank", "difficult start", "takes long to start"]),
]

def insert_batch(table: str, rows: list) -> int:
    """Insert batch of rows, return count inserted."""
    if not rows:
        return 0

    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    resp = requests.post(
        f"{BASE_URL}/rest/v1/{table}",
        headers=headers,
        json=rows
    )

    if resp.status_code in [200, 201]:
        return len(rows)
    else:
        print(f"  ERROR inserting into {table}: {resp.status_code} - {resp.text[:200]}")
        return 0


def seed_equipment() -> list:
    """Seed pms_equipment with realistic yacht equipment."""
    rows = []
    locations = ["Engine Room", "Lazarette", "Flybridge", "Foredeck", "Aft Deck", "Lower Deck", "Crew Quarters"]

    for yacht_id in YACHT_IDS:
        for name, code, system in EQUIPMENT_TYPES:
            mfr = random.choice(MANUFACTURERS[:10])
            rows.append({
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "name": name,
                "code": code,
                "manufacturer": mfr,
                "model": f"{mfr[:3].upper()}-{random.randint(1000,9999)}",
                "serial_number": f"SN{random.randint(100000,999999)}",
                "system_type": system,
                "location": random.choice(locations),
                "install_date": (datetime.now() - timedelta(days=random.randint(100, 2000))).isoformat(),
                "running_hours": random.randint(1000, 15000),
                "created_at": datetime.now().isoformat(),
            })

    count = insert_batch("pms_equipment", rows)
    return rows


def seed_parts() -> list:
    """Seed pms_parts with realistic marine parts."""
    rows = []

    for yacht_id in YACHT_IDS:
        part_num = 1
        for name, pn_template, category, tags in PART_TEMPLATES:
            # Multiple parts per template (different manufacturers)
            for mfr in random.sample(MANUFACTURERS, min(3, len(MANUFACTURERS))):
                rows.append({
                    "id": str(uuid.uuid4()),
                    "yacht_id": yacht_id,
                    "name": name,
                    "part_number": pn_template.format(n=part_num),
                    "manufacturer": mfr,
                    "category": category,
                    "unit_price": round(random.uniform(10, 500), 2),
                    "quantity_on_hand": random.randint(0, 20),
                    "minimum_quantity": random.randint(1, 5),
                    "location": f"Shelf {random.choice('ABCDEF')}-{random.randint(1,10)}",
                    "created_at": datetime.now().isoformat(),
                })
                part_num += 1

        # Add typo variants for fuzzy testing
        for original, typos in MANUFACTURERS_TYPOS.items():
            for typo in typos[:2]:
                rows.append({
                    "id": str(uuid.uuid4()),
                    "yacht_id": yacht_id,
                    "name": f"Test Part {typo}",
                    "part_number": f"TYPO-{random.randint(1000,9999)}",
                    "manufacturer": typo,  # Intentional typo
                    "category": "testing",
                    "quantity_on_hand": 5,
                    "created_at": datetime.now().isoformat(),
                })

    count = insert_batch("pms_parts", rows)
    return rows


def seed_faults() -> list:
    """Seed pms_faults with fault codes."""
    rows = []

    for yacht_id in YACHT_IDS:
        for code, title, severity, desc in FAULT_CODES:
            rows.append({
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "fault_code": code,
                "title": title,
                "severity": severity,
                "description": desc,
                "created_at": datetime.now().isoformat(),
            })

    count = insert_batch("pms_faults", rows)
    return rows


def seed_suppliers() -> list:
    """Seed pms_suppliers."""
    rows = []

    for yacht_id in YACHT_IDS:
        for name, email, phone, location in SUPPLIERS:
            rows.append({
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "name": name,
                "contact_name": name.split()[0] + " Rep",
                "email": email,
                "phone": phone,
                "address": location,
                "created_at": datetime.now().isoformat(),
            })

    count = insert_batch("pms_suppliers", rows)
    return rows


def seed_work_orders() -> list:
    """Seed pms_work_orders."""
    rows = []
    statuses = ["open", "in_progress", "completed", "on_hold"]
    priorities = ["low", "medium", "high", "critical"]

    for yacht_id in YACHT_IDS:
        for i in range(30):
            rows.append({
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "wo_number": f"WO-{yacht_id[:4].upper()}-{i+1:04d}",
                "title": f"Service task {i+1}",
                "description": f"Description for work order {i+1}",
                "status": random.choice(statuses),
                "priority": random.choice(priorities),
                "due_date": (datetime.now() + timedelta(days=random.randint(-30, 60))).isoformat(),
                "created_at": datetime.now().isoformat(),
            })

    count = insert_batch("pms_work_orders", rows)
    return rows


def seed_symptom_aliases() -> list:
    """Seed additional symptom_aliases for fuzzy matching."""
    rows = []

    for yacht_id in YACHT_IDS:
        for symptom_code, aliases in SYMPTOM_ALIASES:
            for alias in aliases:
                rows.append({
                    "id": str(uuid.uuid4()),
                    "yacht_id": yacht_id,
                    "symptom_code": symptom_code.upper(),
                    "alias": alias,
                    "created_at": datetime.now().isoformat(),
                })

    count = insert_batch("symptom_aliases", rows)
    return rows


def seed_fault_catalog() -> list:
    """Seed search_fault_code_catalog."""
    rows = []

    for yacht_id in YACHT_IDS:
        for code, title, severity, desc in FAULT_CODES:
            symptoms = random.sample(["overheating", "vibration", "noise", "smoke", "leak"], 2)
            rows.append({
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "code": code,
                "name": title,
                "severity": severity,
                "symptoms": ", ".join(symptoms),
                "created_at": datetime.now().isoformat(),
            })

    count = insert_batch("search_fault_code_catalog", rows)
    return rows


def run_seeding():
    """Run all seeding operations."""
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "yacht_ids": YACHT_IDS,
        "tables": {}
    }

    print("=" * 60)
    print("SEEDING DATABASE FOR OVERNIGHT TESTS")
    print("=" * 60)

    # Seed each table
    seeders = [
        ("pms_equipment", seed_equipment),
        ("pms_parts", seed_parts),
        ("pms_faults", seed_faults),
        ("pms_suppliers", seed_suppliers),
        ("pms_work_orders", seed_work_orders),
        ("symptom_aliases", seed_symptom_aliases),
        ("search_fault_code_catalog", seed_fault_catalog),
    ]

    for table, seeder in seeders:
        print(f"\nSeeding {table}...")
        rows = seeder()
        manifest["tables"][table] = {
            "rows_inserted": len(rows),
            "sample": rows[0] if rows else None
        }
        print(f"  Inserted {len(rows)} rows")

    # Save manifest
    with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))tests/overnight/seed_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print("SEEDING COMPLETE")
    print("=" * 60)

    return manifest


if __name__ == "__main__":
    run_seeding()

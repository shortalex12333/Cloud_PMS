"""
Comprehensive table seeder for SQL Foundation testing.
Seeds all tables to 50+ rows for proper test coverage.
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import random

SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1'
YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598'

HEADERS = {
    'apikey': SERVICE_KEY,
    'Authorization': f'Bearer {SERVICE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

# Equipment data generators
EQUIPMENT_TEMPLATES = [
    # Engine Room
    ("Main Engine Port", "ENG-001", "MTU", "16V4000 M93L", "Engine Room Port", "propulsion"),
    ("Main Engine Starboard", "ENG-002", "MTU", "16V4000 M93L", "Engine Room Starboard", "propulsion"),
    ("Generator 1", "GEN-001", "Caterpillar", "C32", "Generator Room", "electrical"),
    ("Generator 2", "GEN-002", "Caterpillar", "C32", "Generator Room", "electrical"),
    ("Generator 3", "GEN-003", "Kohler", "500REOZJ", "Generator Room", "electrical"),
    ("Bow Thruster", "THR-001", "ABT", "TRAC 35", "Bow", "propulsion"),
    ("Stern Thruster", "THR-002", "ABT", "TRAC 30", "Stern", "propulsion"),
    ("Watermaker 1", "WM-001", "Sea Recovery", "Aqua Whisper 1800", "Engine Room", "water"),
    ("Watermaker 2", "WM-002", "Sea Recovery", "Aqua Whisper 1800", "Engine Room", "water"),
    ("Air Conditioning Chiller 1", "HVAC-001", "Marine Air", "MCU-16", "AC Room", "hvac"),
    ("Air Conditioning Chiller 2", "HVAC-002", "Marine Air", "MCU-16", "AC Room", "hvac"),
    ("Fuel Transfer Pump", "FTP-001", "Jabsco", "23610-3003", "Engine Room", "fuel"),
    ("Fuel Polisher", "FPL-001", "Algae-X", "LGX1200", "Engine Room", "fuel"),
    ("Sewage Treatment Plant", "STP-001", "Hamann", "HL-Cont Plus", "Crew Area", "water"),
    ("Hot Water Heater 1", "HWH-001", "Isotemp", "Spa 40", "Engine Room", "water"),
    ("Hydraulic Power Pack", "HYD-001", "Vetus", "HPU", "Lazarette", "hydraulic"),
    ("Shore Power Converter", "SPC-001", "Victron", "Quattro 48/15000", "Engine Room", "electrical"),
    ("Battery Bank 1", "BAT-001", "Mastervolt", "MLI Ultra 24/5000", "Engine Room", "electrical"),
    ("Battery Bank 2", "BAT-002", "Mastervolt", "MLI Ultra 24/5000", "Engine Room", "electrical"),
    ("Anchor Windlass", "WIN-001", "Maxwell", "VWC 5000", "Foredeck", "deck"),
    ("Capstan Port", "CAP-001", "Maxwell", "RC12-24V", "Aft Deck", "deck"),
    ("Capstan Starboard", "CAP-002", "Maxwell", "RC12-24V", "Aft Deck", "deck"),
    ("Stabilizer Port", "STAB-001", "Naiad", "502", "Stabilizer Room", "stabilization"),
    ("Stabilizer Starboard", "STAB-002", "Naiad", "502", "Stabilizer Room", "stabilization"),
    ("Radar 1", "RAD-001", "Furuno", "FAR-2228", "Bridge", "navigation"),
    ("GPS Chartplotter", "GPS-001", "Simrad", "NSO EVO3S", "Bridge", "navigation"),
    ("Autopilot", "AP-001", "Furuno", "NAVpilot 711C", "Bridge", "navigation"),
    ("VHF Radio 1", "VHF-001", "Icom", "M605", "Bridge", "communication"),
    ("Satellite Phone", "SAT-001", "Iridium", "Certus 350", "Bridge", "communication"),
]

SUPPLIER_TEMPLATES = [
    ("MTU America", "John Smith", "jsmith@mtu-online.com", "+1 248 560 8000", "33401 Manufacturing Drive, Clinton Township, MI 48035", True),
    ("Caterpillar Marine", "Sarah Jones", "sarah.jones@cat.com", "+1 309 675 1000", "510 Lake Cook Road, Deerfield, IL 60015", True),
    ("Furuno USA", "Mike Chen", "mchen@furunousa.com", "+1 360 834 9300", "4400 NW Pacific Rim Blvd, Camas, WA 98607", True),
    ("Raymarine", "Emma Wilson", "ewilson@raymarine.com", "+1 603 881 5200", "9 Townsend West, Nashua, NH 03063", True),
    ("Simrad Marine", "David Brown", "dbrown@simrad.com", "+1 480 596 9500", "5720 S 48th St, Phoenix, AZ 85040", True),
    ("Victron Energy", "Anna Berg", "aberg@victronenergy.com", "+31 36 535 9700", "De Paal 35, 1351 JG Almere", True),
    ("Mastervolt", "Peter Van Der Berg", "peter@mastervolt.com", "+31 20 342 2100", "Snijdersbergweg 93, 1105 AN Amsterdam", True),
    ("Maxwell Marine", "Tom Collins", "tcollins@maxwell-marine.com", "+64 9 985 0250", "8 Pacific Rise, Mt Wellington, Auckland 1060", True),
    ("Naiad Dynamics", "Lisa Martinez", "lmartinez@naiad.com", "+1 203 327 7733", "215 Stillwater Ave, Stamford, CT 06902", True),
    ("Sea Recovery", "James Wilson", "jwilson@searecovery.com", "+1 310 637 3400", "23305 La Palma Ave, Yorba Linda, CA 92887", True),
    ("Marine Air Systems", "Robert Taylor", "rtaylor@marineair.com", "+1 954 973 2477", "1721 NW 25th Ave, Pompano Beach, FL 33069", True),
    ("ABT TRAC", "Henrik Larsson", "hlarsson@abt-trac.com", "+46 31 89 54 70", "Järnbrottsvägen 11, 421 32 Västra Frölunda, Sweden", True),
    ("Jabsco Marine", "Chris Anderson", "canderson@jabsco.com", "+1 714 545 8251", "30 Bareno Place, Costa Mesa, CA 92626", True),
    ("VETUS Maxwell", "Jan De Groot", "jdegroot@vetus.com", "+31 78 618 8100", "Fokkerstraat 571-575, 3125 BD Schiedam", True),
    ("Kohler Power", "Mark Johnson", "mjohnson@kohlerpower.com", "+1 920 457 4441", "444 Highland Dr, Kohler, WI 53044", True),
    ("Hamann AG", "Klaus Mueller", "kmueller@hamann.de", "+49 4102 4556 0", "Industriestraße 15, 22946 Trittau, Germany", True),
    ("Algae-X International", "Steven Lee", "slee@algae-x.com", "+1 954 581 6996", "2351 NW 65th Ave, Sunrise, FL 33313", True),
    ("Isotemp Marine", "Paolo Rossi", "prossi@isotemp.it", "+39 0543 797400", "Via Emilia Ponente 1235, 47522 Cesena FC, Italy", True),
    ("Icom America", "Kevin Park", "kpark@icomamerica.com", "+1 425 454 8155", "12421 Willows Rd NE, Kirkland, WA 98034", True),
    ("Iridium Communications", "Nicole Adams", "nadams@iridium.com", "+1 703 287 7400", "1750 Tysons Blvd #1400, McLean, VA 22102", True),
    ("Parker Racor", "Bill Thompson", "bthompson@parker.com", "+1 209 521 7860", "3400 Finch Rd, Modesto, CA 95357", True),
    ("Separ Filter", "Hans Schmidt", "hschmidt@separ.de", "+49 4342 9890", "Kronsheider Strasse 36, 24790 Schacht-Audorf, Germany", True),
    ("ZF Marine", "Frank Schneider", "fschneider@zf.com", "+1 954 581 4040", "3300 Gateway Dr, Pompano Beach, FL 33069", True),
    ("Twin Disc", "Greg Williams", "gwilliams@twindisc.com", "+1 262 638 4000", "1328 Racine St, Racine, WI 53403", True),
    ("Cummins Marine", "Brian Harris", "bharris@cummins.com", "+1 812 377 5000", "500 Jackson St, Columbus, IN 47201", True),
    ("Yanmar Marine", "Kenji Tanaka", "ktanaka@yanmar.com", "+81 6 6376 6211", "1-32 Chayamachi, Kita-ku, Osaka 530-8311, Japan", True),
    ("Volvo Penta", "Erik Lindberg", "elindberg@volvopenta.com", "+46 31 66 00 00", "Sven Källfelts Gata 1, 405 08 Göteborg, Sweden", True),
    ("Northern Lights", "Jack Miller", "jmiller@northernlights.com", "+1 206 789 3880", "4420 14th Ave NW, Seattle, WA 98107", True),
    ("Fischer Panda", "Wolfgang Klein", "wklein@fischerpanda.de", "+49 5254 9202 0", "Otto-Hahn-Straße 34, 33104 Paderborn, Germany", True),
    ("Lewmar", "Andrew Carter", "acarter@lewmar.com", "+44 1onal329 246700", "Southmoor Lane, Havant, Hampshire PO9 1JJ, UK", True),
    ("Besenzoni", "Marco Bianchi", "mbianchi@besenzoni.it", "+39 0444 579711", "Via della Meccanica 13, 36015 Schio VI, Italy", True),
    ("Quick Nautical", "Luca Ferrari", "lferrai@quicknautical.com", "+39 0543 798300", "Via Fosso Ghiaia 178, 48124 Ravenna, Italy", True),
    ("Sperry Marine", "Alan Wright", "awright@sperrymarine.com", "+1 434 974 2000", "1070 Seminole Trail, Charlottesville, VA 22901", True),
    ("JRC Marine", "Hiroshi Yamamoto", "hyamamoto@jrc.com", "+81 3 6269 3500", "5-1-1 Shimorenjaku, Mitaka, Tokyo 181-8510, Japan", True),
    ("B&G Marine", "Sophie Davis", "sdavis@bandg.com", "+1 480 596 9500", "5720 S 48th St, Phoenix, AZ 85040", True),
    ("Garmin Marine", "Michael Brooks", "mbrooks@garmin.com", "+1 913 397 8200", "1200 E 151st St, Olathe, KS 66062", True),
    ("ACR Electronics", "Patricia Moore", "pmoore@acrartex.com", "+1 954 981 3333", "5757 Ravenswood Rd, Fort Lauderdale, FL 33312", True),
    ("Ocean Signal", "Richard Turner", "rturner@oceansignal.com", "+44 1011 251 6000", "Hythe Marina, Southampton SO45 6DX, UK", True),
    ("Sealand Technology", "Amy Nelson", "anelson@sealandtechnology.com", "+1 440 953 8464", "6765 Parkland Blvd, Cleveland, OH 44139", True),
    ("Dometic Marine", "Carl Johansson", "cjohansson@dometic.com", "+46 8 501 025 00", "Hemvärnsgatan 15, 171 54 Solna, Sweden", True),
]

FAULT_CODES = [
    ("E001", "High Temperature Alarm", "Engine coolant temperature exceeded threshold", "critical"),
    ("E002", "Low Oil Pressure", "Engine oil pressure below safe operating level", "critical"),
    ("E003", "Fuel Contamination Detected", "Water or particulate detected in fuel system", "high"),
    ("E004", "Battery Low Voltage", "Battery voltage dropped below minimum threshold", "medium"),
    ("E005", "Generator Overload", "Generator load exceeded rated capacity", "high"),
    ("E006", "Thruster Motor Overheat", "Thruster motor temperature exceeded limit", "high"),
    ("E007", "Hydraulic Pressure Low", "Hydraulic system pressure below operating range", "medium"),
    ("E008", "Steering System Fault", "Steering system detected anomaly", "critical"),
    ("E009", "Navigation Light Failure", "One or more navigation lights not functioning", "medium"),
    ("E010", "Bilge High Level", "Bilge water level exceeded alert threshold", "high"),
    ("E011", "Fire Suppression Fault", "Fire suppression system self-test failed", "critical"),
    ("E012", "AIS Transponder Offline", "AIS system not transmitting", "medium"),
    ("E013", "Radar Signal Lost", "Radar system not receiving echoes", "high"),
    ("E014", "EPIRB Battery Low", "EPIRB beacon battery requires replacement", "medium"),
    ("E015", "Watermaker High Pressure", "RO membrane pressure exceeded limit", "high"),
    ("E016", "Sewage Tank Full", "Sewage holding tank at capacity", "medium"),
    ("E017", "Fresh Water Tank Low", "Fresh water below 20% capacity", "low"),
    ("E018", "Fuel Tank Low", "Fuel level below 25% capacity", "medium"),
    ("E019", "Air Conditioning Fault", "HVAC system compressor fault detected", "low"),
    ("E020", "Windlass Overload", "Anchor windlass motor current exceeded limit", "medium"),
    ("E021", "Stabilizer Fault", "Stabilizer system error detected", "medium"),
    ("E022", "Shore Power Fault", "Shore power connection issue detected", "low"),
    ("E023", "Battery Charger Fault", "Battery charging system malfunction", "medium"),
    ("E024", "Inverter Overload", "Inverter output exceeded rated capacity", "high"),
    ("E025", "Water Heater Fault", "Hot water system thermostat failure", "low"),
    ("E026", "Exhaust Temperature High", "Exhaust gas temperature exceeded limit", "critical"),
    ("E027", "Turbo Boost Low", "Turbocharger boost pressure below normal", "medium"),
    ("E028", "Transmission Fault", "Transmission temperature or pressure anomaly", "high"),
    ("E029", "Propeller Shaft Vibration", "Abnormal vibration detected on prop shaft", "high"),
    ("E030", "Rudder Position Fault", "Rudder position sensor disagreement", "critical"),
    ("E031", "Autopilot Disengaged", "Autopilot automatically disconnected", "high"),
    ("E032", "GPS Signal Lost", "No GPS satellites acquired", "medium"),
    ("E033", "Depth Sounder Fault", "Depth transducer not responding", "medium"),
    ("E034", "Speed Log Fault", "Speed sensor malfunction", "low"),
    ("E035", "Wind Sensor Fault", "Anemometer not responding", "low"),
    ("E036", "Fire Detected", "Fire alarm activated in monitored zone", "critical"),
    ("E037", "Smoke Detected", "Smoke detector activated", "critical"),
    ("E038", "CO Alarm", "Carbon monoxide level exceeded safe limit", "critical"),
    ("E039", "LPG Leak Detected", "Gas detector triggered", "critical"),
    ("E040", "Security Breach", "Unauthorized access detected", "high"),
    ("E041", "Man Overboard Alarm", "MOB button activated", "critical"),
    ("E042", "Engine Room Flood", "Water sensor triggered in engine room", "critical"),
    ("E043", "Lazarette Flood", "Water sensor triggered in lazarette", "high"),
    ("E044", "Bow Compartment Flood", "Water sensor triggered in bow area", "high"),
    ("E045", "Battery Disconnect", "Emergency battery disconnect activated", "high"),
    ("E046", "Emergency Stop Activated", "Engine emergency stop engaged", "critical"),
    ("E047", "Main Bus Undervoltage", "Main DC bus voltage critically low", "critical"),
    ("E048", "Genset Start Failure", "Generator failed to start after 3 attempts", "high"),
    ("E049", "Oil Change Due", "Scheduled oil change interval reached", "low"),
    ("E050", "Filter Change Due", "Scheduled filter replacement required", "low"),
]

SYMPTOM_TEMPLATES = [
    # Equipment symptoms
    ("engine won't start", "ENGINE_START_FAIL", "colloquial"),
    ("engine no start", "ENGINE_START_FAIL", "colloquial"),
    ("motor not turning over", "ENGINE_START_FAIL", "colloquial"),
    ("generator not running", "GEN_FAULT", "colloquial"),
    ("genset won't fire up", "GEN_FAULT", "colloquial"),
    ("no power from gen", "GEN_FAULT", "colloquial"),
    ("AC not cooling", "HVAC_FAULT", "colloquial"),
    ("air con broken", "HVAC_FAULT", "colloquial"),
    ("cabin too hot", "HVAC_FAULT", "colloquial"),
    ("watermaker not working", "WM_FAULT", "colloquial"),
    ("desal offline", "WM_FAULT", "colloquial"),
    ("no fresh water", "WM_FAULT", "colloquial"),
    ("thruster not responding", "THRUSTER_FAULT", "colloquial"),
    ("bow thruster dead", "THRUSTER_FAULT", "colloquial"),
    ("can't dock properly", "THRUSTER_FAULT", "colloquial"),
    ("anchor won't drop", "WINDLASS_FAULT", "colloquial"),
    ("windlass stuck", "WINDLASS_FAULT", "colloquial"),
    ("chain jammed", "WINDLASS_FAULT", "colloquial"),
    ("stabilizers not working", "STAB_FAULT", "colloquial"),
    ("boat rolling too much", "STAB_FAULT", "colloquial"),
    ("excessive motion", "STAB_FAULT", "colloquial"),
]

# Work order templates - use valid enum values: type=scheduled, priority=routine
WORK_ORDER_TEMPLATES = [
    ("Engine Oil Change - Port", "scheduled", "routine", "Scheduled oil and filter change for port main engine"),
    ("Engine Oil Change - Starboard", "scheduled", "routine", "Scheduled oil and filter change for starboard main engine"),
    ("Generator 1 Service", "scheduled", "routine", "500 hour service on generator 1"),
    ("Generator 2 Service", "scheduled", "routine", "500 hour service on generator 2"),
    ("Fuel Filter Replacement", "scheduled", "routine", "Replace primary and secondary fuel filters"),
    ("Air Filter Inspection", "scheduled", "routine", "Inspect and clean air filter elements"),
    ("Coolant Level Check", "scheduled", "routine", "Check and top up coolant levels all engines"),
    ("Belt Inspection", "scheduled", "routine", "Inspect drive belts for wear and tension"),
    ("Impeller Replacement", "scheduled", "routine", "Replace raw water pump impellers"),
    ("Zincs Replacement", "scheduled", "routine", "Replace sacrificial anodes on hull and running gear"),
    ("Bottom Inspection", "scheduled", "routine", "Diver inspection of underwater hull"),
    ("Propeller Inspection", "scheduled", "routine", "Check props for damage and fouling"),
    ("Shaft Seal Check", "scheduled", "routine", "Inspect shaft seals for leaks"),
    ("Rudder Bearing Check", "scheduled", "routine", "Check rudder bearings for play"),
    ("Thruster Motor Service", "scheduled", "routine", "Service bow and stern thrusters"),
    ("Hydraulic Fluid Change", "scheduled", "routine", "Replace hydraulic fluid and filters"),
    ("Steering System Check", "scheduled", "routine", "Full steering system inspection"),
    ("Autopilot Calibration", "scheduled", "routine", "Recalibrate autopilot heading sensor"),
    ("Radar Maintenance", "scheduled", "routine", "Clean scanner and check connections"),
    ("VHF Radio Test", "scheduled", "routine", "Test VHF radios and DSC functionality"),
    ("EPIRB Battery Replace", "scheduled", "routine", "Replace EPIRB beacon battery"),
    ("Liferaft Service Due", "scheduled", "routine", "Annual liferaft service required"),
    ("Fire Extinguisher Check", "scheduled", "routine", "Inspect and service fire extinguishers"),
    ("Smoke Detector Test", "scheduled", "routine", "Test all smoke and CO detectors"),
    ("Bilge Pump Test", "scheduled", "routine", "Test all bilge pumps and alarms"),
    ("Emergency Lighting Test", "scheduled", "routine", "Verify emergency lighting function"),
    ("Navigation Light Check", "scheduled", "routine", "Test all navigation lights"),
    ("Anchor Chain Inspection", "scheduled", "routine", "Check chain for wear and corrosion"),
    ("Tender Engine Service", "scheduled", "routine", "Outboard engine scheduled service"),
    ("Crane Hydraulics Service", "scheduled", "routine", "Service crane hydraulic system"),
    ("Gangway Inspection", "scheduled", "routine", "Inspect gangway mechanism and cables"),
    ("Stabilizer Service", "scheduled", "routine", "Annual stabilizer fin service"),
    ("Watermaker Membrane", "scheduled", "routine", "Replace RO membranes"),
    ("A/C Compressor Service", "scheduled", "routine", "Service HVAC compressors"),
    ("Refrigeration Check", "scheduled", "routine", "Check refrigerant levels all systems"),
    ("Hot Water System Service", "scheduled", "routine", "Service water heaters and mixing valves"),
    ("Sewage System Service", "scheduled", "routine", "Service MSD and holding tanks"),
    ("Fuel Polishing", "scheduled", "routine", "Run fuel polishing system"),
    ("Battery Capacity Test", "scheduled", "routine", "Load test house batteries"),
    ("Shore Power Service", "scheduled", "routine", "Service shore power connections"),
    ("Solar Panel Clean", "scheduled", "routine", "Clean and inspect solar panels"),
    ("Teak Deck Maintenance", "scheduled", "routine", "Teak deck clean and oil"),
    ("Window Seal Check", "scheduled", "routine", "Check window seals for leaks"),
    ("Hatch Seal Replace", "scheduled", "routine", "Replace worn hatch gaskets"),
    ("Mooring Line Inspection", "scheduled", "routine", "Check all mooring lines for wear"),
    ("Fender Cover Replace", "scheduled", "routine", "Replace worn fender covers"),
    ("Davit Service", "scheduled", "routine", "Service davit motor and cables"),
    ("Passerelle Service", "scheduled", "routine", "Service passerelle hydraulics"),
    ("Dinghy Outboard Service", "scheduled", "routine", "100 hour service tender outboard"),
    ("Safety Equipment Check", "scheduled", "routine", "Inventory and inspect all safety gear"),
]


def get_current_count(table):
    """Get current row count for yacht."""
    resp = requests.get(
        f'{BASE_URL}/{table}?yacht_id=eq.{YACHT_ID}&select=id',
        headers={k: v for k, v in HEADERS.items() if k != 'Prefer'}
    )
    return len(resp.json()) if resp.status_code == 200 else 0


def get_equipment_ids():
    """Get existing equipment IDs for FK references."""
    resp = requests.get(
        f'{BASE_URL}/pms_equipment?yacht_id=eq.{YACHT_ID}&select=id',
        headers={k: v for k, v in HEADERS.items() if k != 'Prefer'}
    )
    if resp.status_code == 200:
        return [row['id'] for row in resp.json()]
    return []


def seed_equipment(target=50):
    """Seed pms_equipment table."""
    current = get_current_count('pms_equipment')
    needed = max(0, target - current)

    if needed == 0:
        print(f"  pms_equipment: {current} ✓ (already >= {target})")
        return

    rows = []
    for i, template in enumerate(EQUIPMENT_TEMPLATES[:needed]):
        name, code, mfr, model, location, sys_type = template
        rows.append({
            "yacht_id": YACHT_ID,
            "name": name,
            "code": f"{code}-SEED{i:02d}",
            "manufacturer": mfr,
            "model": model,
            "location": location,
            "system_type": sys_type,
            "serial_number": f"SN{random.randint(100000, 999999)}",
            "criticality": random.choice(["critical", "high", "medium", "low"]),
            "description": f"{name} - {mfr} {model}"
        })

    if rows:
        resp = requests.post(f'{BASE_URL}/pms_equipment', headers=HEADERS, json=rows)
        if resp.status_code in (200, 201):
            print(f"  pms_equipment: Inserted {len(rows)}, now at {current + len(rows)}")
        else:
            print(f"  pms_equipment: FAILED - {resp.status_code} {resp.text[:200]}")


def seed_suppliers(target=50):
    """Seed pms_suppliers table."""
    current = get_current_count('pms_suppliers')
    needed = max(0, target - current)

    if needed == 0:
        print(f"  pms_suppliers: {current} ✓ (already >= {target})")
        return

    rows = []
    for i, template in enumerate(SUPPLIER_TEMPLATES[:needed]):
        name, contact, email, phone, address, preferred = template
        rows.append({
            "yacht_id": YACHT_ID,
            "name": name,
            "contact_name": contact,
            "email": email,
            "phone": phone,
            "address": address,
            "preferred": preferred
        })

    if rows:
        resp = requests.post(f'{BASE_URL}/pms_suppliers', headers=HEADERS, json=rows)
        if resp.status_code in (200, 201):
            print(f"  pms_suppliers: Inserted {len(rows)}, now at {current + len(rows)}")
        else:
            print(f"  pms_suppliers: FAILED - {resp.status_code} {resp.text[:200]}")


def seed_faults(target=50):
    """Seed pms_faults table."""
    current = get_current_count('pms_faults')
    needed = max(0, target - current)

    if needed == 0:
        print(f"  pms_faults: {current} ✓ (already >= {target})")
        return

    equipment_ids = get_equipment_ids()
    if not equipment_ids:
        print("  pms_faults: SKIPPED - no equipment IDs available")
        return

    rows = []
    for i, template in enumerate(FAULT_CODES[:needed]):
        code, title, desc, severity = template
        rows.append({
            "yacht_id": YACHT_ID,
            "equipment_id": random.choice(equipment_ids),
            "fault_code": code,
            "title": title,
            "description": desc,
            "severity": severity,
            "detected_at": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()
        })

    if rows:
        resp = requests.post(f'{BASE_URL}/pms_faults', headers=HEADERS, json=rows)
        if resp.status_code in (200, 201):
            print(f"  pms_faults: Inserted {len(rows)}, now at {current + len(rows)}")
        else:
            print(f"  pms_faults: FAILED - {resp.status_code} {resp.text[:200]}")


def seed_work_orders(target=50):
    """Seed pms_work_orders table."""
    current = get_current_count('pms_work_orders')
    needed = max(0, target - current)

    if needed == 0:
        print(f"  pms_work_orders: {current} ✓ (already >= {target})")
        return

    equipment_ids = get_equipment_ids()
    if not equipment_ids:
        print("  pms_work_orders: SKIPPED - no equipment IDs available")
        return

    rows = []
    statuses = ["open", "in_progress", "completed", "deferred"]
    priorities = ["critical", "high", "normal", "low"]

    # Use existing user ID for created_by
    SYSTEM_USER_ID = "570b6c2b-0e47-4c95-9840-a41ca7318b2e"

    for i, template in enumerate(WORK_ORDER_TEMPLATES[:needed]):
        title, wo_type, priority, desc = template
        due = (datetime.now() + timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d')
        rows.append({
            "yacht_id": YACHT_ID,
            "equipment_id": random.choice(equipment_ids),
            "title": title,
            "description": desc,
            "type": wo_type,
            "priority": priority,
            "status": random.choice(["planned", "in_progress", "completed"]),
            "due_date": due,
            "due_hours": random.randint(100, 10000),
            "created_by": SYSTEM_USER_ID
        })

    if rows:
        resp = requests.post(f'{BASE_URL}/pms_work_orders', headers=HEADERS, json=rows)
        if resp.status_code in (200, 201):
            print(f"  pms_work_orders: Inserted {len(rows)}, now at {current + len(rows)}")
        else:
            print(f"  pms_work_orders: FAILED - {resp.status_code} {resp.text[:200]}")


def seed_symptom_catalog(target=50):
    """Seed symptom_catalog table (global catalog, no yacht_id)."""
    # Get current count without yacht_id filter
    resp = requests.get(
        f'{BASE_URL}/symptom_catalog?select=code',
        headers={k: v for k, v in HEADERS.items() if k != 'Prefer'}
    )
    current = len(resp.json()) if resp.status_code == 200 else 0
    needed = max(0, target - current)

    if needed == 0:
        print(f"  symptom_catalog: {current} ✓ (already >= {target})")
        return

    # Symptom catalog entries (code, label, desc, system_type, severity 1-5)
    symptom_entries = [
        ("ENGINE_START_FAIL", "Engine Start Failure", "Engine fails to start or turn over", "engine", 5),
        ("GEN_FAULT", "Generator Fault", "Generator not producing power or failing to start", "electrical", 4),
        ("HVAC_FAULT", "HVAC System Fault", "Air conditioning not cooling or heating properly", "hvac", 2),
        ("WM_FAULT", "Watermaker Fault", "Desalination system not producing water", "water", 3),
        ("THRUSTER_FAULT", "Thruster Fault", "Bow or stern thruster not responding", "propulsion", 4),
        ("WINDLASS_FAULT", "Windlass Fault", "Anchor windlass not operating", "deck", 3),
        ("STAB_FAULT", "Stabilizer Fault", "Stabilizer fins not deploying or retracting", "stabilization", 3),
        ("NAV_FAULT", "Navigation Fault", "Navigation equipment malfunction", "navigation", 4),
        ("COMM_FAULT", "Communication Fault", "Radio or satellite communication failure", "communication", 4),
        ("FUEL_FAULT", "Fuel System Fault", "Fuel contamination or supply issue", "fuel", 5),
        ("ELEC_FAULT", "Electrical Fault", "Shore power or battery system issue", "electrical", 4),
        ("STEER_FAULT", "Steering Fault", "Steering system malfunction", "steering", 5),
        ("BILGE_HIGH", "Bilge High Level", "High water level detected in bilge", "safety", 5),
        ("FIRE_DETECT", "Fire Detection", "Smoke or fire detected", "safety", 5),
        ("PROP_FAULT", "Propulsion Fault", "Propeller or shaft issue", "propulsion", 4),
        ("COOLANT_LOW", "Coolant Low", "Engine coolant level below minimum", "engine", 4),
        ("BELT_SLIP", "Belt Slipping", "Drive belt slippage detected", "engine", 3),
        ("TURBO_FAULT", "Turbo Fault", "Turbocharger underperforming", "engine", 4),
        ("EXHAUST_HIGH", "Exhaust High Temp", "Exhaust temperature exceeded limit", "engine", 5),
        ("TRANS_FAULT", "Transmission Fault", "Gearbox temperature or pressure issue", "propulsion", 4),
        ("SHAFT_VIB", "Shaft Vibration", "Abnormal propeller shaft vibration", "propulsion", 4),
        ("RUDDER_FAULT", "Rudder Fault", "Rudder position sensor error", "steering", 5),
        ("AP_FAULT", "Autopilot Fault", "Autopilot system malfunction", "navigation", 4),
        ("GPS_LOST", "GPS Signal Lost", "No GPS satellite signal", "navigation", 3),
        ("RADAR_FAULT", "Radar Fault", "Radar not receiving echoes", "navigation", 4),
        ("VHF_FAULT", "VHF Radio Fault", "VHF radio not transmitting", "communication", 4),
        ("SAT_FAULT", "Satellite Fault", "Satellite communication offline", "communication", 3),
        ("AIS_FAULT", "AIS Transponder Fault", "AIS not transmitting", "navigation", 3),
        ("EPIRB_LOW", "EPIRB Battery Low", "Emergency beacon battery low", "safety", 4),
        ("MOB_ALARM", "Man Overboard Alarm", "MOB button activated", "safety", 5),
        ("FLOOD_ENG", "Engine Room Flood", "Water detected in engine room", "safety", 5),
        ("FLOOD_AFT", "Aft Compartment Flood", "Water detected aft", "safety", 5),
        ("CO_ALARM", "Carbon Monoxide Alarm", "CO levels exceeded safe limit", "safety", 5),
        ("GAS_DETECT", "Gas Detected", "LPG or fuel vapor detected", "safety", 5),
        ("BATT_LOW", "Battery Voltage Low", "House battery voltage critically low", "electrical", 4),
        ("CHARGER_FAULT", "Battery Charger Fault", "Battery not charging", "electrical", 3),
        ("INVERTER_FAULT", "Inverter Fault", "AC inverter overload or failure", "electrical", 3),
        ("SHORE_FAULT", "Shore Power Fault", "Shore power connection issue", "electrical", 2),
        ("TANK_FUEL_LOW", "Fuel Tank Low", "Fuel level below 25%", "fuel", 3),
        ("TANK_WATER_LOW", "Fresh Water Low", "Fresh water below 20%", "water", 2),
        ("TANK_WASTE_FULL", "Waste Tank Full", "Holding tank at capacity", "water", 2),
        ("WM_PRESSURE", "Watermaker High Pressure", "RO membrane pressure high", "water", 4),
        ("AC_COMPRESSOR", "AC Compressor Fault", "Air conditioning compressor failure", "hvac", 2),
        ("FRIDGE_FAULT", "Refrigeration Fault", "Galley refrigeration failure", "hvac", 2),
        ("HEATER_FAULT", "Heater Fault", "Hot water heater malfunction", "hvac", 2),
    ]

    rows = []
    for i, entry in enumerate(symptom_entries[:needed]):
        code, label, desc, sys_type, severity = entry
        rows.append({
            "code": f"{code}_{random.randint(100,999)}",  # Make unique
            "label": label,
            "description": desc,
            "system_type": sys_type,
            "severity": severity
        })

    if rows:
        resp = requests.post(f'{BASE_URL}/symptom_catalog', headers=HEADERS, json=rows)
        if resp.status_code in (200, 201):
            print(f"  symptom_catalog: Inserted {len(rows)}, now at {current + len(rows)}")
        else:
            print(f"  symptom_catalog: FAILED - {resp.status_code} {resp.text[:200]}")


def verify_counts():
    """Verify final counts."""
    tables = ['pms_equipment', 'pms_parts', 'pms_suppliers', 'pms_work_orders',
              'graph_nodes', 'pms_faults']

    print("\n=== VERIFICATION ===")
    all_good = True

    # Tables with yacht_id filter
    for table in tables:
        count = get_current_count(table)
        status = "✓" if count >= 50 else "✗ SPARSE"
        if count < 50:
            all_good = False
        print(f"  {table}: {count} {status}")

    # symptom_catalog (no yacht_id filter)
    resp = requests.get(
        f'{BASE_URL}/symptom_catalog?select=code',
        headers={k: v for k, v in HEADERS.items() if k != 'Prefer'}
    )
    count = len(resp.json()) if resp.status_code == 200 else 0
    status = "✓" if count >= 50 else "✗ SPARSE"
    if count < 50:
        all_good = False
    print(f"  symptom_catalog: {count} {status}")

    return all_good


def main():
    print("=" * 60)
    print("TABLE SEEDING - SQL FOUNDATION")
    print("=" * 60)
    print(f"Target yacht: {YACHT_ID}")
    print(f"Target per table: 50+ rows\n")

    # Seed in order (equipment first for FK references)
    seed_equipment(50)
    seed_suppliers(50)
    seed_faults(50)
    seed_work_orders(50)
    seed_symptom_catalog(50)

    # Verify
    success = verify_counts()

    print("\n" + "=" * 60)
    if success:
        print("SEEDING COMPLETE - All tables at 50+")
    else:
        print("SEEDING INCOMPLETE - Some tables still sparse")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

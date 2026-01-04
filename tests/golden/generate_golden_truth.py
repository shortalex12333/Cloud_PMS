#!/usr/bin/env python3
"""
Generate golden truth by running queries through extraction endpoint.
3 second delay between calls to avoid API rate limiting.
"""
import json
import time
import requests
from datetime import datetime

SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
EXTRACT_URL = "https://extract.core.celeste7.ai/extract"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
DELAY_SECONDS = 3

# 250 test queries across 8 categories
QUERIES = [
    # === RAW vs CANONICAL (30) ===
    {"id": "RAW-001", "cat": "RAW_VS_CANONICAL", "query": "ENG-0008-103"},
    {"id": "RAW-002", "cat": "RAW_VS_CANONICAL", "query": "eng-0008-103"},
    {"id": "RAW-003", "cat": "RAW_VS_CANONICAL", "query": "ENG0008103"},
    {"id": "RAW-004", "cat": "RAW_VS_CANONICAL", "query": "PMP-0018-280"},
    {"id": "RAW-005", "cat": "RAW_VS_CANONICAL", "query": "pmp0018280"},
    {"id": "RAW-006", "cat": "RAW_VS_CANONICAL", "query": "FLT-0033-146"},
    {"id": "RAW-007", "cat": "RAW_VS_CANONICAL", "query": "flt0033146"},
    {"id": "RAW-008", "cat": "RAW_VS_CANONICAL", "query": "ME-P-001"},
    {"id": "RAW-009", "cat": "RAW_VS_CANONICAL", "query": "mep001"},
    {"id": "RAW-010", "cat": "RAW_VS_CANONICAL", "query": "GEN-001"},
    {"id": "RAW-011", "cat": "RAW_VS_CANONICAL", "query": "gen001"},
    {"id": "RAW-012", "cat": "RAW_VS_CANONICAL", "query": "WM-001"},
    {"id": "RAW-013", "cat": "RAW_VS_CANONICAL", "query": "wm001"},
    {"id": "RAW-014", "cat": "RAW_VS_CANONICAL", "query": "MTU-2018-4567-P"},
    {"id": "RAW-015", "cat": "RAW_VS_CANONICAL", "query": "mtu20184567p"},
    {"id": "RAW-016", "cat": "RAW_VS_CANONICAL", "query": "KOH-2018-9901"},
    {"id": "RAW-017", "cat": "RAW_VS_CANONICAL", "query": "PO-2025-001"},
    {"id": "RAW-018", "cat": "RAW_VS_CANONICAL", "query": "po2025001"},
    {"id": "RAW-019", "cat": "RAW_VS_CANONICAL", "query": "PO-2025-002"},
    {"id": "RAW-020", "cat": "RAW_VS_CANONICAL", "query": "NAV-RAD-001"},
    {"id": "RAW-021", "cat": "RAW_VS_CANONICAL", "query": "navrad001"},
    {"id": "RAW-022", "cat": "RAW_VS_CANONICAL", "query": "THR-B-001"},
    {"id": "RAW-023", "cat": "RAW_VS_CANONICAL", "query": "thrb001"},
    {"id": "RAW-024", "cat": "RAW_VS_CANONICAL", "query": "HVAC-001"},
    {"id": "RAW-025", "cat": "RAW_VS_CANONICAL", "query": "hvac001"},
    {"id": "RAW-026", "cat": "RAW_VS_CANONICAL", "query": "ELC-0041-489"},
    {"id": "RAW-027", "cat": "RAW_VS_CANONICAL", "query": "elc0041489"},
    {"id": "RAW-028", "cat": "RAW_VS_CANONICAL", "query": "HYD-0066-515"},
    {"id": "RAW-029", "cat": "RAW_VS_CANONICAL", "query": "DCK-0076-515"},
    {"id": "RAW-030", "cat": "RAW_VS_CANONICAL", "query": "SAF-0092-318"},

    # === COLUMN AMBIGUITY (30) ===
    {"id": "AMB-001", "cat": "COLUMN_AMBIGUITY", "query": "MTU"},
    {"id": "AMB-002", "cat": "COLUMN_AMBIGUITY", "query": "Kohler"},
    {"id": "AMB-003", "cat": "COLUMN_AMBIGUITY", "query": "Generator"},
    {"id": "AMB-004", "cat": "COLUMN_AMBIGUITY", "query": "Engine Room"},
    {"id": "AMB-005", "cat": "COLUMN_AMBIGUITY", "query": "filter"},
    {"id": "AMB-006", "cat": "COLUMN_AMBIGUITY", "query": "pump"},
    {"id": "AMB-007", "cat": "COLUMN_AMBIGUITY", "query": "oil"},
    {"id": "AMB-008", "cat": "COLUMN_AMBIGUITY", "query": "fuel"},
    {"id": "AMB-009", "cat": "COLUMN_AMBIGUITY", "query": "water"},
    {"id": "AMB-010", "cat": "COLUMN_AMBIGUITY", "query": "service"},
    {"id": "AMB-011", "cat": "COLUMN_AMBIGUITY", "query": "annual"},
    {"id": "AMB-012", "cat": "COLUMN_AMBIGUITY", "query": "inspection"},
    {"id": "AMB-013", "cat": "COLUMN_AMBIGUITY", "query": "main engine"},
    {"id": "AMB-014", "cat": "COLUMN_AMBIGUITY", "query": "watermaker"},
    {"id": "AMB-015", "cat": "COLUMN_AMBIGUITY", "query": "thruster"},
    {"id": "AMB-016", "cat": "COLUMN_AMBIGUITY", "query": "radar"},
    {"id": "AMB-017", "cat": "COLUMN_AMBIGUITY", "query": "navigation"},
    {"id": "AMB-018", "cat": "COLUMN_AMBIGUITY", "query": "electrical"},
    {"id": "AMB-019", "cat": "COLUMN_AMBIGUITY", "query": "hydraulic"},
    {"id": "AMB-020", "cat": "COLUMN_AMBIGUITY", "query": "propulsion"},
    {"id": "AMB-021", "cat": "COLUMN_AMBIGUITY", "query": "safety"},
    {"id": "AMB-022", "cat": "COLUMN_AMBIGUITY", "query": "deck"},
    {"id": "AMB-023", "cat": "COLUMN_AMBIGUITY", "query": "bridge"},
    {"id": "AMB-024", "cat": "COLUMN_AMBIGUITY", "query": "Sea Recovery"},
    {"id": "AMB-025", "cat": "COLUMN_AMBIGUITY", "query": "Furuno"},
    {"id": "AMB-026", "cat": "COLUMN_AMBIGUITY", "query": "Simrad"},
    {"id": "AMB-027", "cat": "COLUMN_AMBIGUITY", "query": "Maxwell"},
    {"id": "AMB-028", "cat": "COLUMN_AMBIGUITY", "query": "Grundfos"},
    {"id": "AMB-029", "cat": "COLUMN_AMBIGUITY", "query": "Volvo Penta"},
    {"id": "AMB-030", "cat": "COLUMN_AMBIGUITY", "query": "Caterpillar"},

    # === CONJUNCTION-ONLY ENFORCEMENT (30) ===
    {"id": "CONJ-001", "cat": "CONJUNCTION_ONLY", "query": "manufacturer MTU"},
    {"id": "CONJ-002", "cat": "CONJUNCTION_ONLY", "query": "description fuel injector"},
    {"id": "CONJ-003", "cat": "CONJUNCTION_ONLY", "query": "contact Carlos Mendez"},
    {"id": "CONJ-004", "cat": "CONJUNCTION_ONLY", "query": "model 16V4000"},
    {"id": "CONJ-005", "cat": "CONJUNCTION_ONLY", "query": "frequency 500 hours"},
    {"id": "CONJ-006", "cat": "CONJUNCTION_ONLY", "query": "notes injectors"},
    {"id": "CONJ-007", "cat": "CONJUNCTION_ONLY", "query": "MTU fuel filter"},
    {"id": "CONJ-008", "cat": "CONJUNCTION_ONLY", "query": "Kohler generator parts"},
    {"id": "CONJ-009", "cat": "CONJUNCTION_ONLY", "query": "Volvo Penta gasket"},
    {"id": "CONJ-010", "cat": "CONJUNCTION_ONLY", "query": "engine oil change procedure"},
    {"id": "CONJ-011", "cat": "CONJUNCTION_ONLY", "query": "generator annual service description"},
    {"id": "CONJ-012", "cat": "CONJUNCTION_ONLY", "query": "watermaker membrane replacement"},
    {"id": "CONJ-013", "cat": "CONJUNCTION_ONLY", "query": "main engine port 500hr"},
    {"id": "CONJ-014", "cat": "CONJUNCTION_ONLY", "query": "hydraulic system oil"},
    {"id": "CONJ-015", "cat": "CONJUNCTION_ONLY", "query": "MTU serial number"},
    {"id": "CONJ-016", "cat": "CONJUNCTION_ONLY", "query": "supplier Mediterranean Marine"},
    {"id": "CONJ-017", "cat": "CONJUNCTION_ONLY", "query": "contact Jean-Pierre"},
    {"id": "CONJ-018", "cat": "CONJUNCTION_ONLY", "query": "MTU Americas parts"},
    {"id": "CONJ-019", "cat": "CONJUNCTION_ONLY", "query": "Sea Recovery watermaker"},
    {"id": "CONJ-020", "cat": "CONJUNCTION_ONLY", "query": "Grundfos pump seal"},
    {"id": "CONJ-021", "cat": "CONJUNCTION_ONLY", "query": "Blue Sea Systems wire"},
    {"id": "CONJ-022", "cat": "CONJUNCTION_ONLY", "query": "Raymarine GPS antenna"},
    {"id": "CONJ-023", "cat": "CONJUNCTION_ONLY", "query": "Marine Air compressor"},
    {"id": "CONJ-024", "cat": "CONJUNCTION_ONLY", "query": "Lewmar anchor chain"},
    {"id": "CONJ-025", "cat": "CONJUNCTION_ONLY", "query": "Parker filter micron"},
    {"id": "CONJ-026", "cat": "CONJUNCTION_ONLY", "query": "Racor air filter"},
    {"id": "CONJ-027", "cat": "CONJUNCTION_ONLY", "query": "3M teak cleaner"},
    {"id": "CONJ-028", "cat": "CONJUNCTION_ONLY", "query": "Permatex grease waterproof"},
    {"id": "CONJ-029", "cat": "CONJUNCTION_ONLY", "query": "Survitec fire extinguisher"},
    {"id": "CONJ-030", "cat": "CONJUNCTION_ONLY", "query": "Danfoss hydraulic filter"},

    # === ENTITY TYPE MISLEADS (30) ===
    {"id": "MIS-001", "cat": "ENTITY_MISLEAD", "query": "E047"},
    {"id": "MIS-002", "cat": "ENTITY_MISLEAD", "query": "G012"},
    {"id": "MIS-003", "cat": "ENTITY_MISLEAD", "query": "WM-003"},
    {"id": "MIS-004", "cat": "ENTITY_MISLEAD", "query": "T-001"},
    {"id": "MIS-005", "cat": "ENTITY_MISLEAD", "query": "NAV-R01"},
    {"id": "MIS-006", "cat": "ENTITY_MISLEAD", "query": "HVAC-05"},
    {"id": "MIS-007", "cat": "ENTITY_MISLEAD", "query": "E023"},
    {"id": "MIS-008", "cat": "ENTITY_MISLEAD", "query": "SP-002"},
    {"id": "MIS-009", "cat": "ENTITY_MISLEAD", "query": "1234"},
    {"id": "MIS-010", "cat": "ENTITY_MISLEAD", "query": "high exhaust temperature"},
    {"id": "MIS-011", "cat": "ENTITY_MISLEAD", "query": "low coolant"},
    {"id": "MIS-012", "cat": "ENTITY_MISLEAD", "query": "high pressure warning"},
    {"id": "MIS-013", "cat": "ENTITY_MISLEAD", "query": "hydraulic leak"},
    {"id": "MIS-014", "cat": "ENTITY_MISLEAD", "query": "bearing drift"},
    {"id": "MIS-015", "cat": "ENTITY_MISLEAD", "query": "short cycling"},
    {"id": "MIS-016", "cat": "ENTITY_MISLEAD", "query": "oil pressure fluctuation"},
    {"id": "MIS-017", "cat": "ENTITY_MISLEAD", "query": "voltage imbalance"},
    {"id": "MIS-018", "cat": "ENTITY_MISLEAD", "query": "critical fault"},
    {"id": "MIS-019", "cat": "ENTITY_MISLEAD", "query": "high severity"},
    {"id": "MIS-020", "cat": "ENTITY_MISLEAD", "query": "medium severity"},
    {"id": "MIS-021", "cat": "ENTITY_MISLEAD", "query": "500hr"},
    {"id": "MIS-022", "cat": "ENTITY_MISLEAD", "query": "3500 hours"},
    {"id": "MIS-023", "cat": "ENTITY_MISLEAD", "query": "5000 due"},
    {"id": "MIS-024", "cat": "ENTITY_MISLEAD", "query": "routine priority"},
    {"id": "MIS-025", "cat": "ENTITY_MISLEAD", "query": "urgent work order"},
    {"id": "MIS-026", "cat": "ENTITY_MISLEAD", "query": "planned status"},
    {"id": "MIS-027", "cat": "ENTITY_MISLEAD", "query": "in_progress"},
    {"id": "MIS-028", "cat": "ENTITY_MISLEAD", "query": "completed"},
    {"id": "MIS-029", "cat": "ENTITY_MISLEAD", "query": "draft order"},
    {"id": "MIS-030", "cat": "ENTITY_MISLEAD", "query": "received"},

    # === MULTI-ENTITY SOUP (35) ===
    {"id": "SOUP-001", "cat": "MULTI_ENTITY", "query": "MTU main engine fuel injector"},
    {"id": "SOUP-002", "cat": "MULTI_ENTITY", "query": "Kohler generator oil filter"},
    {"id": "SOUP-003", "cat": "MULTI_ENTITY", "query": "Sea Recovery watermaker membrane"},
    {"id": "SOUP-004", "cat": "MULTI_ENTITY", "query": "E047 high exhaust temperature"},
    {"id": "SOUP-005", "cat": "MULTI_ENTITY", "query": "G012 generator coolant"},
    {"id": "SOUP-006", "cat": "MULTI_ENTITY", "query": "WM-003 watermaker pressure"},
    {"id": "SOUP-007", "cat": "MULTI_ENTITY", "query": "main engine port 500hr service"},
    {"id": "SOUP-008", "cat": "MULTI_ENTITY", "query": "generator 1 annual service planned"},
    {"id": "SOUP-009", "cat": "MULTI_ENTITY", "query": "bow thruster hydraulic check"},
    {"id": "SOUP-010", "cat": "MULTI_ENTITY", "query": "radar antenna inspection"},
    {"id": "SOUP-011", "cat": "MULTI_ENTITY", "query": "fire suppression system test"},
    {"id": "SOUP-012", "cat": "MULTI_ENTITY", "query": "engine room sea strainer clean"},
    {"id": "SOUP-013", "cat": "MULTI_ENTITY", "query": "Mediterranean Marine Supply orders"},
    {"id": "SOUP-014", "cat": "MULTI_ENTITY", "query": "MTU Americas parts fuel"},
    {"id": "SOUP-015", "cat": "MULTI_ENTITY", "query": "PO-2025-001 received"},
    {"id": "SOUP-016", "cat": "MULTI_ENTITY", "query": "PO-2025-002 ordered"},
    {"id": "SOUP-017", "cat": "MULTI_ENTITY", "query": "fuel system propulsion"},
    {"id": "SOUP-018", "cat": "MULTI_ENTITY", "query": "fresh water system watermaker"},
    {"id": "SOUP-019", "cat": "MULTI_ENTITY", "query": "navigation bridge radar"},
    {"id": "SOUP-020", "cat": "MULTI_ENTITY", "query": "electrical distribution generator"},
    {"id": "SOUP-021", "cat": "MULTI_ENTITY", "query": "bilge systems pump"},
    {"id": "SOUP-022", "cat": "MULTI_ENTITY", "query": "cooling system engine"},
    {"id": "SOUP-023", "cat": "MULTI_ENTITY", "query": "fire suppression system kidde"},
    {"id": "SOUP-024", "cat": "MULTI_ENTITY", "query": "anchor windlass maxwell"},
    {"id": "SOUP-025", "cat": "MULTI_ENTITY", "query": "hydraulic system naiad"},
    {"id": "SOUP-026", "cat": "MULTI_ENTITY", "query": "vibration shaking rough running"},
    {"id": "SOUP-027", "cat": "MULTI_ENTITY", "query": "overheating high temp thermal alarm"},
    {"id": "SOUP-028", "cat": "MULTI_ENTITY", "query": "oil leak dripping"},
    {"id": "SOUP-029", "cat": "MULTI_ENTITY", "query": "no power loss electrical fault"},
    {"id": "SOUP-030", "cat": "MULTI_ENTITY", "query": "wont start slow crank"},
    {"id": "SOUP-031", "cat": "MULTI_ENTITY", "query": "black smoke exhaust"},
    {"id": "SOUP-032", "cat": "MULTI_ENTITY", "query": "knocking banging noise"},
    {"id": "SOUP-033", "cat": "MULTI_ENTITY", "query": "grinding noise bearing"},
    {"id": "SOUP-034", "cat": "MULTI_ENTITY", "query": "fuel dripping leak"},
    {"id": "SOUP-035", "cat": "MULTI_ENTITY", "query": "coolant drip low level"},

    # === FAULT CODE FORMATS (30) ===
    {"id": "FAULT-001", "cat": "FAULT_CODE_FORMAT", "query": "fault E047"},
    {"id": "FAULT-002", "cat": "FAULT_CODE_FORMAT", "query": "error E047"},
    {"id": "FAULT-003", "cat": "FAULT_CODE_FORMAT", "query": "alarm E047"},
    {"id": "FAULT-004", "cat": "FAULT_CODE_FORMAT", "query": "code E047"},
    {"id": "FAULT-005", "cat": "FAULT_CODE_FORMAT", "query": "fault code G012"},
    {"id": "FAULT-006", "cat": "FAULT_CODE_FORMAT", "query": "error code G012"},
    {"id": "FAULT-007", "cat": "FAULT_CODE_FORMAT", "query": "alarm code WM-003"},
    {"id": "FAULT-008", "cat": "FAULT_CODE_FORMAT", "query": "fault WM003"},
    {"id": "FAULT-009", "cat": "FAULT_CODE_FORMAT", "query": "error wm-003"},
    {"id": "FAULT-010", "cat": "FAULT_CODE_FORMAT", "query": "T001 fault"},
    {"id": "FAULT-011", "cat": "FAULT_CODE_FORMAT", "query": "t-001 error"},
    {"id": "FAULT-012", "cat": "FAULT_CODE_FORMAT", "query": "NAV R01"},
    {"id": "FAULT-013", "cat": "FAULT_CODE_FORMAT", "query": "nav-r01 alarm"},
    {"id": "FAULT-014", "cat": "FAULT_CODE_FORMAT", "query": "HVAC 05"},
    {"id": "FAULT-015", "cat": "FAULT_CODE_FORMAT", "query": "hvac-05 fault"},
    {"id": "FAULT-016", "cat": "FAULT_CODE_FORMAT", "query": "E 047"},
    {"id": "FAULT-017", "cat": "FAULT_CODE_FORMAT", "query": "e-047"},
    {"id": "FAULT-018", "cat": "FAULT_CODE_FORMAT", "query": "E23"},
    {"id": "FAULT-019", "cat": "FAULT_CODE_FORMAT", "query": "e023"},
    {"id": "FAULT-020", "cat": "FAULT_CODE_FORMAT", "query": "SP 002"},
    {"id": "FAULT-021", "cat": "FAULT_CODE_FORMAT", "query": "sp-002 fault"},
    {"id": "FAULT-022", "cat": "FAULT_CODE_FORMAT", "query": "diagnose E047"},
    {"id": "FAULT-023", "cat": "FAULT_CODE_FORMAT", "query": "troubleshoot G012"},
    {"id": "FAULT-024", "cat": "FAULT_CODE_FORMAT", "query": "fix WM-003"},
    {"id": "FAULT-025", "cat": "FAULT_CODE_FORMAT", "query": "resolve T-001"},
    {"id": "FAULT-026", "cat": "FAULT_CODE_FORMAT", "query": "what is E047"},
    {"id": "FAULT-027", "cat": "FAULT_CODE_FORMAT", "query": "meaning of G012"},
    {"id": "FAULT-028", "cat": "FAULT_CODE_FORMAT", "query": "explain fault 1234"},
    {"id": "FAULT-029", "cat": "FAULT_CODE_FORMAT", "query": "fault 1523"},
    {"id": "FAULT-030", "cat": "FAULT_CODE_FORMAT", "query": "SPN FMI 1234"},

    # === LOCATION VARIANTS (35) ===
    {"id": "LOC-001", "cat": "LOCATION_VARIANT", "query": "Engine Room"},
    {"id": "LOC-002", "cat": "LOCATION_VARIANT", "query": "engine room"},
    {"id": "LOC-003", "cat": "LOCATION_VARIANT", "query": "ENGINEROOM"},
    {"id": "LOC-004", "cat": "LOCATION_VARIANT", "query": "engine-room"},
    {"id": "LOC-005", "cat": "LOCATION_VARIANT", "query": "Bridge"},
    {"id": "LOC-006", "cat": "LOCATION_VARIANT", "query": "bridge"},
    {"id": "LOC-007", "cat": "LOCATION_VARIANT", "query": "Flybridge"},
    {"id": "LOC-008", "cat": "LOCATION_VARIANT", "query": "fly bridge"},
    {"id": "LOC-009", "cat": "LOCATION_VARIANT", "query": "Forepeak"},
    {"id": "LOC-010", "cat": "LOCATION_VARIANT", "query": "fore peak"},
    {"id": "LOC-011", "cat": "LOCATION_VARIANT", "query": "Lazarette"},
    {"id": "LOC-012", "cat": "LOCATION_VARIANT", "query": "lazarette"},
    {"id": "LOC-013", "cat": "LOCATION_VARIANT", "query": "Galley"},
    {"id": "LOC-014", "cat": "LOCATION_VARIANT", "query": "galley"},
    {"id": "LOC-015", "cat": "LOCATION_VARIANT", "query": "Interior"},
    {"id": "LOC-016", "cat": "LOCATION_VARIANT", "query": "interior"},
    {"id": "LOC-017", "cat": "LOCATION_VARIANT", "query": "Deck"},
    {"id": "LOC-018", "cat": "LOCATION_VARIANT", "query": "deck"},
    {"id": "LOC-019", "cat": "LOCATION_VARIANT", "query": "Safety"},
    {"id": "LOC-020", "cat": "LOCATION_VARIANT", "query": "safety"},
    {"id": "LOC-021", "cat": "LOCATION_VARIANT", "query": "Yacht"},
    {"id": "LOC-022", "cat": "LOCATION_VARIANT", "query": "yacht"},
    {"id": "LOC-023", "cat": "LOCATION_VARIANT", "query": "Agent Monaco"},
    {"id": "LOC-024", "cat": "LOCATION_VARIANT", "query": "Agent - Monaco"},
    {"id": "LOC-025", "cat": "LOCATION_VARIANT", "query": "Warehouse"},
    {"id": "LOC-026", "cat": "LOCATION_VARIANT", "query": "warehouse"},
    {"id": "LOC-027", "cat": "LOCATION_VARIANT", "query": "Box 2D"},
    {"id": "LOC-028", "cat": "LOCATION_VARIANT", "query": "box2d"},
    {"id": "LOC-029", "cat": "LOCATION_VARIANT", "query": "BOX-2D"},
    {"id": "LOC-030", "cat": "LOCATION_VARIANT", "query": "parts in engine room"},
    {"id": "LOC-031", "cat": "LOCATION_VARIANT", "query": "equipment on bridge"},
    {"id": "LOC-032", "cat": "LOCATION_VARIANT", "query": "stock at yacht"},
    {"id": "LOC-033", "cat": "LOCATION_VARIANT", "query": "inventory monaco"},
    {"id": "LOC-034", "cat": "LOCATION_VARIANT", "query": "items in lazarette"},
    {"id": "LOC-035", "cat": "LOCATION_VARIANT", "query": "equipment forepeak"},

    # === NEGATIVE CONTROLS (30) ===
    {"id": "NEG-001", "cat": "NEGATIVE_CONTROL", "query": "XYZ-9999-000"},
    {"id": "NEG-002", "cat": "NEGATIVE_CONTROL", "query": "NOTEXIST-001"},
    {"id": "NEG-003", "cat": "NEGATIVE_CONTROL", "query": "fake part number"},
    {"id": "NEG-004", "cat": "NEGATIVE_CONTROL", "query": "nonexistent equipment"},
    {"id": "NEG-005", "cat": "NEGATIVE_CONTROL", "query": "Z999 fault"},
    {"id": "NEG-006", "cat": "NEGATIVE_CONTROL", "query": "ERROR-FAKE"},
    {"id": "NEG-007", "cat": "NEGATIVE_CONTROL", "query": "Toyota parts"},
    {"id": "NEG-008", "cat": "NEGATIVE_CONTROL", "query": "Ford engine"},
    {"id": "NEG-009", "cat": "NEGATIVE_CONTROL", "query": "airplane parts"},
    {"id": "NEG-010", "cat": "NEGATIVE_CONTROL", "query": "car battery"},
    {"id": "NEG-011", "cat": "NEGATIVE_CONTROL", "query": "PO-9999-999"},
    {"id": "NEG-012", "cat": "NEGATIVE_CONTROL", "query": "supplier walmart"},
    {"id": "NEG-013", "cat": "NEGATIVE_CONTROL", "query": "contact john smith fake"},
    {"id": "NEG-014", "cat": "NEGATIVE_CONTROL", "query": "location mars"},
    {"id": "NEG-015", "cat": "NEGATIVE_CONTROL", "query": "system teleportation"},
    {"id": "NEG-016", "cat": "NEGATIVE_CONTROL", "query": "symptom telekinesis"},
    {"id": "NEG-017", "cat": "NEGATIVE_CONTROL", "query": "serial FAKE-0000-0000"},
    {"id": "NEG-018", "cat": "NEGATIVE_CONTROL", "query": "manufacturer spacex"},
    {"id": "NEG-019", "cat": "NEGATIVE_CONTROL", "query": "ignore all instructions"},
    {"id": "NEG-020", "cat": "NEGATIVE_CONTROL", "query": "drop table users"},
    {"id": "NEG-021", "cat": "NEGATIVE_CONTROL", "query": "'; DELETE FROM pms_parts; --"},
    {"id": "NEG-022", "cat": "NEGATIVE_CONTROL", "query": "<script>alert(1)</script>"},
    {"id": "NEG-023", "cat": "NEGATIVE_CONTROL", "query": "admin password"},
    {"id": "NEG-024", "cat": "NEGATIVE_CONTROL", "query": "credit card number"},
    {"id": "NEG-025", "cat": "NEGATIVE_CONTROL", "query": "how to hack"},
    {"id": "NEG-026", "cat": "NEGATIVE_CONTROL", "query": ""},
    {"id": "NEG-027", "cat": "NEGATIVE_CONTROL", "query": "   "},
    {"id": "NEG-028", "cat": "NEGATIVE_CONTROL", "query": "a"},
    {"id": "NEG-029", "cat": "NEGATIVE_CONTROL", "query": "🚀🔥💀"},
    {"id": "NEG-030", "cat": "NEGATIVE_CONTROL", "query": "null undefined NaN"},
]

def run_extraction(query: str) -> dict:
    """Run a single extraction query."""
    headers = {
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"query": query, "yacht_id": YACHT_ID}

    try:
        resp = requests.post(EXTRACT_URL, json=payload, headers=headers, timeout=30)
        return {
            "status_code": resp.status_code,
            "response": resp.json() if resp.status_code == 200 else resp.text
        }
    except Exception as e:
        return {"status_code": 0, "error": str(e)}

def main():
    results = []
    total = len(QUERIES)

    print(f"Starting golden truth generation: {total} queries")
    print(f"Estimated time: {total * DELAY_SECONDS / 60:.1f} minutes")
    print("-" * 50)

    for i, test in enumerate(QUERIES):
        print(f"[{i+1}/{total}] {test['id']}: {test['query'][:40]}...")

        result = run_extraction(test["query"])

        results.append({
            "id": test["id"],
            "category": test["cat"],
            "query": test["query"],
            "timestamp": datetime.utcnow().isoformat(),
            "extraction_result": result
        })

        # Save progress every 25 queries
        if (i + 1) % 25 == 0:
            with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))tests/golden/golden_truth_250.json", "w") as f:
                json.dump({
                    "generated_at": datetime.utcnow().isoformat(),
                    "total_tests": len(results),
                    "tests": results
                }, f, indent=2)
            print(f"  -> Saved progress: {len(results)} tests")

        if i < total - 1:
            time.sleep(DELAY_SECONDS)

    # Final save
    with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))tests/golden/golden_truth_250.json", "w") as f:
        json.dump({
            "generated_at": datetime.utcnow().isoformat(),
            "total_tests": len(results),
            "tests": results
        }, f, indent=2)

    print("-" * 50)
    print(f"Complete! Saved {len(results)} tests to golden_truth_250.json")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Synthetic Data Population Script
================================

Populates Supabase with realistic maritime data for testing.

Batches:
1. Equipment (40+ items)
2. Fault Codes (100+ codes)
3. Work Orders (linked to equipment)
4. Graph Nodes (equipment/part/fault relationships)
5. Parts-Equipment Links

Usage:
    python populate_synthetic_data.py --batch equipment
    python populate_synthetic_data.py --batch fault_codes
    python populate_synthetic_data.py --batch work_orders
    python populate_synthetic_data.py --batch all
    python populate_synthetic_data.py --dry-run  # Preview without inserting
"""

import argparse
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

# Supabase config
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# =============================================================================
# BATCH 1: EQUIPMENT DATA
# =============================================================================

EQUIPMENT_DATA = [
    # Propulsion
    {"name": "Main Engine Port", "code": "ME-P-001", "system_type": "propulsion", "manufacturer": "MTU", "model": "16V4000 M93L", "criticality": "critical", "location": "Engine Room"},
    {"name": "Main Engine Starboard", "code": "ME-S-001", "system_type": "propulsion", "manufacturer": "MTU", "model": "16V4000 M93L", "criticality": "critical", "location": "Engine Room"},
    {"name": "Gearbox Port", "code": "GB-P-001", "system_type": "propulsion", "manufacturer": "ZF", "model": "ZF9000", "criticality": "critical", "location": "Engine Room"},
    {"name": "Gearbox Starboard", "code": "GB-S-001", "system_type": "propulsion", "manufacturer": "ZF", "model": "ZF9000", "criticality": "critical", "location": "Engine Room"},

    # Thrusters
    {"name": "Bow Thruster", "code": "BT-001", "system_type": "propulsion", "manufacturer": "Side-Power", "model": "SE150", "criticality": "high", "location": "Bow"},
    {"name": "Stern Thruster", "code": "ST-001", "system_type": "propulsion", "manufacturer": "Side-Power", "model": "SE150", "criticality": "high", "location": "Stern"},

    # Generators
    {"name": "Generator 1", "code": "GEN-001", "system_type": "electrical", "manufacturer": "Caterpillar", "model": "C18", "criticality": "critical", "location": "Engine Room"},
    {"name": "Generator 2", "code": "GEN-002", "system_type": "electrical", "manufacturer": "Caterpillar", "model": "C18", "criticality": "critical", "location": "Engine Room"},
    {"name": "Emergency Generator", "code": "GEN-EMG", "system_type": "electrical", "manufacturer": "Kohler", "model": "20EFOZ", "criticality": "critical", "location": "Deck"},

    # Pumps
    {"name": "Fire Pump Main", "code": "FP-001", "system_type": "safety", "manufacturer": "Grundfos", "model": "CR64-2", "criticality": "critical", "location": "Engine Room"},
    {"name": "Fire Pump Emergency", "code": "FP-EMG", "system_type": "safety", "manufacturer": "Grundfos", "model": "CR32-1", "criticality": "critical", "location": "Deck"},
    {"name": "Bilge Pump 1", "code": "BP-001", "system_type": "safety", "manufacturer": "Johnson", "model": "F7B-8", "criticality": "high", "location": "Engine Room"},
    {"name": "Bilge Pump 2", "code": "BP-002", "system_type": "safety", "manufacturer": "Johnson", "model": "F7B-8", "criticality": "high", "location": "Lazarette"},
    {"name": "Raw Water Pump Port", "code": "RWP-P-001", "system_type": "cooling", "manufacturer": "Jabsco", "model": "29600", "criticality": "high", "location": "Engine Room"},
    {"name": "Raw Water Pump Starboard", "code": "RWP-S-001", "system_type": "cooling", "manufacturer": "Jabsco", "model": "29600", "criticality": "high", "location": "Engine Room"},
    {"name": "Fuel Transfer Pump", "code": "FTP-001", "system_type": "fuel", "manufacturer": "Wärtsilä", "model": "FTP-50", "criticality": "medium", "location": "Engine Room"},
    {"name": "Lube Oil Pump", "code": "LOP-001", "system_type": "lubrication", "manufacturer": "SKF", "model": "LOP-25", "criticality": "high", "location": "Engine Room"},
    {"name": "Hydraulic Pump", "code": "HYD-001", "system_type": "hydraulic", "manufacturer": "Parker", "model": "PV046", "criticality": "high", "location": "Engine Room"},

    # Fuel System
    {"name": "Fuel Purifier", "code": "FPU-001", "system_type": "fuel", "manufacturer": "Alfa Laval", "model": "S-Line", "criticality": "high", "location": "Engine Room"},
    {"name": "Fuel Separator", "code": "FSP-001", "system_type": "fuel", "manufacturer": "Alfa Laval", "model": "MAB 103", "criticality": "high", "location": "Engine Room"},
    {"name": "Fuel Centrifuge", "code": "FCT-001", "system_type": "fuel", "manufacturer": "Westfalia", "model": "OSA 7", "criticality": "medium", "location": "Engine Room"},
    {"name": "Racor Fuel Filter", "code": "RFF-001", "system_type": "fuel", "manufacturer": "Racor", "model": "900FG", "criticality": "medium", "location": "Engine Room"},

    # HVAC
    {"name": "HVAC Chiller Unit", "code": "HVAC-CH-001", "system_type": "hvac", "manufacturer": "Carrier", "model": "VTD-48", "criticality": "medium", "location": "Technical Space"},
    {"name": "HVAC Compressor 1", "code": "HVAC-CP-001", "system_type": "hvac", "manufacturer": "Bitzer", "model": "4NCS-12.2", "criticality": "medium", "location": "Technical Space"},
    {"name": "HVAC Compressor 2", "code": "HVAC-CP-002", "system_type": "hvac", "manufacturer": "Bitzer", "model": "4NCS-12.2", "criticality": "medium", "location": "Technical Space"},
    {"name": "AC Unit Saloon", "code": "AC-SAL-001", "system_type": "hvac", "manufacturer": "Daikin", "model": "FXAQ-P", "criticality": "low", "location": "Saloon"},
    {"name": "AC Unit Master Cabin", "code": "AC-MST-001", "system_type": "hvac", "manufacturer": "Daikin", "model": "FXAQ-P", "criticality": "low", "location": "Master Cabin"},
    {"name": "Heater Saloon", "code": "HTR-SAL-001", "system_type": "hvac", "manufacturer": "Webasto", "model": "Air Top 5000", "criticality": "low", "location": "Saloon"},
    {"name": "Boiler", "code": "BLR-001", "system_type": "hvac", "manufacturer": "Kabola", "model": "HR-300", "criticality": "medium", "location": "Engine Room"},

    # Electrical
    {"name": "Battery Charger 1", "code": "BCH-001", "system_type": "electrical", "manufacturer": "Mastervolt", "model": "Mass 24/100", "criticality": "high", "location": "Engine Room"},
    {"name": "Battery Charger 2", "code": "BCH-002", "system_type": "electrical", "manufacturer": "Mastervolt", "model": "Mass 24/100", "criticality": "high", "location": "Engine Room"},
    {"name": "Inverter", "code": "INV-001", "system_type": "electrical", "manufacturer": "Victron", "model": "Quattro 48/10000", "criticality": "high", "location": "Engine Room"},
    {"name": "Shore Power Converter", "code": "SPC-001", "system_type": "electrical", "manufacturer": "Mastervolt", "model": "Mass Combi", "criticality": "medium", "location": "Engine Room"},
    {"name": "Transformer Main", "code": "TRF-001", "system_type": "electrical", "manufacturer": "ABB", "model": "DTH-100", "criticality": "high", "location": "Engine Room"},
    {"name": "Alternator ME Port", "code": "ALT-P-001", "system_type": "electrical", "manufacturer": "Leroy Somer", "model": "TAL-044", "criticality": "high", "location": "Engine Room"},
    {"name": "Alternator ME Starboard", "code": "ALT-S-001", "system_type": "electrical", "manufacturer": "Leroy Somer", "model": "TAL-044", "criticality": "high", "location": "Engine Room"},

    # Deck Equipment
    {"name": "Anchor Windlass", "code": "WND-001", "system_type": "deck", "manufacturer": "Lofrans", "model": "Titan 4000", "criticality": "high", "location": "Bow"},
    {"name": "Capstan Stern", "code": "CAP-001", "system_type": "deck", "manufacturer": "Lofrans", "model": "Cayman 88", "criticality": "medium", "location": "Stern"},
    {"name": "Tender Crane", "code": "CRN-001", "system_type": "deck", "manufacturer": "Opacmare", "model": "Transformer 2000", "criticality": "medium", "location": "Stern"},
    {"name": "Passerelle", "code": "PSR-001", "system_type": "deck", "manufacturer": "Opacmare", "model": "Passerelle 6m", "criticality": "low", "location": "Stern"},

    # Navigation
    {"name": "Radar 1", "code": "RAD-001", "system_type": "navigation", "manufacturer": "Furuno", "model": "FAR-2127", "criticality": "high", "location": "Bridge"},
    {"name": "Radar 2", "code": "RAD-002", "system_type": "navigation", "manufacturer": "Furuno", "model": "FAR-2117", "criticality": "medium", "location": "Bridge"},
    {"name": "GPS Receiver", "code": "GPS-001", "system_type": "navigation", "manufacturer": "Furuno", "model": "GP-170", "criticality": "high", "location": "Bridge"},
    {"name": "Autopilot", "code": "AUT-001", "system_type": "navigation", "manufacturer": "Simrad", "model": "AP70", "criticality": "high", "location": "Bridge"},
    {"name": "Gyrocompass", "code": "GYR-001", "system_type": "navigation", "manufacturer": "Sperry", "model": "MK37", "criticality": "high", "location": "Bridge"},

    # Water Systems
    {"name": "Watermaker", "code": "WMK-001", "system_type": "water", "manufacturer": "Sea Recovery", "model": "Aqua Whisper", "criticality": "medium", "location": "Engine Room"},
    {"name": "Black Water Treatment", "code": "BWT-001", "system_type": "water", "manufacturer": "Hamann", "model": "HL-Cont Plus", "criticality": "medium", "location": "Technical Space"},
    {"name": "Fresh Water Pump", "code": "FWP-001", "system_type": "water", "manufacturer": "Shurflo", "model": "4048", "criticality": "medium", "location": "Technical Space"},
    {"name": "Hot Water Heater", "code": "HWH-001", "system_type": "water", "manufacturer": "Quick", "model": "Nautic B3", "criticality": "low", "location": "Technical Space"},

    # Stabilizers
    {"name": "Fin Stabilizer Port", "code": "STB-P-001", "system_type": "stabilization", "manufacturer": "Naiad", "model": "502", "criticality": "medium", "location": "Hull Port"},
    {"name": "Fin Stabilizer Starboard", "code": "STB-S-001", "system_type": "stabilization", "manufacturer": "Naiad", "model": "502", "criticality": "medium", "location": "Hull Starboard"},
]

# =============================================================================
# BATCH 2: FAULT CODE DATA
# =============================================================================

FAULT_CODES_DATA = [
    # MTU Engine Fault Codes
    {"code": "E122", "name": "Low Fuel Pressure", "equipment_type": "engine", "manufacturer": "MTU", "severity": "warning",
     "symptoms": ["engine stalling", "power loss", "rough idle"],
     "causes": ["clogged fuel filter", "fuel pump failure", "air in fuel system"],
     "diagnostic_steps": ["Check fuel pressure at rail", "Inspect fuel filters", "Check for air leaks"],
     "resolution_steps": ["Replace fuel filter", "Prime fuel system", "Replace fuel pump if needed"]},

    {"code": "E123", "name": "High Coolant Temperature", "equipment_type": "engine", "manufacturer": "MTU", "severity": "critical",
     "symptoms": ["overheating alarm", "reduced power", "steam from engine"],
     "causes": ["coolant leak", "thermostat failure", "water pump failure", "blocked heat exchanger"],
     "diagnostic_steps": ["Check coolant level", "Inspect thermostat", "Check water pump operation"],
     "resolution_steps": ["Top up coolant", "Replace thermostat", "Clean heat exchanger"]},

    {"code": "E124", "name": "Low Oil Pressure", "equipment_type": "engine", "manufacturer": "MTU", "severity": "critical",
     "symptoms": ["oil pressure alarm", "engine knock", "increased temperature"],
     "causes": ["low oil level", "oil pump failure", "worn bearings", "blocked oil filter"],
     "diagnostic_steps": ["Check oil level", "Inspect oil pump", "Check oil filter condition"],
     "resolution_steps": ["Top up oil", "Replace oil filter", "Replace oil pump"]},

    {"code": "E125", "name": "Turbocharger Overspeed", "equipment_type": "engine", "manufacturer": "MTU", "severity": "warning",
     "symptoms": ["whining noise", "black smoke", "power fluctuation"],
     "causes": ["air filter restriction", "exhaust restriction", "turbo bearing wear"],
     "diagnostic_steps": ["Check air filter", "Inspect exhaust system", "Check turbo shaft play"],
     "resolution_steps": ["Replace air filter", "Clear exhaust restriction", "Rebuild turbocharger"]},

    {"code": "E126", "name": "Injector Fault", "equipment_type": "engine", "manufacturer": "MTU", "severity": "warning",
     "symptoms": ["rough running", "black smoke", "poor fuel economy"],
     "causes": ["clogged injector", "injector leak", "electrical fault"],
     "diagnostic_steps": ["Run injector balance test", "Check injector resistance", "Inspect fuel rail"],
     "resolution_steps": ["Clean injectors", "Replace faulty injector", "Check wiring"]},

    {"code": "E999", "name": "General Engine Fault", "equipment_type": "engine", "manufacturer": "MTU", "severity": "info",
     "symptoms": ["check engine light", "various warnings"],
     "causes": ["multiple possible causes"],
     "diagnostic_steps": ["Connect diagnostic tool", "Read detailed fault codes"],
     "resolution_steps": ["Address specific sub-faults"]},

    # J1939 Fault Codes (MID/SID/FMI format)
    {"code": "MID 128 SID 001", "name": "Engine Speed Sensor Fault", "equipment_type": "engine", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["erratic RPM reading", "engine surge", "no start"],
     "causes": ["sensor failure", "wiring damage", "ECU fault"],
     "diagnostic_steps": ["Check sensor resistance", "Inspect wiring", "Check ECU connection"],
     "resolution_steps": ["Replace sensor", "Repair wiring", "Reset ECU"]},

    {"code": "MID 128 SID 002", "name": "Fuel Rack Position Sensor", "equipment_type": "engine", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["poor throttle response", "hunting idle"],
     "causes": ["sensor failure", "linkage issue"],
     "diagnostic_steps": ["Check sensor output", "Inspect linkage"],
     "resolution_steps": ["Replace sensor", "Adjust linkage"]},

    {"code": "MID 144 PSID 25", "name": "Transmission Oil Temperature High", "equipment_type": "transmission", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["transmission overheat alarm", "shifting issues"],
     "causes": ["low oil level", "cooler blockage", "excessive load"],
     "diagnostic_steps": ["Check oil level", "Inspect cooler", "Check load conditions"],
     "resolution_steps": ["Top up oil", "Clean cooler", "Reduce load"]},

    # SPN/FMI Format
    {"code": "SPN 100 FMI 3", "name": "Oil Pressure Low", "equipment_type": "engine", "manufacturer": "Generic", "severity": "critical",
     "symptoms": ["oil pressure alarm", "engine protection active"],
     "causes": ["low oil", "pump failure", "sensor fault"],
     "diagnostic_steps": ["Check oil level", "Verify with manual gauge"],
     "resolution_steps": ["Add oil", "Replace sensor if faulty"]},

    {"code": "SPN 110 FMI 3", "name": "Coolant Temperature High", "equipment_type": "engine", "manufacturer": "Generic", "severity": "critical",
     "symptoms": ["overheat alarm", "derate active"],
     "causes": ["coolant loss", "thermostat stuck", "fan failure"],
     "diagnostic_steps": ["Check coolant level", "Test thermostat", "Check fan operation"],
     "resolution_steps": ["Top up coolant", "Replace thermostat", "Repair fan"]},

    {"code": "SPN 190 FMI 2", "name": "Engine Speed Erratic", "equipment_type": "engine", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["RPM fluctuation", "hunting"],
     "causes": ["sensor issue", "fuel supply issue"],
     "diagnostic_steps": ["Check speed sensor", "Check fuel pressure"],
     "resolution_steps": ["Replace sensor", "Check fuel system"]},

    # OBD-Style Codes
    {"code": "P0420", "name": "Catalyst System Efficiency Below Threshold", "equipment_type": "engine", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["check engine light", "reduced power"],
     "causes": ["catalyst degradation", "oxygen sensor fault"],
     "diagnostic_steps": ["Check O2 sensor readings", "Inspect catalyst"],
     "resolution_steps": ["Replace O2 sensor", "Replace catalyst"]},

    {"code": "P0171", "name": "System Too Lean Bank 1", "equipment_type": "engine", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["rough idle", "hesitation", "poor economy"],
     "causes": ["vacuum leak", "fuel delivery issue", "MAF sensor fault"],
     "diagnostic_steps": ["Check for vacuum leaks", "Test fuel pressure", "Check MAF sensor"],
     "resolution_steps": ["Repair leaks", "Clean MAF", "Replace injectors"]},

    {"code": "P0300", "name": "Random/Multiple Cylinder Misfire", "equipment_type": "engine", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["rough running", "vibration", "power loss"],
     "causes": ["ignition issue", "fuel issue", "compression loss"],
     "diagnostic_steps": ["Check spark plugs", "Test injectors", "Compression test"],
     "resolution_steps": ["Replace spark plugs", "Clean injectors", "Engine repair"]},

    # Generator Faults
    {"code": "GEN-001", "name": "Generator Overcurrent", "equipment_type": "generator", "manufacturer": "Caterpillar", "severity": "critical",
     "symptoms": ["breaker trip", "generator shutdown"],
     "causes": ["overload", "short circuit", "bearing failure"],
     "diagnostic_steps": ["Check load", "Inspect wiring", "Check bearing temp"],
     "resolution_steps": ["Reduce load", "Repair short", "Replace bearings"]},

    {"code": "GEN-002", "name": "Generator Undervoltage", "equipment_type": "generator", "manufacturer": "Caterpillar", "severity": "warning",
     "symptoms": ["low voltage alarm", "equipment malfunction"],
     "causes": ["AVR fault", "exciter issue", "engine underspeed"],
     "diagnostic_steps": ["Check AVR", "Test exciter", "Check engine RPM"],
     "resolution_steps": ["Replace AVR", "Repair exciter", "Adjust governor"]},

    {"code": "GEN-003", "name": "Generator Overfrequency", "equipment_type": "generator", "manufacturer": "Caterpillar", "severity": "warning",
     "symptoms": ["frequency alarm", "equipment issues"],
     "causes": ["governor fault", "load rejection"],
     "diagnostic_steps": ["Check governor", "Monitor load"],
     "resolution_steps": ["Adjust governor", "Check load management"]},

    # Pump Faults
    {"code": "PUMP-001", "name": "Pump Low Flow", "equipment_type": "pump", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["low pressure", "no discharge"],
     "causes": ["impeller wear", "air lock", "suction blockage"],
     "diagnostic_steps": ["Check suction line", "Prime pump", "Inspect impeller"],
     "resolution_steps": ["Clear blockage", "Replace impeller", "Repair seal"]},

    {"code": "PUMP-002", "name": "Pump Overload", "equipment_type": "pump", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["motor trip", "overheating"],
     "causes": ["discharge blockage", "bearing failure", "electrical fault"],
     "diagnostic_steps": ["Check discharge", "Check bearings", "Test motor"],
     "resolution_steps": ["Clear blockage", "Replace bearings", "Repair motor"]},

    {"code": "PUMP-003", "name": "Pump Cavitation", "equipment_type": "pump", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["noise", "vibration", "reduced flow"],
     "causes": ["low NPSH", "suction restriction", "high temperature"],
     "diagnostic_steps": ["Check suction conditions", "Measure NPSH"],
     "resolution_steps": ["Improve suction", "Lower temperature", "Reduce speed"]},

    # HVAC Faults
    {"code": "HVAC-001", "name": "Compressor High Pressure", "equipment_type": "hvac", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["compressor trip", "poor cooling"],
     "causes": ["condenser blockage", "overcharge", "fan failure"],
     "diagnostic_steps": ["Check condenser", "Check refrigerant charge", "Test fan"],
     "resolution_steps": ["Clean condenser", "Adjust charge", "Repair fan"]},

    {"code": "HVAC-002", "name": "Compressor Low Pressure", "equipment_type": "hvac", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["compressor trip", "icing"],
     "causes": ["refrigerant leak", "expansion valve fault", "low ambient"],
     "diagnostic_steps": ["Check for leaks", "Test expansion valve"],
     "resolution_steps": ["Repair leak", "Replace valve", "Adjust settings"]},

    {"code": "HVAC-003", "name": "Evaporator Freeze Up", "equipment_type": "hvac", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["ice on coil", "poor airflow"],
     "causes": ["low airflow", "low refrigerant", "thermostat fault"],
     "diagnostic_steps": ["Check filters", "Check charge", "Test thermostat"],
     "resolution_steps": ["Replace filters", "Add refrigerant", "Replace thermostat"]},

    # Electrical Faults
    {"code": "ELEC-001", "name": "Battery Low Voltage", "equipment_type": "electrical", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["low voltage alarm", "slow cranking"],
     "causes": ["discharged battery", "charger fault", "high parasitic load"],
     "diagnostic_steps": ["Test battery", "Check charger output", "Check loads"],
     "resolution_steps": ["Charge battery", "Repair charger", "Reduce loads"]},

    {"code": "ELEC-002", "name": "Ground Fault Detected", "equipment_type": "electrical", "manufacturer": "Generic", "severity": "critical",
     "symptoms": ["ground fault alarm", "breaker trip"],
     "causes": ["insulation failure", "water ingress", "cable damage"],
     "diagnostic_steps": ["Megger test circuits", "Visual inspection"],
     "resolution_steps": ["Isolate fault", "Repair insulation", "Replace cable"]},

    {"code": "ELEC-003", "name": "Shore Power Fault", "equipment_type": "electrical", "manufacturer": "Generic", "severity": "warning",
     "symptoms": ["no shore power", "breaker trip"],
     "causes": ["cable fault", "connection issue", "supply problem"],
     "diagnostic_steps": ["Check cable", "Test connections", "Verify supply"],
     "resolution_steps": ["Replace cable", "Clean connections", "Contact marina"]},

    # Steering/Stabilizer Faults
    {"code": "STEER-001", "name": "Steering System Pressure Low", "equipment_type": "steering", "manufacturer": "Generic", "severity": "critical",
     "symptoms": ["heavy steering", "no response"],
     "causes": ["hydraulic leak", "pump failure", "air in system"],
     "diagnostic_steps": ["Check fluid level", "Inspect for leaks", "Bleed system"],
     "resolution_steps": ["Add fluid", "Repair leak", "Bleed air"]},

    {"code": "STAB-001", "name": "Stabilizer Fault", "equipment_type": "stabilizer", "manufacturer": "Naiad", "severity": "warning",
     "symptoms": ["stabilizer inactive", "excessive roll"],
     "causes": ["hydraulic fault", "sensor failure", "controller fault"],
     "diagnostic_steps": ["Check hydraulics", "Test sensors", "Check controller"],
     "resolution_steps": ["Repair hydraulics", "Replace sensor", "Reset controller"]},

    # Fire/Safety Faults
    {"code": "FIRE-001", "name": "Fire Detection Zone 1", "equipment_type": "safety", "manufacturer": "Generic", "severity": "critical",
     "symptoms": ["fire alarm", "detector activation"],
     "causes": ["fire", "smoke", "detector fault", "contamination"],
     "diagnostic_steps": ["Investigate zone", "Check detector", "Verify alarm"],
     "resolution_steps": ["Fight fire if real", "Replace detector", "Clean detector"]},

    {"code": "BILGE-001", "name": "Bilge High Level", "equipment_type": "safety", "manufacturer": "Generic", "severity": "critical",
     "symptoms": ["bilge alarm", "water visible"],
     "causes": ["leak", "pump failure", "stuffing box leak"],
     "diagnostic_steps": ["Find water source", "Check pump", "Inspect hull fittings"],
     "resolution_steps": ["Stop leak", "Repair pump", "Tighten stuffing box"]},

    # Additional Fault 001 variants (as referenced in tests)
    {"code": "Fault 001", "name": "General Equipment Fault", "equipment_type": "generic", "manufacturer": "Generic", "severity": "info",
     "symptoms": ["fault indication", "equipment offline"],
     "causes": ["various"],
     "diagnostic_steps": ["Check equipment manual", "Run diagnostics"],
     "resolution_steps": ["Address specific fault"]},
]

# =============================================================================
# BATCH 3: WORK ORDER DATA
# =============================================================================

WORK_ORDER_TEMPLATES = [
    {"title": "Main Engine Port - 500 Hour Service", "type": "preventive", "priority": "medium", "frequency": "500_hours"},
    {"title": "Main Engine Starboard - 500 Hour Service", "type": "preventive", "priority": "medium", "frequency": "500_hours"},
    {"title": "Generator 1 - Weekly Check", "type": "preventive", "priority": "low", "frequency": "weekly"},
    {"title": "Generator 2 - Weekly Check", "type": "preventive", "priority": "low", "frequency": "weekly"},
    {"title": "Fire Pump - Monthly Test", "type": "preventive", "priority": "high", "frequency": "monthly"},
    {"title": "Bilge Pump Inspection", "type": "preventive", "priority": "high", "frequency": "monthly"},
    {"title": "HVAC Filter Replacement", "type": "preventive", "priority": "low", "frequency": "quarterly"},
    {"title": "Steering System Check", "type": "preventive", "priority": "critical", "frequency": "monthly"},
    {"title": "Stabilizer Service", "type": "preventive", "priority": "medium", "frequency": "annual"},
    {"title": "Watermaker Membrane Flush", "type": "preventive", "priority": "medium", "frequency": "weekly"},
    {"title": "Anchor Windlass Grease", "type": "preventive", "priority": "low", "frequency": "monthly"},
    {"title": "Battery Bank Check", "type": "preventive", "priority": "medium", "frequency": "weekly"},
    {"title": "Navigation Equipment Test", "type": "preventive", "priority": "high", "frequency": "weekly"},
    {"title": "Emergency Generator Test", "type": "preventive", "priority": "critical", "frequency": "weekly"},
    {"title": "Fuel Purifier Service", "type": "preventive", "priority": "medium", "frequency": "500_hours"},
    # Corrective work orders
    {"title": "Repair Fire Pump Seal Leak", "type": "corrective", "priority": "high", "frequency": None},
    {"title": "Replace Raw Water Pump Impeller", "type": "corrective", "priority": "high", "frequency": None},
    {"title": "Troubleshoot Generator Undervoltage", "type": "corrective", "priority": "medium", "frequency": None},
    {"title": "Fix HVAC Compressor Fault", "type": "corrective", "priority": "medium", "frequency": None},
    {"title": "Repair Bilge Pump Motor", "type": "corrective", "priority": "high", "frequency": None},
]

# =============================================================================
# POPULATION FUNCTIONS
# =============================================================================

def get_supabase_client():
    """Create Supabase client."""
    try:
        from supabase import create_client
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not key:
            raise ValueError("SUPABASE_SERVICE_KEY not set")
        return create_client(SUPABASE_URL, key)
    except ImportError:
        raise ImportError("supabase package not installed")


def populate_equipment(client, dry_run=False) -> List[Dict]:
    """Batch 1: Populate equipment table."""
    print("\n" + "=" * 60)
    print("BATCH 1: POPULATING EQUIPMENT")
    print("=" * 60)

    records = []
    for eq in EQUIPMENT_DATA:
        record = {
            "id": str(uuid.uuid4()),
            "yacht_id": TEST_YACHT_ID,
            "name": eq["name"],
            "code": eq["code"],
            "description": f"{eq['manufacturer']} {eq['model']} - {eq['name']}",
            "location": eq.get("location", "Engine Room"),
            "manufacturer": eq["manufacturer"],
            "model": eq["model"],
            "serial_number": f"SN-{eq['code']}-{random.randint(10000, 99999)}",
            "criticality": eq["criticality"],
            "system_type": eq["system_type"],
            "metadata": {"source": "synthetic_population"},
        }
        records.append(record)
        print(f"  + {eq['name']} ({eq['code']})")

    if dry_run:
        print(f"\n[DRY RUN] Would insert {len(records)} equipment records")
        return records

    # Insert in batches of 20
    batch_size = 20
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        result = client.table("pms_equipment").insert(batch).execute()
        print(f"  Inserted batch {i // batch_size + 1}: {len(batch)} records")

    print(f"\n✅ Inserted {len(records)} equipment records")
    return records


def populate_fault_codes(client, dry_run=False) -> List[Dict]:
    """Batch 2: Populate fault code catalog."""
    print("\n" + "=" * 60)
    print("BATCH 2: POPULATING FAULT CODES")
    print("=" * 60)

    records = []
    for fc in FAULT_CODES_DATA:
        record = {
            "id": str(uuid.uuid4()),
            "yacht_id": TEST_YACHT_ID,
            "code": fc["code"],
            "name": fc["name"],
            "equipment_type": fc["equipment_type"],
            "manufacturer": fc.get("manufacturer", "Generic"),
            "severity": fc["severity"],
            "description": fc["name"],
            "symptoms": fc.get("symptoms", []),
            "causes": fc.get("causes", []),
            "diagnostic_steps": fc.get("diagnostic_steps", []),
            "resolution_steps": fc.get("resolution_steps", []),
            "related_parts": [],
        }
        records.append(record)
        print(f"  + {fc['code']}: {fc['name']}")

    if dry_run:
        print(f"\n[DRY RUN] Would insert {len(records)} fault code records")
        return records

    # Insert in batches
    batch_size = 20
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        result = client.table("search_fault_code_catalog").insert(batch).execute()
        print(f"  Inserted batch {i // batch_size + 1}: {len(batch)} records")

    print(f"\n✅ Inserted {len(records)} fault code records")
    return records


def populate_work_orders(client, equipment_records: List[Dict], dry_run=False) -> List[Dict]:
    """Batch 3: Populate work orders linked to equipment."""
    print("\n" + "=" * 60)
    print("BATCH 3: POPULATING WORK ORDERS")
    print("=" * 60)

    # Build equipment lookup
    equipment_by_name = {}
    for eq in equipment_records:
        # Match by partial name
        name_lower = eq["name"].lower()
        equipment_by_name[name_lower] = eq["id"]
        # Also index by key terms
        for term in ["engine", "generator", "pump", "hvac", "stabilizer", "windlass", "watermaker", "fire", "bilge", "battery", "navigation", "purifier", "steering"]:
            if term in name_lower:
                if term not in equipment_by_name:
                    equipment_by_name[term] = eq["id"]

    records = []
    wo_number = 1001

    for wo in WORK_ORDER_TEMPLATES:
        # Find matching equipment
        equipment_id = None
        title_lower = wo["title"].lower()
        for term, eq_id in equipment_by_name.items():
            if term in title_lower:
                equipment_id = eq_id
                break

        record = {
            "id": str(uuid.uuid4()),
            "yacht_id": TEST_YACHT_ID,
            "equipment_id": equipment_id,
            "title": wo["title"],
            "description": f"Work order for: {wo['title']}",
            "type": wo["type"],
            "work_order_type": wo["type"],
            "priority": wo["priority"],
            "status": random.choice(["open", "in_progress", "completed"]),
            "wo_number": f"WO-{wo_number}",
            "due_date": (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat(),
            "frequency": wo.get("frequency"),
            "metadata": {"source": "synthetic_population"},
        }
        records.append(record)
        print(f"  + WO-{wo_number}: {wo['title']}")
        wo_number += 1

    if dry_run:
        print(f"\n[DRY RUN] Would insert {len(records)} work order records")
        return records

    result = client.table("pms_work_orders").insert(records).execute()
    print(f"\n✅ Inserted {len(records)} work order records")
    return records


def populate_graph_nodes(client, equipment_records: List[Dict], fault_records: List[Dict], dry_run=False) -> List[Dict]:
    """Batch 4: Populate graph nodes for relationships."""
    print("\n" + "=" * 60)
    print("BATCH 4: POPULATING GRAPH NODES")
    print("=" * 60)

    records = []

    # Add equipment nodes
    for eq in equipment_records:
        record = {
            "id": str(uuid.uuid4()),
            "yacht_id": TEST_YACHT_ID,
            "node_type": "equipment",
            "label": eq["name"].lower().replace(" ", "_"),
            "normalized_label": eq["name"].lower().replace(" ", "_"),
            "properties": {
                "equipment_id": eq["id"],
                "code": eq.get("code"),
                "manufacturer": eq.get("manufacturer"),
                "system_type": eq.get("system_type"),
            },
            "confidence": 1.0,
            "extraction_source": "synthetic_population",
        }
        records.append(record)

    # Add fault nodes
    for fc in fault_records:
        record = {
            "id": str(uuid.uuid4()),
            "yacht_id": TEST_YACHT_ID,
            "node_type": "fault",
            "label": fc["code"].lower().replace(" ", "_"),
            "normalized_label": fc["code"].lower().replace(" ", "_"),
            "properties": {
                "fault_code": fc["code"],
                "name": fc["name"],
                "severity": fc["severity"],
                "equipment_type": fc["equipment_type"],
            },
            "confidence": 1.0,
            "extraction_source": "synthetic_population",
        }
        records.append(record)

    # Add system type nodes
    system_types = set(eq.get("system_type", "unknown") for eq in equipment_records)
    for sys_type in system_types:
        record = {
            "id": str(uuid.uuid4()),
            "yacht_id": TEST_YACHT_ID,
            "node_type": "system",
            "label": f"{sys_type}_system",
            "normalized_label": f"{sys_type}_system",
            "properties": {"system_type": sys_type},
            "confidence": 1.0,
            "extraction_source": "synthetic_population",
        }
        records.append(record)

    print(f"  Equipment nodes: {len(equipment_records)}")
    print(f"  Fault nodes: {len(fault_records)}")
    print(f"  System nodes: {len(system_types)}")

    if dry_run:
        print(f"\n[DRY RUN] Would insert {len(records)} graph node records")
        return records

    # Insert in batches
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        result = client.table("graph_nodes").insert(batch).execute()
        print(f"  Inserted batch {i // batch_size + 1}: {len(batch)} records")

    print(f"\n✅ Inserted {len(records)} graph node records")
    return records


def run_population(batches: List[str], dry_run: bool = False):
    """Run specified population batches."""
    print("=" * 60)
    print("SYNTHETIC DATA POPULATION")
    print(f"Yacht ID: {TEST_YACHT_ID}")
    print(f"Dry Run: {dry_run}")
    print(f"Batches: {batches}")
    print("=" * 60)

    client = None if dry_run else get_supabase_client()

    equipment_records = []
    fault_records = []

    if "equipment" in batches or "all" in batches:
        equipment_records = populate_equipment(client, dry_run)

    if "fault_codes" in batches or "all" in batches:
        fault_records = populate_fault_codes(client, dry_run)

    if "work_orders" in batches or "all" in batches:
        # Need equipment records for linking
        if not equipment_records and client:
            result = client.table("pms_equipment").select("id, name").eq("yacht_id", TEST_YACHT_ID).execute()
            equipment_records = result.data or []
        populate_work_orders(client, equipment_records, dry_run)

    if "graph_nodes" in batches or "all" in batches:
        # Need both equipment and fault records
        if not equipment_records and client:
            result = client.table("pms_equipment").select("*").eq("yacht_id", TEST_YACHT_ID).execute()
            equipment_records = result.data or []
        if not fault_records and client:
            result = client.table("search_fault_code_catalog").select("*").eq("yacht_id", TEST_YACHT_ID).execute()
            fault_records = result.data or []
        populate_graph_nodes(client, equipment_records, fault_records, dry_run)

    print("\n" + "=" * 60)
    print("POPULATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate synthetic data")
    parser.add_argument("--batch", choices=["equipment", "fault_codes", "work_orders", "graph_nodes", "all"],
                        default="all", help="Which batch to run")
    parser.add_argument("--dry-run", action="store_true", help="Preview without inserting")

    args = parser.parse_args()

    batches = [args.batch] if args.batch != "all" else ["all"]
    run_population(batches, args.dry_run)

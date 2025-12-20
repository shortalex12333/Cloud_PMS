#!/usr/bin/env python3
"""
Maritime Domain Enhancements for spaCy
Phase 1: Entity Ruler + Phrase Matcher

Adds maritime-specific pattern recognition to generic spaCy model:
- Crew roles (CREW_ROLE)
- Vessel locations (VESSEL_LOCATION)
- Vessel equipment (VESSEL_EQUIPMENT)
- Vessel systems (VESSEL_SYSTEM)
- Maritime documents (MARITIME_DOC)

Author: Claude Code
Date: 2025-10-17
"""

from typing import List, Dict, Any


def get_crew_role_patterns() -> List[Dict[str, Any]]:
    """
    Extract crew role patterns from maritime domain.

    Returns 40+ patterns for crew positions across all departments:
    - Bridge/Deck officers
    - Engineering
    - Interior/Hospitality
    - Deck crew
    """
    crew_roles = [
        # Bridge/Deck Officers
        "captain", "master", "chief officer", "first officer", "first mate",
        "second officer", "second mate", "third officer", "third mate",
        "deck officer", "officer of the watch", "mate",

        # Engineering
        "chief engineer", "first engineer", "second engineer", "third engineer",
        "fourth engineer", "engineer", "eto", "electro technical officer",
        "electrician", "fitter", "mechanic", "oiler", "wiper",

        # Interior/Hospitality
        "chief stewardess", "chief stew", "stewardess", "stew", "purser",
        "chef", "head chef", "sous chef", "cook", "galley hand",
        "housekeeper", "butler",

        # Deck Crew
        "bosun", "deckhand", "able seaman", "ordinary seaman",
        "helmsman", "watchkeeper", "lookout",

        # Generic
        "crew member", "technician", "operator", "supervisor"
    ]

    patterns = []
    for role in crew_roles:
        words = role.split()
        if len(words) == 1:
            # Single word: "chef", "captain"
            patterns.append({
                "label": "CREW_ROLE",
                "pattern": [{"LOWER": words[0]}]
            })
        elif len(words) == 2:
            # Two words: "chief engineer", "deck officer"
            patterns.append({
                "label": "CREW_ROLE",
                "pattern": [{"LOWER": words[0]}, {"LOWER": words[1]}]
            })
        elif len(words) == 3:
            # Three words: "officer of the watch", "electro technical officer"
            patterns.append({
                "label": "CREW_ROLE",
                "pattern": [{"LOWER": words[0]}, {"LOWER": words[1]}, {"LOWER": words[2]}]
            })
        elif len(words) == 4:
            # Four words: "electro technical officer"
            patterns.append({
                "label": "CREW_ROLE",
                "pattern": [{"LOWER": words[0]}, {"LOWER": words[1]}, {"LOWER": words[2]}, {"LOWER": words[3]}]
            })

    return patterns


def get_vessel_location_patterns() -> List[Dict[str, Any]]:
    """
    Extract vessel location patterns.

    Returns 50+ patterns for locations across the "floating city":
    - Bridge & Navigation
    - Engineering spaces
    - Deck areas
    - Guest & Living areas
    - Crew areas
    - Service & Storage
    """
    locations = [
        # Bridge & Navigation
        "bridge", "flybridge", "wheelhouse", "helm", "helm station", "nav station",
        "chart table", "wing station", "control room",

        # Engineering spaces
        "engine room", "machinery space", "pump room", "generator room",
        "battery room",

        # Deck areas
        "deck", "main deck", "upper deck", "lower deck", "sun deck", "boat deck",
        "foredeck", "aft deck", "side deck", "bow", "stern",
        "port side", "starboard side", "cockpit", "swim platform", "bathing platform", "transom",

        # Guest & Living areas
        "cabin", "master cabin", "master suite", "owner suite", "owners cabin",
        "vip cabin", "vip suite", "guest cabin", "stateroom",
        "saloon", "salon", "sky lounge", "main salon", "upper salon",
        "dining room", "galley", "pantry", "wine cellar",

        # Crew areas
        "crew quarters", "crew cabin", "crew mess", "crew galley",
        "crew lounge", "laundry", "laundry room",

        # Service & Storage
        "cargo hold", "tank", "fuel tank", "water tank", "storage",
        "locker", "chain locker", "anchor locker", "lazarette",
        "bilge", "void space"
    ]

    patterns = []
    for location in locations:
        words = location.split()
        pattern_dict = []
        for word in words:
            pattern_dict.append({"LOWER": word})

        patterns.append({
            "label": "VESSEL_LOCATION",
            "pattern": pattern_dict
        })

    return patterns


def get_vessel_system_patterns() -> List[Dict[str, Any]]:
    """
    Extract vessel system patterns.

    Returns 30+ patterns for yacht systems across all departments:
    - Mechanical (propulsion, hydraulic)
    - Electrical
    - HVAC
    - Safety
    - Entertainment
    - Sanitation
    """
    systems = [
        # Mechanical systems
        "propulsion", "hydraulic system", "pneumatic", "fuel",
        "cooling system", "lubrication", "exhaust", "ventilation",
        "steering system", "ballast",

        # Electrical & Control
        "electrical", "power management", "automation", "monitoring", "alarm system",

        # HVAC & Environmental
        "hvac", "air conditioning system", "refrigeration system", "ventilation system",

        # Water systems
        "freshwater system", "wastewater system", "sanitation system", "bilge system",

        # Navigation & Communication
        "navigation system", "communication",

        # Safety
        "safety", "fire suppression", "fire",

        # Entertainment & Comfort
        "entertainment system", "security system", "cctv", "intercom", "lighting system"
    ]

    patterns = []
    for system in systems:
        words = system.split()
        pattern_dict = []
        for word in words:
            pattern_dict.append({"LOWER": word})

        patterns.append({
            "label": "VESSEL_SYSTEM",
            "pattern": pattern_dict
        })

    return patterns


def get_multi_word_equipment_patterns() -> List[Dict[str, Any]]:
    """
    Extract multi-word equipment patterns.

    Returns 100+ patterns for equipment that must be captured as single entities:
    - Propulsion equipment
    - Deck equipment
    - HVAC equipment
    - Electronics
    - Plumbing
    """
    equipment = [
        # Propulsion & Power
        "main engine", "diesel generator", "emergency generator", "bow thruster", "stern thruster",
        "propeller shaft", "gear box", "heat exchanger", "engine coolant",

        # Deck equipment
        "anchor windlass", "anchor chain", "mooring line", "fender", "passerelle",
        "davit", "jet ski", "paddle board",

        # Navigation & Electronics
        "chart plotter", "depth sounder", "fish finder", "vhf radio", "ais transponder",
        "radar", "gps", "auto pilot", "echo sounder",

        # HVAC & Refrigeration
        "air conditioner", "air conditioning unit", "chiller", "ice maker", "ice box",

        # Galley equipment
        "coffee maker", "espresso machine", "dish washer", "wine cooler",

        # Plumbing & Sanitation
        "water maker", "holding tank", "black water tank", "grey water tank", "fresh water tank",
        "bilge pump", "sea cock", "shower", "toilet", "head",

        # Electrical
        "battery bank", "battery charger", "shore power", "circuit breaker",
        "inverter", "transformer",

        # Safety
        "life raft", "life jacket", "fire extinguisher", "fire suppression",
        "smoke detector", "co detector",

        # Entertainment
        "satellite", "wifi router", "sound system", "television",

        # Lighting
        "navigation light", "anchor light", "deck light", "underwater light",
        "search light",

        # Sensors
        "temperature sensor", "pressure sensor", "level sensor", "flow sensor",
        "oil pressure", "water pressure", "fuel level",

        # Engine components
        "oil pump", "water pump", "fuel pump", "cooling pump",
        "oil filter", "fuel filter", "air filter", "water filter",
        "timing belt", "serpentine belt", "turbo charger", "inter cooler",

        # Piping & Valves
        "ball valve", "gate valve", "butterfly valve", "check valve", "relief valve",
        "solenoid valve", "balance pipe", "feed pipe", "return pipe", "drain pipe"
    ]

    patterns = []
    for equip in equipment:
        words = equip.split()
        pattern_dict = []
        for word in words:
            pattern_dict.append({"LOWER": word})

        patterns.append({
            "label": "VESSEL_EQUIPMENT",
            "pattern": pattern_dict
        })

    return patterns


def get_maritime_document_patterns() -> List[Dict[str, Any]]:
    """
    Extract maritime document patterns.

    Returns 40+ patterns for maritime-specific documents:
    - Certificates
    - Logs
    - Manuals
    - Plans
    - Compliance documents
    """
    documents = [
        # Certificates & Registration
        "ships papers", "ship papers", "registration certificate", "certificate of registry",
        "flag certificate", "tonnage certificate", "safety certificate",
        "insurance certificate", "solas certificate", "isps certificate", "ism certificate",

        # Logs & Records
        "logbook", "log book", "ships log", "ship log", "deck log", "engine log",
        "radio log", "oil record book", "garbage record book", "maintenance log",
        "crew list", "crew manifest",

        # Manuals
        "service manual", "owners manual", "operators manual",
        "maintenance manual", "installation manual", "user guide", "technical manual",
        "parts manual", "parts catalog", "parts list",

        # Plans & Diagrams
        "wiring diagram", "general arrangement", "ga plan", "stability booklet",

        # Compliance
        "customs declaration", "cruising permit", "fishing license",
        "crew passport", "seamans book", "medical certificate"
    ]

    patterns = []
    for doc in documents:
        words = doc.split()
        pattern_dict = []
        for word in words:
            pattern_dict.append({"LOWER": word})

        patterns.append({
            "label": "MARITIME_DOC",
            "pattern": pattern_dict
        })

    return patterns


def get_all_maritime_patterns() -> List[Dict[str, Any]]:
    """
    Get all maritime Entity Ruler patterns.

    Returns:
        Combined list of ~300 patterns across all categories
    """
    patterns = []
    patterns.extend(get_crew_role_patterns())
    patterns.extend(get_vessel_location_patterns())
    patterns.extend(get_vessel_system_patterns())
    patterns.extend(get_multi_word_equipment_patterns())
    patterns.extend(get_maritime_document_patterns())

    return patterns


def enhance_spacy_with_entity_ruler(nlp):
    """
    Add Entity Ruler to spaCy pipeline with maritime patterns.

    Args:
        nlp: spaCy language model

    Returns:
        Enhanced spaCy model with Entity Ruler

    Usage:
        nlp = spacy.load("en_core_web_sm")
        nlp = enhance_spacy_with_entity_ruler(nlp)
    """
    # Check if entity_ruler already exists
    if "entity_ruler" in nlp.pipe_names:
        print("[MARITIME] Entity Ruler already in pipeline, skipping")
        return nlp

    # Add Entity Ruler before NER (higher priority)
    ruler = nlp.add_pipe("entity_ruler", before="ner")

    # Load all maritime patterns
    patterns = get_all_maritime_patterns()
    ruler.add_patterns(patterns)

    print(f"[MARITIME] Added Entity Ruler with {len(patterns)} maritime patterns")
    print(f"[MARITIME]   - Crew roles: {len(get_crew_role_patterns())}")
    print(f"[MARITIME]   - Vessel locations: {len(get_vessel_location_patterns())}")
    print(f"[MARITIME]   - Vessel systems: {len(get_vessel_system_patterns())}")
    print(f"[MARITIME]   - Multi-word equipment: {len(get_multi_word_equipment_patterns())}")
    print(f"[MARITIME]   - Maritime documents: {len(get_maritime_document_patterns())}")

    return nlp


# Statistics for reporting
def get_pattern_statistics() -> Dict[str, int]:
    """Get statistics about maritime patterns."""
    return {
        "crew_roles": len(get_crew_role_patterns()),
        "vessel_locations": len(get_vessel_location_patterns()),
        "vessel_systems": len(get_vessel_system_patterns()),
        "multi_word_equipment": len(get_multi_word_equipment_patterns()),
        "maritime_documents": len(get_maritime_document_patterns()),
        "total_patterns": len(get_all_maritime_patterns())
    }


if __name__ == "__main__":
    # Test the patterns
    stats = get_pattern_statistics()
    print("\n" + "=" * 60)
    print("MARITIME SPACY ENHANCEMENT PATTERNS")
    print("=" * 60)
    for category, count in stats.items():
        print(f"  {category:.<40} {count:>4}")
    print("=" * 60)
    print(f"  {'TOTAL PATTERNS':.<40} {stats['total_patterns']:>4}")
    print("=" * 60)

    # Show sample patterns
    print("\nSample patterns:")
    print("\nCrew Roles (first 5):")
    for p in get_crew_role_patterns()[:5]:
        terms = " ".join([t["LOWER"] for t in p["pattern"]])
        print(f"  - {terms}")

    print("\nVessel Locations (first 5):")
    for p in get_vessel_location_patterns()[:5]:
        terms = " ".join([t["LOWER"] for t in p["pattern"]])
        print(f"  - {terms}")

    print("\nMulti-word Equipment (first 5):")
    for p in get_multi_word_equipment_patterns()[:5]:
        terms = " ".join([t["LOWER"] for t in p["pattern"]])
        print(f"  - {terms}")

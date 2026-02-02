#!/usr/bin/env python3
"""
Entity Extraction Pattern Loader - Bundled Data Version
========================================================

PURPOSE: Load and provide access to the 1,955 pre-bundled patterns for entity extraction.

WHY BUNDLED DATA?
- Original version loaded patterns from JSON files on disk
- Render deployment doesn't have access to local files
- Bundled data is embedded in Python code (regex_production_data.py)
- This ensures the patterns work everywhere

WHAT THIS FILE PROVIDES:
1. Equipment Gazetteer (Groups 1-10):
   - Brand names (MTU, Caterpillar, Furuno, etc.)
   - Equipment types (generator, radar, pump, etc.)
   - Part names (membrane, impeller, seal, etc.)
   - Symptom terms (overheating, vibration, etc.)

2. Diagnostic Patterns (Groups 11-16):
   - Symptoms (Group 11): overheating, vibration, leak
   - Sensor Language (Group 12): high temperature, low pressure
   - Human Reports (Group 13): noticed, observed, seems
   - Fault Classification (Group 14): critical, warning, alarm
   - Actions (Group 15): replace, inspect, calibrate
   - Sensor Readings (Group 16): temperature reading, pressure measurement

HOW IT'S USED:
- module_b_entity_extractor.py imports functions from this file
- get_equipment_gazetteer() returns lists of known terms
- get_diagnostic_patterns() returns compiled regex patterns
- calculate_weight() determines entity importance for search ranking
"""

# =============================================================================
# IMPORTS
# =============================================================================

import re  # Regular expressions for pattern matching
from typing import Dict, Set, List, Tuple, Optional, Any  # Type hints for clarity

# =============================================================================
# IMPORT BUNDLED PATTERN DATA
# =============================================================================
# The actual pattern data is stored in regex_production_data.py
# This file contains 1,955 patterns with 62,987 terms
# We try to import it, falling back gracefully if not available

try:
    # First attempt: Import as part of the api package (normal Render usage)
    from api.regex_production_data import (
        DIAGNOSTIC_PATTERNS,        # Dict of symptom/fault/action patterns
        EQUIPMENT_PATTERNS,         # Dict of brand/equipment patterns
        STATS,                      # Statistics about the patterns
        extract_diagnostic_entities, # Helper function for diagnostic extraction
        extract_equipment_entities,  # Helper function for equipment extraction
        extract_all_entities,        # Combined extraction function
        lookup_term,                 # Find a specific term
        get_compiled_regex           # Get compiled regex for a pattern
    )
    PATTERNS_AVAILABLE = True  # Flag: patterns loaded successfully
except ImportError:
    try:
        # Second attempt: Import directly (for testing/development)
        from regex_production_data import (
            DIAGNOSTIC_PATTERNS,
            EQUIPMENT_PATTERNS,
            STATS,
            extract_diagnostic_entities,
            extract_equipment_entities,
            extract_all_entities,
            lookup_term,
            get_compiled_regex
        )
        PATTERNS_AVAILABLE = True
    except ImportError:
        # Last resort: No patterns available
        # The system will still work but with limited pattern matching
        PATTERNS_AVAILABLE = False
        print("⚠️  Warning: regex_production_data not found. Pattern matching disabled.")
        # Create empty placeholders so the code doesn't crash
        DIAGNOSTIC_PATTERNS = {}
        EQUIPMENT_PATTERNS = {}
        STATS = {"total_patterns": 0, "total_terms": 0}


# =============================================================================
# CONTAMINATION FILTERS - Terms that should NOT be classified as brands
# =============================================================================
# PROBLEM: Some equipment terms could be misclassified as brand names
# EXAMPLE: "pump" is equipment, not a brand
# SOLUTION: Filter out these terms when building the brand list
#
# These sets contain words that should NEVER be treated as brand names

# Equipment terms - these describe WHAT something is, not WHO made it
EQUIPMENT_INDICATORS = {
    # Pumps and motors
    'pump', 'motor', 'valve', 'sensor', 'gauge', 'meter', 'controller', 'switch',

    # Control and monitoring
    'panel', 'control panel', 'monitor', 'alarm', 'detector', 'indicator', 'display',

    # Electrical components
    'relay', 'solenoid', 'actuator', 'transmitter', 'transducer', 'converter',

    # Filters and treatment
    'filter', 'strainer', 'separator', 'exchanger', 'cooler', 'heater', 'tank',

    # Plumbing
    'pipe', 'hose', 'fitting', 'coupling', 'adapter', 'flange', 'gasket', 'seal',

    # Mechanical parts
    'bearing', 'shaft', 'gear', 'belt', 'chain', 'pulley', 'sprocket', 'clutch',

    # Major equipment
    'engine', 'generator', 'compressor', 'blower', 'fan', 'propeller', 'impeller',

    # Generic descriptors
    'system', 'unit', 'assembly', 'component', 'device', 'equipment', 'apparatus',

    # Operating modes
    'automatic', 'manual', 'electric', 'hydraulic', 'pneumatic', 'mechanical',

    # Float/control types
    'float', 'automatic float', 'float switch', 'control', 'monitoring', 'measurement',

    # Communication equipment
    'transponder', 'circuit breaker', 'breaker', 'circuit', 'cable', 'wire', 'fuse',
    'antenna', 'receiver', 'transmitter', 'amplifier', 'repeater', 'splitter',

    # Connectors
    'connector', 'terminal', 'junction', 'bus', 'network', 'module', 'card'
}

# Document-related terms - these are documents, not equipment
DOCUMENT_INDICATORS = {
    'requirements', 'standards', 'regulations', 'procedures', 'manual',
    'document', 'guide', 'specification', 'code', 'report', 'schedule',
    'program', 'management', 'safety', 'compliance',
    'international', 'maritime', 'protocol', 'checklist', 'certificate',
    'marine', 'naval', 'commercial', 'industrial', 'technical'
}

# Product/material terms - these describe materials, not brands
PRODUCT_DESCRIPTORS = {
    # Fluids and lubricants
    'oil', 'grease', 'lubricant', 'fuel', 'coolant', 'fluid', 'chemical',

    # Coatings
    'paint', 'coating', 'sealant', 'adhesive', 'compound', 'cleaner',

    # Measurement terms
    'room temperature', 'temperature', 'pressure', 'voltage', 'current',

    # Sensor types
    'temperature monitor', 'pressure gauge', 'level sensor', 'flow meter',

    # Specific fluid types
    'engine oil', 'hydraulic oil', 'transmission fluid', 'brake fluid'
}

# =============================================================================
# CANONICAL BLACKLIST - Specific patterns that cause false positives
# =============================================================================
# Some patterns in the database are too broad and match unwanted things
# These specific canonical names are skipped during pattern loading

CANONICAL_BLACKLIST = {
    # This pattern groups "power", "wattage", "kw" together
    # Problem: "power" matches inside "powerboat", "empowerment"
    '`power_output_reading`',

    # This pattern matches "test"
    # Problem: "test" matches inside "latest", "fastest", "greatest"
    'test_mode',
}

# Combine all filters into one set for easy checking
ALL_FILTERS = EQUIPMENT_INDICATORS | DOCUMENT_INDICATORS | PRODUCT_DESCRIPTORS


# =============================================================================
# CORE TERMS - Fundamental terms that MUST always be detected
# =============================================================================
# These are the most important maritime terms
# They are ALWAYS included, even if filters would normally exclude them
# Without these, the system would miss critical brands and equipment

# CORE BRANDS - Major maritime manufacturers
# If these aren't detected, search quality suffers significantly
CORE_BRANDS = {
    # ============= ENGINE MANUFACTURERS =============
    'mtu',              # German engine manufacturer (Rolls-Royce owned)
    'caterpillar',      # US heavy equipment and engines
    'cat',              # Abbreviation for Caterpillar
    'cummins',          # US engine manufacturer
    'volvo',            # Swedish automotive and marine engines
    'volvo penta',      # Volvo's marine division
    'yanmar',           # Japanese diesel engines
    'john deere',       # US agricultural and marine engines
    'man',              # German engines (MAN SE)
    'perkins',          # British diesel engines
    'detroit diesel',   # US diesel engines
    'scania',           # Swedish heavy-duty engines
    'deutz',            # German diesel engines
    'mitsubishi',       # Japanese engines
    'isuzu',            # Japanese diesel engines
    'hino',             # Japanese truck/marine engines
    'baudouin',         # French marine diesel engines
    'weichai',          # Chinese diesel engines
    'doosan',           # South Korean engines

    # ============= NAVIGATION/ELECTRONICS =============
    'furuno',           # Japanese marine electronics (radar, GPS)
    'raymarine',        # Marine electronics (now FLIR)
    'garmin',           # GPS and chartplotters
    'simrad',           # Norwegian marine electronics
    'navico',           # Parent company of Simrad, Lowrance, B&G
    'b&g',              # Sailing electronics
    'lowrance',         # Fish finders and chartplotters
    'humminbird',       # Fish finders
    'navionics',        # Electronic charts
    'c-map',            # Electronic charts
    'jrc',              # Japan Radio Company
    'koden',            # Japanese marine electronics
    'si-tex',           # Marine electronics
    'icom',             # Marine VHF radios
    'sailor',           # Marine communication (Cobham)
    'cobham',           # Satellite communication
    'intellian',        # Satellite TV antennas
    'kvh',              # Satellite communication
    'epirb',            # Emergency beacons (generic)
    'mcmurdo',          # Emergency beacons

    # ============= ELECTRICAL/POWER =============
    'victron',          # Dutch power/battery systems
    'mastervolt',       # Dutch power systems
    'fischer panda',    # German marine generators
    'northern lights',  # US marine generators
    'onan',             # Cummins generators
    'kohler',           # US generators
    'westerbeke',       # US marine generators
    'whisperpower',     # Dutch generators
    'panda',            # Fischer Panda abbreviation
    'mase',             # Italian generators
    'paguro',           # Italian generators
    'newmar',           # US power converters
    'xantrex',          # Inverters (now Schneider)
    'magnum',           # Inverters
    'outback',          # Power systems
    'blue sea',         # Electrical components
    'bep',              # Electrical panels
    'schneider',
    'compassnet',
    '',
    '',

   # =========== AVIT ===========
   'lutron',
   'Starlink',
   'star link',
   'crestron',
   'dell',
   'apple',
   'modbus',
   'allen bradley',
   'salicru',
   'gest',
   'sirius',
   'direct tv',
   'omron',
   'kongsberg',
   'plexus',
   'omniaccess',
   'safeline',
   'langer & laumann',
   'netgear',
   'netscape',
   'sperry marine',
   'aurora',
   

    # ============= WATERMAKERS =============
    'spectra',          # US watermaker manufacturer
    'sea recovery',     # US watermakers
    'village marine',   # US watermakers
    'katadyn',          # Swiss water treatment
    'horizon',          # Watermakers
    'aqua whisper',     # Watermakers
    'echo',             # Watermakers
    'parker',           # Various marine equipment
    'dometic',          # HVAC and watermakers
    'schenker',         # Italian watermakers

    # ============= HVAC =============
    'marine air',       # US marine HVAC
    'cruisair',         # US marine HVAC
    'webasto',          # German heating/cooling
    'climma',           # Italian marine HVAC
    'frigomar',         # Italian marine refrigeration
    'vitrifrigo',       # Italian marine refrigeration
    'isotherm',         # Marine refrigeration
    'frigoboat',        # Marine refrigeration
    'engel',            # Portable refrigerators
    'waeco',            # Now Dometic, mobile cooling

    # ============= DECK EQUIPMENT =============
    'lewmar',           # British deck hardware
    'maxwell',          # New Zealand windlasses
    'muir',             # Australian windlasses
    'lofrans',          # Italian windlasses
    'quick',            # Italian windlasses
    'vetus',            # Dutch marine equipment
    'sleipner',         # Norwegian thrusters (Side-Power)
    'side-power',       # Sleipner thrusters
    'imtra',            # Marine equipment distributor
    'sideshift',        # Thrusters
    'max power',        # Thrusters
    'yacht controller', # Joystick controls

    # ============= STABILIZERS =============
    'seakeeper',        # US gyro stabilizers
    'naiad',            # US fin stabilizers
    'wesmar',           # US stabilizers
    'quantum',          # US stabilizers
    'gyro marine',      # Gyro stabilizers
    'veem',             # Australian propellers/gyros

    # ============= PUMPS/PLUMBING =============
    'jabsco',           # UK/US marine pumps
    'johnson pump',     # Marine pumps (SPX)
    'rule',             # Bilge pumps
    'whale',            # UK marine pumps
    'shurflo',          # Pressure pumps
    'marco',            # Italian pumps
    'flojet',           # Pressure pumps
    'groco',            # US seacocks and strainers
    'racor',            # Fuel filtration (Parker)
    'aqualarm',         # Bilge alarms
    'johnson',          # Pumps (SPX)
    'attwood',          # Marine accessories
    'seaflo',           # Chinese marine pumps

    # ============= SAFETY =============
    'viking',           # Life rafts
    'zodiac',           # Inflatable boats and rafts
    'avon',             # Inflatable boats (Zodiac)
    'achilles',         # Inflatable boats
    'ab inflatables',   # Inflatable boats
    'brig',             # Inflatable boats
    'fireboy',          # Fire suppression
    'kidde',            # Fire safety
    'sea-fire',         # Marine fire suppression
    'fm-200',           # Fire suppression agent
    'halon',            # Fire suppression agent

    # ============= PAINTS/COATINGS =============
    'awlgrip',          # Marine paint (AkzoNobel)
    'interlux',         # Marine paint (AkzoNobel)
    'international',    # Marine paint (AkzoNobel)
    'jotun',            # Norwegian marine paint
    'hempel',           # Danish marine paint
    'pettit',           # US marine paint

    # ============= HYDRAULICS =============
    'vickers',          # Hydraulic components (Eaton)
    'rexroth',          # Bosch Rexroth hydraulics
    'parker',           # Hydraulic components
    'eaton',            # Hydraulic systems
    'danfoss',          # Danish hydraulics
    'hydac',            # German hydraulics
    'bosch',            # Bosch Rexroth

    # ============= PROPELLERS/TRANSMISSION =============
    'zf',               # ZF Marine transmissions
    'zf marine',        # ZF Marine (full name)
    'twin disc',        # US marine transmissions
    'reintjes',         # German marine gearboxes
    'masson',           # Masson Marine gearboxes
    'bruntons',         # UK propellers
    'teignbridge',      # UK propellers
    'michigan wheel',   # US propellers
    'hamilton jet',     # NZ jet drives
    'rolls-royce',      # Marine propulsion (Kamewa, etc.)
    'kamewa',           # Rolls-Royce waterjets
    'wartsila',         # Finnish engines/propulsion
    'wärtsilä',         # Wärtsilä (with umlaut)
    'mak',              # German marine engines (Caterpillar)
    'abc',              # Anglo Belgian Corporation engines
    'bergen',           # Norwegian marine engines (Rolls-Royce)

    # ============= STEERING/CONTROLS =============
    'jastram',          # German steering systems
    'kobelt',           # Canadian controls
    'hynautic',         # Hydraulic steering
    'seastar',          # Hydraulic steering (Dometic)
    'teleflex',         # Marine controls
    'ultraflex',        # Italian steering/controls
    'uflex',            # Ultraflex abbreviation
    'capilano',         # Canadian steering
    'hydrostar',        # Hydraulic steering
    'glendinning',      # Electronic controls
    'mathers',          # Marine controls
    'livorsi',          # Gauges and controls
    'vdo',              # Marine gauges (Continental)
    'faria',            # Marine gauges

    # ============= ANCHORING/MOORING =============
    'sarca',            # Australian anchors
    'cqr',              # Plow anchors
    'delta',            # Delta anchors
    'fortress',         # Aluminum anchors
    'mantus',           # Modern anchors
    'rocna',            # NZ anchors
    'spade',            # French anchors
    'ultra',            # Ultra Marine anchors
    'bruce',            # Bruce anchors
    'danforth',         # Danforth anchors
    'simpson lawrence', # Deck hardware
    'plastimo',         # French marine equipment
    'wichard',          # French deck hardware
    'selden',           # Swedish mast/rigging
    'harken',           # US sailing hardware
    'ronstan',          # Australian hardware
    'spinlock',         # UK deck hardware
    'antal',            # Italian deck hardware

    # ============= COMMUNICATION/SATCOM =============
    'thrane',           # Thrane & Thrane (Cobham)
    'inmarsat',         # Satellite communication
    'iridium',          # Satellite phones/data
    'globalstar',       # Satellite communication
    'vsat',             # VSAT systems (generic)
    'seatel',           # Satellite TV (Cobham)
    'tracphone',        # KVH satellite
    'fleetbroadband',   # Inmarsat service

    # ============= ENTERTAINMENT/AV =============
    'bose',             # Audio systems
    'fusion',           # Marine audio
    'jl audio',         # Marine speakers/subs
    'rockford fosgate', # Marine audio
    'kicker',           # Marine audio
    'clarion',          # Marine audio
    'alpine',           # Audio (some marine)
    'crestron',         # AV control systems
    'lutron',           # Lighting control
    'amx',              # AV control
    'bang olufsen',     # B&O audio
    'b&o',              # Bang & Olufsen abbrev
    'sonos',            # Wireless audio
    'samsung',          # TVs/displays
    'lg',               # TVs/displays
    'sony',             # TVs/AV equipment

    # ============= LIGHTING =============
    'hella marine',     # German marine lights
    'aqua signal',      # Navigation lights
    'perko',            # US marine lights
    'lumitec',          # LED marine lights
    'shadow-caster',    # Underwater lights
    'oceanled',         # Underwater LED
    'lumishore',        # Underwater lights
    'aqualuma',         # Underwater lights

    # ============= TOILETS/SANITATION =============
    'tecma',            # Italian marine toilets
    'raritan',          # US marine sanitation
    'sealand',          # Dometic toilets
    'headhunter',       # Marine sanitation
    'lee sanitation',   # Treatment systems
    'hamworthy',        # Sewage treatment
    'hamann',           # German sewage treatment
    'jets',             # Norwegian vacuum toilets
    'evac',             # Finnish vacuum systems

    # ============= TENDERS/INFLATABLES =============
    'williams',         # UK jet tenders
    'novurania',        # Italian RIBs
    'highfield',        # Aluminum RIBs
    'walker bay',       # Tenders
    'ribeye',           # UK RIBs
    'rupert',           # Superyacht tenders
    'castoldi',         # Italian jet tenders
    'pascoe',           # UK tenders
    'argos nautic',     # Superyacht tenders
    'sea doo',          # Personal watercraft
    'yamaha',           # PWC and outboards
    'mercury',          # Outboard engines
    'honda marine',     # Outboard engines
    'suzuki marine',    # Outboard engines
    'tohatsu',          # Outboard engines
    'evinrude',         # Outboard engines (discontinued)

    # ============= SAFETY EQUIPMENT =============
    'mustang',          # Lifejackets/survival
    'crewsaver',        # UK lifejackets
    'secumar',          # German lifejackets
    'ocean safety',     # Safety equipment
    'baltic',           # Swedish lifejackets
    'survitec',         # Survival equipment
    'revere',           # Life rafts
    'winslow',          # Life rafts
    'givens',           # Life rafts
    'switlik',          # Life rafts
    'plastimo',         # Safety equipment

    # ============= WINDOWS/GLASS =============
    'bofor',            # Swedish marine glass
    'manship',          # Marine windows
    'freeman',          # Marine glazing
    'taylor',           # Taylor Made windows
    'beckson',          # Ports/hatches
    'goiot',            # French hatches
    'lewmar',           # Hatches/portlights (already listed for deck)
    'bomar',            # Hatches

    # ============= INSULATION/INTERIOR =============
    'armacell',         # Insulation
    'armaflex',         # Foam insulation
    'ultralon',         # Decking
    'teak isle',        # Synthetic teak
    'flexiteek',        # Synthetic teak
    'permateek',        # Synthetic teak
    'marinedeck',       # Synthetic decking
    'amtico',           # Marine flooring

    # ============= BATTERIES =============
    'trojan',           # Deep cycle batteries
    'lifeline',         # AGM batteries
    'optima',           # Spiral cell batteries
    'odyssey',          # High performance batteries
    'northstar',        # AGM batteries
    'sonnenschein',     # German batteries
    'deka',             # Marine batteries
    'exide',            # Batteries
    'interstate',       # Batteries
    'firefly',          # Carbon foam batteries
    'relion',           # Lithium batteries
    'battleborn',       # Lithium batteries
    'super b',          # Lithium batteries

    # ============= CABLES/WIRING =============
    'ancor',            # Marine wire
    'pacer',            # Marine wire
    'sea wire',         # Marine wire
    'alpha wire',       # Industrial wire
    'lapp',             # German cables
    'belden',           # Signal cables

    # ============= SEALS/BEARINGS =============
    'cutless',          # Shaft bearings
    'duramax',          # Shaft bearings
    'johnson duramax',  # Cutlass bearings
    'thordon',          # Polymer bearings
    'skf',              # Swedish bearings
    'nsk',              # Japanese bearings
    'fag',              # German bearings (Schaeffler)
    'timken',           # US bearings
    'tides marine',     # Shaft seals
    'pss',              # Packless shaft seals

    # ============= FUEL SYSTEMS =============
    'alfa laval',       # Separators/purifiers
    'westfalia',        # Separators (GEA)
    'facet',            # Fuel pumps
    'walbro',           # Fuel pumps
    'carter',           # Fuel pumps
    'fuelguard',        # Fuel systems
    'hy-pro',           # Fuel filtration
    'separ',            # Fuel/water separators
    'vetus',            # Fuel tanks/systems (already listed)
    'moeller',          # Fuel tanks

    # ============= OILY WATER/ENVIRONMENTAL =============
    'victor marine',    # Oily water separators
    'rwo',              # Marine environmental
    'puretech',         # Water treatment
    'marinefloc',       # Treatment systems
    'dvz',              # German separators
    'detegasa',         # Spanish environmental equipment

    # ============= FIRE SUPPRESSION =============
    'novec',            # 3M clean agent
    'inergen',          # Inert gas system
    'argonite',         # Fire suppression
    'sapphire',         # Clean agent system
    'ansul',            # Fire suppression
    'kidde',            # Fire systems (already listed)
    'viking',           # Fire/safety (already listed)

    # ============= PLC/AUTOMATION =============
    'siemens',          # German automation
    'allen bradley',    # Rockwell automation
    'schneider',        # French automation
    'omron',            # Japanese automation
    'mitsubishi electric', # Automation (different from engines)
    'abb',              # Swiss automation
    'honeywell',        # Controls
    'danaher',          # Industrial controls
    'esa',              # Italian automation
    'deif',             # Danish genset controllers
    'comap',            # Czech genset controllers
    'deep sea',         # DSE controllers
    'woodward',         # Engine controls

    # =============================================================================
    # MODERN YACHT SYSTEMS - IT/AV/SMART (NOT JUST ENGINE ROOM!)
    # =============================================================================

    # ============= IT/NETWORK INFRASTRUCTURE =============
    'cisco',            # Enterprise networking
    'meraki',           # Cisco cloud-managed
    'ubiquiti',         # UniFi networking
    'unifi',            # Ubiquiti brand
    'netgear',          # Networking
    'draytek',          # Multi-WAN routers
    'peplink',          # Cellular bonding/SD-WAN
    'pepwave',          # Peplink marine
    'mikrotik',         # Advanced routers
    'ruckus',           # Enterprise WiFi
    'aruba',            # HPE WiFi
    'fortinet',         # Firewalls
    'sonicwall',        # Firewalls
    'synology',         # NAS storage
    'qnap',             # NAS storage
    'dell',             # Servers/computers
    'hp',               # Servers/computers
    'hpe',              # HP Enterprise
    'lenovo',           # Servers
    'apple',            # Macs/iPads
    'microsoft',        # Windows/Surface

    # ============= AV CONTROL SYSTEMS =============
    'savant',           # Smart yacht
    'control4',         # Home automation
    'rti',              # Remote Technologies
    'urc',              # Universal Remote
    'elan',             # Home automation
    'russound',         # Multiroom audio
    'autonomic',        # Music streaming
    'snap one',         # AV distribution
    'just add power',   # AV over IP
    'atlona',           # AV connectivity
    'extron',           # Pro AV
    'kramer',           # AV switching
    'qsc',              # Pro audio
    'biamp',            # Audio DSP

    # ============= SPEAKERS/AUDIO =============
    'bowers wilkins',   # B&W speakers
    'kef',              # British speakers
    'sonance',          # Marine speakers
    'origin acoustics', # Architectural speakers
    'definitive',       # Speakers
    'paradigm',         # Speakers
    'focal',            # French speakers
    'dynaudio',         # Danish speakers
    'jbl',              # Pro audio
    'harman kardon',    # Audio
    'denon',            # Receivers
    'marantz',          # Hi-fi
    'mcintosh',         # High-end audio
    'naim',             # British hi-fi
    'devialet',         # French audio

    # ============= VIDEO/DISPLAYS =============
    'panasonic',        # Displays
    'barco',            # Projectors
    'christie',         # Projectors
    'epson',            # Projectors
    'screen innovations', # Screens
    'stewart',          # Screens
    'kaleidescape',     # Media servers
    'roku',             # Streaming
    'apple tv',         # Streaming

    # ============= LIGHTING CONTROL =============
    'philips hue',      # Smart lighting
    'loxone',           # Building automation
    'knx',              # Building automation
    'dynalite',         # Lighting control
    'helvar',           # Lighting control
    'eldoled',          # LED drivers
    'mean well',        # LED power
    'osram',            # Lighting
    'legrand',          # Electrical

    # ============= SHADES/BLINDS =============
    'hunter douglas',   # Blinds
    'somfy',            # Shade motors
    'silent gliss',     # Curtain tracks
    'mechoshade',       # Shades
    'qmotion',          # Motorized shades
    'draper',           # Screens/shades

    # ============= CONNECTIVITY/SATCOM =============
    'starlink',         # SpaceX internet - CRITICAL!
    'oneweb',           # LEO satellite
    'ses',              # Satellite
    'eutelsat',         # Satellite
    'marlink',          # Maritime connectivity
    'speedcast',        # Maritime VSAT
    'kymeta',           # Flat panel antenna
    'e3 systems',       # Maritime IT
    'gtmaritime',       # Maritime IT
    'navarino',         # Maritime IT

    # ============= BRIDGE/NAVIGATION MODERN =============
    'sperry marine',    # Navigation
    'raytheon',         # Navigation
    'anschutz',         # German navigation
    'kongsberg',        # Norwegian systems
    'transas',          # Now Wärtsilä Voyage
    'kelvin hughes',    # Radar
    'sam electronics',  # German nav
    'danelec',          # VDR/ECDIS
    'consilium',        # Safety systems
    'böning',           # German monitoring
    'boning',           # Böning without umlaut
    'hatteland',        # Maritime displays
    'zenitel',          # Intercom/PA

    # ============= YACHT MANAGEMENT SYSTEMS =============
    'palladium',        # Palladium Technologies
    'idea',             # IDEA yacht systems
    'besenzoni',        # Italian equipment
    'opacmare',         # Italian equipment
    'nautilus',         # Yacht monitoring
    'cathelco',         # ICCP/MGPS

    # ============= SECURITY/CCTV =============
    'hikvision',        # CCTV
    'dahua',            # CCTV
    'axis',             # Network cameras
    'hanwha',           # Cameras
    'milestone',        # VMS software
    'genetec',          # VMS software
    'avigilon',         # Security
    'mobotix',          # German cameras
    'verkada',          # Cloud cameras

    # ============= ACCESS CONTROL =============
    'assa abloy',       # Door locks
    'salto',            # Access control
    'dormakaba',        # Door systems
    'schlage',          # Locks
    'yale',             # Locks
    'hid',              # Access cards
    'paxton',           # Access control

    # ============= GALLEY EQUIPMENT =============
    'miele',            # Premium appliances
    'gaggenau',         # Luxury appliances
    'sub-zero',         # Refrigeration
    'wolf',             # Cooking
    'la cornue',        # French ranges
    'thermador',        # Appliances
    'viking range',     # Cooking (not life rafts)
    'smeg',             # Italian appliances
    'aga',              # British ranges
    'rational',         # Combi ovens
    'true',             # Commercial refrigeration
    'hoshizaki',        # Ice machines
    'scotsman',         # Ice machines
    'franke',           # Sinks/coffee
    'miele marine',     # Marine appliances

    # ============= LAUNDRY =============
    'electrolux marine', # Marine laundry
    'primus',           # Commercial laundry
    'speed queen',      # Commercial laundry
    'ipso',             # Commercial laundry

    # ============= SMART GLASS =============
    'gauzy',            # Smart glass
    'halio',            # Electrochromic glass
    'view glass',       # Smart windows
    'sage glass',       # Dynamic glass
    'pilkington',       # Marine glass

    # ============= WATER TOYS/RECREATION =============
    'seabob',           # Underwater scooter
    'cayago',           # Seabob maker
    'sublue',           # Underwater scooter
    'jetsurf',          # Motorized surfboard
    'lift foil',        # eFoil
    'fliteboard',       # eFoil
    'awake',            # Electric surfboard
    'radinn',           # Electric surfboard
    'flyboard',         # Zapata
    'zapata',           # Flyboard
    'jobe',             # Watersports
    'ronix',            # Wakeboards
    'mastercraft',      # Wakeboard boats
    'nautique',         # Ski boats
    'funair',           # Yacht inflatables
    'aquaglide',        # Inflatables
    'nautibuoy',        # Floating platforms

    # ============= DIVING =============
    'bauer',            # Dive compressors
    'coltri',           # Dive compressors
    'nuvair',           # Dive compressors
    'brownie',          # Hookah diving
    'u-boat worx',      # Submersibles
    'triton',           # Submersibles

    # ============= MEDICAL =============
    'zoll',             # Defibrillators
    'laerdal',          # Medical training
    'cardiac science',  # AEDs
    'physio-control',   # Defibrillators
    'masimo',           # Pulse oximetry

    # ============= CREW COMMUNICATION =============
    'motorola',         # Radios
    'hytera',           # Radios
    'kenwood',          # Radios
    'david clark',      # Headsets
    'peltor',           # Hearing protection
    'eartec',           # Wireless headsets

    # ============= COATINGS =============
    'akzonobel',        # Parent company
    'alexseal',         # Yacht paint
    'ppg',              # Coatings
    'sikkens',          # Yacht coatings

    # ============= YACHT BUILDERS =============
    'lurssen',          # German megayachts
    'feadship',         # Dutch superyachts
    'benetti',          # Italian yachts
    'amels',            # Dutch superyachts
    'oceanco',          # Dutch megayachts
    'heesen',           # Dutch yachts
    'sanlorenzo',       # Italian yachts
    'ferretti',         # Italian group
    'riva',             # Italian sport
    'princess',         # British yachts
    'sunseeker',        # British yachts
    'azimut',           # Italian yachts
    'baglietto',        # Italian yachts
    'crn',              # Ferretti megayachts
    'westport',         # US yachts
    'christensen',      # US megayachts
    'nordhavn',         # US explorer
    'damen',            # Dutch shipyard
    'abeking',          # German shipyard
    'nobiskrug',        # German megayachts
    'perini navi',      # Italian sailing
    'royal huisman',    # Dutch sailing
    'vitters',          # Dutch sailing
    'swan',             # Nautor's Swan
    'oyster',           # British sailing
    'beneteau',         # French yachts
    'jeanneau',         # French sailing
    'lagoon',           # Catamarans
    'fountaine pajot',  # Catamarans
    'sunreef',          # Polish catamarans

    # ============= CLASS SOCIETIES/CERTIFICATION =============
    'lloyds',           # Lloyd's Register
    'lloyd register',   # Lloyd's (alt spelling)
    'dnv',              # DNV GL
    'dnv gl',           # DNV GL (full)
    'bureau veritas',   # French class
    'abs',              # American Bureau of Shipping
    'rina',             # Italian register
    'class nk',         # Japanese class
    'ccs',              # China Classification
    'korean register',  # Korean class
    'russian maritime', # Russian class
    'mca',              # Maritime Coastguard Agency (UK)
    'uscg',             # US Coast Guard
    'solas',            # Safety of Life at Sea
    'marpol',           # Marine pollution regulations
    'ism',              # International Safety Management
    'isps',             # International Ship/Port Security
    'psc',              # Port State Control

    # ============= YACHT MANAGEMENT COMPANIES =============
    'burgess',          # Yacht management
    'hill robinson',    # Yacht management
    'iyc',              # International Yacht Company
    'fraser',           # Yacht services
    'camper nicholsons',# Yacht management
    'edmiston',         # Yacht services
    'ocean independence',# Yacht management
    'northrop johnson', # Yacht services
    'denison',          # Yacht services
    'worth avenue',     # Yacht services
    'y.co',             # Yacht management
    'yacht cloud',      # Management software
    'harbour pilot',    # Management software
    'spectec',          # AMOS maintenance software
    'amos',             # Maintenance software

    # ============= MARINE SURVEYORS/INSPECTIONS =============
    'nace',             # Corrosion certification
    'cci',              # Certified coating inspector
    'ultrasonic',       # UT thickness gauging
    'mpi',              # Magnetic particle inspection
    'ndt',              # Non-destructive testing
    'dye penetrant',    # PT inspection

    # ============= ADDITIONAL NAVIGATION/AUTOPILOT =============
    'mhu',              # Navico (Simrad) MHU
    'b&g zeus',         # B&G chartplotter
    'b&g triton',       # B&G instruments
    'maretron',         # NMEA 2000 displays
    'actisense',        # NMEA converters
    'yacht devices',    # NMEA interfaces
    'digital yacht',    # Marine electronics
    'vesper',           # AIS/VHF
    'em-trak',          # AIS transponders
    'si-tex',           # Marine electronics
    'standard horizon', # VHF radios
    'ship mate',        # Navigation apps
    'navionics',        # Charts (already listed)
    'nobeltec',         # Navigation software
    'maxsea',           # Navigation software
    'rose point',       # Coastal Explorer
    'opencpn',          # Navigation software
    'expedition',       # Weather routing

    # ============= WEATHER/ROUTING =============
    'predict wind',     # Weather/routing
    'predictwind',      # PredictWind (alt)
    'weather routing',  # Generic
    'squid sailing',    # Weather
    'theyr',            # Weather
    'windguru',         # Weather
    'windy',            # Weather app
    'passageweather',   # Weather
    'ugrib',            # Grib files

    # ============= ADDITIONAL DECK HARDWARE =============
    'seldén',           # Rig/mast
    'z spars',          # Mast/rig
    'sparcraft',        # Spars
    'ubi maior',        # Furling systems
    'facnor',           # Furling systems
    'profurl',          # Furling
    'reckmann',         # Hydraulic furling
    'bamar',            # Hydraulic systems
    'barbarossa',       # Deck cranes
    'opacmare',         # Deck equipment (already listed)
    'mar co',           # Davits
    'd-i davit',        # Davit International
    'exit engineering', # Cranes/davits
    'palfinger',        # Deck cranes
    'heila',            # Deck cranes
    'effer',            # Cranes
    'fassi',            # Cranes
    'hiab',             # Cranes
    'macgregor',        # Deck equipment

    # ============= ADDITIONAL TENDER/OUTBOARD BRANDS =============
    'asis',             # Military RIBs
    'safehavenyachts',  # Tenders
    'technohull',       # Greek RIBs
    'sacs',             # Italian RIBs
    'revenger',         # Italian RIBs
    'capelli',          # Italian RIBs
    'lomac',            # Italian RIBs
    'joker boat',       # Italian RIBs
    'nuova jolly',      # Italian RIBs
    'pirelli',          # Pirelli boats
    'zar formenti',     # Italian RIBs
    'scanner',          # Italian RIBs
    'mar-co',           # Italian RIBs
    'marlin',           # RIBs
    'osprey',           # UK RIBs
    'humber',           # UK RIBs
    'ring powercraft',  # Swedish RIBs
    'grand',            # Turkish RIBs
    'nimbus',           # Swedish boats
    'axopar',           # Finnish boats
    'iguana yachts',    # Amphibious tenders
    'sealegs',          # Amphibious boats

    # ============= OUTBOARD ENGINE BRANDS =============
    'torqeedo',         # Electric outboards
    'elco',             # Electric motors
    'epropulsion',      # Electric outboards
    'minn kota',        # Electric trolling
    'motorguide',       # Electric trolling
    'mariner',          # Outboards (Mercury)
    'parsun',           # Chinese outboards
    'selva',            # Italian outboards
    'hidea',            # Chinese outboards
    'hangkai',          # Chinese outboards

    # ============= ADDITIONAL HYDRAULIC BRANDS =============
    'bucher hydraulics',# Swiss hydraulics
    'casappa',          # Italian pumps
    'salami',           # Italian hydraulics
    'berarma',          # Italian vane pumps
    'atos',             # Italian hydraulics
    'moog',             # Servo valves
    'sun hydraulics',   # Cartridge valves
    'hawe',             # German hydraulics
    'linde',            # Hydraulic motors
    'poclain',          # Hydraulic motors
    'staffa',           # Hydraulic motors
    'hagglunds',        # Hydraulic motors
    'sauer danfoss',    # Hydraulics
    'nachi',            # Japanese hydraulics
    'daikin',           # Japanese hydraulics
    'yuken',            # Japanese hydraulics
    'prince',           # US hydraulics
    'cross',            # US hydraulics

    # ============= COATING/PAINT SPECIALIZED =============
    'epifanes',         # Dutch varnish
    'sikkens cetol',    # Wood finish
    'awlfair',          # Fairing compound
    'awlprep',          # Surface prep
    'perfection',       # Interlux topcoat
    'brightside',       # Interlux paint
    'micron',           # Interlux antifouling
    'interprotect',     # Barrier coat
    'gelshield',        # Barrier coat
    'primocon',         # Primer
    'watertite',        # Fairing
    'total boat',       # Marine coatings
    'west system',      # Epoxy
    'system three',     # Epoxy
    'mas epoxies',      # Epoxy
    'pro-set',          # Epoxy

    # ============= ELECTRONICS/SENSORS =============
    'seika',            # German sensors
    'marel',            # Marine sensors
    'gems sensors',     # Level sensors
    'wika',             # Pressure gauges
    'dwyer',            # Instruments
    'kobold',           # Flow sensors
    'pt100',            # Temp sensor type
    'thermocouple',     # Temp sensor type
    'strain gauge',     # Load cells
    'loadcell',         # Load measurement
    'lvdt',             # Position sensors
    'encoder',          # Rotary encoder
    'potentiometer',    # Position
    'pressure transmitter', # Pressure sensor
    'flowmeter',        # Flow measurement

    # ============= MARINE SEALANTS/ADHESIVES =============
    'sikaflex',         # Sika sealant
    'sika',             # Sika brand
    '3m marine',        # 3M marine products
    '5200',             # 3M 5200 sealant
    '4200',             # 3M 4200 sealant
    'lifecaulk',        # BoatLife sealant
    'life caulk',       # BoatLife (alt)
    'dolfinite',        # Bedding compound
    'boatlife',         # Marine sealants
    'sudbury',          # Marine products
    'tef-gel',          # Anti-seize
    'lanocote',         # Corrosion inhibitor
    'lanolin',          # Preservation
    'loctite',          # Thread locker
    'permatex',         # Sealants

    # ============= INSULATION/SOUNDPROOFING =============
    'rockwool',         # Mineral wool
    'mineral wool',     # Insulation type
    'acoustic foam',    # Sound deadening
    'mass loaded vinyl',# Sound barrier
    'dynamat',          # Sound deadening
    'soundown',         # Marine acoustic
    'halyard',          # Marine insulation
    'k-flex',           # Insulation
    'aeroflex',         # Insulation
    'superlon',         # Insulation

    # ============= ANCHOR CHAIN/RODE =============
    'acco',             # Chain
    'titan',            # Anchor chain
    'lewmar chain',     # Chain
    'short link',       # Chain type
    'bbb chain',        # Grade
    'ht chain',         # High test
    'g4 chain',         # Grade 4
    'stainless chain',  # SS chain
    'anchor rode',      # Generic
    'snubber',          # Chain snubber
    'bridle',           # Anchor bridle
    'swivel',           # Anchor swivel

    # ============= FENDERS/DOCKING =============
    'polyform',         # Fenders
    'taylor made',      # Fenders
    'aere',             # Fenders
    'yokohama',         # Commercial fenders
    'supafend',         # Inflatable fenders
    'fendequip',        # Fender systems
    'dock edge',        # Dock products
    'mooring arm',      # Yacht mooring
    'seijsener',        # Mooring systems

    # ============= LINES/ROPE =============
    'marlow',           # UK rope
    'liros',            # German rope
    'gleistein',        # German rope
    'samson',           # US rope
    'new england ropes',# US rope
    'yale cordage',     # US rope
    'english braids',   # UK rope
    'robline',          # Rope
    'dyneema',          # UHMWPE fiber
    'spectra',          # HMPE fiber (already listed as watermaker)
    'kevlar',           # Aramid fiber
    'technora',         # Aramid fiber
    'vectran',          # LCP fiber

    # ============= RIGGING HARDWARE =============
    'sta-lok',          # Swage terminals
    'norseman',         # Swage terminals
    'blue wave',        # Rigging hardware
    'petersen',         # Stainless fittings
    'hayn',             # Rigging hardware
    'c-sherman johnson',# Rigging
    'hi-mod',           # Carbon rigging
    'future fibres',    # Carbon rigging
    'carbo',            # Carbon products
    'southern spars',   # Mast/rigging
    'hall spars',       # Mast/rigging

    # ============= ADDITIONAL GALLEY/BAR =============
    'breville',         # Small appliances
    'kitchenaid',       # Appliances
    'vitamix',          # Blenders
    'nespresso',        # Coffee
    'la marzocco',      # Coffee machines
    'rocket espresso',  # Espresso
    'u-line',           # Undercounter refrigeration
    'perlick',          # Bar equipment
    'marvel',           # Wine coolers
    'wine cooler',      # Generic
    'ice maker',        # Generic
    'wine captain',     # Wine storage
    'eurocave',         # Wine cabinets

    # ============= LAUNDRY/HOUSEKEEPING =============
    'dyson',            # Vacuum
    'miele vacuum',     # Vacuum
    'nilfisk',          # Commercial vacuum
    'karcher',          # Cleaning equipment
    'numatic',          # Henry vacuum
    'henry',            # Vacuum brand
    'hetty',            # Vacuum brand
    'steamer',          # Garment steamer
    'jiffy steamer',    # Steamers
    'rowenta',          # Irons/steamers

    # ============= ADDITIONAL WATER TOYS =============
    'pedalos',          # Paddle boats
    'hobie cat',        # Small cats
    'laser',            # Sailing dinghy
    'optimist',         # Youth sailing
    'rs sailing',       # Sailing dinghies
    'topper',           # Sailing dinghy
    'waszp',            # Foiling dinghy
    'moth',             # Foiling moth
    'nacra',            # Beach cats
    'dart catamaran',   # Beach cats
    'prindle',          # Beach cats
    'sup',              # Stand up paddle
    'standup paddle',   # SUP full name
    'inflatable kayak', # Kayak type
    'sea eagle',        # Inflatables
    'advanced elements',# Inflatables
    'red paddle',       # SUP brand
    'starboard',        # SUP/windsurf
    'fanatic',          # SUP/windsurf
    'naish',            # Kiteboarding
    'cabrinha',         # Kiteboarding
    'ozone',            # Kites
    'duotone',          # Kites
    'core kiteboarding',# Kites

    # ============= GYM/FITNESS =============
    'technogym',        # Gym equipment
    'life fitness',     # Gym equipment
    'peloton',          # Exercise bikes
    'concept2',         # Rowing machines
    'precor',           # Gym equipment
    'matrix fitness',   # Gym equipment
    'hydrow',           # Rowing

    # ============= SPA/WELLNESS =============
    'jacuzzi',          # Hot tubs
    'hot spring',       # Hot tubs
    'coast spas',       # Hot tubs
    'endless pools',    # Swim spa
    'swimex',           # Swim spa
    'infrared sauna',   # Sauna type
    'harvia',           # Finnish sauna
    'helo',             # Sauna
    'steam shower',     # Steam
    'mr steam',         # Steam generators
    'thermasol',        # Steam
    'kohler spa',       # Spa products

    # ============= INTERIOR FABRICS/MATERIALS =============
    'sunbrella',        # Outdoor fabrics
    'phifertex',        # Mesh fabrics
    'batyline',         # Sling fabric
    'silvertex',        # Vinyl
    'ultraleather',     # Synthetic leather
    'alcantara',        # Suede-like
    'majilite',         # Marine vinyl
    'marine vinyl',     # Generic
    'stamoid',          # Coated fabric
    'weblon',           # PVC fabric
    'serge ferrari',    # Technical textiles
    'dickson',          # Awning fabrics
    'marine grade',     # Generic qualifier
    'stainmaster',      # Carpet
    'karastan',         # Rugs
    'stark carpet',     # Luxury carpet
    'tai ping',         # Luxury carpet
    'jacaranda',        # Natural carpets

    # ============= WINDOW TREATMENTS =============
    'sunbrella shade',  # Shade fabric
    'phifer',           # Screen fabrics
    'marine shade',     # Generic
    'strataglass',      # Clear vinyl
    'eisenglass',       # Clear vinyl
    "o'sea",            # Clear enclosures
    'oseaglass',        # Clear vinyl
    'crystal clear',    # Vinyl type
    'press polished',   # Vinyl finish

    # ============= MATTRESS/BEDDING =============
    'tempur',           # Memory foam
    'tempurpedic',      # Mattress
    'sealy',            # Mattress
    'simmons',          # Mattress
    'serta',            # Mattress
    'sleep number',     # Adjustable
    'frette',           # Luxury linens
    'sferra',           # Luxury linens
    'matouk',           # Linens
    'pratesi',          # Italian linens
    'yves delorme',     # French linens
    'peacock alley',    # Linens
    'brooklinen',       # Bedding

    # ============= MEDICAL/FIRST AID =============
    'ocean medical',    # Marine first aid
    'marines', # First aid
    'thomas fetterman', # Medical kits
    'medical sea pak',  # Marine medical
    'adventure medical',# First aid kits
    'first aid only',   # First aid
    'st john ambulance',# First aid training
    'stryker',          # Medical equipment
    'philips aed',      # Defibrillators
    'defibtech',        # AEDs
    'med pak',          # Medical kits
    'emergency oxygen', # O2 equipment
    'dan',              # Divers Alert Network
    'remote medical',   # Telemedicine
    'medaire',          # Yacht medical
    'msos',             # Maritime medical
    'yacht aid',        # Yacht first aid

    # ============= CREW UNIFORMS/WEAR =============
    'crew clothing',    # Generic
    'henri lloyd',      # Sailing wear
    'musto',            # Marine clothing
    'gill',             # Sailing gear
    'helly hansen',     # Marine clothing
    'zhik',             # Sailing apparel
    'slam',             # Italian sailing
    'north sails',      # Sailing brand
    'dubarry',          # Deck shoes
    'sperry',           # Deck shoes
    'sebago',           # Deck shoes
    'xtratuf',          # Deck boots
    'grundens',         # Foul weather
    'guy cotten',       # French oilskins
    'stormline',        # Foul weather
    'douglas gill',     # Foul weather
    'ocean safety suit',# Survival suits

    # ============= TOOLS/WORKSHOP =============
    'snap-on',          # Professional tools
    'snap on',          # Snap-On (alt)
    'mac tools',        # Professional tools
    'matco',            # Professional tools
    'stanley',          # Hand tools
    'dewalt',           # Power tools
    'milwaukee',        # Power tools
    'makita',           # Power tools
    'festool',          # Premium power tools
    'bosch tools',      # Power tools
    'hilti',            # Professional tools
    'dremel',           # Rotary tools
    'fluke',            # Test equipment
    'megger',           # Insulation testers
    'multimeter',       # Generic
    'oscilloscope',     # Test equipment
    'clamp meter',      # Electrical test
    'infrared thermometer', # Temperature
    'flir',             # Thermal imaging
    'testo',            # Test instruments
    'amprobe',          # Meters
    'klein tools',      # Electrical tools
    'knipex',           # German pliers
    'wiha',             # German tools
    'wera',             # German tools
    'hazet',            # German tools
    'stahlwille',       # German tools
    'gedore',           # German tools
    'bahco',            # Swedish tools
    'facom',            # French tools

    # ============= CLEANING PRODUCTS =============
    'starbrite',        # Marine cleaning
    'star brite',       # Star Brite (alt)
    'meguiars',         # Marine polish
    'collinite',        # Marine wax
    'shurhold',         # Cleaning tools
    'swobbit',          # Cleaning tools
    'imar',             # Vinyl cleaner
    'aurora',           # Teak cleaner
    'te-ka',            # Teak treatment
    'semco',            # Teak sealer
    'deks olje',        # Teak oil
    'cetol marine',     # Wood finish
    'boat wash',        # Generic
    'hull cleaner',     # Generic
    'on & off',         # Hull cleaner
    'mary kate',        # Marine chemicals
    'orpine',           # Cleaning
    'sudbury yacht',    # Marine chemicals
    'bio-kleen',        # Eco cleaning
    'simple green',     # Cleaning
    '303 protectant',   # UV protection
    '303 aerospace',    # Protectant

    # ============= LUBRICANTS/FLUIDS =============
    'shell marine',     # Marine lubricants
    'mobil delvac',     # Heavy duty oil
    'chevron delo',     # Diesel oil
    'castrol',          # Lubricants
    'total lubmarine',  # Marine oils
    'gulf',             # Marine oils
    'pennzoil',         # Oil
    'valvoline',        # Oil
    'quicksilver',      # Mercury oil
    'yamalube',         # Yamaha oil
    'evinrude xd',      # Outboard oil
    'lucas oil',        # Additives
    'seafoam',          # Fuel treatment
    'stabil',           # Fuel stabilizer
    'startron',         # Fuel treatment
    'biobor',           # Diesel biocide
    'power service',    # Diesel treatment
    'pri-g',            # Fuel treatment
    'wd-40',            # Lubricant
    'lanox',            # Anti-corrosion
    'corrosion x',      # Corrosion inhibitor
    'boeshield',        # Corrosion protection
    'crc',              # Lubricants
    'lps',              # Lubricants
    'lubriplate',       # Grease
    'super lube',       # Lubricant
    'marine grease',    # Generic

    # ============= ANODES/CORROSION =============
    'zinc anode',       # Corrosion protection
    'aluminum anode',   # Corrosion protection
    'magnesium anode',  # Freshwater anode
    'zincs',            # Generic
    'martyr',           # Anode brand
    'camp',             # Anode brand
    'performance metals',# Anodes
    'sea shield',       # Anodes
    'tecnoseal',        # Anodes
    'mercruiser anode', # OEM anodes
    'volvo anode',      # OEM anodes
    'iccp',             # Impressed current
    'mgps',             # Anti-fouling

    # ============= DOCUMENTATION/SOFTWARE =============
    'autocad',          # CAD software
    'rhinoceros',       # 3D modeling
    'solidworks',       # CAD
    'napa',             # Ship design
    'maxsurf',          # Hull design
    'shipconstructor',  # Ship design
    'aveva',            # Marine software
    'cadmatic',         # Ship design
    'ssi',              # Shipbuilding software
    'tribon',           # Ship design

    # ============= SHIPPING/LOGISTICS =============
    'dhl',              # Courier
    'fedex',            # Courier
    'ups',              # Courier
    'loomis',           # Secure shipping
    'peters shipbrokers',# Ship parts
    'ism parts',        # Marine parts
    'ship spares',      # Parts supplier
    'impa',             # Marine purchasing
    'issa',             # Ship suppliers assoc
    'shipserv',         # Marine marketplace

    # ============= CHARTER/BROKERAGE =============
    'charter guest',    # Charter terminology
    'apa',              # Advance Provisioning Allowance
    'cipa',             # Charter Insurance
    'myba',             # Med Yacht Brokers Assn
    'cyba',             # Charter Yacht Brokers Assn
    'ecpy',             # Charter standards
    'igy',              # Island Global Yachting (marinas)
    'camper & nicholsons', # Charter/brokerage
    'berthon',          # Yacht sales
    'ancasta',          # Yacht sales
    'williams marine',  # Yacht sales

    # ============= CREW TRAINING/CERTIFICATION =============
    'stcw',             # Maritime training
    'uscg license',     # US license
    'mca certificate',  # UK certification
    'rya',              # Royal Yachting Association
    'yachtmaster',      # RYA qualification
    'eng1',             # UK medical
    'flag state',       # Registration
    'pya',              # Professional Yachts Assn
    'acrew',            # Crew training
    'uksa',             # UK Sailing Academy
    'warsash',          # Maritime training
    'mpi training',     # Training provider

    # ============= REFIT YARDS/SHIPYARDS =============
    'mb92',             # Barcelona refit
    'compositeworks',   # La Ciotat
    'la ciotat',        # Refit yard location
    'monaco marine',    # Refit yard
    'stp',              # Palma shipyard
    'pinmar',           # Palma paint
    'rolling stock',    # Refit services
    'pure superyacht',  # Refit services
    'huisfit',          # Refit yard
    'balk shipyard',    # Dutch refit
    'pendennis',        # UK refit
    'devonport',        # UK yard
    'lloyd werft',      # German yard
    'german dry dock',  # German refit
    'gulf craft',       # UAE builder
    'oceania marine',   # NZ yard
    'auckland marine',  # NZ yard
    'rivergate',        # Brisbane yard
    'lauderdale marine',# Florida yard
    'derecktor',        # US yard
    'rybovich',         # US yard
    'safe harbor',      # Marina group

    # ============= INSURANCE =============
    'pantaenius',       # Yacht insurance
    'gowrie',           # Marine insurance
    'lloyd open form',  # Salvage
    'lof',              # Lloyd's Open Form
    'general average',  # Maritime law
    'p&i',              # Protection & Indemnity
    'h&m',              # Hull & Machinery
    'loss of hire',     # Insurance type
    'mou',              # Memorandum of Understanding

    # ============= COMMON LOCATIONS/PORTS =============
    'port hercules',    # Monaco
    'monaco',           # Destination
    'antibes',          # French Riviera
    'port vauban',      # Antibes marina
    'fontvieille',      # Monaco marina
    'port canto',       # Cannes
    'palma',            # Mallorca
    'ibiza',            # Balearics
    'marina di stabia', # Italy
    'porto cervo',      # Sardinia
    'genoa',            # Italy
    'la spezia',        # Italy
    'naples',           # Italy
    'capri',            # Italy
    'aeolian',          # Islands
    'sicily',           # Italy
    'malta',            # Mediterranean
    'croatia',          # Cruising ground
    'montenegro',       # Cruising ground
    'greece',           # Cruising ground
    'turkey',           # Cruising ground
    'caribbean',        # Cruising ground
    'bahamas',          # Destination
    'virgin islands',   # Destination
    'st barths',        # St Barthélemy
    'st martin',        # Destination
    'antigua',          # Destination
    'newport',          # Rhode Island
    'fort lauderdale',  # Florida
    'palm beach',       # Florida
    'miami',            # Florida
    'key west',         # Florida
    'caribbean',        # Region
    'maldives',         # Destination
    'seychelles',       # Destination
    'thailand',         # Destination
    'phuket',           # Thailand
    'bali',             # Indonesia
    'fiji',             # South Pacific
    'tahiti',           # French Polynesia
    'new zealand',      # Cruising ground
    'australia',        # Cruising ground
    'sydney',           # Australia
    'auckland',         # New Zealand
}

# CORE EQUIPMENT - Essential equipment types
# These must always be recognized regardless of context
CORE_EQUIPMENT = {
    # ============= EQUIPMENT ABBREVIATIONS =============
    # Common yacht equipment naming conventions (critical for search)
    'me1', 'me2', 'me3',        # Main Engine 1/2/3
    'main engine 1', 'main engine 2',
    'dg1', 'dg2', 'dg3',        # Diesel Generator 1/2/3
    'gen1', 'gen2', 'gen3',     # Generator 1/2/3
    'generator 1', 'generator 2',
    'aux1', 'aux2',             # Auxiliary 1/2
    'bt', 'st',                 # Bow/Stern Thruster
    'bt1', 'bt2', 'st1', 'st2', # Numbered thrusters
    'ac1', 'ac2', 'ac3',        # AC Unit 1/2/3
    'stbd', 'port',             # Starboard/Port sides
    'port main', 'stbd main',   # Port/Starboard main engine
    'port generator', 'stbd generator',

    # ============= PROPULSION =============
    'engine',           # Generic engine reference
    'main engine',      # Primary propulsion engine
    'generator',        # Electrical generation
    'genset',           # Generator set (engine + alternator)
    'thruster',         # Generic thruster
    'bow thruster',     # Forward maneuvering thruster
    'stern thruster',   # Aft maneuvering thruster
    'propeller',        # Propulsion propeller
    'shaft',            # Propeller shaft
    'gearbox',          # Transmission gearbox
    'transmission',     # Power transmission
    'turbocharger',     # Engine turbocharger
    'turbo',            # Abbreviation for turbocharger
    'intercooler',      # Charge air cooler
    'aftercooler',      # Same as intercooler

    # ============= NAVIGATION =============
    'radar',            # Radio detection and ranging
    'chartplotter',     # Electronic chart display
    'autopilot',        # Automatic steering
    'gps',              # Global Positioning System
    'vhf',              # VHF radio
    'ais',              # Automatic Identification System
    'compass',          # Magnetic or gyro compass
    'gyro',             # Gyrocompass
    'gyrocompass',      # Full name
    'echo sounder',     # Depth measurement
    'sonar',            # Sound navigation
    'wind instrument',  # Wind speed/direction
    'anemometer',       # Wind speed meter
    'speed log',        # Boat speed measurement
    'depth sounder',    # Depth measurement
    'transducer',       # Sensor (depth, speed, etc.)

    # ============= ELECTRICAL =============
    'battery',          # Single battery
    'batteries',        # Battery bank
    'inverter',         # DC to AC converter
    'charger',          # Battery charger
    'battery charger',  # Full name
    'shore power',      # Dock power connection
    'alternator',       # Engine-driven generator
    'starter',          # Engine starter motor
    'motor',            # Electric motor
    'transformer',      # Voltage transformer

    # ============= WATER SYSTEMS =============
    'watermaker',       # Desalination unit
    'desalinator',      # Same as watermaker
    'reverse osmosis',  # RO system
    'freshwater pump',  # Potable water pump
    'pressure pump',    # Water pressure pump
    'bilge pump',       # Bilge dewatering
    'fire pump',        # Fire fighting pump
    'transfer pump',    # Fuel/water transfer
    'raw water pump',   # Engine cooling (seawater)
    'sea water pump',   # Same as raw water pump
    'cooling pump',     # Engine cooling circuit
    'circulation pump', # Coolant circulation

    # ============= HVAC =============
    'air conditioner',  # AC unit
    'ac unit',          # Abbreviation
    'chiller',          # Chilled water unit
    'compressor',       # AC or refrigeration compressor
    'condenser',        # Heat rejection unit
    'evaporator',       # Heat absorption unit
    'blower',           # Air circulation fan
    'fan',              # Generic fan
    'heater',           # Heating unit
    'boiler',           # Hot water/steam generation

    # ============= DECK =============
    'windlass',         # Anchor winch
    'winch',            # Rope handling winch
    'capstan',          # Vertical winch
    'anchor',           # Ground tackle
    'davit',            # Boat lifting crane
    'crane',            # Deck crane
    'passerelle',       # Boarding ramp
    'gangway',          # Boarding ramp
    'tender',           # Small boat
    'jet ski',          # Personal watercraft
    'dinghy',           # Small boat
    'rib',              # Rigid inflatable boat

    # ============= STABILIZERS =============
    'stabilizer',       # Generic stabilizer
    'gyro stabilizer',  # Gyroscopic stabilizer
    'fin stabilizer',   # Fin-type stabilizer
    'zero speed stabilizer',  # Works at anchor

    # ============= SAFETY =============
    'fire damper',      # Fire containment valve
    'fire extinguisher',# Portable extinguisher
    'life raft',        # Emergency raft
    'lifeboat',         # Emergency boat
    'epirb',            # Emergency beacon
    'smoke detector',   # Fire detection
    'fire alarm',       # Fire detection system
    'co2 system',       # CO2 fire suppression
    'sprinkler',        # Fire sprinkler system

    # ============= TANKS/STORAGE =============
    'fuel tank',        # Fuel storage
    'water tank',       # Potable water storage
    'holding tank',     # Sewage holding
    'black water',      # Sewage tank
    'grey water',       # Waste water tank
    'day tank',         # Engine fuel supply tank
    'header tank',      # Coolant expansion tank
    'expansion tank',   # Same as header tank

    # ============= FILTERS/TREATMENT =============
    'fuel filter',      # Fuel filtration
    'oil filter',       # Lubricating oil filter
    'air filter',       # Intake air filter
    'strainer',         # Debris strainer
    'separator',        # Fuel/water separator
    'polisher',         # Fuel polishing
    'purifier',         # Oil/fuel purifier
    'centrifuge',       # Centrifugal purifier

    # ============= VALVES/FITTINGS =============
    'sea cock',         # Through-hull valve
    'seacock',          # Same as sea cock
    'valve',            # Generic valve
    'solenoid',         # Electromagnetic valve
    'actuator',         # Valve actuator
    'manifold',         # Pipe manifold
}

# CORE PARTS - Essential replacement parts
CORE_PARTS = {
    # Watermaker parts
    'membrane',         # RO membrane

    # Pump parts
    'impeller',         # Pump impeller

    # Sealing
    'seal', 'gasket', 'o-ring', 'oring', 'packing',

    # Rotating parts
    'bearing', 'belt', 'rotor', 'stator', 'armature',

    # Fluid handling
    'hose', 'filter', 'element', 'cartridge',

    # Electrical
    'sensor', 'relay', 'fuse', 'breaker', 'brush', 'diode', 'capacitor', 'resistor',

    # Mechanical
    'thermostat', 'injector', 'nozzle', 'piston', 'ring', 'liner', 'head',

    # Controls
    'switch', 'contactor', 'solenoid', 'actuator', 'cylinder', 'rod',

    # Fittings
    'coupling', 'flange', 'clamp', 'bracket', 'mount',

    # Electronics
    'display', 'screen', 'keypad', 'control panel', 'pcb', 'board', 'module',

    # Acronyms for common parts
    'avr',   # Automatic Voltage Regulator
    'ptu',   # Power Take-off Unit
    'hpu',   # Hydraulic Power Unit
    'vfd',   # Variable Frequency Drive
    'plc',   # Programmable Logic Controller
    'ecu',   # Engine Control Unit
    'ecm',   # Engine Control Module
}

# CORE SYMPTOMS - Common fault symptoms
CORE_SYMPTOMS = {
    # Temperature issues
    'overheating', 'overheat', 'running hot', 'high temp', 'high temperature',
    'engine overheating', 'exhaust temp', 'coolant temp',

    # Pressure issues
    'low oil pressure', 'low pressure', 'high pressure', 'pressure drop',
    'oil pressure', 'fuel pressure', 'boost pressure',

    # Mechanical issues
    'vibration', 'vibrating', 'noise', 'noisy', 'grinding', 'knocking',
    'running rough', 'rough idle', 'misfiring', 'stalling', 'tripping',

    # Fluid issues
    'leak', 'leaking', 'coolant leak', 'oil leak', 'fuel leak', 'water leak',

    # Electrical issues
    'voltage drop', 'no power', 'won\'t start', 'starting issue',

    # General failures
    'failure', 'failed', 'alarm', 'warning', 'error', 'fault', 'malfunction',
    'not working', 'broken', 'stuck', 'seized', 'jammed',

    # Blockages
    'stuck', 'jammed', 'blocked', 'clogged',

    # Deterioration
    'corroded', 'worn', 'damaged', 'cracked', 'broken', 'seized', 'burned', 'burnt',

    # Dangerous conditions
    'smoking', 'sparking',

    # Electrical issues
    'tripping', 'cutting out',

    # Starting problems
    'not starting', 'wont start', 'hard starting',

    # Running problems
    'stalling', 'surging', 'hunting', 'misfiring',

    # Sounds
    'knocking', 'rattling', 'grinding', 'squealing', 'whining', 'humming',

    # Pump issues
    'cavitation', 'aeration',

    # Pressure issues
    'low pressure', 'high pressure',

    # Electrical readings
    'low voltage', 'high temperature',

    # Performance issues
    'no output', 'reduced output', 'intermittent', 'erratic', 'fluctuating',
}

# =============================================================================
# SHOPPING LIST TERMS - Procurement and approval-related entities
# =============================================================================
# CRITICAL: These terms enable fast-path (regex) extraction for shopping list queries
# Without these, shopping list queries route to AI lane (3-4s instead of 60-130ms)
#
# Added: 2026-01-30
# Impact: 25x performance improvement for procurement queries

# Shopping list entity terms
CORE_SHOPPING_LIST_TERMS = {
    'shopping list', 'shopping list item', 'shopping list items',
    'procurement', 'procurement list', 'procurement request',
    'parts request', 'parts order', 'parts list',
    'order list', 'ordering', 'parts ordering',
    'buy list', 'purchase list', 'purchase order',
}

# Approval status terms (contextual: shopping list approval states)
CORE_APPROVAL_STATUSES = {
    'pending', 'approved', 'rejected',
    'under review', 'awaiting approval', 'waiting for approval',
    'candidate', 'draft', 'submitted',
    'needs approval', 'pending approval',
}

# Urgency level terms
CORE_URGENCY_LEVELS = {
    'urgent', 'critical', 'high priority', 'high urgency',
    'asap', 'as soon as possible', 'rush',
    'normal priority', 'normal', 'standard',
    'low priority', 'low urgency', 'routine',
}

# Source type terms
CORE_SOURCE_TYPES = {
    'manual add', 'manually added', 'manual entry',
    'inventory low', 'low inventory', 'inventory alert',
    'work order', 'work order usage', 'from work order',
    'receiving', 'from receiving', 'receiving report',
    'damaged', 'damage report', 'damaged part',
}

# =============================================================================
# INVENTORY LENS - STOCK STATUS TERMS (Added 2026-02-02)
# =============================================================================
# These terms support entity extraction for inventory stock status queries.
# Critical for: stock level monitoring, reorder alerts, inventory management.
#
# Entity type: STOCK_STATUS
# Purpose: Compound phrases that should match BEFORE single-word patterns
#
# Why needed:
# - "critically low" should match as STOCK_STATUS, not "critical" as URGENCY_LEVEL
# - "low stock" should match as compound phrase, not just "stock"
# - "out of stock" should match as status phrase, not individual words

CORE_STOCK_STATUS = {
    # Compound stock status phrases
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
    'stock depleted', 'inventory depleted', 'stock exhausted',
}

# =============================================================================
# CREW LENS - HOURS OF REST COMPLIANCE TERMS (Added 2026-01-31)
# =============================================================================
# These terms support entity extraction for crew hours of rest compliance queries.
# Critical for: compliance monitoring, crew rest violations, warning management.
#
# Entity types:
# - REST_COMPLIANCE: Compliance status (compliant, non-compliant, violations)
# - WARNING_SEVERITY: Severity levels (critical, high, medium, low)
# - WARNING_STATUS: Warning states (active, acknowledged, dismissed)

# Rest compliance terms
CORE_REST_COMPLIANCE = {
    # Compliance states
    'compliant', 'non-compliant', 'non compliant', 'noncompliant',
    'in compliance', 'complies', 'complying',
    # Violations
    'violations', 'violation', 'violating', 'violated',
    'rest violation', 'rest violations', 'compliance violation',
    'non compliant rest', 'non-compliant rest',
    # Natural language paraphrases
    'didn\'t sleep enough', 'didnt sleep enough', 'not enough sleep',
    'not enough rest', 'insufficient rest', 'inadequate rest',
    'crew who didn\'t sleep', 'people not getting enough rest',
    'not getting enough rest', 'didn\'t get enough rest',
}

# Warning severity levels
CORE_WARNING_SEVERITY = {
    # Severity levels
    'critical', 'high', 'medium', 'low',
    # Compound severity terms
    'high severity', 'critical severity', 'medium severity', 'low severity',
    'high priority', 'critical priority', 'medium priority', 'low priority',
    # Compound with "warnings" (user queries)
    'critical warnings', 'high warnings', 'medium warnings', 'low warnings',
    'high severity warnings', 'critical severity warnings',
    # Compound with "alerts" (user queries)
    'critical alerts', 'high alerts', 'medium alerts', 'low alerts',
    # Paraphrases
    'serious', 'severe', 'minor', 'major',
    'important', 'urgent',
}

# Warning status terms
CORE_WARNING_STATUS = {
    # Status states
    'active', 'acknowledged', 'dismissed', 'resolved', 'closed',
    'open', 'pending', 'snoozed',
    # Compound status terms
    'active warnings', 'open warnings', 'pending warnings',
    'acknowledged warnings', 'dismissed warnings', 'resolved warnings',
    # Paraphrases (alerts instead of warnings)
    'active alerts', 'open alerts', 'pending alerts',
}



# =============================================================================
# DATE/TIME PATTERNS - For temporal entity extraction
# =============================================================================
# These patterns extract dates, times, and temporal references from queries.
# Critical for: scheduling, log analysis, historical searches, compliance.
#
# OUTPUT: Canonical forms for searchability
# - Months → MONTH_JAN, MONTH_FEB, etc.
# - Days → DAY_MON, DAY_TUE, etc.
# - Relative → TIME_YESTERDAY, TIME_LAST_WEEK, etc.

# Month names (full and abbreviated)
MONTH_PATTERNS = {
    # Full month names → canonical form
    'january': 'MONTH_01_JAN',
    'february': 'MONTH_02_FEB',
    'march': 'MONTH_03_MAR',
    'april': 'MONTH_04_APR',
    'may': 'MONTH_05_MAY',
    'june': 'MONTH_06_JUN',
    'july': 'MONTH_07_JUL',
    'august': 'MONTH_08_AUG',
    'september': 'MONTH_09_SEP',
    'october': 'MONTH_10_OCT',
    'november': 'MONTH_11_NOV',
    'december': 'MONTH_12_DEC',
    # Abbreviated month names
    'jan': 'MONTH_01_JAN',
    'feb': 'MONTH_02_FEB',
    'mar': 'MONTH_03_MAR',
    'apr': 'MONTH_04_APR',
    'jun': 'MONTH_06_JUN',
    'jul': 'MONTH_07_JUL',
    'aug': 'MONTH_08_AUG',
    'sep': 'MONTH_09_SEP',
    'sept': 'MONTH_09_SEP',
    'oct': 'MONTH_10_OCT',
    'nov': 'MONTH_11_NOV',
    'dec': 'MONTH_12_DEC',
}

# Day names (full and abbreviated)
DAY_PATTERNS = {
    # Full day names
    'monday': 'DAY_1_MON',
    'tuesday': 'DAY_2_TUE',
    'wednesday': 'DAY_3_WED',
    'thursday': 'DAY_4_THU',
    'friday': 'DAY_5_FRI',
    'saturday': 'DAY_6_SAT',
    'sunday': 'DAY_7_SUN',
    # Abbreviated day names
    'mon': 'DAY_1_MON',
    'tue': 'DAY_2_TUE',
    'tues': 'DAY_2_TUE',
    'wed': 'DAY_3_WED',
    'thu': 'DAY_4_THU',
    'thur': 'DAY_4_THU',
    'thurs': 'DAY_4_THU',
    'fri': 'DAY_5_FRI',
    'sat': 'DAY_6_SAT',
    'sun': 'DAY_7_SUN',
}

# Time unit patterns (with abbreviations)
TIME_UNIT_PATTERNS = {
    # Hours
    'hour': 'UNIT_HOUR',
    'hours': 'UNIT_HOUR',
    'hr': 'UNIT_HOUR',
    'hrs': 'UNIT_HOUR',
    # Minutes
    'minute': 'UNIT_MINUTE',
    'minutes': 'UNIT_MINUTE',
    'min': 'UNIT_MINUTE',
    'mins': 'UNIT_MINUTE',
    # Seconds
    'second': 'UNIT_SECOND',
    'seconds': 'UNIT_SECOND',
    'sec': 'UNIT_SECOND',
    'secs': 'UNIT_SECOND',
    # Days
    'day': 'UNIT_DAY',
    'days': 'UNIT_DAY',
    # Weeks
    'week': 'UNIT_WEEK',
    'weeks': 'UNIT_WEEK',
    'wk': 'UNIT_WEEK',
    'wks': 'UNIT_WEEK',
    # Months
    'month': 'UNIT_MONTH',
    'months': 'UNIT_MONTH',
    'mo': 'UNIT_MONTH',
    'mos': 'UNIT_MONTH',
    # Years
    'year': 'UNIT_YEAR',
    'years': 'UNIT_YEAR',
    'yr': 'UNIT_YEAR',
    'yrs': 'UNIT_YEAR',
}

# Relative time references
RELATIVE_TIME_PATTERNS = {
    # Recent past
    'today': 'REL_TODAY',
    'yesterday': 'REL_YESTERDAY',
    'last night': 'REL_LAST_NIGHT',
    'this morning': 'REL_THIS_MORNING',
    'this afternoon': 'REL_THIS_AFTERNOON',
    'this evening': 'REL_THIS_EVENING',
    # Week references
    'this week': 'REL_THIS_WEEK',
    'last week': 'REL_LAST_WEEK',
    'next week': 'REL_NEXT_WEEK',
    'past week': 'REL_LAST_WEEK',
    # Month references
    'this month': 'REL_THIS_MONTH',
    'last month': 'REL_LAST_MONTH',
    'next month': 'REL_NEXT_MONTH',
    'past month': 'REL_LAST_MONTH',
    # Year references
    'this year': 'REL_THIS_YEAR',
    'last year': 'REL_LAST_YEAR',
    'next year': 'REL_NEXT_YEAR',
    # Quarter references
    'this quarter': 'REL_THIS_QUARTER',
    'last quarter': 'REL_LAST_QUARTER',
    'q1': 'REL_Q1',
    'q2': 'REL_Q2',
    'q3': 'REL_Q3',
    'q4': 'REL_Q4',
    # General past
    'recently': 'REL_RECENT',
    'lately': 'REL_RECENT',
    'previously': 'REL_PREVIOUS',
    'earlier': 'REL_EARLIER',
    'before': 'REL_BEFORE',
    'ago': 'REL_AGO',
}

# Time of day patterns
TIME_OF_DAY_PATTERNS = {
    'am': 'TOD_AM',
    'a.m.': 'TOD_AM',
    'pm': 'TOD_PM',
    'p.m.': 'TOD_PM',
    'morning': 'TOD_MORNING',
    'afternoon': 'TOD_AFTERNOON',
    'evening': 'TOD_EVENING',
    'night': 'TOD_NIGHT',
    'midnight': 'TOD_MIDNIGHT',
    'noon': 'TOD_NOON',
    'midday': 'TOD_NOON',
}

# Maritime-specific time references
MARITIME_TIME_PATTERNS = {
    # Watch times (4-hour watches)
    'first watch': 'WATCH_FIRST',      # 2000-0000
    'middle watch': 'WATCH_MIDDLE',    # 0000-0400
    'morning watch': 'WATCH_MORNING',  # 0400-0800
    'forenoon watch': 'WATCH_FORENOON', # 0800-1200
    'afternoon watch': 'WATCH_AFTERNOON', # 1200-1600
    'dog watch': 'WATCH_DOG',          # 1600-2000
    'first dog': 'WATCH_FIRST_DOG',    # 1600-1800
    'second dog': 'WATCH_SECOND_DOG',  # 1800-2000
    # Voyage references
    'departure': 'VOYAGE_DEPARTURE',
    'arrival': 'VOYAGE_ARRIVAL',
    'underway': 'VOYAGE_UNDERWAY',
    'at anchor': 'VOYAGE_ANCHOR',
    'in port': 'VOYAGE_PORT',
    'at sea': 'VOYAGE_SEA',
    'sea trial': 'VOYAGE_SEA_TRIAL',
    'dry dock': 'VOYAGE_DRY_DOCK',
    'drydock': 'VOYAGE_DRY_DOCK',
    # Maintenance intervals
    'annual': 'INTERVAL_ANNUAL',
    'bi-annual': 'INTERVAL_BIANNUAL',
    'biannual': 'INTERVAL_BIANNUAL',
    'quarterly': 'INTERVAL_QUARTERLY',
    'monthly': 'INTERVAL_MONTHLY',
    'weekly': 'INTERVAL_WEEKLY',
    'daily': 'INTERVAL_DAILY',
    'running hours': 'INTERVAL_RUNNING_HOURS',
    'engine hours': 'INTERVAL_ENGINE_HOURS',
    'service interval': 'INTERVAL_SERVICE',
}

# Combine all time patterns for easy access
ALL_TIME_PATTERNS = {
    **MONTH_PATTERNS,
    **DAY_PATTERNS,
    **TIME_UNIT_PATTERNS,
    **RELATIVE_TIME_PATTERNS,
    **TIME_OF_DAY_PATTERNS,
    **MARITIME_TIME_PATTERNS,
}


# =============================================================================
# EQUIPMENT GAZETTEER BUILDER (Groups 1-10)
# =============================================================================

def load_equipment_gazetteer() -> Dict[str, Set[str]]:
    """
    Build equipment/brand gazetteer from bundled EQUIPMENT_PATTERNS + CORE terms.

    WHAT THIS DOES:
    1. Starts with CORE terms (brands, equipment, parts, symptoms)
    2. Adds compound terms from EQUIPMENT_PATTERNS
    3. Filters out terms that match equipment/document filters
    4. Returns a dictionary with categorized sets of terms

    WHY SEPARATE CATEGORIES?
    - Different types need different handling
    - Brands get higher confidence than generic equipment
    - Parts might need part number lookup
    - Symptoms feed into diagnostic logic

    Returns:
        Dictionary mapping category -> set of terms:
        - brand: Brand names (MTU, Caterpillar, etc.)
        - equipment: Equipment types (generator, radar, etc.)
        - part: Part names (membrane, impeller, etc.)
        - symptom: Symptom terms (overheating, vibration, etc.)
        - equipment_brand: Combined brand terms (for backward compatibility)
        - equipment_type: Combined equipment terms
        - system_type: System categories (propulsion, navigation, etc.)
    """
    # Initialize empty sets for each category
    gazetteer = {
        'brand': set(),           # Core brand names
        'equipment': set(),       # Core equipment types
        'part': set(),            # Core part names
        'symptom': set(),         # Core symptoms
        'equipment_brand': set(), # All brand terms (backward compatibility)
        'equipment_type': set(),  # All equipment terms
        'system_type': set(),     # System categories
        # Shopping list categories (Added 2026-01-30)
        'shopping_list_term': set(),  # Shopping list keywords
        'approval_status': set(),     # Approval states
        'urgency_level': set(),       # Urgency indicators
        'source_type': set(),         # Source of shopping list items
        # Inventory Lens - Stock Status (Added 2026-02-02)
        'stock_status': set(),        # Stock level status phrases
        # Crew Lens - Hours of Rest (Added 2026-01-31)
        'REST_COMPLIANCE': set(),     # Rest compliance status
        'WARNING_SEVERITY': set(),    # Warning severity levels
        'WARNING_STATUS': set(),      # Warning status states
    }

    # =========================================================================
    # STEP 1: Add CORE terms first
    # =========================================================================
    # These are GUARANTEED to be detected regardless of filters
    # They form the foundation of entity extraction

    # Add core brands to both 'brand' and 'equipment_brand'
    gazetteer['brand'].update(CORE_BRANDS)
    gazetteer['equipment_brand'].update(CORE_BRANDS)  # Backward compatibility

    # Add core equipment to both 'equipment' and 'equipment_type'
    gazetteer['equipment'].update(CORE_EQUIPMENT)
    gazetteer['equipment_type'].update(CORE_EQUIPMENT)  # Backward compatibility

    # Add core parts and symptoms
    gazetteer['part'].update(CORE_PARTS)
    gazetteer['symptom'].update(CORE_SYMPTOMS)

    # Add shopping list terms (Added 2026-01-30 for fast-path extraction)
    gazetteer['shopping_list_term'].update(CORE_SHOPPING_LIST_TERMS)
    gazetteer['approval_status'].update(CORE_APPROVAL_STATUSES)
    gazetteer['urgency_level'].update(CORE_URGENCY_LEVELS)
    gazetteer['source_type'].update(CORE_SOURCE_TYPES)

    # Add inventory lens terms (Added 2026-02-02 for fast-path stock status extraction)
    gazetteer['stock_status'].update(CORE_STOCK_STATUS)

    # Add crew lens terms (Added 2026-01-31 for fast-path crew extraction)
    gazetteer['REST_COMPLIANCE'].update(CORE_REST_COMPLIANCE)
    gazetteer['WARNING_SEVERITY'].update(CORE_WARNING_SEVERITY)
    gazetteer['WARNING_STATUS'].update(CORE_WARNING_STATUS)

    # =========================================================================
    # STEP 2: Add compound terms from EQUIPMENT_PATTERNS
    # =========================================================================
    # EQUIPMENT_PATTERNS contains additional brand/equipment terms from the database
    # We filter these to avoid adding generic terms like "pump" as brands

    # Track total for summary
    total_terms = len(CORE_BRANDS) + len(CORE_EQUIPMENT) + len(CORE_PARTS) + len(CORE_SYMPTOMS)

    # Loop through each pattern in EQUIPMENT_PATTERNS
    for canonical, pattern_data in EQUIPMENT_PATTERNS.items():
        # Get the list of terms for this pattern
        terms = pattern_data.get('terms', [])
        domain = pattern_data.get('domain', '')      # e.g., "propulsion"
        subdomain = pattern_data.get('subdomain', '')  # e.g., "main engine"

        # Add each term to equipment_brand (if it passes filters)
        for term in terms:
            term_lower = term.lower()
            term_words = set(term_lower.split())

            # FILTER 1: Skip if term is a SINGLE word that exactly matches a filter
            # Example: "pump" alone is filtered out
            # FIX: Only block single generic words, NOT compounds
            if len(term_words) == 1 and term_lower in ALL_FILTERS:
                continue

            # FILTER 2 (FIXED): For compound terms, only skip if ALL words are generic
            # OLD (wrong): Skip if ANY word is a filter word → dropped "jabsco pump"
            # NEW (correct): Skip if ALL words are generic AND no brand/model context
            #
            # Examples:
            # - "jabsco pump" → KEEP (has brand "jabsco")
            # - "mtu generator" → KEEP (has brand "mtu")
            # - "fuel oil pump" → KEEP (has specificity "fuel oil")
            # - "pump motor" → SKIP (both are generic)
            if len(term_words) > 1:
                # Check if any word is a brand or model (not generic)
                has_specific_word = False
                for word in term_words:
                    # Word is specific if:
                    # - It's a core brand (mtu, jabsco, furuno, etc.)
                    # - It's NOT in the generic filter list
                    # - It contains numbers (likely a model: 3512, 16V4000)
                    is_brand = word in CORE_BRANDS
                    is_not_generic = word not in ALL_FILTERS
                    has_numbers = any(c.isdigit() for c in word)

                    if is_brand or has_numbers or (is_not_generic and len(word) > 3):
                        has_specific_word = True
                        break

                # Skip only if ALL words are generic (no specific context)
                if not has_specific_word:
                    continue

            # FILTER 3: Skip single short generic words
            # Exception: Core brands/equipment are kept even if short
            # Example: "mtu" is kept (core brand), but "abc" is filtered
            if len(term_words) == 1 and len(term_lower) < 4:
                if term_lower not in CORE_BRANDS and term_lower not in CORE_EQUIPMENT:
                    continue

            # Passed all filters - add to equipment_brand
            gazetteer['equipment_brand'].add(term_lower)
            total_terms += 1

        # Add subdomain as equipment type
        # Example: subdomain "bow thruster" → equipment_type
        if subdomain:
            gazetteer['equipment_type'].add(subdomain.lower())

        # Add domain as system type (clean up numbering)
        # Example: domain "01: propulsion" → system_type "propulsion"
        if domain:
            # Remove leading number prefix like "01: "
            clean_domain = re.sub(r'^\d+:\s*', '', domain)
            gazetteer['system_type'].add(clean_domain.lower())

    # Print summary of what was loaded
    print(f"✅ Loaded {total_terms:,} terms from {len(EQUIPMENT_PATTERNS)} equipment patterns")
    print(f"   - {len(gazetteer['brand']):,} core brands")
    print(f"   - {len(gazetteer['equipment']):,} core equipment types")
    print(f"   - {len(gazetteer['part']):,} core parts")
    print(f"   - {len(gazetteer['symptom']):,} core symptoms")
    print(f"   - {len(gazetteer['equipment_brand']):,} total brand terms (incl. compound)")
    print(f"   - {len(gazetteer['system_type']):,} unique system types")
    print(f"   - {len(gazetteer['shopping_list_term']):,} shopping list terms")
    print(f"   - {len(gazetteer['approval_status']):,} approval statuses")
    print(f"   - {len(gazetteer['urgency_level']):,} urgency levels")
    print(f"   - {len(gazetteer['source_type']):,} source types")
    print(f"   - {len(gazetteer['stock_status']):,} stock status terms")
    print(f"   - {len(gazetteer['REST_COMPLIANCE']):,} rest compliance terms")
    print(f"   - {len(gazetteer['WARNING_SEVERITY']):,} warning severity levels")
    print(f"   - {len(gazetteer['WARNING_STATUS']):,} warning status terms")

    return gazetteer


# =============================================================================
# DIAGNOSTIC PATTERNS BUILDER (Groups 11-16)
# =============================================================================

def load_diagnostic_patterns() -> Dict[str, List[Tuple[re.Pattern, str, str, str]]]:
    """
    Build diagnostic pattern matchers from bundled DIAGNOSTIC_PATTERNS.

    WHAT THIS DOES:
    1. Reads DIAGNOSTIC_PATTERNS from the bundled data
    2. Groups patterns by type (symptom, sensor_language, etc.)
    3. Compiles each regex pattern for fast matching
    4. Adds word boundaries to prevent false positives
    5. Returns compiled patterns ready for matching

    PATTERN GROUPS (from database):
    - Group 11: Symptoms (overheating, vibration, etc.)
    - Group 12: Sensor Language (high temperature, low pressure, etc.)
    - Group 13: Human Reports (noticed, observed, seems, etc.)
    - Group 14: Fault Classification (critical, warning, alarm, etc.)
    - Group 15: Actions (replace, inspect, calibrate, etc.)
    - Group 16: Sensor Readings (temperature reading, pressure measurement, etc.)

    WORD BOUNDARIES:
    - CRITICAL FIX: We add \\b (word boundary) to prevent substring matches
    - Without: "vent" would match inside "inVENTory" (WRONG!)
    - With: "\\bvent\\b" only matches "vent" as a complete word

    Returns:
        Dictionary mapping entity_type -> list of (compiled_regex, domain, subdomain, canonical)
    """
    # Map group numbers to entity type names
    GROUP_TO_TYPE = {
        11: 'symptom',           # System symptoms
        12: 'sensor_language',   # Sensor terminology
        13: 'human_report',      # Human observations
        14: 'fault_classification',  # Fault types/severity
        15: 'action',            # Verbs and actions
        16: 'sensor_reading'     # Measurement terminology
    }

    # Initialize empty lists for each type
    patterns = {
        'symptom': [],
        'sensor_language': [],
        'human_report': [],
        'fault_classification': [],
        'action': [],
        'sensor_reading': []
    }

    # Counters for summary
    total_patterns = 0
    blacklisted_count = 0

    # Loop through each pattern in DIAGNOSTIC_PATTERNS
    for canonical, pattern_data in DIAGNOSTIC_PATTERNS.items():
        # FILTER: Skip blacklisted patterns (known false positive generators)
        if canonical in CANONICAL_BLACKLIST:
            blacklisted_count += 1
            continue

        # Get pattern metadata
        group = pattern_data.get('group', 0)           # Group number (11-16)
        entity_type = GROUP_TO_TYPE.get(group)         # Map to entity type

        # Skip if group not in our mapping (groups 1-10 are equipment, not diagnostic)
        if not entity_type:
            continue

        domain = pattern_data.get('domain', '')         # e.g., "temperature"
        subdomain = pattern_data.get('subdomain', '')   # e.g., "high_temperature"
        regex_str = pattern_data.get('regex', '')       # The regex pattern

        # Skip if no regex pattern
        if not regex_str:
            continue

        # =====================================================================
        # CRITICAL FIX: Add word boundaries to prevent substring false positives
        # =====================================================================
        # Problem: Pattern "vent" matches inside "inVENTory"
        # Solution: Add \b (word boundary) at start and end
        #
        # Before: vent
        # After:  \bvent\b
        #
        # \b matches the boundary between a word character and non-word character
        # So \bvent\b only matches "vent" when it's a complete word

        # Check if pattern already has word boundary at start
        if not regex_str.startswith(r'\b') and not regex_str.startswith('\\b'):
            regex_str = r'\b' + regex_str

        # Check if pattern already has word boundary at end
        if not regex_str.endswith(r'\b') and not regex_str.endswith('\\b'):
            regex_str = regex_str + r'\b'

        # Compile the regex pattern
        try:
            compiled = re.compile(regex_str, re.IGNORECASE)  # Case insensitive
            patterns[entity_type].append((compiled, domain, subdomain, canonical))
            total_patterns += 1
        except re.error as e:
            # Handle invalid regex (shouldn't happen with bundled data)
            print(f"⚠️  Regex error in {canonical}: {e}")
            continue

    # Print summary
    print(f"✅ Loaded {total_patterns} diagnostic patterns:")
    for entity_type, pattern_list in patterns.items():
        print(f"   - {entity_type}: {len(pattern_list)} patterns")

    if blacklisted_count > 0:
        print(f"⚠️  Blacklisted {blacklisted_count} patterns (known false positive generators)")

    return patterns


# =============================================================================
# WEIGHT CALCULATION
# =============================================================================

def calculate_weight(entity_type: str, metadata: Dict, text_length: int = 0) -> float:
    """
    Calculate entity weight based on type, metadata, and specificity.

    WHY WEIGHTS MATTER:
    - Search results are ranked by relevance
    - More specific entities should rank higher
    - Weight directly affects search ranking

    WEIGHT RANGES (1.0 to 5.0):
    - 4.0-5.0: Very specific (fault codes, model numbers)
    - 3.0-3.5: Specific (brands, symptoms)
    - 2.5-3.0: Moderate (equipment types)
    - 2.0-2.5: Generic (system types, actions)

    ADJUSTMENTS:
    - Longer text = more specific = higher weight
    - Diagnostic groups (11-16) get +0.5 bonus

    Args:
        entity_type: The type of entity (brand, symptom, etc.)
        metadata: Additional metadata (may contain group number)
        text_length: Length of the matched text

    Returns:
        Weight value between 1.0 and 5.0
    """
    # Base weights by entity type
    type_weights = {
        'fault_code': 4.5,          # Fault codes are very specific
        # Crew Lens - Hours of Rest (Added 2026-01-31)
        # HIGH PRIORITY: Crew-specific entity types must override generic types
        'REST_COMPLIANCE': 4.3,      # Rest compliance status (higher than symptom)
        'WARNING_SEVERITY': 4.2,     # Warning severity (higher than fault_classification)
        'WARNING_STATUS': 4.2,       # Warning status (higher than fault_classification)
        'symptom': 4.0,             # Symptoms are key for diagnosis
        'model': 4.0,               # Model numbers are very specific
        'fault_classification': 3.8,# Fault types
        'product_name': 3.5,        # Product names
        'sensor_reading': 3.5,      # Measurement terms
        'sensor_language': 3.3,     # Sensor terminology
        'equipment_brand': 3.2,     # Brand names
        'equipment': 3.2,           # Equipment items (FIXED 2026-02-02: was missing, defaulted to 2.0)
        'human_report': 3.0,        # Human observations
        'shopping_list_term': 3.0,  # Shopping list queries (FIXED 2026-02-02)
        'approval_status': 3.0,     # Approval status (pending, approved, etc.) (FIXED 2026-02-02)
        'equipment_type': 2.8,      # Equipment types
        'part': 2.8,                # Parts and components (FIXED 2026-02-02: was missing, defaulted to 2.0)
        'action': 2.5,              # Action verbs
        'system_type': 2.3          # System categories
    }

    # Get base weight (default 2.0 if type not found)
    base_weight = type_weights.get(entity_type, 2.0)

    # ADJUSTMENT 1: Specificity based on text length
    # Longer matches are usually more specific
    if text_length > 15:
        base_weight += 1.0    # Very specific: +1.0
    elif text_length > 8:
        base_weight += 0.5    # Somewhat specific: +0.5

    # ADJUSTMENT 2: Diagnostic groups get bonus
    # Groups 11-16 are diagnostic patterns (symptoms, faults, etc.)
    # These are more valuable for troubleshooting
    group = metadata.get('group', 0)
    if isinstance(group, int) and 11 <= group <= 16:
        base_weight += 0.5

    # CAP: Maximum weight is 5.0
    return min(base_weight, 5.0)


def get_pattern_metadata(domain: str, subdomain: str, group: str) -> Dict:
    """
    Create metadata dict for extracted entity.

    This metadata is attached to each extracted entity for:
    - Tracking where the entity came from
    - Debugging pattern matches
    - Weight calculation

    Args:
        domain: The domain category (e.g., "propulsion")
        subdomain: The subdomain (e.g., "main engine")
        group: The pattern group (e.g., "11" for symptoms)

    Returns:
        Dict with source info
    """
    return {
        'source_file': 'regex_production_data',  # Where patterns came from
        'domain': domain,                         # Category
        'subdomain': subdomain,                   # Subcategory
        'group': group                            # Pattern group number
    }


# =============================================================================
# CACHED LOADERS - Load patterns once, reuse for all requests
# =============================================================================
# Why caching?
# - Loading patterns is slow (parsing thousands of entries)
# - We only need to load once at startup
# - All requests share the same pattern data
#
# How it works:
# - _equipment_gazetteer starts as None
# - First call to get_equipment_gazetteer() loads and caches
# - Subsequent calls return the cached version

_equipment_gazetteer: Optional[Dict[str, Set[str]]] = None
_diagnostic_patterns: Optional[Dict[str, List[Tuple[re.Pattern, str, str, str]]]] = None


def get_equipment_gazetteer() -> Dict[str, Set[str]]:
    """
    Get cached equipment gazetteer (loads on first call).

    This is the main function called by module_b_entity_extractor.py.

    Returns:
        Cached dictionary of brand/equipment/part/symptom sets
    """
    global _equipment_gazetteer
    if _equipment_gazetteer is None:
        _equipment_gazetteer = load_equipment_gazetteer()
    return _equipment_gazetteer


def get_diagnostic_patterns() -> Dict[str, List[Tuple[re.Pattern, str, str, str]]]:
    """
    Get cached diagnostic patterns (loads on first call).

    This is the main function called by module_b_entity_extractor.py.

    Returns:
        Cached dictionary of compiled regex patterns
    """
    global _diagnostic_patterns
    if _diagnostic_patterns is None:
        _diagnostic_patterns = load_diagnostic_patterns()
    return _diagnostic_patterns


# =============================================================================
# QUICK EXTRACTION WRAPPERS
# =============================================================================

# Cache for compiled gazetteer patterns (with word boundaries)
_gazetteer_patterns_cache = None

def _compile_gazetteer_patterns() -> Dict[str, List[Tuple[re.Pattern, str]]]:
    """
    Compile gazetteer terms into regex patterns with word boundaries.

    FIX #1: Naive substring matching (if term in text) causes false positives.
    Example: "cat" matches inside "caterpillar" or "category"
    Solution: Use word boundaries \\b for exact word matching.

    Returns:
        Dict mapping entity_type to list of (compiled_pattern, term) tuples
    """
    global _gazetteer_patterns_cache

    if _gazetteer_patterns_cache is not None:
        return _gazetteer_patterns_cache

    gazetteer = get_equipment_gazetteer()
    patterns = {}

    for entity_type, terms in gazetteer.items():
        patterns[entity_type] = []
        for term in terms:
            if not term or len(term) < 2:
                continue
            # Escape special regex characters and add word boundaries
            escaped = re.escape(term)
            # For multi-word terms, match the whole phrase
            # For single words, use word boundaries
            pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
            patterns[entity_type].append((pattern, term))

    _gazetteer_patterns_cache = patterns
    return patterns


def extract_entities_from_text(text: str) -> Dict[str, Any]:
    """
    Extract all entities from text using bundled patterns.

    RETURNS UNIFIED SCHEMA:
    All entities (diagnostic + equipment + gazetteer) are normalized to:
    [{
        type: str,           # equipment_brand, symptom, fault_code, etc.
        value: str,          # The matched text from query
        confidence: float,   # 0.0-1.0
        weight: float,       # 1.0-5.0 for ranking
        source: str,         # "regex", "gazetteer", or "bundled"
        domain: str,         # Optional domain (for diagnostics)
        subdomain: str,      # Optional subdomain
        start_char: int,     # Starting position in text
        end_char: int        # Ending position in text
    }]

    This unified format makes downstream processing consistent.

    Args:
        text: The query text to extract entities from

    Returns:
        Dict with:
        - entities: Unified list of ALL extracted entities
        - diagnostic: (deprecated) kept for backwards compatibility
        - equipment: (deprecated) kept for backwards compatibility
        - gazetteer_matches: (deprecated) kept for backwards compatibility
    """
    # Unified result list
    entities = []

    # Legacy result dicts (kept for backwards compatibility)
    result = {
        'entities': entities,           # NEW: Unified list
        'diagnostic': [],               # DEPRECATED: Use entities instead
        'equipment': [],                # DEPRECATED: Use entities instead
        'gazetteer_matches': []         # DEPRECATED: Use entities instead
    }

    # Check if patterns are available
    if not PATTERNS_AVAILABLE:
        return result

    text_lower = text.lower()

    # =========================================================================
    # 1. DIAGNOSTIC PATTERNS (regex with word boundaries)
    # =========================================================================
    # FIX #3: Carry actual group from pattern_data, not hardcoded 11
    # FIX #4: Use finditer() instead of findall() to get proper spans

    diag_patterns = get_diagnostic_patterns()
    for entity_type, pattern_list in diag_patterns.items():
        for pattern_data in pattern_list:
            # Unpack with proper group handling
            if len(pattern_data) == 4:
                pattern, domain, subdomain, canonical = pattern_data
                group = 11  # Default for legacy patterns
            elif len(pattern_data) == 5:
                pattern, domain, subdomain, canonical, group = pattern_data
            else:
                continue

            # FIX #4: Use finditer() for proper span information
            for match in pattern.finditer(text_lower):
                matched_text = match.group(0)  # Full match, not capture groups

                entity = {
                    'type': entity_type,
                    'value': matched_text,
                    'canonical': canonical,
                    'domain': domain,
                    'subdomain': subdomain,
                    'confidence': 0.9,
                    'weight': calculate_weight(entity_type, {'group': group}, len(matched_text)),
                    'source': 'regex',
                    'start_char': match.start(),
                    'end_char': match.end()
                }

                entities.append(entity)
                result['diagnostic'].append(entity)  # Legacy compatibility

    # =========================================================================
    # 2. GAZETTEER MATCHING (with word boundaries)
    # =========================================================================
    # FIX #1: Use compiled patterns with word boundaries, not substring check

    gazetteer_patterns = _compile_gazetteer_patterns()

    for entity_type, pattern_list in gazetteer_patterns.items():
        for pattern, term in pattern_list:
            for match in pattern.finditer(text_lower):
                matched_text = match.group(0)

                entity = {
                    'type': entity_type,
                    'value': matched_text,
                    'confidence': 0.85,
                    'weight': calculate_weight(entity_type, {}, len(matched_text)),
                    'source': 'gazetteer',
                    'domain': None,
                    'subdomain': None,
                    'start_char': match.start(),
                    'end_char': match.end()
                }

                entities.append(entity)
                result['gazetteer_matches'].append(entity)  # Legacy compatibility

    # =========================================================================
    # 3. BUNDLED EXTRACTORS (from regex_production_data.py)
    # =========================================================================
    bundled_results = extract_all_entities(text)
    for eq in bundled_results.get('equipment', []):
        # FIX: extract_equipment_entities returns 'matches' list, not 'value'
        # Extract first match as the value, or skip if no matches
        matches = eq.get('matches', [])
        if not matches:
            continue  # Skip empty matches

        value = matches[0] if matches else eq.get('value', '')
        if not value:
            continue  # Skip if no value found

        # Filter out noisy short matches from bundled extractor
        # The bundled extractor uses substring matching which catches noise
        # like "ge" in "generator", "at" in "caterpillar", etc.
        if len(value) < 3:
            continue  # Skip very short matches (likely noise)

        # Also skip known false positives from substring matching
        value_lower = value.lower()
        if value_lower in {'ge', 'at', 'br', 'ion', 'sea', 'iss', 'nos', 'dia', 'keeper'}:
            continue  # Skip common substring noise

        entity = {
            'type': eq.get('type', 'equipment'),
            'value': value,
            'canonical': eq.get('canonical', ''),  # Include canonical form
            'confidence': eq.get('confidence', 0.8),
            'weight': eq.get('weight', 3.0),
            'source': 'bundled',
            'domain': eq.get('domain'),
            'subdomain': eq.get('subdomain'),
            'start_char': eq.get('start_char', -1),
            'end_char': eq.get('end_char', -1)
        }
        entities.append(entity)
        result['equipment'].append(entity)  # Legacy compatibility

    # =========================================================================
    # 4. DEDUPLICATE by span (overlapping entities)
    # =========================================================================
    # If two entities overlap significantly, keep the higher-weight one
    entities = _deduplicate_by_span(entities)
    result['entities'] = entities

    return result


def _deduplicate_by_span(entities: List[Dict]) -> List[Dict]:
    """
    Remove duplicate entities that overlap in the text.

    When two entities have overlapping character spans, keep the one with:
    1. Higher weight (more specific)
    2. Longer span (if weights are equal)

    Args:
        entities: List of entity dicts with start_char/end_char

    Returns:
        Deduplicated list of entities
    """
    if not entities:
        return []

    # Sort by start position, then by weight descending
    sorted_ents = sorted(entities, key=lambda e: (e.get('start_char', -1), -e.get('weight', 0)))

    result = []
    for entity in sorted_ents:
        start = entity.get('start_char', -1)
        end = entity.get('end_char', -1)

        # Skip entities without valid spans
        if start < 0 or end < 0:
            result.append(entity)
            continue

        # Check if this entity overlaps significantly with any kept entity
        is_duplicate = False
        for kept in result:
            k_start = kept.get('start_char', -1)
            k_end = kept.get('end_char', -1)

            if k_start < 0 or k_end < 0:
                continue

            # Calculate overlap
            overlap_start = max(start, k_start)
            overlap_end = min(end, k_end)
            overlap_len = max(0, overlap_end - overlap_start)

            # If overlap is >50% of shorter entity, it's a duplicate
            shorter_len = min(end - start, k_end - k_start)
            if shorter_len > 0 and overlap_len / shorter_len > 0.5:
                # Keep the one with higher weight
                if entity.get('weight', 0) > kept.get('weight', 0):
                    result.remove(kept)
                    result.append(entity)
                is_duplicate = True
                break

        if not is_duplicate:
            result.append(entity)

    return result


# =============================================================================
# MODULE TEST - Runs when file is executed directly
# =============================================================================
# Usage: python entity_extraction_loader.py

if __name__ == "__main__":
    print("=" * 80)
    print("ENTITY EXTRACTION LOADER - BUNDLED DATA VERSION")
    print("=" * 80)

    # Show bundled pattern statistics
    print(f"\n📊 Bundled Pattern Stats:")
    print(f"   Total patterns: {STATS.get('total_patterns', 0):,}")
    print(f"   Total terms: {STATS.get('total_terms', 0):,}")
    print(f"   Diagnostic patterns: {STATS.get('diagnostic_patterns', 0)}")
    print(f"   Equipment patterns: {STATS.get('equipment_patterns', 0)}")

    # Load and display gazetteer
    print(f"\n🔧 Loading Equipment Gazetteer...")
    gaz = get_equipment_gazetteer()

    # Load and display diagnostic patterns
    print(f"\n🩺 Loading Diagnostic Patterns...")
    diag = get_diagnostic_patterns()

    # Test extraction with sample queries
    print(f"\n🧪 Sample Test:")
    test_queries = [
        "MTU 16V4000 engine overheating with high exhaust temperature",
        "watermaker membrane needs replacement, low output",
        "Furuno radar display showing error code E-15",
        "fire damper stuck open in engine room"
    ]

    for query in test_queries:
        print(f"\n   Query: {query}")
        results = extract_entities_from_text(query)
        print(f"   Diagnostic: {len(results['diagnostic'])} entities")
        print(f"   Equipment: {len(results['equipment'])} entities")
        print(f"   Gazetteer: {len(results['gazetteer_matches'])} matches")

        # Show top matches
        if results['diagnostic']:
            top_diag = results['diagnostic'][0]
            print(f"   → Top diagnostic: {top_diag['canonical']} ({top_diag['type']})")
        if results['gazetteer_matches']:
            top_gaz = results['gazetteer_matches'][0]
            print(f"   → Top equipment: {top_gaz['value']} ({top_gaz['type']})")

    print("\n" + "=" * 80)
    print("TEST COMPLETE - Ready for Render deployment")
    print("=" * 80)

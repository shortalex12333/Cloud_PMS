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
}

# CORE EQUIPMENT - Essential equipment types
# These must always be recognized regardless of context
CORE_EQUIPMENT = {
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
    'overheating', 'overheat',

    # Mechanical issues
    'vibration', 'noise',

    # Fluid issues
    'leak', 'leaking',

    # General failures
    'failure', 'failed', 'alarm', 'warning', 'error', 'fault', 'malfunction',

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
        'system_type': set()      # System categories
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

            # FILTER 1: Skip if term exactly matches a filter word
            # Example: "pump" alone is filtered out
            if term_lower in ALL_FILTERS:
                continue

            # FILTER 2: Skip if any word in the term is a filter word
            # Example: "bilge pump" contains "pump" which is filtered
            term_words = set(term_lower.split())
            if term_words & ALL_FILTERS:  # & is set intersection
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
        'symptom': 4.0,             # Symptoms are key for diagnosis
        'model': 4.0,               # Model numbers are very specific
        'fault_classification': 3.8,# Fault types
        'product_name': 3.5,        # Product names
        'sensor_reading': 3.5,      # Measurement terms
        'sensor_language': 3.3,     # Sensor terminology
        'equipment_brand': 3.2,     # Brand names
        'human_report': 3.0,        # Human observations
        'equipment_type': 2.8,      # Equipment types
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

def extract_entities_from_text(text: str) -> Dict[str, Any]:
    """
    Extract all entities from text using bundled patterns.

    This is a convenience function that combines multiple extraction methods.
    For production use, module_b_entity_extractor.py is preferred.

    Args:
        text: The query text to extract entities from

    Returns:
        Dict with:
        - diagnostic: List of symptom/fault/action entities
        - equipment: List of brand/equipment entities
        - gazetteer_matches: Direct term matches from gazetteer
    """
    result = {
        'diagnostic': [],       # Symptoms, faults, actions
        'equipment': [],        # Brands, equipment types
        'gazetteer_matches': [] # Direct term matches
    }

    # Check if patterns are available
    if not PATTERNS_AVAILABLE:
        return result

    text_lower = text.lower()

    # =========================================================================
    # 1. Get diagnostic matches using regex patterns
    # =========================================================================
    diag_patterns = get_diagnostic_patterns()
    for entity_type, pattern_list in diag_patterns.items():
        for pattern, domain, subdomain, canonical in pattern_list:
            # Find all matches of this pattern
            matches = pattern.findall(text_lower)
            if matches:
                result['diagnostic'].append({
                    'type': entity_type,
                    'canonical': canonical,
                    'domain': domain,
                    'subdomain': subdomain,
                    'matches': list(set(matches))[:5],  # Limit to 5 unique matches
                    'confidence': 0.9,
                    'weight': calculate_weight(entity_type, {'group': 11}, len(matches[0]))
                })

    # =========================================================================
    # 2. Get equipment matches using gazetteer
    # =========================================================================
    gazetteer = get_equipment_gazetteer()
    words = set(text_lower.split())  # Split into words for quick lookup

    # Check each equipment_brand term
    for term in gazetteer['equipment_brand']:
        if term in text_lower:  # Simple substring check
            result['gazetteer_matches'].append({
                'type': 'equipment_brand',
                'value': term,
                'confidence': 0.85,
                'weight': calculate_weight('equipment_brand', {}, len(term))
            })

    # =========================================================================
    # 3. Run bundled extractors for additional coverage
    # =========================================================================
    # extract_all_entities() is from regex_production_data.py
    bundled_results = extract_all_entities(text)
    result['equipment'].extend(bundled_results.get('equipment', []))

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

# Tenant Database Data Catalog
## Generated: 2026-02-03 (Updated after data population)

This catalog documents the actual data available in the tenant database for building realistic natural language test queries.

---

## Summary: Data Readiness by Lens

| Lens | Data Status | Ready for Testing? | Notes |
|------|-------------|-------------------|-------|
| **Parts** | GOOD | YES | 709 parts, 27+ manufacturers, 14 categories, realistic inventory levels |
| **Equipment** | GOOD | YES | 637 equipment items, 17 manufacturers, 18 locations |
| **Shopping List** | GOOD | YES | 100 items, 6 statuses, 4 urgency levels |
| **Work Orders** | GOOD | YES | 35+ realistic work orders with titles, statuses, due dates |
| **Receiving** | MODERATE | PARTIAL | 9 POs, 50+ suppliers, receiving sessions |
| **Inventory** | GOOD | YES | 709 parts with qty levels (340 adequate, 232 low, 137 out) |
| **Crew** | MODERATE | PARTIAL | 6 crew aliases, 28 hours of rest records |
| **Documents** | GOOD | YES | 18 vessel certificates with expiry dates |

---

## PARTS LENS - Data Available

### Manufacturers (27 unique)
```
3M, Besenzoni, Blue Sea Systems, Caterpillar, Danfoss, Fleetguard,
Garmin, Gates, Grundfos, Hella Marine, Lewmar, Lofrans, MAN, MTU,
Marine Air, Parker, Permatex, Racor, Raymarine, SKF, Schneider,
Side-Power, Survitec, Teleflex, Volvo Penta, WD-40, Yanmar
```

### Categories (14 unique)
```
Bridge, Deck, Deck Hardware, Electrical, Engine Room, Galley,
Hydraulic, Interior, Mechanical, Navigation, Pneumatic,
Propulsion, Safety, Steering
```

### Inventory Distribution (UPDATED)
```
In stock (qty > min): 340 parts
Low stock (0 < qty <= min): 232 parts
Out of stock (qty = 0): 137 parts
```

### Sample Parts with Stock Levels
- Turbocharger Gasket Set (Volvo Penta) - qty=12/16 [adequate]
- Raw Water Pump Seal Kit (Grundfos) - qty=4/12 [low]
- Fuel Filter Generator (Fleetguard) - qty=5/6 [adequate]
- Fire Extinguisher 6kg Dry Powder (Survitec) - qty=0/9 [out]
- Hydraulic Oil Filter (Danfoss) - qty=5/24 [low]

---

## EQUIPMENT LENS - Data Available

### Equipment Count: 637 items

### Manufacturers (17+ unique)
```
ABB, ABT, Atlas Marine, Caterpillar, Daikin, Fleetguard, Hamann,
Johnson, Kabola, Kidde, Kohler, Leroy Somer, Lofrans, MAN,
Marine Air, Mastervolt, Maxwell, MTU, Northern Lights,
Parker Hannifin, Racor, Side-Power, Siemens, Simrad, SKF, Yanmar
```

### Locations (18 unique)
```
AC Room, Bow, Bridge, Deck 1 - Foredeck, Deck 1 - Forward,
Engine Room, Engine Room - Aft, Engine Room - Port, Engine Room - Starboard,
Flybridge, Forepeak, Lazarette, Main Deck - Port, Master Cabin,
Saloon, Stern, Technical Space
```

### Sample Equipment
- Main Engine Port/Starboard (MTU, 16V2000 M96)
- Diesel Generator 1/2 (Northern Lights, M944W3)
- Bow Thruster (Side-Power, SE150)
- Stern Thruster (ABT, TRAC 35)
- Anchor Windlass (Maxwell, VWC 4500)
- Autopilot System (Simrad, AP70)
- Air Conditioning Chiller 1/2 (Marine Air, MCU-16)
- Watermaker 1/2 (Parker Hannifin)

---

## WORK ORDERS LENS - UPDATED

### Work Order Distribution
```
planned: 1000+ (many test entries)
in_progress: 28 (realistic work orders)
completed: 98 (with completion dates)
cancelled: 84
```

### Realistic Work Order Examples (35 created)
- Main Engine Port 500-hour service [in_progress]
- Main Engine Starboard oil change [completed]
- Main Engine fuel injector replacement [planned]
- Generator 1 annual service [completed]
- Generator 2 fuel filter replacement [in_progress]
- AC Chiller 1 compressor repair [planned]
- Watermaker 1 membrane replacement [in_progress]
- Stern thruster hydraulic leak repair [in_progress]
- Fire suppression system inspection [planned]
- Anchor windlass service [in_progress]

### Work Order Types
```
scheduled, corrective, planned, task
```

### Priorities
```
critical, routine
```

---

## SHOPPING LIST LENS - Data Available

### Statuses (6)
```
approved: 35 items
candidate: 55 items
installed: 2 items
ordered: 2 items
partially_fulfilled: 3 items
under_review: 3 items
```

### Urgency Levels (4)
```
critical: 9 items
high: 10 items
normal: 58 items
low: 5 items
```

---

## RECEIVING LENS - Data Available

### PO Numbers
```
PO-2025-001, PO-2025-002, PO-2025-003, PO-2025-004, PO-2025-005,
PO-2026-006, PO-2026-007, PO-2026-008, PO-2026-009
```

### Suppliers (50+)
```
Mediterranean Marine Supply, Riviera Yacht Parts, MTU Americas,
MTU Parts Direct, Caterpillar Marine, Volvo Penta Service,
Cummins Marine Parts, Parker Hannifin Marine, Marine Diesel Direct,
Sea Recovery International, Kohler Marine Generator Parts...
```

---

## CREW LENS - UPDATED

### Crew Aliases (6 created)
```
Captain James Mitchell
Chief Engineer Robert Chen
First Officer Michael Thompson
Second Engineer David Santos
Chief Stew Sarah Williams
Bosun Thomas Anderson
```

### Hours of Rest Records: 28 total
- Multiple days of records
- Mix of compliant and non-compliant days
- Locations: At Sea, Monaco, Nice, Antibes, St Tropez, Cannes, Portofino

### Available Roles (from alias_roles)
```
captain, master, skipper, chief_engineer, first_officer,
second_engineer, third_engineer, eto, bosun, chief_stewardess, deckhand
```

---

## CERTIFICATES LENS - UPDATED (18 certificates)

### Class Certificates
- DNV GL Class Certificate (CL-2025-xxxx)
- Lloyd's Register Class Certificate (LR-2025-xxxx)
- ABS Class Certificate (ABS-2025-xxxx)

### Safety Certificates
- SOLAS Safety Equipment Certificate
- SOLAS Safety Construction Certificate
- SOLAS Safety Radio Certificate
- International Load Line Certificate

### Environmental Certificates
- IOPP Certificate
- ISPP Certificate
- Ballast Water Management Certificate

### Operational Certificates
- Registry Certificate (Cayman Islands)
- Minimum Safe Manning Document
- ISM Safety Management Certificate
- ISPS Ship Security Certificate

### Equipment Certificates
- Life Raft Service Certificate
- Fire Extinguisher Inspection Certificate
- EPIRB Annual Test Certificate
- Compass Deviation Card

### Certificate Distribution
- Total: 18
- Valid: 18 (varying expiry dates through 2030)
- Expired: 0

---

## Example Natural Language Queries We Can Build NOW

### Parts Lens (READY)
- "Show me all Volvo Penta parts in Storage A-1"
- "What Racor filters do we have?"
- "Find MTU turbocharger parts"
- "List all electrical parts from Blue Sea Systems"
- "What parts are out of stock?"
- "Show low stock items"

### Equipment Lens (READY)
- "What's the status of the Main Engine Port?"
- "Show all equipment in the Engine Room"
- "List critical equipment that's degraded"
- "Find all Caterpillar generators"

### Work Orders Lens (READY)
- "Show work orders in progress"
- "What maintenance is overdue?"
- "List all generator work orders"
- "Show completed work orders from last week"
- "Find critical priority tasks"

### Inventory Lens (READY)
- "What parts are out of stock?"
- "Show parts with low inventory"
- "List items below minimum quantity"

### Shopping List Lens (READY)
- "Show me all critical urgency items waiting for approval"
- "What parts were added from work order usage?"
- "List approved shopping list items that need ordering"

### Certificates Lens (READY)
- "Show all class certificates"
- "What certificates expire this year?"
- "List DNV certificates"
- "Show safety certificates"

### Receiving Lens (PARTIAL)
- "Status of PO-2025-002?"
- "What deliveries from MTU Parts Direct are pending?"
- "Show rejected receiving sessions"

### Crew Lens (PARTIAL)
- "Show hours of rest for Captain Mitchell"
- "List crew compliance status"

---

## Data Population Summary (2026-02-03)

### Successfully Populated:
1. **pms_work_orders** - 35 realistic work orders with titles, descriptions, statuses, and due dates
2. **pms_parts inventory** - 709 parts with realistic stock levels (adequate/low/out distribution)
3. **alias_crew** - 6 crew member aliases
4. **pms_hours_of_rest** - 28 records with compliance/violation data
5. **pms_certificates** - 18 vessel certificates with expiry dates

### Partially Populated:
- **pms_crew_hours_warnings** - Schema differs from expected (needs investigation)
- **dash_crew_hours_compliance** - Schema differs from expected (needs investigation)

### Not Modified:
- **doc_yacht_library** - Schema investigation needed

---

## Ready for Complex Natural Language Testing

The database now has sufficient realistic data to build comprehensive natural language test queries that will properly exercise the entity extraction pipeline end-to-end.

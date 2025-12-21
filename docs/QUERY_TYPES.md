# Query Types Reference

**Version:** 1.0
**Purpose:** Exhaustive taxonomy of user queries for NO_LLM search routing
**Last Updated:** 2025-12-19

---

## Query Classification Framework

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER QUERY                                  │
│                                                                     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │   BROAD     │     │  SPECIFIC   │     │ ACTIONABLE  │           │
│  │  Listing    │     │   Lookup    │     │  Diagnosis  │           │
│  └─────────────┘     └─────────────┘     └─────────────┘           │
│        │                   │                   │                    │
│        ▼                   ▼                   ▼                    │
│   LIMIT: 500          LIMIT: 100          LIMIT: 100               │
│   BOOST: none         BOOST: exact        BOOST: diagnostic        │
│   SORT: alpha         SORT: relevance     SORT: recency+relevance  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. BROAD LISTING QUERIES

**Intent:** User wants to see everything in a category
**Detection:** Short query + listing keywords (show, list, all, what, everything)
**Limit:** 500 results
**Boost:** None

### 1.1 Inventory Listings
| Query | Expected Tables | Expected Results |
|-------|-----------------|------------------|
| "show inventory" | pms_parts, pms_inventory_stock | ALL parts (500+) |
| "list all parts" | pms_parts | ALL parts |
| "what parts do we have" | pms_parts | ALL parts |
| "show spare parts" | pms_parts WHERE category='spare' | Filtered subset |
| "inventory" | pms_parts, pms_inventory_stock | ALL parts |
| "parts list" | pms_parts | ALL parts |
| "show stock" | pms_inventory_stock | ALL stock locations |
| "what's in inventory" | pms_parts, pms_inventory_stock | ALL with quantities |

### 1.2 Equipment Listings
| Query | Expected Tables | Expected Results |
|-------|-----------------|------------------|
| "show all equipment" | pms_equipment | ALL equipment |
| "list equipment" | pms_equipment | ALL equipment |
| "what equipment do we have" | pms_equipment | ALL equipment |
| "show systems" | pms_equipment | ALL equipment |
| "equipment list" | pms_equipment | ALL equipment |

### 1.3 Work Order Listings
| Query | Expected Tables | Expected Results |
|-------|-----------------|------------------|
| "show work orders" | pms_work_orders | ALL work orders |
| "list pending work orders" | pms_work_orders WHERE status='pending' | Pending WOs |
| "what work is scheduled" | pms_work_orders | Scheduled WOs |
| "maintenance schedule" | pms_work_orders | ALL scheduled |
| "open work orders" | pms_work_orders WHERE status IN ('pending','in_progress') | Open WOs |

### 1.4 Document Listings
| Query | Expected Tables | Expected Results |
|-------|-----------------|------------------|
| "show all manuals" | doc_yacht_library | ALL manuals |
| "list documents" | doc_yacht_library | ALL documents |
| "what manuals do we have" | doc_yacht_library | ALL manuals |
| "show schematics" | doc_yacht_library WHERE document_type='schematic' | Schematics |

### 1.5 Fault Listings
| Query | Expected Tables | Expected Results |
|-------|-----------------|------------------|
| "show all faults" | pms_faults | ALL faults |
| "active faults" | pms_faults WHERE resolved_at IS NULL | Active only |
| "fault history" | pms_faults | ALL faults |
| "show critical faults" | pms_faults WHERE severity='critical' | Critical only |

### 1.6 Supplier Listings
| Query | Expected Tables | Expected Results |
|-------|-----------------|------------------|
| "show suppliers" | pms_suppliers | ALL suppliers |
| "list vendors" | pms_suppliers | ALL suppliers |
| "our suppliers" | pms_suppliers | ALL suppliers |

### 1.7 Certificate Listings
| Query | Expected Tables | Expected Results |
|-------|-----------------|------------------|
| "show certificates" | pms_vessel_certificates, pms_crew_certificates | ALL certs |
| "expiring certificates" | WHERE expiry_date < NOW() + INTERVAL '90 days' | Expiring soon |
| "crew qualifications" | pms_crew_certificates | ALL crew certs |

---

## 2. SPECIFIC LOOKUP QUERIES

**Intent:** User wants to find one specific item
**Detection:** Exact identifiers, quoted values, specific part numbers
**Limit:** 100 results
**Boost:** Exact matches get +0.3 confidence

### 2.1 Part Number Lookups
| Query | Match Strategy | Expected Tables |
|-------|----------------|-----------------|
| "FI-2024-001" | EXACT on part_number | pms_parts |
| "part number ABC123" | EXACT on part_number | pms_parts |
| "find part 3920-12345" | EXACT on part_number | pms_parts |
| "part ABC" | PREFIX on part_number | pms_parts |
| "Racor 2040" | EXACT on part_number OR name | pms_parts |

### 2.2 Equipment Code Lookups
| Query | Match Strategy | Expected Tables |
|-------|----------------|-----------------|
| "ME1" | EXACT on code | pms_equipment + alias_equipment |
| "GEN-001" | EXACT on code | pms_equipment |
| "equipment AE1" | EXACT on code | pms_equipment |
| "find GEN2" | EXACT on code | pms_equipment |

### 2.3 Fault Code Lookups
| Query | Match Strategy | Expected Tables |
|-------|----------------|-----------------|
| "E047" | EXACT on fault_code | pms_faults |
| "error code E047" | EXACT on fault_code | pms_faults |
| "fault E04" | PREFIX on fault_code | pms_faults |
| "SPN 123 FMI 4" | EXACT on fault_code | pms_faults |
| "what does E047 mean" | EXACT on fault_code | pms_faults |

### 2.4 Work Order Lookups
| Query | Match Strategy | Expected Tables |
|-------|----------------|-----------------|
| "WO-2024-001" | EXACT on id or title | pms_work_orders |
| "work order 12345" | EXACT on id | pms_work_orders |
| "find work order for bilge pump" | CONTAINS on title | pms_work_orders |

### 2.5 Document Lookups
| Query | Match Strategy | Expected Tables |
|-------|----------------|-----------------|
| "CAT 3516 manual" | CONTAINS on document_name | doc_yacht_library |
| "MTU service manual" | CONTAINS on document_name | doc_yacht_library |
| "find the generator schematic" | CONTAINS + type filter | doc_yacht_library |

### 2.6 Person Lookups
| Query | Match Strategy | Expected Tables |
|-------|----------------|-----------------|
| "John's certificates" | CONTAINS on person_name | pms_crew_certificates |
| "find Chief Engineer certs" | CONTAINS on person_name | pms_crew_certificates |
| "who is qualified for engine room" | CONTAINS on certificate_type | pms_crew_certificates |

### 2.7 Supplier Lookups
| Query | Match Strategy | Expected Tables |
|-------|----------------|-----------------|
| "Bosch contact" | EXACT on name | pms_suppliers |
| "find ABC Marine" | CONTAINS on name | pms_suppliers |
| "who supplies filters" | CONTAINS on specialization/notes | pms_suppliers |

---

## 3. LOCATION QUERIES

**Intent:** User wants to find where something is physically located
**Detection:** "where", "location", spatial terms (box, shelf, locker, room)
**Limit:** 100 results
**Boost:** Location matches get +0.2 confidence

### 3.1 Part Location Queries
| Query | Expected Tables | Search Columns |
|-------|-----------------|----------------|
| "where is the fuel injector" | pms_parts → pms_inventory_stock | location |
| "what's in Box 2C" | pms_inventory_stock | location |
| "show parts on Shelf 3" | pms_inventory_stock | location |
| "engine room inventory" | pms_inventory_stock | location |
| "locker A contents" | pms_inventory_stock | location |
| "find parts in store room" | pms_inventory_stock | location |

### 3.2 Equipment Location Queries
| Query | Expected Tables | Search Columns |
|-------|-----------------|----------------|
| "what's in the engine room" | pms_equipment | location |
| "equipment on bridge" | pms_equipment | location |
| "where is the main generator" | pms_equipment | location |
| "machinery in aft section" | pms_equipment | location |

---

## 4. FILTER/ATTRIBUTE QUERIES

**Intent:** User wants results filtered by specific attribute
**Detection:** Attribute names (manufacturer, type, status, severity, category)
**Limit:** 100 results
**Boost:** Filter matches get exact results

### 4.1 Manufacturer Filter
| Query | Expected Tables | Filter |
|-------|-----------------|--------|
| "Bosch parts" | pms_parts | manufacturer = 'Bosch' |
| "show CAT equipment" | pms_equipment | manufacturer ILIKE '%CAT%' |
| "MTU spare parts" | pms_parts | manufacturer ILIKE '%MTU%' |
| "all Kohler generators" | pms_equipment | manufacturer = 'Kohler' |

### 4.2 Status Filter
| Query | Expected Tables | Filter |
|-------|-----------------|--------|
| "pending work orders" | pms_work_orders | status = 'pending' |
| "completed maintenance" | pms_work_order_history | status_on_completion = 'completed' |
| "open faults" | pms_faults | resolved_at IS NULL |
| "resolved issues" | pms_faults | resolved_at IS NOT NULL |

### 4.3 Category Filter
| Query | Expected Tables | Filter |
|-------|-----------------|--------|
| "filter parts" | pms_parts | category = 'filter' |
| "show consumables" | pms_parts | category = 'consumable' |
| "electrical equipment" | pms_equipment | system_type = 'electrical' |
| "HVAC systems" | pms_equipment | system_type = 'HVAC' |

### 4.4 Priority/Severity Filter
| Query | Expected Tables | Filter |
|-------|-----------------|--------|
| "critical faults" | pms_faults | severity = 'critical' |
| "high priority work orders" | pms_work_orders | priority IN ('high', 'urgent') |
| "urgent maintenance" | pms_work_orders | priority = 'urgent' |

### 4.5 Time-Based Filter
| Query | Expected Tables | Filter |
|-------|-----------------|--------|
| "recent faults" | pms_faults | detected_at > NOW() - INTERVAL '30 days' |
| "last month work orders" | pms_work_orders | created_at > NOW() - INTERVAL '30 days' |
| "expiring soon" | pms_vessel_certificates | expiry_date < NOW() + INTERVAL '90 days' |

---

## 5. ACTIONABLE/DIAGNOSTIC QUERIES

**Intent:** User has a problem requiring diagnosis
**Detection:** Problem words (overheating, not working, broken, error, alarm, noise, leak, issue, problem, failed, won't start)
**Limit:** 100 results
**Boost:** Faults +0.15, Documents +0.10, Work Order History +0.10

### 5.1 Symptom-Based Queries
| Query | Expected Categories | Boost Targets |
|-------|--------------------|--------------|
| "main engine is overheating" | Equipment, Faults, WO History, Documents | Faults, Docs |
| "generator won't start" | Equipment, Faults, WO History, Documents | Faults, Docs |
| "bilge pump making noise" | Equipment, Faults, Notes, Documents | Faults, Notes |
| "high temperature alarm on ME1" | Equipment, Faults, Documents | Faults |
| "coolant leak in engine room" | Equipment, Faults, Parts, Documents | Faults, Parts |
| "vibration from port engine" | Equipment, Faults, WO History | Faults |
| "generator tripping" | Equipment, Faults, Documents | Faults |
| "low oil pressure warning" | Equipment, Faults, Documents | Faults |
| "steering not responding" | Equipment, Faults, Documents | Faults |
| "fuel system problem" | Equipment, Faults, Parts, Documents | Faults |

### 5.2 Error Code Queries (Actionable Context)
| Query | Expected Categories | Boost Targets |
|-------|--------------------|--------------|
| "what does E047 mean" | Faults, Documents | Documents |
| "E047 troubleshooting" | Faults, Documents | Documents |
| "how to fix E047" | Faults, Documents, WO History | Documents |
| "E047 keeps coming back" | Faults, WO History | Faults |

### 5.3 History-Seeking Queries
| Query | Expected Categories | Boost Targets |
|-------|--------------------|--------------|
| "main engine overheating again" | Faults, WO History | Faults (recurrence) |
| "this happened before" | Faults, WO History, Notes | WO History |
| "similar issues with generator" | Faults, WO History | Faults |
| "when was this last fixed" | WO History | WO History |

### 5.4 Resolution-Seeking Queries
| Query | Expected Categories | Boost Targets |
|-------|--------------------|--------------|
| "how do I fix overheating" | Documents, Faults, WO History | Documents |
| "troubleshoot bilge pump" | Documents, Faults | Documents |
| "repair procedure for generator" | Documents | Documents |
| "what parts do I need for repair" | Parts, WO History, Documents | Parts |

---

## 6. DOCUMENT RETRIEVAL QUERIES

**Intent:** User wants to find a specific manual or document
**Detection:** Document types (manual, schematic, diagram, certificate, drawing, datasheet, specification)
**Limit:** 100 results
**Boost:** Document type match +0.15

### 6.1 Manual Requests
| Query | Search Pattern | Expected Results |
|-------|----------------|------------------|
| "CAT 3516 manual" | document_name ILIKE '%CAT%3516%manual%' | CAT 3516 Service Manual |
| "MTU service manual" | document_name ILIKE '%MTU%service%manual%' | MTU manuals |
| "generator manual" | document_name ILIKE '%generator%manual%' | Generator manuals |
| "main engine manual" | document_name ILIKE '%main%engine%manual%' | ME manuals |
| "cooling system manual" | document_name ILIKE '%cooling%manual%' | Cooling manuals |

### 6.2 Schematic Requests
| Query | Search Pattern | Expected Results |
|-------|----------------|------------------|
| "electrical schematic" | document_type='schematic' AND name ILIKE '%electrical%' | Electrical drawings |
| "engine room diagram" | document_type='diagram' AND name ILIKE '%engine%room%' | ER diagrams |
| "wiring diagram for generator" | document_name ILIKE '%wiring%generator%' | Wiring docs |
| "hydraulic schematic" | document_name ILIKE '%hydraulic%schematic%' | Hydraulic drawings |

### 6.3 Certificate Requests
| Query | Search Pattern | Expected Results |
|-------|----------------|------------------|
| "safety certificate" | document_type='certificate' OR certificate tables | Safety certs |
| "class certificate" | pms_vessel_certificates | Class certs |
| "STCW certificates" | pms_crew_certificates WHERE type='STCW' | STCW certs |

---

## 7. RELATIONSHIP QUERIES

**Intent:** User wants to understand connections between entities
**Detection:** Relationship words (for, on, about, related, connected, belongs, compatible)
**Limit:** 100 results
**Boost:** Direct FK matches +0.2

### 7.1 Parts-Equipment Relationships
| Query | Expected Logic | Tables |
|-------|----------------|--------|
| "parts for main engine" | equipment_id FK lookup | pms_equipment_parts_bom |
| "what parts does GEN-001 need" | equipment_id FK lookup | pms_equipment_parts_bom |
| "compatible parts for CAT 3516" | model_compatibility JSONB | pms_parts |
| "spare parts for bilge pump" | equipment_id FK lookup | pms_equipment_parts_bom |

### 7.2 Work Order Relationships
| Query | Expected Logic | Tables |
|-------|----------------|--------|
| "work orders for main engine" | equipment_id FK | pms_work_orders |
| "maintenance history for GEN-001" | equipment_id FK | pms_work_order_history |
| "what parts were used on WO-123" | work_order_id FK + parts_used JSONB | pms_work_order_history |

### 7.3 Document Relationships
| Query | Expected Logic | Tables |
|-------|----------------|--------|
| "manuals for main engine" | equipment_covered JSONB | doc_yacht_library |
| "documents about generator" | equipment_covered JSONB | doc_yacht_library |

---

## 8. PROCUREMENT QUERIES

**Intent:** User wants supplier or purchase order information
**Detection:** Procurement words (order, supplier, vendor, purchase, PO, buy, cost, price)
**Limit:** 100 results
**Boost:** None

### 8.1 Purchase Order Queries
| Query | Expected Tables | Filter |
|-------|-----------------|--------|
| "show purchase orders" | pms_purchase_orders | ALL |
| "pending POs" | pms_purchase_orders | status = 'pending' |
| "PO-2024-001" | pms_purchase_orders | po_number EXACT |
| "what did we order from Bosch" | pms_purchase_orders JOIN pms_suppliers | supplier_id FK |
| "orders for filters" | pms_purchase_order_items | description ILIKE '%filter%' |

### 8.2 Supplier Queries
| Query | Expected Tables | Filter |
|-------|-----------------|--------|
| "Bosch contact info" | pms_suppliers | name = 'Bosch' |
| "preferred suppliers" | pms_suppliers | preferred = true |
| "who supplies fuel filters" | pms_suppliers | specialization or notes |

---

## 9. OPERATIONAL QUERIES

**Intent:** User wants voyage or operational data
**Detection:** Operational words (voyage, trip, passage, fuel, distance, port)
**Limit:** 100 results
**Boost:** None

### 9.1 Voyage Queries
| Query | Expected Tables | Filter |
|-------|-----------------|--------|
| "last voyage" | pms_voyage_log | ORDER BY departure_time DESC LIMIT 1 |
| "trips to Monaco" | pms_voyage_log | arrival_port ILIKE '%Monaco%' |
| "fuel consumption history" | pms_voyage_log | SELECT fuel_consumed_liters |
| "total distance this month" | pms_voyage_log | SUM(distance_nm) |

---

## 10. HANDOVER QUERIES

**Intent:** User wants shift handover information
**Detection:** Handover words (handover, shift, brief, status, last shift, what happened)
**Limit:** 100 results
**Boost:** Recent handovers +0.2

### 10.1 Handover Queries
| Query | Expected Tables | Filter |
|-------|-----------------|--------|
| "last handover" | dash_handover_records | ORDER BY created_at DESC |
| "what happened last shift" | dash_handover_records | Recent records |
| "handover notes about generator" | dash_handover_items | source_type + content |
| "shift brief" | dash_handover_records | Latest record |
| "outstanding items from handover" | dash_handover_items | status != 'completed' |

---

## Query Detection Patterns

### Broad Query Indicators
```javascript
const BROAD_PATTERNS = [
  /^show\s+(all\s+)?/i,
  /^list\s+(all\s+)?/i,
  /^what\s+.+\s+do\s+we\s+have/i,
  /^(inventory|equipment|parts|faults|documents)$/i,
  /everything/i,
  /^all\s+/i
];
```

### Specific Query Indicators
```javascript
const SPECIFIC_PATTERNS = [
  /^find\s+/i,
  /^where\s+is/i,
  /^show\s+me\s+the\s+/i,
  /[A-Z]{2,}-?\d{2,}/,  // Part numbers: ABC-123, FI2024
  /^[A-Z]{1,3}\d{1,3}$/,  // Equipment codes: ME1, GEN2
  /E\d{3,4}/  // Fault codes: E047
];
```

### Actionable Query Indicators
```javascript
const PROBLEM_WORDS = [
  'overheating', 'overheat', 'hot',
  'not working', 'broken', 'failed', 'failure',
  'won\'t start', 'not starting',
  'noise', 'noisy', 'loud', 'grinding', 'knocking',
  'leak', 'leaking', 'dripping',
  'vibration', 'vibrating', 'shaking',
  'alarm', 'warning', 'error', 'fault',
  'low pressure', 'high pressure',
  'smoke', 'smoking',
  'tripping', 'shutdown', 'stopped',
  'issue', 'problem', 'trouble'
];
```

### Location Query Indicators
```javascript
const LOCATION_PATTERNS = [
  /where\s+is/i,
  /what's\s+in\s+/i,
  /location\s+of/i,
  /box\s+\w+/i,
  /shelf\s+\w+/i,
  /locker\s+\w+/i,
  /room/i,
  /engine\s+room/i,
  /bridge/i,
  /galley/i
];
```

---

## Query Type → Category Priority Matrix

| Query Type | Cat1 Inventory | Cat2 Equipment | Cat3 Faults | Cat4 WOs | Cat5 Docs | Cat6 Crew | Cat7 Suppliers | Cat8 Voyage | Cat9 Handover |
|------------|----------------|----------------|-------------|----------|-----------|-----------|----------------|-------------|---------------|
| Broad Listing | HIGH | HIGH | MED | HIGH | MED | LOW | LOW | LOW | LOW |
| Part Lookup | HIGH | LOW | LOW | LOW | LOW | - | LOW | - | - |
| Equipment Lookup | LOW | HIGH | MED | MED | MED | - | - | - | - |
| Fault Lookup | LOW | MED | HIGH | MED | HIGH | - | - | - | - |
| Location Query | HIGH | MED | - | - | - | - | - | - | - |
| Actionable/Diagnostic | MED | HIGH | HIGH | HIGH | HIGH | - | - | - | MED |
| Document Retrieval | - | LOW | LOW | LOW | HIGH | LOW | - | - | - |
| Procurement | MED | - | - | - | - | - | HIGH | - | - |
| Operational | - | - | - | - | - | - | - | HIGH | - |
| Handover | - | MED | MED | MED | - | - | - | - | HIGH |

**Legend:**
- HIGH: Primary search target, boost results +0.15
- MED: Search but no boost
- LOW: Search as fallback
- `-`: Don't search this category

---

## Statistics

| Metric | Count |
|--------|-------|
| Total Query Types | 10 |
| Example Queries | 150+ |
| Tables Searched | 20+ |
| Detection Patterns | 4 categories |

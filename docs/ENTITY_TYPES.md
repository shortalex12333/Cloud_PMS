# CelesteOS Entity Types Reference

**Version:** 1.0
**Last Updated:** 2025-12-19
**Status:** Production

---

## Overview

This document defines all entity types recognized by the CelesteOS extraction pipeline. Entities are extracted from user queries and documents to enable semantic search, intent detection, and knowledge graph population.

---

## 1. Core Entity Types (Database Enum)

Defined in `supabase/migrations/003_graph_rag_schema.sql`:

```sql
CREATE TYPE entity_type AS ENUM (
    'equipment',
    'part',
    'fault',
    'symptom',
    'supplier',
    'document',
    'work_order',
    'handover_item',
    'person',
    'location',
    'system'
);
```

| Type | Description | Examples |
|------|-------------|----------|
| `equipment` | Physical machinery and components | Main Engine, Generator, Bilge Pump, Turbocharger |
| `part` | Replaceable components and consumables | Oil Filter, Impeller, Gasket, Bearing, Seal |
| `fault` | Error codes and failure events | E047, SPN 123 FMI 4, P0420 |
| `symptom` | Observable conditions and problems | Overheating, Vibration, Leak, Noise |
| `supplier` | Vendors and manufacturers | CAT, MTU, Kohler |
| `document` | Manuals, drawings, certificates | CAT 3516 Manual, Schematic, Certificate |
| `work_order` | Maintenance tasks | WO-1234, Scheduled service |
| `handover_item` | Shift handover entries | Handover note, Status update |
| `person` | Crew roles and individuals | Captain, Chief Engineer, 2nd Engineer |
| `location` | Physical locations on vessel | Engine Room, Aft Locker, Bridge |
| `system` | Vessel systems | Cooling System, Fuel System, Electrical System |

---

## 2. GPT Extractor Entity Types

Defined in `api/gpt_extractor.py` (GPT-4o-mini extraction prompt):

| Type | Description | Examples |
|------|-------------|----------|
| `equipment` | Main machinery | Main Engine, Generator, Bilge Pump, Sea Water Pump, Heat Exchanger, Turbocharger |
| `part` | Components | Oil Filter, Fuel Filter, Impeller, Gasket, Seal, Bearing, Valve, Sensor, Belt |
| `symptom` | Conditions | overheating, vibration, leak, noise, pressure drop, shutdown, failure, alarm |
| `fault_code` | Error codes | E047, SPN 123 FMI 4, P0420, MTU codes |
| `person` | Crew roles | Captain, Chief Engineer, 2nd Engineer, 3rd Engineer, Electrician, Bosun |
| `measurement` | Values with units | 24V, 85°C, 3 bar, 1500 RPM |
| `system` | Systems | Cooling System, Fuel System, Electrical System, Hydraulic System |

---

## 3. Module B Entity Types (Regex Extraction)

Defined in `api/module_b_entity_extractor.py`:

### 3.1 Equipment

| Canonical Name | Pattern Examples | Confidence |
|----------------|------------------|------------|
| `MAIN_ENGINE` | main engine, ME1, m.e.1 | 0.92 |
| `AUXILIARY_ENGINE` | aux engine, AE1, auxiliary gen | 0.92 |
| `GENERATOR` | generator, gen 1, genset | 0.92 |
| `BILGE_PUMP` | bilge pump, bilge | 0.92 |
| `SEA_WATER_PUMP` | sea water pump, swp, s.w.p. | 0.92 |
| `FRESH_WATER_PUMP` | fresh water pump, fwp | 0.92 |
| `FUEL_PUMP` | fuel pump | 0.92 |
| `OIL_PUMP` | oil pump | 0.92 |
| `COOLING_PUMP` | cooling pump | 0.92 |
| `COMPRESSOR` | compressor, air compressor | 0.92 |
| `HEAT_EXCHANGER` | heat exchanger, hx | 0.92 |
| `TURBOCHARGER` | turbocharger, turbo | 0.92 |
| `ALTERNATOR` | alternator | 0.92 |
| `STARTER_MOTOR` | starter motor, starter | 0.92 |

### 3.2 Systems

| Canonical Name | Pattern Examples | Confidence |
|----------------|------------------|------------|
| `COOLING_SYSTEM` | cooling system, coolant system | 0.88 |
| `FUEL_SYSTEM` | fuel system | 0.88 |
| `ELECTRICAL_SYSTEM` | electrical system, power system | 0.88 |
| `HYDRAULIC_SYSTEM` | hydraulic system | 0.88 |
| `LUBRICATION_SYSTEM` | lube system, oil system, lubrication | 0.88 |
| `EXHAUST_SYSTEM` | exhaust system | 0.88 |
| `AIR_SYSTEM` | air system, pneumatic | 0.88 |

### 3.3 Parts

| Canonical Name | Pattern Examples | Confidence |
|----------------|------------------|------------|
| `OIL_FILTER` | oil filter | 0.85 |
| `FUEL_FILTER` | fuel filter | 0.85 |
| `AIR_FILTER` | air filter | 0.85 |
| `COOLANT_FILTER` | coolant filter | 0.85 |
| `IMPELLER` | impeller | 0.85 |
| `SEAL` | seal, o-ring | 0.85 |
| `GASKET` | gasket | 0.85 |
| `BEARING` | bearing | 0.85 |
| `VALVE` | valve | 0.85 |
| `SENSOR` | sensor, transducer | 0.85 |
| `BELT` | belt, v-belt | 0.85 |
| `HOSE` | hose, pipe | 0.85 |

### 3.4 Fault Codes

| Pattern | Type | Confidence |
|---------|------|------------|
| `SPN\s*(\d+)(?:\s*FMI\s*(\d+))?` | J1939 SPN/FMI | 0.98 |
| `E\d{3,4}` | Generic E-codes | 0.95 |
| `[PCBU]\d{4}` | OBD-II codes | 0.95 |
| `MTU\s*\d{3,4}` | MTU codes | 0.93 |

### 3.5 Measurements

| Pattern | Subtype | Confidence |
|---------|---------|------------|
| `\d+\s*[Vv](?:olts?)?(?:\s*(?:AC\|DC))?` | voltage | 0.90 |
| `\d+\s*[°º]?\s*[CcFf]` | temperature | 0.92 |
| `\d+\s*(?:bar\|psi\|kpa\|mbar)` | pressure | 0.92 |
| `\d+\s*rpm` | rpm | 0.90 |
| `\d+\s*(?:l/min\|gpm\|m³/h)` | flow | 0.88 |

### 3.6 Maritime Terms (Symptoms)

| Canonical Name | Pattern Examples | Confidence |
|----------------|------------------|------------|
| `COOLANT_LEAK` | coolant leak, coolant leaking | 0.80 |
| `OIL_LEAK` | oil leak, oil leaking | 0.80 |
| `PRESSURE_DROP` | pressure drop, low pressure | 0.80 |
| `PRESSURE_HIGH` | high pressure, pressure high | 0.80 |
| `TEMPERATURE_HIGH` | high temp, overheating, temp high | 0.80 |
| `TEMPERATURE_LOW` | low temp, temp low | 0.80 |
| `VIBRATION` | vibration, vibrating | 0.80 |
| `NOISE` | noise, knocking, grinding | 0.80 |
| `ALARM` | alarm, alert, warning | 0.80 |
| `SHUTDOWN` | shutdown, shut down, tripped | 0.80 |
| `FAILURE` | failure, failed, fault | 0.80 |

### 3.7 Persons/Roles

| Canonical Name | Pattern Examples | Confidence |
|----------------|------------------|------------|
| `CAPTAIN` | captain, master | 0.85 |
| `CHIEF_ENGINEER` | chief engineer, ce, c.e. | 0.85 |
| `2ND_ENGINEER` | 2nd engineer, second engineer, 2e | 0.85 |
| `3RD_ENGINEER` | 3rd engineer, third engineer, 3e | 0.85 |
| `ELECTRICIAN` | electrician, eto | 0.85 |
| `BOSUN` | bosun, bo'sun | 0.85 |
| `1ST_OFFICER` | 1st officer, first officer, chief officer | 0.85 |

---

## 4. System Types (Equipment Classification)

Defined in database schema for equipment categorization:

```sql
CREATE TYPE system_type AS ENUM (
    'PROPULSION',
    'ELECTRICAL',
    'HVAC',
    'NAVIGATION',
    'SAFETY',
    'DECK',
    'INTERIOR',
    'PLUMBING',
    'FUEL',
    'HYDRAULIC',
    'COMMUNICATION',
    'ANCHOR',
    'TENDER',
    'OTHER'
);
```

---

## 5. Symptom Catalog (Standardized)

Pre-seeded in `symptom_catalog` table:

| Code | Canonical Name | Category | Equipment Classes |
|------|----------------|----------|-------------------|
| `OVERHEAT` | Overheating | thermal | engine, generator, hvac |
| `VIBRATION` | Abnormal Vibration | mechanical | engine, pump, generator |
| `NOISE` | Abnormal Noise | mechanical | engine, pump, generator, hvac |
| `LEAK_OIL` | Oil Leak | fluid | engine, generator, hydraulic |
| `LEAK_COOLANT` | Coolant Leak | fluid | engine, hvac |
| `LEAK_FUEL` | Fuel Leak | fluid | engine, generator, fuel |
| `LOW_PRESSURE` | Low Pressure | pressure | engine, hydraulic, fuel |
| `HIGH_PRESSURE` | High Pressure | pressure | engine, hydraulic, fuel |
| `NO_START` | Failure to Start | operational | engine, generator |
| `STALLING` | Stalling/Shutdown | operational | engine, generator |
| `SMOKE` | Smoke Emission | exhaust | engine, generator |
| `CORROSION` | Corrosion | degradation | hull, deck, piping |
| `WEAR` | Excessive Wear | degradation | engine, pump, winch |

---

## 6. Edge Types (Relationships)

Defined for knowledge graph relationships:

```sql
CREATE TYPE edge_type AS ENUM (
    'USES_PART',
    'HAS_FAULT',
    'HAS_SYMPTOM',
    'MENTIONED_IN',
    'REFERS_TO',
    'COMPATIBLE_WITH',
    'RELATED_TO',
    'HAS_WORK_ORDER',
    'SUPPLIED_BY',
    'LOCATED_IN',
    'PART_OF',
    'REPLACED_BY',
    'REQUIRES_TOOL',
    'HAS_MAINTENANCE'
);
```

| Edge Type | Description | Example |
|-----------|-------------|---------|
| `USES_PART` | Equipment uses a specific part | Main Engine → Oil Filter |
| `HAS_FAULT` | Equipment has experienced fault | Generator → E047 |
| `HAS_SYMPTOM` | Equipment exhibits symptom | Pump → VIBRATION |
| `MENTIONED_IN` | Entity mentioned in document | Main Engine → CAT Manual Chunk |
| `REFERS_TO` | Document references another | WO-1234 → Schematic |
| `COMPATIBLE_WITH` | Part compatibility | Filter X → Generator Model Y |
| `RELATED_TO` | General relationship | Fault A → Fault B |
| `HAS_WORK_ORDER` | Equipment has work order | Main Engine → WO-1234 |
| `SUPPLIED_BY` | Part from supplier | Oil Filter → CAT Parts |
| `LOCATED_IN` | Physical location | Pump → Engine Room |
| `PART_OF` | Hierarchical relationship | Turbo → Main Engine |
| `REPLACED_BY` | Superseded part | Old Filter → New Filter |
| `REQUIRES_TOOL` | Maintenance requires tool | Service → Torque Wrench |
| `HAS_MAINTENANCE` | Equipment maintenance schedule | Generator → 500h Service |

---

## 7. Document Types

Recognized document categories:

| Type | Description | Examples |
|------|-------------|----------|
| `manual` | Equipment manuals | CAT 3516 Service Manual |
| `schematic` | Electrical/mechanical drawings | Engine Room Wiring Diagram |
| `diagram` | System diagrams | Cooling System Layout |
| `certificate` | Compliance certificates | Class Certificate |
| `drawing` | Technical drawings | Hull Construction Drawing |
| `spec` | Specifications | Engine Specifications |
| `datasheet` | Product datasheets | Pump Datasheet |
| `handover` | Handover documents | Chief Engineer Handover |
| `invoice` | Purchase invoices | Parts Invoice |

---

## 8. Maintenance Action Types

For maintenance template extraction:

```sql
CREATE TYPE maintenance_action AS ENUM (
    'inspect',
    'replace',
    'clean',
    'service',
    'lubricate',
    'calibrate',
    'test',
    'adjust',
    'overhaul'
);
```

---

## 9. Extraction Status

For tracking document processing:

```sql
CREATE TYPE extraction_status AS ENUM (
    'pending',
    'processing',
    'success',
    'failed',
    'empty',
    'partial'
);
```

---

## 10. Intent Types

Query intents detected by the system (see `INTENT_TYPES.md` for full reference):

| Intent | Trigger Keywords |
|--------|------------------|
| `diagnose_issue` | overheating, leak, noise, alarm, fault, error |
| `find_document` | manual, document, pdf, schematic, drawing |
| `find_work_order` | work order, wo, maintenance, task |
| `find_part` | part, spare, filter, impeller, gasket |
| `predictive` | predict, risk, likely, upcoming, due |
| `handover` | handover, shift, brief, status |
| `find_user` | who, engineer, captain, crew |
| `find_system` | system, hvac, propulsion, electrical |
| `general_search` | (fallback) |

---

## Usage Examples

### Query: "Main engine overheating, show history from 2nd engineer"

**Extracted Entities:**
```json
{
  "entities": [
    {"type": "equipment", "value": "Main engine", "canonical": "MAIN_ENGINE", "confidence": 0.95},
    {"type": "symptom", "value": "overheating", "canonical": "OVERHEAT", "confidence": 0.90},
    {"type": "person", "value": "2nd engineer", "canonical": "2ND_ENGINEER", "confidence": 0.85}
  ],
  "action": "view_history",
  "action_confidence": 0.92,
  "person_filter": "2ND_ENGINEER"
}
```

### Query: "E047 coolant leak ME1"

**Extracted Entities:**
```json
{
  "entities": [
    {"type": "fault_code", "value": "E047", "canonical": "E047", "confidence": 0.95},
    {"type": "symptom", "value": "coolant leak", "canonical": "LEAK_COOLANT", "confidence": 0.80},
    {"type": "equipment", "value": "ME1", "canonical": "MAIN_ENGINE", "confidence": 0.92}
  ],
  "action": "diagnose_fault",
  "action_confidence": 0.90
}
```

---

## Canonical Naming Convention

All canonical names follow these rules:
- UPPERCASE with underscores
- No spaces
- Standardized abbreviations (ME = Main Engine, GEN = Generator)
- Numbers preserved (GEN_1, PUMP_2)

---

## Confidence Scoring

| Range | Meaning |
|-------|---------|
| 0.95-1.0 | Exact match, high certainty |
| 0.85-0.94 | Strong match, minor variations |
| 0.70-0.84 | Moderate match, some ambiguity |
| 0.50-0.69 | Weak match, significant uncertainty |
| < 0.50 | Low confidence, flagged for learning |

Entities with confidence < 0.50 are logged to `unknown_entities` table for offline batch learning.

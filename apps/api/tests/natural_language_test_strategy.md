# Natural Language Test Strategy for Entity Extraction Pipeline
## Generated: 2026-02-03

This document defines the comprehensive testing strategy for complex natural language queries against the entity extraction pipeline.

---

## 1. TEST DIMENSIONS

### 1.1 Misspelling Variations
Test the pipeline's ability to handle common misspellings and typos.

**Existing Misspellings in Database:**
```
catterpillar, Catepillar, Caterpiller → Caterpillar
MTu, M.T.U., mtu → MTU
VolvoPenta, volvo penta → Volvo Penta
filtr, flter → filter
gen, genny, genset → generator
```

**Test Query Examples:**
| Query | Expected Entity | Type |
|-------|----------------|------|
| "find caterpillar parts" | Caterpillar | brand |
| "show catterpillar filters" | Caterpillar + filter | brand + part |
| "MTU turbo gasket" | MTU + turbocharger gasket | brand + part |
| "volvo penta pump seals" | Volvo Penta + pump seal | brand + part |
| "fleetgard oil filter" | Fleetguard + oil filter | brand + part |
| "rackor fuel filter" | Racor + fuel filter | brand + part |
| "northen lights generator" | Northern Lights + generator | brand + equipment |

---

### 1.2 Term Type Variations
Test different ways users express the same concept.

**Equipment References:**
| Variation | Canonical Form |
|-----------|---------------|
| main engine, ME, main eng | Main Engine |
| generator, gen, genset, genny | Generator |
| bow thruster, fwd thruster, forward thruster | Bow Thruster |
| stern thruster, aft thruster | Stern Thruster |
| AC, A/C, air con, aircon, air conditioning, HVAC | Air Conditioning |
| watermaker, water maker, desalinator | Watermaker |

**Status Terms:**
| Variation | Canonical Form |
|-----------|---------------|
| broken, down, failed, not working, out of service | failed |
| needs repair, degraded, issues with, problems with | degraded |
| working, running, OK, good, operational | operational |
| under maintenance, being serviced, in maintenance | maintenance |

**Priority/Urgency Terms:**
| Variation | Canonical Form |
|-----------|---------------|
| urgent, ASAP, critical, emergency, immediately | critical |
| normal, standard, regular | routine |
| low priority, when possible, not urgent | low |

---

### 1.3 Time Frame Queries
Test temporal entity extraction and relative time parsing.

**Relative Time Expressions:**
```
today, now, currently
yesterday, last day
this week, current week
last week, previous week
this month, current month
last month, previous month
last 7 days, past week
last 30 days, past month
next week, upcoming week
overdue, past due, late
due soon, due shortly, coming up
expiring soon, expires this month
```

**Test Query Examples:**
| Query | Expected Time Entity |
|-------|---------------------|
| "work orders due this week" | time_ref: this_week |
| "overdue maintenance tasks" | time_ref: overdue |
| "certificates expiring in 30 days" | time_ref: 30_days |
| "completed work orders from last month" | time_ref: last_month + status: completed |
| "what was done yesterday" | time_ref: yesterday |
| "show hours of rest for last 7 days" | time_ref: last_7_days |

---

### 1.4 User/Crew Scope Queries
Test extraction of person names and roles.

**Crew Names in Database:**
```
Captain James Mitchell
Chief Engineer Robert Chen
First Officer Michael Thompson
Second Engineer David Santos
Chief Stew Sarah Williams
Bosun Thomas Anderson
```

**Role Variations:**
| Variation | Canonical Role |
|-----------|---------------|
| captain, skipper, master | captain |
| chief engineer, chief eng, CE, C/E | chief_engineer |
| first officer, 1st officer, mate, 1/O | first_officer |
| bosun, boatswain, bos'n | bosun |
| chief stew, chief stewardess | chief_stewardess |
| deckhand, deck hand | deckhand |

**Test Query Examples:**
| Query | Expected Entities |
|-------|------------------|
| "hours of rest for Captain Mitchell" | person: Captain James Mitchell |
| "work orders assigned to the chief engineer" | role: chief_engineer |
| "who worked in the engine room yesterday" | location: engine room + time: yesterday |
| "show compliance for Robert Chen" | person: Robert Chen |

---

### 1.5 Negative Queries
Test exclusion and negation patterns.

**Negation Patterns:**
```
not, don't, doesn't, didn't
without, excluding, except
other than, besides
no [X], none, nothing
isn't, aren't, wasn't, weren't
```

**Test Query Examples:**
| Query | Expected Extraction |
|-------|-------------------|
| "parts not in stock" | stock_status: out_of_stock |
| "equipment excluding generators" | negation: generator |
| "work orders not completed" | status: NOT completed |
| "certificates without expiry issues" | negation: expiring |
| "show all parts except filters" | negation: filter |
| "non-compliant hours of rest" | compliance: false |

---

### 1.6 Measurement & Value Queries
Test numeric and measurement extraction.

**Quantity Patterns:**
```
[number] units, [number] pieces
more than [X], greater than [X], over [X], above [X]
less than [X], under [X], below [X]
at least [X], minimum [X]
at most [X], maximum [X]
between [X] and [Y]
exactly [X]
```

**Test Query Examples:**
| Query | Expected Extraction |
|-------|-------------------|
| "parts with quantity below 5" | quantity: < 5 |
| "items with more than 10 in stock" | quantity: > 10 |
| "work orders over 100 hours" | measurement: > 100 hours |
| "equipment running at 80% capacity" | measurement: 80% |
| "parts between $50 and $200" | value: 50-200 |

---

### 1.7 ID & Number Queries
Test extraction of specific identifiers.

**ID Patterns in Database:**
```
Part Numbers: CAT-1R0739-E2E, DCK-0076-515, ELC-0041-489, FLT-0033-146
Certificate Numbers: CL-2025-3644, ABS-2025-4205, ISM-2025-9945
PO Numbers: PO-2025-001, PO-2026-009
```

**Test Query Examples:**
| Query | Expected Extraction |
|-------|-------------------|
| "find part CAT-1R0739" | part_number: CAT-1R0739* |
| "certificate ISM-2025-9945" | certificate_id: ISM-2025-9945 |
| "status of PO-2025-002" | po_number: PO-2025-002 |
| "part number starting with ELC" | part_number: ELC* |
| "show part DCK-0076-515" | part_number: DCK-0076-515 |

---

### 1.8 Description & Action Queries
Test extraction from descriptive phrases and action verbs.

**Action Verbs:**
```
show, display, list, find, get, retrieve
add, create, new, insert
update, change, modify, edit
delete, remove, cancel
approve, reject, complete
order, purchase, buy
inspect, service, repair, replace
```

**Descriptive Patterns:**
```
"needs [action]" → work order implication
"has [issue]" → fault/symptom
"is [status]" → equipment status
"shows [symptom]" → diagnostic indication
"requires [action]" → maintenance need
```

**Test Query Examples:**
| Query | Expected Extraction |
|-------|-------------------|
| "generator needs oil change" | equipment: generator, action: oil_change |
| "main engine showing vibration" | equipment: main engine, symptom: vibration |
| "approve pending shopping list items" | action: approve, status: pending |
| "complete work order for watermaker" | action: complete, equipment: watermaker |
| "order replacement filters" | action: order, part: filter |

---

## 2. GROUND TRUTH TEST CASES BY LENS

### 2.1 Parts Lens Tests

```python
PARTS_LENS_TESTS = [
    # Basic brand + part
    {"query": "Volvo Penta turbocharger gasket", "expected": {"brand": "Volvo Penta", "part": "turbocharger gasket"}, "lens": "parts"},
    {"query": "MTU fuel filter", "expected": {"brand": "MTU", "part": "fuel filter"}, "lens": "parts"},
    {"query": "Racor filters", "expected": {"brand": "Racor", "part": "filter"}, "lens": "parts"},

    # Misspelling tests
    {"query": "catterpillar oil filter", "expected": {"brand": "Caterpillar", "part": "oil filter"}, "lens": "parts"},
    {"query": "northen lights generator parts", "expected": {"brand": "Northern Lights", "part": "generator"}, "lens": "parts"},
    {"query": "volvo penta seal kit", "expected": {"brand": "Volvo Penta", "part": "seal kit"}, "lens": "parts"},

    # Location queries
    {"query": "parts in Storage A-1", "expected": {"location": "Storage A-1"}, "lens": "parts"},
    {"query": "engine room parts", "expected": {"location": "Engine Room"}, "lens": "parts"},
    {"query": "filters in Storage B-2", "expected": {"part": "filter", "location": "Storage B-2"}, "lens": "parts"},

    # Stock status queries
    {"query": "out of stock parts", "expected": {"stock_status": "out_of_stock"}, "lens": "inventory"},
    {"query": "low stock items", "expected": {"stock_status": "low_stock"}, "lens": "inventory"},
    {"query": "parts that need reordering", "expected": {"stock_status": "reorder"}, "lens": "inventory"},

    # Part number queries
    {"query": "part CAT-1R0739-E2E", "expected": {"part_number": "CAT-1R0739-E2E"}, "lens": "parts"},
    {"query": "find ELC-0041-489", "expected": {"part_number": "ELC-0041-489"}, "lens": "parts"},

    # Category queries
    {"query": "electrical parts", "expected": {"category": "Electrical"}, "lens": "parts"},
    {"query": "hydraulic components", "expected": {"category": "Hydraulic"}, "lens": "parts"},
    {"query": "navigation equipment parts", "expected": {"category": "Navigation"}, "lens": "parts"},

    # Compound queries
    {"query": "MTU fuel filters in engine room storage", "expected": {"brand": "MTU", "part": "fuel filter", "location": "Engine Room"}, "lens": "parts"},
    {"query": "low stock Volvo Penta gaskets", "expected": {"brand": "Volvo Penta", "part": "gasket", "stock_status": "low_stock"}, "lens": "inventory"},
]
```

### 2.2 Equipment Lens Tests

```python
EQUIPMENT_LENS_TESTS = [
    # Basic equipment queries
    {"query": "status of Main Engine Port", "expected": {"equipment": "Main Engine Port"}, "lens": "equipment"},
    {"query": "Generator 1 information", "expected": {"equipment": "Generator 1"}, "lens": "equipment"},
    {"query": "bow thruster status", "expected": {"equipment": "Bow Thruster"}, "lens": "equipment"},

    # Location queries
    {"query": "equipment in engine room", "expected": {"location": "Engine Room"}, "lens": "equipment"},
    {"query": "what's on the bridge", "expected": {"location": "Bridge"}, "lens": "equipment"},
    {"query": "flybridge equipment", "expected": {"location": "Flybridge"}, "lens": "equipment"},

    # Status queries
    {"query": "failed equipment", "expected": {"status": "failed"}, "lens": "equipment"},
    {"query": "equipment under maintenance", "expected": {"status": "maintenance"}, "lens": "equipment"},
    {"query": "what's degraded", "expected": {"status": "degraded"}, "lens": "equipment"},
    {"query": "operational equipment in engine room", "expected": {"status": "operational", "location": "Engine Room"}, "lens": "equipment"},

    # System type queries
    {"query": "propulsion system equipment", "expected": {"system_type": "propulsion"}, "lens": "equipment"},
    {"query": "HVAC equipment status", "expected": {"system_type": "hvac"}, "lens": "equipment"},
    {"query": "navigation systems", "expected": {"system_type": "navigation"}, "lens": "equipment"},

    # Criticality queries
    {"query": "critical equipment", "expected": {"criticality": "critical"}, "lens": "equipment"},
    {"query": "high priority systems", "expected": {"criticality": "high"}, "lens": "equipment"},
    {"query": "critical equipment that's degraded", "expected": {"criticality": "critical", "status": "degraded"}, "lens": "equipment"},

    # Brand queries
    {"query": "MTU equipment", "expected": {"brand": "MTU"}, "lens": "equipment"},
    {"query": "Northern Lights generators", "expected": {"brand": "Northern Lights", "equipment": "generator"}, "lens": "equipment"},
    {"query": "Simrad navigation equipment", "expected": {"brand": "Simrad", "system_type": "navigation"}, "lens": "equipment"},
]
```

### 2.3 Work Orders Lens Tests

```python
WORK_ORDER_LENS_TESTS = [
    # Status queries
    {"query": "work orders in progress", "expected": {"status": "in_progress"}, "lens": "work_orders"},
    {"query": "completed maintenance", "expected": {"status": "completed"}, "lens": "work_orders"},
    {"query": "planned work orders", "expected": {"status": "planned"}, "lens": "work_orders"},
    {"query": "cancelled tasks", "expected": {"status": "cancelled"}, "lens": "work_orders"},

    # Priority queries
    {"query": "critical work orders", "expected": {"priority": "critical"}, "lens": "work_orders"},
    {"query": "urgent maintenance tasks", "expected": {"priority": "critical"}, "lens": "work_orders"},
    {"query": "routine maintenance", "expected": {"priority": "routine"}, "lens": "work_orders"},

    # Type queries
    {"query": "corrective maintenance", "expected": {"work_order_type": "corrective"}, "lens": "work_orders"},
    {"query": "planned maintenance tasks", "expected": {"work_order_type": "planned"}, "lens": "work_orders"},

    # Time queries
    {"query": "overdue work orders", "expected": {"time_ref": "overdue"}, "lens": "work_orders"},
    {"query": "maintenance due this week", "expected": {"time_ref": "this_week"}, "lens": "work_orders"},
    {"query": "work orders completed last month", "expected": {"status": "completed", "time_ref": "last_month"}, "lens": "work_orders"},
    {"query": "what's due tomorrow", "expected": {"time_ref": "tomorrow"}, "lens": "work_orders"},

    # Equipment-specific queries
    {"query": "main engine work orders", "expected": {"equipment": "Main Engine"}, "lens": "work_orders"},
    {"query": "generator maintenance tasks", "expected": {"equipment": "generator"}, "lens": "work_orders"},
    {"query": "watermaker service history", "expected": {"equipment": "watermaker"}, "lens": "work_orders"},

    # Compound queries
    {"query": "critical overdue work orders for main engine", "expected": {"priority": "critical", "time_ref": "overdue", "equipment": "Main Engine"}, "lens": "work_orders"},
    {"query": "completed generator maintenance last week", "expected": {"status": "completed", "equipment": "generator", "time_ref": "last_week"}, "lens": "work_orders"},
]
```

### 2.4 Certificates Lens Tests

```python
CERTIFICATE_LENS_TESTS = [
    # Type queries
    {"query": "class certificates", "expected": {"certificate_type": "class"}, "lens": "certificates"},
    {"query": "safety certificates", "expected": {"certificate_type": "safety"}, "lens": "certificates"},
    {"query": "environmental certificates", "expected": {"certificate_type": "environmental"}, "lens": "certificates"},
    {"query": "loadline certificate", "expected": {"certificate_type": "loadline"}, "lens": "certificates"},

    # Authority queries
    {"query": "DNV certificates", "expected": {"authority": "DNV GL"}, "lens": "certificates"},
    {"query": "Lloyd's Register certificates", "expected": {"authority": "Lloyd's Register"}, "lens": "certificates"},
    {"query": "ABS class certificate", "expected": {"authority": "ABS", "certificate_type": "class"}, "lens": "certificates"},

    # ID queries
    {"query": "certificate CL-2025-3644", "expected": {"certificate_id": "CL-2025-3644"}, "lens": "certificates"},
    {"query": "ISM certificate status", "expected": {"certificate_type": "ism"}, "lens": "certificates"},

    # Expiry queries
    {"query": "certificates expiring soon", "expected": {"time_ref": "expiring_soon"}, "lens": "certificates"},
    {"query": "certificates expiring this month", "expected": {"time_ref": "this_month"}, "lens": "certificates"},
    {"query": "expired certificates", "expected": {"status": "expired"}, "lens": "certificates"},
    {"query": "certificates expiring in 90 days", "expected": {"time_ref": "90_days"}, "lens": "certificates"},

    # Specific certificate queries
    {"query": "SOLAS safety equipment certificate", "expected": {"certificate_name": "SOLAS Safety Equipment"}, "lens": "certificates"},
    {"query": "IOPP certificate expiry", "expected": {"certificate_name": "IOPP"}, "lens": "certificates"},
    {"query": "minimum safe manning document", "expected": {"certificate_name": "Minimum Safe Manning"}, "lens": "certificates"},
]
```

### 2.5 Crew Lens Tests

```python
CREW_LENS_TESTS = [
    # Person queries
    {"query": "hours of rest for Captain Mitchell", "expected": {"person": "Captain James Mitchell"}, "lens": "crew"},
    {"query": "Robert Chen compliance", "expected": {"person": "Robert Chen"}, "lens": "crew"},
    {"query": "show hours for Chief Engineer", "expected": {"role": "chief_engineer"}, "lens": "crew"},

    # Role queries
    {"query": "captain hours of rest", "expected": {"role": "captain"}, "lens": "crew"},
    {"query": "engineering department hours", "expected": {"department": "engineering"}, "lens": "crew"},
    {"query": "deck crew compliance", "expected": {"department": "deck"}, "lens": "crew"},

    # Compliance queries
    {"query": "non-compliant crew", "expected": {"compliance": "non_compliant"}, "lens": "crew"},
    {"query": "compliance violations", "expected": {"compliance": "violation"}, "lens": "crew"},
    {"query": "good compliance records", "expected": {"compliance": "compliant"}, "lens": "crew"},

    # Time queries
    {"query": "hours of rest this week", "expected": {"time_ref": "this_week"}, "lens": "crew"},
    {"query": "crew hours yesterday", "expected": {"time_ref": "yesterday"}, "lens": "crew"},
    {"query": "last 7 days compliance", "expected": {"time_ref": "last_7_days"}, "lens": "crew"},

    # Location queries
    {"query": "hours at sea", "expected": {"voyage_type": "at_sea"}, "lens": "crew"},
    {"query": "in port rest hours", "expected": {"voyage_type": "in_port"}, "lens": "crew"},
    {"query": "hours in Monaco", "expected": {"location": "Monaco"}, "lens": "crew"},
]
```

---

## 3. MISSPELLING TEST MATRIX

### 3.1 Brand Misspellings to Test

| Correct | Misspelling Variations |
|---------|----------------------|
| Caterpillar | catterpillar, caterpiller, catepillar, caterpilar |
| MTU | mtu, M.T.U., mTu |
| Volvo Penta | volvo penta, VolvoPenta, volvopenta |
| Northern Lights | northen lights, northern lite, nothern lights |
| Fleetguard | fleetgard, fleet guard, fleetgaurd |
| Racor | rackor, raycor |
| Yanmar | yanmnar, yanamar |
| Grundfos | grundfoss, grunfos |
| Kohler | koehler, koheler |
| Mastervolt | master volt, mastervlt |

### 3.2 Part Type Misspellings

| Correct | Misspelling Variations |
|---------|----------------------|
| filter | filtr, flter, fillter |
| gasket | gaskit, gascket |
| impeller | impeler, impellor |
| thermostat | thermstat, thermosat |
| alternator | alternater, alterntor |
| turbocharger | turbo charger, turbochargor |
| injector | injecter, injector |
| solenoid | solinoid, solenod |

### 3.3 Location Misspellings

| Correct | Misspelling Variations |
|---------|----------------------|
| Engine Room | engineroom, engin room |
| Flybridge | fly bridge, fli bridge |
| Lazarette | lazaret, lazerette |
| Forepeak | fore peak, forpeak |

---

## 4. NEGATIVE QUERY TEST CASES

```python
NEGATIVE_QUERIES = [
    # Stock negation
    {"query": "parts not in stock", "expected": {"stock_status": "out_of_stock"}},
    {"query": "items without stock", "expected": {"stock_status": "out_of_stock"}},

    # Status negation
    {"query": "work orders not completed", "expected": {"status": "NOT:completed"}},
    {"query": "equipment that isn't operational", "expected": {"status": "NOT:operational"}},
    {"query": "unfinished maintenance", "expected": {"status": "NOT:completed"}},

    # Exclusion
    {"query": "all parts except filters", "expected": {"exclude": "filter"}},
    {"query": "equipment excluding generators", "expected": {"exclude": "generator"}},
    {"query": "suppliers other than MTU", "expected": {"exclude": "MTU"}},

    # Compliance negation
    {"query": "non-compliant hours", "expected": {"compliance": "false"}},
    {"query": "crew not meeting rest requirements", "expected": {"compliance": "false"}},

    # None/empty
    {"query": "parts with no stock", "expected": {"quantity": 0}},
    {"query": "equipment without maintenance history", "expected": {"history": "empty"}},
]
```

---

## 5. COMPOUND QUERY TEST CASES

These test multiple entity types in a single query:

```python
COMPOUND_QUERIES = [
    # Brand + Part + Location
    {"query": "MTU fuel filters in engine room storage that are low stock",
     "expected": {"brand": "MTU", "part": "fuel filter", "location": "Engine Room", "stock_status": "low_stock"},
     "lens": "parts"},

    # Equipment + Status + Time
    {"query": "failed propulsion equipment from last month",
     "expected": {"status": "failed", "system_type": "propulsion", "time_ref": "last_month"},
     "lens": "equipment"},

    # Work Order + Equipment + Priority + Time
    {"query": "critical overdue main engine work orders",
     "expected": {"priority": "critical", "time_ref": "overdue", "equipment": "Main Engine"},
     "lens": "work_orders"},

    # Certificate + Authority + Time
    {"query": "DNV class certificates expiring in 90 days",
     "expected": {"authority": "DNV GL", "certificate_type": "class", "time_ref": "90_days"},
     "lens": "certificates"},

    # Crew + Role + Location + Time
    {"query": "captain hours of rest at sea this week",
     "expected": {"role": "captain", "voyage_type": "at_sea", "time_ref": "this_week"},
     "lens": "crew"},
]
```

---

## 6. IMPLEMENTATION PLAN

### Phase 1: Basic Entity Extraction
- Single entity per query
- Exact matches
- No time references

### Phase 2: Misspelling Tolerance
- Add fuzzy matching tests
- Brand variations
- Part type variations

### Phase 3: Time Frame Support
- Relative time parsing
- Date range queries
- Expiry/due date queries

### Phase 4: Compound Queries
- Multiple entities per query
- Cross-lens disambiguation
- Negative/exclusion queries

### Phase 5: Natural Language Variations
- Action verbs
- Descriptive phrases
- Conversational queries

---

## 7. SCORING METHODOLOGY

### Match Types:
- **EXACT**: Entity extracted matches expected exactly
- **PARTIAL**: Entity extracted partially matches (e.g., "Main Engine" vs "Main Engine Port")
- **FUZZY**: Entity extracted via fuzzy matching (misspelling correction)
- **MISS**: Expected entity not extracted
- **FALSE_POS**: Unexpected entity extracted

### Scoring Formula:
```
Score = (EXACT * 1.0 + PARTIAL * 0.75 + FUZZY * 0.9) / Total_Expected
```

### Target Accuracy:
- Phase 1: 95%+ on basic queries
- Phase 2: 90%+ with misspellings
- Phase 3: 85%+ with time references
- Phase 4: 80%+ on compound queries
- Phase 5: 75%+ on natural language variations

---

## 8. NEXT STEPS

1. Implement ground truth test runner with new test cases
2. Add misspelling fuzzy matching to extraction pipeline
3. Implement time reference extraction
4. Add compound query support
5. Track accuracy metrics per dimension

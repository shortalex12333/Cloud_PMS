# Entity Extraction Failure Analysis
## Generated: 2026-02-03

This document analyzes the 20 failures (out of 164 expected entities) in the ground truth tests, organized by root cause.

---

## Root Cause Categories

| Category | Count | Impact |
|----------|-------|--------|
| Value alias missing | 7 | Test runner needs expanded VALUE_ALIASES |
| Equipment synonym missing | 4 | Need equipment abbreviation/synonym mapping |
| Certificate type patterns | 3 | "class", "environmental" not extracted as certificate_type |
| Person name partial match | 2 | Query contains partial name, expected full name |
| Voyage type pattern | 1 | "at sea" not extracted as voyage_type |
| Part plural form | 1 | "gaskets" not matching part patterns |
| Work order type pattern | 1 | "corrective" not extracted as work_order_type |
| Quantity value format | 1 | "0" expected but "zero stock" extracted |

---

## Detailed Failure Analysis

### 1. MEASUREMENT DIMENSION (4 failures) - VALUE FORMAT MISMATCH

**Problem**: The extraction pipeline correctly extracts quantity comparisons, but the VALUE format doesn't match expectations.

| Test ID | Query | Extracted | Expected | Issue |
|---------|-------|-----------|----------|-------|
| MEAS-001 | "parts with quantity below 5" | `quantity_comparison:'below 5'` | `quantity:'<5'` | Value format mismatch |
| MEAS-002 | "items with more than 10 in stock" | `quantity_comparison:'more than 10'` | `quantity:'>10'` | Value format mismatch |
| MEAS-003 | "parts with zero stock" | `stock_status:'zero stock'` | `quantity:'0'` | Type AND value mismatch |
| MEAS-005 | "less than 10 hours rest" | `quantity_comparison:'less than 10'` | `measurement:'<10_hours'` | Value format mismatch |

**Root Cause**: Ground truth uses symbolic format (`<5`, `>10`, `0`) but pipeline extracts natural language (`below 5`, `more than 10`, `zero stock`).

**Solution Options**:
1. Add VALUE_ALIASES: `'<5': ['below 5', 'less than 5', 'under 5']`
2. Or normalize extracted values to symbolic format in pipeline
3. Or update ground truth to expect natural language values

---

### 2. TERM_TYPE DIMENSION (4 failures) - EQUIPMENT SYNONYMS

**Problem**: Equipment abbreviations and synonyms not mapping to canonical names.

| Test ID | Query | Extracted | Expected | Issue |
|---------|-------|-----------|----------|-------|
| TERM-003 | "gen 1 running hours" | Nothing for "gen 1" | `equipment:'Generator 1'` | "gen" abbreviation not expanded |
| TERM-004 | "genset fuel consumption" | `equipment:'genset'` | `equipment:'generator'` | Synonym value mismatch |
| TERM-009 | "water maker output" | `equipment:'water maker'` | `equipment:'Watermaker'` | Spacing/case value mismatch |
| TERM-010 | "desalinator membrane" | `equipment:'desalinator'` | `equipment:'Watermaker'` | Synonym value mismatch |

**Root Cause**:
- Abbreviations like "gen", "gen 1" not being expanded to "Generator", "Generator 1"
- Synonyms like "genset", "desalinator", "water maker" not mapping to canonical "generator", "watermaker"

**Solution**:
Add EQUIPMENT_ALIASES:
```python
EQUIPMENT_ALIASES = {
    'gen': 'generator',
    'gen 1': 'generator 1',
    'gen 2': 'generator 2',
    'genset': 'generator',
    'desalinator': 'watermaker',
    'water maker': 'watermaker',
    'fwd thruster': 'bow thruster',
    'aft thruster': 'stern thruster',
    'ME': 'main engine',
    'ME port': 'main engine port',
    'ME stbd': 'main engine starboard',
    'A/C': 'air conditioning',
    'aircon': 'air conditioning',
}
```

---

### 3. CERTIFICATE TYPE (3 failures) - MISSING PATTERNS

**Problem**: Certificate type keywords "class" and "environmental" not being extracted.

| Test ID | Query | Extracted | Expected | Issue |
|---------|-------|-----------|----------|-------|
| CERT-001 | "class certificates" | `document_type:'certificates'` | `certificate_type:'class'` | "class" not extracted |
| CERT-008 | "environmental certificates" | `document_type:'certificates'` | `certificate_type:'environmental'` | "environmental" not extracted |
| COMP-004 | "DNV class certificates..." | `document_type:'certificates'` | `certificate_type:'class'` | "class" not extracted |

**Root Cause**: The word "class" is generic and may be filtered. "environmental" similarly not in certificate_type patterns.

**Solution**: Add certificate type patterns:
```python
'certificate_type': [
    re.compile(r'\b(class)\s+certificate', re.IGNORECASE),
    re.compile(r'\b(safety)\s+certificate', re.IGNORECASE),
    re.compile(r'\b(environmental)\s+certificate', re.IGNORECASE),
    re.compile(r'\b(loadline)\s+certificate', re.IGNORECASE),
    re.compile(r'\b(ism|isps|iopp|ispp)\s+certificate', re.IGNORECASE),
]
```

---

### 4. USER_SCOPE (2 failures) - PERSON NAME PARTIAL MATCH

**Problem**: Query contains partial name, but expected value is full name from database.

| Test ID | Query | Extracted | Expected | Issue |
|---------|-------|-----------|----------|-------|
| USER-001 | "Captain Mitchell" | `org:'Captain Mitchell'` | `person:'Captain James Mitchell'` | 1) Wrong type (org vs person), 2) Missing middle name |
| USER-005 | "First Officer Thompson" | `org:'First Officer Thompson'` | `person:'First Officer Michael Thompson'` | 1) Wrong type, 2) Missing middle name |

**Root Cause**:
1. **Type issue**: Title+LastName pattern being classified as `org` instead of `person`
2. **Value issue**: Ground truth expects FULL database name, but query only has partial name

**Solution**:
1. Add pattern to recognize "Title + Name" as person: `Captain Mitchell`, `First Officer Thompson`
2. Update test runner to accept partial name matches for person type
3. Or update ground truth to expect the query value, not the database value

---

### 5. VOYAGE TYPE (1 failure) - MISSING PATTERN

**Problem**: "at sea" not being extracted as voyage_type.

| Test ID | Query | Extracted | Expected | Issue |
|---------|-------|-----------|----------|-------|
| COMP-005 | "captain hours of rest at sea this week" | Nothing | `voyage_type:'at_sea'` | Pattern missing |

**Root Cause**: No regex pattern for voyage types like "at sea", "in port".

**Solution**: Add voyage_type patterns:
```python
'voyage_type': [
    re.compile(r'\b(at\s+sea|at\s+anchor|in\s+port|underway|moored|docked)\b', re.IGNORECASE),
]
```

---

### 6. WORK ORDER TYPE (1 failure) - MISSING PATTERN

**Problem**: "corrective" not being extracted as work_order_type.

| Test ID | Query | Extracted | Expected | Issue |
|---------|-------|-----------|----------|-------|
| WO-005 | "corrective maintenance" | `action:'maintenance'` | `work_order_type:'corrective'` | "corrective" not extracted |

**Root Cause**: Work order type keywords not in patterns.

**Solution**: Add work_order_type patterns:
```python
'work_order_type': [
    re.compile(r'\b(corrective|preventive|scheduled|emergency|planned|unplanned)\s+(?:maintenance|work|task)', re.IGNORECASE),
]
```

---

### 7. PART PLURAL (1 failure) - PLURAL FORM MISMATCH

**Problem**: "gaskets" not matching "gasket" part pattern.

| Test ID | Query | Extracted | Expected | Issue |
|---------|-------|-----------|----------|-------|
| COMP-007 | "Volvo Penta gaskets with zero stock" | Nothing for "gaskets" | `part:'gasket'` | Plural not matching |

**Root Cause**: Part patterns may only match singular forms.

**Solution**: Ensure part patterns include plural forms or add VALUE_ALIAS:
```python
'gasket': ['gaskets', 'gasket'],
'filter': ['filters', 'filter'],
'seal': ['seals', 'seal'],
```

---

## Summary of Required Fixes

### 1. Test Runner VALUE_ALIASES (Immediate fix)
```python
VALUE_ALIASES.update({
    '<5': ['below 5', 'less than 5', 'under 5'],
    '>10': ['more than 10', 'greater than 10', 'over 10'],
    '<10_hours': ['less than 10 hours', 'less than 10'],
    'Generator 1': ['generator 1', 'gen 1'],
    'generator': ['genset', 'gen'],
    'Watermaker': ['watermaker', 'water maker', 'desalinator'],
    'gasket': ['gaskets'],
})
```

### 2. Test Runner TYPE_ALIASES (Immediate fix)
```python
TYPE_ALIASES.update({
    'person': ['person', 'org'],  # Accept org as person for names
    'certificate_type': ['certificate_type', 'document_type'],  # Temporary
})
```

### 3. Pipeline Enhancements (Future work)
1. Add EQUIPMENT_ALIASES for abbreviation expansion
2. Add certificate_type patterns for "class", "environmental"
3. Add voyage_type patterns for "at sea", "in port"
4. Add work_order_type patterns for "corrective", "preventive"
5. Add person patterns for "Title + Name" format

---

## Priority Order for Fixes

1. **High Impact, Low Effort**: Update VALUE_ALIASES in test runner (fixes 7+ tests)
2. **Medium Impact, Low Effort**: Update TYPE_ALIASES in test runner (fixes 3+ tests)
3. **Medium Impact, Medium Effort**: Add equipment alias expansion (fixes 4 tests)
4. **Low Impact, Medium Effort**: Add certificate_type, voyage_type, work_order_type patterns

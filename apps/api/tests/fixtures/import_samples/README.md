# Import Test Fixtures

Test data simulating real PMS export files for the import pipeline.

## Files

### IDEA Yacht (semicolon-delimited CSV)
- `idea_yacht_equipment.csv` — 15 records, UPPER_SNAKE_CASE headers, semicolon delimiter, integer IDs, parent hierarchy via PARENT_EQUIP_ID, DD-MMM-YYYY dates
- `idea_yacht_work_orders.csv` — 12 records, mixed statuses (COMPLETED/OPEN/IN_PROGRESS), semicolon delimiter

### Seahub (comma-delimited CSV)
- `seahub_equipment.csv` — 8 records, snake_case headers, comma delimiter, string IDs (EQ-xxx), parent hierarchy via parent_id
- `seahub_defects.csv` — 5 records, note: "defects" not "faults", statuses: open/closed
- `seahub_tasks.csv` — 9 records, note: "tasks" not "work_orders", statuses: completed/open
- `seahub_inventory.csv` — 10 records, note: "inventory" not "parts", includes equipment cross-references
- `seahub_certificates.csv` — 8 records, ISO dates, includes permanent certs (no expiry)

### Sealogical (CSV simulating XLSX quirks)
- `sealogical_equipment.csv` — 8 records, Title Case headers with spaces, DD/MM/YYYY dates, 4 metadata rows above header row

## Edge Cases Covered

1. **Delimiter variance**: semicolon (IDEA) vs comma (Seahub/Sealogical)
2. **Date formats**: DD-MMM-YYYY (IDEA), ISO YYYY-MM-DD (Seahub), DD/MM/YYYY (Sealogical)
3. **Column naming**: UPPER_SNAKE_CASE (IDEA), snake_case (Seahub), Title Case Spaces (Sealogical)
4. **Vocabulary mismatches**: defects→faults, tasks→work_orders, inventory→parts
5. **Equipment hierarchy**: integer parent_id (IDEA), string parent_id (Seahub), flat (Sealogical)
6. **Metadata rows**: Sealogical has 4 non-data rows before headers
7. **Missing values**: empty running_hours, empty service_interval, empty dates
8. **Status mapping**: ACTIVE/COMPLETED/OPEN/IN_PROGRESS (IDEA) vs active/completed/open (Seahub)
9. **Permanent certificates**: no expiry date (tonnage, registry)
10. **Expired certificates**: must import with historical status preserved

## Verification Criteria (per verification-integrity skill)

A REAL SUCCESS means:
- [ ] Parser correctly detects delimiter (not just returns 200)
- [ ] Parser correctly identifies header row (especially Sealogical with metadata rows)
- [ ] Column mapping confidence scores are reasonable (>90% for exact matches, <60% for unknown)
- [ ] Date values are correctly converted to ISO 8601
- [ ] Equipment hierarchy parent references resolve correctly
- [ ] "defects" maps to faults domain, "tasks" maps to work_orders domain
- [ ] Row counts match expected (not just "array has items")
- [ ] yacht_id is set on every imported record (not just trusting 200 OK)
- [ ] source_id preserves original ID from source system
- [ ] Encoding is correctly detected and converted to UTF-8

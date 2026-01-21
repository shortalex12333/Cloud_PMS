# Schema Truth Map

**Generated:** 2026-01-20
**Tenant DB:** https://vzsohavtuotocgrfkfyd.supabase.co

## Summary

| Metric | Count |
|--------|-------|
| Tables in Database (confirmed via API) | 17 |
| Tables referenced in Web Code | 35 |
| Tables referenced in Backend Code | 78 |

## Tables Confirmed in Database

These tables were verified to exist via Supabase API:

1. auth_microsoft_tokens
2. document_chunks
3. documents
4. email_attachments
5. email_links
6. email_messages
7. email_threads
8. email_watchers
9. ledger_events
10. pms_equipment
11. pms_faults
12. pms_handover
13. pms_maintenance_schedules
14. pms_parts
15. pms_work_orders
16. search_document_chunks
17. v_inventory

## Tables Referenced in Web App Code (35)

```
action_executions, auth_microsoft_tokens, auth_signatures, auth_users,
auth_users_profiles, crew_members, deliveries, document_chunks, documents,
email_watchers, graph_edges, handover_items, handovers, invoices,
maintenance_templates, pms_attachments, pms_audit_log, pms_checklist_items,
pms_equipment, pms_equipment_notes, pms_faults, pms_hours_of_rest, pms_notes,
pms_parts, pms_purchase_orders, pms_work_order_notes, pms_work_order_parts,
pms_work_orders, pms_worklist_tasks, predictive_state, purchase_request_items,
sensor_readings, suggestion_log, survey_tags, symptom_reports
```

## Tables Referenced in Backend Code (78)

```
action_logs, attachments, audit_log, auth_microsoft_tokens, auth_users_profiles,
auth_users_roles, checklist_items, checklists, doc_metadata, doc_yacht_library,
document_chunks, documents, email_link_decisions, email_links, email_messages,
email_threads, email_watchers, equipment, equipment_notes, event_logs,
fault_notes, faults, fleet_registry, graph_edges, graph_nodes, handover,
handover_items, handovers, hours_of_rest, inventory_transactions, ledger_events,
maintenance_templates, navigation_contexts, notes, part_usage_log, parts,
pms_audit_log, pms_equipment, pms_equipment_parts_bom, pms_faults, pms_handover,
pms_hours_of_rest, pms_notes, pms_orders, pms_part_usage, pms_parts,
pms_purchase_order_items, pms_purchase_orders, pms_receiving_events,
pms_shopping_list_items, pms_suppliers, pms_work_order_checklist,
pms_work_order_notes, pms_work_order_parts, pms_work_orders, predictive_state,
purchase_items, purchases, receiving_sessions, reorders, sensor_readings,
shopping_list, suggestion_log, survey_tags, symptom_reports, user_accounts,
user_added_relations, user_profiles, v_extraction_status, v_graph_stats,
vendors, work_order_notes, work_order_parts, work_orders, worklist_items,
worklist_tasks, worklists, yacht_registry, yachts
```

## Mismatch Analysis

### Tables in Code but NOT confirmed in DB

The following tables are referenced in code but were not found when probing the database:

**High Priority (used in Web app):**
- `action_executions` - Action logging
- `auth_signatures` - Auth signatures
- `auth_users` - User auth (may be Supabase internal)
- `auth_users_profiles` - User profiles
- `crew_members` - Crew management
- `deliveries` - Delivery tracking
- `graph_edges` - Graph relationships
- `handover_items` - Handover items
- `handovers` - Handovers (note: `pms_handover` exists)
- `invoices` - Invoice tracking
- `maintenance_templates` - Maintenance templates
- `pms_attachments` - Attachments
- `pms_audit_log` - Audit log
- `pms_checklist_items` - Checklist items
- `pms_equipment_notes` - Equipment notes
- `pms_hours_of_rest` - Hours of rest
- `pms_notes` - Notes
- `pms_purchase_orders` - Purchase orders
- `pms_work_order_notes` - Work order notes
- `pms_work_order_parts` - Work order parts
- `pms_worklist_tasks` - Worklist tasks
- `predictive_state` - Predictive maintenance
- `purchase_request_items` - Purchase request items
- `sensor_readings` - Sensor data
- `suggestion_log` - Suggestions
- `survey_tags` - Survey tags
- `symptom_reports` - Symptom reports

### Potential Issues

1. **Naming inconsistency:** `handovers` vs `pms_handover`
2. **Missing tables:** Many tables referenced in code don't exist
3. **Legacy references:** Some code may reference old table names

### Recommendations

1. **Audit code paths:** Identify if missing tables cause runtime errors
2. **Create migrations:** For tables that should exist but don't
3. **Remove dead code:** For references to deprecated tables
4. **Standardize naming:** Use `pms_` prefix consistently

## Status

This is a **discovery report** identifying schema discrepancies. Action items:
- [ ] Review each missing table to determine if it's needed
- [ ] Create migrations for required tables
- [ ] Update code to remove references to unused tables

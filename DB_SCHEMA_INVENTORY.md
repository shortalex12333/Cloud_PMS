# DATABASE SCHEMA INVENTORY

**Generated:** 2026-01-18
**Method:** Live introspection via REST API + Migration file analysis

---

## MASTER DATABASE

**URL:** `https://qvzmkaamzaqxpzbewjxe.supabase.co`

### Tables (27 total)

| Table | Columns |
|-------|---------|
| `user_accounts` | id, yacht_id, email, display_name, status, email_verified, created_at, last_login, login_count, failed_login_attempts, locked_until, role |
| `fleet_registry` | yacht_id, yacht_id_hash, buyer_email, buyer_name, active, credentials_retrieved, shared_secret, created_at, registered_at, activated_at, credentials_retrieved_at, registration_ip, activation_ip, yacht_name, yacht_model, last_seen_at, api_calls_count, user_id, dmg_storage_path, dmg_sha256, dmg_built_at, tenant_key_alias, updated_at |
| `alert_history` | (not queried) |
| `alert_rules` | (not queried) |
| `alias_blocklist` | (not queried) |
| `alias_candidates` | (not queried) |
| `alias_regression_failures` | (not queried) |
| `analytics_daily` | (not queried) |
| `audit_log` | (not queried) |
| `db_registry` | (empty) |
| `department_definitions` | (not queried) |
| `download_links` | (not queried) |
| `entity_feedback` | (not queried) |
| `identity_audit_log` | (not queried) |
| `resolution_episodes` | (not queried) |
| `resolution_provenance` | (not queried) |
| `resolver_versions` | (not queried) |
| `role_definitions` | (not queried) |
| `security_events` | (not queried) |
| `term_history` | (not queried) |
| `twofa_codes` | (not queried) |
| `user_sessions` | (not queried) |

### Views

| View | Purpose |
|------|---------|
| `v_candidates_pending` | Unknown |
| `v_candidates_ready_for_deployment` | Unknown |
| `v_feedback_health` | Unknown |
| `v_resolver_drift` | Unknown |
| `v_term_lifecycle_stats` | Unknown |

---

## TENANT DATABASE

**URL:** `https://vzsohavtuotocgrfkfyd.supabase.co`
**Yacht ID:** `85fe1119-b04c-41ac-80f1-829d23322598`

### Tables (100+ total)

#### PMS Tables (Exist)
| Table | yacht_id Column |
|-------|-----------------|
| `pms_equipment` | ✅ YES |
| `pms_faults` | ✅ YES |
| `pms_parts` | ✅ YES |
| `pms_work_orders` | ✅ YES |
| `pms_work_order_notes` | ✅ YES |
| `pms_work_order_parts` | ✅ YES |
| `pms_attachments` | ✅ YES |
| `pms_checklists` | ✅ YES |
| `pms_checklist_items` | ✅ YES |
| `pms_audit_log` | ✅ YES |
| `pms_worklist_tasks` | ✅ YES |

#### Handover Tables (Exist)
| Table | Columns |
|-------|---------|
| `handovers` | id, yacht_id, title, description, status, from_user_id, to_user_id, shift_date, shift_type, started_at, completed_at, approved_by, approved_at, approval_notes, metadata, created_at, created_by, updated_at, updated_by, deleted_at, deleted_by, deletion_reason |
| `handover_items` | id, yacht_id, handover_id, entity_id, entity_type, section, summary, priority, status, acknowledged_by, acknowledged_at, acknowledgement_notes, metadata, created_at, added_by, updated_at, updated_by, deleted_at, deleted_by, deletion_reason |

#### Email Tables (Exist)
| Table | Columns |
|-------|---------|
| `email_threads` | id, yacht_id, provider_conversation_id, latest_subject, message_count, has_attachments, participant_hashes, source, first_message_at, last_activity_at, last_inbound_at, last_outbound_at, created_at, updated_at, extracted_tokens, suggestions_generated_at, thread_embedding |
| `email_messages` | (exists) |
| `email_links` | (exists) |
| `email_watchers` | (exists) |
| `auth_microsoft_tokens` | (exists) |

#### Search Tables (Exist)
| Table | Columns |
|-------|---------|
| `search_document_chunks` | id, yacht_id, document_id, chunk_index, text, page_number, embedding, equipment_ids, fault_codes, tags, metadata, created_at, content, graph_extracted, graph_extracted_at, section_title, doc_type, system_tag, graph_extract_status, graph_extract_error, section_path, section_type, is_section_entry, symptom_codes, graph_extract_ts |
| `documents` | (exists) |
| `document_chunks` | (exists) |

#### Action Tables (Exist)
| Table | Columns |
|-------|---------|
| `action_executions` | (exists) |
| `navigation_contexts` | (exists) |

---

## TABLES REFERENCED IN CODE BUT DO NOT EXIST

| Table | Referenced In | Lines |
|-------|---------------|-------|
| `attachments` | faults.ts, workOrders.ts | 570, 620, 1049 |
| `audit_log` | workOrders.ts | 209 |
| `auth_users` | lib/auth.ts | 74 |
| `checklist_items` | workOrders.ts | 121, 865, 927 |
| `crew_members` | useEmailData.ts | 476 |
| `deliveries` | procurement.ts | 470 |
| `hours_of_rest` | compliance.ts | 24, 118, 186 |
| `invoices` | procurement.ts | 299 |
| `maintenance_templates` | faults.ts | 209, 388 |
| `notes` | equipment.ts, faults.ts, workOrders.ts | 626, 483, 472 |
| `pms_equipment_notes` | dispatchers.ts | 21 |
| `purchase_request_items` | procurement.ts | 138, 505 |
| `purchase_requests` | inventory.ts, procurement.ts | 190, 37, 110 |
| `sensor_readings` | equipment.ts | 487 |
| `survey_tags` | compliance.ts | 379 |
| `work_order_parts` | inventory.ts, workOrders.ts | 266, 141 |
| `worklist_items` | workOrders.ts | 1119, 1194, 1293 |

**Total: 17 tables referenced but do not exist**

---

## STORAGE BUCKETS

### Referenced in Code
- Document storage path format: `documents/{yacht_id}/...`
- Attachment paths expected

### Verification Status
- NOT VERIFIED - requires Supabase dashboard access

---

## DATA COUNTS

### MASTER DB
| Table | Count |
|-------|-------|
| `user_accounts` | 1 |
| `fleet_registry` | 1 |

### TENANT DB
| Table | Count |
|-------|-------|
| `search_document_chunks` | 47,166+ |
| `pms_work_orders` | 1,233+ |
| `pms_equipment` | 426+ |
| `pms_parts` | 480+ |
| `handovers` | 1+ |
| `handover_items` | 1+ |

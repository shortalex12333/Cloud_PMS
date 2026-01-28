# DB Truth Snapshot
**Generated**: 2026-01-24T06:35:34.367297
**Source**: Production Supabase Database
**Total Tables**: 143

---

## Enum Types

### `action_status`
Values: `pending`, `in_progress`, `completed`, `failed`, `cancelled`

### `confidence_level`
Values: `LOW`, `MEDIUM`, `HIGH`

### `doc_category`
Values: `manual`, `service_bulletin`, `parts_catalog`, `wiring_diagram`, `piping_diagram`, `ga_drawing`, `schematic`, `specification`, `sop`, `checklist`, `procedure`, `policy`, `guideline`, `log`, `report`, `survey`, `inspection`, `audit`, `work_order`, `service_record`, `incident_report`, `drill_record`, `class_certificate`, `flag_certificate`, `equipment_certificate`, `crew_certificate`, `insurance_certificate`, `permit`, `invoice`, `quote`, `purchase_order`, `delivery_note`, `receipt`, `contract`, `budget`, `statement`, `crew_list`, `training_record`, `medical_record`, `hours_of_rest`, `employment_contract`, `evaluation`, `itinerary`, `preference_sheet`, `menu`, `charter_agreement`, `trip_report`, `feedback`, `email`, `letter`, `memo`, `notice`, `photo`, `video`, `audio`, `reference`, `template`, `archive`, `other`

### `equipment_criticality`
Values: `low`, `medium`, `high`, `critical`

### `fault_severity`
Values: `low`, `medium`, `high`, `critical`

### `graph_edge_type`
Values: `PART_OF`, `CONTAINS`, `BELONGS_TO`, `LOCATED_IN`, `INSTALLED_ON`, `CONNECTED_TO`, `USES_PART`, `REQUIRES_CONSUMABLE`, `HAS_FAULT`, `SHOWS_SYMPTOM`, `CAUSES`, `SYMPTOM_OF`, `REPAIRED_BY`, `MAINTAINED_BY`, `SPECIFIED_IN`, `SUPERSEDES`, `COMPATIBLE_WITH`, `ALTERNATIVE_TO`, `DOCUMENTED_IN`, `REFERENCES`, `APPLIES_TO`, `COVERS`, `SECTION_OF`, `REVISION_OF`, `ATTACHMENT_TO`, `ASSIGNED_TO`, `RESPONSIBLE_FOR`, `REPORTS_TO`, `MEMBER_OF`, `PERFORMED_BY`, `APPROVED_BY`, `CREATED_BY`, `WITNESSED_BY`, `HOLDS_CERTIFICATE`, `CERTIFIES`, `ISSUED_BY`, `VALID_UNTIL`, `EXPIRES_ON`, `SATISFIES`, `REQUIRED_BY`, `COMPLIES_WITH`, `INSPECTED_BY`, `SUPPLIED_BY`, `INVOICED_BY`, `PAID_TO`, `ALLOCATED_TO`, `QUOTED_BY`, `CONTRACTED_WITH`, `INSURED_BY`, `CLAIMED_UNDER`, `PART_OF_VOYAGE`, `DEPARTED_FROM`, `ARRIVED_AT`, `TRANSITED_THROUGH`, `PLANNED_FOR`, `OCCURRED_DURING`, `BOOKED_BY`, `ATTENDED_BY`, `PREFERS`, `ALLERGIC_TO`, `REQUESTED_BY`, `SERVED_TO`, `SCHEDULED_FOR`, `DUE_ON`, `COMPLETED_ON`, `STARTED_ON`, `VALID_FROM`, `EFFECTIVE_FROM`, `LAST_DONE`, `NEXT_DUE`, `HOSTS`, `AUTHENTICATES`, `BACKS_UP_TO`, `STREAMS_TO`, `RELATED_TO`, `LINKED_TO`, `ASSOCIATED_WITH`, `MENTIONED_IN`, `TAGGED_WITH`, `SIMILAR_TO`, `REPLACED_BY`, `DERIVED_FROM`, `AFFECTS`, `has_fault`, `has_part`, `related_to`, `causes`, `resolves`

### `graph_node_type`
Values: `equipment`, `part`, `system`, `subcomponent`, `fault`, `symptom`, `procedure`, `measurement`, `specification`, `consumable`, `tool`, `document`, `manual`, `drawing`, `certificate`, `report`, `sop`, `checklist`, `log_entry`, `work_order`, `service_record`, `person`, `role`, `department`, `watch`, `qualification`, `training`, `voyage`, `passage`, `port`, `waypoint`, `route`, `anchorage`, `chart`, `weather_window`, `regulation`, `inspection`, `drill`, `incident`, `deficiency`, `corrective_action`, `permit`, `flag_requirement`, `invoice`, `purchase_order`, `expense`, `budget`, `contract`, `policy`, `claim`, `payment`, `currency`, `supplier`, `manufacturer`, `agent`, `shipyard`, `surveyor`, `service_provider`, `guest`, `trip`, `itinerary`, `preference`, `activity`, `dietary_requirement`, `reservation`, `menu`, `recipe`, `provision`, `linen`, `uniform`, `amenity`, `cabin`, `area`, `tender`, `toy`, `dive_equipment`, `mooring_equipment`, `deck_area`, `cover`, `network_device`, `av_system`, `software`, `credential`, `connection`, `ip_address`, `medication`, `medical_equipment`, `medical_record`, `vaccination`, `location`, `compartment`, `tank`, `locker`, `void`, `date`, `time_period`, `schedule`, `deadline`, `milestone`, `identifier`, `reference`, `tag`, `note`, `other`

### `handover_draft_state`
Values: `DRAFT`, `IN_REVIEW`, `ACCEPTED`, `SIGNED`, `EXPORTED`

### `handover_entry_status`
Values: `candidate`, `included`, `suppressed`, `resolved`

### `handover_source_type`
Values: `fault`, `work_order`, `history`, `document`, `predictive`, `note`

### `insight_type`
Values: `threshold_alert`, `pattern_detected`, `trend_warning`, `crew_frustration`, `inventory_gap`, `compliance_due`

### `maintenance_action_type`
Values: `inspect`, `check`, `test`, `measure`, `record`, `clean`, `lubricate`, `adjust`, `calibrate`, `tighten`, `replace`, `repair`, `rebuild`, `overhaul`, `recondition`, `service`, `flush`, `drain`, `fill`, `bleed`, `purge`, `sample`, `analyze`, `diagnose`, `troubleshoot`, `document`, `photograph`, `report`, `certify`, `other`, `oil_change`, `filter_replace`, `belt_check`, `coolant_check`, `pressure_test`, `visual_inspection`

### `note_type`
Values: `general`, `observation`, `warning`, `resolution`, `handover`

### `pms_entity_type`
Values: `equipment`, `part`, `fault`, `supplier`

### `presentation_bucket`
Values: `Command`, `Engineering`, `ETO_AVIT`, `Deck`, `Interior`, `Galley`, `Security`, `Admin_Compliance`

### `risk_level`
Values: `normal`, `monitor`, `emerging`, `high`, `critical`

### `risk_tag`
Values: `Safety_Critical`, `Compliance_Critical`, `Guest_Impacting`, `Cost_Impacting`, `Operational_Debt`, `Informational`

### `snapshot_type`
Values: `briefing`, `legacy`, `predictive`

### `system_type`
Values: `main_engine`, `generator`, `hvac`, `electrical`, `hydraulic`, `plumbing`, `fuel`, `freshwater`, `blackwater`, `graywater`, `fire_suppression`, `steering`, `stabilizers`, `thrusters`, `anchor_windlass`, `propulsion`, `navigation`, `communication`, `radar`, `ecdis`, `autopilot`, `gyro`, `lifesaving`, `firefighting`, `security`, `cctv`, `galley`, `laundry`, `housekeeping`, `provisions`, `tender`, `toys`, `dive`, `mooring`, `deck_equipment`, `av_entertainment`, `network`, `satellite`, `lighting_control`, `crew_management`, `guest_services`, `finance`, `compliance`, `charter`, `general`, `multi_system`, `vessel_wide`

### `work_order_priority`
Values: `routine`, `important`, `critical`, `emergency`

### `work_order_status`
Values: `planned`, `in_progress`, `completed`, `deferred`, `cancelled`

### `work_order_type`
Values: `scheduled`, `corrective`, `unplanned`, `preventive`

---

## Tables

### `pms_faults`
**Row Count**: 1,623

**Columns** (19):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_id` | uuid | NO |  |  |
| `fault_code` | text | YES |  |  |
| `title` | text | NO |  |  |
| `description` | text | YES |  |  |
| `severity` | USER-DEFINED | NO | 'medium'::fault_severity | enum: fault_severity |
| `detected_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `resolved_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `resolved_by` | uuid | YES |  |  |
| `work_order_id` | uuid | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `updated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |
| `status` | text | YES | 'open'::text |  |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18180_13_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18180_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18180_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18180_3_not_null`: equipment_id IS NOT NULL
- **CHECK** `2200_18180_5_not_null`: title IS NOT NULL
- **CHECK** `2200_18180_7_not_null`: severity IS NOT NULL
- **CHECK** `2200_18180_8_not_null`: detected_at IS NOT NULL
- **CHECK** `pms_faults_status_check`: (status = ANY (ARRAY['open'::text, 'investigating'::text, 'resolved'::text, 'closed'::text]))

**Indexes** (14):
- `faults_pkey`
  ```sql
  CREATE UNIQUE INDEX faults_pkey ON public.pms_faults USING btree (id)
  ```
- `idx_faults_code`
  ```sql
  CREATE INDEX idx_faults_code ON public.pms_faults USING btree (yacht_id, fault_code) WHERE (fault_code IS NOT NULL)
  ```
- `idx_faults_date`
  ```sql
  CREATE INDEX idx_faults_date ON public.pms_faults USING btree (yacht_id, created_at DESC)
  ```
- `idx_faults_detected`
  ```sql
  CREATE INDEX idx_faults_detected ON public.pms_faults USING btree (yacht_id, detected_at DESC)
  ```
- `idx_faults_detected_at`
  ```sql
  CREATE INDEX idx_faults_detected_at ON public.pms_faults USING btree (detected_at)
  ```
- `idx_faults_equipment`
  ```sql
  CREATE INDEX idx_faults_equipment ON public.pms_faults USING btree (equipment_id)
  ```
- `idx_faults_equipment_id`
  ```sql
  CREATE INDEX idx_faults_equipment_id ON public.pms_faults USING btree (equipment_id)
  ```
- `idx_faults_fault_code`
  ```sql
  CREATE INDEX idx_faults_fault_code ON public.pms_faults USING btree (fault_code)
  ```
- `idx_faults_severity`
  ```sql
  CREATE INDEX idx_faults_severity ON public.pms_faults USING btree (severity)
  ```
- `idx_faults_work_order_id`
  ```sql
  CREATE INDEX idx_faults_work_order_id ON public.pms_faults USING btree (work_order_id)
  ```
- `idx_faults_yacht_id`
  ```sql
  CREATE INDEX idx_faults_yacht_id ON public.pms_faults USING btree (yacht_id)
  ```
- `idx_pms_faults_equipment`
  ```sql
  CREATE INDEX idx_pms_faults_equipment ON public.pms_faults USING btree (equipment_id)
  ```
- `idx_pms_faults_status`
  ```sql
  CREATE INDEX idx_pms_faults_status ON public.pms_faults USING btree (yacht_id, status)
  ```
- `idx_pms_faults_yacht`
  ```sql
  CREATE INDEX idx_pms_faults_yacht ON public.pms_faults USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Engineers can manage faults** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'deck'::text, 'interior'::text])))`
- **Service role full access faults** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view faults** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (4):
- `no_hard_delete_faults` (BEFORE DELETE)
  - Action: EXECUTE FUNCTION prevent_hard_delete()
- `set_updated_at_faults` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at()
- `trg_fault_insert_predictive` (AFTER INSERT)
  - Action: EXECUTE FUNCTION on_fault_insert_notify_predictive()
- `trg_fault_update_predictive` (AFTER UPDATE)
  - Action: EXECUTE FUNCTION on_fault_update_notify_predictive()

---

### `pms_work_orders`
**Row Count**: 2,820

**Columns** (29):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_id` | uuid | YES |  |  |
| `title` | text | NO |  |  |
| `description` | text | YES |  |  |
| `type` | USER-DEFINED | NO | 'scheduled'::work_order_type | enum: work_order_type |
| `priority` | USER-DEFINED | NO | 'routine'::work_order_priority | enum: work_order_priority |
| `status` | USER-DEFINED | NO | 'planned'::work_order_status | enum: work_order_status |
| `due_date` | date | YES |  |  |
| `due_hours` | integer | YES |  | enum: int4 |
| `last_completed_date` | date | YES |  |  |
| `last_completed_hours` | integer | YES |  | enum: int4 |
| `frequency` | jsonb | YES |  |  |
| `created_by` | uuid | NO |  |  |
| `updated_by` | uuid | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `wo_number` | text | YES |  |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |
| `work_order_type` | text | YES | 'planned'::text |  |
| `fault_id` | uuid | YES |  |  |
| `assigned_to` | uuid | YES |  |  |
| `completed_by` | uuid | YES |  |  |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `completion_notes` | text | YES |  |  |
| `vendor_contact_hash` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `fault_id` → `pms_faults(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18104_14_not_null`: created_by IS NOT NULL
- **CHECK** `2200_18104_17_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18104_18_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_18104_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18104_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18104_4_not_null`: title IS NOT NULL
- **CHECK** `2200_18104_6_not_null`: type IS NOT NULL
- **CHECK** `2200_18104_7_not_null`: priority IS NOT NULL
- **CHECK** `2200_18104_8_not_null`: status IS NOT NULL

**Indexes** (18):
- `idx_pms_work_orders_assigned`
  ```sql
  CREATE INDEX idx_pms_work_orders_assigned ON public.pms_work_orders USING btree (assigned_to) WHERE (status <> ALL (ARRAY['completed'::work_order_status, 'cancelled'::work_order_status]))
  ```
- `idx_pms_work_orders_completed_by`
  ```sql
  CREATE INDEX idx_pms_work_orders_completed_by ON public.pms_work_orders USING btree (completed_by, completed_at DESC) WHERE (completed_by IS NOT NULL)
  ```
- `idx_pms_work_orders_equipment`
  ```sql
  CREATE INDEX idx_pms_work_orders_equipment ON public.pms_work_orders USING btree (equipment_id)
  ```
- `idx_pms_work_orders_fault`
  ```sql
  CREATE INDEX idx_pms_work_orders_fault ON public.pms_work_orders USING btree (fault_id) WHERE (fault_id IS NOT NULL)
  ```
- `idx_pms_work_orders_status`
  ```sql
  CREATE INDEX idx_pms_work_orders_status ON public.pms_work_orders USING btree (yacht_id, status)
  ```
- `idx_pms_work_orders_vendor_hash`
  ```sql
  CREATE INDEX idx_pms_work_orders_vendor_hash ON public.pms_work_orders USING btree (vendor_contact_hash) WHERE (vendor_contact_hash IS NOT NULL)
  ```
- `idx_pms_work_orders_wo_number`
  ```sql
  CREATE INDEX idx_pms_work_orders_wo_number ON public.pms_work_orders USING btree (yacht_id, wo_number)
  ```
- `idx_pms_work_orders_yacht`
  ```sql
  CREATE INDEX idx_pms_work_orders_yacht ON public.pms_work_orders USING btree (yacht_id)
  ```
- `idx_work_orders_created`
  ```sql
  CREATE INDEX idx_work_orders_created ON public.pms_work_orders USING btree (yacht_id, created_at DESC)
  ```
- `idx_work_orders_due`
  ```sql
  CREATE INDEX idx_work_orders_due ON public.pms_work_orders USING btree (yacht_id, due_date) WHERE (due_date IS NOT NULL)
  ```
- `idx_work_orders_due_date`
  ```sql
  CREATE INDEX idx_work_orders_due_date ON public.pms_work_orders USING btree (due_date)
  ```
- `idx_work_orders_equipment`
  ```sql
  CREATE INDEX idx_work_orders_equipment ON public.pms_work_orders USING btree (equipment_id) WHERE (equipment_id IS NOT NULL)
  ```
- `idx_work_orders_equipment_id`
  ```sql
  CREATE INDEX idx_work_orders_equipment_id ON public.pms_work_orders USING btree (equipment_id)
  ```
- `idx_work_orders_priority`
  ```sql
  CREATE INDEX idx_work_orders_priority ON public.pms_work_orders USING btree (priority)
  ```
- `idx_work_orders_status`
  ```sql
  CREATE INDEX idx_work_orders_status ON public.pms_work_orders USING btree (status)
  ```
- `idx_work_orders_wo_number`
  ```sql
  CREATE INDEX idx_work_orders_wo_number ON public.pms_work_orders USING btree (wo_number)
  ```
- `idx_work_orders_yacht_id`
  ```sql
  CREATE INDEX idx_work_orders_yacht_id ON public.pms_work_orders USING btree (yacht_id)
  ```
- `work_orders_pkey`
  ```sql
  CREATE UNIQUE INDEX work_orders_pkey ON public.pms_work_orders USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (5):
- **Engineers can create work orders** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'deck'::text, 'interior'::text])))`
- **Engineers can update work orders** (UPDATE)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text])))`
- **Managers can delete work orders** (DELETE)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Service role full access work_orders** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view work orders** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (4):
- `no_hard_delete_work_orders` (BEFORE DELETE)
  - Action: EXECUTE FUNCTION prevent_hard_delete()
- `set_updated_at_work_orders` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at()
- `trg_work_order_insert_predictive` (AFTER INSERT)
  - Action: EXECUTE FUNCTION on_work_order_insert_notify_predictive()
- `trg_work_order_update_predictive` (AFTER UPDATE)
  - Action: EXECUTE FUNCTION on_work_order_update_notify_predictive()

---

### `pms_audit_log`
**Row Count**: 147

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `action` | text | NO |  |  |
| `entity_type` | text | NO |  |  |
| `entity_id` | uuid | NO |  |  |
| `user_id` | uuid | NO |  |  |
| `signature` | jsonb | NO |  |  |
| `old_values` | jsonb | YES |  |  |
| `new_values` | jsonb | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `metadata` | jsonb | YES | '{}'::jsonb |  |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_126648_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_126648_1_not_null`: id IS NOT NULL
- **CHECK** `2200_126648_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_126648_3_not_null`: action IS NOT NULL
- **CHECK** `2200_126648_4_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_126648_5_not_null`: entity_id IS NOT NULL
- **CHECK** `2200_126648_6_not_null`: user_id IS NOT NULL
- **CHECK** `2200_126648_7_not_null`: signature IS NOT NULL
- **CHECK** `2200_126648_9_not_null`: new_values IS NOT NULL

**Indexes** (5):
- `idx_pms_audit_log_action`
  ```sql
  CREATE INDEX idx_pms_audit_log_action ON public.pms_audit_log USING btree (action, created_at DESC)
  ```
- `idx_pms_audit_log_entity`
  ```sql
  CREATE INDEX idx_pms_audit_log_entity ON public.pms_audit_log USING btree (entity_type, entity_id, created_at DESC)
  ```
- `idx_pms_audit_log_user`
  ```sql
  CREATE INDEX idx_pms_audit_log_user ON public.pms_audit_log USING btree (user_id, created_at DESC)
  ```
- `idx_pms_audit_log_yacht`
  ```sql
  CREATE INDEX idx_pms_audit_log_yacht ON public.pms_audit_log USING btree (yacht_id, created_at DESC)
  ```
- `pms_audit_log_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_audit_log_pkey ON public.pms_audit_log USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **pms_audit_log_yacht_isolation** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id = (current_setting('app.current_yacht_id'::text))::uuid)`

---

### `decision_audit_log`
**Row Count**: 540

**Columns** (21):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `execution_id` | uuid | NO |  |  |
| `timestamp` | timestamp with time zone | NO | now() | enum: timestamptz |
| `user_id` | uuid | NO |  |  |
| `yacht_id` | uuid | NO |  |  |
| `session_id` | uuid | YES |  |  |
| `user_role` | text | YES |  |  |
| `action` | text | NO |  |  |
| `decision` | text | NO |  |  |
| `tier` | text | YES |  |  |
| `confidence_total` | double precision | YES | 0.0 | enum: float8 |
| `confidence_intent` | double precision | YES | 0.0 | enum: float8 |
| `confidence_entity` | double precision | YES | 0.0 | enum: float8 |
| `confidence_situation` | double precision | YES | 0.0 | enum: float8 |
| `reasons` | jsonb | YES | '[]'::jsonb |  |
| `blocked_by` | text | YES |  |  |
| `blocked_by_type` | text | YES |  |  |
| `detected_intents` | jsonb | YES | '[]'::jsonb |  |
| `entities` | jsonb | YES | '[]'::jsonb |  |
| `situation` | jsonb | YES | '{}'::jsonb |  |
| `environment` | text | YES | 'at_sea'::text |  |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_146466_1_not_null`: id IS NOT NULL
- **CHECK** `2200_146466_2_not_null`: execution_id IS NOT NULL
- **CHECK** `2200_146466_3_not_null`: timestamp IS NOT NULL
- **CHECK** `2200_146466_4_not_null`: user_id IS NOT NULL
- **CHECK** `2200_146466_5_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_146466_8_not_null`: action IS NOT NULL
- **CHECK** `2200_146466_9_not_null`: decision IS NOT NULL

**Indexes** (7):
- `decision_audit_log_pkey`
  ```sql
  CREATE UNIQUE INDEX decision_audit_log_pkey ON public.decision_audit_log USING btree (id)
  ```
- `idx_decision_audit_action`
  ```sql
  CREATE INDEX idx_decision_audit_action ON public.decision_audit_log USING btree (action, decision)
  ```
- `idx_decision_audit_analytics`
  ```sql
  CREATE INDEX idx_decision_audit_analytics ON public.decision_audit_log USING btree (yacht_id, action, decision, "timestamp" DESC)
  ```
- `idx_decision_audit_execution`
  ```sql
  CREATE INDEX idx_decision_audit_execution ON public.decision_audit_log USING btree (execution_id)
  ```
- `idx_decision_audit_timestamp`
  ```sql
  CREATE INDEX idx_decision_audit_timestamp ON public.decision_audit_log USING btree ("timestamp" DESC)
  ```
- `idx_decision_audit_user`
  ```sql
  CREATE INDEX idx_decision_audit_user ON public.decision_audit_log USING btree (user_id, "timestamp" DESC)
  ```
- `idx_decision_audit_yacht`
  ```sql
  CREATE INDEX idx_decision_audit_yacht ON public.decision_audit_log USING btree (yacht_id, "timestamp" DESC)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role can insert** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `true`
- **Service role can select** (SELECT)
  - Roles: ['public']
  - USING: `(auth.role() = 'service_role'::text)`
- **Users can view their yacht decisions** (SELECT)
  - Roles: ['public']
  - USING: `((yacht_id)::text = (auth.jwt() ->> 'yacht_id'::text))`

---

### `related_audit_events`
**Row Count**: 0

**Columns** (6):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | NO |  |  |
| `event_name` | text | NO |  |  |
| `payload` | jsonb | NO |  |  |
| `occurred_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_140228_1_not_null`: id IS NOT NULL
- **CHECK** `2200_140228_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_140228_3_not_null`: user_id IS NOT NULL
- **CHECK** `2200_140228_4_not_null`: event_name IS NOT NULL
- **CHECK** `2200_140228_5_not_null`: payload IS NOT NULL
- **CHECK** `2200_140228_6_not_null`: occurred_at IS NOT NULL
- **CHECK** `related_audit_events_event_name_check`: (event_name = ANY (ARRAY['artefact_opened'::text, 'relation_added'::text, 'situation_ended'::text]))

**Indexes** (3):
- `idx_related_audit_events_event_name`
  ```sql
  CREATE INDEX idx_related_audit_events_event_name ON public.related_audit_events USING btree (yacht_id, event_name)
  ```
- `idx_related_audit_events_yacht_occurred`
  ```sql
  CREATE INDEX idx_related_audit_events_yacht_occurred ON public.related_audit_events USING btree (yacht_id, occurred_at DESC)
  ```
- `related_audit_events_pkey`
  ```sql
  CREATE UNIQUE INDEX related_audit_events_pkey ON public.related_audit_events USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role manages related_audit_events** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **related_audit_events_insert_own_yacht** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `((yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))) AND (user_id = auth.uid()))`
- **related_audit_events_select_own_yacht** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

---

### ❌ MISSING: `pms_fault_notes`
**Status**: Table does not exist in production database.

### ❌ MISSING: `pms_fault_attachments`
**Status**: Table does not exist in production database.

### `action_confirmations`
**Row Count**: 0

**Columns** (19):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | NO |  |  |
| `action_type` | text | NO |  |  |
| `entity_type` | text | NO |  |  |
| `entity_id` | uuid | NO |  |  |
| `confirmation_title` | text | NO |  |  |
| `confirmation_message` | text | NO |  |  |
| `changes_summary` | jsonb | NO |  |  |
| `can_undo` | boolean | YES | true | enum: bool |
| `undo_deadline` | timestamp with time zone | YES |  | enum: timestamptz |
| `undo_action` | jsonb | YES |  |  |
| `was_undone` | boolean | YES | false | enum: bool |
| `undone_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `related_actions` | ARRAY | YES |  | enum: _uuid |
| `source_session_id` | uuid | YES |  |  |
| `source_context` | text | YES | 'direct'::text |  |
| `ledger_event_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_135807_19_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135807_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135807_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_135807_3_not_null`: user_id IS NOT NULL
- **CHECK** `2200_135807_4_not_null`: action_type IS NOT NULL
- **CHECK** `2200_135807_5_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_135807_6_not_null`: entity_id IS NOT NULL
- **CHECK** `2200_135807_7_not_null`: confirmation_title IS NOT NULL
- **CHECK** `2200_135807_8_not_null`: confirmation_message IS NOT NULL
- **CHECK** `2200_135807_9_not_null`: changes_summary IS NOT NULL
- **CHECK** `valid_source`: (source_context = ANY (ARRAY['search'::text, 'direct'::text, 'microaction'::text, 'api'::text, 'scheduled'::text]))

**Indexes** (6):
- `action_confirmations_pkey`
  ```sql
  CREATE UNIQUE INDEX action_confirmations_pkey ON public.action_confirmations USING btree (id)
  ```
- `idx_action_confirmations_action`
  ```sql
  CREATE INDEX idx_action_confirmations_action ON public.action_confirmations USING btree (action_type)
  ```
- `idx_action_confirmations_created`
  ```sql
  CREATE INDEX idx_action_confirmations_created ON public.action_confirmations USING btree (created_at DESC)
  ```
- `idx_action_confirmations_entity`
  ```sql
  CREATE INDEX idx_action_confirmations_entity ON public.action_confirmations USING btree (entity_type, entity_id)
  ```
- `idx_action_confirmations_user`
  ```sql
  CREATE INDEX idx_action_confirmations_user ON public.action_confirmations USING btree (user_id)
  ```
- `idx_action_confirmations_yacht`
  ```sql
  CREATE INDEX idx_action_confirmations_yacht ON public.action_confirmations USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **action_confirmations_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(user_id = auth.uid())`
- **action_confirmations_own** (SELECT)
  - Roles: ['authenticated']
  - USING: `(user_id = auth.uid())`
- **action_confirmations_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `action_executions`
**Row Count**: 0

**Columns** (13):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | NO |  |  |
| `action_name` | text | NO |  |  |
| `entity_type` | text | NO |  |  |
| `entity_id` | uuid | YES |  |  |
| `params` | jsonb | YES |  |  |
| `result` | jsonb | YES |  |  |
| `success` | boolean | NO |  | enum: bool |
| `error_code` | text | YES |  |  |
| `error_message` | text | YES |  |  |
| `duration_ms` | integer | YES |  | enum: int4 |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_137308_13_not_null`: created_at IS NOT NULL
- **CHECK** `2200_137308_1_not_null`: id IS NOT NULL
- **CHECK** `2200_137308_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_137308_3_not_null`: user_id IS NOT NULL
- **CHECK** `2200_137308_4_not_null`: action_name IS NOT NULL
- **CHECK** `2200_137308_5_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_137308_9_not_null`: success IS NOT NULL

**Indexes** (2):
- `action_executions_pkey`
  ```sql
  CREATE UNIQUE INDEX action_executions_pkey ON public.action_executions USING btree (id)
  ```
- `idx_action_executions_yacht`
  ```sql
  CREATE INDEX idx_action_executions_yacht ON public.action_executions USING btree (yacht_id, created_at DESC)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **vessel_isolation_action_executions** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

---

### `alias_crew`
**Row Count**: 0

**Columns** (7):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `crew_id` | uuid | YES |  |  |
| `alias` | text | NO |  |  |
| `alias_type` | text | YES | 'manual'::text |  |
| `confidence` | double precision | YES | 1.0 | enum: float8 |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_29926_1_not_null`: id IS NOT NULL
- **CHECK** `2200_29926_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_29926_4_not_null`: alias IS NOT NULL
- **CHECK** `crew_aliases_alias_type_check`: (alias_type = ANY (ARRAY['manual'::text, 'learned'::text, 'llm_generated'::text]))

**Indexes** (4):
- `crew_aliases_pkey`
  ```sql
  CREATE UNIQUE INDEX crew_aliases_pkey ON public.alias_crew USING btree (id)
  ```
- `idx_crew_aliases_trgm`
  ```sql
  CREATE INDEX idx_crew_aliases_trgm ON public.alias_crew USING gin (alias gin_trgm_ops)
  ```
- `idx_crew_aliases_unique`
  ```sql
  CREATE UNIQUE INDEX idx_crew_aliases_unique ON public.alias_crew USING btree (yacht_id, lower(alias))
  ```
- `idx_crew_aliases_yacht`
  ```sql
  CREATE INDEX idx_crew_aliases_yacht ON public.alias_crew USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access to crew_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Yacht isolation for crew_aliases** (ALL)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `alias_documents`
**Row Count**: 0

**Columns** (7):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `document_id` | uuid | YES |  |  |
| `alias` | text | NO |  |  |
| `alias_type` | text | YES | 'manual'::text |  |
| `confidence` | double precision | YES | 1.0 | enum: float8 |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `document_id` → `doc_metadata(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_29880_1_not_null`: id IS NOT NULL
- **CHECK** `2200_29880_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_29880_4_not_null`: alias IS NOT NULL
- **CHECK** `document_aliases_alias_type_check`: (alias_type = ANY (ARRAY['manual'::text, 'learned'::text, 'llm_generated'::text]))

**Indexes** (5):
- `document_aliases_pkey`
  ```sql
  CREATE UNIQUE INDEX document_aliases_pkey ON public.alias_documents USING btree (id)
  ```
- `document_aliases_yacht_alias_unique`
  ```sql
  CREATE UNIQUE INDEX document_aliases_yacht_alias_unique ON public.alias_documents USING btree (yacht_id, alias)
  ```
- `idx_document_aliases_trgm`
  ```sql
  CREATE INDEX idx_document_aliases_trgm ON public.alias_documents USING gin (alias gin_trgm_ops)
  ```
- `idx_document_aliases_unique`
  ```sql
  CREATE UNIQUE INDEX idx_document_aliases_unique ON public.alias_documents USING btree (yacht_id, lower(alias))
  ```
- `idx_document_aliases_yacht`
  ```sql
  CREATE INDEX idx_document_aliases_yacht ON public.alias_documents USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access to document_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Yacht isolation for document_aliases** (ALL)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `alias_equipment`
**Row Count**: 55

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_id` | uuid | NO |  |  |
| `alias` | text | NO |  |  |
| `is_primary` | boolean | NO | false | enum: bool |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `confidence` | double precision | YES | 1.0 | enum: float8 |
| `source` | text | YES | 'manual'::text |  |
| `candidate_id` | uuid | YES |  |  |
| `master_candidate_id` | uuid | YES |  |  |
| `deployed_at` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `alias`
- **CHECK** `2200_23912_1_not_null`: id IS NOT NULL
- **CHECK** `2200_23912_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_23912_3_not_null`: equipment_id IS NOT NULL
- **CHECK** `2200_23912_4_not_null`: alias IS NOT NULL
- **CHECK** `2200_23912_5_not_null`: is_primary IS NOT NULL
- **CHECK** `2200_23912_6_not_null`: created_at IS NOT NULL

**Indexes** (10):
- `equipment_aliases_pkey`
  ```sql
  CREATE UNIQUE INDEX equipment_aliases_pkey ON public.alias_equipment USING btree (id)
  ```
- `equipment_aliases_yacht_alias_unique`
  ```sql
  CREATE UNIQUE INDEX equipment_aliases_yacht_alias_unique ON public.alias_equipment USING btree (yacht_id, alias)
  ```
- `equipment_aliases_yacht_id_alias_key`
  ```sql
  CREATE UNIQUE INDEX equipment_aliases_yacht_id_alias_key ON public.alias_equipment USING btree (yacht_id, alias)
  ```
- `idx_equipment_aliases_alias_trgm`
  ```sql
  CREATE INDEX idx_equipment_aliases_alias_trgm ON public.alias_equipment USING gin (alias gin_trgm_ops)
  ```
- `idx_equipment_aliases_equipment`
  ```sql
  CREATE INDEX idx_equipment_aliases_equipment ON public.alias_equipment USING btree (equipment_id)
  ```
- `idx_equipment_aliases_lookup`
  ```sql
  CREATE INDEX idx_equipment_aliases_lookup ON public.alias_equipment USING btree (yacht_id, lower(alias))
  ```
- `idx_equipment_aliases_lower`
  ```sql
  CREATE INDEX idx_equipment_aliases_lower ON public.alias_equipment USING btree (yacht_id, lower(alias))
  ```
- `idx_equipment_aliases_unique`
  ```sql
  CREATE UNIQUE INDEX idx_equipment_aliases_unique ON public.alias_equipment USING btree (yacht_id, lower(alias))
  ```
- `idx_equipment_aliases_yacht`
  ```sql
  CREATE INDEX idx_equipment_aliases_yacht ON public.alias_equipment USING btree (yacht_id)
  ```
- `idx_equipment_aliases_yacht_alias`
  ```sql
  CREATE UNIQUE INDEX idx_equipment_aliases_yacht_alias ON public.alias_equipment USING btree (yacht_id, lower(alias))
  ```

**RLS**: ✅ ENABLED
**Policies** (5):
- **Service role full access equipment_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Service role full access to equipment_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **System can manage equipment aliases** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`
- **Users can view equipment aliases** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`
- **Yacht isolation for equipment_aliases** (ALL)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `alias_faults`
**Row Count**: 0

**Columns** (10):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `fault_id` | uuid | YES |  |  |
| `alias` | text | NO |  |  |
| `alias_type` | text | YES | 'manual'::text |  |
| `confidence` | double precision | YES | 1.0 | enum: float8 |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `source` | text | YES | 'manual'::text |  |
| `master_candidate_id` | uuid | YES |  |  |
| `deployed_at` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `fault_id` → `pms_faults(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_29830_1_not_null`: id IS NOT NULL
- **CHECK** `2200_29830_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_29830_4_not_null`: alias IS NOT NULL
- **CHECK** `fault_aliases_alias_type_check`: (alias_type = ANY (ARRAY['manual'::text, 'learned'::text, 'llm_generated'::text]))

**Indexes** (5):
- `fault_aliases_pkey`
  ```sql
  CREATE UNIQUE INDEX fault_aliases_pkey ON public.alias_faults USING btree (id)
  ```
- `fault_aliases_yacht_alias_unique`
  ```sql
  CREATE UNIQUE INDEX fault_aliases_yacht_alias_unique ON public.alias_faults USING btree (yacht_id, alias)
  ```
- `idx_fault_aliases_trgm`
  ```sql
  CREATE INDEX idx_fault_aliases_trgm ON public.alias_faults USING gin (alias gin_trgm_ops)
  ```
- `idx_fault_aliases_unique`
  ```sql
  CREATE UNIQUE INDEX idx_fault_aliases_unique ON public.alias_faults USING btree (yacht_id, lower(alias))
  ```
- `idx_fault_aliases_yacht`
  ```sql
  CREATE INDEX idx_fault_aliases_yacht ON public.alias_faults USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access to fault_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Yacht isolation for fault_aliases** (ALL)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `alias_parts`
**Row Count**: 0

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `part_id` | uuid | NO |  |  |
| `alias` | text | NO |  |  |
| `alias_type` | text | YES | 'manual'::text |  |
| `confidence` | numeric | YES | 1.0 |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `source` | text | YES | 'manual'::text |  |
| `candidate_id` | uuid | YES |  |  |
| `master_candidate_id` | uuid | YES |  |  |
| `deployed_at` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `part_id` → `pms_parts(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_29500_1_not_null`: id IS NOT NULL
- **CHECK** `2200_29500_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_29500_3_not_null`: part_id IS NOT NULL
- **CHECK** `2200_29500_4_not_null`: alias IS NOT NULL
- **CHECK** `part_aliases_alias_type_check`: (alias_type = ANY (ARRAY['manual'::text, 'extracted'::text, 'inferred'::text]))

**Indexes** (8):
- `idx_part_aliases_alias_trgm`
  ```sql
  CREATE INDEX idx_part_aliases_alias_trgm ON public.alias_parts USING gin (alias gin_trgm_ops)
  ```
- `idx_part_aliases_part`
  ```sql
  CREATE INDEX idx_part_aliases_part ON public.alias_parts USING btree (part_id)
  ```
- `idx_part_aliases_trgm`
  ```sql
  CREATE INDEX idx_part_aliases_trgm ON public.alias_parts USING gin (alias gin_trgm_ops)
  ```
- `idx_part_aliases_unique`
  ```sql
  CREATE UNIQUE INDEX idx_part_aliases_unique ON public.alias_parts USING btree (yacht_id, lower(alias))
  ```
- `idx_part_aliases_yacht`
  ```sql
  CREATE INDEX idx_part_aliases_yacht ON public.alias_parts USING btree (yacht_id)
  ```
- `idx_part_aliases_yacht_alias`
  ```sql
  CREATE UNIQUE INDEX idx_part_aliases_yacht_alias ON public.alias_parts USING btree (yacht_id, lower(alias))
  ```
- `part_aliases_pkey`
  ```sql
  CREATE UNIQUE INDEX part_aliases_pkey ON public.alias_parts USING btree (id)
  ```
- `part_aliases_yacht_alias_unique`
  ```sql
  CREATE UNIQUE INDEX part_aliases_yacht_alias_unique ON public.alias_parts USING btree (yacht_id, alias)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access to part_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Yacht isolation for part_aliases** (ALL)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `alias_roles`
**Row Count**: 27

**Columns** (4):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `canonical_role` | text | NO |  |  |
| `alias` | text | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `alias`
- **CHECK** `2200_23964_1_not_null`: id IS NOT NULL
- **CHECK** `2200_23964_2_not_null`: canonical_role IS NOT NULL
- **CHECK** `2200_23964_3_not_null`: alias IS NOT NULL
- **CHECK** `2200_23964_4_not_null`: created_at IS NOT NULL

**Indexes** (2):
- `role_aliases_alias_key`
  ```sql
  CREATE UNIQUE INDEX role_aliases_alias_key ON public.alias_roles USING btree (alias)
  ```
- `role_aliases_pkey`
  ```sql
  CREATE UNIQUE INDEX role_aliases_pkey ON public.alias_roles USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **Service role full access role_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`

---

### `alias_symptoms`
**Row Count**: 37

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `symptom_id` | uuid | YES |  |  |
| `alias` | text | NO |  |  |
| `alias_type` | text | YES | 'manual'::text |  |
| `confidence` | double precision | YES | 1.0 | enum: float8 |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `source` | text | YES | 'manual'::text |  |
| `candidate_id` | uuid | YES |  |  |
| `master_candidate_id` | uuid | YES |  |  |
| `deployed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `symptom_code` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_29810_1_not_null`: id IS NOT NULL
- **CHECK** `2200_29810_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_29810_4_not_null`: alias IS NOT NULL
- **CHECK** `symptom_aliases_alias_type_check`: (alias_type = ANY (ARRAY['manual'::text, 'learned'::text, 'llm_generated'::text]))

**Indexes** (5):
- `idx_symptom_aliases_trgm`
  ```sql
  CREATE INDEX idx_symptom_aliases_trgm ON public.alias_symptoms USING gin (alias gin_trgm_ops)
  ```
- `idx_symptom_aliases_unique`
  ```sql
  CREATE UNIQUE INDEX idx_symptom_aliases_unique ON public.alias_symptoms USING btree (yacht_id, lower(alias))
  ```
- `idx_symptom_aliases_yacht`
  ```sql
  CREATE INDEX idx_symptom_aliases_yacht ON public.alias_symptoms USING btree (yacht_id)
  ```
- `symptom_aliases_pkey`
  ```sql
  CREATE UNIQUE INDEX symptom_aliases_pkey ON public.alias_symptoms USING btree (id)
  ```
- `symptom_aliases_yacht_alias_unique`
  ```sql
  CREATE UNIQUE INDEX symptom_aliases_yacht_alias_unique ON public.alias_symptoms USING btree (yacht_id, alias)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access to symptom_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Yacht isolation for symptom_aliases** (ALL)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `alias_systems`
**Row Count**: 28

**Columns** (10):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `system_type` | text | NO |  |  |
| `alias` | text | NO |  |  |
| `alias_type` | text | YES | 'manual'::text |  |
| `confidence` | double precision | YES | 1.0 | enum: float8 |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `source` | text | YES | 'manual'::text |  |
| `master_candidate_id` | uuid | YES |  |  |
| `deployed_at` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_29906_1_not_null`: id IS NOT NULL
- **CHECK** `2200_29906_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_29906_3_not_null`: system_type IS NOT NULL
- **CHECK** `2200_29906_4_not_null`: alias IS NOT NULL
- **CHECK** `system_aliases_alias_type_check`: (alias_type = ANY (ARRAY['manual'::text, 'learned'::text, 'llm_generated'::text]))

**Indexes** (4):
- `idx_system_aliases_trgm`
  ```sql
  CREATE INDEX idx_system_aliases_trgm ON public.alias_systems USING gin (alias gin_trgm_ops)
  ```
- `idx_system_aliases_unique`
  ```sql
  CREATE UNIQUE INDEX idx_system_aliases_unique ON public.alias_systems USING btree (yacht_id, lower(alias))
  ```
- `idx_system_aliases_yacht`
  ```sql
  CREATE INDEX idx_system_aliases_yacht ON public.alias_systems USING btree (yacht_id)
  ```
- `system_aliases_pkey`
  ```sql
  CREATE UNIQUE INDEX system_aliases_pkey ON public.alias_systems USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access to system_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Yacht isolation for system_aliases** (ALL)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `alias_tasks`
**Row Count**: 0

**Columns** (7):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `task_id` | uuid | YES |  |  |
| `alias` | text | NO |  |  |
| `alias_type` | text | YES | 'manual'::text |  |
| `confidence` | double precision | YES | 1.0 | enum: float8 |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_29946_1_not_null`: id IS NOT NULL
- **CHECK** `2200_29946_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_29946_4_not_null`: alias IS NOT NULL
- **CHECK** `task_aliases_alias_type_check`: (alias_type = ANY (ARRAY['manual'::text, 'learned'::text, 'llm_generated'::text]))

**Indexes** (4):
- `idx_task_aliases_trgm`
  ```sql
  CREATE INDEX idx_task_aliases_trgm ON public.alias_tasks USING gin (alias gin_trgm_ops)
  ```
- `idx_task_aliases_unique`
  ```sql
  CREATE UNIQUE INDEX idx_task_aliases_unique ON public.alias_tasks USING btree (yacht_id, lower(alias))
  ```
- `idx_task_aliases_yacht`
  ```sql
  CREATE INDEX idx_task_aliases_yacht ON public.alias_tasks USING btree (yacht_id)
  ```
- `task_aliases_pkey`
  ```sql
  CREATE UNIQUE INDEX task_aliases_pkey ON public.alias_tasks USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access to task_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Yacht isolation for task_aliases** (ALL)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `alias_work_orders`
**Row Count**: 0

**Columns** (7):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `work_order_id` | uuid | YES |  |  |
| `alias` | text | NO |  |  |
| `alias_type` | text | YES | 'manual'::text |  |
| `confidence` | double precision | YES | 1.0 | enum: float8 |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_29855_1_not_null`: id IS NOT NULL
- **CHECK** `2200_29855_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_29855_4_not_null`: alias IS NOT NULL
- **CHECK** `work_order_aliases_alias_type_check`: (alias_type = ANY (ARRAY['manual'::text, 'learned'::text, 'llm_generated'::text]))

**Indexes** (4):
- `idx_work_order_aliases_trgm`
  ```sql
  CREATE INDEX idx_work_order_aliases_trgm ON public.alias_work_orders USING gin (alias gin_trgm_ops)
  ```
- `idx_work_order_aliases_unique`
  ```sql
  CREATE UNIQUE INDEX idx_work_order_aliases_unique ON public.alias_work_orders USING btree (yacht_id, lower(alias))
  ```
- `idx_work_order_aliases_yacht`
  ```sql
  CREATE INDEX idx_work_order_aliases_yacht ON public.alias_work_orders USING btree (yacht_id)
  ```
- `work_order_aliases_pkey`
  ```sql
  CREATE UNIQUE INDEX work_order_aliases_pkey ON public.alias_work_orders USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access to work_order_aliases** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Yacht isolation for work_order_aliases** (ALL)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `audit_field_history`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `table_name` | text | NO |  |  |
| `record_id` | uuid | NO |  |  |
| `field_name` | text | NO |  |  |
| `old_value` | text | YES |  |  |
| `new_value` | text | YES |  |  |
| `changed_by` | uuid | NO |  |  |
| `changed_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_125333_1_not_null`: id IS NOT NULL
- **CHECK** `2200_125333_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_125333_3_not_null`: table_name IS NOT NULL
- **CHECK** `2200_125333_4_not_null`: record_id IS NOT NULL
- **CHECK** `2200_125333_5_not_null`: field_name IS NOT NULL
- **CHECK** `2200_125333_8_not_null`: changed_by IS NOT NULL
- **CHECK** `2200_125333_9_not_null`: changed_at IS NOT NULL

**Indexes** (2):
- `audit_field_history_pkey`
  ```sql
  CREATE UNIQUE INDEX audit_field_history_pkey ON public.audit_field_history USING btree (id)
  ```
- `idx_audit_history`
  ```sql
  CREATE INDEX idx_audit_history ON public.audit_field_history USING btree (table_name, record_id)
  ```

**RLS**: ❌ DISABLED

---

### `auth_api_keys`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `key_prefix` | text | NO |  |  |
| `hashed_key` | text | NO |  |  |
| `name` | text | NO |  |  |
| `scopes` | ARRAY | YES | '{}'::text[] | enum: _text |
| `created_by` | uuid | YES |  |  |
| `expires_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `last_used_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `is_active` | boolean | YES | true | enum: bool |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `hashed_key`
- **CHECK** `2200_17988_12_not_null`: created_at IS NOT NULL
- **CHECK** `2200_17988_1_not_null`: id IS NOT NULL
- **CHECK** `2200_17988_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_17988_3_not_null`: key_prefix IS NOT NULL
- **CHECK** `2200_17988_4_not_null`: hashed_key IS NOT NULL
- **CHECK** `2200_17988_5_not_null`: name IS NOT NULL
- **CHECK** `api_keys_hashed_key_check`: (hashed_key ~ '^\$2[aby]\$'::text)
- **CHECK** `api_keys_key_prefix_check`: (key_prefix ~ '^sk_(live|test)_[a-z0-9]{4,8}$'::text)

**Indexes** (5):
- `api_keys_hashed_key_key`
  ```sql
  CREATE UNIQUE INDEX api_keys_hashed_key_key ON public.auth_api_keys USING btree (hashed_key)
  ```
- `api_keys_pkey`
  ```sql
  CREATE UNIQUE INDEX api_keys_pkey ON public.auth_api_keys USING btree (id)
  ```
- `idx_api_keys_hashed_key`
  ```sql
  CREATE INDEX idx_api_keys_hashed_key ON public.auth_api_keys USING btree (hashed_key)
  ```
- `idx_api_keys_is_active`
  ```sql
  CREATE INDEX idx_api_keys_is_active ON public.auth_api_keys USING btree (is_active)
  ```
- `idx_api_keys_yacht_id`
  ```sql
  CREATE INDEX idx_api_keys_yacht_id ON public.auth_api_keys USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Managers can manage api keys** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Managers can view api keys** (SELECT)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Service role full access api_keys** (ALL)
  - Roles: ['service_role']
  - USING: `true`

---

### `auth_guest_preferences`
**Row Count**: 0

**Columns** (10):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `guest_name` | text | NO |  |  |
| `guest_node_id` | uuid | YES |  |  |
| `preference_category` | text | NO |  |  |
| `preference_key` | text | NO |  |  |
| `preference_value` | text | NO |  |  |
| `notes` | text | YES |  |  |
| `source_trip_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `guest_node_id` → `search_graph_nodes(id)` ON DELETE NO ACTION, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_24903_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_24903_1_not_null`: id IS NOT NULL
- **CHECK** `2200_24903_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_24903_3_not_null`: guest_name IS NOT NULL
- **CHECK** `2200_24903_5_not_null`: preference_category IS NOT NULL
- **CHECK** `2200_24903_6_not_null`: preference_key IS NOT NULL
- **CHECK** `2200_24903_7_not_null`: preference_value IS NOT NULL

**Indexes** (5):
- `guest_preferences_pkey`
  ```sql
  CREATE UNIQUE INDEX guest_preferences_pkey ON public.auth_guest_preferences USING btree (id)
  ```
- `idx_guest_prefs_category`
  ```sql
  CREATE INDEX idx_guest_prefs_category ON public.auth_guest_preferences USING btree (yacht_id, preference_category)
  ```
- `idx_guest_prefs_guest`
  ```sql
  CREATE INDEX idx_guest_prefs_guest ON public.auth_guest_preferences USING btree (yacht_id, guest_name)
  ```
- `idx_guest_prefs_guest_cat`
  ```sql
  CREATE INDEX idx_guest_prefs_guest_cat ON public.auth_guest_preferences USING btree (yacht_id, guest_name, preference_category)
  ```
- `idx_guest_prefs_yacht`
  ```sql
  CREATE INDEX idx_guest_prefs_yacht ON public.auth_guest_preferences USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access guest_preferences** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view yacht guest preferences** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `auth_microsoft_tokens`
**Row Count**: 2

**Columns** (23):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `user_id` | text | NO |  |  |
| `microsoft_user_id` | text | YES |  |  |
| `original_email` | text | YES |  |  |
| `microsoft_email` | text | YES |  |  |
| `display_name` | text | YES |  |  |
| `microsoft_access_token` | text | NO |  |  |
| `microsoft_refresh_token` | text | YES |  |  |
| `token_expires_at` | timestamp with time zone | NO |  | enum: timestamptz |
| `token_type` | text | YES | 'Bearer'::text |  |
| `scopes` | ARRAY | YES | ARRAY['Mail.Read'::text, 'User.Read'::text] | enum: _text |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `client_id` | text | YES |  |  |
| `client_secret` | text | YES |  |  |
| `yacht_id` | text | YES |  |  |
| `provider` | text | YES | 'microsoft_graph'::text |  |
| `token_purpose` | text | YES | 'read'::text |  |
| `provider_email_hash` | text | YES |  |  |
| `provider_display_name` | text | YES |  |  |
| `is_revoked` | boolean | YES | false | enum: bool |
| `revoked_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `revoked_by` | uuid | YES |  |  |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `user_id`, `yacht_id`, `provider`, `token_purpose`
- **CHECK** `2200_27653_1_not_null`: id IS NOT NULL
- **CHECK** `2200_27653_2_not_null`: user_id IS NOT NULL
- **CHECK** `2200_27653_7_not_null`: microsoft_access_token IS NOT NULL
- **CHECK** `2200_27653_9_not_null`: token_expires_at IS NOT NULL
- **CHECK** `auth_microsoft_tokens_token_purpose_check`: (token_purpose = ANY (ARRAY['read'::text, 'write'::text]))

**Indexes** (4):
- `auth_microsoft_tokens_user_yacht_provider_purpose_key`
  ```sql
  CREATE UNIQUE INDEX auth_microsoft_tokens_user_yacht_provider_purpose_key ON public.auth_microsoft_tokens USING btree (user_id, yacht_id, provider, token_purpose)
  ```
- `idx_auth_microsoft_tokens_user_purpose`
  ```sql
  CREATE INDEX idx_auth_microsoft_tokens_user_purpose ON public.auth_microsoft_tokens USING btree (user_id, token_purpose) WHERE ((is_revoked = false) OR (is_revoked IS NULL))
  ```
- `idx_user_microsoft_tokens_yacht_id`
  ```sql
  CREATE INDEX idx_user_microsoft_tokens_yacht_id ON public.auth_microsoft_tokens USING btree (yacht_id)
  ```
- `user_microsoft_tokens_pkey`
  ```sql
  CREATE UNIQUE INDEX user_microsoft_tokens_pkey ON public.auth_microsoft_tokens USING btree (id)
  ```

**RLS**: ❌ DISABLED
**Policies** (4):
- **Service role can manage microsoft tokens** (ALL)
  - Roles: ['public']
  - USING: `(current_setting('role'::text) = 'service_role'::text)`
- **Service role full access user_microsoft_tokens** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Service role has full access** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can access own microsoft tokens** (ALL)
  - Roles: ['public']
  - USING: `((auth.uid())::text = user_id)`

**Triggers** (1):
- `update_user_microsoft_tokens_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at_column()

---

### `auth_role_assignments`
**Row Count**: 1

**Columns** (10):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `user_id` | uuid | NO |  |  |
| `yacht_id` | uuid | NO |  |  |
| `role` | text | NO |  |  |
| `scopes` | ARRAY | YES |  | enum: _text |
| `is_active` | boolean | YES | true | enum: bool |
| `valid_from` | timestamp with time zone | YES |  | enum: timestamptz |
| `valid_until` | timestamp with time zone | YES |  | enum: timestamptz |
| `assigned_by` | uuid | YES |  |  |
| `assigned_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_21048_1_not_null`: id IS NOT NULL
- **CHECK** `2200_21048_2_not_null`: user_id IS NOT NULL
- **CHECK** `2200_21048_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_21048_4_not_null`: role IS NOT NULL

**Indexes** (4):
- `idx_user_role_assignments_active`
  ```sql
  CREATE INDEX idx_user_role_assignments_active ON public.auth_role_assignments USING btree (user_id, yacht_id) WHERE (is_active = true)
  ```
- `idx_user_role_assignments_user_id`
  ```sql
  CREATE INDEX idx_user_role_assignments_user_id ON public.auth_role_assignments USING btree (user_id)
  ```
- `idx_user_role_assignments_yacht_id`
  ```sql
  CREATE INDEX idx_user_role_assignments_yacht_id ON public.auth_role_assignments USING btree (yacht_id)
  ```
- `user_role_assignments_pkey`
  ```sql
  CREATE UNIQUE INDEX user_role_assignments_pkey ON public.auth_role_assignments USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **Service role full access user_role_assignments** (ALL)
  - Roles: ['service_role']
  - USING: `true`

---

### `auth_role_definitions`
**Row Count**: 0

**Columns** (5):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `name` | text | NO |  |  |
| `description` | text | YES |  |  |
| `permissions` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `name`
- **CHECK** `2200_18017_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18017_2_not_null`: name IS NOT NULL
- **CHECK** `2200_18017_5_not_null`: created_at IS NOT NULL

**Indexes** (2):
- `user_roles_name_key`
  ```sql
  CREATE UNIQUE INDEX user_roles_name_key ON public.auth_role_definitions USING btree (name)
  ```
- `user_roles_pkey`
  ```sql
  CREATE UNIQUE INDEX user_roles_pkey ON public.auth_role_definitions USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Anyone can view roles** (SELECT)
  - Roles: ['public']
  - USING: `true`
- **Service role full access role_definitions** (ALL)
  - Roles: ['service_role']
  - USING: `true`

---

### `auth_signatures`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | NO |  |  |
| `role_at_signing` | text | NO |  |  |
| `signature_type` | text | NO |  |  |
| `entity_type` | text | NO |  |  |
| `entity_id` | uuid | NO |  |  |
| `signature_hash` | text | NO |  |  |
| `signed_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_125324_1_not_null`: id IS NOT NULL
- **CHECK** `2200_125324_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_125324_3_not_null`: user_id IS NOT NULL
- **CHECK** `2200_125324_4_not_null`: role_at_signing IS NOT NULL
- **CHECK** `2200_125324_5_not_null`: signature_type IS NOT NULL
- **CHECK** `2200_125324_6_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_125324_7_not_null`: entity_id IS NOT NULL
- **CHECK** `2200_125324_8_not_null`: signature_hash IS NOT NULL
- **CHECK** `2200_125324_9_not_null`: signed_at IS NOT NULL

**Indexes** (1):
- `auth_signatures_pkey`
  ```sql
  CREATE UNIQUE INDEX auth_signatures_pkey ON public.auth_signatures USING btree (id)
  ```

**RLS**: ❌ DISABLED

---

### `auth_users_profiles`
**Row Count**: 1

**Columns** (8):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO |  |  |
| `yacht_id` | uuid | NO |  |  |
| `email` | text | NO |  |  |
| `name` | text | NO |  |  |
| `is_active` | boolean | NO | true | enum: bool |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `email`
- **CHECK** `2200_127910_1_not_null`: id IS NOT NULL
- **CHECK** `2200_127910_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_127910_3_not_null`: email IS NOT NULL
- **CHECK** `2200_127910_4_not_null`: name IS NOT NULL
- **CHECK** `2200_127910_5_not_null`: is_active IS NOT NULL
- **CHECK** `2200_127910_7_not_null`: created_at IS NOT NULL
- **CHECK** `2200_127910_8_not_null`: updated_at IS NOT NULL

**Indexes** (5):
- `idx_auth_users_profiles_active`
  ```sql
  CREATE INDEX idx_auth_users_profiles_active ON public.auth_users_profiles USING btree (yacht_id, is_active) WHERE (is_active = true)
  ```
- `idx_auth_users_profiles_email`
  ```sql
  CREATE INDEX idx_auth_users_profiles_email ON public.auth_users_profiles USING btree (email)
  ```
- `idx_auth_users_profiles_yacht_id`
  ```sql
  CREATE INDEX idx_auth_users_profiles_yacht_id ON public.auth_users_profiles USING btree (yacht_id)
  ```
- `user_profiles_email_key`
  ```sql
  CREATE UNIQUE INDEX user_profiles_email_key ON public.auth_users_profiles USING btree (email)
  ```
- `user_profiles_pkey`
  ```sql
  CREATE UNIQUE INDEX user_profiles_pkey ON public.auth_users_profiles USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Users can update own profile** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(auth.uid() = id)`
  - WITH CHECK: `(auth.uid() = id)`
- **Users can view own profile** (SELECT)
  - Roles: ['authenticated']
  - USING: `(auth.uid() = id)`

---

### `auth_users_roles`
**Row Count**: 1

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `user_id` | uuid | NO |  |  |
| `yacht_id` | uuid | NO |  |  |
| `role` | text | NO |  |  |
| `assigned_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `assigned_by` | uuid | YES |  |  |
| `is_active` | boolean | NO | true | enum: bool |
| `valid_from` | timestamp with time zone | NO | now() | enum: timestamptz |
| `valid_until` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `user_id`, `yacht_id`, `role`
- **CHECK** `2200_127936_1_not_null`: id IS NOT NULL
- **CHECK** `2200_127936_2_not_null`: user_id IS NOT NULL
- **CHECK** `2200_127936_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_127936_4_not_null`: role IS NOT NULL
- **CHECK** `2200_127936_5_not_null`: assigned_at IS NOT NULL
- **CHECK** `2200_127936_7_not_null`: is_active IS NOT NULL
- **CHECK** `2200_127936_8_not_null`: valid_from IS NOT NULL
- **CHECK** `user_roles_role_check`: (role = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'captain'::text, 'manager'::text, 'vendor'::text, 'crew'::text, 'deck'::text, 'interior'::text]))

**Indexes** (5):
- `idx_auth_users_roles_active`
  ```sql
  CREATE INDEX idx_auth_users_roles_active ON public.auth_users_roles USING btree (user_id, yacht_id, is_active) WHERE (is_active = true)
  ```
- `idx_auth_users_roles_user_id`
  ```sql
  CREATE INDEX idx_auth_users_roles_user_id ON public.auth_users_roles USING btree (user_id)
  ```
- `idx_auth_users_roles_yacht_id`
  ```sql
  CREATE INDEX idx_auth_users_roles_yacht_id ON public.auth_users_roles USING btree (yacht_id)
  ```
- `unique_active_user_yacht_role`
  ```sql
  CREATE UNIQUE INDEX unique_active_user_yacht_role ON public.auth_users_roles USING btree (user_id, yacht_id, role)
  ```
- `user_roles_pkey1`
  ```sql
  CREATE UNIQUE INDEX user_roles_pkey1 ON public.auth_users_roles USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **HODs can manage roles** (ALL)
  - Roles: ['authenticated']
  - USING: `is_hod(auth.uid(), yacht_id)`
- **Users can view own roles** (SELECT)
  - Roles: ['authenticated']
  - USING: `(auth.uid() = user_id)`

---

### `chat_agent_configs`
**Row Count**: 0

**Columns** (10):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `name` | text | NO |  |  |
| `agent_secret_hash` | text | NO |  |  |
| `device_info` | jsonb | YES | '{}'::jsonb |  |
| `last_seen_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `is_active` | boolean | YES | true | enum: bool |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_17967_10_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_17967_1_not_null`: id IS NOT NULL
- **CHECK** `2200_17967_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_17967_3_not_null`: name IS NOT NULL
- **CHECK** `2200_17967_4_not_null`: agent_secret_hash IS NOT NULL
- **CHECK** `2200_17967_9_not_null`: created_at IS NOT NULL
- **CHECK** `agents_agent_secret_hash_check`: (agent_secret_hash ~ '^\$2[aby]\$'::text)

**Indexes** (3):
- `agents_pkey`
  ```sql
  CREATE UNIQUE INDEX agents_pkey ON public.chat_agent_configs USING btree (id)
  ```
- `idx_agents_is_active`
  ```sql
  CREATE INDEX idx_agents_is_active ON public.chat_agent_configs USING btree (is_active)
  ```
- `idx_agents_yacht_id`
  ```sql
  CREATE INDEX idx_agents_yacht_id ON public.chat_agent_configs USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Managers can manage agents** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Managers can view agents** (SELECT)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Service role full access agents** (ALL)
  - Roles: ['service_role']
  - USING: `true`

---

### `chat_messages`
**Row Count**: 0

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `session_id` | uuid | YES |  |  |
| `role` | text | NO |  |  |
| `content` | text | NO |  |  |
| `timestamp` | timestamp with time zone | YES | now() | enum: timestamptz |
| `message_index` | integer | NO |  | enum: int4 |
| `sources` | jsonb | YES | '[]'::jsonb |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `tokens_used` | integer | YES |  | enum: int4 |
| `confidence_score` | double precision | YES |  | enum: float8 |
| `yacht_id` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `session_id` → `chat_sessions(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_27919_1_not_null`: id IS NOT NULL
- **CHECK** `2200_27919_3_not_null`: role IS NOT NULL
- **CHECK** `2200_27919_4_not_null`: content IS NOT NULL
- **CHECK** `2200_27919_6_not_null`: message_index IS NOT NULL
- **CHECK** `chat_messages_role_check`: (role = ANY (ARRAY['user'::text, 'assistant'::text, 'system'::text]))

**Indexes** (8):
- `chat_messages_pkey`
  ```sql
  CREATE UNIQUE INDEX chat_messages_pkey ON public.chat_messages USING btree (id)
  ```
- `idx_chat_messages_message_index`
  ```sql
  CREATE INDEX idx_chat_messages_message_index ON public.chat_messages USING btree (session_id, message_index)
  ```
- `idx_chat_messages_metadata_gin`
  ```sql
  CREATE INDEX idx_chat_messages_metadata_gin ON public.chat_messages USING gin (metadata)
  ```
- `idx_chat_messages_role`
  ```sql
  CREATE INDEX idx_chat_messages_role ON public.chat_messages USING btree (role)
  ```
- `idx_chat_messages_session_id`
  ```sql
  CREATE INDEX idx_chat_messages_session_id ON public.chat_messages USING btree (session_id)
  ```
- `idx_chat_messages_sources_gin`
  ```sql
  CREATE INDEX idx_chat_messages_sources_gin ON public.chat_messages USING gin (sources)
  ```
- `idx_chat_messages_timestamp`
  ```sql
  CREATE INDEX idx_chat_messages_timestamp ON public.chat_messages USING btree ("timestamp")
  ```
- `idx_chat_messages_yacht_id`
  ```sql
  CREATE INDEX idx_chat_messages_yacht_id ON public.chat_messages USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (8):
- **Allow backend read messages** (SELECT)
  - Roles: ['anon', 'authenticated']
  - USING: `true`
- **Service role can manage all messages** (ALL)
  - Roles: ['public']
  - USING: `((current_setting('role'::text) = 'service_role'::text) OR (current_setting('role'::text) = 'postgres'::text))`
- **anon_full_access_messages** (ALL)
  - Roles: ['anon']
  - USING: `true`
  - WITH CHECK: `true`
- **authenticated_delete_own_messages** (DELETE)
  - Roles: ['authenticated']
  - USING: `(EXISTS ( SELECT 1
   FROM chat_sessions
  WHERE ((chat_sessions.id = chat_messages.session_id) AND (chat_sessions.user_id = auth.uid()))))`
- **authenticated_insert_own_messages** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(EXISTS ( SELECT 1
   FROM chat_sessions
  WHERE ((chat_sessions.id = chat_messages.session_id) AND (chat_sessions.user_id = auth.uid()))))`
- **authenticated_select_own_messages** (SELECT)
  - Roles: ['authenticated']
  - USING: `(EXISTS ( SELECT 1
   FROM chat_sessions
  WHERE ((chat_sessions.id = chat_messages.session_id) AND (chat_sessions.user_id = auth.uid()))))`
- **authenticated_update_own_messages** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(EXISTS ( SELECT 1
   FROM chat_sessions
  WHERE ((chat_sessions.id = chat_messages.session_id) AND (chat_sessions.user_id = auth.uid()))))`
- **service_role_full_access_messages** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

**Triggers** (4):
- `trigger_update_message_count` (AFTER INSERT)
  - Action: EXECUTE FUNCTION update_session_message_count()
- `trigger_update_message_count` (AFTER DELETE)
  - Action: EXECUTE FUNCTION update_session_message_count()
- `trigger_update_session_timestamp` (AFTER INSERT)
  - Action: EXECUTE FUNCTION update_session_timestamp()
- `trigger_update_session_timestamp` (AFTER UPDATE)
  - Action: EXECUTE FUNCTION update_session_timestamp()

---

### `chat_sessions`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `user_id` | uuid | YES |  |  |
| `title` | text | NO | 'New Chat'::text |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `folder` | text | YES |  |  |
| `yacht_id` | text | YES |  |  |
| `search_type` | text | YES | 'yacht'::text |  |
| `session_metadata` | jsonb | YES | '{}'::jsonb |  |
| `is_archived` | boolean | YES | false | enum: bool |
| `message_count` | integer | YES | 0 | enum: int4 |
| `deleted` | boolean | YES | false | enum: bool |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_27898_1_not_null`: id IS NOT NULL
- **CHECK** `2200_27898_3_not_null`: title IS NOT NULL
- **CHECK** `chat_sessions_search_type_check`: (search_type = ANY (ARRAY['yacht'::text, 'email'::text, 'nas'::text]))

**Indexes** (8):
- `chat_sessions_pkey`
  ```sql
  CREATE UNIQUE INDEX chat_sessions_pkey ON public.chat_sessions USING btree (id)
  ```
- `idx_chat_sessions_created_at`
  ```sql
  CREATE INDEX idx_chat_sessions_created_at ON public.chat_sessions USING btree (created_at DESC)
  ```
- `idx_chat_sessions_deleted`
  ```sql
  CREATE INDEX idx_chat_sessions_deleted ON public.chat_sessions USING btree (deleted) WHERE (deleted = false)
  ```
- `idx_chat_sessions_folder`
  ```sql
  CREATE INDEX idx_chat_sessions_folder ON public.chat_sessions USING btree (folder)
  ```
- `idx_chat_sessions_metadata_gin`
  ```sql
  CREATE INDEX idx_chat_sessions_metadata_gin ON public.chat_sessions USING gin (session_metadata)
  ```
- `idx_chat_sessions_updated_at`
  ```sql
  CREATE INDEX idx_chat_sessions_updated_at ON public.chat_sessions USING btree (updated_at DESC)
  ```
- `idx_chat_sessions_user_id`
  ```sql
  CREATE INDEX idx_chat_sessions_user_id ON public.chat_sessions USING btree (user_id)
  ```
- `idx_chat_sessions_yacht_id`
  ```sql
  CREATE INDEX idx_chat_sessions_yacht_id ON public.chat_sessions USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (8):
- **Allow backend read sessions** (SELECT)
  - Roles: ['anon', 'authenticated']
  - USING: `true`
- **Service role can manage all chat sessions** (ALL)
  - Roles: ['public']
  - USING: `((current_setting('role'::text) = 'service_role'::text) OR (current_setting('role'::text) = 'postgres'::text))`
- **anon_full_access_sessions** (ALL)
  - Roles: ['anon']
  - USING: `true`
  - WITH CHECK: `true`
- **authenticated_delete_own_sessions** (DELETE)
  - Roles: ['authenticated']
  - USING: `(auth.uid() = user_id)`
- **authenticated_insert_own_sessions** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(auth.uid() = user_id)`
- **authenticated_select_own_sessions** (SELECT)
  - Roles: ['authenticated']
  - USING: `(auth.uid() = user_id)`
- **authenticated_update_own_sessions** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(auth.uid() = user_id)`
- **service_role_full_access_sessions** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `confirmation_templates`
**Row Count**: 12

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `action_type` | text | NO |  |  |
| `title_template` | text | NO |  |  |
| `message_template` | text | NO |  |  |
| `supports_undo` | boolean | YES | true | enum: bool |
| `undo_window_seconds` | integer | YES | 30 | enum: int4 |
| `icon` | text | YES |  |  |
| `color` | text | YES |  |  |
| `duration_ms` | integer | YES | 5000 | enum: int4 |
| `active` | boolean | YES | true | enum: bool |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `action_type`
- **CHECK** `2200_135825_11_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135825_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135825_2_not_null`: action_type IS NOT NULL
- **CHECK** `2200_135825_3_not_null`: title_template IS NOT NULL
- **CHECK** `2200_135825_4_not_null`: message_template IS NOT NULL

**Indexes** (2):
- `confirmation_templates_action_type_key`
  ```sql
  CREATE UNIQUE INDEX confirmation_templates_action_type_key ON public.confirmation_templates USING btree (action_type)
  ```
- `confirmation_templates_pkey`
  ```sql
  CREATE UNIQUE INDEX confirmation_templates_pkey ON public.confirmation_templates USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **confirmation_templates_read** (SELECT)
  - Roles: ['authenticated']
  - USING: `(active = true)`
- **confirmation_templates_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `dash_action_logs`
**Row Count**: 0

**Columns** (16):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | YES |  |  |
| `action_name` | text | NO |  |  |
| `action_status` | USER-DEFINED | NO | 'pending'::action_status | enum: action_status |
| `request_payload` | jsonb | NO | '{}'::jsonb |  |
| `response_payload` | jsonb | YES |  |  |
| `context` | jsonb | YES | '{}'::jsonb |  |
| `error_code` | text | YES |  |  |
| `error_message` | text | YES |  |  |
| `started_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `duration_ms` | integer | YES |  | enum: int4 |
| `source_ip` | text | YES |  |  |
| `user_agent` | text | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_32995_11_not_null`: started_at IS NOT NULL
- **CHECK** `2200_32995_16_not_null`: created_at IS NOT NULL
- **CHECK** `2200_32995_1_not_null`: id IS NOT NULL
- **CHECK** `2200_32995_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_32995_4_not_null`: action_name IS NOT NULL
- **CHECK** `2200_32995_5_not_null`: action_status IS NOT NULL
- **CHECK** `2200_32995_6_not_null`: request_payload IS NOT NULL

**Indexes** (6):
- `action_logs_pkey`
  ```sql
  CREATE UNIQUE INDEX action_logs_pkey ON public.dash_action_logs USING btree (id)
  ```
- `idx_action_logs_action`
  ```sql
  CREATE INDEX idx_action_logs_action ON public.dash_action_logs USING btree (action_name)
  ```
- `idx_action_logs_created`
  ```sql
  CREATE INDEX idx_action_logs_created ON public.dash_action_logs USING btree (created_at DESC)
  ```
- `idx_action_logs_status`
  ```sql
  CREATE INDEX idx_action_logs_status ON public.dash_action_logs USING btree (action_status)
  ```
- `idx_action_logs_user`
  ```sql
  CREATE INDEX idx_action_logs_user ON public.dash_action_logs USING btree (user_id)
  ```
- `idx_action_logs_yacht`
  ```sql
  CREATE INDEX idx_action_logs_yacht ON public.dash_action_logs USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED

---

### `dash_crew_hours_compliance`
**Row Count**: 0

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | NO |  |  |
| `date` | date | NO |  |  |
| `hours_worked` | numeric | NO |  |  |
| `hours_of_rest` | numeric | NO |  |  |
| `violations` | boolean | YES | false | enum: bool |
| `notes` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18218_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18218_11_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_18218_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18218_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18218_3_not_null`: user_id IS NOT NULL
- **CHECK** `2200_18218_4_not_null`: date IS NOT NULL
- **CHECK** `2200_18218_5_not_null`: hours_worked IS NOT NULL
- **CHECK** `2200_18218_6_not_null`: hours_of_rest IS NOT NULL

**Indexes** (8):
- `hours_of_rest_pkey`
  ```sql
  CREATE UNIQUE INDEX hours_of_rest_pkey ON public.dash_crew_hours_compliance USING btree (id)
  ```
- `idx_hor_date`
  ```sql
  CREATE INDEX idx_hor_date ON public.dash_crew_hours_compliance USING btree (yacht_id, date DESC)
  ```
- `idx_hor_user`
  ```sql
  CREATE INDEX idx_hor_user ON public.dash_crew_hours_compliance USING btree (user_id)
  ```
- `idx_hor_violations`
  ```sql
  CREATE INDEX idx_hor_violations ON public.dash_crew_hours_compliance USING btree (yacht_id, violations) WHERE (violations = true)
  ```
- `idx_hours_of_rest_date`
  ```sql
  CREATE INDEX idx_hours_of_rest_date ON public.dash_crew_hours_compliance USING btree (date)
  ```
- `idx_hours_of_rest_unique`
  ```sql
  CREATE UNIQUE INDEX idx_hours_of_rest_unique ON public.dash_crew_hours_compliance USING btree (yacht_id, user_id, date)
  ```
- `idx_hours_of_rest_user_id`
  ```sql
  CREATE INDEX idx_hours_of_rest_user_id ON public.dash_crew_hours_compliance USING btree (user_id)
  ```
- `idx_hours_of_rest_yacht_id`
  ```sql
  CREATE INDEX idx_hours_of_rest_yacht_id ON public.dash_crew_hours_compliance USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **Service role full access hours_of_rest** (ALL)
  - Roles: ['service_role']
  - USING: `true`

---

### `dash_handover_items`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `handover_id` | uuid | NO |  |  |
| `source_type` | USER-DEFINED | NO |  | enum: handover_source_type |
| `source_id` | uuid | NO |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `title` | text | YES |  |  |
| `description` | text | YES |  |  |
| `priority` | text | YES | 'normal'::text |  |
| `status` | text | YES | 'pending'::text |  |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18419_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18419_11_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_18419_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18419_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18419_3_not_null`: handover_id IS NOT NULL
- **CHECK** `2200_18419_4_not_null`: source_type IS NOT NULL
- **CHECK** `2200_18419_5_not_null`: source_id IS NOT NULL

**Indexes** (4):
- `handover_items_pkey`
  ```sql
  CREATE UNIQUE INDEX handover_items_pkey ON public.dash_handover_items USING btree (id)
  ```
- `idx_handover_items_handover_id`
  ```sql
  CREATE INDEX idx_handover_items_handover_id ON public.dash_handover_items USING btree (handover_id)
  ```
- `idx_handover_items_source`
  ```sql
  CREATE INDEX idx_handover_items_source ON public.dash_handover_items USING btree (source_type, source_id)
  ```
- `idx_handover_items_yacht_id`
  ```sql
  CREATE INDEX idx_handover_items_yacht_id ON public.dash_handover_items USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Engineers can manage handover items** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'captain'::text, 'manager'::text])))`
- **Service role full access handover_items** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view handover items** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `dash_handover_records`
**Row Count**: 0

**Columns** (22):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `handover_id` | uuid | NO | gen_random_uuid() |  |
| `user_id` | uuid | NO |  |  |
| `yacht_id` | text | NO |  |  |
| `solution_id` | uuid | YES |  |  |
| `document_name` | text | YES |  |  |
| `document_path` | text | YES |  |  |
| `document_page` | numeric | YES |  |  |
| `system_affected` | text | YES |  |  |
| `fault_code` | text | YES |  |  |
| `symptoms` | jsonb | YES |  |  |
| `actions_taken` | jsonb | YES |  |  |
| `duration_minutes` | integer | YES |  | enum: int4 |
| `notes` | text | YES |  |  |
| `status` | text | YES | 'draft'::text |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `document_source` | text | YES | 'manual'::text |  |
| `entities` | jsonb | YES | '[]'::jsonb |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `handover_id`
- **UNIQUE**: `user_id`, `solution_id`, `yacht_id`
- **CHECK** `2200_27976_1_not_null`: handover_id IS NOT NULL
- **CHECK** `2200_27976_2_not_null`: user_id IS NOT NULL
- **CHECK** `2200_27976_3_not_null`: yacht_id IS NOT NULL

**Indexes** (6):
- `handover_yacht_pkey`
  ```sql
  CREATE UNIQUE INDEX handover_yacht_pkey ON public.dash_handover_records USING btree (handover_id)
  ```
- `handover_yacht_user_solution_yacht_key`
  ```sql
  CREATE UNIQUE INDEX handover_yacht_user_solution_yacht_key ON public.dash_handover_records USING btree (user_id, solution_id, yacht_id)
  ```
- `idx_handover_solution`
  ```sql
  CREATE INDEX idx_handover_solution ON public.dash_handover_records USING btree (solution_id)
  ```
- `idx_handover_status`
  ```sql
  CREATE INDEX idx_handover_status ON public.dash_handover_records USING btree (status)
  ```
- `idx_handover_user_yacht`
  ```sql
  CREATE INDEX idx_handover_user_yacht ON public.dash_handover_records USING btree (user_id, yacht_id, created_at DESC)
  ```
- `idx_handover_yacht_document_source`
  ```sql
  CREATE INDEX idx_handover_yacht_document_source ON public.dash_handover_records USING btree (document_source)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **Service role full access handover_yacht** (ALL)
  - Roles: ['service_role']
  - USING: `true`

**Triggers** (1):
- `update_handover_yacht_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at_column()

---

### `dash_intelligence_snapshot`
**Row Count**: 0

**Columns** (17):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `snapshot_type` | USER-DEFINED | NO | 'briefing'::snapshot_type | enum: snapshot_type |
| `high_risk_equipment` | jsonb | NO | '[]'::jsonb |  |
| `risk_movements` | jsonb | NO | '[]'::jsonb |  |
| `unstable_systems` | jsonb | NO | '[]'::jsonb |  |
| `patterns_7d` | jsonb | NO | '[]'::jsonb |  |
| `overdue_critical` | jsonb | NO | '[]'::jsonb |  |
| `inventory_gaps` | jsonb | NO | '[]'::jsonb |  |
| `inspections_due` | jsonb | NO | '[]'::jsonb |  |
| `crew_frustration` | jsonb | NO | '[]'::jsonb |  |
| `summary_stats` | jsonb | NO | '{}'::jsonb |  |
| `generated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `generation_duration_ms` | integer | YES |  | enum: int4 |
| `data_freshness_hours` | numeric | YES |  |  |
| `valid_until` | timestamp with time zone | YES |  | enum: timestamptz |
| `is_stale` | boolean | YES | false | enum: bool |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_33158_10_not_null`: inspections_due IS NOT NULL
- **CHECK** `2200_33158_11_not_null`: crew_frustration IS NOT NULL
- **CHECK** `2200_33158_12_not_null`: summary_stats IS NOT NULL
- **CHECK** `2200_33158_13_not_null`: generated_at IS NOT NULL
- **CHECK** `2200_33158_1_not_null`: id IS NOT NULL
- **CHECK** `2200_33158_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_33158_3_not_null`: snapshot_type IS NOT NULL
- **CHECK** `2200_33158_4_not_null`: high_risk_equipment IS NOT NULL
- **CHECK** `2200_33158_5_not_null`: risk_movements IS NOT NULL
- **CHECK** `2200_33158_6_not_null`: unstable_systems IS NOT NULL
- **CHECK** `2200_33158_7_not_null`: patterns_7d IS NOT NULL
- **CHECK** `2200_33158_8_not_null`: overdue_critical IS NOT NULL
- **CHECK** `2200_33158_9_not_null`: inventory_gaps IS NOT NULL

**Indexes** (5):
- `dashboard_snapshot_pkey`
  ```sql
  CREATE UNIQUE INDEX dashboard_snapshot_pkey ON public.dash_intelligence_snapshot USING btree (id)
  ```
- `idx_dashboard_snapshot_active`
  ```sql
  CREATE INDEX idx_dashboard_snapshot_active ON public.dash_intelligence_snapshot USING btree (yacht_id, snapshot_type, generated_at DESC)
  ```
- `idx_dashboard_snapshot_generated`
  ```sql
  CREATE INDEX idx_dashboard_snapshot_generated ON public.dash_intelligence_snapshot USING btree (generated_at DESC)
  ```
- `idx_dashboard_snapshot_type`
  ```sql
  CREATE INDEX idx_dashboard_snapshot_type ON public.dash_intelligence_snapshot USING btree (snapshot_type)
  ```
- `idx_dashboard_snapshot_yacht`
  ```sql
  CREATE INDEX idx_dashboard_snapshot_yacht ON public.dash_intelligence_snapshot USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED

---

### `dash_legacy_view`
**Row Count**: 0

**Columns** (26):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_overview` | jsonb | NO | '[]'::jsonb |  |
| `equipment_count` | integer | YES | 0 | enum: int4 |
| `equipment_by_status` | jsonb | YES | '{}'::jsonb |  |
| `work_orders_overview` | jsonb | NO | '[]'::jsonb |  |
| `work_orders_count` | integer | YES | 0 | enum: int4 |
| `work_orders_by_status` | jsonb | YES | '{}'::jsonb |  |
| `work_orders_overdue_count` | integer | YES | 0 | enum: int4 |
| `inventory_overview` | jsonb | NO | '[]'::jsonb |  |
| `inventory_count` | integer | YES | 0 | enum: int4 |
| `inventory_low_stock_count` | integer | YES | 0 | enum: int4 |
| `certificates_overview` | jsonb | NO | '[]'::jsonb |  |
| `certificates_count` | integer | YES | 0 | enum: int4 |
| `certificates_expiring_soon` | integer | YES | 0 | enum: int4 |
| `fault_history` | jsonb | NO | '[]'::jsonb |  |
| `faults_active_count` | integer | YES | 0 | enum: int4 |
| `faults_resolved_30d` | integer | YES | 0 | enum: int4 |
| `scheduled_maintenance` | jsonb | NO | '[]'::jsonb |  |
| `maintenance_upcoming_7d` | integer | YES | 0 | enum: int4 |
| `maintenance_overdue` | integer | YES | 0 | enum: int4 |
| `parts_usage` | jsonb | NO | '[]'::jsonb |  |
| `documents_summary` | jsonb | NO | '{}'::jsonb |  |
| `documents_total` | integer | YES | 0 | enum: int4 |
| `generated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `valid_until` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`
- **CHECK** `2200_32955_10_not_null`: inventory_overview IS NOT NULL
- **CHECK** `2200_32955_13_not_null`: certificates_overview IS NOT NULL
- **CHECK** `2200_32955_16_not_null`: fault_history IS NOT NULL
- **CHECK** `2200_32955_19_not_null`: scheduled_maintenance IS NOT NULL
- **CHECK** `2200_32955_1_not_null`: id IS NOT NULL
- **CHECK** `2200_32955_22_not_null`: parts_usage IS NOT NULL
- **CHECK** `2200_32955_23_not_null`: documents_summary IS NOT NULL
- **CHECK** `2200_32955_25_not_null`: generated_at IS NOT NULL
- **CHECK** `2200_32955_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_32955_3_not_null`: equipment_overview IS NOT NULL
- **CHECK** `2200_32955_6_not_null`: work_orders_overview IS NOT NULL

**Indexes** (4):
- `dashboard_legacy_view_pkey`
  ```sql
  CREATE UNIQUE INDEX dashboard_legacy_view_pkey ON public.dash_legacy_view USING btree (id)
  ```
- `dashboard_legacy_view_yacht_id_key`
  ```sql
  CREATE UNIQUE INDEX dashboard_legacy_view_yacht_id_key ON public.dash_legacy_view USING btree (yacht_id)
  ```
- `idx_dashboard_legacy_generated`
  ```sql
  CREATE INDEX idx_dashboard_legacy_generated ON public.dash_legacy_view USING btree (generated_at DESC)
  ```
- `idx_dashboard_legacy_yacht`
  ```sql
  CREATE INDEX idx_dashboard_legacy_yacht ON public.dash_legacy_view USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED

---

### `dash_notifications`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | YES |  |  |
| `equipment_id` | uuid | YES |  |  |
| `type` | text | NO |  |  |
| `title` | text | NO |  |  |
| `message` | text | NO |  |  |
| `priority` | text | NO | 'normal'::text |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `is_read` | boolean | NO | false | enum: bool |
| `read_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_31701_10_not_null`: is_read IS NOT NULL
- **CHECK** `2200_31701_12_not_null`: created_at IS NOT NULL
- **CHECK** `2200_31701_1_not_null`: id IS NOT NULL
- **CHECK** `2200_31701_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_31701_5_not_null`: type IS NOT NULL
- **CHECK** `2200_31701_6_not_null`: title IS NOT NULL
- **CHECK** `2200_31701_7_not_null`: message IS NOT NULL
- **CHECK** `2200_31701_8_not_null`: priority IS NOT NULL

**Indexes** (7):
- `idx_notifications_created`
  ```sql
  CREATE INDEX idx_notifications_created ON public.dash_notifications USING btree (created_at DESC)
  ```
- `idx_notifications_type`
  ```sql
  CREATE INDEX idx_notifications_type ON public.dash_notifications USING btree (type)
  ```
- `idx_notifications_user`
  ```sql
  CREATE INDEX idx_notifications_user ON public.dash_notifications USING btree (user_id)
  ```
- `idx_notifications_user_unread`
  ```sql
  CREATE INDEX idx_notifications_user_unread ON public.dash_notifications USING btree (user_id, is_read, created_at DESC) WHERE (is_read = false)
  ```
- `idx_notifications_yacht`
  ```sql
  CREATE INDEX idx_notifications_yacht ON public.dash_notifications USING btree (yacht_id)
  ```
- `idx_notifications_yacht_created`
  ```sql
  CREATE INDEX idx_notifications_yacht_created ON public.dash_notifications USING btree (yacht_id, created_at DESC)
  ```
- `notifications_pkey`
  ```sql
  CREATE UNIQUE INDEX notifications_pkey ON public.dash_notifications USING btree (id)
  ```

**RLS**: ✅ ENABLED

---

### `dash_predictive_equipment_risk`
**Row Count**: 0

**Columns** (13):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_id` | uuid | NO |  |  |
| `risk_score` | numeric | NO | 0.0 |  |
| `risk_level` | USER-DEFINED | YES |  | enum: risk_level |
| `confidence` | numeric | NO | 0.25 |  |
| `trend` | text | YES |  |  |
| `trend_delta` | numeric | YES | 0 |  |
| `contributing_factors` | jsonb | NO | '{}'::jsonb |  |
| `last_calculated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `previous_risk_score` | numeric | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `equipment_id`
- **CHECK** `2200_33090_10_not_null`: last_calculated_at IS NOT NULL
- **CHECK** `2200_33090_12_not_null`: created_at IS NOT NULL
- **CHECK** `2200_33090_13_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_33090_1_not_null`: id IS NOT NULL
- **CHECK** `2200_33090_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_33090_3_not_null`: equipment_id IS NOT NULL
- **CHECK** `2200_33090_4_not_null`: risk_score IS NOT NULL
- **CHECK** `2200_33090_6_not_null`: confidence IS NOT NULL
- **CHECK** `2200_33090_9_not_null`: contributing_factors IS NOT NULL
- **CHECK** `predictive_state_confidence_check`: ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))
- **CHECK** `predictive_state_risk_score_check`: ((risk_score >= (0)::numeric) AND (risk_score <= (1)::numeric))
- **CHECK** `predictive_state_trend_check`: (trend = ANY (ARRAY['improving'::text, 'stable'::text, 'worsening'::text]))

**Indexes** (6):
- `idx_predictive_state_level`
  ```sql
  CREATE INDEX idx_predictive_state_level ON public.dash_predictive_equipment_risk USING btree (risk_level)
  ```
- `idx_predictive_state_risk`
  ```sql
  CREATE INDEX idx_predictive_state_risk ON public.dash_predictive_equipment_risk USING btree (risk_score DESC)
  ```
- `idx_predictive_state_updated`
  ```sql
  CREATE INDEX idx_predictive_state_updated ON public.dash_predictive_equipment_risk USING btree (updated_at DESC)
  ```
- `idx_predictive_state_yacht`
  ```sql
  CREATE INDEX idx_predictive_state_yacht ON public.dash_predictive_equipment_risk USING btree (yacht_id)
  ```
- `predictive_state_pkey`
  ```sql
  CREATE UNIQUE INDEX predictive_state_pkey ON public.dash_predictive_equipment_risk USING btree (id)
  ```
- `predictive_state_yacht_id_equipment_id_key`
  ```sql
  CREATE UNIQUE INDEX predictive_state_yacht_id_equipment_id_key ON public.dash_predictive_equipment_risk USING btree (yacht_id, equipment_id)
  ```

**RLS**: ✅ ENABLED

**Triggers** (1):
- `trigger_update_previous_risk` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_previous_risk_score()

---

### `dash_predictive_insights`
**Row Count**: 0

**Columns** (16):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_id` | uuid | YES |  |  |
| `insight_type` | USER-DEFINED | NO |  | enum: insight_type |
| `title` | text | NO |  |  |
| `description` | text | NO |  |  |
| `recommendation` | text | YES |  |  |
| `severity` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `acknowledged` | boolean | YES | false | enum: bool |
| `acknowledged_by` | uuid | YES |  |  |
| `acknowledged_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `dismissed` | boolean | YES | false | enum: bool |
| `dismissed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `expires_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_33125_16_not_null`: created_at IS NOT NULL
- **CHECK** `2200_33125_1_not_null`: id IS NOT NULL
- **CHECK** `2200_33125_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_33125_4_not_null`: insight_type IS NOT NULL
- **CHECK** `2200_33125_5_not_null`: title IS NOT NULL
- **CHECK** `2200_33125_6_not_null`: description IS NOT NULL
- **CHECK** `predictive_insights_severity_check`: (severity = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text, 'critical'::text]))

**Indexes** (6):
- `idx_predictive_insights_active`
  ```sql
  CREATE INDEX idx_predictive_insights_active ON public.dash_predictive_insights USING btree (yacht_id, dismissed, acknowledged) WHERE (dismissed = false)
  ```
- `idx_predictive_insights_equipment`
  ```sql
  CREATE INDEX idx_predictive_insights_equipment ON public.dash_predictive_insights USING btree (equipment_id)
  ```
- `idx_predictive_insights_severity`
  ```sql
  CREATE INDEX idx_predictive_insights_severity ON public.dash_predictive_insights USING btree (severity)
  ```
- `idx_predictive_insights_type`
  ```sql
  CREATE INDEX idx_predictive_insights_type ON public.dash_predictive_insights USING btree (insight_type)
  ```
- `idx_predictive_insights_yacht`
  ```sql
  CREATE INDEX idx_predictive_insights_yacht ON public.dash_predictive_insights USING btree (yacht_id)
  ```
- `predictive_insights_pkey`
  ```sql
  CREATE UNIQUE INDEX predictive_insights_pkey ON public.dash_predictive_insights USING btree (id)
  ```

**RLS**: ✅ ENABLED

---

### `dash_safety_drills`
**Row Count**: 0

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `drill_type` | text | NO |  |  |
| `drill_date` | timestamp with time zone | NO |  | enum: timestamptz |
| `conducted_by` | text | YES |  |  |
| `participants` | jsonb | YES | '[]'::jsonb |  |
| `duration_minutes` | integer | YES |  | enum: int4 |
| `outcome` | text | YES |  |  |
| `notes` | text | YES |  |  |
| `document_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_24879_11_not_null`: created_at IS NOT NULL
- **CHECK** `2200_24879_1_not_null`: id IS NOT NULL
- **CHECK** `2200_24879_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_24879_3_not_null`: drill_type IS NOT NULL
- **CHECK** `2200_24879_4_not_null`: drill_date IS NOT NULL

**Indexes** (4):
- `drill_records_pkey`
  ```sql
  CREATE UNIQUE INDEX drill_records_pkey ON public.dash_safety_drills USING btree (id)
  ```
- `idx_drill_records_date`
  ```sql
  CREATE INDEX idx_drill_records_date ON public.dash_safety_drills USING btree (yacht_id, drill_date)
  ```
- `idx_drill_records_type`
  ```sql
  CREATE INDEX idx_drill_records_type ON public.dash_safety_drills USING btree (yacht_id, drill_type)
  ```
- `idx_drill_records_yacht`
  ```sql
  CREATE INDEX idx_drill_records_yacht ON public.dash_safety_drills USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access drill_records** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view yacht drill records** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `database_architecture_notes`
**Row Count**: 5

**Columns** (4):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | integer | NO | nextval('database_architecture_notes_id_seq'::regclass) | enum: int4 |
| `note_type` | text | NO |  |  |
| `note_content` | text | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_129605_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129605_2_not_null`: note_type IS NOT NULL
- **CHECK** `2200_129605_3_not_null`: note_content IS NOT NULL
- **CHECK** `2200_129605_4_not_null`: created_at IS NOT NULL

**Indexes** (1):
- `database_architecture_notes_pkey`
  ```sql
  CREATE UNIQUE INDEX database_architecture_notes_pkey ON public.database_architecture_notes USING btree (id)
  ```

**RLS**: ❌ DISABLED

---

### `doc_metadata`
**Row Count**: 2,759

**Columns** (21):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `source` | text | NO |  |  |
| `original_path` | text | YES |  |  |
| `filename` | text | NO |  |  |
| `content_type` | text | YES |  |  |
| `size_bytes` | bigint | YES |  | enum: int8 |
| `sha256` | text | YES |  |  |
| `storage_path` | text | NO |  |  |
| `equipment_ids` | ARRAY | YES | '{}'::uuid[] | enum: _uuid |
| `tags` | ARRAY | YES | '{}'::text[] | enum: _text |
| `indexed` | boolean | YES | false | enum: bool |
| `indexed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `system_path` | text | YES |  |  |
| `doc_type` | text | YES |  |  |
| `oem` | text | YES |  |  |
| `model` | text | YES |  |  |
| `system_type` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_18444_15_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18444_16_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_18444_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18444_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18444_3_not_null`: source IS NOT NULL
- **CHECK** `2200_18444_5_not_null`: filename IS NOT NULL
- **CHECK** `2200_18444_9_not_null`: storage_path IS NOT NULL

**Indexes** (18):
- `documents_pkey`
  ```sql
  CREATE UNIQUE INDEX documents_pkey ON public.doc_metadata USING btree (id)
  ```
- `idx_documents_created`
  ```sql
  CREATE INDEX idx_documents_created ON public.doc_metadata USING btree (yacht_id, created_at DESC)
  ```
- `idx_documents_department`
  ```sql
  CREATE INDEX idx_documents_department ON public.doc_metadata USING btree ((((metadata -> 'directories'::text) -> 0)))
  ```
- `idx_documents_directories`
  ```sql
  CREATE INDEX idx_documents_directories ON public.doc_metadata USING gin (((metadata -> 'directories'::text)))
  ```
- `idx_documents_doc_type`
  ```sql
  CREATE INDEX idx_documents_doc_type ON public.doc_metadata USING btree (yacht_id, doc_type)
  ```
- `idx_documents_equipment_ids`
  ```sql
  CREATE INDEX idx_documents_equipment_ids ON public.doc_metadata USING gin (equipment_ids)
  ```
- `idx_documents_indexed`
  ```sql
  CREATE INDEX idx_documents_indexed ON public.doc_metadata USING btree (indexed)
  ```
- `idx_documents_metadata`
  ```sql
  CREATE INDEX idx_documents_metadata ON public.doc_metadata USING gin (metadata)
  ```
- `idx_documents_oem`
  ```sql
  CREATE INDEX idx_documents_oem ON public.doc_metadata USING btree (yacht_id, oem)
  ```
- `idx_documents_sha256`
  ```sql
  CREATE INDEX idx_documents_sha256 ON public.doc_metadata USING btree (sha256)
  ```
- `idx_documents_source`
  ```sql
  CREATE INDEX idx_documents_source ON public.doc_metadata USING btree (source)
  ```
- `idx_documents_system_path`
  ```sql
  CREATE INDEX idx_documents_system_path ON public.doc_metadata USING btree (system_path)
  ```
- `idx_documents_system_path_gin`
  ```sql
  CREATE INDEX idx_documents_system_path_gin ON public.doc_metadata USING gin (system_path gin_trgm_ops)
  ```
- `idx_documents_system_type`
  ```sql
  CREATE INDEX idx_documents_system_type ON public.doc_metadata USING btree (yacht_id, system_type)
  ```
- `idx_documents_tags`
  ```sql
  CREATE INDEX idx_documents_tags ON public.doc_metadata USING gin (tags)
  ```
- `idx_documents_yacht_id`
  ```sql
  CREATE INDEX idx_documents_yacht_id ON public.doc_metadata USING btree (yacht_id)
  ```
- `idx_documents_yacht_system`
  ```sql
  CREATE INDEX idx_documents_yacht_system ON public.doc_metadata USING btree (yacht_id, system_path)
  ```
- `idx_documents_yacht_system_path`
  ```sql
  CREATE INDEX idx_documents_yacht_system_path ON public.doc_metadata USING btree (yacht_id, system_path)
  ```

**RLS**: ✅ ENABLED
**Policies** (6):
- **Managers can manage documents** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = jwt_yacht_id()) AND is_manager())`
- **Service role full access documents** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **System can insert documents** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Users can view documents** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = COALESCE(jwt_yacht_id(), get_user_yacht_id()))`
- **doc_metadata_yacht_isolation** (ALL)
  - Roles: ['public']
  - USING: `((auth.uid() IS NOT NULL) AND (yacht_id = ((auth.jwt() ->> 'yacht_id'::text))::uuid))`
- **service_role_full_access** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `doc_sop_edit_history`
**Row Count**: 0

**Columns** (7):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `sop_id` | uuid | YES |  |  |
| `user_id` | uuid | YES |  |  |
| `original_content` | text | NO |  |  |
| `edited_content` | text | NO |  |  |
| `edit_count` | integer | YES | 0 | enum: int4 |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `sop_id` → `doc_sop_procedures(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_28113_1_not_null`: id IS NOT NULL
- **CHECK** `2200_28113_4_not_null`: original_content IS NOT NULL
- **CHECK** `2200_28113_5_not_null`: edited_content IS NOT NULL

**Indexes** (1):
- `sop_edits_pkey`
  ```sql
  CREATE UNIQUE INDEX sop_edits_pkey ON public.doc_sop_edit_history USING btree (id)
  ```

**RLS**: ✅ ENABLED

---

### `doc_sop_procedures`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `user_id` | uuid | YES |  |  |
| `yacht_id` | text | NO |  |  |
| `equipment` | text | YES |  |  |
| `title` | text | NO |  |  |
| `query` | text | NO |  |  |
| `content_markdown` | text | NO |  |  |
| `source_chunks` | ARRAY | YES | '{}'::integer[] | enum: _int4 |
| `version` | integer | YES | 1 | enum: int4 |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `metadata` | jsonb | YES | '{}'::jsonb |  |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_28095_1_not_null`: id IS NOT NULL
- **CHECK** `2200_28095_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_28095_5_not_null`: title IS NOT NULL
- **CHECK** `2200_28095_6_not_null`: query IS NOT NULL
- **CHECK** `2200_28095_7_not_null`: content_markdown IS NOT NULL

**Indexes** (3):
- `sop_documents_pkey`
  ```sql
  CREATE UNIQUE INDEX sop_documents_pkey ON public.doc_sop_procedures USING btree (id)
  ```
- `sop_documents_user_id_idx`
  ```sql
  CREATE INDEX sop_documents_user_id_idx ON public.doc_sop_procedures USING btree (user_id)
  ```
- `sop_documents_yacht_idx`
  ```sql
  CREATE INDEX sop_documents_yacht_idx ON public.doc_sop_procedures USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role has full access to sop_documents** (ALL)
  - Roles: ['public']
  - USING: `((auth.jwt() ->> 'role'::text) = 'service_role'::text)`
  - WITH CHECK: `((auth.jwt() ->> 'role'::text) = 'service_role'::text)`
- **Users can insert SOPs** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `(auth.uid() = user_id)`
- **Users can view their yacht's SOPs** (SELECT)
  - Roles: ['public']
  - USING: `(auth.uid() = user_id)`

---

### `doc_yacht_library`
**Row Count**: 0

**Columns** (31):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `document_name` | text | NO |  |  |
| `document_path` | text | NO |  |  |
| `document_type` | text | YES |  |  |
| `times_accessed` | integer | YES | 0 | enum: int4 |
| `times_helpful` | integer | YES | 0 | enum: int4 |
| `times_not_helpful` | integer | YES | 0 | enum: int4 |
| `equipment_covered` | jsonb | YES | '[]'::jsonb |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `last_used` | timestamp with time zone | YES |  | enum: timestamptz |
| `yacht_id` | text | YES |  |  |
| `total_uses` | integer | YES | 0 | enum: int4 |
| `successful_uses` | integer | YES | 0 | enum: int4 |
| `effectiveness_score` | numeric | YES |  |  |
| `department` | character varying | YES |  | enum: varchar |
| `fault_code_matches` | jsonb | YES | '{}'::jsonb |  |
| `user_id` | uuid | YES |  |  |
| `helpful_count` | integer | YES |  | enum: int4 |
| `chunk_id` | text | YES |  |  |
| `chunk_text` | text | YES |  |  |
| `chunk_index` | integer | YES |  | enum: int4 |
| `page_num` | integer | YES |  | enum: int4 |
| `entities_found` | jsonb | YES |  |  |
| `entity_weights` | jsonb | YES |  |  |
| `query` | text | YES |  |  |
| `session_id` | uuid | YES |  |  |
| `score` | numeric | YES |  |  |
| `chunk_metadata` | jsonb | YES |  |  |
| `is_chunk` | boolean | YES |  | enum: bool |
| `conversion_rate` | numeric | YES |  |  |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_27667_1_not_null`: id IS NOT NULL
- **CHECK** `2200_27667_2_not_null`: document_name IS NOT NULL
- **CHECK** `2200_27667_3_not_null`: document_path IS NOT NULL

**Indexes** (8):
- `document_yacht_pkey`
  ```sql
  CREATE UNIQUE INDEX document_yacht_pkey ON public.doc_yacht_library USING btree (id)
  ```
- `idx_document_yacht_chunk_id`
  ```sql
  CREATE INDEX idx_document_yacht_chunk_id ON public.doc_yacht_library USING btree (chunk_id)
  ```
- `idx_document_yacht_chunk_metadata_gin`
  ```sql
  CREATE INDEX idx_document_yacht_chunk_metadata_gin ON public.doc_yacht_library USING gin (chunk_metadata)
  ```
- `idx_document_yacht_conversion_rate`
  ```sql
  CREATE INDEX idx_document_yacht_conversion_rate ON public.doc_yacht_library USING btree (conversion_rate DESC)
  ```
- `idx_document_yacht_entities_found_gin`
  ```sql
  CREATE INDEX idx_document_yacht_entities_found_gin ON public.doc_yacht_library USING gin (entities_found)
  ```
- `idx_document_yacht_entity_weights_gin`
  ```sql
  CREATE INDEX idx_document_yacht_entity_weights_gin ON public.doc_yacht_library USING gin (entity_weights)
  ```
- `idx_document_yacht_is_chunk`
  ```sql
  CREATE INDEX idx_document_yacht_is_chunk ON public.doc_yacht_library USING btree (is_chunk)
  ```
- `idx_document_yacht_session_id`
  ```sql
  CREATE INDEX idx_document_yacht_session_id ON public.doc_yacht_library USING btree (session_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (6):
- **Allow backend read documents** (SELECT)
  - Roles: ['anon', 'authenticated']
  - USING: `true`
- **Service role can manage all documents** (ALL)
  - Roles: ['public']
  - USING: `(current_setting('role'::text) = 'service_role'::text)`
- **Service role full access document_yacht** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Service role full access documents** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can manage own documents** (ALL)
  - Roles: ['public']
  - USING: `(auth.uid() = user_id)`
- **Users can read own documents** (SELECT)
  - Roles: ['public']
  - USING: `(auth.uid() = user_id)`

**Triggers** (1):
- `update_document_yacht_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at_column()

---

### `email_attachments`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `message_id` | uuid | NO |  |  |
| `yacht_id` | uuid | NO |  |  |
| `filename` | text | NO |  |  |
| `content_type` | text | YES |  |  |
| `size_bytes` | integer | YES |  | enum: int4 |
| `storage_path` | text | YES |  |  |
| `graph_attachment_id` | text | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `message_id` → `email_messages(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_144068_1_not_null`: id IS NOT NULL
- **CHECK** `2200_144068_2_not_null`: message_id IS NOT NULL
- **CHECK** `2200_144068_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_144068_4_not_null`: filename IS NOT NULL
- **CHECK** `2200_144068_9_not_null`: created_at IS NOT NULL

**Indexes** (3):
- `email_attachments_pkey`
  ```sql
  CREATE UNIQUE INDEX email_attachments_pkey ON public.email_attachments USING btree (id)
  ```
- `idx_email_attachments_message`
  ```sql
  CREATE INDEX idx_email_attachments_message ON public.email_attachments USING btree (message_id)
  ```
- `idx_email_attachments_yacht`
  ```sql
  CREATE INDEX idx_email_attachments_yacht ON public.email_attachments USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role manages attachments** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can view yacht attachments** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

---

### `email_extraction_jobs`
**Row Count**: 0

**Columns** (19):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `query` | text | YES |  |  |
| `days_back` | integer | YES | 90 | enum: int4 |
| `max_emails` | integer | YES | 500 | enum: int4 |
| `folder_id` | text | YES |  |  |
| `status` | text | NO | 'pending'::text |  |
| `started_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `emails_fetched` | integer | YES | 0 | enum: int4 |
| `emails_classified` | integer | YES | 0 | enum: int4 |
| `entries_created` | integer | YES | 0 | enum: int4 |
| `current_stage` | text | YES |  |  |
| `stage_progress` | jsonb | YES | '{}'::jsonb |  |
| `error_message` | text | YES |  |  |
| `error_details` | jsonb | YES |  |  |
| `draft_id` | uuid | YES |  |  |
| `created_by_user_id` | uuid | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_136115_18_not_null`: created_by_user_id IS NOT NULL
- **CHECK** `2200_136115_19_not_null`: created_at IS NOT NULL
- **CHECK** `2200_136115_1_not_null`: id IS NOT NULL
- **CHECK** `2200_136115_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_136115_7_not_null`: status IS NOT NULL
- **CHECK** `valid_job_status`: (status = ANY (ARRAY['pending'::text, 'running'::text, 'completed'::text, 'failed'::text]))

**Indexes** (4):
- `email_extraction_jobs_pkey`
  ```sql
  CREATE UNIQUE INDEX email_extraction_jobs_pkey ON public.email_extraction_jobs USING btree (id)
  ```
- `idx_email_extraction_jobs_status`
  ```sql
  CREATE INDEX idx_email_extraction_jobs_status ON public.email_extraction_jobs USING btree (status)
  ```
- `idx_email_extraction_jobs_user`
  ```sql
  CREATE INDEX idx_email_extraction_jobs_user ON public.email_extraction_jobs USING btree (created_by_user_id)
  ```
- `idx_email_extraction_jobs_yacht`
  ```sql
  CREATE INDEX idx_email_extraction_jobs_yacht ON public.email_extraction_jobs USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **jobs_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `email_link_decisions`
**Row Count**: 0

**Columns** (10):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `thread_id` | uuid | NO |  |  |
| `action` | text | NO |  |  |
| `chosen_object_type` | text | YES |  |  |
| `chosen_object_id` | uuid | YES |  |  |
| `previous_suggestion` | jsonb | YES |  |  |
| `system_score` | integer | YES |  | enum: int4 |
| `created_by` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `thread_id` → `email_threads(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_140301_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_140301_1_not_null`: id IS NOT NULL
- **CHECK** `2200_140301_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_140301_3_not_null`: thread_id IS NOT NULL
- **CHECK** `2200_140301_4_not_null`: action IS NOT NULL
- **CHECK** `email_link_decisions_action_check`: (action = ANY (ARRAY['accept'::text, 'reject'::text, 'change'::text, 'unlink'::text]))

**Indexes** (4):
- `email_link_decisions_pkey`
  ```sql
  CREATE UNIQUE INDEX email_link_decisions_pkey ON public.email_link_decisions USING btree (id)
  ```
- `idx_link_decisions_action`
  ```sql
  CREATE INDEX idx_link_decisions_action ON public.email_link_decisions USING btree (yacht_id, action)
  ```
- `idx_link_decisions_thread`
  ```sql
  CREATE INDEX idx_link_decisions_thread ON public.email_link_decisions USING btree (thread_id)
  ```
- `idx_link_decisions_yacht`
  ```sql
  CREATE INDEX idx_link_decisions_yacht ON public.email_link_decisions USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role manages link_decisions** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can create link_decisions** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`
- **Users can view yacht link_decisions** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

---

### `email_links`
**Row Count**: 1

**Columns** (21):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `thread_id` | uuid | NO |  |  |
| `object_type` | text | NO |  |  |
| `object_id` | uuid | NO |  |  |
| `confidence` | text | NO | 'suggested'::text |  |
| `suggested_reason` | text | YES |  |  |
| `suggested_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `accepted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `accepted_by` | uuid | YES |  |  |
| `modified_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `modified_by` | uuid | YES |  |  |
| `is_active` | boolean | NO | true | enum: bool |
| `removed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `removed_by` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `is_primary` | boolean | YES | false | enum: bool |
| `score` | integer | YES |  | enum: int4 |
| `score_breakdown` | jsonb | YES |  |  |
| `user_blocked` | boolean | YES | false | enum: bool |

**Constraints**:
- **PK**: `id`
- **FK**: `thread_id` → `email_threads(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_138046_13_not_null`: is_active IS NOT NULL
- **CHECK** `2200_138046_16_not_null`: created_at IS NOT NULL
- **CHECK** `2200_138046_17_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_138046_1_not_null`: id IS NOT NULL
- **CHECK** `2200_138046_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_138046_3_not_null`: thread_id IS NOT NULL
- **CHECK** `2200_138046_4_not_null`: object_type IS NOT NULL
- **CHECK** `2200_138046_5_not_null`: object_id IS NOT NULL
- **CHECK** `2200_138046_6_not_null`: confidence IS NOT NULL
- **CHECK** `email_links_confidence_check`: (confidence = ANY (ARRAY['deterministic'::text, 'user_confirmed'::text, 'suggested'::text]))
- **CHECK** `email_links_object_type_check`: (object_type = ANY (ARRAY['work_order'::text, 'equipment'::text, 'part'::text, 'fault'::text, 'purchase_order'::text, 'supplier'::text]))
- **CHECK** `email_links_suggested_reason_check`: (suggested_reason = ANY (ARRAY['token_match'::text, 'vendor_domain'::text, 'wo_pattern'::text, 'po_pattern'::text, 'serial_match'::text, 'part_number'::text, 'manual'::text]))

**Indexes** (7):
- `email_links_pkey`
  ```sql
  CREATE UNIQUE INDEX email_links_pkey ON public.email_links USING btree (id)
  ```
- `idx_email_links_blocked`
  ```sql
  CREATE INDEX idx_email_links_blocked ON public.email_links USING btree (thread_id) WHERE (user_blocked = true)
  ```
- `idx_email_links_object`
  ```sql
  CREATE INDEX idx_email_links_object ON public.email_links USING btree (object_type, object_id) WHERE is_active
  ```
- `idx_email_links_pending`
  ```sql
  CREATE INDEX idx_email_links_pending ON public.email_links USING btree (yacht_id, suggested_at DESC) WHERE ((confidence = 'suggested'::text) AND is_active)
  ```
- `idx_email_links_primary`
  ```sql
  CREATE INDEX idx_email_links_primary ON public.email_links USING btree (thread_id) WHERE (is_primary = true)
  ```
- `idx_email_links_thread`
  ```sql
  CREATE INDEX idx_email_links_thread ON public.email_links USING btree (thread_id) WHERE is_active
  ```
- `idx_email_links_unique_active`
  ```sql
  CREATE UNIQUE INDEX idx_email_links_unique_active ON public.email_links USING btree (thread_id, object_type, object_id) WHERE is_active
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Service role manages links** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can create links** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`
- **Users can update links** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`
- **Users can view yacht links** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

**Triggers** (3):
- `audit_email_link_changes` (AFTER INSERT)
  - Action: EXECUTE FUNCTION audit_email_link_change()
- `audit_email_link_changes` (AFTER UPDATE)
  - Action: EXECUTE FUNCTION audit_email_link_change()
- `update_email_links_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at()

---

### `email_messages`
**Row Count**: 2

**Columns** (23):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `thread_id` | uuid | NO |  |  |
| `yacht_id` | uuid | NO |  |  |
| `provider_message_id` | text | NO |  |  |
| `internet_message_id` | text | YES |  |  |
| `direction` | text | NO |  |  |
| `from_address_hash` | text | NO |  |  |
| `from_display_name` | text | YES |  |  |
| `to_addresses_hash` | ARRAY | YES |  | enum: _text |
| `cc_addresses_hash` | ARRAY | YES |  | enum: _text |
| `subject` | text | YES |  |  |
| `sent_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `received_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `has_attachments` | boolean | NO | false | enum: bool |
| `attachments` | jsonb | YES | '[]'::jsonb |  |
| `folder` | text | YES | 'inbox'::text |  |
| `provider_etag` | text | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `subject_embedding` | USER-DEFINED | YES |  | enum: vector |
| `sender_embedding` | USER-DEFINED | YES |  | enum: vector |
| `meta_embedding` | USER-DEFINED | YES |  | enum: vector |
| `entities_extracted` | jsonb | YES |  |  |
| `entities_extracted_at` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `thread_id` → `email_threads(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `provider_message_id`
- **CHECK** `2200_138016_14_not_null`: has_attachments IS NOT NULL
- **CHECK** `2200_138016_18_not_null`: created_at IS NOT NULL
- **CHECK** `2200_138016_1_not_null`: id IS NOT NULL
- **CHECK** `2200_138016_2_not_null`: thread_id IS NOT NULL
- **CHECK** `2200_138016_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_138016_4_not_null`: provider_message_id IS NOT NULL
- **CHECK** `2200_138016_6_not_null`: direction IS NOT NULL
- **CHECK** `2200_138016_7_not_null`: from_address_hash IS NOT NULL
- **CHECK** `email_messages_direction_check`: (direction = ANY (ARRAY['inbound'::text, 'outbound'::text]))
- **CHECK** `email_messages_folder_check`: (folder = ANY (ARRAY['inbox'::text, 'sent'::text, 'drafts'::text, 'other'::text]))

**Indexes** (6):
- `email_messages_pkey`
  ```sql
  CREATE UNIQUE INDEX email_messages_pkey ON public.email_messages USING btree (id)
  ```
- `email_messages_yacht_provider_key`
  ```sql
  CREATE UNIQUE INDEX email_messages_yacht_provider_key ON public.email_messages USING btree (yacht_id, provider_message_id)
  ```
- `idx_email_messages_direction`
  ```sql
  CREATE INDEX idx_email_messages_direction ON public.email_messages USING btree (yacht_id, direction, sent_at DESC)
  ```
- `idx_email_messages_meta_embedding`
  ```sql
  CREATE INDEX idx_email_messages_meta_embedding ON public.email_messages USING hnsw (meta_embedding vector_cosine_ops) WITH (m='16', ef_construction='64')
  ```
- `idx_email_messages_subject_embedding`
  ```sql
  CREATE INDEX idx_email_messages_subject_embedding ON public.email_messages USING hnsw (subject_embedding vector_cosine_ops) WITH (m='16', ef_construction='64')
  ```
- `idx_email_messages_thread`
  ```sql
  CREATE INDEX idx_email_messages_thread ON public.email_messages USING btree (thread_id, sent_at DESC)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role manages messages** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can view yacht messages** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

---

### `email_threads`
**Row Count**: 1

**Columns** (17):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `provider_conversation_id` | text | NO |  |  |
| `latest_subject` | text | YES |  |  |
| `message_count` | integer | NO | 0 | enum: int4 |
| `has_attachments` | boolean | NO | false | enum: bool |
| `participant_hashes` | ARRAY | YES |  | enum: _text |
| `source` | text | NO | 'external'::text |  |
| `first_message_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `last_activity_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `last_inbound_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `last_outbound_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `extracted_tokens` | jsonb | YES | '{}'::jsonb |  |
| `suggestions_generated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `thread_embedding` | USER-DEFINED | YES |  | enum: vector |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `provider_conversation_id`
- **CHECK** `2200_137990_13_not_null`: created_at IS NOT NULL
- **CHECK** `2200_137990_14_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_137990_1_not_null`: id IS NOT NULL
- **CHECK** `2200_137990_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_137990_3_not_null`: provider_conversation_id IS NOT NULL
- **CHECK** `2200_137990_5_not_null`: message_count IS NOT NULL
- **CHECK** `2200_137990_6_not_null`: has_attachments IS NOT NULL
- **CHECK** `2200_137990_8_not_null`: source IS NOT NULL
- **CHECK** `email_threads_source_check`: (source = ANY (ARRAY['celeste_originated'::text, 'external'::text, 'mixed'::text]))

**Indexes** (7):
- `email_threads_pkey`
  ```sql
  CREATE UNIQUE INDEX email_threads_pkey ON public.email_threads USING btree (id)
  ```
- `email_threads_yacht_conversation_key`
  ```sql
  CREATE UNIQUE INDEX email_threads_yacht_conversation_key ON public.email_threads USING btree (yacht_id, provider_conversation_id)
  ```
- `idx_email_threads_needs_suggestions`
  ```sql
  CREATE INDEX idx_email_threads_needs_suggestions ON public.email_threads USING btree (yacht_id, last_activity_at) WHERE (suggestions_generated_at IS NULL)
  ```
- `idx_email_threads_pending_suggestions`
  ```sql
  CREATE INDEX idx_email_threads_pending_suggestions ON public.email_threads USING btree (yacht_id, last_activity_at DESC) WHERE (suggestions_generated_at IS NULL)
  ```
- `idx_email_threads_source`
  ```sql
  CREATE INDEX idx_email_threads_source ON public.email_threads USING btree (yacht_id, source)
  ```
- `idx_email_threads_thread_embedding`
  ```sql
  CREATE INDEX idx_email_threads_thread_embedding ON public.email_threads USING hnsw (thread_embedding vector_cosine_ops) WITH (m='16', ef_construction='64')
  ```
- `idx_email_threads_yacht_activity`
  ```sql
  CREATE INDEX idx_email_threads_yacht_activity ON public.email_threads USING btree (yacht_id, last_activity_at DESC)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role manages threads** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can view yacht threads** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

**Triggers** (1):
- `update_email_threads_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at()

---

### `email_watchers`
**Row Count**: 1

**Columns** (21):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `user_id` | uuid | NO |  |  |
| `yacht_id` | uuid | NO |  |  |
| `provider` | text | NO | 'microsoft_graph'::text |  |
| `mailbox_address_hash` | text | YES |  |  |
| `delta_link_inbox` | text | YES |  |  |
| `delta_link_sent` | text | YES |  |  |
| `subscription_id` | text | YES |  |  |
| `subscription_expires_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `last_sync_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `last_sync_error` | text | YES |  |  |
| `sync_status` | text | NO | 'pending'::text |  |
| `backfill_days_inbox` | integer | YES | 14 | enum: int4 |
| `backfill_days_sent` | integer | YES | 14 | enum: int4 |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `api_calls_this_hour` | integer | YES | 0 | enum: int4 |
| `hour_window_start` | timestamp with time zone | YES |  | enum: timestamptz |
| `sync_interval_minutes` | integer | YES | 15 | enum: int4 |
| `is_paused` | boolean | YES | false | enum: bool |
| `pause_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `user_id`, `yacht_id`, `provider`
- **CHECK** `2200_137954_12_not_null`: sync_status IS NOT NULL
- **CHECK** `2200_137954_15_not_null`: created_at IS NOT NULL
- **CHECK** `2200_137954_16_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_137954_1_not_null`: id IS NOT NULL
- **CHECK** `2200_137954_2_not_null`: user_id IS NOT NULL
- **CHECK** `2200_137954_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_137954_4_not_null`: provider IS NOT NULL
- **CHECK** `email_watchers_sync_status_check`: (sync_status = ANY (ARRAY['pending'::text, 'active'::text, 'read_only'::text, 'write_only'::text, 'degraded'::text, 'disconnected'::text]))

**Indexes** (6):
- `email_watchers_pkey`
  ```sql
  CREATE UNIQUE INDEX email_watchers_pkey ON public.email_watchers USING btree (id)
  ```
- `email_watchers_user_yacht_provider_key`
  ```sql
  CREATE UNIQUE INDEX email_watchers_user_yacht_provider_key ON public.email_watchers USING btree (user_id, yacht_id, provider)
  ```
- `idx_email_watchers_status`
  ```sql
  CREATE INDEX idx_email_watchers_status ON public.email_watchers USING btree (yacht_id, sync_status)
  ```
- `idx_email_watchers_subscription`
  ```sql
  CREATE INDEX idx_email_watchers_subscription ON public.email_watchers USING btree (subscription_expires_at) WHERE (sync_status = ANY (ARRAY['active'::text, 'degraded'::text]))
  ```
- `idx_email_watchers_user`
  ```sql
  CREATE INDEX idx_email_watchers_user ON public.email_watchers USING btree (user_id)
  ```
- `idx_email_watchers_yacht`
  ```sql
  CREATE INDEX idx_email_watchers_yacht ON public.email_watchers USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Service role full access watchers** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can insert own watcher** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(user_id = auth.uid())`
- **Users can update own watcher** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(user_id = auth.uid())`
  - WITH CHECK: `(user_id = auth.uid())`
- **Users can view own watcher** (SELECT)
  - Roles: ['authenticated']
  - USING: `(user_id = auth.uid())`

**Triggers** (1):
- `update_email_watchers_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at()

---

### `entity_definitions`
**Row Count**: 0

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | YES |  |  |
| `entity_type` | text | NO |  |  |
| `canonical_name` | text | NO |  |  |
| `aliases` | ARRAY | YES | '{}'::text[] | enum: _text |
| `category` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `extraction_patterns` | ARRAY | YES |  | enum: _text |
| `priority` | integer | YES | 100 | enum: int4 |
| `active` | boolean | YES | true | enum: bool |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `yacht_id`, `entity_type`, `canonical_name`
- **CHECK** `2200_135778_11_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135778_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135778_3_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_135778_4_not_null`: canonical_name IS NOT NULL

**Indexes** (5):
- `entity_definitions_pkey`
  ```sql
  CREATE UNIQUE INDEX entity_definitions_pkey ON public.entity_definitions USING btree (id)
  ```
- `entity_definitions_yacht_id_entity_type_canonical_name_key`
  ```sql
  CREATE UNIQUE INDEX entity_definitions_yacht_id_entity_type_canonical_name_key ON public.entity_definitions USING btree (yacht_id, entity_type, canonical_name)
  ```
- `idx_entity_definitions_aliases`
  ```sql
  CREATE INDEX idx_entity_definitions_aliases ON public.entity_definitions USING gin (aliases)
  ```
- `idx_entity_definitions_type`
  ```sql
  CREATE INDEX idx_entity_definitions_type ON public.entity_definitions USING btree (entity_type)
  ```
- `idx_entity_definitions_yacht`
  ```sql
  CREATE INDEX idx_entity_definitions_yacht ON public.entity_definitions USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **entity_definitions_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `entity_staging`
**Row Count**: 904

**Columns** (15):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `entity_type` | text | NO |  |  |
| `entity_value` | text | NO |  |  |
| `canonical_label` | text | NO |  |  |
| `confidence` | double precision | YES | 0.9 | enum: float8 |
| `source_chunk_id` | text | YES |  |  |
| `source_document_id` | text | YES |  |  |
| `source_storage_path` | text | YES |  |  |
| `attributes` | jsonb | YES | '{}'::jsonb |  |
| `status` | text | YES | 'pending'::text |  |
| `error_message` | text | YES |  |  |
| `processed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `graph_node_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_45115_1_not_null`: id IS NOT NULL
- **CHECK** `2200_45115_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_45115_3_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_45115_4_not_null`: entity_value IS NOT NULL
- **CHECK** `2200_45115_5_not_null`: canonical_label IS NOT NULL
- **CHECK** `entity_staging_status_check`: (status = ANY (ARRAY['pending'::text, 'processing'::text, 'completed'::text, 'failed'::text]))

**Indexes** (3):
- `entity_staging_pkey`
  ```sql
  CREATE UNIQUE INDEX entity_staging_pkey ON public.entity_staging USING btree (id)
  ```
- `idx_entity_staging_status`
  ```sql
  CREATE INDEX idx_entity_staging_status ON public.entity_staging USING btree (status) WHERE (status = 'pending'::text)
  ```
- `idx_entity_staging_yacht`
  ```sql
  CREATE INDEX idx_entity_staging_yacht ON public.entity_staging USING btree (yacht_id)
  ```

**RLS**: ❌ DISABLED

---

### `handover_draft_edits`
**Row Count**: 0

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `draft_id` | uuid | NO |  |  |
| `draft_item_id` | uuid | YES |  |  |
| `edited_by_user_id` | uuid | NO |  |  |
| `edited_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `field_edited` | text | NO | 'summary_text'::text |  |
| `original_text` | text | YES |  |  |
| `edited_text` | text | NO |  |  |
| `edit_reason` | text | YES |  |  |
| `edit_type` | text | YES | 'modification'::text |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `draft_id` → `handover_drafts(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `draft_item_id` → `handover_draft_items(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **CHECK** `2200_136030_11_not_null`: created_at IS NOT NULL
- **CHECK** `2200_136030_1_not_null`: id IS NOT NULL
- **CHECK** `2200_136030_2_not_null`: draft_id IS NOT NULL
- **CHECK** `2200_136030_4_not_null`: edited_by_user_id IS NOT NULL
- **CHECK** `2200_136030_5_not_null`: edited_at IS NOT NULL
- **CHECK** `2200_136030_6_not_null`: field_edited IS NOT NULL
- **CHECK** `2200_136030_8_not_null`: edited_text IS NOT NULL

**Indexes** (4):
- `handover_draft_edits_pkey`
  ```sql
  CREATE UNIQUE INDEX handover_draft_edits_pkey ON public.handover_draft_edits USING btree (id)
  ```
- `idx_handover_draft_edits_draft`
  ```sql
  CREATE INDEX idx_handover_draft_edits_draft ON public.handover_draft_edits USING btree (draft_id)
  ```
- `idx_handover_draft_edits_item`
  ```sql
  CREATE INDEX idx_handover_draft_edits_item ON public.handover_draft_edits USING btree (draft_item_id)
  ```
- `idx_handover_draft_edits_user`
  ```sql
  CREATE INDEX idx_handover_draft_edits_user ON public.handover_draft_edits USING btree (edited_by_user_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **draft_edits_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `handover_draft_items`
**Row Count**: 0

**Columns** (18):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `draft_id` | uuid | NO |  |  |
| `section_id` | uuid | YES |  |  |
| `section_bucket` | text | NO |  |  |
| `domain_code` | text | YES |  |  |
| `summary_text` | text | NO |  |  |
| `source_entry_ids` | ARRAY | YES |  | enum: _uuid |
| `source_event_ids` | ARRAY | YES |  | enum: _uuid |
| `risk_tags` | ARRAY | YES |  | enum: _text |
| `confidence_level` | text | YES | 'HIGH'::text |  |
| `item_order` | integer | NO |  | enum: int4 |
| `conflict_flag` | boolean | YES | false | enum: bool |
| `uncertainty_flag` | boolean | YES | false | enum: bool |
| `is_critical` | boolean | YES | false | enum: bool |
| `requires_action` | boolean | YES | false | enum: bool |
| `action_summary` | text | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `draft_id` → `handover_drafts(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `section_id` → `handover_draft_sections(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **CHECK** `2200_135999_11_not_null`: item_order IS NOT NULL
- **CHECK** `2200_135999_17_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135999_18_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_135999_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135999_2_not_null`: draft_id IS NOT NULL
- **CHECK** `2200_135999_4_not_null`: section_bucket IS NOT NULL
- **CHECK** `2200_135999_6_not_null`: summary_text IS NOT NULL
- **CHECK** `valid_confidence`: (confidence_level = ANY (ARRAY['LOW'::text, 'MEDIUM'::text, 'HIGH'::text]))

**Indexes** (5):
- `handover_draft_items_pkey`
  ```sql
  CREATE UNIQUE INDEX handover_draft_items_pkey ON public.handover_draft_items USING btree (id)
  ```
- `idx_handover_draft_items_bucket`
  ```sql
  CREATE INDEX idx_handover_draft_items_bucket ON public.handover_draft_items USING btree (section_bucket)
  ```
- `idx_handover_draft_items_critical`
  ```sql
  CREATE INDEX idx_handover_draft_items_critical ON public.handover_draft_items USING btree (is_critical) WHERE (is_critical = true)
  ```
- `idx_handover_draft_items_draft`
  ```sql
  CREATE INDEX idx_handover_draft_items_draft ON public.handover_draft_items USING btree (draft_id)
  ```
- `idx_handover_draft_items_section`
  ```sql
  CREATE INDEX idx_handover_draft_items_section ON public.handover_draft_items USING btree (section_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **draft_items_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `handover_draft_sections`
**Row Count**: 0

**Columns** (8):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `draft_id` | uuid | NO |  |  |
| `bucket_name` | text | NO |  |  |
| `section_order` | integer | NO |  | enum: int4 |
| `display_title` | text | YES |  |  |
| `item_count` | integer | YES | 0 | enum: int4 |
| `critical_count` | integer | YES | 0 | enum: int4 |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `draft_id` → `handover_drafts(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `draft_id`, `bucket_name`
- **CHECK** `2200_135979_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135979_2_not_null`: draft_id IS NOT NULL
- **CHECK** `2200_135979_3_not_null`: bucket_name IS NOT NULL
- **CHECK** `2200_135979_4_not_null`: section_order IS NOT NULL
- **CHECK** `2200_135979_8_not_null`: created_at IS NOT NULL

**Indexes** (3):
- `handover_draft_sections_draft_id_bucket_name_key`
  ```sql
  CREATE UNIQUE INDEX handover_draft_sections_draft_id_bucket_name_key ON public.handover_draft_sections USING btree (draft_id, bucket_name)
  ```
- `handover_draft_sections_pkey`
  ```sql
  CREATE UNIQUE INDEX handover_draft_sections_pkey ON public.handover_draft_sections USING btree (id)
  ```
- `idx_handover_draft_sections_draft`
  ```sql
  CREATE INDEX idx_handover_draft_sections_draft ON public.handover_draft_sections USING btree (draft_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **draft_sections_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `handover_drafts`
**Row Count**: 0

**Columns** (17):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `period_start` | timestamp with time zone | NO |  | enum: timestamptz |
| `period_end` | timestamp with time zone | NO |  | enum: timestamptz |
| `title` | text | YES |  |  |
| `department` | text | YES |  |  |
| `generated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `generated_by_user_id` | uuid | YES |  |  |
| `generated_by_version` | text | YES | '1.0'::text |  |
| `generation_method` | text | YES | 'manual'::text |  |
| `state` | text | NO | 'DRAFT'::text |  |
| `last_modified_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `last_modified_by` | uuid | YES |  |  |
| `total_entries` | integer | YES | 0 | enum: int4 |
| `critical_entries` | integer | YES | 0 | enum: int4 |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_135957_11_not_null`: state IS NOT NULL
- **CHECK** `2200_135957_12_not_null`: last_modified_at IS NOT NULL
- **CHECK** `2200_135957_17_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135957_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135957_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_135957_3_not_null`: period_start IS NOT NULL
- **CHECK** `2200_135957_4_not_null`: period_end IS NOT NULL
- **CHECK** `2200_135957_7_not_null`: generated_at IS NOT NULL
- **CHECK** `valid_state`: (state = ANY (ARRAY['DRAFT'::text, 'IN_REVIEW'::text, 'ACCEPTED'::text, 'SIGNED'::text, 'EXPORTED'::text]))

**Indexes** (5):
- `handover_drafts_pkey`
  ```sql
  CREATE UNIQUE INDEX handover_drafts_pkey ON public.handover_drafts USING btree (id)
  ```
- `idx_handover_drafts_department`
  ```sql
  CREATE INDEX idx_handover_drafts_department ON public.handover_drafts USING btree (department)
  ```
- `idx_handover_drafts_period`
  ```sql
  CREATE INDEX idx_handover_drafts_period ON public.handover_drafts USING btree (period_start, period_end)
  ```
- `idx_handover_drafts_state`
  ```sql
  CREATE INDEX idx_handover_drafts_state ON public.handover_drafts USING btree (state)
  ```
- `idx_handover_drafts_yacht`
  ```sql
  CREATE INDEX idx_handover_drafts_yacht ON public.handover_drafts USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **handover_drafts_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `handover_entries`
**Row Count**: 0

**Columns** (23):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `created_by_user_id` | uuid | NO |  |  |
| `created_by_role` | text | YES |  |  |
| `created_by_department` | text | YES |  |  |
| `primary_domain` | text | NO |  |  |
| `secondary_domains` | ARRAY | YES |  | enum: _text |
| `presentation_bucket` | text | NO |  |  |
| `suggested_owner_roles` | ARRAY | YES |  | enum: _text |
| `risk_tags` | ARRAY | YES |  | enum: _text |
| `narrative_text` | text | NO |  |  |
| `summary_text` | text | YES |  |  |
| `source_event_ids` | ARRAY | YES |  | enum: _uuid |
| `source_document_ids` | ARRAY | YES |  | enum: _uuid |
| `source_entity_type` | text | YES |  |  |
| `source_entity_id` | uuid | YES |  |  |
| `status` | text | NO | 'candidate'::text |  |
| `classification_flagged` | boolean | YES | false | enum: bool |
| `is_critical` | boolean | YES | false | enum: bool |
| `requires_acknowledgment` | boolean | YES | false | enum: bool |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `resolved_at` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_135933_11_not_null`: narrative_text IS NOT NULL
- **CHECK** `2200_135933_17_not_null`: status IS NOT NULL
- **CHECK** `2200_135933_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135933_21_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135933_22_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_135933_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_135933_3_not_null`: created_by_user_id IS NOT NULL
- **CHECK** `2200_135933_6_not_null`: primary_domain IS NOT NULL
- **CHECK** `2200_135933_8_not_null`: presentation_bucket IS NOT NULL
- **CHECK** `valid_bucket`: (presentation_bucket = ANY (ARRAY['Command'::text, 'Engineering'::text, 'ETO_AVIT'::text, 'Deck'::text, 'Interior'::text, 'Galley'::text, 'Security'::text, 'Admin_Compliance'::text]))
- **CHECK** `valid_status`: (status = ANY (ARRAY['candidate'::text, 'included'::text, 'suppressed'::text, 'resolved'::text]))

**Indexes** (9):
- `handover_entries_pkey`
  ```sql
  CREATE UNIQUE INDEX handover_entries_pkey ON public.handover_entries USING btree (id)
  ```
- `idx_handover_entries_bucket`
  ```sql
  CREATE INDEX idx_handover_entries_bucket ON public.handover_entries USING btree (presentation_bucket)
  ```
- `idx_handover_entries_created`
  ```sql
  CREATE INDEX idx_handover_entries_created ON public.handover_entries USING btree (created_at DESC)
  ```
- `idx_handover_entries_critical`
  ```sql
  CREATE INDEX idx_handover_entries_critical ON public.handover_entries USING btree (is_critical) WHERE (is_critical = true)
  ```
- `idx_handover_entries_domain`
  ```sql
  CREATE INDEX idx_handover_entries_domain ON public.handover_entries USING btree (primary_domain)
  ```
- `idx_handover_entries_source`
  ```sql
  CREATE INDEX idx_handover_entries_source ON public.handover_entries USING btree (source_entity_type, source_entity_id)
  ```
- `idx_handover_entries_status`
  ```sql
  CREATE INDEX idx_handover_entries_status ON public.handover_entries USING btree (status)
  ```
- `idx_handover_entries_user`
  ```sql
  CREATE INDEX idx_handover_entries_user ON public.handover_entries USING btree (created_by_user_id)
  ```
- `idx_handover_entries_yacht`
  ```sql
  CREATE INDEX idx_handover_entries_yacht ON public.handover_entries USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **handover_entries_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `handover_exports`
**Row Count**: 0

**Columns** (17):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `draft_id` | uuid | NO |  |  |
| `yacht_id` | uuid | NO |  |  |
| `export_type` | text | NO |  |  |
| `storage_path` | text | YES |  |  |
| `storage_bucket` | text | YES | 'handover-exports'::text |  |
| `file_name` | text | YES |  |  |
| `file_size_bytes` | integer | YES |  | enum: int4 |
| `exported_by_user_id` | uuid | NO |  |  |
| `exported_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `recipients` | ARRAY | YES |  | enum: _text |
| `email_subject` | text | YES |  |  |
| `email_sent_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `document_hash` | text | YES |  |  |
| `export_status` | text | YES | 'completed'::text |  |
| `error_message` | text | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `draft_id` → `handover_drafts(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_136078_10_not_null`: exported_at IS NOT NULL
- **CHECK** `2200_136078_17_not_null`: created_at IS NOT NULL
- **CHECK** `2200_136078_1_not_null`: id IS NOT NULL
- **CHECK** `2200_136078_2_not_null`: draft_id IS NOT NULL
- **CHECK** `2200_136078_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_136078_4_not_null`: export_type IS NOT NULL
- **CHECK** `2200_136078_9_not_null`: exported_by_user_id IS NOT NULL
- **CHECK** `valid_export_type`: (export_type = ANY (ARRAY['pdf'::text, 'html'::text, 'email'::text]))

**Indexes** (5):
- `handover_exports_pkey`
  ```sql
  CREATE UNIQUE INDEX handover_exports_pkey ON public.handover_exports USING btree (id)
  ```
- `idx_handover_exports_draft`
  ```sql
  CREATE INDEX idx_handover_exports_draft ON public.handover_exports USING btree (draft_id)
  ```
- `idx_handover_exports_type`
  ```sql
  CREATE INDEX idx_handover_exports_type ON public.handover_exports USING btree (export_type)
  ```
- `idx_handover_exports_user`
  ```sql
  CREATE INDEX idx_handover_exports_user ON public.handover_exports USING btree (exported_by_user_id)
  ```
- `idx_handover_exports_yacht`
  ```sql
  CREATE INDEX idx_handover_exports_yacht ON public.handover_exports USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **exports_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `handover_items`
**Row Count**: 13

**Columns** (20):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `handover_id` | uuid | NO |  |  |
| `entity_id` | uuid | NO |  |  |
| `entity_type` | character varying | NO |  | enum: varchar |
| `section` | character varying | YES |  | enum: varchar |
| `summary` | text | YES |  |  |
| `priority` | integer | YES | 0 | enum: int4 |
| `status` | character varying | NO | 'pending'::character varying | enum: varchar |
| `acknowledged_by` | uuid | YES |  |  |
| `acknowledged_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `acknowledgement_notes` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `added_by` | uuid | NO |  |  |
| `updated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `handover_id` → `handovers(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_138906_14_not_null`: created_at IS NOT NULL
- **CHECK** `2200_138906_15_not_null`: added_by IS NOT NULL
- **CHECK** `2200_138906_1_not_null`: id IS NOT NULL
- **CHECK** `2200_138906_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_138906_3_not_null`: handover_id IS NOT NULL
- **CHECK** `2200_138906_4_not_null`: entity_id IS NOT NULL
- **CHECK** `2200_138906_5_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_138906_9_not_null`: status IS NOT NULL
- **CHECK** `chk_handover_items_entity_type`: ((entity_type)::text = ANY ((ARRAY['fault'::character varying, 'work_order'::character varying, 'equipment'::character varying, 'part'::character varying, 'document'::character varying, 'note'::character varying, 'general'::character varying])::text[]))
- **CHECK** `chk_handover_items_status`: ((status)::text = ANY ((ARRAY['pending'::character varying, 'acknowledged'::character varying, 'completed'::character varying, 'deferred'::character varying])::text[]))

**Indexes** (2):
- `handover_items_pkey1`
  ```sql
  CREATE UNIQUE INDEX handover_items_pkey1 ON public.handover_items USING btree (id)
  ```
- `idx_handover_items_entity`
  ```sql
  CREATE INDEX idx_handover_items_entity ON public.handover_items USING btree (entity_type, entity_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (9):
- **service_role_bypass** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **users_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **users_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_view** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **yacht_isolation_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_select** (SELECT)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`

---

### `handover_signoffs`
**Row Count**: 0

**Columns** (16):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `draft_id` | uuid | NO |  |  |
| `yacht_id` | uuid | NO |  |  |
| `outgoing_user_id` | uuid | NO |  |  |
| `outgoing_role` | text | YES |  |  |
| `outgoing_signed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `outgoing_notes` | text | YES |  |  |
| `incoming_user_id` | uuid | YES |  |  |
| `incoming_role` | text | YES |  |  |
| `incoming_signed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `incoming_notes` | text | YES |  |  |
| `incoming_acknowledged_critical` | boolean | YES | false | enum: bool |
| `document_hash` | text | YES |  |  |
| `signoff_complete` | boolean | YES | false | enum: bool |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `draft_id` → `handover_drafts(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `draft_id`
- **CHECK** `2200_136055_15_not_null`: created_at IS NOT NULL
- **CHECK** `2200_136055_16_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_136055_1_not_null`: id IS NOT NULL
- **CHECK** `2200_136055_2_not_null`: draft_id IS NOT NULL
- **CHECK** `2200_136055_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_136055_4_not_null`: outgoing_user_id IS NOT NULL

**Indexes** (6):
- `handover_signoffs_draft_id_key`
  ```sql
  CREATE UNIQUE INDEX handover_signoffs_draft_id_key ON public.handover_signoffs USING btree (draft_id)
  ```
- `handover_signoffs_pkey`
  ```sql
  CREATE UNIQUE INDEX handover_signoffs_pkey ON public.handover_signoffs USING btree (id)
  ```
- `idx_handover_signoffs_draft`
  ```sql
  CREATE INDEX idx_handover_signoffs_draft ON public.handover_signoffs USING btree (draft_id)
  ```
- `idx_handover_signoffs_incoming`
  ```sql
  CREATE INDEX idx_handover_signoffs_incoming ON public.handover_signoffs USING btree (incoming_user_id)
  ```
- `idx_handover_signoffs_outgoing`
  ```sql
  CREATE INDEX idx_handover_signoffs_outgoing ON public.handover_signoffs USING btree (outgoing_user_id)
  ```
- `idx_handover_signoffs_yacht`
  ```sql
  CREATE INDEX idx_handover_signoffs_yacht ON public.handover_signoffs USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **signoffs_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `handover_sources`
**Row Count**: 0

**Columns** (16):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `source_type` | text | NO |  |  |
| `external_id` | text | YES |  |  |
| `storage_path` | text | YES |  |  |
| `storage_bucket` | text | YES |  |  |
| `subject` | text | YES |  |  |
| `body_preview` | text | YES |  |  |
| `sender_name` | text | YES |  |  |
| `sender_email` | text | YES |  |  |
| `received_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `is_processed` | boolean | YES | false | enum: bool |
| `processed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `processing_error` | text | YES |  |  |
| `classification` | jsonb | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_136100_16_not_null`: created_at IS NOT NULL
- **CHECK** `2200_136100_1_not_null`: id IS NOT NULL
- **CHECK** `2200_136100_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_136100_3_not_null`: source_type IS NOT NULL
- **CHECK** `valid_source_type`: (source_type = ANY (ARRAY['email'::text, 'document'::text, 'work_order'::text, 'fault'::text, 'message'::text, 'api'::text]))

**Indexes** (5):
- `handover_sources_pkey`
  ```sql
  CREATE UNIQUE INDEX handover_sources_pkey ON public.handover_sources USING btree (id)
  ```
- `idx_handover_sources_external`
  ```sql
  CREATE INDEX idx_handover_sources_external ON public.handover_sources USING btree (external_id)
  ```
- `idx_handover_sources_processed`
  ```sql
  CREATE INDEX idx_handover_sources_processed ON public.handover_sources USING btree (is_processed)
  ```
- `idx_handover_sources_type`
  ```sql
  CREATE INDEX idx_handover_sources_type ON public.handover_sources USING btree (source_type)
  ```
- `idx_handover_sources_yacht`
  ```sql
  CREATE INDEX idx_handover_sources_yacht ON public.handover_sources USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **sources_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `handovers`
**Row Count**: 3

**Columns** (22):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `title` | character varying | YES |  | enum: varchar |
| `description` | text | YES |  |  |
| `status` | character varying | NO | 'draft'::character varying | enum: varchar |
| `from_user_id` | uuid | YES |  |  |
| `to_user_id` | uuid | YES |  |  |
| `shift_date` | date | YES |  |  |
| `shift_type` | character varying | YES |  | enum: varchar |
| `started_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `approved_by` | uuid | YES |  |  |
| `approved_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `approval_notes` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_by` | uuid | NO |  |  |
| `updated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_138886_16_not_null`: created_at IS NOT NULL
- **CHECK** `2200_138886_17_not_null`: created_by IS NOT NULL
- **CHECK** `2200_138886_1_not_null`: id IS NOT NULL
- **CHECK** `2200_138886_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_138886_5_not_null`: status IS NOT NULL
- **CHECK** `chk_handovers_status`: ((status)::text = ANY ((ARRAY['draft'::character varying, 'pending_review'::character varying, 'approved'::character varying, 'completed'::character varying, 'cancelled'::character varying])::text[]))

**Indexes** (4):
- `handovers_pkey`
  ```sql
  CREATE UNIQUE INDEX handovers_pkey ON public.handovers USING btree (id)
  ```
- `idx_handovers_created_at`
  ```sql
  CREATE INDEX idx_handovers_created_at ON public.handovers USING btree (created_at DESC)
  ```
- `idx_handovers_status`
  ```sql
  CREATE INDEX idx_handovers_status ON public.handovers USING btree (status) WHERE (deleted_at IS NULL)
  ```
- `idx_handovers_yacht_id`
  ```sql
  CREATE INDEX idx_handovers_yacht_id ON public.handovers USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (9):
- **service_role_bypass** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **users_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **users_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_view** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **yacht_isolation_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_select** (SELECT)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`

---

### `intent_patterns`
**Row Count**: 25

**Columns** (8):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `intent_type` | text | NO |  |  |
| `pattern_type` | text | NO |  |  |
| `pattern` | text | NO |  |  |
| `weight` | numeric | YES | 1.0 |  |
| `examples` | ARRAY | YES |  | enum: _text |
| `active` | boolean | YES | true | enum: bool |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_135796_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135796_2_not_null`: intent_type IS NOT NULL
- **CHECK** `2200_135796_3_not_null`: pattern_type IS NOT NULL
- **CHECK** `2200_135796_4_not_null`: pattern IS NOT NULL
- **CHECK** `2200_135796_8_not_null`: created_at IS NOT NULL

**Indexes** (1):
- `intent_patterns_pkey`
  ```sql
  CREATE UNIQUE INDEX intent_patterns_pkey ON public.intent_patterns USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **intent_patterns_read** (SELECT)
  - Roles: ['authenticated']
  - USING: `(active = true)`
- **intent_patterns_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `ledger_day_anchors`
**Row Count**: 0

**Columns** (20):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `anchor_date` | date | NO |  |  |
| `total_mutations` | integer | YES | 0 | enum: int4 |
| `total_reads` | integer | YES | 0 | enum: int4 |
| `total_contexts` | integer | YES | 0 | enum: int4 |
| `mutation_by_type` | jsonb | YES | '{}'::jsonb |  |
| `mutations_by_user` | jsonb | YES | '{}'::jsonb |  |
| `mutations_by_department` | jsonb | YES | '{}'::jsonb |  |
| `actions_breakdown` | jsonb | YES | '{}'::jsonb |  |
| `first_event_id` | uuid | YES |  |  |
| `last_event_id` | uuid | YES |  |  |
| `first_event_time` | timestamp with time zone | YES |  | enum: timestamptz |
| `last_event_time` | timestamp with time zone | YES |  | enum: timestamptz |
| `day_proof_hash` | text | YES |  |  |
| `previous_day_hash` | text | YES |  |  |
| `is_finalized` | boolean | YES | false | enum: bool |
| `finalized_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `yacht_id`, `anchor_date`
- **CHECK** `2200_135706_19_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135706_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135706_20_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_135706_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_135706_3_not_null`: anchor_date IS NOT NULL

**Indexes** (5):
- `idx_ledger_day_anchors_date`
  ```sql
  CREATE INDEX idx_ledger_day_anchors_date ON public.ledger_day_anchors USING btree (anchor_date DESC)
  ```
- `idx_ledger_day_anchors_yacht`
  ```sql
  CREATE INDEX idx_ledger_day_anchors_yacht ON public.ledger_day_anchors USING btree (yacht_id)
  ```
- `idx_ledger_day_anchors_yacht_date`
  ```sql
  CREATE INDEX idx_ledger_day_anchors_yacht_date ON public.ledger_day_anchors USING btree (yacht_id, anchor_date DESC)
  ```
- `ledger_day_anchors_pkey`
  ```sql
  CREATE UNIQUE INDEX ledger_day_anchors_pkey ON public.ledger_day_anchors USING btree (id)
  ```
- `ledger_day_anchors_yacht_id_anchor_date_key`
  ```sql
  CREATE UNIQUE INDEX ledger_day_anchors_yacht_id_anchor_date_key ON public.ledger_day_anchors USING btree (yacht_id, anchor_date)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **day_anchors_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `ledger_events`
**Row Count**: 0

**Columns** (21):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `event_type` | text | NO |  |  |
| `entity_type` | text | NO |  |  |
| `entity_id` | uuid | NO |  |  |
| `action` | text | NO |  |  |
| `previous_state` | jsonb | YES |  |  |
| `new_state` | jsonb | YES |  |  |
| `change_summary` | text | YES |  |  |
| `user_id` | uuid | NO |  |  |
| `user_role` | text | YES |  |  |
| `user_department` | text | YES |  |  |
| `source_context` | text | YES |  |  |
| `session_id` | uuid | YES |  |  |
| `related_event_ids` | ARRAY | YES |  | enum: _uuid |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `proof_hash` | text | NO |  |  |
| `previous_proof_hash` | text | YES |  |  |
| `day_anchor_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `event_timestamp` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_135681_10_not_null`: user_id IS NOT NULL
- **CHECK** `2200_135681_17_not_null`: proof_hash IS NOT NULL
- **CHECK** `2200_135681_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135681_20_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135681_21_not_null`: event_timestamp IS NOT NULL
- **CHECK** `2200_135681_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_135681_3_not_null`: event_type IS NOT NULL
- **CHECK** `2200_135681_4_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_135681_5_not_null`: entity_id IS NOT NULL
- **CHECK** `2200_135681_6_not_null`: action IS NOT NULL
- **CHECK** `valid_event_type`: (event_type = ANY (ARRAY['create'::text, 'update'::text, 'delete'::text, 'status_change'::text, 'assignment'::text, 'approval'::text, 'rejection'::text, 'escalation'::text, 'handover'::text, 'import'::text, 'export'::text]))
- **CHECK** `valid_source_context`: (source_context = ANY (ARRAY['search'::text, 'direct'::text, 'microaction'::text, 'api'::text, 'scheduled'::text, 'import'::text, 'system'::text, 'handover'::text]))

**Indexes** (13):
- `idx_ledger_events_action`
  ```sql
  CREATE INDEX idx_ledger_events_action ON public.ledger_events USING btree (action)
  ```
- `idx_ledger_events_created`
  ```sql
  CREATE INDEX idx_ledger_events_created ON public.ledger_events USING btree (created_at DESC)
  ```
- `idx_ledger_events_day_anchor`
  ```sql
  CREATE INDEX idx_ledger_events_day_anchor ON public.ledger_events USING btree (day_anchor_id)
  ```
- `idx_ledger_events_entity`
  ```sql
  CREATE INDEX idx_ledger_events_entity ON public.ledger_events USING btree (entity_type, entity_id)
  ```
- `idx_ledger_events_metadata`
  ```sql
  CREATE INDEX idx_ledger_events_metadata ON public.ledger_events USING gin (metadata)
  ```
- `idx_ledger_events_new_state`
  ```sql
  CREATE INDEX idx_ledger_events_new_state ON public.ledger_events USING gin (new_state)
  ```
- `idx_ledger_events_session`
  ```sql
  CREATE INDEX idx_ledger_events_session ON public.ledger_events USING btree (session_id)
  ```
- `idx_ledger_events_timestamp`
  ```sql
  CREATE INDEX idx_ledger_events_timestamp ON public.ledger_events USING btree (event_timestamp DESC)
  ```
- `idx_ledger_events_type`
  ```sql
  CREATE INDEX idx_ledger_events_type ON public.ledger_events USING btree (event_type)
  ```
- `idx_ledger_events_user`
  ```sql
  CREATE INDEX idx_ledger_events_user ON public.ledger_events USING btree (user_id)
  ```
- `idx_ledger_events_yacht`
  ```sql
  CREATE INDEX idx_ledger_events_yacht ON public.ledger_events USING btree (yacht_id)
  ```
- `idx_ledger_events_yacht_entity_time`
  ```sql
  CREATE INDEX idx_ledger_events_yacht_entity_time ON public.ledger_events USING btree (yacht_id, entity_type, event_timestamp DESC)
  ```
- `ledger_events_pkey`
  ```sql
  CREATE UNIQUE INDEX ledger_events_pkey ON public.ledger_events USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **ledger_events_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `ledger_filter_presets`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | NO |  |  |
| `name` | text | NO |  |  |
| `description` | text | YES |  |  |
| `filters` | jsonb | NO |  |  |
| `display_options` | jsonb | YES | '{}'::jsonb |  |
| `is_default` | boolean | YES | false | enum: bool |
| `use_count` | integer | YES | 0 | enum: int4 |
| `last_used_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `yacht_id`, `user_id`, `name`
- **CHECK** `2200_135729_11_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135729_12_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_135729_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135729_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_135729_3_not_null`: user_id IS NOT NULL
- **CHECK** `2200_135729_4_not_null`: name IS NOT NULL
- **CHECK** `2200_135729_6_not_null`: filters IS NOT NULL

**Indexes** (3):
- `idx_ledger_filter_presets_user`
  ```sql
  CREATE INDEX idx_ledger_filter_presets_user ON public.ledger_filter_presets USING btree (user_id)
  ```
- `ledger_filter_presets_pkey`
  ```sql
  CREATE UNIQUE INDEX ledger_filter_presets_pkey ON public.ledger_filter_presets USING btree (id)
  ```
- `ledger_filter_presets_yacht_id_user_id_name_key`
  ```sql
  CREATE UNIQUE INDEX ledger_filter_presets_yacht_id_user_id_name_key ON public.ledger_filter_presets USING btree (yacht_id, user_id, name)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **filter_presets_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(user_id = auth.uid())`
- **filter_presets_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(user_id = auth.uid())`
- **filter_presets_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **filter_presets_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(user_id = auth.uid())`

---

### `log_events`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | YES |  |  |
| `event_type` | text | NO |  |  |
| `entity_type` | text | YES |  |  |
| `entity_id` | uuid | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `session_id` | uuid | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18053_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18053_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18053_4_not_null`: event_type IS NOT NULL
- **CHECK** `2200_18053_8_not_null`: created_at IS NOT NULL

**Indexes** (5):
- `event_logs_pkey`
  ```sql
  CREATE UNIQUE INDEX event_logs_pkey ON public.log_events USING btree (id)
  ```
- `idx_event_logs_created_at`
  ```sql
  CREATE INDEX idx_event_logs_created_at ON public.log_events USING btree (created_at)
  ```
- `idx_event_logs_event_type`
  ```sql
  CREATE INDEX idx_event_logs_event_type ON public.log_events USING btree (event_type)
  ```
- `idx_event_logs_user_id`
  ```sql
  CREATE INDEX idx_event_logs_user_id ON public.log_events USING btree (user_id)
  ```
- `idx_event_logs_yacht_id`
  ```sql
  CREATE INDEX idx_event_logs_yacht_id ON public.log_events USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role full access event_logs** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **System can insert event logs** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Users can view yacht event logs** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `log_pipeline_execution`
**Row Count**: 0

**Columns** (10):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | YES |  |  |
| `document_id` | uuid | YES |  |  |
| `step` | text | NO |  |  |
| `status` | text | NO |  |  |
| `message` | text | YES |  |  |
| `error_details` | jsonb | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `duration_ms` | integer | YES |  | enum: int4 |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_33023_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_33023_1_not_null`: id IS NOT NULL
- **CHECK** `2200_33023_4_not_null`: step IS NOT NULL
- **CHECK** `2200_33023_5_not_null`: status IS NOT NULL
- **CHECK** `pipeline_logs_status_check`: (status = ANY (ARRAY['info'::text, 'warning'::text, 'retry'::text, 'failed'::text, 'success'::text]))

**Indexes** (6):
- `idx_pipeline_logs_created`
  ```sql
  CREATE INDEX idx_pipeline_logs_created ON public.log_pipeline_execution USING btree (created_at DESC)
  ```
- `idx_pipeline_logs_document`
  ```sql
  CREATE INDEX idx_pipeline_logs_document ON public.log_pipeline_execution USING btree (document_id)
  ```
- `idx_pipeline_logs_status`
  ```sql
  CREATE INDEX idx_pipeline_logs_status ON public.log_pipeline_execution USING btree (status)
  ```
- `idx_pipeline_logs_step`
  ```sql
  CREATE INDEX idx_pipeline_logs_step ON public.log_pipeline_execution USING btree (step)
  ```
- `idx_pipeline_logs_yacht`
  ```sql
  CREATE INDEX idx_pipeline_logs_yacht ON public.log_pipeline_execution USING btree (yacht_id)
  ```
- `pipeline_logs_pkey`
  ```sql
  CREATE UNIQUE INDEX pipeline_logs_pkey ON public.log_pipeline_execution USING btree (id)
  ```

**RLS**: ✅ ENABLED

---

### `log_system_events`
**Row Count**: 0

**Columns** (4):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `event_type` | text | NO |  |  |
| `event_data` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_33055_1_not_null`: id IS NOT NULL
- **CHECK** `2200_33055_2_not_null`: event_type IS NOT NULL
- **CHECK** `2200_33055_4_not_null`: created_at IS NOT NULL

**Indexes** (3):
- `idx_system_logs_created`
  ```sql
  CREATE INDEX idx_system_logs_created ON public.log_system_events USING btree (created_at DESC)
  ```
- `idx_system_logs_type`
  ```sql
  CREATE INDEX idx_system_logs_type ON public.log_system_events USING btree (event_type)
  ```
- `system_logs_pkey`
  ```sql
  CREATE UNIQUE INDEX system_logs_pkey ON public.log_system_events USING btree (id)
  ```

**RLS**: ❌ DISABLED

---

### `navigation_contexts`
**Row Count**: 26

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `created_by_user_id` | uuid | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `ended_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `active_anchor_type` | text | NO |  |  |
| `active_anchor_id` | uuid | NO |  |  |
| `extracted_entities` | jsonb | NO | '{}'::jsonb |  |
| `temporal_bias` | text | NO | 'now'::text |  |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_140179_1_not_null`: id IS NOT NULL
- **CHECK** `2200_140179_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_140179_3_not_null`: created_by_user_id IS NOT NULL
- **CHECK** `2200_140179_4_not_null`: created_at IS NOT NULL
- **CHECK** `2200_140179_6_not_null`: active_anchor_type IS NOT NULL
- **CHECK** `2200_140179_7_not_null`: active_anchor_id IS NOT NULL
- **CHECK** `2200_140179_8_not_null`: extracted_entities IS NOT NULL
- **CHECK** `2200_140179_9_not_null`: temporal_bias IS NOT NULL
- **CHECK** `navigation_contexts_active_anchor_type_check`: (active_anchor_type = ANY (ARRAY['manual_section'::text, 'document'::text, 'inventory_item'::text, 'work_order'::text, 'fault'::text, 'shopping_item'::text, 'shopping_list'::text, 'email_thread'::text, 'certificate'::text, 'equipment'::text, 'part'::text]))
- **CHECK** `navigation_contexts_temporal_bias_check`: (temporal_bias = ANY (ARRAY['now'::text, 'recent'::text, 'historical'::text]))

**Indexes** (3):
- `idx_navigation_contexts_active`
  ```sql
  CREATE INDEX idx_navigation_contexts_active ON public.navigation_contexts USING btree (yacht_id, created_by_user_id) WHERE (ended_at IS NULL)
  ```
- `idx_navigation_contexts_yacht_created`
  ```sql
  CREATE INDEX idx_navigation_contexts_yacht_created ON public.navigation_contexts USING btree (yacht_id, created_at DESC)
  ```
- `navigation_contexts_pkey`
  ```sql
  CREATE UNIQUE INDEX navigation_contexts_pkey ON public.navigation_contexts USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Service role manages navigation_contexts** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **navigation_contexts_insert_own_yacht** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `((yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))) AND (created_by_user_id = auth.uid()))`
- **navigation_contexts_select_own_yacht** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`
- **navigation_contexts_update_own** (UPDATE)
  - Roles: ['public']
  - USING: `((yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))) AND (created_by_user_id = auth.uid()))`

---

### `onedrive_connections`
**Row Count**: 1

**Columns** (10):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | text | NO |  |  |
| `user_principal_name` | text | NO |  |  |
| `access_token_encrypted` | text | NO |  |  |
| `refresh_token_encrypted` | text | NO |  |  |
| `token_expires_at` | timestamp with time zone | NO |  | enum: timestamptz |
| `sync_enabled` | boolean | YES | true | enum: bool |
| `selected_folders` | jsonb | YES | '[]'::jsonb |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `last_sync_at` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `yacht_id`, `user_principal_name`
- **CHECK** `2200_126479_1_not_null`: id IS NOT NULL
- **CHECK** `2200_126479_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_126479_3_not_null`: user_principal_name IS NOT NULL
- **CHECK** `2200_126479_4_not_null`: access_token_encrypted IS NOT NULL
- **CHECK** `2200_126479_5_not_null`: refresh_token_encrypted IS NOT NULL
- **CHECK** `2200_126479_6_not_null`: token_expires_at IS NOT NULL

**Indexes** (3):
- `ix_onedrive_connections_yacht_id`
  ```sql
  CREATE INDEX ix_onedrive_connections_yacht_id ON public.onedrive_connections USING btree (yacht_id)
  ```
- `onedrive_connections_pkey`
  ```sql
  CREATE UNIQUE INDEX onedrive_connections_pkey ON public.onedrive_connections USING btree (id)
  ```
- `uq_yacht_user`
  ```sql
  CREATE UNIQUE INDEX uq_yacht_user ON public.onedrive_connections USING btree (yacht_id, user_principal_name)
  ```

**RLS**: ❌ DISABLED

---

### `onedrive_sync_jobs`
**Row Count**: 0

**Columns** (10):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `connection_id` | uuid | NO |  |  |
| `yacht_id` | text | NO |  |  |
| `job_status` | text | NO | 'pending'::text |  |
| `total_files_found` | integer | YES | 0 | enum: int4 |
| `files_succeeded` | integer | YES | 0 | enum: int4 |
| `files_failed` | integer | YES | 0 | enum: int4 |
| `started_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `connection_id` → `onedrive_connections(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_126511_1_not_null`: id IS NOT NULL
- **CHECK** `2200_126511_2_not_null`: connection_id IS NOT NULL
- **CHECK** `2200_126511_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_126511_4_not_null`: job_status IS NOT NULL

**Indexes** (2):
- `ix_onedrive_sync_jobs_yacht_id`
  ```sql
  CREATE INDEX ix_onedrive_sync_jobs_yacht_id ON public.onedrive_sync_jobs USING btree (yacht_id)
  ```
- `onedrive_sync_jobs_pkey`
  ```sql
  CREATE UNIQUE INDEX onedrive_sync_jobs_pkey ON public.onedrive_sync_jobs USING btree (id)
  ```

**RLS**: ❌ DISABLED

---

### `onedrive_sync_state`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `connection_id` | uuid | NO |  |  |
| `yacht_id` | text | NO |  |  |
| `onedrive_item_id` | text | NO |  |  |
| `onedrive_path` | text | NO |  |  |
| `file_name` | text | NO |  |  |
| `file_size` | bigint | YES |  | enum: int8 |
| `onedrive_etag` | text | YES |  |  |
| `sync_status` | text | NO | 'pending'::text |  |
| `supabase_doc_id` | uuid | YES |  |  |
| `extracted_metadata` | jsonb | YES |  |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `connection_id` → `onedrive_connections(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `connection_id`, `onedrive_item_id`
- **CHECK** `2200_126493_1_not_null`: id IS NOT NULL
- **CHECK** `2200_126493_2_not_null`: connection_id IS NOT NULL
- **CHECK** `2200_126493_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_126493_4_not_null`: onedrive_item_id IS NOT NULL
- **CHECK** `2200_126493_5_not_null`: onedrive_path IS NOT NULL
- **CHECK** `2200_126493_6_not_null`: file_name IS NOT NULL
- **CHECK** `2200_126493_9_not_null`: sync_status IS NOT NULL

**Indexes** (3):
- `ix_onedrive_sync_state_yacht_id`
  ```sql
  CREATE INDEX ix_onedrive_sync_state_yacht_id ON public.onedrive_sync_state USING btree (yacht_id)
  ```
- `onedrive_sync_state_pkey`
  ```sql
  CREATE UNIQUE INDEX onedrive_sync_state_pkey ON public.onedrive_sync_state USING btree (id)
  ```
- `uq_connection_item`
  ```sql
  CREATE UNIQUE INDEX uq_connection_item ON public.onedrive_sync_state USING btree (connection_id, onedrive_item_id)
  ```

**RLS**: ❌ DISABLED

---

### `pms_attachments`
**Row Count**: 6

**Columns** (22):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `entity_type` | character varying | NO |  | enum: varchar |
| `entity_id` | uuid | NO |  |  |
| `filename` | character varying | NO |  | enum: varchar |
| `original_filename` | character varying | YES |  | enum: varchar |
| `mime_type` | character varying | NO |  | enum: varchar |
| `file_size` | integer | YES |  | enum: int4 |
| `storage_path` | text | NO |  |  |
| `width` | integer | YES |  | enum: int4 |
| `height` | integer | YES |  | enum: int4 |
| `thumbnail_path` | text | YES |  |  |
| `description` | text | YES |  |  |
| `tags` | ARRAY | YES |  | enum: _text |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `uploaded_by` | uuid | NO |  |  |
| `uploaded_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_138797_16_not_null`: uploaded_by IS NOT NULL
- **CHECK** `2200_138797_17_not_null`: uploaded_at IS NOT NULL
- **CHECK** `2200_138797_18_not_null`: created_at IS NOT NULL
- **CHECK** `2200_138797_1_not_null`: id IS NOT NULL
- **CHECK** `2200_138797_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_138797_3_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_138797_4_not_null`: entity_id IS NOT NULL
- **CHECK** `2200_138797_5_not_null`: filename IS NOT NULL
- **CHECK** `2200_138797_7_not_null`: mime_type IS NOT NULL
- **CHECK** `2200_138797_9_not_null`: storage_path IS NOT NULL
- **CHECK** `chk_pms_attachments_entity_type`: ((entity_type)::text = ANY ((ARRAY['fault'::character varying, 'work_order'::character varying, 'equipment'::character varying, 'checklist_item'::character varying, 'note'::character varying, 'handover'::character varying, 'purchase_order'::character varying])::text[]))

**Indexes** (5):
- `idx_pms_attachments_entity`
  ```sql
  CREATE INDEX idx_pms_attachments_entity ON public.pms_attachments USING btree (entity_type, entity_id)
  ```
- `idx_pms_attachments_mime_type`
  ```sql
  CREATE INDEX idx_pms_attachments_mime_type ON public.pms_attachments USING btree (mime_type)
  ```
- `idx_pms_attachments_uploaded_by`
  ```sql
  CREATE INDEX idx_pms_attachments_uploaded_by ON public.pms_attachments USING btree (uploaded_by)
  ```
- `idx_pms_attachments_yacht_id`
  ```sql
  CREATE INDEX idx_pms_attachments_yacht_id ON public.pms_attachments USING btree (yacht_id)
  ```
- `pms_attachments_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_attachments_pkey ON public.pms_attachments USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (9):
- **service_role_bypass** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **users_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **users_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_view** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **yacht_isolation_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_select** (SELECT)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`

**Triggers** (1):
- `trg_pms_attachments_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_pms_attachments_updated_at()

---

### `pms_certificates`
**Row Count**: 0

**Columns** (17):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `certificate_name` | text | NO |  |  |
| `certificate_type` | text | NO |  |  |
| `certificate_number` | text | YES |  |  |
| `issuing_authority` | text | YES |  |  |
| `issue_date` | date | YES |  |  |
| `expiry_date` | date | YES |  |  |
| `document_id` | uuid | YES |  |  |
| `equipment_id` | uuid | YES |  |  |
| `status` | text | YES | 'valid'::text |  |
| `superseded_by` | uuid | YES |  |  |
| `notes` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_by` | uuid | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `superseded_by` → `pms_certificates(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_144139_15_not_null`: created_at IS NOT NULL
- **CHECK** `2200_144139_16_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_144139_1_not_null`: id IS NOT NULL
- **CHECK** `2200_144139_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_144139_3_not_null`: certificate_name IS NOT NULL
- **CHECK** `2200_144139_4_not_null`: certificate_type IS NOT NULL

**Indexes** (6):
- `idx_certificates_equipment`
  ```sql
  CREATE INDEX idx_certificates_equipment ON public.pms_certificates USING btree (equipment_id) WHERE (equipment_id IS NOT NULL)
  ```
- `idx_certificates_expiry`
  ```sql
  CREATE INDEX idx_certificates_expiry ON public.pms_certificates USING btree (expiry_date) WHERE (expiry_date IS NOT NULL)
  ```
- `idx_certificates_status`
  ```sql
  CREATE INDEX idx_certificates_status ON public.pms_certificates USING btree (status)
  ```
- `idx_certificates_type`
  ```sql
  CREATE INDEX idx_certificates_type ON public.pms_certificates USING btree (certificate_type)
  ```
- `idx_certificates_yacht`
  ```sql
  CREATE INDEX idx_certificates_yacht ON public.pms_certificates USING btree (yacht_id)
  ```
- `pms_certificates_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_certificates_pkey ON public.pms_certificates USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (5):
- **Managers can delete certificates** (DELETE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Officers can create certificates** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text, 'captain'::text, 'purser'::text])))`
- **Officers can update certificates** (UPDATE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text, 'captain'::text, 'purser'::text])))`
- **Service role full access certificates** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can view certificates** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_checklist_items`
**Row Count**: 29

**Columns** (32):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `checklist_id` | uuid | NO |  |  |
| `description` | text | NO |  |  |
| `instructions` | text | YES |  |  |
| `sequence` | integer | NO | 0 | enum: int4 |
| `is_completed` | boolean | NO | false | enum: bool |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `completed_by` | uuid | YES |  |  |
| `completion_notes` | text | YES |  |  |
| `is_required` | boolean | NO | true | enum: bool |
| `requires_photo` | boolean | NO | false | enum: bool |
| `requires_signature` | boolean | NO | false | enum: bool |
| `requires_value` | boolean | NO | false | enum: bool |
| `value_type` | character varying | YES |  | enum: varchar |
| `value_unit` | character varying | YES |  | enum: varchar |
| `value_min` | numeric | YES |  |  |
| `value_max` | numeric | YES |  |  |
| `recorded_value` | text | YES |  |  |
| `recorded_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `recorded_by` | uuid | YES |  |  |
| `photo_url` | text | YES |  |  |
| `signature_data` | jsonb | YES |  |  |
| `status` | character varying | NO | 'pending'::character varying | enum: varchar |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_by` | uuid | YES |  |  |
| `updated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `checklist_id` → `pms_checklists(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_138763_11_not_null`: is_required IS NOT NULL
- **CHECK** `2200_138763_12_not_null`: requires_photo IS NOT NULL
- **CHECK** `2200_138763_13_not_null`: requires_signature IS NOT NULL
- **CHECK** `2200_138763_14_not_null`: requires_value IS NOT NULL
- **CHECK** `2200_138763_1_not_null`: id IS NOT NULL
- **CHECK** `2200_138763_24_not_null`: status IS NOT NULL
- **CHECK** `2200_138763_26_not_null`: created_at IS NOT NULL
- **CHECK** `2200_138763_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_138763_3_not_null`: checklist_id IS NOT NULL
- **CHECK** `2200_138763_4_not_null`: description IS NOT NULL
- **CHECK** `2200_138763_6_not_null`: sequence IS NOT NULL
- **CHECK** `2200_138763_7_not_null`: is_completed IS NOT NULL
- **CHECK** `chk_pms_checklist_items_status`: ((status)::text = ANY ((ARRAY['pending'::character varying, 'in_progress'::character varying, 'completed'::character varying, 'skipped'::character varying, 'na'::character varying])::text[]))
- **CHECK** `chk_pms_checklist_items_value_type`: ((value_type IS NULL) OR ((value_type)::text = ANY ((ARRAY['number'::character varying, 'text'::character varying, 'boolean'::character varying, 'date'::character varying])::text[])))

**Indexes** (6):
- `idx_pms_checklist_items_checklist_id`
  ```sql
  CREATE INDEX idx_pms_checklist_items_checklist_id ON public.pms_checklist_items USING btree (checklist_id)
  ```
- `idx_pms_checklist_items_completed`
  ```sql
  CREATE INDEX idx_pms_checklist_items_completed ON public.pms_checklist_items USING btree (is_completed) WHERE (deleted_at IS NULL)
  ```
- `idx_pms_checklist_items_sequence`
  ```sql
  CREATE INDEX idx_pms_checklist_items_sequence ON public.pms_checklist_items USING btree (checklist_id, sequence)
  ```
- `idx_pms_checklist_items_status`
  ```sql
  CREATE INDEX idx_pms_checklist_items_status ON public.pms_checklist_items USING btree (status) WHERE (deleted_at IS NULL)
  ```
- `idx_pms_checklist_items_yacht_id`
  ```sql
  CREATE INDEX idx_pms_checklist_items_yacht_id ON public.pms_checklist_items USING btree (yacht_id)
  ```
- `pms_checklist_items_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_checklist_items_pkey ON public.pms_checklist_items USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (9):
- **service_role_bypass** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **users_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **users_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_view** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **yacht_isolation_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_select** (SELECT)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`

**Triggers** (4):
- `trg_pms_checklist_items_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_pms_checklist_items_updated_at()
- `trg_update_checklist_counts` (AFTER INSERT)
  - Action: EXECUTE FUNCTION update_checklist_completion_count()
- `trg_update_checklist_counts` (AFTER DELETE)
  - Action: EXECUTE FUNCTION update_checklist_completion_count()
- `trg_update_checklist_counts` (AFTER UPDATE)
  - Action: EXECUTE FUNCTION update_checklist_completion_count()

---

### `pms_checklists`
**Row Count**: 5

**Columns** (19):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `name` | character varying | NO |  | enum: varchar |
| `description` | text | YES |  |  |
| `checklist_type` | character varying | NO | 'maintenance'::character varying | enum: varchar |
| `equipment_id` | uuid | YES |  |  |
| `work_order_id` | uuid | YES |  |  |
| `status` | character varying | NO | 'active'::character varying | enum: varchar |
| `is_template` | boolean | NO | false | enum: bool |
| `total_items` | integer | YES | 0 | enum: int4 |
| `completed_items` | integer | YES | 0 | enum: int4 |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_by` | uuid | YES |  |  |
| `updated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **CHECK** `2200_138728_13_not_null`: created_at IS NOT NULL
- **CHECK** `2200_138728_1_not_null`: id IS NOT NULL
- **CHECK** `2200_138728_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_138728_3_not_null`: name IS NOT NULL
- **CHECK** `2200_138728_5_not_null`: checklist_type IS NOT NULL
- **CHECK** `2200_138728_8_not_null`: status IS NOT NULL
- **CHECK** `2200_138728_9_not_null`: is_template IS NOT NULL
- **CHECK** `chk_pms_checklists_status`: ((status)::text = ANY ((ARRAY['active'::character varying, 'archived'::character varying, 'draft'::character varying])::text[]))
- **CHECK** `chk_pms_checklists_type`: ((checklist_type)::text = ANY ((ARRAY['maintenance'::character varying, 'safety'::character varying, 'inspection'::character varying, 'departure'::character varying, 'arrival'::character varying, 'watch'::character varying, 'custom'::character varying])::text[]))

**Indexes** (6):
- `idx_pms_checklists_equipment_id`
  ```sql
  CREATE INDEX idx_pms_checklists_equipment_id ON public.pms_checklists USING btree (equipment_id) WHERE (equipment_id IS NOT NULL)
  ```
- `idx_pms_checklists_status`
  ```sql
  CREATE INDEX idx_pms_checklists_status ON public.pms_checklists USING btree (status) WHERE (deleted_at IS NULL)
  ```
- `idx_pms_checklists_type`
  ```sql
  CREATE INDEX idx_pms_checklists_type ON public.pms_checklists USING btree (checklist_type)
  ```
- `idx_pms_checklists_work_order_id`
  ```sql
  CREATE INDEX idx_pms_checklists_work_order_id ON public.pms_checklists USING btree (work_order_id) WHERE (work_order_id IS NOT NULL)
  ```
- `idx_pms_checklists_yacht_id`
  ```sql
  CREATE INDEX idx_pms_checklists_yacht_id ON public.pms_checklists USING btree (yacht_id)
  ```
- `pms_checklists_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_checklists_pkey ON public.pms_checklists USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (9):
- **service_role_bypass** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **users_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **users_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_view** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **yacht_isolation_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_select** (SELECT)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`

**Triggers** (1):
- `trg_pms_checklists_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_pms_checklists_updated_at()

---

### `pms_crew_certificates`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `person_node_id` | uuid | YES |  |  |
| `person_name` | text | NO |  |  |
| `certificate_type` | text | NO |  |  |
| `certificate_number` | text | YES |  |  |
| `issuing_authority` | text | YES |  |  |
| `issue_date` | date | YES |  |  |
| `expiry_date` | date | YES |  |  |
| `document_id` | uuid | YES |  |  |
| `properties` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `person_node_id` → `search_graph_nodes(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_24797_12_not_null`: created_at IS NOT NULL
- **CHECK** `2200_24797_1_not_null`: id IS NOT NULL
- **CHECK** `2200_24797_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_24797_4_not_null`: person_name IS NOT NULL
- **CHECK** `2200_24797_5_not_null`: certificate_type IS NOT NULL

**Indexes** (6):
- `crew_certificates_pkey`
  ```sql
  CREATE UNIQUE INDEX crew_certificates_pkey ON public.pms_crew_certificates USING btree (id)
  ```
- `idx_crew_certs_expiry`
  ```sql
  CREATE INDEX idx_crew_certs_expiry ON public.pms_crew_certificates USING btree (yacht_id, expiry_date)
  ```
- `idx_crew_certs_expiry_range`
  ```sql
  CREATE INDEX idx_crew_certs_expiry_range ON public.pms_crew_certificates USING btree (yacht_id, expiry_date) WHERE (expiry_date IS NOT NULL)
  ```
- `idx_crew_certs_person`
  ```sql
  CREATE INDEX idx_crew_certs_person ON public.pms_crew_certificates USING btree (person_node_id)
  ```
- `idx_crew_certs_type`
  ```sql
  CREATE INDEX idx_crew_certs_type ON public.pms_crew_certificates USING btree (yacht_id, certificate_type)
  ```
- `idx_crew_certs_yacht`
  ```sql
  CREATE INDEX idx_crew_certs_yacht ON public.pms_crew_certificates USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access crew_certificates** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view yacht crew certificates** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_entity_images`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `entity_type` | text | NO |  |  |
| `entity_id` | uuid | NO |  |  |
| `image_id` | uuid | NO |  |  |
| `image_role` | text | NO |  |  |
| `sequence` | integer | YES | 1 | enum: int4 |
| `notes` | text | YES |  |  |
| `metadata` | jsonb | YES |  |  |
| `added_by` | uuid | NO |  |  |
| `added_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `image_id` → `pms_image_uploads(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_129734_10_not_null`: added_by IS NOT NULL
- **CHECK** `2200_129734_11_not_null`: added_at IS NOT NULL
- **CHECK** `2200_129734_12_not_null`: created_at IS NOT NULL
- **CHECK** `2200_129734_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129734_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129734_3_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_129734_4_not_null`: entity_id IS NOT NULL
- **CHECK** `2200_129734_5_not_null`: image_id IS NOT NULL
- **CHECK** `2200_129734_6_not_null`: image_role IS NOT NULL
- **CHECK** `chk_entity_type`: (entity_type = ANY (ARRAY['session'::text, 'order'::text, 'part'::text, 'shopping_list_item'::text, 'receiving_line_item'::text, 'work_order'::text, 'receiving_event'::text]))

**Indexes** (5):
- `idx_entity_images_entity`
  ```sql
  CREATE INDEX idx_entity_images_entity ON public.pms_entity_images USING btree (entity_type, entity_id)
  ```
- `idx_entity_images_image`
  ```sql
  CREATE INDEX idx_entity_images_image ON public.pms_entity_images USING btree (image_id)
  ```
- `idx_entity_images_unique`
  ```sql
  CREATE UNIQUE INDEX idx_entity_images_unique ON public.pms_entity_images USING btree (entity_type, entity_id, image_id, image_role)
  ```
- `idx_entity_images_yacht`
  ```sql
  CREATE INDEX idx_entity_images_yacht ON public.pms_entity_images USING btree (yacht_id)
  ```
- `pms_entity_images_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_entity_images_pkey ON public.pms_entity_images USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role full access to entity images** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can add entity images** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (added_by = auth.uid()))`
- **Users can view their yacht's entity images** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_equipment`
**Row Count**: 560

**Columns** (24):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `parent_id` | uuid | YES |  |  |
| `name` | text | NO |  |  |
| `code` | text | YES |  |  |
| `description` | text | YES |  |  |
| `location` | text | YES |  |  |
| `manufacturer` | text | YES |  |  |
| `model` | text | YES |  |  |
| `serial_number` | text | YES |  |  |
| `installed_date` | date | YES |  |  |
| `criticality` | USER-DEFINED | YES | 'medium'::equipment_criticality | enum: equipment_criticality |
| `system_type` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `attention_flag` | boolean | YES | false | enum: bool |
| `attention_reason` | text | YES |  |  |
| `attention_updated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |
| `status` | text | YES | 'operational'::text |  |

**Constraints**:
- **PK**: `id`
- **FK**: `parent_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18077_15_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18077_16_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_18077_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18077_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18077_4_not_null`: name IS NOT NULL
- **CHECK** `pms_equipment_status_check`: (status = ANY (ARRAY['operational'::text, 'degraded'::text, 'failed'::text, 'maintenance'::text, 'decommissioned'::text]))

**Indexes** (12):
- `equipment_pkey`
  ```sql
  CREATE UNIQUE INDEX equipment_pkey ON public.pms_equipment USING btree (id)
  ```
- `idx_equipment_attention_flag`
  ```sql
  CREATE INDEX idx_equipment_attention_flag ON public.pms_equipment USING btree (attention_flag) WHERE (attention_flag = true)
  ```
- `idx_equipment_code`
  ```sql
  CREATE INDEX idx_equipment_code ON public.pms_equipment USING btree (code)
  ```
- `idx_equipment_criticality`
  ```sql
  CREATE INDEX idx_equipment_criticality ON public.pms_equipment USING btree (criticality)
  ```
- `idx_equipment_location`
  ```sql
  CREATE INDEX idx_equipment_location ON public.pms_equipment USING btree (yacht_id, location) WHERE (location IS NOT NULL)
  ```
- `idx_equipment_manufacturer`
  ```sql
  CREATE INDEX idx_equipment_manufacturer ON public.pms_equipment USING btree (yacht_id, manufacturer) WHERE (manufacturer IS NOT NULL)
  ```
- `idx_equipment_parent_id`
  ```sql
  CREATE INDEX idx_equipment_parent_id ON public.pms_equipment USING btree (parent_id)
  ```
- `idx_equipment_system`
  ```sql
  CREATE INDEX idx_equipment_system ON public.pms_equipment USING btree (yacht_id, system_type) WHERE (system_type IS NOT NULL)
  ```
- `idx_equipment_system_type`
  ```sql
  CREATE INDEX idx_equipment_system_type ON public.pms_equipment USING btree (system_type)
  ```
- `idx_equipment_yacht_id`
  ```sql
  CREATE INDEX idx_equipment_yacht_id ON public.pms_equipment USING btree (yacht_id)
  ```
- `idx_pms_equipment_status`
  ```sql
  CREATE INDEX idx_pms_equipment_status ON public.pms_equipment USING btree (yacht_id, status)
  ```
- `idx_pms_equipment_yacht`
  ```sql
  CREATE INDEX idx_pms_equipment_yacht ON public.pms_equipment USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Engineers can manage equipment** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text])))`
- **Service role full access equipment** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view yacht equipment** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (1):
- `no_hard_delete_equipment` (BEFORE DELETE)
  - Action: EXECUTE FUNCTION prevent_hard_delete()

---

### `pms_equipment_parts_bom`
**Row Count**: 15

**Columns** (7):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_id` | uuid | NO |  |  |
| `part_id` | uuid | NO |  |  |
| `quantity_required` | integer | YES | 1 | enum: int4 |
| `notes` | text | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `part_id` → `pms_parts(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18264_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18264_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18264_3_not_null`: equipment_id IS NOT NULL
- **CHECK** `2200_18264_4_not_null`: part_id IS NOT NULL
- **CHECK** `2200_18264_7_not_null`: created_at IS NOT NULL

**Indexes** (5):
- `equipment_parts_pkey`
  ```sql
  CREATE UNIQUE INDEX equipment_parts_pkey ON public.pms_equipment_parts_bom USING btree (id)
  ```
- `idx_equipment_parts_equipment_id`
  ```sql
  CREATE INDEX idx_equipment_parts_equipment_id ON public.pms_equipment_parts_bom USING btree (equipment_id)
  ```
- `idx_equipment_parts_part_id`
  ```sql
  CREATE INDEX idx_equipment_parts_part_id ON public.pms_equipment_parts_bom USING btree (part_id)
  ```
- `idx_equipment_parts_unique`
  ```sql
  CREATE UNIQUE INDEX idx_equipment_parts_unique ON public.pms_equipment_parts_bom USING btree (equipment_id, part_id)
  ```
- `idx_equipment_parts_yacht_id`
  ```sql
  CREATE INDEX idx_equipment_parts_yacht_id ON public.pms_equipment_parts_bom USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Engineers can manage equipment parts** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text])))`
- **Service role full access equipment_parts** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view equipment parts** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_finance_transactions`
**Row Count**: 3

**Columns** (27):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `transaction_number` | text | NO |  |  |
| `transaction_date` | timestamp with time zone | NO | now() | enum: timestamptz |
| `transaction_type` | text | NO |  |  |
| `amount` | numeric | NO |  |  |
| `currency` | text | NO | 'USD'::text |  |
| `order_id` | uuid | YES |  |  |
| `receiving_event_id` | uuid | YES |  |  |
| `receiving_line_item_id` | uuid | YES |  |  |
| `shopping_list_item_id` | uuid | YES |  |  |
| `work_order_id` | uuid | YES |  |  |
| `part_id` | uuid | YES |  |  |
| `equipment_id` | uuid | YES |  |  |
| `description` | text | NO |  |  |
| `source_trigger` | text | NO |  |  |
| `posted_by` | uuid | NO |  |  |
| `approved_by` | uuid | YES |  |  |
| `invoice_number` | text | YES |  |  |
| `invoice_date` | date | YES |  |  |
| `invoice_document_id` | uuid | YES |  |  |
| `notes` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `invoice_document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `order_id` → `pms_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `part_id` → `pms_parts(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `receiving_event_id` → `pms_receiving_events(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `receiving_line_item_id` → `pms_receiving_line_items(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `shopping_list_item_id` → `pms_shopping_list_items(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `transaction_number`
- **CHECK** `2200_129200_15_not_null`: description IS NOT NULL
- **CHECK** `2200_129200_16_not_null`: source_trigger IS NOT NULL
- **CHECK** `2200_129200_17_not_null`: posted_by IS NOT NULL
- **CHECK** `2200_129200_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129200_24_not_null`: created_at IS NOT NULL
- **CHECK** `2200_129200_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129200_3_not_null`: transaction_number IS NOT NULL
- **CHECK** `2200_129200_4_not_null`: transaction_date IS NOT NULL
- **CHECK** `2200_129200_5_not_null`: transaction_type IS NOT NULL
- **CHECK** `2200_129200_6_not_null`: amount IS NOT NULL
- **CHECK** `2200_129200_7_not_null`: currency IS NOT NULL
- **CHECK** `pms_finance_transactions_transaction_type_check`: (transaction_type = ANY (ARRAY['parts_received'::text, 'parts_installed'::text, 'order_adjustment'::text, 'return_credit'::text]))

**Indexes** (11):
- `idx_finance_date`
  ```sql
  CREATE INDEX idx_finance_date ON public.pms_finance_transactions USING btree (transaction_date DESC)
  ```
- `idx_finance_order`
  ```sql
  CREATE INDEX idx_finance_order ON public.pms_finance_transactions USING btree (order_id) WHERE (order_id IS NOT NULL)
  ```
- `idx_finance_part`
  ```sql
  CREATE INDEX idx_finance_part ON public.pms_finance_transactions USING btree (part_id) WHERE (part_id IS NOT NULL)
  ```
- `idx_finance_receiving`
  ```sql
  CREATE INDEX idx_finance_receiving ON public.pms_finance_transactions USING btree (receiving_event_id) WHERE (receiving_event_id IS NOT NULL)
  ```
- `idx_finance_type`
  ```sql
  CREATE INDEX idx_finance_type ON public.pms_finance_transactions USING btree (transaction_type)
  ```
- `idx_finance_wo`
  ```sql
  CREATE INDEX idx_finance_wo ON public.pms_finance_transactions USING btree (work_order_id) WHERE (work_order_id IS NOT NULL)
  ```
- `idx_finance_yacht`
  ```sql
  CREATE INDEX idx_finance_yacht ON public.pms_finance_transactions USING btree (yacht_id)
  ```
- `idx_finance_yacht_date`
  ```sql
  CREATE INDEX idx_finance_yacht_date ON public.pms_finance_transactions USING btree (yacht_id, transaction_date DESC) WHERE (deleted_at IS NULL)
  ```
- `idx_finance_yacht_type`
  ```sql
  CREATE INDEX idx_finance_yacht_type ON public.pms_finance_transactions USING btree (yacht_id, transaction_type) WHERE (deleted_at IS NULL)
  ```
- `pms_finance_transactions_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_finance_transactions_pkey ON public.pms_finance_transactions USING btree (id)
  ```
- `pms_finance_transactions_yacht_transaction_number_unique`
  ```sql
  CREATE UNIQUE INDEX pms_finance_transactions_yacht_transaction_number_unique ON public.pms_finance_transactions USING btree (yacht_id, transaction_number)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Only service role can insert finance transactions** (INSERT)
  - Roles: ['service_role']
  - WITH CHECK: `true`
- **Users can view finance transactions for their yacht** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (1):
- `trg_prevent_finance_updates` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION prevent_finance_transaction_updates()

---

### `pms_handover`
**Row Count**: 97

**Columns** (10):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `entity_type` | text | NO |  |  |
| `entity_id` | uuid | YES |  |  |
| `summary_text` | text | NO |  |  |
| `category` | text | YES |  |  |
| `priority` | integer | YES | 0 | enum: int4 |
| `added_by` | uuid | NO |  |  |
| `added_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `metadata` | jsonb | YES | '{}'::jsonb |  |

**Constraints**:
- **PK**: `id`
- **FK**: `added_by` → `auth_users_profiles(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **CHECK** `2200_126727_1_not_null`: id IS NOT NULL
- **CHECK** `2200_126727_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_126727_3_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_126727_5_not_null`: summary_text IS NOT NULL
- **CHECK** `2200_126727_8_not_null`: added_by IS NOT NULL
- **CHECK** `2200_126727_9_not_null`: added_at IS NOT NULL
- **CHECK** `pms_handover_category_check`: (category = ANY (ARRAY['urgent'::text, 'in_progress'::text, 'completed'::text, 'watch'::text, 'fyi'::text]))
- **CHECK** `pms_handover_entity_type_check`: (entity_type = ANY (ARRAY['work_order'::text, 'fault'::text, 'equipment'::text, 'note'::text, 'document_chunk'::text, 'part'::text]))
- **CHECK** `pms_handover_priority_check`: ((priority >= 0) AND (priority <= 5))

**Indexes** (4):
- `idx_pms_handover_entity`
  ```sql
  CREATE INDEX idx_pms_handover_entity ON public.pms_handover USING btree (entity_type, entity_id) WHERE (entity_id IS NOT NULL)
  ```
- `idx_pms_handover_urgent`
  ```sql
  CREATE INDEX idx_pms_handover_urgent ON public.pms_handover USING btree (yacht_id, priority DESC, added_at DESC) WHERE (category = 'urgent'::text)
  ```
- `idx_pms_handover_yacht`
  ```sql
  CREATE INDEX idx_pms_handover_yacht ON public.pms_handover USING btree (yacht_id, added_at DESC)
  ```
- `pms_handover_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_handover_pkey ON public.pms_handover USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (5):
- **Service role full access handover** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can create handover** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Users can delete handover** (DELETE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Users can update handover** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **Users can view handover** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_hours_of_rest`
**Row Count**: 7

**Columns** (29):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | NO |  |  |
| `record_date` | date | NO |  |  |
| `rest_periods` | jsonb | NO | '[]'::jsonb |  |
| `total_rest_hours` | numeric | NO | 0 |  |
| `total_work_hours` | numeric | NO | 0 |  |
| `is_daily_compliant` | boolean | NO | false | enum: bool |
| `daily_compliance_notes` | text | YES |  |  |
| `weekly_rest_hours` | numeric | NO | 0 |  |
| `is_weekly_compliant` | boolean | NO | false | enum: bool |
| `weekly_compliance_notes` | text | YES |  |  |
| `is_compliant` | boolean | NO | false | enum: bool |
| `status` | text | NO | 'draft'::text |  |
| `submitted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `approved_by` | uuid | YES |  |  |
| `approved_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `location` | text | YES |  |  |
| `voyage_type` | text | YES |  |  |
| `has_exception` | boolean | NO | false | enum: bool |
| `exception_reason` | text | YES |  |  |
| `exception_approved_by` | uuid | YES |  |  |
| `exception_approved_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `signature` | jsonb | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_by` | uuid | YES |  |  |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `yacht_id`, `user_id`, `record_date`
- **CHECK** `2200_133312_10_not_null`: weekly_rest_hours IS NOT NULL
- **CHECK** `2200_133312_11_not_null`: is_weekly_compliant IS NOT NULL
- **CHECK** `2200_133312_13_not_null`: is_compliant IS NOT NULL
- **CHECK** `2200_133312_14_not_null`: status IS NOT NULL
- **CHECK** `2200_133312_1_not_null`: id IS NOT NULL
- **CHECK** `2200_133312_20_not_null`: has_exception IS NOT NULL
- **CHECK** `2200_133312_26_not_null`: created_at IS NOT NULL
- **CHECK** `2200_133312_28_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_133312_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_133312_3_not_null`: user_id IS NOT NULL
- **CHECK** `2200_133312_4_not_null`: record_date IS NOT NULL
- **CHECK** `2200_133312_5_not_null`: rest_periods IS NOT NULL
- **CHECK** `2200_133312_6_not_null`: total_rest_hours IS NOT NULL
- **CHECK** `2200_133312_7_not_null`: total_work_hours IS NOT NULL
- **CHECK** `2200_133312_8_not_null`: is_daily_compliant IS NOT NULL
- **CHECK** `pms_hours_of_rest_status_check`: (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'flagged'::text]))
- **CHECK** `pms_hours_of_rest_voyage_type_check`: (voyage_type = ANY (ARRAY['at_sea'::text, 'in_port'::text, 'shipyard'::text, NULL::text]))

**Indexes** (4):
- `idx_pms_hor_user_date`
  ```sql
  CREATE INDEX idx_pms_hor_user_date ON public.pms_hours_of_rest USING btree (yacht_id, user_id, record_date DESC)
  ```
- `idx_pms_hor_yacht_date`
  ```sql
  CREATE INDEX idx_pms_hor_yacht_date ON public.pms_hours_of_rest USING btree (yacht_id, record_date DESC)
  ```
- `pms_hours_of_rest_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_hours_of_rest_pkey ON public.pms_hours_of_rest USING btree (id)
  ```
- `uq_pms_hor_user_date`
  ```sql
  CREATE UNIQUE INDEX uq_pms_hor_user_date ON public.pms_hours_of_rest USING btree (yacht_id, user_id, record_date)
  ```

**RLS**: ❌ DISABLED

**Triggers** (4):
- `trg_pms_hor_daily` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION fn_calculate_hor_daily_compliance()
- `trg_pms_hor_daily` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION fn_calculate_hor_daily_compliance()
- `trg_pms_hor_weekly` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION fn_calculate_hor_weekly_compliance()
- `trg_pms_hor_weekly` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION fn_calculate_hor_weekly_compliance()

---

### `pms_image_uploads`
**Row Count**: 1

**Columns** (37):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `storage_bucket` | text | NO |  |  |
| `storage_path` | text | NO |  |  |
| `file_name` | text | NO |  |  |
| `mime_type` | text | NO |  |  |
| `file_size_bytes` | bigint | NO |  | enum: int8 |
| `sha256_hash` | text | NO |  |  |
| `is_valid` | boolean | NO | false | enum: bool |
| `validation_stage` | text | NO | 'uploaded'::text |  |
| `validation_errors` | jsonb | YES |  |  |
| `document_type` | text | YES |  |  |
| `classification_confidence` | numeric | YES |  |  |
| `classification_metadata` | jsonb | YES |  |  |
| `ocr_raw_text` | text | YES |  |  |
| `ocr_completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `extraction_status` | text | YES |  |  |
| `extracted_data` | jsonb | YES |  |  |
| `extracted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `upload_ip_address` | inet | YES |  |  |
| `is_duplicate` | boolean | NO | false | enum: bool |
| `duplicate_of_image_id` | uuid | YES |  |  |
| `uploaded_by` | uuid | NO |  |  |
| `uploaded_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `processed_by` | uuid | YES |  |  |
| `processed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `metadata` | jsonb | YES |  |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `ocr_confidence` | double precision | YES |  | enum: float8 |
| `ocr_engine` | text | YES |  |  |
| `ocr_processing_time_ms` | integer | YES |  | enum: int4 |
| `ocr_line_count` | integer | YES |  | enum: int4 |
| `ocr_word_count` | integer | YES |  | enum: int4 |

**Constraints**:
- **PK**: `id`
- **FK**: `duplicate_of_image_id` → `pms_image_uploads(id)` ON DELETE NO ACTION, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_129631_10_not_null`: validation_stage IS NOT NULL
- **CHECK** `2200_129631_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129631_21_not_null`: is_duplicate IS NOT NULL
- **CHECK** `2200_129631_23_not_null`: uploaded_by IS NOT NULL
- **CHECK** `2200_129631_24_not_null`: uploaded_at IS NOT NULL
- **CHECK** `2200_129631_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129631_31_not_null`: created_at IS NOT NULL
- **CHECK** `2200_129631_32_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_129631_3_not_null`: storage_bucket IS NOT NULL
- **CHECK** `2200_129631_4_not_null`: storage_path IS NOT NULL
- **CHECK** `2200_129631_5_not_null`: file_name IS NOT NULL
- **CHECK** `2200_129631_6_not_null`: mime_type IS NOT NULL
- **CHECK** `2200_129631_7_not_null`: file_size_bytes IS NOT NULL
- **CHECK** `2200_129631_8_not_null`: sha256_hash IS NOT NULL
- **CHECK** `2200_129631_9_not_null`: is_valid IS NOT NULL
- **CHECK** `pms_image_uploads_document_type_check`: (document_type = ANY (ARRAY['packing_slip'::text, 'shipping_label'::text, 'invoice'::text, 'part_photo'::text, 'discrepancy_photo'::text, 'unknown'::text]))
- **CHECK** `pms_image_uploads_extraction_status_check`: (extraction_status = ANY (ARRAY['pending'::text, 'processing'::text, 'completed'::text, 'failed'::text]))
- **CHECK** `pms_image_uploads_validation_stage_check`: (validation_stage = ANY (ARRAY['uploaded'::text, 'validated'::text, 'classified'::text, 'extracted'::text, 'processed'::text, 'failed'::text]))

**Indexes** (11):
- `idx_image_uploads_document_type`
  ```sql
  CREATE INDEX idx_image_uploads_document_type ON public.pms_image_uploads USING btree (document_type) WHERE (deleted_at IS NULL)
  ```
- `idx_image_uploads_hash`
  ```sql
  CREATE INDEX idx_image_uploads_hash ON public.pms_image_uploads USING btree (sha256_hash) WHERE (deleted_at IS NULL)
  ```
- `idx_image_uploads_hash_yacht`
  ```sql
  CREATE UNIQUE INDEX idx_image_uploads_hash_yacht ON public.pms_image_uploads USING btree (sha256_hash, yacht_id) WHERE (deleted_at IS NULL)
  ```
- `idx_image_uploads_storage_path`
  ```sql
  CREATE UNIQUE INDEX idx_image_uploads_storage_path ON public.pms_image_uploads USING btree (storage_bucket, storage_path) WHERE (deleted_at IS NULL)
  ```
- `idx_image_uploads_uploaded_at`
  ```sql
  CREATE INDEX idx_image_uploads_uploaded_at ON public.pms_image_uploads USING btree (yacht_id, uploaded_at DESC)
  ```
- `idx_image_uploads_uploaded_by`
  ```sql
  CREATE INDEX idx_image_uploads_uploaded_by ON public.pms_image_uploads USING btree (uploaded_by, uploaded_at DESC)
  ```
- `idx_image_uploads_validation_stage`
  ```sql
  CREATE INDEX idx_image_uploads_validation_stage ON public.pms_image_uploads USING btree (validation_stage) WHERE (deleted_at IS NULL)
  ```
- `idx_image_uploads_yacht`
  ```sql
  CREATE INDEX idx_image_uploads_yacht ON public.pms_image_uploads USING btree (yacht_id) WHERE (deleted_at IS NULL)
  ```
- `idx_pms_image_uploads_ocr_engine`
  ```sql
  CREATE INDEX idx_pms_image_uploads_ocr_engine ON public.pms_image_uploads USING btree (ocr_engine) WHERE (deleted_at IS NULL)
  ```
- `idx_pms_image_uploads_ocr_text_search`
  ```sql
  CREATE INDEX idx_pms_image_uploads_ocr_text_search ON public.pms_image_uploads USING gin (to_tsvector('english'::regconfig, ocr_raw_text)) WHERE (deleted_at IS NULL)
  ```
- `pms_image_uploads_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_image_uploads_pkey ON public.pms_image_uploads USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role full access to images** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can upload images for their yacht** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (uploaded_by = auth.uid()))`
- **Users can view their yacht's images** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (3):
- `trg_enforce_deduplication` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION enforce_image_deduplication()
- `trg_enforce_rate_limit` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION check_image_upload_rate_limit()
- `trg_image_uploads_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at_column()

---

### `pms_inventory_stock`
**Row Count**: 282

**Columns** (16):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `part_id` | uuid | NO |  |  |
| `location` | text | YES |  |  |
| `quantity` | integer | NO | 0 | enum: int4 |
| `min_quantity` | integer | YES |  | enum: int4 |
| `max_quantity` | integer | YES |  | enum: int4 |
| `reorder_quantity` | integer | YES |  | enum: int4 |
| `last_counted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `part_id` → `pms_parts(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18293_11_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18293_12_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_18293_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18293_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18293_3_not_null`: part_id IS NOT NULL
- **CHECK** `2200_18293_5_not_null`: quantity IS NOT NULL

**Indexes** (6):
- `idx_inventory_location`
  ```sql
  CREATE INDEX idx_inventory_location ON public.pms_inventory_stock USING btree (yacht_id, location) WHERE (location IS NOT NULL)
  ```
- `idx_inventory_part`
  ```sql
  CREATE INDEX idx_inventory_part ON public.pms_inventory_stock USING btree (part_id)
  ```
- `idx_inventory_stock_location`
  ```sql
  CREATE INDEX idx_inventory_stock_location ON public.pms_inventory_stock USING btree (location)
  ```
- `idx_inventory_stock_part_id`
  ```sql
  CREATE INDEX idx_inventory_stock_part_id ON public.pms_inventory_stock USING btree (part_id)
  ```
- `idx_inventory_stock_yacht_id`
  ```sql
  CREATE INDEX idx_inventory_stock_yacht_id ON public.pms_inventory_stock USING btree (yacht_id)
  ```
- `inventory_stock_pkey`
  ```sql
  CREATE UNIQUE INDEX inventory_stock_pkey ON public.pms_inventory_stock USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Engineers can manage stock** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'deck'::text, 'interior'::text])))`
- **Service role full access inventory_stock** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view stock levels** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_inventory_transactions`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `stock_id` | uuid | NO |  |  |
| `transaction_type` | text | NO |  |  |
| `quantity_change` | integer | NO |  | enum: int4 |
| `quantity_before` | integer | NO |  | enum: int4 |
| `quantity_after` | integer | NO |  | enum: int4 |
| `user_id` | uuid | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_125343_1_not_null`: id IS NOT NULL
- **CHECK** `2200_125343_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_125343_3_not_null`: stock_id IS NOT NULL
- **CHECK** `2200_125343_4_not_null`: transaction_type IS NOT NULL
- **CHECK** `2200_125343_5_not_null`: quantity_change IS NOT NULL
- **CHECK** `2200_125343_6_not_null`: quantity_before IS NOT NULL
- **CHECK** `2200_125343_7_not_null`: quantity_after IS NOT NULL
- **CHECK** `2200_125343_8_not_null`: user_id IS NOT NULL
- **CHECK** `2200_125343_9_not_null`: created_at IS NOT NULL

**Indexes** (1):
- `pms_inventory_transactions_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_inventory_transactions_pkey ON public.pms_inventory_transactions USING btree (id)
  ```

**RLS**: ❌ DISABLED

---

### `pms_label_generations`
**Row Count**: 0

**Columns** (21):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `receiving_event_id` | uuid | YES |  |  |
| `receiving_session_id` | uuid | YES |  |  |
| `label_type` | text | NO |  |  |
| `lines_included` | jsonb | NO |  |  |
| `total_labels_count` | integer | NO |  | enum: int4 |
| `status` | text | NO | 'pending'::text |  |
| `pdf_storage_path` | text | YES |  |  |
| `pdf_file_size_bytes` | bigint | YES |  | enum: int8 |
| `generation_completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `generation_errors` | jsonb | YES |  |  |
| `emailed_to` | text | YES |  |  |
| `emailed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `downloaded_count` | integer | YES | 0 | enum: int4 |
| `last_downloaded_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `requested_by` | uuid | NO |  |  |
| `requested_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `expires_at` | timestamp with time zone | YES | (now() + '90 days'::interval) | enum: timestamptz |
| `metadata` | jsonb | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `receiving_event_id` → `pms_receiving_events(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `receiving_session_id` → `pms_receiving_sessions(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_129830_17_not_null`: requested_by IS NOT NULL
- **CHECK** `2200_129830_18_not_null`: requested_at IS NOT NULL
- **CHECK** `2200_129830_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129830_21_not_null`: created_at IS NOT NULL
- **CHECK** `2200_129830_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129830_5_not_null`: label_type IS NOT NULL
- **CHECK** `2200_129830_6_not_null`: lines_included IS NOT NULL
- **CHECK** `2200_129830_7_not_null`: total_labels_count IS NOT NULL
- **CHECK** `2200_129830_8_not_null`: status IS NOT NULL
- **CHECK** `pms_label_generations_status_check`: (status = ANY (ARRAY['pending'::text, 'generating'::text, 'completed'::text, 'failed'::text]))

**Indexes** (5):
- `idx_label_generations_expires`
  ```sql
  CREATE INDEX idx_label_generations_expires ON public.pms_label_generations USING btree (expires_at) WHERE (status = 'completed'::text)
  ```
- `idx_label_generations_receiving_event`
  ```sql
  CREATE INDEX idx_label_generations_receiving_event ON public.pms_label_generations USING btree (receiving_event_id)
  ```
- `idx_label_generations_requested_by`
  ```sql
  CREATE INDEX idx_label_generations_requested_by ON public.pms_label_generations USING btree (requested_by, requested_at DESC)
  ```
- `idx_label_generations_status`
  ```sql
  CREATE INDEX idx_label_generations_status ON public.pms_label_generations USING btree (status) WHERE (status = ANY (ARRAY['pending'::text, 'generating'::text]))
  ```
- `pms_label_generations_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_label_generations_pkey ON public.pms_label_generations USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role can update label generations** (UPDATE)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can request labels** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (requested_by = auth.uid()))`
- **Users can view their label generations** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_maintenance_schedules`
**Row Count**: 0

**Columns** (22):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_id` | uuid | YES |  |  |
| `task_name` | text | NO |  |  |
| `description` | text | YES |  |  |
| `frequency` | text | NO |  |  |
| `frequency_days` | integer | YES |  | enum: int4 |
| `frequency_hours` | integer | YES |  | enum: int4 |
| `last_completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `last_completed_hours` | integer | YES |  | enum: int4 |
| `next_due_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `next_due_hours` | integer | YES |  | enum: int4 |
| `assigned_to` | uuid | YES |  |  |
| `priority` | text | YES | 'medium'::text |  |
| `status` | text | YES | 'active'::text |  |
| `deferral_reason` | text | YES |  |  |
| `deferred_by` | uuid | YES |  |  |
| `deferred_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_by` | uuid | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_144091_1_not_null`: id IS NOT NULL
- **CHECK** `2200_144091_20_not_null`: created_at IS NOT NULL
- **CHECK** `2200_144091_21_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_144091_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_144091_4_not_null`: task_name IS NOT NULL
- **CHECK** `2200_144091_6_not_null`: frequency IS NOT NULL

**Indexes** (5):
- `idx_maintenance_schedules_equipment`
  ```sql
  CREATE INDEX idx_maintenance_schedules_equipment ON public.pms_maintenance_schedules USING btree (equipment_id) WHERE (equipment_id IS NOT NULL)
  ```
- `idx_maintenance_schedules_next_due`
  ```sql
  CREATE INDEX idx_maintenance_schedules_next_due ON public.pms_maintenance_schedules USING btree (next_due_at) WHERE (next_due_at IS NOT NULL)
  ```
- `idx_maintenance_schedules_status`
  ```sql
  CREATE INDEX idx_maintenance_schedules_status ON public.pms_maintenance_schedules USING btree (status)
  ```
- `idx_maintenance_schedules_yacht`
  ```sql
  CREATE INDEX idx_maintenance_schedules_yacht ON public.pms_maintenance_schedules USING btree (yacht_id)
  ```
- `pms_maintenance_schedules_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_maintenance_schedules_pkey ON public.pms_maintenance_schedules USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (5):
- **Engineers can create schedules** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text, 'captain'::text])))`
- **Engineers can update schedules** (UPDATE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text, 'captain'::text])))`
- **Managers can delete schedules** (DELETE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Service role full access schedules** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can view schedules** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_notes`
**Row Count**: 5

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_id` | uuid | YES |  |  |
| `work_order_id` | uuid | YES |  |  |
| `fault_id` | uuid | YES |  |  |
| `text` | text | NO |  |  |
| `note_type` | USER-DEFINED | NO | 'general'::note_type | enum: note_type |
| `created_by` | uuid | NO |  |  |
| `attachments` | jsonb | YES | '[]'::jsonb |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `fault_id` → `pms_faults(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_28209_11_not_null`: created_at IS NOT NULL
- **CHECK** `2200_28209_12_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_28209_1_not_null`: id IS NOT NULL
- **CHECK** `2200_28209_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_28209_6_not_null`: text IS NOT NULL
- **CHECK** `2200_28209_7_not_null`: note_type IS NOT NULL
- **CHECK** `2200_28209_8_not_null`: created_by IS NOT NULL

**Indexes** (12):
- `idx_notes_created`
  ```sql
  CREATE INDEX idx_notes_created ON public.pms_notes USING btree (created_at DESC)
  ```
- `idx_notes_equipment`
  ```sql
  CREATE INDEX idx_notes_equipment ON public.pms_notes USING btree (equipment_id)
  ```
- `idx_notes_yacht`
  ```sql
  CREATE INDEX idx_notes_yacht ON public.pms_notes USING btree (yacht_id)
  ```
- `notes_created_at_idx`
  ```sql
  CREATE INDEX notes_created_at_idx ON public.pms_notes USING btree (yacht_id, created_at DESC)
  ```
- `notes_created_by_idx`
  ```sql
  CREATE INDEX notes_created_by_idx ON public.pms_notes USING btree (created_by)
  ```
- `notes_equipment_id_idx`
  ```sql
  CREATE INDEX notes_equipment_id_idx ON public.pms_notes USING btree (equipment_id)
  ```
- `notes_fault_id_idx`
  ```sql
  CREATE INDEX notes_fault_id_idx ON public.pms_notes USING btree (fault_id)
  ```
- `notes_note_type_idx`
  ```sql
  CREATE INDEX notes_note_type_idx ON public.pms_notes USING btree (yacht_id, note_type)
  ```
- `notes_pkey`
  ```sql
  CREATE UNIQUE INDEX notes_pkey ON public.pms_notes USING btree (id)
  ```
- `notes_text_gin_idx`
  ```sql
  CREATE INDEX notes_text_gin_idx ON public.pms_notes USING gin (text gin_trgm_ops)
  ```
- `notes_work_order_id_idx`
  ```sql
  CREATE INDEX notes_work_order_id_idx ON public.pms_notes USING btree (work_order_id)
  ```
- `notes_yacht_id_idx`
  ```sql
  CREATE INDEX notes_yacht_id_idx ON public.pms_notes USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role full access to notes** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can create notes** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Users can view own yacht notes** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (3):
- `notes_updated_at_trigger` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_notes_updated_at()
- `trg_note_insert_predictive` (AFTER INSERT)
  - Action: EXECUTE FUNCTION on_note_insert_notify_predictive()
- `trigger_notes_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at()

---

### `pms_orders`
**Row Count**: 3

**Columns** (29):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `order_number` | text | NO |  |  |
| `order_title` | text | YES |  |  |
| `supplier_name` | text | NO |  |  |
| `supplier_contact` | text | YES |  |  |
| `status` | text | NO | 'draft'::text |  |
| `estimated_total` | numeric | YES |  |  |
| `actual_total` | numeric | YES |  |  |
| `currency` | text | YES | 'USD'::text |  |
| `ordered_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `expected_delivery_date` | date | YES |  |  |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `approved_by` | uuid | YES |  |  |
| `approved_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `submitted_by` | uuid | YES |  |  |
| `submitted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `purchase_order_document_id` | uuid | YES |  |  |
| `invoice_document_id` | uuid | YES |  |  |
| `packing_slip_document_id` | uuid | YES |  |  |
| `notes` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_by` | uuid | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `invoice_document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `packing_slip_document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `purchase_order_document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `order_number`
- **CHECK** `2200_128939_1_not_null`: id IS NOT NULL
- **CHECK** `2200_128939_23_not_null`: created_by IS NOT NULL
- **CHECK** `2200_128939_24_not_null`: created_at IS NOT NULL
- **CHECK** `2200_128939_26_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_128939_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_128939_3_not_null`: order_number IS NOT NULL
- **CHECK** `2200_128939_5_not_null`: supplier_name IS NOT NULL
- **CHECK** `2200_128939_7_not_null`: status IS NOT NULL
- **CHECK** `pms_orders_status_check`: (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'acknowledged'::text, 'partially_shipped'::text, 'shipped'::text, 'partially_received'::text, 'completed'::text, 'cancelled'::text]))

**Indexes** (9):
- `idx_orders_number`
  ```sql
  CREATE INDEX idx_orders_number ON public.pms_orders USING btree (order_number)
  ```
- `idx_orders_ordered_at`
  ```sql
  CREATE INDEX idx_orders_ordered_at ON public.pms_orders USING btree (ordered_at DESC) WHERE (ordered_at IS NOT NULL)
  ```
- `idx_orders_status`
  ```sql
  CREATE INDEX idx_orders_status ON public.pms_orders USING btree (status) WHERE (deleted_at IS NULL)
  ```
- `idx_orders_supplier`
  ```sql
  CREATE INDEX idx_orders_supplier ON public.pms_orders USING btree (supplier_name) WHERE (deleted_at IS NULL)
  ```
- `idx_orders_yacht`
  ```sql
  CREATE INDEX idx_orders_yacht ON public.pms_orders USING btree (yacht_id)
  ```
- `idx_orders_yacht_ordered`
  ```sql
  CREATE INDEX idx_orders_yacht_ordered ON public.pms_orders USING btree (yacht_id, ordered_at DESC) WHERE ((ordered_at IS NOT NULL) AND (deleted_at IS NULL))
  ```
- `idx_orders_yacht_status`
  ```sql
  CREATE INDEX idx_orders_yacht_status ON public.pms_orders USING btree (yacht_id, status) WHERE (deleted_at IS NULL)
  ```
- `pms_orders_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_orders_pkey ON public.pms_orders USING btree (id)
  ```
- `pms_orders_yacht_order_number_unique`
  ```sql
  CREATE UNIQUE INDEX pms_orders_yacht_order_number_unique ON public.pms_orders USING btree (yacht_id, order_number)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **HOD can create and update orders** (ALL)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_hod(auth.uid(), yacht_id))`
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND is_hod(auth.uid(), yacht_id))`
- **Service role has full access to orders** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can view orders for their yacht** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_part_usage`
**Row Count**: 8

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `part_id` | uuid | NO |  |  |
| `quantity` | integer | NO |  | enum: int4 |
| `work_order_id` | uuid | YES |  |  |
| `equipment_id` | uuid | YES |  |  |
| `usage_reason` | text | NO |  |  |
| `notes` | text | YES |  |  |
| `used_by` | uuid | NO |  |  |
| `used_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `metadata` | jsonb | YES | '{}'::jsonb |  |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `part_id` → `pms_parts(id)` ON DELETE RESTRICT, ON UPDATE NO ACTION
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **CHECK** `2200_126667_10_not_null`: used_at IS NOT NULL
- **CHECK** `2200_126667_1_not_null`: id IS NOT NULL
- **CHECK** `2200_126667_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_126667_3_not_null`: part_id IS NOT NULL
- **CHECK** `2200_126667_4_not_null`: quantity IS NOT NULL
- **CHECK** `2200_126667_7_not_null`: usage_reason IS NOT NULL
- **CHECK** `2200_126667_9_not_null`: used_by IS NOT NULL
- **CHECK** `pms_part_usage_quantity_check`: (quantity > 0)
- **CHECK** `pms_part_usage_usage_reason_check`: (usage_reason = ANY (ARRAY['work_order'::text, 'preventive_maintenance'::text, 'emergency_repair'::text, 'testing'::text, 'other'::text]))

**Indexes** (10):
- `idx_pms_part_usage_equipment_id`
  ```sql
  CREATE INDEX idx_pms_part_usage_equipment_id ON public.pms_part_usage USING btree (equipment_id)
  ```
- `idx_pms_part_usage_part`
  ```sql
  CREATE INDEX idx_pms_part_usage_part ON public.pms_part_usage USING btree (part_id, used_at DESC)
  ```
- `idx_pms_part_usage_part_id`
  ```sql
  CREATE INDEX idx_pms_part_usage_part_id ON public.pms_part_usage USING btree (part_id, used_at DESC)
  ```
- `idx_pms_part_usage_used_at`
  ```sql
  CREATE INDEX idx_pms_part_usage_used_at ON public.pms_part_usage USING btree (used_at DESC)
  ```
- `idx_pms_part_usage_user`
  ```sql
  CREATE INDEX idx_pms_part_usage_user ON public.pms_part_usage USING btree (used_by, used_at DESC)
  ```
- `idx_pms_part_usage_wo`
  ```sql
  CREATE INDEX idx_pms_part_usage_wo ON public.pms_part_usage USING btree (work_order_id) WHERE (work_order_id IS NOT NULL)
  ```
- `idx_pms_part_usage_work_order_id`
  ```sql
  CREATE INDEX idx_pms_part_usage_work_order_id ON public.pms_part_usage USING btree (work_order_id)
  ```
- `idx_pms_part_usage_yacht`
  ```sql
  CREATE INDEX idx_pms_part_usage_yacht ON public.pms_part_usage USING btree (yacht_id, used_at DESC)
  ```
- `idx_pms_part_usage_yacht_id`
  ```sql
  CREATE INDEX idx_pms_part_usage_yacht_id ON public.pms_part_usage USING btree (yacht_id)
  ```
- `pms_part_usage_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_part_usage_pkey ON public.pms_part_usage USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Authenticated users can view usage** (SELECT)
  - Roles: ['authenticated']
  - USING: `true`
- **Service role full access** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **pms_part_usage_yacht_isolation** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id = (current_setting('app.current_yacht_id'::text))::uuid)`

---

### `pms_parts`
**Row Count**: 538

**Columns** (19):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `name` | text | NO |  |  |
| `part_number` | text | YES |  |  |
| `manufacturer` | text | YES |  |  |
| `description` | text | YES |  |  |
| `category` | text | YES |  |  |
| `model_compatibility` | jsonb | YES | '[]'::jsonb |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `search_embedding` | USER-DEFINED | YES |  | enum: vector |
| `embedding_text` | text | YES |  |  |
| `quantity_on_hand` | integer | NO | 0 | enum: int4 |
| `minimum_quantity` | integer | YES | 0 | enum: int4 |
| `unit` | text | YES | 'ea'::text |  |
| `location` | text | YES |  |  |
| `last_counted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `last_counted_by` | uuid | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18244_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18244_11_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_18244_14_not_null`: quantity_on_hand IS NOT NULL
- **CHECK** `2200_18244_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18244_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18244_3_not_null`: name IS NOT NULL
- **CHECK** `pms_parts_unit_check`: ((unit = ANY (ARRAY['ea'::text, 'kg'::text, 'g'::text, 'L'::text, 'mL'::text, 'm'::text, 'cm'::text, 'mm'::text, 'ft'::text, 'in'::text, 'm2'::text, 'm3'::text, 'gal'::text, 'qt'::text, 'pt'::text, 'oz'::text, 'lb'::text, 'box'::text, 'set'::text, 'pair'::text, 'roll'::text, 'sheet'::text])) OR (unit IS NULL))

**Indexes** (10):
- `idx_parts_category`
  ```sql
  CREATE INDEX idx_parts_category ON public.pms_parts USING btree (category)
  ```
- `idx_parts_manufacturer`
  ```sql
  CREATE INDEX idx_parts_manufacturer ON public.pms_parts USING btree (yacht_id, manufacturer) WHERE (manufacturer IS NOT NULL)
  ```
- `idx_parts_number`
  ```sql
  CREATE INDEX idx_parts_number ON public.pms_parts USING btree (yacht_id, part_number) WHERE (part_number IS NOT NULL)
  ```
- `idx_parts_part_number`
  ```sql
  CREATE INDEX idx_parts_part_number ON public.pms_parts USING btree (part_number)
  ```
- `idx_parts_yacht_id`
  ```sql
  CREATE INDEX idx_parts_yacht_id ON public.pms_parts USING btree (yacht_id)
  ```
- `idx_pms_parts_embedding`
  ```sql
  CREATE INDEX idx_pms_parts_embedding ON public.pms_parts USING ivfflat (search_embedding vector_cosine_ops) WITH (lists='100')
  ```
- `idx_pms_parts_low_stock`
  ```sql
  CREATE INDEX idx_pms_parts_low_stock ON public.pms_parts USING btree (yacht_id, quantity_on_hand, minimum_quantity) WHERE (quantity_on_hand <= minimum_quantity)
  ```
- `idx_pms_parts_part_number`
  ```sql
  CREATE INDEX idx_pms_parts_part_number ON public.pms_parts USING btree (yacht_id, part_number)
  ```
- `idx_pms_parts_yacht`
  ```sql
  CREATE INDEX idx_pms_parts_yacht ON public.pms_parts USING btree (yacht_id)
  ```
- `parts_pkey`
  ```sql
  CREATE UNIQUE INDEX parts_pkey ON public.pms_parts USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Engineers can manage parts** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text])))`
- **Service role full access parts** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view parts** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (1):
- `trg_prevent_embedding_overwrite` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION prevent_embedding_overwrite()

---

### `pms_purchase_order_items`
**Row Count**: 15

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `purchase_order_id` | uuid | NO |  |  |
| `part_id` | uuid | YES |  |  |
| `description` | text | NO |  |  |
| `quantity_ordered` | integer | NO |  | enum: int4 |
| `quantity_received` | integer | YES | 0 | enum: int4 |
| `unit_price` | numeric | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `part_id` → `pms_parts(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `purchase_order_id` → `pms_purchase_orders(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18364_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18364_11_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_18364_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18364_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18364_3_not_null`: purchase_order_id IS NOT NULL
- **CHECK** `2200_18364_5_not_null`: description IS NOT NULL
- **CHECK** `2200_18364_6_not_null`: quantity_ordered IS NOT NULL

**Indexes** (4):
- `idx_purchase_order_items_part_id`
  ```sql
  CREATE INDEX idx_purchase_order_items_part_id ON public.pms_purchase_order_items USING btree (part_id)
  ```
- `idx_purchase_order_items_po_id`
  ```sql
  CREATE INDEX idx_purchase_order_items_po_id ON public.pms_purchase_order_items USING btree (purchase_order_id)
  ```
- `idx_purchase_order_items_yacht_id`
  ```sql
  CREATE INDEX idx_purchase_order_items_yacht_id ON public.pms_purchase_order_items USING btree (yacht_id)
  ```
- `purchase_order_items_pkey`
  ```sql
  CREATE UNIQUE INDEX purchase_order_items_pkey ON public.pms_purchase_order_items USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Managers can manage PO items** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Service role full access purchase_order_items** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view PO items** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_purchase_orders`
**Row Count**: 9

**Columns** (17):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `supplier_id` | uuid | YES |  |  |
| `po_number` | text | YES |  |  |
| `status` | text | YES | 'draft'::text |  |
| `ordered_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `received_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `currency` | text | YES | 'USD'::text |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `approved_by` | uuid | YES |  |  |
| `approved_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `approval_notes` | text | YES |  |  |
| `received_by` | uuid | YES |  |  |
| `receiving_notes` | text | YES |  |  |
| `ordered_by` | uuid | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `supplier_id` → `pms_suppliers(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18338_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18338_11_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_18338_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18338_2_not_null`: yacht_id IS NOT NULL

**Indexes** (6):
- `idx_pms_purchase_orders_status`
  ```sql
  CREATE INDEX idx_pms_purchase_orders_status ON public.pms_purchase_orders USING btree (yacht_id, status)
  ```
- `idx_pms_purchase_orders_yacht`
  ```sql
  CREATE INDEX idx_pms_purchase_orders_yacht ON public.pms_purchase_orders USING btree (yacht_id)
  ```
- `idx_purchase_orders_status`
  ```sql
  CREATE INDEX idx_purchase_orders_status ON public.pms_purchase_orders USING btree (status)
  ```
- `idx_purchase_orders_supplier_id`
  ```sql
  CREATE INDEX idx_purchase_orders_supplier_id ON public.pms_purchase_orders USING btree (supplier_id)
  ```
- `idx_purchase_orders_yacht_id`
  ```sql
  CREATE INDEX idx_purchase_orders_yacht_id ON public.pms_purchase_orders USING btree (yacht_id)
  ```
- `purchase_orders_pkey`
  ```sql
  CREATE UNIQUE INDEX purchase_orders_pkey ON public.pms_purchase_orders USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Managers can manage purchase orders** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Service role full access purchase_orders** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view purchase orders** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_receiving_attachments`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `receiving_event_id` | uuid | NO |  |  |
| `receiving_line_item_id` | uuid | YES |  |  |
| `document_id` | uuid | NO |  |  |
| `attachment_type` | text | NO |  |  |
| `description` | text | YES |  |  |
| `attached_by` | uuid | NO |  |  |
| `attached_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `document_id` → `doc_metadata(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `receiving_event_id` → `pms_receiving_events(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `receiving_line_item_id` → `pms_receiving_line_items(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_129455_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129455_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129455_3_not_null`: receiving_event_id IS NOT NULL
- **CHECK** `2200_129455_5_not_null`: document_id IS NOT NULL
- **CHECK** `2200_129455_6_not_null`: attachment_type IS NOT NULL
- **CHECK** `2200_129455_8_not_null`: attached_by IS NOT NULL
- **CHECK** `2200_129455_9_not_null`: attached_at IS NOT NULL
- **CHECK** `pms_receiving_attachments_attachment_type_check`: (attachment_type = ANY (ARRAY['packing_slip'::text, 'condition_photo'::text, 'damage_photo'::text, 'invoice'::text, 'delivery_note'::text, 'other'::text]))

**Indexes** (5):
- `idx_receiving_attachments_document`
  ```sql
  CREATE INDEX idx_receiving_attachments_document ON public.pms_receiving_attachments USING btree (document_id)
  ```
- `idx_receiving_attachments_event`
  ```sql
  CREATE INDEX idx_receiving_attachments_event ON public.pms_receiving_attachments USING btree (receiving_event_id)
  ```
- `idx_receiving_attachments_line`
  ```sql
  CREATE INDEX idx_receiving_attachments_line ON public.pms_receiving_attachments USING btree (receiving_line_item_id) WHERE (receiving_line_item_id IS NOT NULL)
  ```
- `idx_receiving_attachments_type`
  ```sql
  CREATE INDEX idx_receiving_attachments_type ON public.pms_receiving_attachments USING btree (attachment_type)
  ```
- `pms_receiving_attachments_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_receiving_attachments_pkey ON public.pms_receiving_attachments USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role has full access to attachments** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can create attachments** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (attached_by = auth.uid()))`
- **Users can view attachments for their yacht** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (2):
- `trg_enforce_attachment_consistency` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION enforce_receiving_attachment_consistency()
- `trg_enforce_attachment_consistency` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION enforce_receiving_attachment_consistency()

---

### `pms_receiving_draft_lines`
**Row Count**: 0

**Columns** (32):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `session_id` | uuid | NO |  |  |
| `source_image_id` | uuid | NO |  |  |
| `line_sequence` | integer | NO |  | enum: int4 |
| `raw_text` | text | NO |  |  |
| `extracted_part_name` | text | YES |  |  |
| `extracted_part_number` | text | YES |  |  |
| `extracted_quantity` | numeric | YES |  |  |
| `extracted_unit` | text | YES |  |  |
| `extracted_description` | text | YES |  |  |
| `extracted_manufacturer` | text | YES |  |  |
| `match_status` | text | NO | 'unmatched'::text |  |
| `suggested_part_id` | uuid | YES |  |  |
| `suggested_shopping_list_item_id` | uuid | YES |  |  |
| `alternative_matches` | jsonb | YES |  |  |
| `is_verified` | boolean | NO | false | enum: bool |
| `verified_by` | uuid | YES |  |  |
| `verified_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `resolved_part_id` | uuid | YES |  |  |
| `resolved_shopping_list_item_id` | uuid | YES |  |  |
| `resolved_quantity` | numeric | YES |  |  |
| `resolved_unit` | text | YES |  |  |
| `resolved_disposition` | text | YES |  |  |
| `resolution_notes` | text | YES |  |  |
| `is_discrepancy` | boolean | YES | false | enum: bool |
| `discrepancy_type` | text | YES |  |  |
| `discrepancy_notes` | text | YES |  |  |
| `creates_candidate_part` | boolean | YES | false | enum: bool |
| `created_candidate_part_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `created_candidate_part_id` → `pms_parts(id)` ON DELETE NO ACTION, ON UPDATE NO ACTION
- **FK**: `resolved_part_id` → `pms_parts(id)` ON DELETE NO ACTION, ON UPDATE NO ACTION
- **FK**: `resolved_shopping_list_item_id` → `pms_shopping_list_items(id)` ON DELETE NO ACTION, ON UPDATE NO ACTION
- **FK**: `session_id` → `pms_receiving_sessions(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `source_image_id` → `pms_image_uploads(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `suggested_part_id` → `pms_parts(id)` ON DELETE NO ACTION, ON UPDATE NO ACTION
- **FK**: `suggested_shopping_list_item_id` → `pms_shopping_list_items(id)` ON DELETE NO ACTION, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_129765_13_not_null`: match_status IS NOT NULL
- **CHECK** `2200_129765_17_not_null`: is_verified IS NOT NULL
- **CHECK** `2200_129765_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129765_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129765_31_not_null`: created_at IS NOT NULL
- **CHECK** `2200_129765_32_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_129765_3_not_null`: session_id IS NOT NULL
- **CHECK** `2200_129765_4_not_null`: source_image_id IS NOT NULL
- **CHECK** `2200_129765_5_not_null`: line_sequence IS NOT NULL
- **CHECK** `2200_129765_6_not_null`: raw_text IS NOT NULL
- **CHECK** `pms_receiving_draft_lines_match_status_check`: (match_status = ANY (ARRAY['matched_order'::text, 'matched_part'::text, 'matched_shopping_list'::text, 'unmatched'::text, 'ignored'::text]))

**Indexes** (6):
- `idx_draft_lines_image`
  ```sql
  CREATE INDEX idx_draft_lines_image ON public.pms_receiving_draft_lines USING btree (source_image_id)
  ```
- `idx_draft_lines_match_status`
  ```sql
  CREATE INDEX idx_draft_lines_match_status ON public.pms_receiving_draft_lines USING btree (match_status) WHERE (is_verified = false)
  ```
- `idx_draft_lines_session`
  ```sql
  CREATE INDEX idx_draft_lines_session ON public.pms_receiving_draft_lines USING btree (session_id, line_sequence)
  ```
- `idx_draft_lines_unverified`
  ```sql
  CREATE INDEX idx_draft_lines_unverified ON public.pms_receiving_draft_lines USING btree (session_id) WHERE (is_verified = false)
  ```
- `idx_draft_lines_verified`
  ```sql
  CREATE INDEX idx_draft_lines_verified ON public.pms_receiving_draft_lines USING btree (verified_by, verified_at DESC) WHERE (is_verified = true)
  ```
- `pms_receiving_draft_lines_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_receiving_draft_lines_pkey ON public.pms_receiving_draft_lines USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role can manage draft lines** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can verify draft lines** (UPDATE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND (is_verified = false))`
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (verified_by = auth.uid()))`
- **Users can view their yacht's draft lines** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (1):
- `trg_draft_lines_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at_column()

---

### `pms_receiving_events`
**Row Count**: 3

**Columns** (21):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `receiving_number` | text | NO |  |  |
| `order_id` | uuid | YES |  |  |
| `received_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `received_by` | uuid | NO |  |  |
| `location` | text | YES |  |  |
| `status` | text | NO | 'in_progress'::text |  |
| `delivery_method` | text | YES |  |  |
| `tracking_number` | text | YES |  |  |
| `notes` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |
| `is_locked` | boolean | NO | false | enum: bool |
| `receiving_session_id` | uuid | YES |  |  |
| `was_camera_initiated` | boolean | YES | false | enum: bool |

**Constraints**:
- **PK**: `id`
- **FK**: `order_id` → `pms_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `receiving_session_id` → `pms_receiving_sessions(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `receiving_number`
- **CHECK** `2200_129005_15_not_null`: created_at IS NOT NULL
- **CHECK** `2200_129005_17_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_129005_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129005_21_not_null`: is_locked IS NOT NULL
- **CHECK** `2200_129005_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129005_3_not_null`: receiving_number IS NOT NULL
- **CHECK** `2200_129005_5_not_null`: received_at IS NOT NULL
- **CHECK** `2200_129005_6_not_null`: received_by IS NOT NULL
- **CHECK** `2200_129005_8_not_null`: status IS NOT NULL
- **CHECK** `pms_receiving_events_status_check`: (status = ANY (ARRAY['in_progress'::text, 'completed'::text, 'partial'::text, 'discrepancy'::text]))

**Indexes** (8):
- `idx_receiving_events_camera_initiated`
  ```sql
  CREATE INDEX idx_receiving_events_camera_initiated ON public.pms_receiving_events USING btree (yacht_id) WHERE (was_camera_initiated = true)
  ```
- `idx_receiving_events_session`
  ```sql
  CREATE INDEX idx_receiving_events_session ON public.pms_receiving_events USING btree (receiving_session_id) WHERE (receiving_session_id IS NOT NULL)
  ```
- `idx_receiving_order`
  ```sql
  CREATE INDEX idx_receiving_order ON public.pms_receiving_events USING btree (order_id) WHERE (order_id IS NOT NULL)
  ```
- `idx_receiving_received_at`
  ```sql
  CREATE INDEX idx_receiving_received_at ON public.pms_receiving_events USING btree (received_at DESC)
  ```
- `idx_receiving_status`
  ```sql
  CREATE INDEX idx_receiving_status ON public.pms_receiving_events USING btree (status) WHERE (deleted_at IS NULL)
  ```
- `idx_receiving_yacht`
  ```sql
  CREATE INDEX idx_receiving_yacht ON public.pms_receiving_events USING btree (yacht_id)
  ```
- `pms_receiving_events_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_receiving_events_pkey ON public.pms_receiving_events USING btree (id)
  ```
- `pms_receiving_events_yacht_receiving_number_unique`
  ```sql
  CREATE UNIQUE INDEX pms_receiving_events_yacht_receiving_number_unique ON public.pms_receiving_events USING btree (yacht_id, receiving_number)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Authorized users can create receiving events** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (received_by = auth.uid()))`
- **Receiver can update own receiving event** (UPDATE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND (((received_by = auth.uid()) AND (is_locked = false)) OR is_hod(auth.uid(), yacht_id)))`
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Service role has full access to receiving events** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can view receiving events for their yacht** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (1):
- `trg_auto_lock_receiving_event` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION auto_lock_receiving_event()

---

### `pms_receiving_line_items`
**Row Count**: 3

**Columns** (37):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `receiving_event_id` | uuid | NO |  |  |
| `shopping_list_item_id` | uuid | YES |  |  |
| `part_id` | uuid | YES |  |  |
| `part_name` | text | NO |  |  |
| `part_number` | text | YES |  |  |
| `manufacturer` | text | YES |  |  |
| `quantity_expected` | numeric | YES |  |  |
| `quantity_received` | numeric | NO |  |  |
| `quantity_accepted` | numeric | NO |  |  |
| `quantity_rejected` | numeric | YES | 0 |  |
| `unit` | text | YES |  |  |
| `disposition` | text | NO |  |  |
| `disposition_notes` | text | YES |  |  |
| `installed_immediately` | boolean | YES | false | enum: bool |
| `installed_to_equipment_id` | uuid | YES |  |  |
| `installed_to_work_order_id` | uuid | YES |  |  |
| `installed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `installed_by` | uuid | YES |  |  |
| `unit_price` | numeric | YES |  |  |
| `line_total` | numeric | YES |  |  |
| `serial_numbers` | ARRAY | YES |  | enum: _text |
| `batch_lot_number` | text | YES |  |  |
| `expiration_date` | date | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `verified_by` | uuid | YES |  |  |
| `verified_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `is_verified` | boolean | NO | false | enum: bool |
| `received_by` | uuid | YES |  |  |
| `draft_line_id` | uuid | YES |  |  |
| `verification_notes` | text | YES |  |  |
| `human_verified_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `human_verified_by` | uuid | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `draft_line_id` → `pms_receiving_draft_lines(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `installed_to_equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `installed_to_work_order_id` → `pms_work_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `part_id` → `pms_parts(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `receiving_event_id` → `pms_receiving_events(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `shopping_list_item_id` → `pms_shopping_list_items(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_129138_10_not_null`: quantity_received IS NOT NULL
- **CHECK** `2200_129138_11_not_null`: quantity_accepted IS NOT NULL
- **CHECK** `2200_129138_14_not_null`: disposition IS NOT NULL
- **CHECK** `2200_129138_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129138_28_not_null`: created_at IS NOT NULL
- **CHECK** `2200_129138_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129138_30_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_129138_33_not_null`: is_verified IS NOT NULL
- **CHECK** `2200_129138_3_not_null`: receiving_event_id IS NOT NULL
- **CHECK** `2200_129138_6_not_null`: part_name IS NOT NULL
- **CHECK** `pms_receiving_line_items_check`: ((quantity_accepted >= (0)::numeric) AND (quantity_accepted <= quantity_received))
- **CHECK** `pms_receiving_line_items_disposition_check`: (disposition = ANY (ARRAY['accepted'::text, 'accepted_with_notes'::text, 'rejected'::text, 'partial_accept'::text, 'missing'::text, 'extra'::text, 'incorrect'::text]))
- **CHECK** `pms_receiving_line_items_quantity_received_check`: (quantity_received >= (0)::numeric)
- **CHECK** `pms_receiving_line_items_quantity_rejected_check`: (quantity_rejected >= (0)::numeric)
- **CHECK** `pms_receiving_line_items_unit_check`: ((unit = ANY (ARRAY['ea'::text, 'kg'::text, 'g'::text, 'L'::text, 'mL'::text, 'm'::text, 'cm'::text, 'mm'::text, 'ft'::text, 'in'::text, 'm2'::text, 'm3'::text, 'gal'::text, 'qt'::text, 'pt'::text, 'oz'::text, 'lb'::text, 'box'::text, 'set'::text, 'pair'::text, 'roll'::text, 'sheet'::text])) OR (unit IS NULL))

**Indexes** (9):
- `idx_receiving_line_items_draft`
  ```sql
  CREATE INDEX idx_receiving_line_items_draft ON public.pms_receiving_line_items USING btree (draft_line_id) WHERE (draft_line_id IS NOT NULL)
  ```
- `idx_receiving_lines_disposition`
  ```sql
  CREATE INDEX idx_receiving_lines_disposition ON public.pms_receiving_line_items USING btree (disposition)
  ```
- `idx_receiving_lines_event`
  ```sql
  CREATE INDEX idx_receiving_lines_event ON public.pms_receiving_line_items USING btree (receiving_event_id)
  ```
- `idx_receiving_lines_part`
  ```sql
  CREATE INDEX idx_receiving_lines_part ON public.pms_receiving_line_items USING btree (part_id) WHERE (part_id IS NOT NULL)
  ```
- `idx_receiving_lines_shopping_item`
  ```sql
  CREATE INDEX idx_receiving_lines_shopping_item ON public.pms_receiving_line_items USING btree (shopping_list_item_id) WHERE (shopping_list_item_id IS NOT NULL)
  ```
- `idx_receiving_lines_yacht`
  ```sql
  CREATE INDEX idx_receiving_lines_yacht ON public.pms_receiving_line_items USING btree (yacht_id)
  ```
- `idx_receiving_lines_yacht_event`
  ```sql
  CREATE INDEX idx_receiving_lines_yacht_event ON public.pms_receiving_line_items USING btree (yacht_id, receiving_event_id)
  ```
- `idx_receiving_lines_yacht_shopping`
  ```sql
  CREATE INDEX idx_receiving_lines_yacht_shopping ON public.pms_receiving_line_items USING btree (yacht_id, shopping_list_item_id) WHERE (shopping_list_item_id IS NOT NULL)
  ```
- `pms_receiving_line_items_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_receiving_line_items_pkey ON public.pms_receiving_line_items USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Receiver or HOD can update receiving line items** (UPDATE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND (((received_by = auth.uid()) AND (EXISTS ( SELECT 1
   FROM pms_receiving_events re
  WHERE ((re.id = pms_receiving_line_items.receiving_event_id) AND (re.is_locked = false))))) OR is_hod(auth.uid(), yacht_id)))`
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Service role has full access to receiving line items** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can create receiving line items** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Users can view receiving line items for their yacht** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (6):
- `trg_enforce_receiving_verification` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION enforce_receiving_verification()
- `trg_enforce_receiving_verification` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION enforce_receiving_verification()
- `trg_set_receiving_line_receiver` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION set_receiving_line_receiver()
- `trg_update_shopping_quantities_on_receiving` (AFTER INSERT)
  - Action: EXECUTE FUNCTION update_shopping_list_quantities()
- `trg_update_shopping_quantities_on_receiving` (AFTER DELETE)
  - Action: EXECUTE FUNCTION update_shopping_list_quantities()
- `trg_update_shopping_quantities_on_receiving` (AFTER UPDATE)
  - Action: EXECUTE FUNCTION update_shopping_list_quantities()

---

### `pms_receiving_sessions`
**Row Count**: 0

**Columns** (27):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `session_number` | text | NO |  |  |
| `status` | text | NO | 'draft'::text |  |
| `order_id` | uuid | YES |  |  |
| `order_matched_automatically` | boolean | YES | false | enum: bool |
| `session_type` | text | NO |  |  |
| `supplier_name` | text | YES |  |  |
| `tracking_number` | text | YES |  |  |
| `expected_items_count` | integer | YES |  | enum: int4 |
| `extraction_completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `reconciliation_completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `verification_completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `committed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `cancelled_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `received_to_inventory_count` | integer | YES | 0 | enum: int4 |
| `installed_immediately_count` | integer | YES | 0 | enum: int4 |
| `discrepancy_count` | integer | YES | 0 | enum: int4 |
| `unresolved_lines_count` | integer | YES | 0 | enum: int4 |
| `receiving_event_id` | uuid | YES |  |  |
| `created_by` | uuid | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `committed_by` | uuid | YES |  |  |
| `cancelled_by` | uuid | YES |  |  |
| `cancellation_reason` | text | YES |  |  |
| `metadata` | jsonb | YES |  |  |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `order_id` → `pms_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `receiving_event_id` → `pms_receiving_events(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `session_number`
- **CHECK** `2200_129681_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129681_21_not_null`: created_by IS NOT NULL
- **CHECK** `2200_129681_22_not_null`: created_at IS NOT NULL
- **CHECK** `2200_129681_27_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_129681_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129681_3_not_null`: session_number IS NOT NULL
- **CHECK** `2200_129681_4_not_null`: status IS NOT NULL
- **CHECK** `2200_129681_7_not_null`: session_type IS NOT NULL
- **CHECK** `pms_receiving_sessions_status_check`: (status = ANY (ARRAY['draft'::text, 'reconciling'::text, 'verifying'::text, 'committed'::text, 'cancelled'::text]))

**Indexes** (6):
- `idx_receiving_sessions_created_by`
  ```sql
  CREATE INDEX idx_receiving_sessions_created_by ON public.pms_receiving_sessions USING btree (created_by, created_at DESC)
  ```
- `idx_receiving_sessions_order`
  ```sql
  CREATE INDEX idx_receiving_sessions_order ON public.pms_receiving_sessions USING btree (order_id) WHERE (order_id IS NOT NULL)
  ```
- `idx_receiving_sessions_status`
  ```sql
  CREATE INDEX idx_receiving_sessions_status ON public.pms_receiving_sessions USING btree (status) WHERE ((status <> 'committed'::text) AND (status <> 'cancelled'::text))
  ```
- `idx_receiving_sessions_yacht`
  ```sql
  CREATE INDEX idx_receiving_sessions_yacht ON public.pms_receiving_sessions USING btree (yacht_id, created_at DESC)
  ```
- `pms_receiving_sessions_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_receiving_sessions_pkey ON public.pms_receiving_sessions USING btree (id)
  ```
- `pms_receiving_sessions_session_number_key`
  ```sql
  CREATE UNIQUE INDEX pms_receiving_sessions_session_number_key ON public.pms_receiving_sessions USING btree (session_number)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Service role can update sessions** (UPDATE)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can create sessions for their yacht** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (created_by = auth.uid()))`
- **Users can update own draft sessions** (UPDATE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND (created_by = auth.uid()) AND (status = ANY (ARRAY['draft'::text, 'reconciling'::text, 'verifying'::text])))`
- **Users can view their yacht's sessions** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (3):
- `trg_enforce_session_state` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION enforce_receiving_session_state_transitions()
- `trg_generate_session_number` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION generate_receiving_session_number()
- `trg_receiving_sessions_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at_column()

---

### `pms_service_contracts`
**Row Count**: 0

**Columns** (23):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `contract_name` | text | NO |  |  |
| `vendor_name` | text | NO |  |  |
| `vendor_id` | uuid | YES |  |  |
| `contract_type` | text | YES |  |  |
| `contract_number` | text | YES |  |  |
| `start_date` | date | YES |  |  |
| `end_date` | date | YES |  |  |
| `value` | numeric | YES |  |  |
| `currency` | text | YES | 'USD'::text |  |
| `coverage_details` | text | YES |  |  |
| `equipment_ids` | ARRAY | YES | '{}'::uuid[] | enum: _uuid |
| `document_id` | uuid | YES |  |  |
| `status` | text | YES | 'active'::text |  |
| `auto_renew` | boolean | YES | false | enum: bool |
| `renewal_notice_days` | integer | YES | 30 | enum: int4 |
| `claims_count` | integer | YES | 0 | enum: int4 |
| `notes` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_by` | uuid | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `vendor_id` → `pms_suppliers(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_144186_1_not_null`: id IS NOT NULL
- **CHECK** `2200_144186_21_not_null`: created_at IS NOT NULL
- **CHECK** `2200_144186_22_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_144186_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_144186_3_not_null`: contract_name IS NOT NULL
- **CHECK** `2200_144186_4_not_null`: vendor_name IS NOT NULL

**Indexes** (6):
- `idx_contracts_end_date`
  ```sql
  CREATE INDEX idx_contracts_end_date ON public.pms_service_contracts USING btree (end_date) WHERE (end_date IS NOT NULL)
  ```
- `idx_contracts_status`
  ```sql
  CREATE INDEX idx_contracts_status ON public.pms_service_contracts USING btree (status)
  ```
- `idx_contracts_type`
  ```sql
  CREATE INDEX idx_contracts_type ON public.pms_service_contracts USING btree (contract_type)
  ```
- `idx_contracts_vendor`
  ```sql
  CREATE INDEX idx_contracts_vendor ON public.pms_service_contracts USING btree (vendor_id) WHERE (vendor_id IS NOT NULL)
  ```
- `idx_contracts_yacht`
  ```sql
  CREATE INDEX idx_contracts_yacht ON public.pms_service_contracts USING btree (yacht_id)
  ```
- `pms_service_contracts_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_service_contracts_pkey ON public.pms_service_contracts USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (5):
- **Managers can delete contracts** (DELETE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Officers can create contracts** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text, 'captain'::text, 'purser'::text])))`
- **Officers can update contracts** (UPDATE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text, 'captain'::text, 'purser'::text])))`
- **Service role full access contracts** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can view contracts** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_shopping_list_items`
**Row Count**: 34

**Columns** (45):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `part_id` | uuid | YES |  |  |
| `part_name` | text | NO |  |  |
| `part_number` | text | YES |  |  |
| `manufacturer` | text | YES |  |  |
| `is_candidate_part` | boolean | NO | false | enum: bool |
| `quantity_requested` | numeric | NO |  |  |
| `quantity_approved` | numeric | YES |  |  |
| `quantity_ordered` | numeric | YES |  |  |
| `quantity_received` | numeric | YES | 0 |  |
| `quantity_installed` | numeric | YES | 0 |  |
| `unit` | text | YES |  |  |
| `preferred_supplier` | text | YES |  |  |
| `estimated_unit_price` | numeric | YES |  |  |
| `status` | text | NO | 'candidate'::text |  |
| `source_type` | text | NO |  |  |
| `source_work_order_id` | uuid | YES |  |  |
| `source_receiving_id` | uuid | YES |  |  |
| `source_notes` | text | YES |  |  |
| `order_id` | uuid | YES |  |  |
| `order_line_number` | integer | YES |  | enum: int4 |
| `approved_by` | uuid | YES |  |  |
| `approved_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `approval_notes` | text | YES |  |  |
| `rejected_by` | uuid | YES |  |  |
| `rejected_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `rejection_reason` | text | YES |  |  |
| `fulfilled_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `installed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `installed_to_equipment_id` | uuid | YES |  |  |
| `urgency` | text | YES |  |  |
| `required_by_date` | date | YES |  |  |
| `created_by` | uuid | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `rejection_notes` | text | YES |  |  |
| `candidate_promoted_to_part_id` | uuid | YES |  |  |
| `promoted_by` | uuid | YES |  |  |
| `promoted_at` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `candidate_promoted_to_part_id` → `pms_parts(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `installed_to_equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `order_id` → `pms_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `part_id` → `pms_parts(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `source_receiving_id` → `pms_receiving_events(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `source_work_order_id` → `pms_work_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_129052_16_not_null`: status IS NOT NULL
- **CHECK** `2200_129052_17_not_null`: source_type IS NOT NULL
- **CHECK** `2200_129052_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129052_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129052_34_not_null`: created_by IS NOT NULL
- **CHECK** `2200_129052_35_not_null`: created_at IS NOT NULL
- **CHECK** `2200_129052_37_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_129052_4_not_null`: part_name IS NOT NULL
- **CHECK** `2200_129052_7_not_null`: is_candidate_part IS NOT NULL
- **CHECK** `2200_129052_8_not_null`: quantity_requested IS NOT NULL
- **CHECK** `check_promotion_consistency`: (((candidate_promoted_to_part_id IS NULL) AND (promoted_by IS NULL) AND (promoted_at IS NULL)) OR ((candidate_promoted_to_part_id IS NOT NULL) AND (promoted_by IS NOT NULL) AND (promoted_at IS NOT NULL)))
- **CHECK** `check_quantities`: ((quantity_received <= COALESCE(quantity_ordered, quantity_requested)) AND (quantity_installed <= COALESCE(quantity_ordered, quantity_requested)))
- **CHECK** `pms_shopping_list_items_quantity_approved_check`: (quantity_approved > (0)::numeric)
- **CHECK** `pms_shopping_list_items_quantity_installed_check`: (quantity_installed >= (0)::numeric)
- **CHECK** `pms_shopping_list_items_quantity_ordered_check`: (quantity_ordered > (0)::numeric)
- **CHECK** `pms_shopping_list_items_quantity_received_check`: (quantity_received >= (0)::numeric)
- **CHECK** `pms_shopping_list_items_quantity_requested_check`: (quantity_requested > (0)::numeric)
- **CHECK** `pms_shopping_list_items_source_type_check`: (source_type = ANY (ARRAY['inventory_low'::text, 'inventory_oos'::text, 'work_order_usage'::text, 'receiving_missing'::text, 'receiving_damaged'::text, 'manual_add'::text]))
- **CHECK** `pms_shopping_list_items_status_check`: (status = ANY (ARRAY['candidate'::text, 'under_review'::text, 'approved'::text, 'ordered'::text, 'partially_fulfilled'::text, 'fulfilled'::text, 'installed'::text]))
- **CHECK** `pms_shopping_list_items_unit_check`: ((unit = ANY (ARRAY['ea'::text, 'kg'::text, 'g'::text, 'L'::text, 'mL'::text, 'm'::text, 'cm'::text, 'mm'::text, 'ft'::text, 'in'::text, 'm2'::text, 'm3'::text, 'gal'::text, 'qt'::text, 'pt'::text, 'oz'::text, 'lb'::text, 'box'::text, 'set'::text, 'pair'::text, 'roll'::text, 'sheet'::text])) OR (unit IS NULL))
- **CHECK** `pms_shopping_list_items_urgency_check`: (urgency = ANY (ARRAY['low'::text, 'normal'::text, 'high'::text, 'critical'::text]))

**Indexes** (12):
- `idx_shopping_list_created`
  ```sql
  CREATE INDEX idx_shopping_list_created ON public.pms_shopping_list_items USING btree (created_at DESC)
  ```
- `idx_shopping_list_order`
  ```sql
  CREATE INDEX idx_shopping_list_order ON public.pms_shopping_list_items USING btree (order_id) WHERE (order_id IS NOT NULL)
  ```
- `idx_shopping_list_part`
  ```sql
  CREATE INDEX idx_shopping_list_part ON public.pms_shopping_list_items USING btree (part_id) WHERE (part_id IS NOT NULL)
  ```
- `idx_shopping_list_source_wo`
  ```sql
  CREATE INDEX idx_shopping_list_source_wo ON public.pms_shopping_list_items USING btree (source_work_order_id) WHERE (source_work_order_id IS NOT NULL)
  ```
- `idx_shopping_list_status`
  ```sql
  CREATE INDEX idx_shopping_list_status ON public.pms_shopping_list_items USING btree (status) WHERE (deleted_at IS NULL)
  ```
- `idx_shopping_list_unpromoted_candidates`
  ```sql
  CREATE INDEX idx_shopping_list_unpromoted_candidates ON public.pms_shopping_list_items USING btree (yacht_id, is_candidate_part) WHERE ((is_candidate_part = true) AND (candidate_promoted_to_part_id IS NULL) AND (deleted_at IS NULL))
  ```
- `idx_shopping_list_urgency`
  ```sql
  CREATE INDEX idx_shopping_list_urgency ON public.pms_shopping_list_items USING btree (urgency) WHERE ((urgency = ANY (ARRAY['high'::text, 'critical'::text])) AND (deleted_at IS NULL))
  ```
- `idx_shopping_list_yacht`
  ```sql
  CREATE INDEX idx_shopping_list_yacht ON public.pms_shopping_list_items USING btree (yacht_id)
  ```
- `idx_shopping_list_yacht_created`
  ```sql
  CREATE INDEX idx_shopping_list_yacht_created ON public.pms_shopping_list_items USING btree (yacht_id, created_at DESC) WHERE (deleted_at IS NULL)
  ```
- `idx_shopping_list_yacht_order`
  ```sql
  CREATE INDEX idx_shopping_list_yacht_order ON public.pms_shopping_list_items USING btree (yacht_id, order_id) WHERE ((order_id IS NOT NULL) AND (deleted_at IS NULL))
  ```
- `idx_shopping_list_yacht_status`
  ```sql
  CREATE INDEX idx_shopping_list_yacht_status ON public.pms_shopping_list_items USING btree (yacht_id, status) WHERE (deleted_at IS NULL)
  ```
- `pms_shopping_list_items_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_shopping_list_items_pkey ON public.pms_shopping_list_items USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **HOD can update shopping list items** (UPDATE)
  - Roles: ['authenticated']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_hod(auth.uid(), yacht_id))`
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Service role has full access to shopping list** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can create shopping list items** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (created_by = auth.uid()) AND (status = 'candidate'::text))`
- **Users can view shopping list items for their yacht** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (3):
- `trg_enforce_shopping_list_edit_rules` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION enforce_shopping_list_edit_rules()
- `trg_log_shopping_list_state_change` (AFTER INSERT)
  - Action: EXECUTE FUNCTION log_shopping_list_state_change()
- `trg_log_shopping_list_state_change` (AFTER UPDATE)
  - Action: EXECUTE FUNCTION log_shopping_list_state_change()

---

### `pms_shopping_list_state_history`
**Row Count**: 36

**Columns** (13):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `yacht_id` | uuid | NO |  |  |
| `shopping_list_item_id` | uuid | NO |  |  |
| `previous_state` | text | YES |  |  |
| `new_state` | text | NO |  |  |
| `transition_reason` | text | YES |  |  |
| `transition_notes` | text | YES |  |  |
| `changed_by` | uuid | NO |  |  |
| `changed_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `related_order_id` | uuid | YES |  |  |
| `related_receiving_event_id` | uuid | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `related_order_id` → `pms_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `related_receiving_event_id` → `pms_receiving_events(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `shopping_list_item_id` → `pms_shopping_list_items(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_129282_13_not_null`: created_at IS NOT NULL
- **CHECK** `2200_129282_1_not_null`: id IS NOT NULL
- **CHECK** `2200_129282_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_129282_3_not_null`: shopping_list_item_id IS NOT NULL
- **CHECK** `2200_129282_5_not_null`: new_state IS NOT NULL
- **CHECK** `2200_129282_8_not_null`: changed_by IS NOT NULL
- **CHECK** `2200_129282_9_not_null`: changed_at IS NOT NULL

**Indexes** (5):
- `idx_shopping_state_changed_at`
  ```sql
  CREATE INDEX idx_shopping_state_changed_at ON public.pms_shopping_list_state_history USING btree (changed_at DESC)
  ```
- `idx_shopping_state_changed_by`
  ```sql
  CREATE INDEX idx_shopping_state_changed_by ON public.pms_shopping_list_state_history USING btree (changed_by)
  ```
- `idx_shopping_state_item`
  ```sql
  CREATE INDEX idx_shopping_state_item ON public.pms_shopping_list_state_history USING btree (shopping_list_item_id)
  ```
- `idx_shopping_state_yacht`
  ```sql
  CREATE INDEX idx_shopping_state_yacht ON public.pms_shopping_list_state_history USING btree (yacht_id)
  ```
- `pms_shopping_list_state_history_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_shopping_list_state_history_pkey ON public.pms_shopping_list_state_history USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role can insert state history** (INSERT)
  - Roles: ['service_role']
  - WITH CHECK: `true`
- **Users can view state history for their yacht** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_suppliers`
**Row Count**: 50

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `name` | text | NO |  |  |
| `contact_name` | text | YES |  |  |
| `email` | text | YES |  |  |
| `phone` | text | YES |  |  |
| `address` | jsonb | YES | '{}'::jsonb |  |
| `preferred` | boolean | YES | false | enum: bool |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18318_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18318_11_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_18318_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18318_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18318_3_not_null`: name IS NOT NULL

**Indexes** (4):
- `idx_pms_suppliers_yacht`
  ```sql
  CREATE INDEX idx_pms_suppliers_yacht ON public.pms_suppliers USING btree (yacht_id)
  ```
- `idx_suppliers_preferred`
  ```sql
  CREATE INDEX idx_suppliers_preferred ON public.pms_suppliers USING btree (preferred)
  ```
- `idx_suppliers_yacht_id`
  ```sql
  CREATE INDEX idx_suppliers_yacht_id ON public.pms_suppliers USING btree (yacht_id)
  ```
- `suppliers_pkey`
  ```sql
  CREATE UNIQUE INDEX suppliers_pkey ON public.pms_suppliers USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Managers can manage suppliers** (ALL)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Service role full access suppliers** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view suppliers** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_vessel_certificates`
**Row Count**: 0

**Columns** (14):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `certificate_type` | text | NO |  |  |
| `certificate_name` | text | NO |  |  |
| `certificate_number` | text | YES |  |  |
| `issuing_authority` | text | NO |  |  |
| `issue_date` | date | YES |  |  |
| `expiry_date` | date | YES |  |  |
| `last_survey_date` | date | YES |  |  |
| `next_survey_due` | date | YES |  |  |
| `status` | text | NO | 'valid'::text |  |
| `document_id` | uuid | YES |  |  |
| `properties` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_24826_11_not_null`: status IS NOT NULL
- **CHECK** `2200_24826_14_not_null`: created_at IS NOT NULL
- **CHECK** `2200_24826_1_not_null`: id IS NOT NULL
- **CHECK** `2200_24826_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_24826_3_not_null`: certificate_type IS NOT NULL
- **CHECK** `2200_24826_4_not_null`: certificate_name IS NOT NULL
- **CHECK** `2200_24826_6_not_null`: issuing_authority IS NOT NULL

**Indexes** (6):
- `idx_vessel_certs_expiry`
  ```sql
  CREATE INDEX idx_vessel_certs_expiry ON public.pms_vessel_certificates USING btree (yacht_id, expiry_date)
  ```
- `idx_vessel_certs_status`
  ```sql
  CREATE INDEX idx_vessel_certs_status ON public.pms_vessel_certificates USING btree (yacht_id, status)
  ```
- `idx_vessel_certs_survey`
  ```sql
  CREATE INDEX idx_vessel_certs_survey ON public.pms_vessel_certificates USING btree (yacht_id, next_survey_due) WHERE (next_survey_due IS NOT NULL)
  ```
- `idx_vessel_certs_type`
  ```sql
  CREATE INDEX idx_vessel_certs_type ON public.pms_vessel_certificates USING btree (yacht_id, certificate_type)
  ```
- `idx_vessel_certs_yacht`
  ```sql
  CREATE INDEX idx_vessel_certs_yacht ON public.pms_vessel_certificates USING btree (yacht_id)
  ```
- `vessel_certificates_pkey`
  ```sql
  CREATE UNIQUE INDEX vessel_certificates_pkey ON public.pms_vessel_certificates USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access vessel_certificates** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view yacht vessel certificates** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_voyage_log`
**Row Count**: 0

**Columns** (14):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `voyage_name` | text | YES |  |  |
| `voyage_type` | text | YES |  |  |
| `departure_port` | text | YES |  |  |
| `departure_port_node_id` | uuid | YES |  |  |
| `arrival_port` | text | YES |  |  |
| `arrival_port_node_id` | uuid | YES |  |  |
| `departure_time` | timestamp with time zone | YES |  | enum: timestamptz |
| `arrival_time` | timestamp with time zone | YES |  | enum: timestamptz |
| `distance_nm` | numeric | YES |  |  |
| `fuel_consumed_liters` | numeric | YES |  |  |
| `properties` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `arrival_port_node_id` → `search_graph_nodes(id)` ON DELETE NO ACTION, ON UPDATE NO ACTION
- **FK**: `departure_port_node_id` → `search_graph_nodes(id)` ON DELETE NO ACTION, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_24851_14_not_null`: created_at IS NOT NULL
- **CHECK** `2200_24851_1_not_null`: id IS NOT NULL
- **CHECK** `2200_24851_2_not_null`: yacht_id IS NOT NULL

**Indexes** (5):
- `idx_voyage_log_dates`
  ```sql
  CREATE INDEX idx_voyage_log_dates ON public.pms_voyage_log USING btree (yacht_id, departure_time)
  ```
- `idx_voyage_log_ports`
  ```sql
  CREATE INDEX idx_voyage_log_ports ON public.pms_voyage_log USING btree (yacht_id, departure_port, arrival_port)
  ```
- `idx_voyage_log_type`
  ```sql
  CREATE INDEX idx_voyage_log_type ON public.pms_voyage_log USING btree (yacht_id, voyage_type)
  ```
- `idx_voyage_log_yacht`
  ```sql
  CREATE INDEX idx_voyage_log_yacht ON public.pms_voyage_log USING btree (yacht_id)
  ```
- `voyage_log_pkey`
  ```sql
  CREATE UNIQUE INDEX voyage_log_pkey ON public.pms_voyage_log USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access voyage_log** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view yacht voyage log** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_work_order_checklist`
**Row Count**: 0

**Columns** (24):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `work_order_id` | uuid | NO |  |  |
| `title` | character varying | NO |  | enum: varchar |
| `description` | text | YES |  |  |
| `instructions` | text | YES |  |  |
| `sequence` | integer | NO | 0 | enum: int4 |
| `is_completed` | boolean | NO | false | enum: bool |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `completed_by` | uuid | YES |  |  |
| `completion_notes` | text | YES |  |  |
| `is_required` | boolean | NO | true | enum: bool |
| `requires_photo` | boolean | NO | false | enum: bool |
| `requires_signature` | boolean | NO | false | enum: bool |
| `photo_url` | text | YES |  |  |
| `signature_data` | jsonb | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_by` | uuid | YES |  |  |
| `updated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_138858_12_not_null`: is_required IS NOT NULL
- **CHECK** `2200_138858_13_not_null`: requires_photo IS NOT NULL
- **CHECK** `2200_138858_14_not_null`: requires_signature IS NOT NULL
- **CHECK** `2200_138858_18_not_null`: created_at IS NOT NULL
- **CHECK** `2200_138858_1_not_null`: id IS NOT NULL
- **CHECK** `2200_138858_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_138858_3_not_null`: work_order_id IS NOT NULL
- **CHECK** `2200_138858_4_not_null`: title IS NOT NULL
- **CHECK** `2200_138858_7_not_null`: sequence IS NOT NULL
- **CHECK** `2200_138858_8_not_null`: is_completed IS NOT NULL

**Indexes** (4):
- `idx_pms_wo_checklist_sequence`
  ```sql
  CREATE INDEX idx_pms_wo_checklist_sequence ON public.pms_work_order_checklist USING btree (work_order_id, sequence)
  ```
- `idx_pms_wo_checklist_work_order_id`
  ```sql
  CREATE INDEX idx_pms_wo_checklist_work_order_id ON public.pms_work_order_checklist USING btree (work_order_id)
  ```
- `idx_pms_wo_checklist_yacht_id`
  ```sql
  CREATE INDEX idx_pms_wo_checklist_yacht_id ON public.pms_work_order_checklist USING btree (yacht_id)
  ```
- `pms_work_order_checklist_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_work_order_checklist_pkey ON public.pms_work_order_checklist USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (9):
- **service_role_bypass** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **users_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **users_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_view** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **yacht_isolation_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_select** (SELECT)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`

---

### `pms_work_order_history`
**Row Count**: 0

**Columns** (14):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `work_order_id` | uuid | NO |  |  |
| `equipment_id` | uuid | YES |  |  |
| `completed_by` | uuid | YES |  |  |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `notes` | text | YES |  |  |
| `hours_logged` | integer | YES |  | enum: int4 |
| `status_on_completion` | text | YES |  |  |
| `parts_used` | jsonb | YES | '[]'::jsonb |  |
| `documents_used` | jsonb | YES | '[]'::jsonb |  |
| `faults_related` | jsonb | YES | '[]'::jsonb |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18143_14_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18143_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18143_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18143_3_not_null`: work_order_id IS NOT NULL

**Indexes** (5):
- `idx_work_order_history_completed_at`
  ```sql
  CREATE INDEX idx_work_order_history_completed_at ON public.pms_work_order_history USING btree (completed_at)
  ```
- `idx_work_order_history_equipment_id`
  ```sql
  CREATE INDEX idx_work_order_history_equipment_id ON public.pms_work_order_history USING btree (equipment_id)
  ```
- `idx_work_order_history_work_order_id`
  ```sql
  CREATE INDEX idx_work_order_history_work_order_id ON public.pms_work_order_history USING btree (work_order_id)
  ```
- `idx_work_order_history_yacht_id`
  ```sql
  CREATE INDEX idx_work_order_history_yacht_id ON public.pms_work_order_history USING btree (yacht_id)
  ```
- `work_order_history_pkey`
  ```sql
  CREATE UNIQUE INDEX work_order_history_pkey ON public.pms_work_order_history USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Engineers can add history** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'deck'::text, 'interior'::text])))`
- **Service role full access work_order_history** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view work order history** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `pms_work_order_notes`
**Row Count**: 2,687

**Columns** (7):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | uuid_generate_v4() |  |
| `work_order_id` | uuid | NO |  |  |
| `note_text` | text | NO |  |  |
| `note_type` | text | NO | 'general'::text |  |
| `created_by` | uuid | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `metadata` | jsonb | YES | '{}'::jsonb |  |

**Constraints**:
- **PK**: `id`
- **FK**: `created_by` → `auth_users_profiles(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_126703_1_not_null`: id IS NOT NULL
- **CHECK** `2200_126703_2_not_null`: work_order_id IS NOT NULL
- **CHECK** `2200_126703_3_not_null`: note_text IS NOT NULL
- **CHECK** `2200_126703_4_not_null`: note_type IS NOT NULL
- **CHECK** `2200_126703_5_not_null`: created_by IS NOT NULL
- **CHECK** `2200_126703_6_not_null`: created_at IS NOT NULL
- **CHECK** `pms_work_order_notes_note_type_check`: (note_type = ANY (ARRAY['general'::text, 'progress'::text, 'issue'::text, 'resolution'::text]))

**Indexes** (5):
- `idx_pms_work_order_notes_created_by`
  ```sql
  CREATE INDEX idx_pms_work_order_notes_created_by ON public.pms_work_order_notes USING btree (created_by)
  ```
- `idx_pms_work_order_notes_user`
  ```sql
  CREATE INDEX idx_pms_work_order_notes_user ON public.pms_work_order_notes USING btree (created_by, created_at DESC)
  ```
- `idx_pms_work_order_notes_wo`
  ```sql
  CREATE INDEX idx_pms_work_order_notes_wo ON public.pms_work_order_notes USING btree (work_order_id, created_at DESC)
  ```
- `idx_pms_work_order_notes_work_order_id`
  ```sql
  CREATE INDEX idx_pms_work_order_notes_work_order_id ON public.pms_work_order_notes USING btree (work_order_id, created_at DESC)
  ```
- `pms_work_order_notes_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_work_order_notes_pkey ON public.pms_work_order_notes USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Authenticated users can view notes** (SELECT)
  - Roles: ['authenticated']
  - USING: `true`
- **Service role full access** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **pms_work_order_notes_yacht_isolation** (ALL)
  - Roles: ['public']
  - USING: `(work_order_id IN ( SELECT pms_work_orders.id
   FROM pms_work_orders
  WHERE (pms_work_orders.yacht_id = (current_setting('app.current_yacht_id'::text))::uuid)))`

---

### `pms_work_order_parts`
**Row Count**: 117

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `work_order_id` | uuid | NO |  |  |
| `part_id` | uuid | NO |  |  |
| `quantity` | integer | YES | 1 | enum: int4 |
| `notes` | text | YES |  |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `part_id` → `pms_parts(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `work_order_id`, `part_id`
- **CHECK** `2200_124064_1_not_null`: id IS NOT NULL
- **CHECK** `2200_124064_2_not_null`: work_order_id IS NOT NULL
- **CHECK** `2200_124064_3_not_null`: part_id IS NOT NULL

**Indexes** (6):
- `idx_pms_work_order_parts_part_id`
  ```sql
  CREATE INDEX idx_pms_work_order_parts_part_id ON public.pms_work_order_parts USING btree (part_id)
  ```
- `idx_pms_work_order_parts_work_order_id`
  ```sql
  CREATE INDEX idx_pms_work_order_parts_work_order_id ON public.pms_work_order_parts USING btree (work_order_id)
  ```
- `idx_wo_parts_part`
  ```sql
  CREATE INDEX idx_wo_parts_part ON public.pms_work_order_parts USING btree (part_id)
  ```
- `idx_wo_parts_work_order`
  ```sql
  CREATE INDEX idx_wo_parts_work_order ON public.pms_work_order_parts USING btree (work_order_id)
  ```
- `pms_work_order_parts_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_work_order_parts_pkey ON public.pms_work_order_parts USING btree (id)
  ```
- `pms_work_order_parts_work_order_id_part_id_key`
  ```sql
  CREATE UNIQUE INDEX pms_work_order_parts_work_order_id_part_id_key ON public.pms_work_order_parts USING btree (work_order_id, part_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (5):
- **Authenticated users can view parts** (SELECT)
  - Roles: ['authenticated']
  - USING: `true`
- **Engineers can manage work order parts** (ALL)
  - Roles: ['public']
  - USING: `((EXISTS ( SELECT 1
   FROM pms_work_orders wo
  WHERE ((wo.id = pms_work_order_parts.work_order_id) AND (wo.yacht_id = get_user_yacht_id())))) AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text])))`
- **Service role full access** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Service role full access wo_parts** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view work order parts** (SELECT)
  - Roles: ['public']
  - USING: `(EXISTS ( SELECT 1
   FROM pms_work_orders wo
  WHERE ((wo.id = pms_work_order_parts.work_order_id) AND (wo.yacht_id = get_user_yacht_id()))))`

---

### `pms_worklist_tasks`
**Row Count**: 0

**Columns** (29):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `description` | text | NO |  |  |
| `instructions` | text | YES |  |  |
| `priority` | character varying | NO | 'normal'::character varying | enum: varchar |
| `assigned_to` | uuid | YES |  |  |
| `assigned_by` | uuid | YES |  |  |
| `assigned_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `scheduled_date` | date | YES |  |  |
| `due_date` | date | YES |  |  |
| `estimated_duration_minutes` | integer | YES |  | enum: int4 |
| `equipment_id` | uuid | YES |  |  |
| `work_order_id` | uuid | YES |  |  |
| `fault_id` | uuid | YES |  |  |
| `status` | character varying | NO | 'pending'::character varying | enum: varchar |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `completed_by` | uuid | YES |  |  |
| `completion_notes` | text | YES |  |  |
| `actual_duration_minutes` | integer | YES |  | enum: int4 |
| `progress` | integer | YES | 0 | enum: int4 |
| `tags` | ARRAY | YES |  | enum: _text |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `created_by` | uuid | NO |  |  |
| `updated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_id` → `pms_equipment(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `fault_id` → `pms_faults(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `work_order_id` → `pms_work_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **CHECK** `2200_138816_15_not_null`: status IS NOT NULL
- **CHECK** `2200_138816_1_not_null`: id IS NOT NULL
- **CHECK** `2200_138816_23_not_null`: created_at IS NOT NULL
- **CHECK** `2200_138816_24_not_null`: created_by IS NOT NULL
- **CHECK** `2200_138816_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_138816_3_not_null`: description IS NOT NULL
- **CHECK** `2200_138816_5_not_null`: priority IS NOT NULL
- **CHECK** `chk_pms_worklist_tasks_priority`: ((priority)::text = ANY ((ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'urgent'::character varying])::text[]))
- **CHECK** `chk_pms_worklist_tasks_progress`: ((progress >= 0) AND (progress <= 100))
- **CHECK** `chk_pms_worklist_tasks_status`: ((status)::text = ANY ((ARRAY['pending'::character varying, 'in_progress'::character varying, 'completed'::character varying, 'cancelled'::character varying, 'deferred'::character varying])::text[]))

**Indexes** (7):
- `idx_pms_worklist_tasks_assigned_to`
  ```sql
  CREATE INDEX idx_pms_worklist_tasks_assigned_to ON public.pms_worklist_tasks USING btree (assigned_to) WHERE (assigned_to IS NOT NULL)
  ```
- `idx_pms_worklist_tasks_created_at`
  ```sql
  CREATE INDEX idx_pms_worklist_tasks_created_at ON public.pms_worklist_tasks USING btree (created_at DESC)
  ```
- `idx_pms_worklist_tasks_due_date`
  ```sql
  CREATE INDEX idx_pms_worklist_tasks_due_date ON public.pms_worklist_tasks USING btree (due_date) WHERE (deleted_at IS NULL)
  ```
- `idx_pms_worklist_tasks_scheduled_date`
  ```sql
  CREATE INDEX idx_pms_worklist_tasks_scheduled_date ON public.pms_worklist_tasks USING btree (scheduled_date) WHERE (deleted_at IS NULL)
  ```
- `idx_pms_worklist_tasks_status`
  ```sql
  CREATE INDEX idx_pms_worklist_tasks_status ON public.pms_worklist_tasks USING btree (status) WHERE (deleted_at IS NULL)
  ```
- `idx_pms_worklist_tasks_yacht_id`
  ```sql
  CREATE INDEX idx_pms_worklist_tasks_yacht_id ON public.pms_worklist_tasks USING btree (yacht_id)
  ```
- `pms_worklist_tasks_pkey`
  ```sql
  CREATE UNIQUE INDEX pms_worklist_tasks_pkey ON public.pms_worklist_tasks USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (9):
- **service_role_bypass** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **users_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **users_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **users_view** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id = get_user_yacht_id())`
- **yacht_isolation_delete** (DELETE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_select** (SELECT)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`
- **yacht_isolation_update** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(((yacht_id)::text = ((current_setting('request.jwt.claims'::text, true))::json ->> 'yacht_id'::text)) OR (yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))))`

**Triggers** (2):
- `trg_pms_worklist_tasks_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_pms_worklist_tasks_updated_at()
- `trg_set_worklist_task_completed` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION set_worklist_task_completed_at()

---

### `predictive_state`
**Row Count**: 4

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_id` | uuid | NO |  |  |
| `risk_score` | numeric | NO | 0 |  |
| `confidence` | numeric | NO | 0 |  |
| `failure_probability` | numeric | YES | 0 |  |
| `trend` | text | YES | 'stable'::text |  |
| `anomalies` | jsonb | YES | '[]'::jsonb |  |
| `failure_modes` | jsonb | YES |  |  |
| `recommended_actions` | jsonb | YES |  |  |
| `next_maintenance_due` | timestamp with time zone | YES |  | enum: timestamptz |
| `last_updated` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `equipment_id`
- **CHECK** `2200_137348_12_not_null`: last_updated IS NOT NULL
- **CHECK** `2200_137348_1_not_null`: id IS NOT NULL
- **CHECK** `2200_137348_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_137348_3_not_null`: equipment_id IS NOT NULL
- **CHECK** `2200_137348_4_not_null`: risk_score IS NOT NULL
- **CHECK** `2200_137348_5_not_null`: confidence IS NOT NULL

**Indexes** (3):
- `idx_predictive_state_equipment`
  ```sql
  CREATE INDEX idx_predictive_state_equipment ON public.predictive_state USING btree (equipment_id)
  ```
- `predictive_state_equipment_id_key`
  ```sql
  CREATE UNIQUE INDEX predictive_state_equipment_id_key ON public.predictive_state USING btree (equipment_id)
  ```
- `predictive_state_pkey1`
  ```sql
  CREATE UNIQUE INDEX predictive_state_pkey1 ON public.predictive_state USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **vessel_isolation_predictive_state** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

---

### `procurement_intents`
**Row Count**: 0

**Columns** (15):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `vendor_id` | uuid | YES |  |  |
| `status` | text | NO | 'open'::text |  |
| `summary` | text | YES |  |  |
| `vendor_domain` | text | YES |  |  |
| `vendor_email_hash` | text | YES |  |  |
| `related_object_type` | text | YES |  |  |
| `related_object_id` | uuid | YES |  |  |
| `created_from_thread_id` | uuid | YES |  |  |
| `converted_to_type` | text | YES |  |  |
| `converted_to_id` | uuid | YES |  |  |
| `created_by` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `created_from_thread_id` → `email_threads(id)` ON DELETE NO ACTION, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_140266_14_not_null`: created_at IS NOT NULL
- **CHECK** `2200_140266_15_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_140266_1_not_null`: id IS NOT NULL
- **CHECK** `2200_140266_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_140266_4_not_null`: status IS NOT NULL
- **CHECK** `procurement_intents_converted_to_type_check`: (converted_to_type = ANY (ARRAY['purchase_order'::text, 'work_order'::text]))
- **CHECK** `procurement_intents_status_check`: (status = ANY (ARRAY['open'::text, 'converted'::text, 'closed'::text]))

**Indexes** (4):
- `idx_procurement_intents_status`
  ```sql
  CREATE INDEX idx_procurement_intents_status ON public.procurement_intents USING btree (yacht_id, status) WHERE (status = 'open'::text)
  ```
- `idx_procurement_intents_vendor_hash`
  ```sql
  CREATE INDEX idx_procurement_intents_vendor_hash ON public.procurement_intents USING btree (vendor_email_hash)
  ```
- `idx_procurement_intents_yacht`
  ```sql
  CREATE INDEX idx_procurement_intents_yacht ON public.procurement_intents USING btree (yacht_id)
  ```
- `procurement_intents_pkey`
  ```sql
  CREATE UNIQUE INDEX procurement_intents_pkey ON public.procurement_intents USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Service role manages procurement_intents** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **Users can create yacht procurement_intents** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`
- **Users can update yacht procurement_intents** (UPDATE)
  - Roles: ['authenticated']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`
- **Users can view yacht procurement_intents** (SELECT)
  - Roles: ['authenticated']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

---

### `relationship_staging`
**Row Count**: 674

**Columns** (13):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `from_canonical` | text | NO |  |  |
| `to_canonical` | text | NO |  |  |
| `relationship_type` | text | NO |  |  |
| `confidence` | double precision | YES | 0.9 | enum: float8 |
| `evidence` | text | YES |  |  |
| `source_chunk_id` | text | YES |  |  |
| `status` | text | YES | 'pending'::text |  |
| `error_message` | text | YES |  |  |
| `processed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `graph_edge_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_45130_1_not_null`: id IS NOT NULL
- **CHECK** `2200_45130_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_45130_3_not_null`: from_canonical IS NOT NULL
- **CHECK** `2200_45130_4_not_null`: to_canonical IS NOT NULL
- **CHECK** `2200_45130_5_not_null`: relationship_type IS NOT NULL
- **CHECK** `relationship_staging_status_check`: (status = ANY (ARRAY['pending'::text, 'processing'::text, 'completed'::text, 'failed'::text]))

**Indexes** (3):
- `idx_relationship_staging_status`
  ```sql
  CREATE INDEX idx_relationship_staging_status ON public.relationship_staging USING btree (status) WHERE (status = 'pending'::text)
  ```
- `idx_relationship_staging_yacht`
  ```sql
  CREATE INDEX idx_relationship_staging_yacht ON public.relationship_staging USING btree (yacht_id)
  ```
- `relationship_staging_pkey`
  ```sql
  CREATE UNIQUE INDEX relationship_staging_pkey ON public.relationship_staging USING btree (id)
  ```

**RLS**: ❌ DISABLED

---

### `role_handover_buckets`
**Row Count**: 46

**Columns** (17):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | YES |  |  |
| `role_id` | text | NO |  |  |
| `department` | text | NO |  |  |
| `bucket_name` | text | NO |  |  |
| `bucket_order` | integer | NO |  | enum: int4 |
| `source_entity_types` | ARRAY | NO |  | enum: _text |
| `filter_criteria` | jsonb | YES | '{}'::jsonb |  |
| `auto_populate` | boolean | YES | true | enum: bool |
| `auto_populate_criteria` | jsonb | YES | '{}'::jsonb |  |
| `max_items` | integer | YES | 10 | enum: int4 |
| `show_if_empty` | boolean | YES | false | enum: bool |
| `empty_message` | text | YES | 'No items'::text |  |
| `is_critical_bucket` | boolean | YES | false | enum: bool |
| `active` | boolean | YES | true | enum: bool |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `yacht_id`, `role_id`, `bucket_name`
- **CHECK** `2200_135650_16_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135650_17_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_135650_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135650_3_not_null`: role_id IS NOT NULL
- **CHECK** `2200_135650_4_not_null`: department IS NOT NULL
- **CHECK** `2200_135650_5_not_null`: bucket_name IS NOT NULL
- **CHECK** `2200_135650_6_not_null`: bucket_order IS NOT NULL
- **CHECK** `2200_135650_7_not_null`: source_entity_types IS NOT NULL

**Indexes** (5):
- `idx_role_handover_buckets_dept`
  ```sql
  CREATE INDEX idx_role_handover_buckets_dept ON public.role_handover_buckets USING btree (department)
  ```
- `idx_role_handover_buckets_role`
  ```sql
  CREATE INDEX idx_role_handover_buckets_role ON public.role_handover_buckets USING btree (role_id)
  ```
- `idx_role_handover_buckets_yacht`
  ```sql
  CREATE INDEX idx_role_handover_buckets_yacht ON public.role_handover_buckets USING btree (yacht_id)
  ```
- `role_handover_buckets_pkey`
  ```sql
  CREATE UNIQUE INDEX role_handover_buckets_pkey ON public.role_handover_buckets USING btree (id)
  ```
- `role_handover_buckets_yacht_id_role_id_bucket_name_key`
  ```sql
  CREATE UNIQUE INDEX role_handover_buckets_yacht_id_role_id_bucket_name_key ON public.role_handover_buckets USING btree (yacht_id, role_id, bucket_name)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **handover_buckets_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

**Triggers** (1):
- `trigger_role_handover_buckets_updated` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_role_handover_buckets_timestamp()

---

### `role_search_profiles`
**Row Count**: 0

**Columns** (16):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | YES |  |  |
| `role_id` | text | NO |  |  |
| `default_intent` | text | YES | 'information'::text |  |
| `intent_biases` | jsonb | YES | '{}'::jsonb |  |
| `entity_biases` | jsonb | YES | '{}'::jsonb |  |
| `domain_weights` | jsonb | NO | '{}'::jsonb |  |
| `result_type_order` | ARRAY | YES | '{}'::text[] | enum: _text |
| `answer_style` | text | YES | 'technical'::text |  |
| `default_detail_level` | text | YES | 'normal'::text |  |
| `recency_boost` | numeric | YES | 1.0 |  |
| `handover_auto_include` | ARRAY | YES | '{}'::text[] | enum: _text |
| `sample_queries` | ARRAY | YES | '{}'::text[] | enum: _text |
| `active` | boolean | YES | true | enum: bool |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **UNIQUE**: `yacht_id`, `role_id`
- **CHECK** `2200_135621_15_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135621_16_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_135621_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135621_3_not_null`: role_id IS NOT NULL
- **CHECK** `2200_135621_7_not_null`: domain_weights IS NOT NULL
- **CHECK** `valid_answer_style`: (answer_style = ANY (ARRAY['technical'::text, 'summary'::text, 'narrative'::text, 'concise'::text]))
- **CHECK** `valid_detail_level`: (default_detail_level = ANY (ARRAY['minimal'::text, 'normal'::text, 'detailed'::text]))

**Indexes** (4):
- `idx_role_search_profiles_role`
  ```sql
  CREATE INDEX idx_role_search_profiles_role ON public.role_search_profiles USING btree (role_id)
  ```
- `idx_role_search_profiles_yacht`
  ```sql
  CREATE INDEX idx_role_search_profiles_yacht ON public.role_search_profiles USING btree (yacht_id)
  ```
- `role_search_profiles_pkey`
  ```sql
  CREATE UNIQUE INDEX role_search_profiles_pkey ON public.role_search_profiles USING btree (id)
  ```
- `role_search_profiles_yacht_id_role_id_key`
  ```sql
  CREATE UNIQUE INDEX role_search_profiles_yacht_id_role_id_key ON public.role_search_profiles USING btree (yacht_id, role_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **search_profiles_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

**Triggers** (1):
- `trigger_role_search_profiles_updated` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_role_search_profiles_timestamp()

---

### `search_document_chunks`
**Row Count**: 47,166

**Columns** (25):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | YES |  |  |
| `document_id` | uuid | YES |  |  |
| `chunk_index` | integer | YES |  | enum: int4 |
| `text` | text | YES |  |  |
| `page_number` | integer | YES |  | enum: int4 |
| `embedding` | USER-DEFINED | YES |  | enum: vector |
| `equipment_ids` | ARRAY | YES | '{}'::uuid[] | enum: _uuid |
| `fault_codes` | ARRAY | YES | '{}'::text[] | enum: _text |
| `tags` | ARRAY | YES | '{}'::text[] | enum: _text |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `content` | text | YES |  |  |
| `graph_extracted` | boolean | YES | false | enum: bool |
| `graph_extracted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `section_title` | text | YES |  |  |
| `doc_type` | text | YES |  |  |
| `system_tag` | text | YES |  |  |
| `graph_extract_status` | text | NO | 'pending'::text |  |
| `graph_extract_error` | text | YES |  |  |
| `section_path` | ARRAY | YES |  | enum: _text |
| `section_type` | text | YES |  |  |
| `is_section_entry` | boolean | NO | false | enum: bool |
| `symptom_codes` | ARRAY | YES |  | enum: _text |
| `graph_extract_ts` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_18470_12_not_null`: created_at IS NOT NULL
- **CHECK** `2200_18470_19_not_null`: graph_extract_status IS NOT NULL
- **CHECK** `2200_18470_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18470_23_not_null`: is_section_entry IS NOT NULL
- **CHECK** `document_chunks_graph_extract_status_check`: (graph_extract_status = ANY (ARRAY['pending'::text, 'success'::text, 'failed'::text]))

**Indexes** (16):
- `document_chunks_pkey`
  ```sql
  CREATE UNIQUE INDEX document_chunks_pkey ON public.search_document_chunks USING btree (id)
  ```
- `idx_chunks_doc_type`
  ```sql
  CREATE INDEX idx_chunks_doc_type ON public.search_document_chunks USING btree (yacht_id, doc_type) WHERE (doc_type IS NOT NULL)
  ```
- `idx_chunks_extract_status`
  ```sql
  CREATE INDEX idx_chunks_extract_status ON public.search_document_chunks USING btree (yacht_id, graph_extract_status) WHERE (graph_extract_status = 'pending'::text)
  ```
- `idx_chunks_graph_status`
  ```sql
  CREATE INDEX idx_chunks_graph_status ON public.search_document_chunks USING btree (yacht_id, graph_extract_status)
  ```
- `idx_chunks_not_extracted`
  ```sql
  CREATE INDEX idx_chunks_not_extracted ON public.search_document_chunks USING btree (graph_extracted) WHERE (graph_extracted = false)
  ```
- `idx_chunks_pending`
  ```sql
  CREATE INDEX idx_chunks_pending ON public.search_document_chunks USING btree (yacht_id, created_at) WHERE (graph_extract_status = 'pending'::text)
  ```
- `idx_chunks_section`
  ```sql
  CREATE INDEX idx_chunks_section ON public.search_document_chunks USING btree (yacht_id, section_title) WHERE (section_title IS NOT NULL)
  ```
- `idx_chunks_section_title`
  ```sql
  CREATE INDEX idx_chunks_section_title ON public.search_document_chunks USING btree (yacht_id, section_title) WHERE (section_title IS NOT NULL)
  ```
- `idx_chunks_symptom_codes`
  ```sql
  CREATE INDEX idx_chunks_symptom_codes ON public.search_document_chunks USING gin (symptom_codes) WHERE (symptom_codes IS NOT NULL)
  ```
- `idx_chunks_system_tag`
  ```sql
  CREATE INDEX idx_chunks_system_tag ON public.search_document_chunks USING btree (yacht_id, system_tag) WHERE (system_tag IS NOT NULL)
  ```
- `idx_document_chunks_document_id`
  ```sql
  CREATE INDEX idx_document_chunks_document_id ON public.search_document_chunks USING btree (document_id)
  ```
- `idx_document_chunks_embedding`
  ```sql
  CREATE INDEX idx_document_chunks_embedding ON public.search_document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists='100')
  ```
- `idx_document_chunks_equipment_ids`
  ```sql
  CREATE INDEX idx_document_chunks_equipment_ids ON public.search_document_chunks USING gin (equipment_ids)
  ```
- `idx_document_chunks_fault_codes`
  ```sql
  CREATE INDEX idx_document_chunks_fault_codes ON public.search_document_chunks USING gin (fault_codes)
  ```
- `idx_document_chunks_graph_extracted`
  ```sql
  CREATE INDEX idx_document_chunks_graph_extracted ON public.search_document_chunks USING btree (graph_extracted) WHERE (graph_extracted = false)
  ```
- `idx_document_chunks_yacht_id`
  ```sql
  CREATE INDEX idx_document_chunks_yacht_id ON public.search_document_chunks USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Service role full access document_chunks** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **System can insert chunks** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Users can view document chunks** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = COALESCE(jwt_yacht_id(), get_user_yacht_id()))`
- **service_role_full_access** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

**Triggers** (4):
- `trigger_mark_document_indexed` (AFTER INSERT)
  - Action: EXECUTE FUNCTION mark_document_indexed()
- `trigger_populate_chunk_metadata` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION populate_chunk_metadata()
- `trigger_sync_content` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION sync_content_text()
- `trigger_sync_content` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION sync_content_text()

---

### `search_embedding_queue`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `document_id` | uuid | YES |  |  |
| `status` | text | NO | 'pending'::text |  |
| `error_message` | text | YES |  |  |
| `started_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `document_id` → `doc_metadata(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18520_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18520_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18520_4_not_null`: status IS NOT NULL
- **CHECK** `2200_18520_9_not_null`: created_at IS NOT NULL

**Indexes** (4):
- `embedding_jobs_pkey`
  ```sql
  CREATE UNIQUE INDEX embedding_jobs_pkey ON public.search_embedding_queue USING btree (id)
  ```
- `idx_embedding_jobs_document_id`
  ```sql
  CREATE INDEX idx_embedding_jobs_document_id ON public.search_embedding_queue USING btree (document_id)
  ```
- `idx_embedding_jobs_status`
  ```sql
  CREATE INDEX idx_embedding_jobs_status ON public.search_embedding_queue USING btree (status)
  ```
- `idx_embedding_jobs_yacht_id`
  ```sql
  CREATE INDEX idx_embedding_jobs_yacht_id ON public.search_embedding_queue USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Managers can view embedding jobs** (SELECT)
  - Roles: ['public']
  - USING: `((yacht_id = get_user_yacht_id()) AND is_manager())`
- **Service role full access embedding_jobs** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **System can manage embedding jobs** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `search_fault_code_catalog`
**Row Count**: 34

**Columns** (17):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_type` | text | NO |  |  |
| `manufacturer` | text | YES |  |  |
| `code` | text | NO |  |  |
| `name` | text | YES |  |  |
| `description` | text | YES |  |  |
| `severity` | text | YES | 'warning'::text |  |
| `symptoms` | ARRAY | YES |  | enum: _text |
| `causes` | ARRAY | YES |  | enum: _text |
| `diagnostic_steps` | ARRAY | YES |  | enum: _text |
| `resolution_steps` | ARRAY | YES |  | enum: _text |
| `related_parts` | ARRAY | YES |  | enum: _text |
| `source_document_id` | uuid | YES |  |  |
| `source_chunk_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `source_chunk_id` → `search_document_chunks(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `source_document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `equipment_type`, `code`
- **CHECK** `2200_25331_16_not_null`: created_at IS NOT NULL
- **CHECK** `2200_25331_17_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_25331_1_not_null`: id IS NOT NULL
- **CHECK** `2200_25331_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_25331_3_not_null`: equipment_type IS NOT NULL
- **CHECK** `2200_25331_5_not_null`: code IS NOT NULL

**Indexes** (10):
- `fault_code_catalog_pkey`
  ```sql
  CREATE UNIQUE INDEX fault_code_catalog_pkey ON public.search_fault_code_catalog USING btree (id)
  ```
- `fault_code_catalog_yacht_id_equipment_type_code_key`
  ```sql
  CREATE UNIQUE INDEX fault_code_catalog_yacht_id_equipment_type_code_key ON public.search_fault_code_catalog USING btree (yacht_id, equipment_type, code)
  ```
- `idx_fault_catalog_causes`
  ```sql
  CREATE INDEX idx_fault_catalog_causes ON public.search_fault_code_catalog USING gin (causes)
  ```
- `idx_fault_catalog_code`
  ```sql
  CREATE INDEX idx_fault_catalog_code ON public.search_fault_code_catalog USING btree (yacht_id, code)
  ```
- `idx_fault_catalog_equipment`
  ```sql
  CREATE INDEX idx_fault_catalog_equipment ON public.search_fault_code_catalog USING btree (yacht_id, equipment_type)
  ```
- `idx_fault_catalog_manufacturer`
  ```sql
  CREATE INDEX idx_fault_catalog_manufacturer ON public.search_fault_code_catalog USING btree (yacht_id, manufacturer) WHERE (manufacturer IS NOT NULL)
  ```
- `idx_fault_catalog_parts`
  ```sql
  CREATE INDEX idx_fault_catalog_parts ON public.search_fault_code_catalog USING gin (related_parts)
  ```
- `idx_fault_catalog_severity`
  ```sql
  CREATE INDEX idx_fault_catalog_severity ON public.search_fault_code_catalog USING btree (yacht_id, severity)
  ```
- `idx_fault_catalog_symptoms`
  ```sql
  CREATE INDEX idx_fault_catalog_symptoms ON public.search_fault_code_catalog USING gin (symptoms)
  ```
- `idx_fault_catalog_yacht`
  ```sql
  CREATE INDEX idx_fault_catalog_yacht ON public.search_fault_code_catalog USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role can manage fault codes** (ALL)
  - Roles: ['public']
  - USING: `((auth.jwt() ->> 'role'::text) = 'service_role'::text)`
- **Service role full access fault_code_catalog** (ALL)
  - Roles: ['service_role']
  - USING: `true`

---

### `search_graph_edges`
**Row Count**: 68

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `from_node_id` | uuid | NO |  |  |
| `to_node_id` | uuid | NO |  |  |
| `edge_type` | USER-DEFINED | NO |  | enum: graph_edge_type |
| `source_chunk_id` | uuid | YES |  |  |
| `source_document_id` | uuid | YES |  |  |
| `properties` | jsonb | YES | '{}'::jsonb |  |
| `confidence` | real | NO | 1.0 | enum: float4 |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `description` | text | YES |  |  |
| `embedding` | USER-DEFINED | YES |  | enum: vector |

**Constraints**:
- **PK**: `id`
- **FK**: `from_node_id` → `search_graph_nodes(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `source_chunk_id` → `search_document_chunks(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `source_document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `to_node_id` → `search_graph_nodes(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `from_node_id`, `to_node_id`, `edge_type`
- **CHECK** `2200_24708_10_not_null`: created_at IS NOT NULL
- **CHECK** `2200_24708_1_not_null`: id IS NOT NULL
- **CHECK** `2200_24708_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_24708_3_not_null`: from_node_id IS NOT NULL
- **CHECK** `2200_24708_4_not_null`: to_node_id IS NOT NULL
- **CHECK** `2200_24708_5_not_null`: edge_type IS NOT NULL
- **CHECK** `2200_24708_9_not_null`: confidence IS NOT NULL

**Indexes** (11):
- `graph_edges_pkey`
  ```sql
  CREATE UNIQUE INDEX graph_edges_pkey ON public.search_graph_edges USING btree (id)
  ```
- `graph_edges_unique`
  ```sql
  CREATE UNIQUE INDEX graph_edges_unique ON public.search_graph_edges USING btree (yacht_id, from_node_id, to_node_id, edge_type)
  ```
- `idx_graph_edges_from`
  ```sql
  CREATE INDEX idx_graph_edges_from ON public.search_graph_edges USING btree (from_node_id)
  ```
- `idx_graph_edges_from_type`
  ```sql
  CREATE INDEX idx_graph_edges_from_type ON public.search_graph_edges USING btree (from_node_id, edge_type)
  ```
- `idx_graph_edges_properties`
  ```sql
  CREATE INDEX idx_graph_edges_properties ON public.search_graph_edges USING gin (properties jsonb_path_ops)
  ```
- `idx_graph_edges_source_chunk`
  ```sql
  CREATE INDEX idx_graph_edges_source_chunk ON public.search_graph_edges USING btree (source_chunk_id) WHERE (source_chunk_id IS NOT NULL)
  ```
- `idx_graph_edges_to`
  ```sql
  CREATE INDEX idx_graph_edges_to ON public.search_graph_edges USING btree (to_node_id)
  ```
- `idx_graph_edges_to_type`
  ```sql
  CREATE INDEX idx_graph_edges_to_type ON public.search_graph_edges USING btree (to_node_id, edge_type)
  ```
- `idx_graph_edges_type`
  ```sql
  CREATE INDEX idx_graph_edges_type ON public.search_graph_edges USING btree (yacht_id, edge_type)
  ```
- `idx_graph_edges_yacht`
  ```sql
  CREATE INDEX idx_graph_edges_yacht ON public.search_graph_edges USING btree (yacht_id)
  ```
- `idx_graph_edges_yacht_type`
  ```sql
  CREATE INDEX idx_graph_edges_yacht_type ON public.search_graph_edges USING btree (yacht_id, edge_type)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role full access graph_edges** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **System can manage graph edges** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`
- **Users can view yacht graph edges** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `search_graph_nodes`
**Row Count**: 109

**Columns** (13):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `node_type` | USER-DEFINED | NO |  | enum: graph_node_type |
| `label` | text | NO |  |  |
| `normalized_label` | text | NO |  |  |
| `source_chunk_id` | uuid | YES |  |  |
| `source_document_id` | uuid | YES |  |  |
| `properties` | jsonb | YES | '{}'::jsonb |  |
| `confidence` | real | NO | 1.0 | enum: float4 |
| `extraction_source` | text | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `embedding` | USER-DEFINED | YES |  | enum: vector |

**Constraints**:
- **PK**: `id`
- **FK**: `source_chunk_id` → `search_document_chunks(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `source_document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `node_type`, `normalized_label`
- **CHECK** `2200_24672_11_not_null`: created_at IS NOT NULL
- **CHECK** `2200_24672_12_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_24672_1_not_null`: id IS NOT NULL
- **CHECK** `2200_24672_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_24672_3_not_null`: node_type IS NOT NULL
- **CHECK** `2200_24672_4_not_null`: label IS NOT NULL
- **CHECK** `2200_24672_5_not_null`: normalized_label IS NOT NULL
- **CHECK** `2200_24672_9_not_null`: confidence IS NOT NULL

**Indexes** (12):
- `graph_nodes_pkey`
  ```sql
  CREATE UNIQUE INDEX graph_nodes_pkey ON public.search_graph_nodes USING btree (id)
  ```
- `graph_nodes_unique`
  ```sql
  CREATE UNIQUE INDEX graph_nodes_unique ON public.search_graph_nodes USING btree (yacht_id, node_type, normalized_label)
  ```
- `idx_graph_nodes_confidence`
  ```sql
  CREATE INDEX idx_graph_nodes_confidence ON public.search_graph_nodes USING btree (yacht_id, confidence DESC)
  ```
- `idx_graph_nodes_embedding`
  ```sql
  CREATE INDEX idx_graph_nodes_embedding ON public.search_graph_nodes USING ivfflat (embedding vector_cosine_ops) WITH (lists='100')
  ```
- `idx_graph_nodes_label`
  ```sql
  CREATE INDEX idx_graph_nodes_label ON public.search_graph_nodes USING btree (yacht_id, normalized_label)
  ```
- `idx_graph_nodes_properties`
  ```sql
  CREATE INDEX idx_graph_nodes_properties ON public.search_graph_nodes USING gin (properties)
  ```
- `idx_graph_nodes_source_chunk`
  ```sql
  CREATE INDEX idx_graph_nodes_source_chunk ON public.search_graph_nodes USING btree (source_chunk_id) WHERE (source_chunk_id IS NOT NULL)
  ```
- `idx_graph_nodes_source_doc`
  ```sql
  CREATE INDEX idx_graph_nodes_source_doc ON public.search_graph_nodes USING btree (source_document_id) WHERE (source_document_id IS NOT NULL)
  ```
- `idx_graph_nodes_type`
  ```sql
  CREATE INDEX idx_graph_nodes_type ON public.search_graph_nodes USING btree (yacht_id, node_type)
  ```
- `idx_graph_nodes_yacht`
  ```sql
  CREATE INDEX idx_graph_nodes_yacht ON public.search_graph_nodes USING btree (yacht_id)
  ```
- `idx_graph_nodes_yacht_label`
  ```sql
  CREATE INDEX idx_graph_nodes_yacht_label ON public.search_graph_nodes USING btree (yacht_id, normalized_label)
  ```
- `idx_graph_nodes_yacht_type`
  ```sql
  CREATE INDEX idx_graph_nodes_yacht_type ON public.search_graph_nodes USING btree (yacht_id, node_type)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role full access graph_nodes** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **System can manage graph nodes** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`
- **Users can view yacht graph nodes** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

**Triggers** (2):
- `trigger_normalize_graph_node` (BEFORE INSERT)
  - Action: EXECUTE FUNCTION normalize_graph_node_label()
- `trigger_normalize_graph_node` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION normalize_graph_node_label()

---

### `search_maintenance_facts`
**Row Count**: 4

**Columns** (14):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_node_id` | uuid | YES |  |  |
| `part_node_id` | uuid | YES |  |  |
| `system_node_id` | uuid | YES |  |  |
| `action` | USER-DEFINED | NO |  | enum: maintenance_action_type |
| `interval_hours` | integer | YES |  | enum: int4 |
| `interval_days` | integer | YES |  | enum: int4 |
| `interval_description` | text | YES |  |  |
| `source_chunk_id` | uuid | YES |  |  |
| `source_document_id` | uuid | YES |  |  |
| `confidence` | real | NO | 1.0 | enum: float4 |
| `properties` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_node_id` → `search_graph_nodes(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `part_node_id` → `search_graph_nodes(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `source_chunk_id` → `search_document_chunks(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `source_document_id` → `doc_metadata(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `system_node_id` → `search_graph_nodes(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_24752_12_not_null`: confidence IS NOT NULL
- **CHECK** `2200_24752_14_not_null`: created_at IS NOT NULL
- **CHECK** `2200_24752_1_not_null`: id IS NOT NULL
- **CHECK** `2200_24752_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_24752_6_not_null`: action IS NOT NULL

**Indexes** (7):
- `idx_maintenance_facts_action`
  ```sql
  CREATE INDEX idx_maintenance_facts_action ON public.search_maintenance_facts USING btree (yacht_id, action)
  ```
- `idx_maintenance_facts_equipment`
  ```sql
  CREATE INDEX idx_maintenance_facts_equipment ON public.search_maintenance_facts USING btree (equipment_node_id)
  ```
- `idx_maintenance_facts_interval`
  ```sql
  CREATE INDEX idx_maintenance_facts_interval ON public.search_maintenance_facts USING btree (yacht_id, interval_hours) WHERE (interval_hours IS NOT NULL)
  ```
- `idx_maintenance_facts_part`
  ```sql
  CREATE INDEX idx_maintenance_facts_part ON public.search_maintenance_facts USING btree (part_node_id) WHERE (part_node_id IS NOT NULL)
  ```
- `idx_maintenance_facts_system`
  ```sql
  CREATE INDEX idx_maintenance_facts_system ON public.search_maintenance_facts USING btree (system_node_id) WHERE (system_node_id IS NOT NULL)
  ```
- `idx_maintenance_facts_yacht`
  ```sql
  CREATE INDEX idx_maintenance_facts_yacht ON public.search_maintenance_facts USING btree (yacht_id)
  ```
- `maintenance_facts_pkey`
  ```sql
  CREATE UNIQUE INDEX maintenance_facts_pkey ON public.search_maintenance_facts USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role full access maintenance_facts** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **System can manage maintenance facts** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`
- **Users can view yacht maintenance facts** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `search_manual_embeddings`
**Row Count**: 0

**Columns** (11):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `user_id` | uuid | YES |  |  |
| `yacht_id` | text | NO |  |  |
| `equipment` | text | YES |  |  |
| `file_name` | text | NO |  |  |
| `file_size` | integer | YES |  | enum: int4 |
| `chunk_text` | text | NO |  |  |
| `chunk_index` | integer | NO |  | enum: int4 |
| `embedding` | USER-DEFINED | YES |  | enum: vector |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `metadata` | jsonb | YES | '{}'::jsonb |  |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_28080_1_not_null`: id IS NOT NULL
- **CHECK** `2200_28080_3_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_28080_5_not_null`: file_name IS NOT NULL
- **CHECK** `2200_28080_7_not_null`: chunk_text IS NOT NULL
- **CHECK** `2200_28080_8_not_null`: chunk_index IS NOT NULL

**Indexes** (4):
- `manual_embeddings_pkey`
  ```sql
  CREATE UNIQUE INDEX manual_embeddings_pkey ON public.search_manual_embeddings USING btree (id)
  ```
- `manual_embeddings_user_id_idx`
  ```sql
  CREATE INDEX manual_embeddings_user_id_idx ON public.search_manual_embeddings USING btree (user_id)
  ```
- `manual_embeddings_vector_idx`
  ```sql
  CREATE INDEX manual_embeddings_vector_idx ON public.search_manual_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists='100')
  ```
- `manual_embeddings_yacht_idx`
  ```sql
  CREATE INDEX manual_embeddings_yacht_idx ON public.search_manual_embeddings USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Service role has full access to manual_embeddings** (ALL)
  - Roles: ['public']
  - USING: `((auth.jwt() ->> 'role'::text) = 'service_role'::text)`
  - WITH CHECK: `((auth.jwt() ->> 'role'::text) = 'service_role'::text)`
- **Users can insert manual embeddings** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `(auth.uid() = user_id)`
- **Users can view their yacht's manual embeddings** (SELECT)
  - Roles: ['public']
  - USING: `(auth.uid() = user_id)`

---

### `search_ocred_pages`
**Row Count**: 0

**Columns** (8):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `document_id` | uuid | NO |  |  |
| `page_number` | integer | NO |  | enum: int4 |
| `raw_text` | text | YES |  |  |
| `confidence` | numeric | YES |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `document_id` → `doc_metadata(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18498_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18498_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18498_3_not_null`: document_id IS NOT NULL
- **CHECK** `2200_18498_4_not_null`: page_number IS NOT NULL
- **CHECK** `2200_18498_8_not_null`: created_at IS NOT NULL

**Indexes** (3):
- `idx_ocred_pages_document_id`
  ```sql
  CREATE INDEX idx_ocred_pages_document_id ON public.search_ocred_pages USING btree (document_id)
  ```
- `idx_ocred_pages_yacht_id`
  ```sql
  CREATE INDEX idx_ocred_pages_yacht_id ON public.search_ocred_pages USING btree (yacht_id)
  ```
- `ocred_pages_pkey`
  ```sql
  CREATE UNIQUE INDEX ocred_pages_pkey ON public.search_ocred_pages USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access ocred_pages** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **System can manage ocred pages** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `search_query_logs`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | YES |  |  |
| `query_text` | text | NO |  |  |
| `interpreted_intent` | text | YES |  |  |
| `entities` | jsonb | YES | '{}'::jsonb |  |
| `latency_ms` | integer | YES |  | enum: int4 |
| `success` | boolean | YES |  | enum: bool |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_18029_1_not_null`: id IS NOT NULL
- **CHECK** `2200_18029_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_18029_4_not_null`: query_text IS NOT NULL
- **CHECK** `2200_18029_9_not_null`: created_at IS NOT NULL

**Indexes** (9):
- `idx_search_queries_created_at`
  ```sql
  CREATE INDEX idx_search_queries_created_at ON public.search_query_logs USING btree (created_at)
  ```
- `idx_search_queries_date`
  ```sql
  CREATE INDEX idx_search_queries_date ON public.search_query_logs USING btree (yacht_id, created_at DESC)
  ```
- `idx_search_queries_entities`
  ```sql
  CREATE INDEX idx_search_queries_entities ON public.search_query_logs USING gin (entities jsonb_path_ops)
  ```
- `idx_search_queries_intent`
  ```sql
  CREATE INDEX idx_search_queries_intent ON public.search_query_logs USING btree (interpreted_intent)
  ```
- `idx_search_queries_success`
  ```sql
  CREATE INDEX idx_search_queries_success ON public.search_query_logs USING btree (yacht_id, success)
  ```
- `idx_search_queries_user_id`
  ```sql
  CREATE INDEX idx_search_queries_user_id ON public.search_query_logs USING btree (user_id)
  ```
- `idx_search_queries_yacht`
  ```sql
  CREATE INDEX idx_search_queries_yacht ON public.search_query_logs USING btree (yacht_id, created_at DESC)
  ```
- `idx_search_queries_yacht_id`
  ```sql
  CREATE INDEX idx_search_queries_yacht_id ON public.search_query_logs USING btree (yacht_id)
  ```
- `search_queries_pkey`
  ```sql
  CREATE UNIQUE INDEX search_queries_pkey ON public.search_query_logs USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (5):
- **Service role full access search_queries** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **System can manage search queries** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`
- **Users can insert search queries** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Users can view own search queries** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`
- **Users can view yacht search queries** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `search_sessions`
**Row Count**: 0

**Columns** (23):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | NO |  |  |
| `raw_query` | text | NO |  |  |
| `normalized_query` | text | YES |  |  |
| `detected_intent` | text | YES |  |  |
| `intent_confidence` | numeric | YES | 0.0 |  |
| `extracted_entities` | jsonb | YES | '[]'::jsonb |  |
| `query_context` | jsonb | YES | '{}'::jsonb |  |
| `result_count` | integer | YES | 0 | enum: int4 |
| `result_types` | jsonb | YES | '{}'::jsonb |  |
| `interpretation_ms` | integer | YES |  | enum: int4 |
| `search_ms` | integer | YES |  | enum: int4 |
| `total_ms` | integer | YES |  | enum: int4 |
| `clicked_results` | ARRAY | YES |  | enum: _uuid |
| `microactions_shown` | ARRAY | YES |  | enum: _text |
| `microactions_executed` | ARRAY | YES |  | enum: _text |
| `was_helpful` | boolean | YES |  | enum: bool |
| `feedback_text` | text | YES |  |  |
| `source` | text | YES | 'search_bar'::text |  |
| `parent_session_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `completed_at` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_135757_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135757_22_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135757_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_135757_3_not_null`: user_id IS NOT NULL
- **CHECK** `2200_135757_4_not_null`: raw_query IS NOT NULL
- **CHECK** `valid_intent`: (detected_intent = ANY (ARRAY['information'::text, 'diagnostic'::text, 'action'::text, 'recall'::text, 'summary'::text, 'comparison'::text, 'navigation'::text, 'handover'::text, 'unknown'::text]))

**Indexes** (6):
- `idx_search_sessions_created`
  ```sql
  CREATE INDEX idx_search_sessions_created ON public.search_sessions USING btree (created_at DESC)
  ```
- `idx_search_sessions_intent`
  ```sql
  CREATE INDEX idx_search_sessions_intent ON public.search_sessions USING btree (detected_intent)
  ```
- `idx_search_sessions_query`
  ```sql
  CREATE INDEX idx_search_sessions_query ON public.search_sessions USING gin (to_tsvector('english'::regconfig, raw_query))
  ```
- `idx_search_sessions_user`
  ```sql
  CREATE INDEX idx_search_sessions_user ON public.search_sessions USING btree (user_id)
  ```
- `idx_search_sessions_yacht`
  ```sql
  CREATE INDEX idx_search_sessions_yacht ON public.search_sessions USING btree (yacht_id)
  ```
- `search_sessions_pkey`
  ```sql
  CREATE UNIQUE INDEX search_sessions_pkey ON public.search_sessions USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **search_sessions_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(user_id = auth.uid())`
- **search_sessions_own** (SELECT)
  - Roles: ['authenticated']
  - USING: `(user_id = auth.uid())`
- **search_sessions_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `search_suggestion_analytics`
**Row Count**: 0

**Columns** (15):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | YES |  |  |
| `query_text` | text | NO |  |  |
| `intent` | text | YES |  |  |
| `search_query_id` | uuid | YES |  |  |
| `situation_detected` | boolean | NO | false | enum: bool |
| `situation_type` | text | YES |  |  |
| `situation_severity` | text | YES |  |  |
| `situation_context` | text | YES |  |  |
| `suggested_actions` | jsonb | NO | '[]'::jsonb |  |
| `evidence_provided` | jsonb | YES | '[]'::jsonb |  |
| `user_action_taken` | text | YES |  |  |
| `user_action_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_30110_11_not_null`: suggested_actions IS NOT NULL
- **CHECK** `2200_30110_15_not_null`: created_at IS NOT NULL
- **CHECK** `2200_30110_1_not_null`: id IS NOT NULL
- **CHECK** `2200_30110_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_30110_4_not_null`: query_text IS NOT NULL
- **CHECK** `2200_30110_7_not_null`: situation_detected IS NOT NULL
- **CHECK** `suggestion_log_severity_check`: ((situation_severity IS NULL) OR (situation_severity = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text])))

**Indexes** (4):
- `idx_suggestion_log_learning`
  ```sql
  CREATE INDEX idx_suggestion_log_learning ON public.search_suggestion_analytics USING btree (situation_type, user_action_taken) WHERE (situation_detected = true)
  ```
- `idx_suggestion_log_situation`
  ```sql
  CREATE INDEX idx_suggestion_log_situation ON public.search_suggestion_analytics USING btree (yacht_id, situation_type) WHERE (situation_detected = true)
  ```
- `idx_suggestion_log_yacht`
  ```sql
  CREATE INDEX idx_suggestion_log_yacht ON public.search_suggestion_analytics USING btree (yacht_id, created_at DESC)
  ```
- `suggestion_log_pkey`
  ```sql
  CREATE UNIQUE INDEX suggestion_log_pkey ON public.search_suggestion_analytics USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Service role full access** (ALL)
  - Roles: ['public']
  - USING: `((auth.jwt() ->> 'role'::text) = 'service_role'::text)`
- **Users can view yacht suggestion log** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `search_suggestions`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_id` | uuid | YES |  |  |
| `suggestion_text` | text | NO |  |  |
| `priority` | integer | NO | 0 | enum: int4 |
| `category` | text | NO |  |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `expires_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_31715_1_not_null`: id IS NOT NULL
- **CHECK** `2200_31715_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_31715_4_not_null`: suggestion_text IS NOT NULL
- **CHECK** `2200_31715_5_not_null`: priority IS NOT NULL
- **CHECK** `2200_31715_6_not_null`: category IS NOT NULL
- **CHECK** `2200_31715_9_not_null`: created_at IS NOT NULL

**Indexes** (5):
- `idx_search_suggestions_expires`
  ```sql
  CREATE INDEX idx_search_suggestions_expires ON public.search_suggestions USING btree (expires_at) WHERE (expires_at IS NOT NULL)
  ```
- `idx_search_suggestions_priority`
  ```sql
  CREATE INDEX idx_search_suggestions_priority ON public.search_suggestions USING btree (priority DESC)
  ```
- `idx_search_suggestions_yacht`
  ```sql
  CREATE INDEX idx_search_suggestions_yacht ON public.search_suggestions USING btree (yacht_id)
  ```
- `idx_search_suggestions_yacht_priority`
  ```sql
  CREATE INDEX idx_search_suggestions_yacht_priority ON public.search_suggestions USING btree (yacht_id, priority DESC, created_at DESC)
  ```
- `search_suggestions_pkey`
  ```sql
  CREATE UNIQUE INDEX search_suggestions_pkey ON public.search_suggestions USING btree (id)
  ```

**RLS**: ✅ ENABLED

---

### `search_symptom_catalog`
**Row Count**: 50

**Columns** (6):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `code` | text | NO |  |  |
| `label` | text | NO |  |  |
| `description` | text | YES |  |  |
| `system_type` | text | YES |  |  |
| `severity` | integer | YES |  | enum: int4 |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `code`
- **CHECK** `2200_23938_1_not_null`: code IS NOT NULL
- **CHECK** `2200_23938_2_not_null`: label IS NOT NULL
- **CHECK** `2200_23938_6_not_null`: created_at IS NOT NULL
- **CHECK** `symptom_catalog_severity_check`: ((severity >= 1) AND (severity <= 5))

**Indexes** (1):
- `symptom_catalog_pkey`
  ```sql
  CREATE UNIQUE INDEX symptom_catalog_pkey ON public.search_symptom_catalog USING btree (code)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **Service role full access symptom_catalog** (ALL)
  - Roles: ['service_role']
  - USING: `true`

---

### `search_symptom_reports`
**Row Count**: 0

**Columns** (13):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_node_id` | uuid | YES |  |  |
| `equipment_label` | text | NO |  |  |
| `symptom_code` | text | NO |  |  |
| `symptom_label` | text | NO |  |  |
| `source_type` | text | NO | 'search'::text |  |
| `source_id` | uuid | YES |  |  |
| `resolution_status` | text | NO | 'open'::text |  |
| `resolved_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `resolution_notes` | text | YES |  |  |
| `reported_by` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **FK**: `equipment_node_id` → `search_graph_nodes(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_30074_13_not_null`: created_at IS NOT NULL
- **CHECK** `2200_30074_1_not_null`: id IS NOT NULL
- **CHECK** `2200_30074_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_30074_4_not_null`: equipment_label IS NOT NULL
- **CHECK** `2200_30074_5_not_null`: symptom_code IS NOT NULL
- **CHECK** `2200_30074_6_not_null`: symptom_label IS NOT NULL
- **CHECK** `2200_30074_7_not_null`: source_type IS NOT NULL
- **CHECK** `2200_30074_9_not_null`: resolution_status IS NOT NULL
- **CHECK** `symptom_reports_source_check`: (source_type = ANY (ARRAY['search'::text, 'manual'::text, 'alarm'::text]))
- **CHECK** `symptom_reports_status_check`: (resolution_status = ANY (ARRAY['open'::text, 'acknowledged'::text, 'work_order_created'::text, 'resolved'::text]))

**Indexes** (5):
- `idx_symptom_reports_open`
  ```sql
  CREATE INDEX idx_symptom_reports_open ON public.search_symptom_reports USING btree (yacht_id, resolution_status) WHERE (resolution_status = 'open'::text)
  ```
- `idx_symptom_reports_pattern`
  ```sql
  CREATE INDEX idx_symptom_reports_pattern ON public.search_symptom_reports USING btree (yacht_id, equipment_label, symptom_code, created_at DESC)
  ```
- `idx_symptom_reports_yacht_equip`
  ```sql
  CREATE INDEX idx_symptom_reports_yacht_equip ON public.search_symptom_reports USING btree (yacht_id, equipment_label, created_at DESC)
  ```
- `idx_symptom_reports_yacht_symptom`
  ```sql
  CREATE INDEX idx_symptom_reports_yacht_symptom ON public.search_symptom_reports USING btree (yacht_id, symptom_code, created_at DESC)
  ```
- `symptom_reports_pkey`
  ```sql
  CREATE UNIQUE INDEX symptom_reports_pkey ON public.search_symptom_reports USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Service role full access** (ALL)
  - Roles: ['public']
  - USING: `((auth.jwt() ->> 'role'::text) = 'service_role'::text)`
- **Users can create symptom reports** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `(yacht_id = get_user_yacht_id())`
- **Users can update symptom reports** (UPDATE)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`
- **Users can view yacht symptom reports** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `shopping_list_items`
**Row Count**: 0

**Columns** (15):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `part_id` | uuid | NO |  |  |
| `quantity_requested` | integer | NO | 1 | enum: int4 |
| `priority` | text | YES | 'normal'::text |  |
| `notes` | text | YES |  |  |
| `requested_by` | uuid | NO |  |  |
| `requested_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `status` | text | YES | 'pending'::text |  |
| `purchase_order_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `deleted_by` | uuid | YES |  |  |
| `deletion_reason` | text | YES |  |  |

**Constraints**:
- **PK**: `id`
- **FK**: `part_id` → `pms_parts(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **FK**: `purchase_order_id` → `pms_purchase_orders(id)` ON DELETE SET NULL, ON UPDATE NO ACTION
- **CHECK** `2200_147726_11_not_null`: created_at IS NOT NULL
- **CHECK** `2200_147726_1_not_null`: id IS NOT NULL
- **CHECK** `2200_147726_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_147726_3_not_null`: part_id IS NOT NULL
- **CHECK** `2200_147726_4_not_null`: quantity_requested IS NOT NULL
- **CHECK** `2200_147726_7_not_null`: requested_by IS NOT NULL
- **CHECK** `2200_147726_8_not_null`: requested_at IS NOT NULL
- **CHECK** `shopping_list_items_priority_check`: (priority = ANY (ARRAY['low'::text, 'normal'::text, 'high'::text, 'urgent'::text]))
- **CHECK** `shopping_list_items_quantity_requested_check`: (quantity_requested > 0)
- **CHECK** `shopping_list_items_status_check`: (status = ANY (ARRAY['pending'::text, 'ordered'::text, 'cancelled'::text]))

**Indexes** (3):
- `idx_shopping_list_items_part`
  ```sql
  CREATE INDEX idx_shopping_list_items_part ON public.shopping_list_items USING btree (part_id)
  ```
- `idx_shopping_list_items_yacht_status`
  ```sql
  CREATE INDEX idx_shopping_list_items_yacht_status ON public.shopping_list_items USING btree (yacht_id, status) WHERE (deleted_at IS NULL)
  ```
- `shopping_list_items_pkey`
  ```sql
  CREATE UNIQUE INDEX shopping_list_items_pkey ON public.shopping_list_items USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (2):
- **Authenticated users can view shopping list** (SELECT)
  - Roles: ['authenticated']
  - USING: `(deleted_at IS NULL)`
- **Service role full access** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `situation_detections`
**Row Count**: 0

**Columns** (14):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | YES |  |  |
| `situation_type` | text | NO |  |  |
| `severity` | text | NO |  |  |
| `label` | text | NO |  |  |
| `context` | text | YES |  |  |
| `evidence` | jsonb | YES |  |  |
| `recommendations` | jsonb | YES |  |  |
| `search_query_id` | uuid | YES |  |  |
| `acknowledged` | boolean | YES | false | enum: bool |
| `acknowledged_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `acknowledged_by` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_137328_14_not_null`: created_at IS NOT NULL
- **CHECK** `2200_137328_1_not_null`: id IS NOT NULL
- **CHECK** `2200_137328_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_137328_4_not_null`: situation_type IS NOT NULL
- **CHECK** `2200_137328_5_not_null`: severity IS NOT NULL
- **CHECK** `2200_137328_6_not_null`: label IS NOT NULL

**Indexes** (2):
- `idx_situation_detections_yacht`
  ```sql
  CREATE INDEX idx_situation_detections_yacht ON public.situation_detections USING btree (yacht_id, created_at DESC)
  ```
- `situation_detections_pkey`
  ```sql
  CREATE UNIQUE INDEX situation_detections_pkey ON public.situation_detections USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **vessel_isolation_situation_detections** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

---

### `suggestion_log`
**Row Count**: 0

**Columns** (13):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | YES |  |  |
| `query_text` | text | NO |  |  |
| `intent` | text | YES |  |  |
| `search_query_id` | uuid | YES |  |  |
| `situation_detected` | boolean | YES | false | enum: bool |
| `situation_type` | text | YES |  |  |
| `suggested_actions` | jsonb | YES |  |  |
| `action_taken` | text | YES |  |  |
| `action_taken_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `feedback` | text | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_137338_13_not_null`: created_at IS NOT NULL
- **CHECK** `2200_137338_1_not_null`: id IS NOT NULL
- **CHECK** `2200_137338_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_137338_4_not_null`: query_text IS NOT NULL

**Indexes** (1):
- `suggestion_log_pkey1`
  ```sql
  CREATE UNIQUE INDEX suggestion_log_pkey1 ON public.suggestion_log USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **vessel_isolation_suggestion_log** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

---

### `symptom_reports`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `equipment_label` | text | NO |  |  |
| `symptom_code` | text | NO |  |  |
| `symptom_label` | text | NO |  |  |
| `search_query_id` | uuid | YES |  |  |
| `reported_by` | uuid | YES |  |  |
| `source` | text | NO | 'manual'::text |  |
| `resolved` | boolean | YES | false | enum: bool |
| `resolved_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `resolved_by` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_137317_12_not_null`: created_at IS NOT NULL
- **CHECK** `2200_137317_1_not_null`: id IS NOT NULL
- **CHECK** `2200_137317_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_137317_3_not_null`: equipment_label IS NOT NULL
- **CHECK** `2200_137317_4_not_null`: symptom_code IS NOT NULL
- **CHECK** `2200_137317_5_not_null`: symptom_label IS NOT NULL
- **CHECK** `2200_137317_8_not_null`: source IS NOT NULL

**Indexes** (3):
- `idx_symptom_reports_recurrence`
  ```sql
  CREATE INDEX idx_symptom_reports_recurrence ON public.symptom_reports USING btree (yacht_id, equipment_label, symptom_code, created_at DESC)
  ```
- `idx_symptom_reports_yacht`
  ```sql
  CREATE INDEX idx_symptom_reports_yacht ON public.symptom_reports USING btree (yacht_id, equipment_label, symptom_code)
  ```
- `symptom_reports_pkey1`
  ```sql
  CREATE UNIQUE INDEX symptom_reports_pkey1 ON public.symptom_reports USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (1):
- **vessel_isolation_symptom_reports** (ALL)
  - Roles: ['public']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`

---

### `user_action_history`
**Row Count**: 0

**Columns** (15):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `user_id` | uuid | NO |  |  |
| `action_type` | text | NO |  |  |
| `action_description` | text | NO |  |  |
| `entity_type` | text | NO |  |  |
| `entity_id` | uuid | NO |  |  |
| `entity_display_name` | text | YES |  |  |
| `action_date` | date | NO | CURRENT_DATE |  |
| `action_hour` | integer | NO | EXTRACT(hour FROM now()) | enum: int4 |
| `was_via_search` | boolean | YES | false | enum: bool |
| `search_query` | text | YES |  |  |
| `confirmation_id` | uuid | YES |  |  |
| `ledger_event_id` | uuid | YES |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_135840_10_not_null`: action_hour IS NOT NULL
- **CHECK** `2200_135840_15_not_null`: created_at IS NOT NULL
- **CHECK** `2200_135840_1_not_null`: id IS NOT NULL
- **CHECK** `2200_135840_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_135840_3_not_null`: user_id IS NOT NULL
- **CHECK** `2200_135840_4_not_null`: action_type IS NOT NULL
- **CHECK** `2200_135840_5_not_null`: action_description IS NOT NULL
- **CHECK** `2200_135840_6_not_null`: entity_type IS NOT NULL
- **CHECK** `2200_135840_7_not_null`: entity_id IS NOT NULL
- **CHECK** `2200_135840_9_not_null`: action_date IS NOT NULL

**Indexes** (4):
- `idx_user_action_history_entity`
  ```sql
  CREATE INDEX idx_user_action_history_entity ON public.user_action_history USING btree (entity_type, entity_id)
  ```
- `idx_user_action_history_user_date`
  ```sql
  CREATE INDEX idx_user_action_history_user_date ON public.user_action_history USING btree (user_id, action_date DESC)
  ```
- `idx_user_action_history_user_type`
  ```sql
  CREATE INDEX idx_user_action_history_user_type ON public.user_action_history USING btree (user_id, action_type)
  ```
- `user_action_history_pkey`
  ```sql
  CREATE UNIQUE INDEX user_action_history_pkey ON public.user_action_history USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **user_action_history_insert** (INSERT)
  - Roles: ['authenticated']
  - WITH CHECK: `(user_id = auth.uid())`
- **user_action_history_own** (SELECT)
  - Roles: ['authenticated']
  - USING: `(user_id = auth.uid())`
- **user_action_history_service** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`

---

### `user_added_relations`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | uuid | NO |  |  |
| `created_by_user_id` | uuid | NO |  |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `from_artefact_type` | text | NO |  |  |
| `from_artefact_id` | uuid | NO |  |  |
| `to_artefact_type` | text | NO |  |  |
| `to_artefact_id` | uuid | NO |  |  |
| `is_active` | boolean | NO | true | enum: bool |

**Constraints**:
- **PK**: `id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **UNIQUE**: `yacht_id`, `from_artefact_type`, `from_artefact_id`, `to_artefact_type`, `to_artefact_id`
- **CHECK** `2200_140204_1_not_null`: id IS NOT NULL
- **CHECK** `2200_140204_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_140204_3_not_null`: created_by_user_id IS NOT NULL
- **CHECK** `2200_140204_4_not_null`: created_at IS NOT NULL
- **CHECK** `2200_140204_5_not_null`: from_artefact_type IS NOT NULL
- **CHECK** `2200_140204_6_not_null`: from_artefact_id IS NOT NULL
- **CHECK** `2200_140204_7_not_null`: to_artefact_type IS NOT NULL
- **CHECK** `2200_140204_8_not_null`: to_artefact_id IS NOT NULL
- **CHECK** `2200_140204_9_not_null`: is_active IS NOT NULL

**Indexes** (4):
- `idx_user_relations_from`
  ```sql
  CREATE INDEX idx_user_relations_from ON public.user_added_relations USING btree (yacht_id, from_artefact_type, from_artefact_id) WHERE (is_active = true)
  ```
- `idx_user_relations_to`
  ```sql
  CREATE INDEX idx_user_relations_to ON public.user_added_relations USING btree (yacht_id, to_artefact_type, to_artefact_id) WHERE (is_active = true)
  ```
- `unique_active_user_relation`
  ```sql
  CREATE UNIQUE INDEX unique_active_user_relation ON public.user_added_relations USING btree (yacht_id, from_artefact_type, from_artefact_id, to_artefact_type, to_artefact_id)
  ```
- `user_added_relations_pkey`
  ```sql
  CREATE UNIQUE INDEX user_added_relations_pkey ON public.user_added_relations USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Service role manages user_added_relations** (ALL)
  - Roles: ['service_role']
  - USING: `true`
  - WITH CHECK: `true`
- **user_relations_insert_own_yacht** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `((yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))) AND (created_by_user_id = auth.uid()))`
- **user_relations_select_own_yacht** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid())))`
- **user_relations_update_own** (UPDATE)
  - Roles: ['public']
  - USING: `((yacht_id IN ( SELECT auth_users_profiles.yacht_id
   FROM auth_users_profiles
  WHERE (auth_users_profiles.id = auth.uid()))) AND (created_by_user_id = auth.uid()))`

---

### `yacht_email_configs`
**Row Count**: 0

**Columns** (12):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `contact_id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | text | NO |  |  |
| `vendor` | character varying | YES |  | enum: varchar |
| `contact_name` | character varying | YES |  | enum: varchar |
| `email` | character varying | NO |  | enum: varchar |
| `specialization` | character varying | YES |  | enum: varchar |
| `notes` | text | YES |  |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `user_id` | uuid | YES |  |  |
| `reliability_score` | numeric | YES |  |  |
| `last_contacted` | timestamp with time zone | YES |  | enum: timestamptz |

**Constraints**:
- **PK**: `contact_id`
- **CHECK** `2200_27715_1_not_null`: contact_id IS NOT NULL
- **CHECK** `2200_27715_2_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_27715_5_not_null`: email IS NOT NULL

**Indexes** (3):
- `email_contacts_yacht_pkey`
  ```sql
  CREATE UNIQUE INDEX email_contacts_yacht_pkey ON public.yacht_email_configs USING btree (contact_id)
  ```
- `idx_emails_yacht_last_contacted`
  ```sql
  CREATE INDEX idx_emails_yacht_last_contacted ON public.yacht_email_configs USING btree (last_contacted DESC)
  ```
- `idx_emails_yacht_reliability_score`
  ```sql
  CREATE INDEX idx_emails_yacht_reliability_score ON public.yacht_email_configs USING btree (reliability_score DESC)
  ```

**RLS**: ✅ ENABLED
**Policies** (6):
- **Allow backend read emails** (SELECT)
  - Roles: ['anon', 'authenticated']
  - USING: `true`
- **Service role can manage all contacts** (ALL)
  - Roles: ['public']
  - USING: `(current_setting('role'::text) = 'service_role'::text)`
- **Service role full access contacts** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Service role full access emails_yacht** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can manage own contacts** (ALL)
  - Roles: ['public']
  - USING: `(auth.uid() = user_id)`
- **Users can read own contacts** (SELECT)
  - Roles: ['public']
  - USING: `(auth.uid() = user_id)`

**Triggers** (1):
- `update_email_contacts_yacht_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at_column()

---

### `yacht_fault_records`
**Row Count**: 0

**Columns** (22):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `fault_id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | text | NO |  |  |
| `equipment_type` | character varying | YES |  | enum: varchar |
| `equipment_brand` | character varying | YES |  | enum: varchar |
| `equipment_model` | character varying | YES |  | enum: varchar |
| `fault_code` | character varying | YES |  | enum: varchar |
| `fault_description` | text | YES |  |  |
| `symptoms` | ARRAY | YES |  | enum: _text |
| `severity_level` | character varying | YES |  | enum: varchar |
| `detected_date` | timestamp with time zone | YES | now() | enum: timestamptz |
| `resolved_date` | timestamp with time zone | YES |  | enum: timestamptz |
| `resolution_status` | character varying | YES | 'open'::character varying | enum: varchar |
| `resolution_id` | uuid | YES |  |  |
| `technician_notes` | text | YES |  |  |
| `root_cause` | text | YES |  |  |
| `preventive_measures` | text | YES |  |  |
| `downtime_hours` | numeric | YES |  |  |
| `repair_cost_usd` | numeric | YES |  |  |
| `parts_replaced` | jsonb | YES | '[]'::jsonb |  |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `user_id` | uuid | YES |  |  |

**Constraints**:
- **PK**: `fault_id`
- **CHECK** `2200_27732_1_not_null`: fault_id IS NOT NULL
- **CHECK** `2200_27732_2_not_null`: yacht_id IS NOT NULL

**Indexes** (1):
- `fault_yacht_pkey`
  ```sql
  CREATE UNIQUE INDEX fault_yacht_pkey ON public.yacht_fault_records USING btree (fault_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (4):
- **Service role can manage all faults** (ALL)
  - Roles: ['public']
  - USING: `(current_setting('role'::text) = 'service_role'::text)`
- **Service role full access fault_yacht** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can report faults** (INSERT)
  - Roles: ['public']
  - WITH CHECK: `(auth.uid() = user_id)`
- **Users can update own faults** (UPDATE)
  - Roles: ['public']
  - USING: `(auth.uid() = user_id)`

**Triggers** (1):
- `update_fault_yacht_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at_column()

---

### `yacht_operational_context`
**Row Count**: 0

**Columns** (9):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `yacht_id` | uuid | NO |  |  |
| `current_status` | text | NO | 'in_port'::text |  |
| `next_event_type` | text | YES |  |  |
| `next_event_at` | timestamp with time zone | YES |  | enum: timestamptz |
| `next_event_name` | text | YES |  |  |
| `hot_work_permitted` | boolean | YES | true | enum: bool |
| `guests_on_board` | boolean | YES | false | enum: bool |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_by` | uuid | YES |  |  |

**Constraints**:
- **PK**: `yacht_id`
- **FK**: `yacht_id` → `yacht_registry(id)` ON DELETE CASCADE, ON UPDATE NO ACTION
- **CHECK** `2200_30048_1_not_null`: yacht_id IS NOT NULL
- **CHECK** `2200_30048_2_not_null`: current_status IS NOT NULL
- **CHECK** `2200_30048_8_not_null`: updated_at IS NOT NULL
- **CHECK** `vessel_context_event_type_check`: ((next_event_type IS NULL) OR (next_event_type = ANY (ARRAY['charter'::text, 'survey'::text, 'crossing'::text, 'refit'::text, 'owner_trip'::text])))
- **CHECK** `vessel_context_status_check`: (current_status = ANY (ARRAY['in_port'::text, 'at_anchor'::text, 'underway'::text, 'in_yard'::text, 'laid_up'::text]))

**Indexes** (1):
- `vessel_context_pkey`
  ```sql
  CREATE UNIQUE INDEX vessel_context_pkey ON public.yacht_operational_context USING btree (yacht_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Officers can update yacht context** (UPDATE)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`
- **Service role full access** (ALL)
  - Roles: ['public']
  - USING: `((auth.jwt() ->> 'role'::text) = 'service_role'::text)`
- **Users can view own yacht context** (SELECT)
  - Roles: ['public']
  - USING: `(yacht_id = get_user_yacht_id())`

---

### `yacht_registry`
**Row Count**: 1

**Columns** (13):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() |  |
| `name` | text | NO |  |  |
| `imo` | text | YES |  |  |
| `mmsi` | text | YES |  |  |
| `flag_state` | text | YES |  |  |
| `length_m` | numeric | YES |  |  |
| `owner_ref` | text | YES |  |  |
| `yacht_secret_hash` | text | NO |  |  |
| `nas_root_path` | text | YES |  |  |
| `status` | text | YES | 'active'::text |  |
| `metadata` | jsonb | YES | '{}'::jsonb |  |
| `created_at` | timestamp with time zone | NO | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | NO | now() | enum: timestamptz |

**Constraints**:
- **PK**: `id`
- **CHECK** `2200_17921_12_not_null`: created_at IS NOT NULL
- **CHECK** `2200_17921_13_not_null`: updated_at IS NOT NULL
- **CHECK** `2200_17921_1_not_null`: id IS NOT NULL
- **CHECK** `2200_17921_2_not_null`: name IS NOT NULL
- **CHECK** `2200_17921_8_not_null`: yacht_secret_hash IS NOT NULL
- **CHECK** `yachts_status_check`: (status = ANY (ARRAY['active'::text, 'inactive'::text, 'demo'::text]))
- **CHECK** `yachts_yacht_secret_hash_check`: (yacht_secret_hash ~ '^\$2[aby]\$'::text)

**Indexes** (2):
- `idx_yachts_status`
  ```sql
  CREATE INDEX idx_yachts_status ON public.yacht_registry USING btree (status)
  ```
- `yachts_pkey`
  ```sql
  CREATE UNIQUE INDEX yachts_pkey ON public.yacht_registry USING btree (id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Managers can update yacht settings** (UPDATE)
  - Roles: ['public']
  - USING: `((id = get_user_yacht_id()) AND is_manager())`
- **Service role full access yachts** (ALL)
  - Roles: ['service_role']
  - USING: `true`
- **Users can view own yacht** (SELECT)
  - Roles: ['public']
  - USING: `(id = get_user_yacht_id())`

---

### `yacht_resolution_records`
**Row Count**: 0

**Columns** (22):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `resolution_id` | uuid | NO | gen_random_uuid() |  |
| `yacht_id` | text | NO |  |  |
| `resolution_title` | character varying | YES |  | enum: varchar |
| `resolution_description` | text | YES |  |  |
| `resolution_steps` | jsonb | YES | '[]'::jsonb |  |
| `equipment_type` | character varying | YES |  | enum: varchar |
| `applicable_models` | ARRAY | YES |  | enum: _text |
| `success_count` | integer | YES | 0 | enum: int4 |
| `failure_count` | integer | YES | 0 | enum: int4 |
| `average_time_minutes` | integer | YES |  | enum: int4 |
| `difficulty_level` | character varying | YES |  | enum: varchar |
| `required_expertise` | ARRAY | YES |  | enum: _text |
| `safety_warnings` | ARRAY | YES |  | enum: _text |
| `tools_required` | ARRAY | YES |  | enum: _text |
| `parts_required` | jsonb | YES | '[]'::jsonb |  |
| `estimated_cost_range` | character varying | YES |  | enum: varchar |
| `created_by` | character varying | YES |  | enum: varchar |
| `approved_by` | character varying | YES |  | enum: varchar |
| `approval_date` | timestamp with time zone | YES |  | enum: timestamptz |
| `is_verified` | boolean | YES | false | enum: bool |
| `created_at` | timestamp with time zone | YES | now() | enum: timestamptz |
| `updated_at` | timestamp with time zone | YES | now() | enum: timestamptz |

**Constraints**:
- **PK**: `resolution_id`
- **CHECK** `2200_27767_1_not_null`: resolution_id IS NOT NULL
- **CHECK** `2200_27767_2_not_null`: yacht_id IS NOT NULL

**Indexes** (1):
- `resolution_yacht_pkey`
  ```sql
  CREATE UNIQUE INDEX resolution_yacht_pkey ON public.yacht_resolution_records USING btree (resolution_id)
  ```

**RLS**: ✅ ENABLED
**Policies** (3):
- **Public read access to resolutions** (SELECT)
  - Roles: ['public']
  - USING: `true`
- **Service role can manage resolutions** (ALL)
  - Roles: ['public']
  - USING: `(current_setting('role'::text) = 'service_role'::text)`
- **Service role full access resolution_yacht** (ALL)
  - Roles: ['service_role']
  - USING: `true`

**Triggers** (1):
- `update_resolution_yacht_updated_at` (BEFORE UPDATE)
  - Action: EXECUTE FUNCTION update_updated_at_column()

---

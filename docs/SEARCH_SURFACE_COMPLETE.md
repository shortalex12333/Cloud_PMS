# COMPLETE SEARCH SURFACE REGISTRY
## Every Table, Column, Entity Type, and Routing Gap

---

## SUMMARY

| Metric | Count |
|--------|-------|
| Tables with yacht_id | 82 |
| Total Columns | 819 |
| Text Columns (searchable) | 515 |
| Columns with Routing Gap | 533 |

---

## ENTITY TYPES REFERENCE

### PART_NUMBER
- **Description**: Part number like ENG-0008-103
- **Match Modes**: EXACT, ILIKE
- **Examples**: ENG-0008-103, PMP-0018-280, 12345678

### FAULT_CODE
- **Description**: Fault/error code like E047, F-123
- **Match Modes**: EXACT, ILIKE
- **Examples**: E047, F-123, ERR001

### SERIAL_NUMBER
- **Description**: Equipment serial number
- **Match Modes**: EXACT, ILIKE
- **Examples**: SN-12345, ABC1234567

### WORK_ORDER_ID
- **Description**: Work order identifier
- **Match Modes**: EXACT
- **Examples**: WO-12345, WO123456

### PART_NAME
- **Description**: Part name like 'Fuel Filter', 'Glow Plug'
- **Match Modes**: ILIKE, TRIGRAM
- **Examples**: Fuel Filter, Glow Plug, Impeller

### EQUIPMENT_NAME
- **Description**: Equipment name like 'Main Engine', 'Generator 1'
- **Match Modes**: ILIKE, TRIGRAM
- **Examples**: Main Engine, Generator 1, Watermaker

### SYSTEM_NAME
- **Description**: System name like 'Electrical System', 'Fuel System'
- **Match Modes**: ILIKE, TRIGRAM
- **Examples**: Electrical System, Fuel System, HVAC

### COMPONENT_NAME
- **Description**: Component name
- **Match Modes**: ILIKE, TRIGRAM
- **Examples**: Turbocharger, Heat Exchanger, Injector

### MANUFACTURER
- **Description**: Manufacturer/brand name
- **Match Modes**: ILIKE, TRIGRAM
- **Examples**: Caterpillar, Cummins, Kohler

### SUPPLIER_NAME
- **Description**: Supplier/vendor name
- **Match Modes**: ILIKE, TRIGRAM
- **Examples**: Marine Parts Direct, West Marine

### SYMPTOM_NAME
- **Description**: Symptom description like 'vibration', 'overheating'
- **Match Modes**: ILIKE, TRIGRAM, VECTOR
- **Examples**: vibration, overheating, smoke

### STOCK_LOCATION
- **Description**: Inventory storage location
- **Match Modes**: EXACT, ILIKE
- **Examples**: Engine Room, Lazarette, Agent - Palma

### EQUIPMENT_LOCATION
- **Description**: Where equipment is installed
- **Match Modes**: ILIKE
- **Examples**: Engine Room, Flybridge, Forepeak

### STATUS
- **Description**: Status values like 'open', 'closed', 'pending'
- **Match Modes**: EXACT
- **Examples**: open, closed, pending

### PRIORITY
- **Description**: Priority levels
- **Match Modes**: EXACT
- **Examples**: high, medium, low

### SEVERITY
- **Description**: Severity levels for faults
- **Match Modes**: EXACT
- **Examples**: critical, warning, info

### DOCUMENT_QUERY
- **Description**: Free text search in documents
- **Match Modes**: ILIKE, TRIGRAM, VECTOR
- **Examples**: oil change procedure, wiring diagram, troubleshooting

### SECTION_NAME
- **Description**: Document section title
- **Match Modes**: ILIKE
- **Examples**: Maintenance, Safety, Specifications

### DOC_TYPE
- **Description**: Document type
- **Match Modes**: EXACT
- **Examples**: manual, procedure, schematic

### CANONICAL_ENTITY
- **Description**: Normalized entity label
- **Match Modes**: EXACT, ILIKE
- **Examples**: MAIN_ENGINE, FUEL_SYSTEM, BOW_THRUSTER

### NODE_TYPE
- **Description**: Graph node type
- **Match Modes**: EXACT
- **Examples**: equipment, system, component

### FREE_TEXT
- **Description**: Any unclassified text query
- **Match Modes**: ILIKE, TRIGRAM, VECTOR
- **Examples**: anything

### UNKNOWN
- **Description**: Unrecognized query type
- **Match Modes**: ILIKE, TRIGRAM
- **Examples**: 


---

## ALL TABLES AND COLUMNS

### alias_crew
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| crew_id | uuid |  | EXACT | - | - |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | - | SYMPTOM_NAME, FREE_TEXT |
| alias_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |


### alias_documents
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| document_id | uuid |  | EXACT | - | - |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | - | SYMPTOM_NAME, FREE_TEXT |
| alias_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |


### alias_equipment
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | - | SYMPTOM_NAME, FREE_TEXT |
| is_primary | boolean |  | EXACT | - | - |
| confidence | numeric |  | EXACT, RANGE | - | - |
| source | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| candidate_id | uuid |  | EXACT | - | - |
| master_candidate_id | uuid |  | EXACT | - | - |
| deployed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### alias_faults
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| fault_id | uuid |  | EXACT | - | - |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | - | SYMPTOM_NAME, FREE_TEXT |
| alias_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| source | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| master_candidate_id | uuid |  | EXACT | - | - |
| deployed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### alias_parts
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| part_id | uuid |  | EXACT | - | - |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | - | SYMPTOM_NAME, FREE_TEXT |
| alias_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| source | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| candidate_id | uuid |  | EXACT | - | - |
| master_candidate_id | uuid |  | EXACT | - | - |
| deployed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### alias_symptoms
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| symptom_id | uuid |  | EXACT | - | - |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | SYMPTOM_NAME | FREE_TEXT |
| alias_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| source | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| candidate_id | uuid |  | EXACT | - | - |
| master_candidate_id | uuid |  | EXACT | - | - |
| deployed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| symptom_code | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### alias_systems
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| system_type | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | SYSTEM_NAME | SYMPTOM_NAME, FREE_TEXT |
| alias_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| source | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| master_candidate_id | uuid |  | EXACT | - | - |
| deployed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### alias_tasks
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| task_id | uuid |  | EXACT | - | - |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | - | SYMPTOM_NAME, FREE_TEXT |
| alias_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |


### alias_work_orders
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| work_order_id | uuid |  | EXACT | - | - |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | - | SYMPTOM_NAME, FREE_TEXT |
| alias_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |


### auth_api_keys
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| key_prefix | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| hashed_key | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| scopes | array |  |  | - | - |
| created_by | uuid |  | EXACT | - | - |
| expires_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| last_used_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| is_active | boolean |  | EXACT | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### auth_guest_preferences
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| guest_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| guest_node_id | uuid |  | EXACT | - | - |
| preference_category | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| preference_key | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| preference_value | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| notes | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| source_trip_id | uuid |  | EXACT | - | - |


### auth_microsoft_tokens
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| microsoft_user_id | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| original_email | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| microsoft_email | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| display_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| microsoft_access_token | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| microsoft_refresh_token | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| token_expires_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| token_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| scopes | array |  |  | - | - |
| client_id | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| client_secret | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### auth_role_assignments
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| role | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| scopes | array |  |  | - | - |
| is_active | boolean |  | EXACT | - | - |
| valid_from | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| valid_until | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| assigned_by | uuid |  | EXACT | - | - |
| assigned_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### auth_users
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| auth_user_id | uuid |  | EXACT | - | - |
| email | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| is_active | boolean |  | EXACT | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### auth_users_yacht
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| role | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| permissions | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| notification_settings | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| total_queries | integer |  | EXACT, RANGE | - | - |
| email | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### chat_agent_configs
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| agent_secret_hash | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| device_info | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| last_seen_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| is_active | boolean |  | EXACT | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### chat_messages
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| session_id | uuid |  | EXACT | - | - |
| role | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| content | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| timestamp | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| message_index | integer |  | EXACT, RANGE | - | - |
| sources | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| tokens_used | integer |  | EXACT, RANGE | - | - |
| confidence_score | numeric |  | EXACT, RANGE | - | - |


### chat_session_summaries
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| title | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| folder | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| search_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| message_count | integer |  | EXACT, RANGE | - | - |
| is_archived | boolean |  | EXACT | - | - |
| deleted | boolean |  | EXACT | - | - |
| first_message_preview | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| last_message_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### chat_sessions
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| title | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| folder | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| search_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| session_metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| is_archived | boolean |  | EXACT | - | - |
| message_count | integer |  | EXACT, RANGE | - | - |
| deleted | boolean |  | EXACT | - | - |


### dash_action_logs
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| action_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| action_status | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| request_payload | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| response_payload | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| context | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| error_code | text | FAULT_CODE, FREE_TEXT | EXACT, ILIKE | - | FAULT_CODE, FREE_TEXT |
| error_message | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| started_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| completed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| duration_ms | integer |  | EXACT, RANGE | - | - |
| source_ip | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| user_agent | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### dash_crew_hours_compliance
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| hours_worked | numeric |  | EXACT, RANGE | - | - |
| hours_of_rest | numeric |  | EXACT, RANGE | - | - |
| violations | boolean |  | EXACT | - | - |
| notes | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### dash_handover_items
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| handover_id | uuid |  | EXACT | - | - |
| source_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| source_id | uuid |  | EXACT | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| title | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| priority | text | PRIORITY | ILIKE | - | PRIORITY |
| status | text | STATUS | ILIKE | - | STATUS |


### dash_handover_records
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| handover_id | uuid |  | EXACT | - | - |
| user_id | uuid |  | EXACT | - | - |
| solution_id | uuid |  | EXACT | - | - |
| document_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| document_path | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| document_page | numeric |  | EXACT, RANGE | - | - |
| system_affected | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| fault_code | text | FAULT_CODE, FREE_TEXT | EXACT, ILIKE | - | FAULT_CODE, FREE_TEXT |
| symptoms | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| actions_taken | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| duration_minutes | integer |  | EXACT, RANGE | - | - |
| notes | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| status | text | STATUS | ILIKE | - | STATUS |
| completed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| document_source | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| entities | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### dash_intelligence_snapshot
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| snapshot_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| high_risk_equipment | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| risk_movements | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| unstable_systems | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| patterns_7d | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| overdue_critical | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| inventory_gaps | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| inspections_due | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| crew_frustration | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| summary_stats | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| generated_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| generation_duration_ms | integer |  | EXACT, RANGE | - | - |
| data_freshness_hours | numeric |  | EXACT, RANGE | - | - |
| valid_until | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| is_stale | boolean |  | EXACT | - | - |


### dash_legacy_view
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_overview | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| equipment_count | integer | EQUIPMENT_NAME, FREE_TEXT | EXACT, RANGE | - | EQUIPMENT_NAME, FREE_TEXT |
| equipment_by_status | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| work_orders_overview | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| work_orders_count | integer |  | EXACT, RANGE | - | - |
| work_orders_by_status | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| work_orders_overdue_count | integer |  | EXACT, RANGE | - | - |
| inventory_overview | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| inventory_count | integer |  | EXACT, RANGE | - | - |
| inventory_low_stock_count | integer |  | EXACT, RANGE | - | - |
| certificates_overview | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| certificates_count | integer |  | EXACT, RANGE | - | - |
| certificates_expiring_soon | integer |  | EXACT, RANGE | - | - |
| fault_history | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| faults_active_count | integer |  | EXACT, RANGE | - | - |
| faults_resolved_30d | integer |  | EXACT, RANGE | - | - |
| scheduled_maintenance | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| maintenance_upcoming_7d | integer |  | EXACT, RANGE | - | - |
| maintenance_overdue | integer |  | EXACT, RANGE | - | - |
| parts_usage | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| documents_summary | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| documents_total | integer |  | EXACT, RANGE | - | - |
| generated_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| valid_until | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### dash_notifications
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| title | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| message | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| priority | text | PRIORITY | ILIKE | - | PRIORITY |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| is_read | boolean |  | EXACT | - | - |
| read_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### dash_predictive_equipment_risk
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| risk_score | numeric |  | EXACT, RANGE | - | - |
| risk_level | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| trend | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| trend_delta | numeric |  | EXACT, RANGE | - | - |
| contributing_factors | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| last_calculated_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| previous_risk_score | numeric |  | EXACT, RANGE | - | - |


### dash_predictive_insights
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| insight_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| title | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| recommendation | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| severity | text | SEVERITY | ILIKE | - | SEVERITY |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| acknowledged | boolean |  | EXACT | - | - |
| acknowledged_by | uuid |  | EXACT | - | - |
| acknowledged_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| dismissed | boolean |  | EXACT | - | - |
| dismissed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| expires_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### dash_safety_drills
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| drill_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| drill_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| conducted_by | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| participants | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| duration_minutes | integer |  | EXACT, RANGE | - | - |
| outcome | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| notes | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| document_id | uuid |  | EXACT | - | - |


### doc_metadata
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| source | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| original_path | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| filename | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| content_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| size_bytes | integer |  | EXACT, RANGE | - | - |
| sha256 | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| storage_path | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| equipment_ids | array | EQUIPMENT_NAME, FREE_TEXT |  | - | EQUIPMENT_NAME, FREE_TEXT |
| tags | array |  |  | - | - |
| indexed | boolean |  | EXACT | - | - |
| indexed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| system_path | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| doc_type | text | DOC_TYPE | ILIKE | - | DOC_TYPE |
| oem | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| model | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| system_type | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |


### doc_sop_procedures
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| equipment | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| title | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| query | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| content_markdown | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| source_chunks | array |  |  | - | - |
| version | integer |  | EXACT, RANGE | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### doc_yacht_library
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| document_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| document_path | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| document_type | text | DOC_TYPE | ILIKE | - | DOC_TYPE |
| times_accessed | integer |  | EXACT, RANGE | - | - |
| times_helpful | integer |  | EXACT, RANGE | - | - |
| times_not_helpful | integer |  | EXACT, RANGE | - | - |
| equipment_covered | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| last_used | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| total_uses | integer |  | EXACT, RANGE | - | - |
| successful_uses | integer |  | EXACT, RANGE | - | - |
| effectiveness_score | numeric |  | EXACT, RANGE | - | - |
| department | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| fault_code_matches | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| user_id | uuid |  | EXACT | - | - |
| helpful_count | integer |  | EXACT, RANGE | - | - |
| chunk_id | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| chunk_text | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| chunk_index | integer |  | EXACT, RANGE | - | - |
| page_num | integer |  | EXACT, RANGE | - | - |
| entities_found | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| entity_weights | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| query | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| session_id | uuid |  | EXACT | - | - |
| score | numeric |  | EXACT, RANGE | - | - |
| chunk_metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| is_chunk | boolean |  | EXACT | - | - |
| conversion_rate | numeric |  | EXACT, RANGE | - | - |


### document_chunks
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| document_id | uuid |  | EXACT | - | - |
| chunk_index | integer |  | EXACT, RANGE | - | - |
| text | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| page_number | integer |  | EXACT, RANGE | - | - |
| embedding | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| equipment_ids | array | EQUIPMENT_NAME, FREE_TEXT |  | - | EQUIPMENT_NAME, FREE_TEXT |
| fault_codes | array |  |  | - | - |
| tags | array |  |  | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| content | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| graph_extracted | boolean |  | EXACT | - | - |
| graph_extracted_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| section_title | text | SECTION_NAME, FREE_TEXT | ILIKE | - | SECTION_NAME, FREE_TEXT |
| doc_type | text | DOC_TYPE | ILIKE | - | DOC_TYPE |
| system_tag | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| graph_extract_status | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| graph_extract_error | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| section_path | array | SECTION_NAME, FREE_TEXT |  | - | SECTION_NAME, FREE_TEXT |
| section_type | text | SECTION_NAME, FREE_TEXT | ILIKE | - | SECTION_NAME, FREE_TEXT |
| is_section_entry | boolean | SECTION_NAME, FREE_TEXT | EXACT | - | SECTION_NAME, FREE_TEXT |
| symptom_codes | array |  |  | - | - |
| graph_extract_ts | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### document_counts_by_department
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| department | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| document_count | integer |  | EXACT, RANGE | - | - |
| total_size_bytes | numeric |  | EXACT, RANGE | - | - |
| indexed_count | integer |  | EXACT, RANGE | - | - |
| pending_count | integer |  | EXACT, RANGE | - | - |


### document_directory_tree
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| level_1 | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| level_2 | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| level_3 | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| document_count | integer |  | EXACT, RANGE | - | - |


### documents
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| source | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| original_path | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| filename | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| content_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| size_bytes | integer |  | EXACT, RANGE | - | - |
| sha256 | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| storage_path | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| equipment_ids | array | EQUIPMENT_NAME, FREE_TEXT |  | - | EQUIPMENT_NAME, FREE_TEXT |
| tags | array |  |  | - | - |
| indexed | boolean |  | EXACT | - | - |
| indexed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| system_path | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| doc_type | text | DOC_TYPE | ILIKE | - | DOC_TYPE |
| oem | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| model | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| system_type | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |


### entity_staging
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| entity_type | text | NODE_TYPE | ILIKE | - | NODE_TYPE |
| entity_value | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| canonical_label | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| source_chunk_id | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| source_document_id | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| source_storage_path | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| attributes | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| status | text | STATUS | ILIKE | - | STATUS |
| error_message | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| processed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| graph_node_id | uuid |  | EXACT | - | - |


### equipment
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| parent_id | uuid |  | EXACT | - | - |
| name | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| code | text | FAULT_CODE, FREE_TEXT | EXACT, ILIKE | - | FAULT_CODE, FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| location | text | FREE_TEXT, EQUIPMENT_LOCATION | ILIKE | - | FREE_TEXT, EQUIPMENT_LOCATION |
| manufacturer | text | MANUFACTURER, FREE_TEXT | TRIGRAM, ILIKE | - | MANUFACTURER, FREE_TEXT |
| model | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| serial_number | text | SERIAL_NUMBER, FREE_TEXT | EXACT, ILIKE | - | SERIAL_NUMBER, FREE_TEXT |


### equipment_aliases
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | - | SYMPTOM_NAME, FREE_TEXT |
| alias_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |


### graph_edges
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| from_node_id | uuid |  | EXACT | - | - |
| to_node_id | uuid |  | EXACT | - | - |
| edge_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| source_chunk_id | uuid |  | EXACT | - | - |
| source_document_id | uuid |  | EXACT | - | - |
| properties | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| embedding | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### graph_nodes
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| node_type | text | NODE_TYPE | ILIKE | NODE_TYPE | - |
| label | text | FREE_TEXT | ILIKE | SYSTEM_NAME, UNKNOWN, FREE_TEXT, EQUIPMENT_NAME, COMPONENT_NAME | - |
| normalized_label | text | CANONICAL_ENTITY | ILIKE | CANONICAL_ENTITY, SYSTEM_NAME | - |
| source_chunk_id | uuid |  | EXACT | - | - |
| source_document_id | uuid |  | EXACT | - | - |
| properties | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| extraction_source | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| embedding | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### log_events
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| event_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| entity_type | text | NODE_TYPE | ILIKE | - | NODE_TYPE |
| entity_id | uuid |  | EXACT | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| session_id | uuid |  | EXACT | - | - |


### log_pipeline_execution
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| document_id | uuid |  | EXACT | - | - |
| step | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| status | text | STATUS | ILIKE | - | STATUS |
| message | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| error_details | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| duration_ms | integer |  | EXACT, RANGE | - | - |


### maintenance_facts
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_node_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| part_node_id | uuid |  | EXACT | - | - |
| system_node_id | uuid | FREE_TEXT, SYSTEM_NAME | EXACT | - | FREE_TEXT, SYSTEM_NAME |
| action | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| interval_hours | integer |  | EXACT, RANGE | - | - |
| interval_days | integer |  | EXACT, RANGE | - | - |
| interval_description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| source_chunk_id | uuid |  | EXACT | - | - |
| source_document_id | uuid |  | EXACT | - | - |
| confidence | numeric |  | EXACT, RANGE | - | - |
| properties | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_crew_certificates
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| person_node_id | uuid |  | EXACT | - | - |
| person_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| certificate_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| certificate_number | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| issuing_authority | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| issue_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| expiry_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| document_id | uuid |  | EXACT | - | - |
| properties | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_equipment
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| parent_id | uuid |  | EXACT | - | - |
| name | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | EQUIPMENT_NAME | FREE_TEXT |
| code | text | FAULT_CODE, FREE_TEXT | EXACT, ILIKE | - | FAULT_CODE, FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| location | text | FREE_TEXT, EQUIPMENT_LOCATION | ILIKE | EQUIPMENT_LOCATION | FREE_TEXT |
| manufacturer | text | MANUFACTURER, FREE_TEXT | TRIGRAM, ILIKE | - | MANUFACTURER, FREE_TEXT |
| model | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| serial_number | text | SERIAL_NUMBER, FREE_TEXT | EXACT, ILIKE | SERIAL_NUMBER | FREE_TEXT |
| installed_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| criticality | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| system_type | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| attention_flag | boolean |  | EXACT | - | - |
| attention_reason | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| attention_updated_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_equipment_parts_bom
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| part_id | uuid |  | EXACT | - | - |
| quantity_required | integer |  | EXACT, RANGE | - | - |
| notes | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_faults
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| fault_code | text | FAULT_CODE, FREE_TEXT | EXACT, ILIKE | - | FAULT_CODE, FREE_TEXT |
| title | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| severity | text | SEVERITY | ILIKE | STATUS | SEVERITY |
| detected_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| resolved_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| resolved_by | uuid |  | EXACT | - | - |
| work_order_id | uuid |  | EXACT | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_inventory_stock
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| part_id | uuid |  | EXACT | - | - |
| location | text | STOCK_LOCATION, FREE_TEXT | ILIKE | - | STOCK_LOCATION, FREE_TEXT |
| quantity | integer |  | EXACT, RANGE | - | - |
| min_quantity | integer |  | EXACT, RANGE | - | - |
| max_quantity | integer |  | EXACT, RANGE | - | - |
| reorder_quantity | integer |  | EXACT, RANGE | - | - |
| last_counted_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_notes
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| work_order_id | uuid |  | EXACT | - | - |
| fault_id | uuid |  | EXACT | - | - |
| text | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| note_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| created_by | uuid |  | EXACT | - | - |
| attachments | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_parts
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| name | text | PART_NAME, FREE_TEXT | TRIGRAM, ILIKE | UNKNOWN, PART_NAME, FREE_TEXT | - |
| part_number | text | PART_NUMBER, FREE_TEXT | EXACT, ILIKE | PART_NUMBER | FREE_TEXT |
| manufacturer | text | MANUFACTURER, FREE_TEXT | TRIGRAM, ILIKE | MANUFACTURER | FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| category | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| model_compatibility | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| search_embedding | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| embedding_text | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_purchase_order_items
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| purchase_order_id | uuid |  | EXACT | - | - |
| part_id | uuid |  | EXACT | - | - |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| quantity_ordered | integer |  | EXACT, RANGE | - | - |
| quantity_received | integer |  | EXACT, RANGE | - | - |
| unit_price | numeric |  | EXACT, RANGE | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_purchase_orders
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| supplier_id | uuid |  | EXACT | - | - |
| po_number | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| status | text | STATUS | ILIKE | - | STATUS |
| ordered_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| received_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| currency | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_suppliers
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| name | text | SUPPLIER_NAME, FREE_TEXT | ILIKE | MANUFACTURER, SUPPLIER_NAME | FREE_TEXT |
| contact_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| email | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| phone | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| address | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| preferred | boolean |  | EXACT | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_vessel_certificates
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| certificate_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| certificate_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| certificate_number | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| issuing_authority | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| issue_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| expiry_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| last_survey_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| next_survey_due | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| status | text | STATUS | ILIKE | - | STATUS |
| document_id | uuid |  | EXACT | - | - |
| properties | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_voyage_log
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| voyage_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| voyage_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| departure_port | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| departure_port_node_id | uuid |  | EXACT | - | - |
| arrival_port | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| arrival_port_node_id | uuid |  | EXACT | - | - |
| departure_time | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| arrival_time | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| distance_nm | numeric |  | EXACT, RANGE | - | - |
| fuel_consumed_liters | numeric |  | EXACT, RANGE | - | - |
| properties | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_work_order_history
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| work_order_id | uuid |  | EXACT | - | - |
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| completed_by | uuid |  | EXACT | - | - |
| completed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| notes | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| hours_logged | integer |  | EXACT, RANGE | - | - |
| status_on_completion | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| parts_used | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| documents_used | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| faults_related | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### pms_work_orders
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| title | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| priority | text | PRIORITY | ILIKE | PRIORITY | - |
| status | text | STATUS | ILIKE | STATUS | - |
| due_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| due_hours | integer |  | EXACT, RANGE | - | - |
| last_completed_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| last_completed_hours | integer |  | EXACT, RANGE | - | - |
| frequency | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| created_by | uuid |  | EXACT | - | - |
| updated_by | uuid |  | EXACT | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### relationship_staging
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| from_canonical | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| to_canonical | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| relationship_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| evidence | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| source_chunk_id | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| status | text | STATUS | ILIKE | - | STATUS |
| error_message | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| processed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| graph_edge_id | uuid |  | EXACT | - | - |


### search_document_chunks
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| document_id | uuid |  | EXACT | - | - |
| chunk_index | integer |  | EXACT, RANGE | - | - |
| text | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| page_number | integer |  | EXACT, RANGE | - | - |
| embedding | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| equipment_ids | array | EQUIPMENT_NAME, FREE_TEXT |  | - | EQUIPMENT_NAME, FREE_TEXT |
| fault_codes | array |  |  | - | - |
| tags | array |  |  | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| content | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | PROCEDURE_SEARCH, SYMPTOM_NAME, UNKNOWN, DOCUMENT_QUERY, FREE_TEXT | - |
| graph_extracted | boolean |  | EXACT | - | - |
| graph_extracted_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| section_title | text | SECTION_NAME, FREE_TEXT | ILIKE | SECTION_NAME | FREE_TEXT |
| doc_type | text | DOC_TYPE | ILIKE | DOC_TYPE | - |
| system_tag | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| graph_extract_status | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| graph_extract_error | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| section_path | array | SECTION_NAME, FREE_TEXT |  | - | SECTION_NAME, FREE_TEXT |
| section_type | text | SECTION_NAME, FREE_TEXT | ILIKE | - | SECTION_NAME, FREE_TEXT |
| is_section_entry | boolean | SECTION_NAME, FREE_TEXT | EXACT | - | SECTION_NAME, FREE_TEXT |
| symptom_codes | array |  |  | - | - |
| graph_extract_ts | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### search_embedding_queue
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| document_id | uuid |  | EXACT | - | - |
| status | text | STATUS | ILIKE | - | STATUS |
| error_message | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| started_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| completed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### search_fault_code_catalog
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_type | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| manufacturer | text | MANUFACTURER, FREE_TEXT | TRIGRAM, ILIKE | - | MANUFACTURER, FREE_TEXT |
| code | text | FAULT_CODE, FREE_TEXT | EXACT, ILIKE | FAULT_CODE | FREE_TEXT |
| name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| severity | text | SEVERITY | ILIKE | SEVERITY | - |
| symptoms | array |  |  | - | - |
| causes | array |  |  | - | - |
| diagnostic_steps | array |  |  | - | - |
| resolution_steps | array |  |  | - | - |
| related_parts | array |  |  | - | - |
| source_document_id | uuid |  | EXACT | - | - |
| source_chunk_id | uuid |  | EXACT | - | - |


### search_graph_edges
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| from_node_id | uuid |  | EXACT | - | - |
| to_node_id | uuid |  | EXACT | - | - |
| edge_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| source_chunk_id | uuid |  | EXACT | - | - |
| source_document_id | uuid |  | EXACT | - | - |
| properties | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| embedding | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### search_graph_nodes
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| node_type | text | NODE_TYPE | ILIKE | - | NODE_TYPE |
| label | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| normalized_label | text | CANONICAL_ENTITY | ILIKE | - | CANONICAL_ENTITY |
| source_chunk_id | uuid |  | EXACT | - | - |
| source_document_id | uuid |  | EXACT | - | - |
| properties | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| extraction_source | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| embedding | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### search_maintenance_facts
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_node_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| part_node_id | uuid |  | EXACT | - | - |
| system_node_id | uuid | FREE_TEXT, SYSTEM_NAME | EXACT | - | FREE_TEXT, SYSTEM_NAME |
| action | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| interval_hours | integer |  | EXACT, RANGE | - | - |
| interval_days | integer |  | EXACT, RANGE | - | - |
| interval_description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| source_chunk_id | uuid |  | EXACT | - | - |
| source_document_id | uuid |  | EXACT | - | - |
| confidence | numeric |  | EXACT, RANGE | - | - |
| properties | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### search_manual_embeddings
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| equipment | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| file_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| file_size | integer |  | EXACT, RANGE | - | - |
| chunk_text | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| chunk_index | integer |  | EXACT, RANGE | - | - |
| embedding | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### search_ocred_pages
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| document_id | uuid |  | EXACT | - | - |
| page_number | integer |  | EXACT, RANGE | - | - |
| raw_text | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### search_query_logs
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| query_text | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| interpreted_intent | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| entities | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| latency_ms | integer |  | EXACT, RANGE | - | - |
| success | boolean |  | EXACT | - | - |


### search_suggestion_analytics
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| user_id | uuid |  | EXACT | - | - |
| query_text | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| intent | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| search_query_id | uuid |  | EXACT | - | - |
| situation_detected | boolean |  | EXACT | - | - |
| situation_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| situation_severity | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| situation_context | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| suggested_actions | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| evidence_provided | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| user_action_taken | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| user_action_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### search_suggestions
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| suggestion_text | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| priority | integer | PRIORITY | EXACT, RANGE | - | PRIORITY |
| category | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| expires_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### search_symptom_reports
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_node_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| equipment_label | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| symptom_code | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| symptom_label | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| source_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| source_id | uuid |  | EXACT | - | - |
| resolution_status | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| resolved_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| resolution_notes | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| reported_by | uuid |  | EXACT | - | - |


### symptom_aliases
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| symptom_id | uuid |  | EXACT | - | - |
| symptom_code | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| alias | text | SYMPTOM_NAME, FREE_TEXT | ILIKE | - | SYMPTOM_NAME, FREE_TEXT |
| alias_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| confidence | numeric |  | EXACT, RANGE | - | - |


### users_with_roles
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| auth_user_id | uuid |  | EXACT | - | - |
| email | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| is_active | boolean |  | EXACT | - | - |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| role | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| scopes | array |  |  | - | - |
| valid_from | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| valid_until | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### v_active_insights
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_id | uuid | EQUIPMENT_NAME, FREE_TEXT | EXACT | - | EQUIPMENT_NAME, FREE_TEXT |
| insight_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| title | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| recommendation | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| severity | text | SEVERITY | ILIKE | - | SEVERITY |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| acknowledged | boolean |  | EXACT | - | - |
| acknowledged_by | uuid |  | EXACT | - | - |
| acknowledged_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| dismissed | boolean |  | EXACT | - | - |
| dismissed_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| expires_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| equipment_name | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| system_type | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| criticality | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### v_equipment_risk
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| parent_id | uuid |  | EXACT | - | - |
| name | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| code | text | FAULT_CODE, FREE_TEXT | EXACT, ILIKE | - | FAULT_CODE, FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| location | text | FREE_TEXT, EQUIPMENT_LOCATION | ILIKE | - | FREE_TEXT, EQUIPMENT_LOCATION |
| manufacturer | text | MANUFACTURER, FREE_TEXT | TRIGRAM, ILIKE | - | MANUFACTURER, FREE_TEXT |
| model | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| serial_number | text | SERIAL_NUMBER, FREE_TEXT | EXACT, ILIKE | - | SERIAL_NUMBER, FREE_TEXT |
| installed_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| criticality | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| system_type | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| metadata | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| attention_flag | boolean |  | EXACT | - | - |
| attention_reason | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| attention_updated_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| risk_score | numeric |  | EXACT, RANGE | - | - |
| risk_level | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| trend | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| contributing_factors | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| risk_calculated_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### v_inventory
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| part_id | uuid |  | EXACT | - | - |
| name | text | FREE_TEXT | ILIKE | PART_NAME | FREE_TEXT |
| part_number | text | PART_NUMBER, FREE_TEXT | EXACT, ILIKE | PART_NUMBER | FREE_TEXT |
| manufacturer | text | MANUFACTURER, FREE_TEXT | TRIGRAM, ILIKE | - | MANUFACTURER, FREE_TEXT |
| description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| category | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| equipment | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| system | text | FREE_TEXT, SYSTEM_NAME | TRIGRAM, ILIKE | - | FREE_TEXT, SYSTEM_NAME |
| unit_cost | numeric |  | EXACT, RANGE | - | - |
| stock_id | uuid |  | EXACT | - | - |
| location | text | STOCK_LOCATION, FREE_TEXT | ILIKE | STOCK_LOCATION | FREE_TEXT |
| quantity | integer |  | EXACT, RANGE | - | - |
| min_quantity | integer |  | EXACT, RANGE | - | - |
| max_quantity | integer |  | EXACT, RANGE | - | - |
| reorder_quantity | integer |  | EXACT, RANGE | - | - |
| needs_reorder | boolean |  | EXACT | - | - |
| has_embedding | boolean |  | EXACT | - | - |


### v_symptom_recurrence
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| equipment_label | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| symptom_code | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| symptom_label | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| occurrence_count | integer |  | EXACT, RANGE | - | - |
| first_occurrence | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| latest_occurrence | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| span_days | numeric |  | EXACT, RANGE | - | - |
| open_count | integer |  | EXACT, RANGE | - | - |
| resolved_count | integer |  | EXACT, RANGE | - | - |


### v_vessel_status
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| current_status | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| next_event_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| next_event_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| next_event_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| hot_work_permitted | boolean |  | EXACT | - | - |
| guests_on_board | boolean |  | EXACT | - | - |
| hours_until_event | numeric |  | EXACT, RANGE | - | - |
| time_pressure | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| is_pre_charter_critical | boolean |  | EXACT | - | - |


### yacht_email_configs
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| contact_id | uuid |  | EXACT | - | - |
| vendor | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| contact_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| email | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| specialization | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| notes | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| user_id | uuid |  | EXACT | - | - |
| reliability_score | numeric |  | EXACT, RANGE | - | - |
| last_contacted | text | FREE_TEXT | ILIKE | - | FREE_TEXT |


### yacht_fault_records
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| fault_id | uuid |  | EXACT | - | - |
| equipment_type | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| equipment_brand | text | MANUFACTURER, EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | MANUFACTURER, EQUIPMENT_NAME... |
| equipment_model | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| fault_code | text | FAULT_CODE, FREE_TEXT | EXACT, ILIKE | - | FAULT_CODE, FREE_TEXT |
| fault_description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| symptoms | array |  |  | - | - |
| severity_level | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| detected_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| resolved_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| resolution_status | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| resolution_id | uuid |  | EXACT | - | - |
| technician_notes | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| root_cause | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| preventive_measures | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| downtime_hours | numeric |  | EXACT, RANGE | - | - |
| repair_cost_usd | numeric |  | EXACT, RANGE | - | - |
| parts_replaced | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| user_id | uuid |  | EXACT | - | - |


### yacht_operational_context
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| current_status | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| next_event_type | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| next_event_at | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| next_event_name | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| hot_work_permitted | boolean |  | EXACT | - | - |
| guests_on_board | boolean |  | EXACT | - | - |
| updated_by | uuid |  | EXACT | - | - |


### yacht_resolution_records
- **Row Count**: 0
- **Primary Key**: id

| Column | Type | Entity Types | Match Modes | Currently Routed | Gap |
|--------|------|--------------|-------------|------------------|-----|
| resolution_id | uuid |  | EXACT | - | - |
| resolution_title | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| resolution_description | text | DOCUMENT_QUERY, FREE_TEXT | VECTOR, TRIGRAM, ILIKE | - | DOCUMENT_QUERY, FREE_TEXT |
| resolution_steps | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| equipment_type | text | EQUIPMENT_NAME, FREE_TEXT | TRIGRAM, ILIKE | - | EQUIPMENT_NAME, FREE_TEXT |
| applicable_models | array |  |  | - | - |
| success_count | integer |  | EXACT, RANGE | - | - |
| failure_count | integer |  | EXACT, RANGE | - | - |
| average_time_minutes | integer |  | EXACT, RANGE | - | - |
| difficulty_level | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| required_expertise | array |  |  | - | - |
| safety_warnings | array |  |  | - | - |
| tools_required | array |  |  | - | - |
| parts_required | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| estimated_cost_range | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| created_by | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| approved_by | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| approval_date | text | FREE_TEXT | ILIKE | - | FREE_TEXT |
| is_verified | boolean |  | EXACT | - | - |


-- PR-IDX-2: Run in Supabase SQL editor (TENANT project), then delete this file.

-- Register pms_notes (polymorphic notes — fault notes, cert notes, etc.)
-- payload_map: fault_id only — entity_type column does not exist on pms_notes
INSERT INTO search_projection_map
    (domain, source_table, object_type, search_text_cols, filter_map, payload_map, enabled)
VALUES
    (
        'note',
        'pms_notes',
        'note',
        ARRAY['text', 'note_type'],
        '{"yacht_id": "yacht_id"}',
        '{"fault_id": "fault_id"}',
        true
    )
ON CONFLICT (source_table) DO NOTHING;

-- Register pms_work_order_notes (work order specific notes)
-- filter_map: {} — yacht_id column does not exist on pms_work_order_notes;
--   yacht scoping is covered by search_index.yacht_id set from the trigger
INSERT INTO search_projection_map
    (domain, source_table, object_type, search_text_cols, filter_map, payload_map, enabled)
VALUES
    (
        'work_order_note',
        'pms_work_order_notes',
        'work_order_note',
        ARRAY['note_text', 'note_type'],
        '{}',
        '{"work_order_id": "work_order_id"}',
        true
    )
ON CONFLICT (source_table) DO NOTHING;

-- Register pms_attachments (all file uploads)
-- search_text_cols: description removed — column does not exist on pms_attachments
INSERT INTO search_projection_map
    (domain, source_table, object_type, search_text_cols, filter_map, payload_map, enabled)
VALUES
    (
        'attachment',
        'pms_attachments',
        'attachment',
        ARRAY['filename', 'category', 'mime_type'],
        '{"entity_type": "entity_type", "category": "category"}',
        '{"entity_type": "entity_type", "entity_id": "entity_id"}',
        true
    )
ON CONFLICT (source_table) DO NOTHING;

-- Register pms_hours_of_rest (MLC 2006 HoR records)
INSERT INTO search_projection_map
    (domain, source_table, object_type, search_text_cols, filter_map, payload_map, enabled)
VALUES
    (
        'hor_entry',
        'pms_hours_of_rest',
        'hor_entry',
        ARRAY['daily_compliance_notes', 'weekly_compliance_notes', 'crew_comment'],
        '{"is_daily_compliant": "is_daily_compliant"}',
        '{"user_id": "user_id", "record_date": "record_date"}',
        true
    )
ON CONFLICT (source_table) DO NOTHING;

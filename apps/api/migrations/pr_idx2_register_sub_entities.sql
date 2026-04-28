-- PR-IDX-2: Run in Supabase SQL editor (TENANT project), then delete this file.

-- Register pms_notes (polymorphic notes — fault notes, cert notes, etc.)
INSERT INTO search_projection_map
    (domain, source_table, object_type, search_text_cols, filter_map, payload_map, enabled)
VALUES
    (
        'note',
        'pms_notes',
        'note',
        ARRAY['text', 'note_type'],
        '{"yacht_id": "yacht_id"}',
        '{"fault_id": "fault_id", "entity_type": "entity_type"}',
        true
    )
ON CONFLICT (source_table) DO NOTHING;

-- Register pms_work_order_notes (work order specific notes)
INSERT INTO search_projection_map
    (domain, source_table, object_type, search_text_cols, filter_map, payload_map, enabled)
VALUES
    (
        'work_order_note',
        'pms_work_order_notes',
        'work_order_note',
        ARRAY['note_text', 'note_type'],
        '{"yacht_id": "yacht_id"}',
        '{"work_order_id": "work_order_id"}',
        true
    )
ON CONFLICT (source_table) DO NOTHING;

-- Register pms_attachments (all file uploads)
INSERT INTO search_projection_map
    (domain, source_table, object_type, search_text_cols, filter_map, payload_map, enabled)
VALUES
    (
        'attachment',
        'pms_attachments',
        'attachment',
        ARRAY['filename', 'description', 'category', 'mime_type'],
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

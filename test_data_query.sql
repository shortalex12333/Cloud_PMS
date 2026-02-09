-- Get real parts (no images yet)
SELECT id, name, part_number, department FROM pms_parts 
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598' 
AND image_storage_path IS NULL
LIMIT 5;

-- Get recent work orders
SELECT id, title, department, priority FROM pms_work_orders
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ORDER BY created_at DESC LIMIT 5;

-- Get documents with real content
SELECT id, file_name, storage_path FROM pms_documents
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
LIMIT 5;

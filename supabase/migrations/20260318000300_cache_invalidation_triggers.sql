-- Migration: Add cache invalidation triggers for all F1 search entity tables
-- Previously only pms_parts had a trigger; 15 entity types were silently stale.
-- The f1_cache_invalidate() function already exists and fires pg_notify('f1_cache_invalidate').
-- The cache-listener eviction pattern was also fixed in this batch (wildcard yacht match).
--
-- Idempotent: uses DROP TRIGGER IF EXISTS before each CREATE TRIGGER.
-- Safe to re-run.

-- pms_work_orders → object_type 'work_order'
DROP TRIGGER IF EXISTS trg_work_orders_cache_invalidate ON pms_work_orders;
CREATE TRIGGER trg_work_orders_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_work_orders
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('work_order');

-- pms_work_order_notes → object_type 'work_order_note'
DROP TRIGGER IF EXISTS trg_work_order_notes_cache_invalidate ON pms_work_order_notes;
CREATE TRIGGER trg_work_order_notes_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_work_order_notes
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('work_order_note');

-- pms_notes → object_type 'note'
DROP TRIGGER IF EXISTS trg_notes_cache_invalidate ON pms_notes;
CREATE TRIGGER trg_notes_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_notes
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('note');

-- pms_equipment → object_type 'equipment'
DROP TRIGGER IF EXISTS trg_equipment_cache_invalidate ON pms_equipment;
CREATE TRIGGER trg_equipment_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_equipment
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('equipment');

-- pms_faults → object_type 'fault'
DROP TRIGGER IF EXISTS trg_faults_cache_invalidate ON pms_faults;
CREATE TRIGGER trg_faults_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_faults
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('fault');

-- pms_inventory_stock → object_type 'inventory'
DROP TRIGGER IF EXISTS trg_inventory_cache_invalidate ON pms_inventory_stock;
CREATE TRIGGER trg_inventory_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_inventory_stock
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('inventory');

-- pms_vessel_certificates → object_type 'certificate'
DROP TRIGGER IF EXISTS trg_certificates_cache_invalidate ON pms_vessel_certificates;
CREATE TRIGGER trg_certificates_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_vessel_certificates
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('certificate');

-- pms_receiving → object_type 'receiving'
DROP TRIGGER IF EXISTS trg_receiving_cache_invalidate ON pms_receiving;
CREATE TRIGGER trg_receiving_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_receiving
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('receiving');

-- email_messages → object_type 'email'
DROP TRIGGER IF EXISTS trg_email_messages_cache_invalidate ON email_messages;
CREATE TRIGGER trg_email_messages_cache_invalidate
    AFTER INSERT OR UPDATE ON email_messages
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('email');

-- pms_shopping_list_items → object_type 'shopping_item'
DROP TRIGGER IF EXISTS trg_shopping_items_cache_invalidate ON pms_shopping_list_items;
CREATE TRIGGER trg_shopping_items_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_shopping_list_items
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('shopping_item');

-- pms_warranty_claims → object_type 'warranty_claim'
DROP TRIGGER IF EXISTS trg_warranty_claims_cache_invalidate ON pms_warranty_claims;
CREATE TRIGGER trg_warranty_claims_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_warranty_claims
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('warranty_claim');

-- pms_purchase_orders → object_type 'purchase_order'
DROP TRIGGER IF EXISTS trg_purchase_orders_cache_invalidate ON pms_purchase_orders;
CREATE TRIGGER trg_purchase_orders_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_purchase_orders
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('purchase_order');

-- pms_suppliers → object_type 'supplier'
DROP TRIGGER IF EXISTS trg_suppliers_cache_invalidate ON pms_suppliers;
CREATE TRIGGER trg_suppliers_cache_invalidate
    AFTER INSERT OR UPDATE ON pms_suppliers
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('supplier');

-- handover_items → object_type 'handover_item'
DROP TRIGGER IF EXISTS trg_handover_items_cache_invalidate ON handover_items;
CREATE TRIGGER trg_handover_items_cache_invalidate
    AFTER INSERT OR UPDATE ON handover_items
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('handover_item');

-- doc_metadata → object_type 'document'
DROP TRIGGER IF EXISTS trg_doc_metadata_cache_invalidate ON doc_metadata;
CREATE TRIGGER trg_doc_metadata_cache_invalidate
    AFTER INSERT OR UPDATE ON doc_metadata
    FOR EACH ROW EXECUTE FUNCTION f1_cache_invalidate('document');

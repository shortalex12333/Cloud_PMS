"""
Database Schema Mapping
=======================

Maps handler field names to actual database columns.
This allows handlers to use semantic names while querying actual schema.

ACTUAL DATABASE TABLES:
-----------------------
- equipment (no prefix): id, yacht_id, parent_id, name, code, description, location, manufacturer, model, serial_number
- documents: id, yacht_id, source, original_path, filename, content_type, size_bytes, storage_path, ...
- document_chunks: id, yacht_id, document_id, chunk_index, content, page_number, embedding, section_title, ...
- graph_nodes: id, yacht_id, node_type, label, normalized_label, properties, ...
- graph_edges: id, yacht_id, from_node_id, to_node_id, edge_type, properties, ...
- pms_work_orders: id, yacht_id, equipment_id, title, description, type, priority, status, due_date, ...
- pms_parts: id, yacht_id, name, part_number, manufacturer, description, category, ...
- pms_faults: id, yacht_id, equipment_id, fault_code, title, description, severity, detected_at, ...
"""

# Table name mapping
TABLES = {
    "equipment": "equipment",
    "documents": "documents",
    "document_chunks": "document_chunks",
    "graph_nodes": "graph_nodes",
    "graph_edges": "graph_edges",
    "work_orders": "pms_work_orders",
    "parts": "pms_parts",
    "faults": "pms_faults",
    # Tables that need to be created:
    "crew_members": "crew_members",
    "hours_of_rest": "hours_of_rest",
    "checklists": "checklists",
    "checklist_items": "checklist_items",
    "attachments": "attachments",
    "purchase_orders": "purchase_orders",
    "audit_log": "audit_log",
    "work_order_notes": "work_order_notes",
    "work_order_parts": "work_order_parts",
    "stock_transactions": "stock_transactions",
    "sensor_readings": "sensor_readings",
    "maintenance_templates": "maintenance_templates",
    "handovers": "handovers",
    "handover_items": "handover_items",
}

# Column mapping for equipment table
EQUIPMENT_COLUMNS = {
    "canonical_label": "name",  # Handler uses canonical_label, DB has name
    "category": "code",         # Using code as category
    "install_date": None,       # Not in current schema
    "last_service_date": None,  # Not in current schema
    "run_hours": None,          # Not in current schema
    "status": None,             # Not in current schema
}

# Column mapping for work_orders (pms_work_orders)
WORK_ORDER_COLUMNS = {
    "assigned_to": None,        # Not in current schema
    "created_by": "created_by",
    "completed_at": None,       # Not in current schema
    "resolution": None,         # Not in current schema
}

# Column mapping for parts (pms_parts)
PARTS_COLUMNS = {
    "canonical_name": "name",
    "quantity": None,           # Not in current schema
    "min_quantity": None,
    "max_quantity": None,
    "unit": None,
    "location": None,
    "bin_number": None,
    "unit_cost": None,
    "supplier": None,
    "last_ordered_at": None,
    "last_used_at": None,
    "barcode": None,
}

# Column mapping for faults (pms_faults)
FAULTS_COLUMNS = {
    "is_resolved": None,        # Use resolved_at IS NOT NULL
    "acknowledged_at": None,    # Not in current schema
    "reported_by": None,        # Not in current schema
}


def get_table(name: str) -> str:
    """Get actual table name"""
    return TABLES.get(name, name)


def map_equipment_select() -> str:
    """Get SELECT columns for equipment that exist"""
    return "id, yacht_id, parent_id, name, code, description, location, manufacturer, model, serial_number"


def map_work_order_select() -> str:
    """Get SELECT columns for work orders that exist"""
    return (
        "id, yacht_id, equipment_id, title, description, type, priority, status, "
        "due_date, due_hours, last_completed_date, last_completed_hours, frequency, "
        "created_by, updated_by, metadata, created_at, updated_at, wo_number"
    )


def map_parts_select() -> str:
    """Get SELECT columns for parts that exist"""
    return (
        "id, yacht_id, name, part_number, manufacturer, description, "
        "category, model_compatibility, metadata, created_at, updated_at"
    )


def map_faults_select() -> str:
    """Get SELECT columns for faults that exist"""
    return (
        "id, yacht_id, equipment_id, fault_code, title, description, "
        "severity, detected_at, resolved_at, resolved_by, work_order_id, metadata, created_at"
    )


def normalize_equipment(row: dict) -> dict:
    """Normalize equipment row to handler expected format"""
    if not row:
        return {}
    return {
        "id": row.get("id"),
        "yacht_id": row.get("yacht_id"),
        "canonical_label": row.get("name"),  # Map name -> canonical_label
        "category": row.get("code"),
        "manufacturer": row.get("manufacturer"),
        "model": row.get("model"),
        "serial_number": row.get("serial_number"),
        "location": row.get("location"),
        "description": row.get("description"),
        "parent_id": row.get("parent_id"),
        # Fields not in DB - use defaults
        "install_date": None,
        "last_service_date": None,
        "run_hours": 0,
        "status": "operational",
    }


def normalize_work_order(row: dict) -> dict:
    """Normalize work order row to handler expected format"""
    if not row:
        return {}
    return {
        "id": row.get("id"),
        "yacht_id": row.get("yacht_id"),
        "equipment_id": row.get("equipment_id"),
        "title": row.get("title"),
        "description": row.get("description"),
        "type": row.get("type"),
        "priority": row.get("priority", "medium"),
        "status": row.get("status", "open"),
        "due_date": row.get("due_date"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "wo_number": row.get("wo_number"),
        # Fields not in DB
        "assigned_to": None,
        "completed_at": row.get("last_completed_date"),
        "resolution": None,
    }


def normalize_part(row: dict) -> dict:
    """Normalize part row to handler expected format"""
    if not row:
        return {}
    return {
        "id": row.get("id"),
        "yacht_id": row.get("yacht_id"),
        "canonical_name": row.get("name"),  # Map name -> canonical_name
        "part_number": row.get("part_number"),
        "manufacturer": row.get("manufacturer"),
        "description": row.get("description"),
        "category": row.get("category"),
        # Fields not in DB - use defaults
        "quantity": 0,
        "min_quantity": 0,
        "max_quantity": None,
        "unit": "units",
        "location": None,
        "bin_number": None,
        "unit_cost": None,
        "supplier": None,
    }


def normalize_fault(row: dict) -> dict:
    """Normalize fault row to handler expected format"""
    if not row:
        return {}
    return {
        "id": row.get("id"),
        "yacht_id": row.get("yacht_id"),
        "equipment_id": row.get("equipment_id"),
        "fault_code": row.get("fault_code"),
        "title": row.get("title"),
        "description": row.get("description"),
        "severity": row.get("severity", "medium"),
        "created_at": row.get("detected_at") or row.get("created_at"),
        "resolved_at": row.get("resolved_at"),
        "is_resolved": row.get("resolved_at") is not None,
        "work_order_id": row.get("work_order_id"),
    }

"""
Known column mapping profiles for each PMS source.
These are deterministic mappings — when we know the source, we don't need fuzzy matching.
Confidence is 1.0 for exact matches.

Each profile maps: source_column_name (case-insensitive) → celeste_field_name
"""

from typing import Optional


# =============================================================================
# IDEA YACHT — UPPER_SNAKE_CASE columns, integer IDs, semicolon-delimited
# =============================================================================

IDEA_YACHT = {
    "equipment": {
        "EQUIP_ID": ("source_id", 1.0),
        "EQUIP_CODE": ("code", 1.0),
        "EQUIP_NAME": ("name", 1.0),
        "EQUIP_TYPE": ("system_type", 0.85),  # real DB has system_type, not category
        "MAKER": ("manufacturer", 1.0),
        "MODEL": ("model", 1.0),
        "SERIAL_NO": ("serial_number", 1.0),
        "LOCATION": ("location", 1.0),
        "CLASS_CODE": ("system_type", 0.85),
        "CRITICALITY": ("criticality", 1.0),
        "STATUS": ("status", 1.0),
        "RUNNING_HOURS": ("running_hours", 1.0),
        "SERVICE_INTERVAL_HOURS": (None, 0.0),  # real DB has no service_interval_hours column
        "CREATED_DATE": (None, 0.0),  # skip — we set created_at ourselves
        "MODIFIED_DATE": (None, 0.0),  # skip
        "PARENT_EQUIP_ID": (None, 0.0),  # skip for MVP — hierarchy deferred
    },
    "work_orders": {
        "WO_NUMBER": ("wo_number", 1.0),
        "WO_TYPE": ("type", 0.9),
        "EQUIP_ID": (None, 0.0),  # skip — equipment FK resolved by name match
        "EQUIP_CODE": (None, 0.0),  # skip
        "DESCRIPTION": ("title", 1.0),
        "PRIORITY": ("priority", 1.0),
        "STATUS": ("status", 1.0),
        "PLANNED_DATE": ("due_date", 0.85),
        "DUE_DATE": ("due_date", 1.0),
        "COMPLETED_DATE": ("completed_at", 1.0),
        "ASSIGNED_TO": ("source_assigned_to", 1.0),
        "INTERVAL_HOURS": (None, 0.0),  # informational, not stored
        "INTERVAL_DAYS": (None, 0.0),
        "LAST_DONE_DATE": (None, 0.0),
        "REMARKS": ("completion_notes", 0.85),
    },
    "faults": {
        "FAULT_ID": ("source_id", 1.0),
        "FAULT_CODE": ("fault_code", 1.0),
        "TITLE": ("title", 1.0),
        "DESCRIPTION": ("description", 1.0),
        "SEVERITY": ("severity", 1.0),
        "STATUS": ("status", 1.0),
        "EQUIP_ID": (None, 0.0),
        "EQUIP_CODE": (None, 0.0),
        "DETECTED_AT": ("detected_at", 1.0),
        "REPORTED_BY": ("source_reported_by", 1.0),
        "RESOLVED_AT": ("resolved_at", 1.0),
        "RESOLVED_BY": ("source_resolved_by", 1.0),
        "RESOLUTION_NOTES": ("resolution_notes", 1.0),
    },
    "parts": {
        "PART_ID": ("source_id", 1.0),
        "PART_NUMBER": ("part_number", 1.0),
        "DESCRIPTION": ("name", 0.9),  # IDEA uses DESCRIPTION as the primary name
        "EQUIP_ID": (None, 0.0),
        "UNIT": ("unit", 1.0),
        "MIN_QTY": ("minimum_quantity", 1.0),
        "MAX_QTY": (None, 0.0),  # we don't have max_quantity
        "ROB_QTY": ("quantity_on_hand", 1.0),
        "LOCATION": ("location", 1.0),
        "MAKER": ("manufacturer", 1.0),
        "DRAWING_REF": ("_file_ref:DRAWING_REF", 0.0),  # routed to file reference resolver
    },
    "certificates": {
        "CERT_ID": ("source_id", 1.0),
        "CERT_TYPE": ("certificate_type", 1.0),
        "CERT_NUMBER": ("certificate_number", 1.0),
        "ISSUING_AUTHORITY": ("issuing_authority", 1.0),
        "ISSUE_DATE": ("issue_date", 1.0),
        "EXPIRY_DATE": ("expiry_date", 1.0),
        "EQUIP_ID": (None, 0.0),
        "VESSEL_ID": (None, 0.0),
        "STATUS": ("status", 1.0),
        "SURVEY_DUE": ("next_survey_due", 0.9),
        "REMARKS": (None, 0.0),
    },
}


# =============================================================================
# SEAHUB — snake_case columns, string IDs, comma-delimited
# Vocabulary mismatches: defects→faults, tasks→work_orders, inventory→parts
# =============================================================================

SEAHUB = {
    "equipment": {
        "equipment_id": ("source_id", 1.0),
        "equipment_name": ("name", 1.0),
        "equipment_code": ("code", 1.0),
        "parent_id": (None, 0.0),  # skip for MVP
        "category": ("category", 1.0),
        "maker": ("manufacturer", 1.0),
        "model": ("model", 1.0),
        "serial_number": ("serial_number", 1.0),
        "location": ("location", 1.0),
        "criticality": ("criticality", 1.0),
        "status": ("status", 1.0),
        "running_hours": ("running_hours", 1.0),
        "service_interval_hours": ("service_interval_hours", 1.0),
    },
    "faults": {
        # Seahub "defects" → CelesteOS "faults"
        "defect_id": ("source_id", 1.0),
        "title": ("title", 1.0),
        "description": ("description", 1.0),
        "equipment_id": (None, 0.0),
        "equipment_name": (None, 0.0),
        "reported_by": ("source_reported_by", 1.0),
        "reported_date": ("detected_at", 0.9),
        "status": ("status", 1.0),
        "priority": ("severity", 0.8),  # Seahub "priority" ≈ our "severity"
        "root_cause": ("description", 0.5),  # append to description
        "corrective_action": ("resolution_notes", 0.9),
        "closed_date": ("resolved_at", 1.0),
        "closed_by": ("source_resolved_by", 1.0),
    },
    "work_orders": {
        # Seahub "tasks" → CelesteOS "work_orders"
        "task_id": ("source_id", 1.0),
        "title": ("title", 1.0),
        "description": ("description", 1.0),
        "equipment_id": (None, 0.0),
        "equipment_name": (None, 0.0),
        "type": ("type", 1.0),
        "priority": ("priority", 1.0),
        "status": ("status", 1.0),
        "due_date": ("due_date", 1.0),
        "completed_date": ("completed_at", 1.0),
        "assigned_to": ("source_assigned_to", 1.0),
        "interval": (None, 0.0),
        "interval_unit": (None, 0.0),
        "last_done": (None, 0.0),
    },
    "parts": {
        # Seahub "inventory" → CelesteOS "parts"
        "part_id": ("source_id", 1.0),
        "part_name": ("name", 1.0),
        "part_number": ("part_number", 1.0),
        "description": ("description", 1.0),
        "equipment_id": (None, 0.0),
        "equipment_name": (None, 0.0),
        "category": ("category", 1.0),
        "maker": ("manufacturer", 1.0),
        "unit": ("unit", 1.0),
        "rob_qty": ("quantity_on_hand", 1.0),
        "min_qty": ("minimum_quantity", 1.0),
        "location": ("location", 1.0),
        "last_ordered": (None, 0.0),
    },
    "certificates": {
        "certificate_id": ("source_id", 1.0),
        "certificate_type": ("certificate_type", 1.0),
        "certificate_name": ("certificate_name", 1.0),
        "certificate_number": ("certificate_number", 1.0),
        "issuing_authority": ("issuing_authority", 1.0),
        "issue_date": ("issue_date", 1.0),
        "expiry_date": ("expiry_date", 1.0),
        "vessel_name": (None, 0.0),
        "status": ("status", 1.0),
        "survey_due": ("next_survey_due", 0.9),
        "remarks": (None, 0.0),
    },
}


# =============================================================================
# SEALOGICAL — Title Case with spaces, XLSX, DD/MM/YYYY dates
# =============================================================================

SEALOGICAL = {
    "equipment": {
        "Equipment Name": ("name", 1.0),
        "Equipment Code": ("code", 1.0),
        "Type": ("category", 0.85),
        "Manufacturer": ("manufacturer", 1.0),
        "Model": ("model", 1.0),
        "Serial Number": ("serial_number", 1.0),
        "Location": ("location", 1.0),
        "System Category": ("system_type", 0.9),
        "Criticality": ("criticality", 1.0),
        "Status": ("status", 1.0),
        "Running Hours": ("running_hours", 1.0),
        "Service Interval (Hours)": ("service_interval_hours", 0.95),
        "Last Service Date": (None, 0.0),  # informational
    },
}


# Registry of all profiles
PROFILES = {
    "idea_yacht": IDEA_YACHT,
    "seahub": SEAHUB,
    "sealogical": SEALOGICAL,
}


# =============================================================================
# FILE REFERENCE COLUMNS — columns in source exports that reference documents
# by filename or path. These get routed to the FileReferenceResolver instead
# of being mapped to entity columns.
#
# Structure: source → domain → column_name → resolution metadata
# =============================================================================

FILE_REFERENCE_COLUMNS = {
    "idea_yacht": {
        "parts": {
            "DRAWING_REF": {
                "link_table": "pms_equipment_documents",
                "document_type_hint": "drawing",
                "entity_type": "equipment",
            },
        },
        # Add more domains as real exports reveal file reference columns
    },
    "seahub": {},       # populated when we get real Seahub exports
    "sealogical": {},   # populated when we get real Sealogical exports
}


# =============================================================================
# Generic file reference column name hints — used when source profile doesn't
# have an explicit mapping. Matched case-insensitively against source columns.
# =============================================================================

FILE_REF_COLUMN_HINTS = {
    "ATTACHMENT", "ATTACHMENTS", "DOCUMENT_PATH", "DOCUMENT_REF",
    "DOC_PATH", "DOC_REF", "FILE_PATH", "FILE_REF", "FILEPATH",
    "FILENAME", "FILE_NAME", "FILE_LOCATION", "PHOTO", "PHOTO_PATH",
    "IMAGE", "IMAGE_PATH", "EVIDENCE", "DRAWING_REF", "REPORT_FILE",
    "CERTIFICATE_FILE", "ATTACHED_FILE", "DOCUMENT", "ATTACHMENT_PATH",
    # snake_case variants
    "attachment", "document_path", "document_ref", "file_path",
    "file_ref", "photo_path", "image_path",
    # Title Case variants
    "Document", "Attachment", "Photo", "FilePath", "File Path",
    "Document Path", "Image",
}


def get_profile_mapping(source: str, domain: str) -> Optional[dict]:
    """
    Get known column mapping for a source + domain.
    Returns dict of {source_col: (target_col, confidence)} or None if unknown.
    """
    profile = PROFILES.get(source)
    if not profile:
        return None
    return profile.get(domain)


def get_file_reference_columns(source: str, domain: str) -> dict:
    """
    Get file reference column definitions for a source + domain.
    Returns dict of {column_name: resolution_metadata} or empty dict.
    """
    source_refs = FILE_REFERENCE_COLUMNS.get(source, {})
    return source_refs.get(domain, {})

#!/usr/bin/env python3
"""Fetch real test data from production database"""
import os
import json
from supabase import create_client, Client

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Get Supabase client
url = os.getenv("SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
key = os.getenv("SUPABASE_SERVICE_KEY")

if not key:
    print("ERROR: SUPABASE_SERVICE_KEY not set")
    exit(1)

db = create_client(url, key)

# Fetch real parts (no images yet)
parts = db.table("pms_parts").select(
    "id, name, part_number, department, manufacturer"
).eq("yacht_id", YACHT_ID).is_("image_storage_path", "null").limit(5).execute()

# Fetch work orders
work_orders = db.table("pms_work_orders").select(
    "id, title, department, priority"
).eq("yacht_id", YACHT_ID).order("created_at", desc=True).limit(5).execute()

# Fetch documents
documents = db.table("pms_documents").select(
    "id, file_name, storage_path"
).eq("yacht_id", YACHT_ID).limit(5).execute()

# Output JSON
test_data = {
    "yacht_id": YACHT_ID,
    "parts": parts.data if parts.data else [],
    "work_orders": work_orders.data if work_orders.data else [],
    "documents": documents.data if documents.data else []
}

print(json.dumps(test_data, indent=2))

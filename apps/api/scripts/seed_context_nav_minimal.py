#!/usr/bin/env python3
"""
Minimal seed script for Situational Continuity Layer acceptance testing.

Creates:
- 1 yacht
- 1 user (user_profile + user_role)
- 3 equipment items
- 2 faults
- 1 work_order
- 2 user_added_relations (optional - for testing Add Related)

Usage:
    python apps/api/scripts/seed_context_nav_minimal.py
"""

import os
import sys
from uuid import uuid4, UUID
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from supabase import create_client, Client

# Supabase connection (local)
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_SERVICE_KEY:
    print("ERROR: SUPABASE_SERVICE_ROLE_KEY environment variable not set")
    print("Get it from: supabase status --override-name api.url=http://127.0.0.1:54321")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Fixed UUIDs for deterministic testing
YACHT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
EQUIPMENT_1_ID = UUID("33333333-3333-3333-3333-333333333333")
EQUIPMENT_2_ID = UUID("44444444-4444-4444-4444-444444444444")
EQUIPMENT_3_ID = UUID("55555555-5555-5555-5555-555555555555")
FAULT_1_ID = UUID("66666666-6666-6666-6666-666666666666")
FAULT_2_ID = UUID("77777777-7777-7777-7777-777777777777")
WORK_ORDER_ID = UUID("88888888-8888-8888-8888-888888888888")


def clear_existing_data():
    """Clear existing test data to ensure clean slate."""
    print("🧹 Clearing existing test data...")

    # Clear auth.users first (required for FK constraints)
    import os
    import subprocess

    sql_delete_auth_user = f"DELETE FROM auth.users WHERE id = '{USER_ID}';"
    try:
        subprocess.run(
            ["psql", "-h", "127.0.0.1", "-p", "54322", "-U", "postgres", "-d", "postgres", "-c", sql_delete_auth_user],
            env={**os.environ, "PGPASSWORD": "postgres"},
            check=True,
            capture_output=True,
            text=True
        )
        print("  ✅ Cleared auth.users")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  auth.users: {e.stderr[:80]}")

    # Order matters due to foreign keys
    tables = [
        "navigation_contexts",
        "user_added_relations",
        "work_orders",
        "faults",
        "equipment",
        "auth_users_roles",
        "auth_users_profiles",
        "yachts",
    ]

    for table in tables:
        try:
            # Delete test records only (by yacht_id or specific IDs)
            if table == "yachts":
                supabase.table(table).delete().eq("id", str(YACHT_ID)).execute()
            elif table == "auth_users_profiles":
                supabase.table(table).delete().eq("id", str(USER_ID)).execute()
            else:
                # Most tables have yacht_id
                supabase.table(table).delete().eq("yacht_id", str(YACHT_ID)).execute()
        except Exception as e:
            # Table may not exist or no data to delete
            print(f"  ⚠️  {table}: {str(e)[:80]}")

    print("✅ Existing data cleared\n")


def seed_yacht():
    """Create test yacht."""
    print("🚢 Creating yacht...")

    yacht = {
        "id": str(YACHT_ID),
        "name": "M/Y Test Vessel",
        "signature": f"test-vessel-{YACHT_ID}",
        "status": "active",
        "imo": "IMO1234567",
        "mmsi": "123456789",
        "flag_state": "Cayman Islands",
        "length_m": 85.5,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    result = supabase.table("yachts").insert(yacht).execute()
    print(f"✅ Yacht created: {result.data[0]['name']}\n")


def seed_user():
    """Create test user in auth.users, profile, and role."""
    print("👤 Creating user...")

    # First, create user in auth.users (required for FK constraints)
    # Note: Using raw SQL since Supabase client doesn't expose auth.users table
    import os
    import subprocess

    sql_create_auth_user = f"""
    INSERT INTO auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at, confirmation_token, raw_user_meta_data)
    VALUES (
        '{USER_ID}',
        '00000000-0000-0000-0000-000000000000',
        'authenticated',
        'authenticated',
        'test-context-nav@example.com',
        crypt('test-password-123', gen_salt('bf')),
        NOW(),
        NOW(),
        NOW(),
        '',
        '{{"name": "Context Nav Test User", "yacht_id": "{YACHT_ID}"}}'::jsonb
    )
    ON CONFLICT (id) DO NOTHING;
    """

    try:
        subprocess.run(
            ["psql", "-h", "127.0.0.1", "-p", "54322", "-U", "postgres", "-d", "postgres", "-c", sql_create_auth_user],
            env={**os.environ, "PGPASSWORD": "postgres"},
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Auth user created in auth.users (profile auto-created by trigger)")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Auth user creation: {e.stderr[:100]}")

    # Create user role (chief_engineer = HOD)
    user_role = {
        "id": str(uuid4()),
        "user_id": str(USER_ID),
        "yacht_id": str(YACHT_ID),
        "role": "chief_engineer",
        "is_active": True,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "valid_from": datetime.now(timezone.utc).isoformat(),
    }

    result = supabase.table("auth_users_roles").insert(user_role).execute()
    print(f"✅ User role created: {result.data[0]['role']}\n")


def seed_equipment():
    """Create test equipment items."""
    print("⚙️  Creating equipment...")

    equipment_items = [
        {
            "id": str(EQUIPMENT_1_ID),
            "yacht_id": str(YACHT_ID),
            "name": "Main Engine Starboard",
            "manufacturer": "MTU",
            "model": "16V4000M90",
            "serial_number": "SN-MTU-001",
            "location": "Engine Room",
            "category": "Propulsion",
            "status": "operational",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(EQUIPMENT_2_ID),
            "yacht_id": str(YACHT_ID),
            "name": "Air Conditioning Unit #1",
            "manufacturer": "Heinen & Hopman",
            "model": "ACU-1500",
            "serial_number": "SN-HH-ACU-001",
            "location": "Lower Deck",
            "category": "HVAC",
            "status": "operational",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(EQUIPMENT_3_ID),
            "yacht_id": str(YACHT_ID),
            "name": "Hydraulic Bow Thruster",
            "manufacturer": "Vetus",
            "model": "BOW95",
            "serial_number": "SN-VET-BOW-001",
            "location": "Bow",
            "category": "Maneuvering",
            "status": "degraded",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    result = supabase.table("equipment").insert(equipment_items).execute()
    print(f"✅ {len(result.data)} equipment items created\n")


def seed_faults():
    """Create test faults."""
    print("🔧 Creating faults...")

    faults = [
        {
            "id": str(FAULT_1_ID),
            "yacht_id": str(YACHT_ID),
            "equipment_id": str(EQUIPMENT_1_ID),
            "fault_code": "MTU-OVHT-01",
            "title": "Main Engine Starboard Overheating",
            "description": "Coolant temperature exceeded 95°C during normal operation",
            "severity": "high",
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "reported_by": str(USER_ID),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(FAULT_2_ID),
            "yacht_id": str(YACHT_ID),
            "equipment_id": str(EQUIPMENT_3_ID),
            "fault_code": None,
            "title": "Bow Thruster Hydraulic Leak",
            "description": "Minor hydraulic fluid leak detected at seal",
            "severity": "medium",
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "reported_by": str(USER_ID),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    result = supabase.table("faults").insert(faults).execute()
    print(f"✅ {len(result.data)} faults created\n")


def seed_work_order():
    """Create test work order."""
    print("📋 Creating work order...")

    work_order = {
        "id": str(WORK_ORDER_ID),
        "yacht_id": str(YACHT_ID),
        "number": "WO-TEST-001",
        "title": "Investigate Engine Overheating",
        "description": "Check coolant system, radiator, and thermostats",
        "equipment_id": str(EQUIPMENT_1_ID),
        "fault_id": str(FAULT_1_ID),
        "location": "Engine Room",
        "priority": "high",
        "status": "in_progress",
        "created_by": str(USER_ID),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    result = supabase.table("work_orders").insert(work_order).execute()
    print(f"✅ Work order created: {result.data[0]['number']}\n")


def seed_user_relations():
    """Create test user_added_relations (for Add Related testing)."""
    print("🔗 Creating user-added relations...")

    relations = [
        {
            "id": str(uuid4()),
            "yacht_id": str(YACHT_ID),
            "created_by_user_id": str(USER_ID),
            "from_artefact_type": "fault",
            "from_artefact_id": str(FAULT_1_ID),
            "to_artefact_type": "equipment",
            "to_artefact_id": str(EQUIPMENT_2_ID),
            "source": "user",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(uuid4()),
            "yacht_id": str(YACHT_ID),
            "created_by_user_id": str(USER_ID),
            "from_artefact_type": "fault",
            "from_artefact_id": str(FAULT_2_ID),
            "to_artefact_type": "work_order",
            "to_artefact_id": str(WORK_ORDER_ID),
            "source": "user",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    result = supabase.table("user_added_relations").insert(relations).execute()
    print(f"✅ {len(result.data)} user relations created\n")


def main():
    """Run all seed operations."""
    print("=" * 60)
    print("SEED SCRIPT: Situational Continuity Layer - Minimal Dataset")
    print("=" * 60)
    print()

    clear_existing_data()
    seed_yacht()
    seed_user()
    seed_equipment()
    seed_faults()
    seed_work_order()
    seed_user_relations()

    print("=" * 60)
    print("✅ SEED COMPLETE")
    print("=" * 60)
    print()
    print("Test Data IDs:")
    print(f"  Yacht ID:       {YACHT_ID}")
    print(f"  User ID:        {USER_ID}")
    print(f"  Equipment IDs:  {EQUIPMENT_1_ID}, {EQUIPMENT_2_ID}, {EQUIPMENT_3_ID}")
    print(f"  Fault IDs:      {FAULT_1_ID}, {FAULT_2_ID}")
    print(f"  Work Order ID:  {WORK_ORDER_ID}")
    print()
    print("Ready for acceptance testing!")
    print()


if __name__ == "__main__":
    main()

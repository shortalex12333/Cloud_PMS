"""
E2E Test Data Seeding - Work Orders
====================================

Seeds staging database with work orders for Playwright E2E testing.

Target:
- Yacht: 85fe1119-b04c-41ac-80f1-829d23322598
- Supabase: https://vzsohavtuotocgrfkfyd.supabase.co
- Purpose: Enable work-order.show-related.spec.ts to pass

Creates:
- 10 work orders with various statuses
- Links to existing equipment (or creates if needed)
- Some with parts/faults for Show Related testing
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta, timezone
import uuid
from supabase import create_client

# Staging credentials (TENANT_1)
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"

# Test yacht
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Test users (from .env.e2e.local)
CHIEF_ENGINEER_ID = None  # Will query from database
CREW_ID = None

# Work order templates
WORK_ORDER_TEMPLATES = [
    {
        "title": "Generator Oil Change",
        "description": "Routine oil change for main generator. Check oil levels and filter condition.",
        "status": "open",
        "priority": "medium",
        "work_type": "preventive_maintenance",
    },
    {
        "title": "Air Conditioning Compressor Repair",
        "description": "AC unit in main salon not cooling. Compressor making unusual noise.",
        "status": "in_progress",
        "priority": "high",
        "work_type": "corrective_maintenance",
    },
    {
        "title": "Engine Room Fire Suppression System Check",
        "description": "Annual inspection of fire suppression system per safety regulations.",
        "status": "open",
        "priority": "urgent",
        "work_type": "inspection",
    },
    {
        "title": "Replace Bilge Pump Float Switch",
        "description": "Port bilge pump float switch malfunctioning. Replace with OEM part.",
        "status": "pending_parts",
        "priority": "high",
        "work_type": "corrective_maintenance",
    },
    {
        "title": "Hydraulic Steering System Service",
        "description": "Regular maintenance: check fluid levels, inspect hoses, test response.",
        "status": "open",
        "priority": "medium",
        "work_type": "preventive_maintenance",
    },
    {
        "title": "Fresh Water Maker Filter Replacement",
        "description": "Replace pre-filters and post-filters on water maker system.",
        "status": "completed",
        "priority": "medium",
        "work_type": "preventive_maintenance",
    },
    {
        "title": "Navigation Lights Inspection",
        "description": "Check all navigation lights for proper operation before departure.",
        "status": "open",
        "priority": "high",
        "work_type": "inspection",
    },
    {
        "title": "Stabilizer Fin Motor Overhaul",
        "description": "Port stabilizer fin motor needs complete overhaul due to wear.",
        "status": "in_progress",
        "priority": "medium",
        "work_type": "overhaul",
    },
    {
        "title": "Waste Water Treatment System Cleaning",
        "description": "Quarterly cleaning and maintenance of waste treatment system.",
        "status": "completed",
        "priority": "low",
        "work_type": "preventive_maintenance",
    },
    {
        "title": "Emergency Generator Load Test",
        "description": "Monthly load test of emergency generator per SOLAS requirements.",
        "status": "open",
        "priority": "medium",
        "work_type": "inspection",
    },
]


def get_or_create_equipment(supabase, yacht_id):
    """Get existing equipment or create test equipment"""
    print("\n" + "="*80)
    print("STEP 1: Equipment Setup")
    print("="*80)

    # Try to find existing equipment
    result = supabase.table("pms_equipment").select(
        "id, name, equipment_type"
    ).eq("yacht_id", yacht_id).is_(
        "deleted_at", "null"
    ).limit(5).execute()

    if result.data and len(result.data) > 0:
        print(f"✓ Found {len(result.data)} existing equipment items:")
        for eq in result.data:
            print(f"  - {eq['name']} ({eq['equipment_type']})")
        return result.data

    # Create test equipment if none exists
    print("Creating test equipment...")

    equipment = [
        {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "name": "Main Generator",
            "equipment_type": "generator",
            "manufacturer": "Northern Lights",
            "model": "M844LW3",
            "serial_number": "NL-2024-001",
            "location": "Engine Room",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "name": "Air Conditioning - Main Salon",
            "equipment_type": "hvac",
            "manufacturer": "Dometic",
            "model": "DCU-16",
            "serial_number": "DOM-2024-002",
            "location": "Main Salon",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "name": "Port Bilge Pump",
            "equipment_type": "pump",
            "manufacturer": "Rule",
            "model": "2000 GPH",
            "serial_number": "RULE-2024-003",
            "location": "Engine Room - Port Side",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "name": "Fresh Water Maker",
            "equipment_type": "water_maker",
            "manufacturer": "Sea Recovery",
            "model": "SR-100",
            "serial_number": "SR-2024-004",
            "location": "Utility Room",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "name": "Emergency Generator",
            "equipment_type": "generator",
            "manufacturer": "Kohler",
            "model": "8EFOZD",
            "serial_number": "KO-2024-005",
            "location": "Engine Room - Aft",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    result = supabase.table("pms_equipment").insert(equipment).execute()

    print(f"✓ Created {len(equipment)} equipment items")
    return result.data


def get_user_ids(supabase, yacht_id):
    """Get test user IDs"""
    print("\n" + "="*80)
    print("STEP 2: User Setup")
    print("="*80)

    # Get chief engineer (HOD)
    result = supabase.table("crew_members").select(
        "id, email, role"
    ).eq("yacht_id", yacht_id).eq(
        "role", "chief_engineer"
    ).is_("deleted_at", "null").limit(1).execute()

    chief_id = None
    if result.data and len(result.data) > 0:
        chief_id = result.data[0]["id"]
        print(f"✓ Found chief engineer: {result.data[0]['email']}")
    else:
        print("⚠️  No chief engineer found")

    # Get crew member
    result = supabase.table("crew_members").select(
        "id, email, role"
    ).eq("yacht_id", yacht_id).eq(
        "role", "crew"
    ).is_("deleted_at", "null").limit(1).execute()

    crew_id = None
    if result.data and len(result.data) > 0:
        crew_id = result.data[0]["id"]
        print(f"✓ Found crew member: {result.data[0]['email']}")
    else:
        print("⚠️  No crew member found")

    return chief_id, crew_id


def seed_work_orders(supabase, yacht_id, equipment_list, chief_id, crew_id):
    """Create work orders"""
    print("\n" + "="*80)
    print("STEP 3: Create Work Orders")
    print("="*80)

    work_orders = []
    now = datetime.now(timezone.utc)

    for i, template in enumerate(WORK_ORDER_TEMPLATES):
        # Pick equipment (cycle through available)
        equipment = equipment_list[i % len(equipment_list)] if equipment_list else None

        # Assign user based on status
        assigned_to = None
        if template["status"] in ("in_progress", "pending_parts"):
            assigned_to = chief_id or crew_id
        elif template["status"] == "completed":
            assigned_to = chief_id or crew_id

        # Set dates based on status
        created_at = now - timedelta(days=30 - i)  # Stagger creation dates
        due_date = None
        completed_at = None
        started_at = None

        if template["priority"] == "urgent":
            due_date = created_at + timedelta(days=1)
        elif template["priority"] == "high":
            due_date = created_at + timedelta(days=3)
        elif template["priority"] == "medium":
            due_date = created_at + timedelta(days=7)

        if template["status"] == "in_progress":
            started_at = created_at + timedelta(hours=2)
        elif template["status"] == "completed":
            started_at = created_at + timedelta(hours=2)
            completed_at = created_at + timedelta(days=1)

        wo = {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "title": template["title"],
            "description": template["description"],
            "status": template["status"],
            "priority": template["priority"],
            "work_type": template.get("work_type", "maintenance"),
            "equipment_id": equipment["id"] if equipment else None,
            "assigned_to": assigned_to,
            "created_at": created_at.isoformat(),
            "due_date": due_date.isoformat() if due_date else None,
            "started_at": started_at.isoformat() if started_at else None,
            "completed_at": completed_at.isoformat() if completed_at else None,
            "created_by": chief_id or crew_id,
        }

        work_orders.append(wo)

    # Insert work orders
    result = supabase.table("pms_work_orders").insert(work_orders).execute()

    print(f"\n✓ Created {len(work_orders)} work orders:")
    for wo in work_orders:
        status_icon = {
            "open": "🟡",
            "in_progress": "🔵",
            "pending_parts": "🟠",
            "completed": "🟢",
        }.get(wo["status"], "⚪")
        print(f"  {status_icon} {wo['title']} ({wo['status']})")

    return result.data


def verify_searchability(supabase, yacht_id):
    """Verify work orders are searchable"""
    print("\n" + "="*80)
    print("STEP 4: Verify Searchability")
    print("="*80)

    # Query work orders like the app would
    result = supabase.table("pms_work_orders").select(
        "id, title, status, priority"
    ).eq("yacht_id", yacht_id).is_(
        "deleted_at", "null"
    ).limit(5).execute()

    if result.data and len(result.data) > 0:
        print(f"✓ Found {len(result.data)} work orders (showing first 5):")
        for wo in result.data:
            print(f"  - {wo['title']} ({wo['status']})")
        return True
    else:
        print("✗ No work orders found")
        return False


def cleanup_old_test_data(supabase, yacht_id):
    """Check for existing test work orders"""
    print("\n" + "="*80)
    print("CHECK: Existing Work Orders")
    print("="*80)

    # Check for existing work orders
    result = supabase.table("pms_work_orders").select(
        "id", count="exact"
    ).eq("yacht_id", yacht_id).is_(
        "deleted_at", "null"
    ).execute()

    count = result.count or 0

    if count > 0:
        print(f"\n✓ Found {count} existing work orders")
        print("  Skipping creation - work orders already exist")
        return count
    else:
        print("No existing work orders found - will create new ones")
        return 0


def main():
    print("="*80)
    print("E2E TEST DATA SEEDING - WORK ORDERS")
    print("="*80)
    print(f"\nTarget Yacht: {YACHT_ID}")
    print(f"Supabase: {SUPABASE_URL}")
    print()

    # Create Supabase client
    supabase = create_client(SUPABASE_URL, SERVICE_KEY)

    try:
        # Check for existing data
        existing_count = cleanup_old_test_data(supabase, YACHT_ID)

        if existing_count > 0:
            # Work orders already exist - just verify searchability
            print("\n" + "="*80)
            print("SKIP: Work Orders Already Exist")
            print("="*80)

            # Step 4: Verify searchability
            searchable = verify_searchability(supabase, YACHT_ID)

            # Summary
            print("\n" + "="*80)
            print("SUMMARY")
            print("="*80)

            if searchable:
                print("\n✅ VERIFICATION COMPLETE")
                print(f"  ✓ {existing_count} work orders already exist")
                print(f"  ✓ Work orders searchable in database")
                print("\n🎯 Database already seeded - ready for testing!")
            else:
                print("\n⚠️  VERIFICATION FAILED")
                print(f"  Work orders exist ({existing_count}) but not searchable")

            return 0

        # Step 1: Get or create equipment
        equipment_list = get_or_create_equipment(supabase, YACHT_ID)

        # Step 2: Get user IDs
        chief_id, crew_id = get_user_ids(supabase, YACHT_ID)

        if not chief_id and not crew_id:
            print("\n⚠️  WARNING: No users found. Work orders will be unassigned.")

        # Step 3: Create work orders
        work_orders = seed_work_orders(supabase, YACHT_ID, equipment_list, chief_id, crew_id)

        # Step 4: Verify searchability
        searchable = verify_searchability(supabase, YACHT_ID)

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        if searchable:
            print("\n✅ SEEDING COMPLETE")
            print(f"  ✓ {len(equipment_list)} equipment items")
            print(f"  ✓ {len(work_orders)} work orders created")
            print(f"  ✓ Work orders searchable in database")
            print("\n🎯 Playwright tests should now pass!")
            print("\nRe-run tests with:")
            print("  cd apps/web")
            print("  npx playwright test work-order.show-related.spec.ts --project=chromium")
        else:
            print("\n⚠️  SEEDING INCOMPLETE")
            print("Work orders created but not searchable. Check database permissions.")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

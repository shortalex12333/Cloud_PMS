#!/usr/bin/env python3
"""
Complete System Validation - Check ALL dependencies before E2E tests
"""
import os
import sys
from supabase import create_client

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_PARTS = [
    "5dd34337-c4c4-41dd-9c6b-adf84af349a8",  # TEAK_COMPOUND
    "2f452e3b-bf3e-464e-82d5-7d0bc849e6c0",  # WATER_PUMP
    "5543266b-2d8c-46a0-88e2-74a7ab403cdd",  # CYLINDER_RING
]
TEST_USERS = {
    "CAPTAIN": "b72c35ff-e309-4a19-a617-bfc706a78c0f",
    "HOD": "89b1262c-ff59-4591-b954-757cdf3d609d",
    "CREW": "2da12a4b-c0a1-4716-80ae-d29c90d98233",
}


def validate_environment():
    """Validate all required environment variables"""
    print("🔍 Validating environment variables...")

    required = {
        "MASTER_SUPABASE_URL": "Master database URL",
        "MASTER_SUPABASE_ANON_KEY": "Master anon key (for auth)",
        "MASTER_SUPABASE_SERVICE_KEY": "Master service key",
        "TENANT_SUPABASE_URL": "Tenant database URL",
        "TENANT_SUPABASE_SERVICE_KEY": "Tenant service key",
    }

    missing = []
    for var, desc in required.items():
        if not os.getenv(var):
            missing.append(f"      {var}: {desc}")

    if missing:
        print("   ❌ Missing environment variables:")
        for m in missing:
            print(m)
        return False

    print(f"   ✅ All {len(required)} required env vars set")
    return True


def validate_master_db():
    """Validate MASTER DB has required data"""
    print("\n🔍 Validating MASTER DB...")

    try:
        master_url = os.getenv("MASTER_SUPABASE_URL")
        master_key = os.getenv("MASTER_SUPABASE_SERVICE_KEY")
        master_db = create_client(master_url, master_key)

        # Check user_accounts
        accounts = master_db.table("user_accounts").select("id, yacht_id, status").in_(
            "id", list(TEST_USERS.values())
        ).execute()

        if len(accounts.data) != 3:
            print(f"   ❌ Expected 3 user accounts, found {len(accounts.data)}")
            print(f"      Users: {', '.join(TEST_USERS.keys())}")
            return False
        print(f"   ✅ User accounts exist: {len(accounts.data)}")

        # Verify all map to correct yacht
        wrong_yacht = [u for u in accounts.data if u["yacht_id"] != YACHT_ID]
        if wrong_yacht:
            print(f"   ❌ {len(wrong_yacht)} users have wrong yacht_id")
            return False
        print(f"   ✅ All users mapped to yacht: {YACHT_ID[:8]}...")

        # Check fleet_registry
        fleet = master_db.table("fleet_registry").select("yacht_id, tenant_key_alias, active").eq(
            "yacht_id", YACHT_ID
        ).execute()

        if not fleet.data or len(fleet.data) == 0:
            print(f"   ❌ Yacht not in fleet_registry: {YACHT_ID}")
            return False

        tenant_key = fleet.data[0].get("tenant_key_alias")
        if not tenant_key:
            print(f"   ❌ Missing tenant_key_alias for yacht")
            return False

        is_active = fleet.data[0].get("active")
        if not is_active:
            print(f"   ⚠️  Yacht is not active in fleet_registry")

        print(f"   ✅ Fleet registry: tenant_key={tenant_key}")
        return True

    except Exception as e:
        print(f"   ❌ MASTER DB check failed: {e}")
        return False


def validate_tenant_db():
    """Validate TENANT DB has required data"""
    print("\n🔍 Validating TENANT DB...")

    try:
        tenant_url = os.getenv("TENANT_SUPABASE_URL")
        tenant_key = os.getenv("TENANT_SUPABASE_SERVICE_KEY")
        tenant_db = create_client(tenant_url, tenant_key)

        # Check test parts exist
        parts = tenant_db.table("pms_parts").select("id, name, part_number").eq(
            "yacht_id", YACHT_ID
        ).in_("id", TEST_PARTS).execute()

        if len(parts.data) != 3:
            print(f"   ❌ Expected 3 test parts, found {len(parts.data)}")
            if len(parts.data) > 0:
                print(f"      Found: {[p['name'] for p in parts.data]}")
            return False
        print(f"   ✅ Test parts exist: {[p['name'][:20] for p in parts.data]}")

        # Check user roles
        roles = tenant_db.table("auth_users_roles").select("user_id, role, is_active").eq(
            "yacht_id", YACHT_ID
        ).eq("is_active", True).in_("user_id", list(TEST_USERS.values())).execute()

        if len(roles.data) != 3:
            print(f"   ❌ Expected 3 active roles, found {len(roles.data)}")
            return False

        role_map = {r["user_id"]: r["role"] for r in roles.data}
        print(f"   ✅ User roles active:")
        for name, user_id in TEST_USERS.items():
            role = role_map.get(user_id, "MISSING")
            print(f"      {name}: {role}")

        # Check crew department metadata
        crew_id = TEST_USERS["CREW"]
        crew_profile = tenant_db.table("auth_users_profiles").select("metadata").eq(
            "id", crew_id
        ).eq("yacht_id", YACHT_ID).execute()

        if not crew_profile.data or len(crew_profile.data) == 0:
            print(f"   ❌ Crew profile not found")
            return False

        metadata = crew_profile.data[0].get("metadata") or {}
        crew_dept = metadata.get("department")
        if not crew_dept:
            print(f"   ❌ Crew missing department metadata")
            fix_sql = f"UPDATE auth_users_profiles SET metadata = '{{\"department\":\"deck\"}}' WHERE id = '{crew_id}'"
            print(f"      Fix: {fix_sql}")
            return False
        print(f"   ✅ Crew department: {crew_dept}")

        return True

    except Exception as e:
        print(f"   ❌ TENANT DB check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_storage():
    """Validate Supabase Storage bucket exists"""
    print("\n🔍 Validating Supabase Storage...")

    try:
        tenant_url = os.getenv("TENANT_SUPABASE_URL")
        tenant_key = os.getenv("TENANT_SUPABASE_SERVICE_KEY")
        tenant_db = create_client(tenant_url, tenant_key)

        buckets = tenant_db.storage.list_buckets()
        bucket_names = [b["name"] if isinstance(b, dict) else b.name for b in buckets]

        if "pms-part-photos" not in bucket_names:
            print(f"   ❌ Bucket 'pms-part-photos' not found")
            print(f"      Available: {bucket_names}")
            print(f"      Action: Create bucket in Supabase Storage dashboard")
            return False

        print(f"   ✅ Storage bucket exists: pms-part-photos")

        # Try to check bucket permissions (may fail if no test upload)
        try:
            # List files in test path (should not error even if empty)
            test_path = f"{YACHT_ID}/parts/test/"
            files = tenant_db.storage.from_("pms-part-photos").list(test_path)
            print(f"   ✅ Storage accessible (listed {len(files)} files in test path)")
        except Exception as e:
            print(f"   ⚠️  Storage list failed (may be permissions): {e}")
            print(f"      This is non-critical if upload works in E2E tests")

        return True

    except Exception as e:
        print(f"   ❌ Storage check failed: {e}")
        return False


def validate_api_deployment():
    """Validate API is deployed with correct version"""
    print("\n🔍 Validating API deployment...")

    try:
        import requests

        response = requests.get("https://pipeline-core.int.celeste7.ai/version", timeout=10)

        if response.status_code != 200:
            print(f"   ❌ Version endpoint failed: HTTP {response.status_code}")
            return False

        data = response.json()
        version = data.get("version")
        fixes = data.get("critical_fixes", [])

        print(f"   ✅ API deployed: v{version}")
        print(f"   ✅ Critical fixes: {len(fixes)}")
        for fix in fixes:
            print(f"      - {fix}")

        # Check if JWT fix is deployed (not in version, but we can infer from PR list)
        if version == "2026.02.09.003":
            print(f"   ⚠️  Current deployment does NOT include JWT validation fix")
            print(f"      PR #208 needs to be merged and deployed")
            print(f"      Tests will FAIL until deployment completes")

        return True

    except Exception as e:
        print(f"   ❌ API check failed: {e}")
        return False


def main():
    print("=" * 70)
    print("COMPLETE SYSTEM VALIDATION")
    print("=" * 70)
    print("Checking all dependencies before E2E tests...\n")

    checks = [
        ("Environment Variables", validate_environment),
        ("MASTER Database", validate_master_db),
        ("TENANT Database", validate_tenant_db),
        ("Supabase Storage", validate_storage),
        ("API Deployment", validate_api_deployment),
    ]

    results = {}
    for name, check_fn in checks:
        results[name] = check_fn()

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    all_pass = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_pass = False

    print("=" * 70)

    if all_pass:
        print("\n✅ ALL VALIDATIONS PASSED")
        print("   System is ready for E2E tests")
        print("\n   Run: python3 test_e2e_journeys.py")
        sys.exit(0)
    else:
        print("\n❌ VALIDATION FAILED")
        print("   Fix the issues above before running E2E tests")
        print("\n   Common fixes:")
        print("   1. Load environment: source .env.local")
        print("   2. Create storage bucket: Supabase dashboard → Storage → New bucket 'pms-part-photos'")
        print("   3. Fix crew department: Run SQL in COMPLETE_SYSTEM_VALIDATION.md")
        print("   4. Wait for PR #208 deployment: Check Render logs")
        sys.exit(1)


if __name__ == "__main__":
    main()

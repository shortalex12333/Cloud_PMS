#!/usr/bin/env python3
"""
Seed Hours of Rest Test Data
=============================

Creates test data for HOR compliance testing:
- Daily rest records (compliant and non-compliant)
- Schedule templates (4-on/8-off watch system)
- Monthly signoff records
- Warnings for non-compliant records

Run on TENANT DB: vzsohavtuotocgrfkfyd.supabase.co
"""
import os
import sys
import json
from datetime import datetime, timedelta, date
from supabase import create_client

# =============================================================================
# CONFIGURATION
# =============================================================================

TENANT_URL = os.getenv("TENANT_SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
TENANT_SERVICE_KEY = os.getenv("TENANT_SUPABASE_SERVICE_KEY")

# Test yacht and users
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Test crew members
CREW_MEMBERS = [
    {
        "user_id": "b72c35ff-e309-4a19-a617-bfc706a78c0f",
        "name": "Captain Test",
        "role": "CAPTAIN",
        "department": "DECK"
    },
    {
        "user_id": "89b1262c-ff59-4591-b954-757cdf3d609d",
        "name": "Chief Engineer Test",
        "role": "CHIEF_ENGINEER",
        "department": "ENGINE"
    },
    {
        "user_id": "00000000-0000-4000-a000-000000000001",
        "name": "Deckhand John",
        "role": "CREW",
        "department": "DECK"
    },
    {
        "user_id": "00000000-0000-4000-a000-000000000002",
        "name": "Engineer Sarah",
        "role": "CREW",
        "department": "ENGINE"
    },
    {
        "user_id": "00000000-0000-4000-a000-000000000003",
        "name": "Steward Alex",
        "role": "CREW",
        "department": "INTERIOR"
    },
]

# =============================================================================
# REST PERIOD TEMPLATES
# =============================================================================

# Compliant rest pattern: 10+ hours per day (MLC 2006 compliant)
COMPLIANT_REST_PERIODS = [
    # Night rest: 22:00 - 06:00 (8 hours)
    # Afternoon rest: 13:00 - 15:00 (2 hours)
    # Total: 10 hours (COMPLIANT)
    [
        {"start": "22:00", "end": "06:00"},
        {"start": "13:00", "end": "15:00"}
    ],
    # Alternative: Long night rest
    # Night rest: 21:00 - 07:00 (10 hours)
    # Total: 10 hours (COMPLIANT)
    [
        {"start": "21:00", "end": "07:00"}
    ],
    # Split rest with longer afternoon
    # Night: 23:00 - 06:00 (7 hours)
    # Afternoon: 12:00 - 15:00 (3 hours)
    # Total: 10 hours (COMPLIANT)
    [
        {"start": "23:00", "end": "06:00"},
        {"start": "12:00", "end": "15:00"}
    ]
]

# Non-compliant rest pattern: <10 hours (MLC 2006 violation)
NON_COMPLIANT_REST_PERIODS = [
    # Only 8 hours total
    [
        {"start": "23:00", "end": "06:00"},  # 7 hours
        {"start": "14:00", "end": "15:00"}   # 1 hour = 8 total
    ],
    # Only 6 hours (severe violation)
    [
        {"start": "00:00", "end": "06:00"}   # 6 hours only
    ],
    # 9 hours (just under threshold)
    [
        {"start": "22:00", "end": "06:00"},  # 8 hours
        {"start": "13:00", "end": "14:00"}   # 1 hour = 9 total
    ]
]

# 4-on/8-off Watch Schedule Template
WATCH_SCHEDULE_4_ON_8_OFF = {
    "monday": [
        {"start": "00:00", "end": "04:00", "type": "work"},
        {"start": "04:00", "end": "08:00", "type": "rest"},
        {"start": "08:00", "end": "12:00", "type": "work"},
        {"start": "12:00", "end": "16:00", "type": "rest"},
        {"start": "16:00", "end": "20:00", "type": "work"},
        {"start": "20:00", "end": "00:00", "type": "rest"}
    ],
    "tuesday": [
        {"start": "00:00", "end": "04:00", "type": "rest"},
        {"start": "04:00", "end": "08:00", "type": "work"},
        {"start": "08:00", "end": "12:00", "type": "rest"},
        {"start": "12:00", "end": "16:00", "type": "work"},
        {"start": "16:00", "end": "20:00", "type": "rest"},
        {"start": "20:00", "end": "00:00", "type": "work"}
    ],
    "wednesday": [
        {"start": "00:00", "end": "04:00", "type": "work"},
        {"start": "04:00", "end": "08:00", "type": "rest"},
        {"start": "08:00", "end": "12:00", "type": "work"},
        {"start": "12:00", "end": "16:00", "type": "rest"},
        {"start": "16:00", "end": "20:00", "type": "work"},
        {"start": "20:00", "end": "00:00", "type": "rest"}
    ],
    "thursday": [
        {"start": "00:00", "end": "04:00", "type": "rest"},
        {"start": "04:00", "end": "08:00", "type": "work"},
        {"start": "08:00", "end": "12:00", "type": "rest"},
        {"start": "12:00", "end": "16:00", "type": "work"},
        {"start": "16:00", "end": "20:00", "type": "rest"},
        {"start": "20:00", "end": "00:00", "type": "work"}
    ],
    "friday": [
        {"start": "00:00", "end": "04:00", "type": "work"},
        {"start": "04:00", "end": "08:00", "type": "rest"},
        {"start": "08:00", "end": "12:00", "type": "work"},
        {"start": "12:00", "end": "16:00", "type": "rest"},
        {"start": "16:00", "end": "20:00", "type": "work"},
        {"start": "20:00", "end": "00:00", "type": "rest"}
    ],
    "saturday": [
        {"start": "00:00", "end": "04:00", "type": "rest"},
        {"start": "04:00", "end": "08:00", "type": "work"},
        {"start": "08:00", "end": "12:00", "type": "rest"},
        {"start": "12:00", "end": "16:00", "type": "work"},
        {"start": "16:00", "end": "20:00", "type": "rest"},
        {"start": "20:00", "end": "00:00", "type": "work"}
    ],
    "sunday": [
        {"start": "00:00", "end": "08:00", "type": "rest"},
        {"start": "08:00", "end": "12:00", "type": "work"},
        {"start": "12:00", "end": "20:00", "type": "rest"},
        {"start": "20:00", "end": "00:00", "type": "work"}
    ]
}


def calculate_total_rest(rest_periods: list) -> float:
    """Calculate total rest hours from rest periods."""
    total = 0.0
    for period in rest_periods:
        start = datetime.strptime(period["start"], "%H:%M")
        end = datetime.strptime(period["end"], "%H:%M")

        # Handle overnight periods (e.g., 22:00 - 06:00)
        if end <= start:
            hours = (24 - start.hour - start.minute/60) + (end.hour + end.minute/60)
        else:
            hours = (end - start).seconds / 3600

        total += hours

    return round(total, 1)


def is_daily_compliant(total_rest_hours: float) -> bool:
    """Check MLC 2006 daily compliance (10 hours minimum)."""
    return total_rest_hours >= 10.0


def seed_hours_of_rest():
    """Seed daily rest records for test crew members."""
    if not TENANT_SERVICE_KEY:
        print("❌ TENANT_SUPABASE_SERVICE_KEY not set")
        print("   Set environment variable and retry")
        sys.exit(1)

    print("=" * 80)
    print("SEEDING HOURS OF REST TEST DATA")
    print("=" * 80)
    print()
    print(f"Tenant URL: {TENANT_URL}")
    print(f"Test Yacht: {TEST_YACHT_ID}")
    print()

    db = create_client(TENANT_URL, TENANT_SERVICE_KEY)

    # Generate 30 days of records (current month)
    today = date.today()
    start_date = today.replace(day=1)

    records_created = 0
    violations_created = 0

    for crew in CREW_MEMBERS:
        print(f"\n{'='*60}")
        print(f"Creating records for: {crew['name']} ({crew['role']})")
        print(f"{'='*60}")

        for day_offset in range(30):
            record_date = start_date + timedelta(days=day_offset)

            # Skip future dates
            if record_date > today:
                break

            # Alternate between compliant and non-compliant
            # 80% compliant, 20% non-compliant for realistic data
            if day_offset % 5 == 0:  # Every 5th day is non-compliant
                rest_periods = NON_COMPLIANT_REST_PERIODS[day_offset % len(NON_COMPLIANT_REST_PERIODS)]
                is_violation = True
            else:
                rest_periods = COMPLIANT_REST_PERIODS[day_offset % len(COMPLIANT_REST_PERIODS)]
                is_violation = False

            total_rest = calculate_total_rest(rest_periods)
            daily_compliant = is_daily_compliant(total_rest)

            # Create rest record
            record_data = {
                "yacht_id": TEST_YACHT_ID,
                "user_id": crew["user_id"],
                "record_date": record_date.isoformat(),
                "rest_periods": json.dumps(rest_periods),
                "total_rest_hours": total_rest,
                "is_daily_compliant": daily_compliant,
                "is_weekly_compliant": True,  # Simplified for seeding
                "notes": f"Auto-seeded test data - {'VIOLATION' if is_violation else 'compliant'}"
            }

            try:
                db.table("pms_hours_of_rest").upsert(
                    record_data,
                    on_conflict="yacht_id,user_id,record_date"
                ).execute()

                records_created += 1
                status = "❌ NON-COMPLIANT" if is_violation else "✅"
                print(f"  {record_date}: {total_rest}h rest {status}")

                # Create warning for violations
                if is_violation:
                    warning_data = {
                        "yacht_id": TEST_YACHT_ID,
                        "user_id": crew["user_id"],
                        "warning_type": "DAILY_REST",
                        "severity": "high" if total_rest < 8 else "medium",
                        "status": "active",
                        "record_date": record_date.isoformat(),
                        "violation_details": json.dumps({
                            "required_hours": 10,
                            "actual_hours": total_rest,
                            "shortfall": round(10 - total_rest, 1)
                        }),
                        "message": f"Daily rest violation: {total_rest}h (minimum 10h required)"
                    }

                    db.table("pms_crew_hours_warnings").upsert(
                        warning_data,
                        on_conflict="yacht_id,user_id,record_date,warning_type"
                    ).execute()
                    violations_created += 1

            except Exception as e:
                print(f"  ⚠️ Error: {e}")

    print()
    print(f"✅ Created {records_created} rest records")
    print(f"⚠️ Created {violations_created} violation warnings")
    return records_created, violations_created


def seed_schedule_templates():
    """Seed schedule templates."""
    print()
    print("=" * 80)
    print("SEEDING SCHEDULE TEMPLATES")
    print("=" * 80)

    db = create_client(TENANT_URL, TENANT_SERVICE_KEY)

    templates = [
        {
            "yacht_id": TEST_YACHT_ID,
            "template_name": "4-on/8-off Watch System",
            "description": "Standard rotating watch schedule - 12 hours work, 12 hours rest per day",
            "schedule_template": json.dumps(WATCH_SCHEDULE_4_ON_8_OFF),
            "is_default": True
        },
        {
            "yacht_id": TEST_YACHT_ID,
            "template_name": "Day Worker",
            "description": "Standard day shift - 08:00 to 18:00 work, rest overnight",
            "schedule_template": json.dumps({
                "monday": [{"start": "08:00", "end": "18:00", "type": "work"}],
                "tuesday": [{"start": "08:00", "end": "18:00", "type": "work"}],
                "wednesday": [{"start": "08:00", "end": "18:00", "type": "work"}],
                "thursday": [{"start": "08:00", "end": "18:00", "type": "work"}],
                "friday": [{"start": "08:00", "end": "18:00", "type": "work"}],
                "saturday": [{"start": "08:00", "end": "14:00", "type": "work"}],
                "sunday": []  # Day off
            }),
            "is_default": False
        },
        {
            "yacht_id": TEST_YACHT_ID,
            "template_name": "Port Day",
            "description": "Reduced hours when in port - minimal watch requirements",
            "schedule_template": json.dumps({
                "monday": [{"start": "09:00", "end": "17:00", "type": "work"}],
                "tuesday": [{"start": "09:00", "end": "17:00", "type": "work"}],
                "wednesday": [{"start": "09:00", "end": "17:00", "type": "work"}],
                "thursday": [{"start": "09:00", "end": "17:00", "type": "work"}],
                "friday": [{"start": "09:00", "end": "17:00", "type": "work"}],
                "saturday": [{"start": "09:00", "end": "12:00", "type": "work"}],
                "sunday": []
            }),
            "is_default": False
        }
    ]

    for template in templates:
        try:
            db.table("pms_crew_normal_hours").upsert(
                template,
                on_conflict="yacht_id,template_name"
            ).execute()
            print(f"✅ Created template: {template['template_name']}")
        except Exception as e:
            print(f"⚠️ Template error: {e}")


def seed_monthly_signoffs():
    """Seed monthly signoff records."""
    print()
    print("=" * 80)
    print("SEEDING MONTHLY SIGNOFFS")
    print("=" * 80)

    db = create_client(TENANT_URL, TENANT_SERVICE_KEY)

    today = date.today()
    current_month = today.strftime("%Y-%m")
    last_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    # Create signoff records for each crew member
    for crew in CREW_MEMBERS:
        # Last month - finalized
        signoff_last = {
            "yacht_id": TEST_YACHT_ID,
            "user_id": crew["user_id"],
            "year_month": last_month,
            "status": "finalized",
            "crew_signature": json.dumps({
                "signed_at": (today - timedelta(days=5)).isoformat(),
                "ip_address": "192.168.1.100"
            }),
            "hod_signature": json.dumps({
                "signed_at": (today - timedelta(days=3)).isoformat(),
                "signed_by": CREW_MEMBERS[1]["user_id"],  # Chief Engineer
                "ip_address": "192.168.1.101"
            }),
            "master_signature": json.dumps({
                "signed_at": (today - timedelta(days=1)).isoformat(),
                "signed_by": CREW_MEMBERS[0]["user_id"],  # Captain
                "ip_address": "192.168.1.102"
            })
        }

        # Current month - draft
        signoff_current = {
            "yacht_id": TEST_YACHT_ID,
            "user_id": crew["user_id"],
            "year_month": current_month,
            "status": "draft"
        }

        try:
            db.table("pms_hor_monthly_signoffs").upsert(
                signoff_last,
                on_conflict="yacht_id,user_id,year_month"
            ).execute()
            print(f"✅ {crew['name']}: {last_month} = finalized")

            db.table("pms_hor_monthly_signoffs").upsert(
                signoff_current,
                on_conflict="yacht_id,user_id,year_month"
            ).execute()
            print(f"✅ {crew['name']}: {current_month} = draft")

        except Exception as e:
            print(f"⚠️ Signoff error for {crew['name']}: {e}")


def main():
    """Run all seeding functions."""
    print()
    print("=" * 80)
    print("HOURS OF REST - TEST DATA SEEDER")
    print("=" * 80)
    print()

    if not TENANT_SERVICE_KEY:
        print("❌ Missing required environment variable:")
        print("   export TENANT_SUPABASE_SERVICE_KEY=<your-service-key>")
        print()
        print("Get this from: https://vzsohavtuotocgrfkfyd.supabase.co")
        print("Project Settings > API > service_role key")
        sys.exit(1)

    # Run all seeders
    records, violations = seed_hours_of_rest()
    seed_schedule_templates()
    seed_monthly_signoffs()

    print()
    print("=" * 80)
    print("SEEDING COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  - Rest records created: {records}")
    print(f"  - Violations created: {violations}")
    print(f"  - Schedule templates: 3")
    print(f"  - Monthly signoffs: {len(CREW_MEMBERS) * 2}")
    print()
    print("Test users:")
    for crew in CREW_MEMBERS:
        print(f"  - {crew['name']} ({crew['role']}): {crew['user_id']}")


if __name__ == "__main__":
    main()

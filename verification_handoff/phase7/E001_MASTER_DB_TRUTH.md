# E001: MASTER DB REALITY

**Date:** 2026-01-21
**Phase:** 7 - System Reality Extraction
**Status:** COMPLETE

---

## Summary

This document records the ground truth for authentication and tenant mapping across MASTER and TENANT databases.

**Key Finding:** The system uses a split architecture:
- **MASTER DB** (qvzmkaamzaqxpzbewjxe): Auth service only
- **TENANT DB** (vzsohavtuotocgrfkfyd): User profiles, roles, and all operational data

Custom JWT claims (`yacht_id`, `user_role`) are injected via a PostgreSQL hook function that queries TENANT tables.

---

## Test User: x@alex-short.com

### Extracted Data

| Field | Value | Source |
|-------|-------|--------|
| user_id | `a35cad0b-02ff-4287-b6e4-17c96fa6a424` | MASTER auth.users, TENANT auth_users_profiles |
| email | `x@alex-short.com` | MASTER auth.users |
| yacht_id | `85fe1119-b04c-41ac-80f1-829d23322598` | TENANT auth_users_profiles |
| user_role | `captain` | TENANT auth_users_roles |
| is_active | `true` | TENANT auth_users_profiles, auth_users_roles |
| tenant_db | `vzsohavtuotocgrfkfyd` | JWT issuer field |

### Integration Status

| Provider | Status |
|----------|--------|
| Email/Password | Active |
| Microsoft OAuth | NOT FOUND in auth.users.identities |

---

## MASTER DB (qvzmkaamzaqxpzbewjxe)

### Query 1: Auth Admin API - List Users
```
GET https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/admin/users
Status: 200
Total users: 1
```

**Result:**
```json
{
  "id": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "email": "x@alex-short.com",
  "role": "authenticated",
  "created_at": "2026-01-20T13:13:02.021768Z",
  "user_metadata": {"email_verified": true},
  "app_metadata": {"provider": "email", "providers": ["email"]}
}
```

### Query 2: Public Tables
```sql
-- Attempted tables (via PostgREST)
SELECT * FROM profiles LIMIT 1;         -- NOT FOUND
SELECT * FROM user_profiles LIMIT 1;    -- NOT FOUND
SELECT * FROM tenants LIMIT 1;          -- NOT FOUND
SELECT * FROM yachts LIMIT 1;           -- NOT FOUND
SELECT * FROM alert_rules LIMIT 1;      -- EXISTS
```

**Tables Found:**
| Table | Columns |
|-------|---------|
| alert_rules | id, rule_name, description, event_type, severity, threshold, time_window_minutes, cooldown_minutes, alert_channels, recipients, enabled, last_triggered_at, created_at, created_by, updated_at |

**Conclusion:** MASTER DB is primarily for authentication. No user profile or tenant mapping tables exposed via PostgREST.

---

## TENANT DB (vzsohavtuotocgrfkfyd)

### Query 3: Auth Admin API - List Users
```
GET https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/admin/users
Status: 200
Total users: 1
```

**Result:** Same user exists in TENANT auth with identical ID.

### Query 4: auth_users_profiles Table
```sql
SELECT * FROM auth_users_profiles WHERE id = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';
```

**Result:**
```json
{
  "id": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "email": "old_1768421213124@temp.local",
  "name": "x@alex-short.com",
  "is_active": true,
  "metadata": {},
  "created_at": "2025-11-21T12:56:56.610658+00:00",
  "updated_at": "2026-01-09T16:08:20.85026+00:00"
}
```

**Columns:** id, yacht_id, email, name, is_active, metadata, created_at, updated_at

### Query 5: auth_users_roles Table
```sql
SELECT * FROM auth_users_roles WHERE user_id = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';
```

**Result:**
```json
{
  "id": "...",
  "user_id": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "role": "captain",
  "assigned_at": "...",
  "assigned_by": "...",
  "is_active": true,
  "valid_from": "...",
  "valid_until": null
}
```

**Columns:** id, user_id, yacht_id, role, assigned_at, assigned_by, is_active, valid_from, valid_until

### Query 6: yacht_registry Table
```sql
SELECT * FROM yacht_registry WHERE id = '85fe1119-b04c-41ac-80f1-829d23322598';
```

**Result:**
```json
{
  "id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "name": "M/Y Test Vessel",
  "imo": null,
  "mmsi": null,
  "flag_state": null,
  "length_m": null,
  "owner_ref": null,
  "yacht_secret_hash": "$2b$12$VTIcydTIFAtqSVWrmDg0Q...",
  "nas_root_path": null,
  "status": "active",
  "metadata": {},
  "created_at": "2025-11-22T01:31:25.729137+00:00",
  "updated_at": "2025-11-22T01:31:25.729137+00:00"
}
```

**Columns:** id, name, imo, mmsi, flag_state, length_m, owner_ref, yacht_secret_hash, nas_root_path, status, metadata, created_at, updated_at

---

## JWT Hook Function

**Location:** `database/migrations/06_fix_jwt_hook_function.sql`

**Function:** `public.custom_access_token_hook(event jsonb)`

**Purpose:** Adds custom claims to JWT at token generation time.

**Logic:**
1. Query `auth_users_profiles` for user's `yacht_id`
2. If found, query `auth_users_roles` for user's `role` where `yacht_id` matches and `is_active = true`
3. Add `yacht_id` and `user_role` to JWT claims

**Decoded JWT Claims (from test user's token):**
```json
{
  "sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "email": "x@alex-short.com",
  "role": "authenticated",
  "user_role": "captain",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "iss": "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1",
  "aud": "authenticated"
}
```

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                         MASTER DB                                │
│                    (qvzmkaamzaqxpzbewjxe)                        │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │   auth.users    │  │   alert_rules   │                       │
│  │  (supabase)     │  │   (monitoring)  │                       │
│  └─────────────────┘  └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ User ID lookup
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         TENANT DB                                │
│                    (vzsohavtuotocgrfkfyd)                        │
│  ┌──────────────────────┐  ┌─────────────────────┐              │
│  │  auth_users_profiles │  │  auth_users_roles   │              │
│  │  - yacht_id          │  │  - role             │              │
│  │  - is_active         │  │  - is_active        │              │
│  └──────────────────────┘  └─────────────────────┘              │
│                                                                  │
│  ┌──────────────────────┐  ┌─────────────────────┐              │
│  │    yacht_registry    │  │  pms_* tables       │              │
│  │  - name, status      │  │  (operational data) │              │
│  └──────────────────────┘  └─────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ JWT hook adds claims
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                           JWT                                    │
│  {                                                               │
│    "sub": "user_id",                                            │
│    "yacht_id": "from auth_users_profiles",                      │
│    "user_role": "from auth_users_roles"                         │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Evidence Files

| File | Description |
|------|-------------|
| `phase7_step1_output_v2.json` | MASTER DB auth query results |
| `phase7_step1_tenant_auth.json` | TENANT DB auth query results |
| `phase7_step1_jwt_tables.json` | auth_users_profiles, auth_users_roles data |
| `phase7_jwt_decoded.json` | Decoded JWT claims |

---

**Document:** E001_MASTER_DB_TRUTH.md
**Completed:** 2026-01-21

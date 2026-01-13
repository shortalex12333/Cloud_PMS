# CELESTEOS V4: DEFINITIVE FOLDER STRUCTURE & ORGANIZATION

**Version:** 4.0 FINAL
**Date:** 2026-01-11
**Purpose:** Eliminate the CORS, RPC, policy chaos by organizing EVERYTHING into a coherent structure

---

## EXECUTIVE SUMMARY

After analyzing your architecture, CORS issues, RPC functions, policies, and the document viewer problems, here is the **exact folder structure** that will prevent these issues from recurring.

### Key Principles:
1. **Colocate related code** - RPC, policy, and frontend code for a feature live together
2. **Single source of truth** - Each situation has ONE folder with ALL its artifacts
3. **Explicit dependencies** - No hidden cross-references
4. **Test-first policies** - Every RPC has a test file
5. **Type safety** - Shared types between frontend/backend/RPC

---

## GRAVE DANGERS IDENTIFIED

### 1. CORS WILDCARD WITH CREDENTIALS

**File:** `apps/api/pipeline_service.py` lines 44-50

```python
allow_origins=["*"]
allow_credentials=True
```

**SEVERITY:** CRITICAL SECURITY VULNERABILITY

**Impact:** Any website can make authenticated requests to your API. Users can be CSRF attacked. Session tokens can be stolen.

**FIX REQUIRED:** Replace with explicit origin list (see CORS section below)

---

### 2. SCATTERED RPC FUNCTIONS

**Current state:** RPC functions are defined in multiple places:
- Some in `database/migrations/*.sql`
- Some in `database/setup_complete.sql`
- Some directly in Supabase dashboard
- No clear mapping between action → RPC → policy

**Impact:** When you add a new action, you don't know if:
- The RPC exists
- The RLS policy allows it
- The storage policy permits bucket access
- The CORS allows the frontend to call it

**FIX:** Every action gets a dedicated folder with ALL its artifacts.

---

### 3. INCONSISTENT RLS POLICIES

**Current state:**
- Some tables have policies referencing `user_profiles`
- Some reference `auth_users_profiles`
- Some use `auth.uid()` directly
- Some use `jwt_yacht_id()`

**Impact:** Unpredictable access - some queries work, some fail silently.

**FIX:** Standardize ALL policies using the same pattern (documented below).

---

### 4. DOCUMENT VIEWER CSP BLOCKS

**Current CSP:**
```javascript
"object-src 'none'"
"frame-src 'self' https://vzsohavtuotocgrfkfyd.supabase.co"
```

**Missing:** `blob:` in `frame-src` and `media-src`

**Impact:** Blob URLs for PDFs may be blocked in some browsers.

**FIX:** Add `blob:` to CSP (documented in structure below).

---

## DEFINITIVE FOLDER STRUCTURE

```
Cloud_PMS/
├── .env.example                      # Environment template
├── .env.local                        # Local dev (gitignored)
├── CLAUDE.md                         # AI assistant instructions
│
├── apps/
│   ├── web/                          # VERCEL FRONTEND
│   │   ├── src/
│   │   │   ├── app/                  # Next.js app router
│   │   │   │   ├── (auth)/           # Auth pages (login, register)
│   │   │   │   ├── (dashboard)/      # Main app pages
│   │   │   │   │   ├── faults/
│   │   │   │   │   │   ├── page.tsx              # Fault list
│   │   │   │   │   │   ├── [id]/
│   │   │   │   │   │   │   └── page.tsx          # Fault detail
│   │   │   │   │   │   └── report/
│   │   │   │   │   │       └── page.tsx          # Report fault form
│   │   │   │   │   ├── work-orders/
│   │   │   │   │   ├── inventory/
│   │   │   │   │   ├── documents/
│   │   │   │   │   ├── receiving/
│   │   │   │   │   └── handover/
│   │   │   │   └── layout.tsx
│   │   │   │
│   │   │   ├── components/
│   │   │   │   ├── ui/               # Reusable UI components
│   │   │   │   ├── situations/       # SITUATION-SPECIFIC COMPONENTS
│   │   │   │   │   ├── fault/
│   │   │   │   │   │   ├── FaultCard.tsx
│   │   │   │   │   │   ├── FaultDetailView.tsx
│   │   │   │   │   │   ├── DiagnoseModal.tsx
│   │   │   │   │   │   └── index.ts
│   │   │   │   │   ├── work-order/
│   │   │   │   │   ├── receiving/
│   │   │   │   │   │   ├── ReceivingSession.tsx
│   │   │   │   │   │   ├── CheckInItem.tsx
│   │   │   │   │   │   ├── DiscrepancyPhoto.tsx
│   │   │   │   │   │   └── SignatureCapture.tsx
│   │   │   │   │   └── document/
│   │   │   │   │       ├── DocumentViewer.tsx    # PDF viewer
│   │   │   │   │       ├── SemanticSearch.tsx
│   │   │   │   │       └── ChunkHighlight.tsx
│   │   │   │   │
│   │   │   │   └── actions/          # MICRO-ACTION COMPONENTS
│   │   │   │       ├── ReportFaultAction.tsx
│   │   │   │       ├── DiagnoseFaultAction.tsx
│   │   │   │       ├── CreateWorkOrderFromFaultAction.tsx
│   │   │   │       ├── AdjustInventoryAction.tsx
│   │   │   │       └── CommitReceivingAction.tsx
│   │   │   │
│   │   │   ├── hooks/
│   │   │   │   ├── useAction.ts      # Generic action executor
│   │   │   │   ├── useFault.ts
│   │   │   │   ├── useWorkOrder.ts
│   │   │   │   ├── useReceiving.ts
│   │   │   │   └── useSemanticSearch.ts
│   │   │   │
│   │   │   ├── lib/
│   │   │   │   ├── supabase/
│   │   │   │   │   ├── client.ts     # Browser client
│   │   │   │   │   ├── server.ts     # Server component client
│   │   │   │   │   └── middleware.ts # Auth middleware
│   │   │   │   ├── actions/
│   │   │   │   │   └── index.ts      # Action dispatcher
│   │   │   │   └── utils/
│   │   │   │       └── pdf-blob.ts   # PDF blob URL handler
│   │   │   │
│   │   │   └── types/
│   │   │       ├── database.types.ts # AUTO-GENERATED from Supabase
│   │   │       ├── actions.types.ts  # Action input/output types
│   │   │       └── situations.types.ts
│   │   │
│   │   ├── next.config.js            # CSP HEADERS HERE
│   │   ├── middleware.ts             # Auth checks
│   │   └── package.json
│   │
│   ├── api/                          # RENDER BACKEND
│   │   ├── pipeline_service.py       # Main FastAPI app
│   │   ├── microaction_service.py    # Action API
│   │   ├── cors.py                   # CORS CONFIGURATION (NEW)
│   │   ├── routes/
│   │   │   ├── search.py
│   │   │   ├── embeddings.py
│   │   │   └── webhooks.py
│   │   ├── services/
│   │   │   ├── semantic_search.py
│   │   │   ├── pdf_processor.py
│   │   │   └── embedding_generator.py
│   │   └── requirements.txt
│   │
│   └── worker/                       # Background jobs (if needed)
│
├── packages/
│   └── shared-types/                 # SHARED TYPES PACKAGE
│       ├── src/
│       │   ├── actions.ts            # Action types
│       │   ├── database.ts           # Database row types
│       │   ├── situations.ts         # Situation state types
│       │   └── index.ts
│       └── package.json
│
├── database/                         # SUPABASE DATABASE
│   ├── migrations/                   # Sequential migrations
│   │   ├── 00001_extensions.sql
│   │   ├── 00002_foundation_tables.sql
│   │   ├── 00003_equipment_tables.sql
│   │   ├── 00004_parts_tables.sql
│   │   ├── 00005_document_tables.sql
│   │   ├── 00006_receiving_tables.sql
│   │   ├── 00007_audit_tables.sql
│   │   └── README.md
│   │
│   ├── rpc/                          # RPC FUNCTIONS BY CLUSTER
│   │   ├── _common/
│   │   │   ├── auth_helpers.sql      # jwt_yacht_id(), get_user_role()
│   │   │   └── audit_helpers.sql     # create_audit_log()
│   │   │
│   │   ├── cluster_01_fix_something/
│   │   │   ├── report_fault.sql
│   │   │   ├── acknowledge_fault.sql
│   │   │   ├── diagnose_fault.sql
│   │   │   └── close_fault.sql
│   │   │
│   │   ├── cluster_02_do_maintenance/
│   │   │   ├── create_work_order.sql
│   │   │   ├── create_work_order_from_fault.sql
│   │   │   ├── add_note_to_work_order.sql
│   │   │   ├── add_part_to_work_order.sql
│   │   │   └── close_work_order.sql
│   │   │
│   │   ├── cluster_04_inventory_parts/
│   │   │   ├── add_part.sql
│   │   │   ├── adjust_inventory.sql
│   │   │   ├── generate_part_label.sql
│   │   │   └── add_to_shopping_list.sql
│   │   │
│   │   ├── cluster_05_handover/
│   │   │   ├── create_handover.sql
│   │   │   └── acknowledge_handover.sql
│   │   │
│   │   ├── cluster_07_documents/
│   │   │   ├── upload_document.sql
│   │   │   ├── get_document_storage_path.sql
│   │   │   └── semantic_search.sql
│   │   │
│   │   ├── cluster_08_purchasing/
│   │   │   ├── approve_shopping_item.sql
│   │   │   └── commit_receiving_session.sql
│   │   │
│   │   └── deploy_all_rpc.sql        # Master file that runs all
│   │
│   ├── policies/                     # RLS POLICIES BY TABLE
│   │   ├── _template.sql             # Policy template
│   │   ├── yachts.sql
│   │   ├── user_profiles.sql
│   │   ├── faults.sql
│   │   ├── work_orders.sql
│   │   ├── parts.sql
│   │   ├── doc_metadata.sql
│   │   ├── search_document_chunks.sql
│   │   ├── receiving_sessions.sql
│   │   ├── receiving_items.sql
│   │   ├── handover.sql
│   │   ├── audit_log.sql
│   │   └── deploy_all_policies.sql   # Master file
│   │
│   ├── storage/                      # STORAGE BUCKET POLICIES
│   │   ├── buckets.sql               # Create buckets
│   │   ├── documents.sql             # documents bucket RLS
│   │   ├── pms-part-photos.sql
│   │   ├── pms-label-pdfs.sql
│   │   ├── pms-discrepancy-photos.sql
│   │   ├── pms-receiving-images.sql
│   │   ├── pms-finance-documents.sql
│   │   └── deploy_all_storage.sql    # Master file
│   │
│   ├── seeds/                        # Test data
│   │   ├── 001_test_yacht.sql
│   │   ├── 002_test_users.sql
│   │   ├── 003_test_equipment.sql
│   │   └── 004_test_parts.sql
│   │
│   ├── tests/                        # DATABASE TESTS
│   │   ├── test_rpc_report_fault.sql
│   │   ├── test_rpc_commit_receiving.sql
│   │   ├── test_policy_faults.sql
│   │   └── run_all_tests.sql
│   │
│   └── schema.sql                    # FULL SCHEMA (generated/reference)
│
├── docs/                             # DOCUMENTATION
│   ├── architecture/
│   │   ├── SITUATIONAL_STATE_ARCHITECTURE_V4.md
│   │   ├── COMPLETE_ACTION_EXECUTION_CATALOG.md
│   │   ├── DATABASE_SCHEMA_V3_COMPLETE.sql
│   │   └── CORS_POLICY_ANALYSIS.md
│   │
│   ├── action_specifications/        # DETAILED ACTION SPECS
│   │   ├── cluster_01_FIX_SOMETHING/
│   │   │   ├── report_fault.md
│   │   │   ├── acknowledge_fault.md
│   │   │   ├── diagnose_fault.md
│   │   │   └── create_work_order_from_fault.md
│   │   ├── cluster_02_DO_MAINTENANCE/
│   │   ├── cluster_04_INVENTORY_PARTS/
│   │   ├── cluster_05_HANDOVER/
│   │   ├── cluster_07_DOCUMENTS/
│   │   ├── cluster_08_PURCHASING/
│   │   └── README.md
│   │
│   ├── situations/                   # SITUATION STATE DOCS
│   │   ├── fault_lifecycle.md
│   │   ├── work_order_lifecycle.md
│   │   ├── receiving_session.md
│   │   ├── document_viewer.md
│   │   └── README.md
│   │
│   └── deployment/
│       ├── VERCEL_CONFIG.md
│       ├── RENDER_CONFIG.md
│       ├── SUPABASE_CONFIG.md
│       └── CORS_CHECKLIST.md
│
├── scripts/                          # UTILITY SCRIPTS
│   ├── deploy-rpc.sh                 # Deploy all RPC functions
│   ├── deploy-policies.sh            # Deploy all RLS policies
│   ├── deploy-storage.sh             # Deploy storage policies
│   ├── generate-types.sh             # Generate TypeScript types from Supabase
│   ├── test-rpc.sh                   # Run RPC tests
│   └── verify-cors.sh                # Verify CORS configuration
│
└── tests/                            # INTEGRATION TESTS
    ├── e2e/
    │   ├── fault-lifecycle.spec.ts
    │   ├── receiving-session.spec.ts
    │   └── document-viewer.spec.ts
    │
    └── api/
        ├── test_pipeline.py
        └── test_microaction.py
```

---

## DETAILED FILE SPECIFICATIONS

### 1. CORS CONFIGURATION (NEW FILE)

**File:** `apps/api/cors.py`

```python
"""
CORS Configuration - Single Source of Truth

RULE: If you need to add a new origin, ADD IT HERE ONLY.
DO NOT add CORS middleware in individual route files.
"""

from typing import List

# Production origins (verified, trusted)
PRODUCTION_ORIGINS = [
    "https://app.celeste7.ai",           # Production frontend
    "https://api.celeste7.ai",           # API domain
]

# Vercel preview deployments
VERCEL_ORIGINS = [
    "https://cloud-ezkuoo4zj-c7s-projects-4a165667.vercel.app",  # Main deployment
    # Preview deployments auto-allowed via pattern below
]

# Development origins
DEV_ORIGINS = [
    "http://localhost:3000",             # Next.js dev
    "http://localhost:8000",             # Local API testing
]

def get_allowed_origins(environment: str = "production") -> List[str]:
    """
    Returns allowed origins based on environment.

    NEVER RETURN ["*"] - this is a security vulnerability
    """
    if environment == "development":
        return PRODUCTION_ORIGINS + VERCEL_ORIGINS + DEV_ORIGINS
    elif environment == "staging":
        return PRODUCTION_ORIGINS + VERCEL_ORIGINS
    else:  # production
        return PRODUCTION_ORIGINS + VERCEL_ORIGINS

def is_allowed_origin(origin: str, environment: str = "production") -> bool:
    """
    Checks if origin is allowed.
    Also allows Vercel preview deployments (*.vercel.app)
    """
    allowed = get_allowed_origins(environment)

    # Exact match
    if origin in allowed:
        return True

    # Vercel preview deployments
    if origin.endswith(".vercel.app"):
        # Verify it's your project (c7s-projects)
        if "c7s-projects" in origin:
            return True

    return False

# CORS middleware configuration
CORS_CONFIG = {
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": [
        "Content-Type",
        "Authorization",
        "X-Yacht-Signature",
        "X-Request-ID",
    ],
    "max_age": 3600,  # Cache preflight for 1 hour
}
```

---

### 2. NEXT.JS CSP CONFIGURATION (FIXED)

**File:** `apps/web/next.config.js`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: [
              // Default: Only allow same-origin
              "default-src 'self'",

              // Scripts: self + Vercel live preview
              "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://vercel.live",

              // Styles: self + inline (for CSS-in-JS)
              "style-src 'self' 'unsafe-inline'",

              // Images: self + data URIs + blobs + Supabase storage
              "img-src 'self' data: blob: https://vzsohavtuotocgrfkfyd.supabase.co",

              // Fonts: self only
              "font-src 'self'",

              // Objects: NONE (security - blocks <object> tags)
              "object-src 'none'",

              // Base URI: self (prevents base tag injection)
              "base-uri 'self'",

              // Forms: self only
              "form-action 'self'",

              // Frame ancestors: none (prevents clickjacking)
              "frame-ancestors 'none'",

              // Frames/iframes: self + blob (for PDF viewer) + Supabase
              "frame-src 'self' blob: https://vzsohavtuotocgrfkfyd.supabase.co",

              // Media: self + blob + Supabase
              "media-src 'self' blob: https://vzsohavtuotocgrfkfyd.supabase.co",

              // Connect (fetch/XHR): self + Supabase + Render API
              "connect-src 'self' https://vzsohavtuotocgrfkfyd.supabase.co wss://vzsohavtuotocgrfkfyd.supabase.co https://pipeline-core.int.celeste7.ai https://api.celeste7.ai",

              // Workers: self + blob (for PDF.js workers)
              "worker-src 'self' blob:",

            ].join('; '),
          },
          // HSTS for HTTPS enforcement
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains',
          },
          // Prevent MIME sniffing
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

---

### 3. RPC FUNCTION TEMPLATE

**File:** `database/rpc/_template.sql`

```sql
-- =============================================================================
-- RPC FUNCTION TEMPLATE
-- =============================================================================
-- Copy this template when creating new RPC functions
--
-- NAMING CONVENTION: action_name (snake_case, matches action ID)
-- SECURITY: ALWAYS use SECURITY DEFINER with explicit user validation
-- RETURN: Always return JSON with consistent structure
-- =============================================================================

CREATE OR REPLACE FUNCTION public.{action_name}(
    -- REQUIRED PARAMETERS (no defaults)
    p_required_param UUID,
    p_another_required TEXT,

    -- OPTIONAL PARAMETERS (with defaults)
    p_optional_param TEXT DEFAULT NULL,
    p_optional_number NUMERIC DEFAULT 0
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER  -- Runs with function owner's permissions
SET search_path = public  -- Prevent search_path injection
AS $$
DECLARE
    v_user_id UUID;
    v_yacht_id UUID;
    v_user_role TEXT;
    v_result JSON;
BEGIN
    -- =========================================================================
    -- STEP 1: AUTHENTICATION & AUTHORIZATION
    -- =========================================================================

    -- Get current user
    v_user_id := auth.uid();
    IF v_user_id IS NULL THEN
        RETURN json_build_object(
            'success', false,
            'error', 'Not authenticated',
            'error_code', 'AUTH_REQUIRED'
        );
    END IF;

    -- Get user's yacht and role
    SELECT yacht_id, role INTO v_yacht_id, v_user_role
    FROM public.user_profiles
    WHERE id = v_user_id AND deleted_at IS NULL;

    IF v_yacht_id IS NULL THEN
        RETURN json_build_object(
            'success', false,
            'error', 'User not assigned to a yacht',
            'error_code', 'NO_YACHT_ASSIGNED'
        );
    END IF;

    -- Check role permissions (customize per action)
    IF v_user_role NOT IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin') THEN
        RETURN json_build_object(
            'success', false,
            'error', 'Insufficient permissions',
            'error_code', 'PERMISSION_DENIED'
        );
    END IF;

    -- =========================================================================
    -- STEP 2: INPUT VALIDATION
    -- =========================================================================

    -- Validate required parameter exists
    IF p_required_param IS NULL THEN
        RETURN json_build_object(
            'success', false,
            'error', 'required_param is required',
            'error_code', 'VALIDATION_ERROR'
        );
    END IF;

    -- Validate required parameter belongs to user's yacht
    IF NOT EXISTS (
        SELECT 1 FROM public.{related_table}
        WHERE id = p_required_param
        AND yacht_id = v_yacht_id
        AND deleted_at IS NULL
    ) THEN
        RETURN json_build_object(
            'success', false,
            'error', 'Entity not found or access denied',
            'error_code', 'NOT_FOUND'
        );
    END IF;

    -- =========================================================================
    -- STEP 3: BUSINESS LOGIC
    -- =========================================================================

    -- Your actual logic here...

    -- =========================================================================
    -- STEP 4: MUTATION + AUDIT LOG (in transaction)
    -- =========================================================================

    -- INSERT or UPDATE your table...

    -- Always create audit log entry
    INSERT INTO public.audit_log (
        yacht_id,
        action,
        entity_type,
        entity_id,
        user_id,
        user_name,
        user_role,
        new_values,
        changes_summary,
        risk_level,
        created_at
    ) VALUES (
        v_yacht_id,
        '{action_name}',
        '{entity_type}',
        p_required_param,
        v_user_id,
        (SELECT full_name FROM public.user_profiles WHERE id = v_user_id),
        v_user_role,
        json_build_object('param1', p_required_param),
        'Description of what changed',
        'low',  -- or 'medium', 'high'
        NOW()
    );

    -- =========================================================================
    -- STEP 5: RETURN SUCCESS
    -- =========================================================================

    RETURN json_build_object(
        'success', true,
        'data', json_build_object(
            'id', p_required_param,
            'message', 'Action completed successfully'
        )
    );

EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'success', false,
            'error', SQLERRM,
            'error_code', 'DATABASE_ERROR'
        );
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION public.{action_name} TO authenticated;

-- Comment for documentation
COMMENT ON FUNCTION public.{action_name} IS 'Action: {action_name} - Description of what this action does';
```

---

### 4. RLS POLICY TEMPLATE

**File:** `database/policies/_template.sql`

```sql
-- =============================================================================
-- RLS POLICY TEMPLATE FOR {TABLE_NAME}
-- =============================================================================
-- RULES:
-- 1. Every policy MUST filter by yacht_id
-- 2. Use consistent helper functions (jwt_yacht_id, get_user_role)
-- 3. Test every policy with the test file
-- =============================================================================

-- Enable RLS
ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;

-- Force RLS for table owners too (important for SECURITY DEFINER functions)
ALTER TABLE public.{table_name} FORCE ROW LEVEL SECURITY;

-- Drop existing policies (idempotent)
DROP POLICY IF EXISTS "{table_name}_select_own_yacht" ON public.{table_name};
DROP POLICY IF EXISTS "{table_name}_insert_own_yacht" ON public.{table_name};
DROP POLICY IF EXISTS "{table_name}_update_own_yacht" ON public.{table_name};
DROP POLICY IF EXISTS "{table_name}_delete_own_yacht" ON public.{table_name};

-- =============================================================================
-- SELECT POLICY: Users can view records from their yacht
-- =============================================================================
CREATE POLICY "{table_name}_select_own_yacht"
    ON public.{table_name}
    FOR SELECT
    TO authenticated
    USING (
        yacht_id = (
            SELECT yacht_id
            FROM public.user_profiles
            WHERE id = auth.uid()
            AND deleted_at IS NULL
        )
        AND deleted_at IS NULL
    );

-- =============================================================================
-- INSERT POLICY: Users can insert records for their yacht
-- =============================================================================
CREATE POLICY "{table_name}_insert_own_yacht"
    ON public.{table_name}
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id = (
            SELECT yacht_id
            FROM public.user_profiles
            WHERE id = auth.uid()
            AND deleted_at IS NULL
        )
    );

-- =============================================================================
-- UPDATE POLICY: Users with appropriate role can update
-- =============================================================================
CREATE POLICY "{table_name}_update_own_yacht"
    ON public.{table_name}
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id = (
            SELECT yacht_id
            FROM public.user_profiles
            WHERE id = auth.uid()
            AND deleted_at IS NULL
        )
        AND deleted_at IS NULL
    )
    WITH CHECK (
        yacht_id = (
            SELECT yacht_id
            FROM public.user_profiles
            WHERE id = auth.uid()
            AND deleted_at IS NULL
        )
    );

-- =============================================================================
-- DELETE POLICY: Only admins can delete (soft delete preferred)
-- =============================================================================
CREATE POLICY "{table_name}_delete_own_yacht"
    ON public.{table_name}
    FOR DELETE
    TO authenticated
    USING (
        yacht_id = (
            SELECT yacht_id
            FROM public.user_profiles
            WHERE id = auth.uid()
            AND deleted_at IS NULL
        )
        AND EXISTS (
            SELECT 1 FROM public.user_profiles
            WHERE id = auth.uid()
            AND role = 'admin'
            AND deleted_at IS NULL
        )
    );

-- =============================================================================
-- SERVICE ROLE POLICY: Service role bypasses RLS
-- =============================================================================
CREATE POLICY "{table_name}_service_role_all"
    ON public.{table_name}
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
```

---

### 5. STORAGE BUCKET POLICY TEMPLATE

**File:** `database/storage/_template.sql`

```sql
-- =============================================================================
-- STORAGE POLICY FOR {bucket_name}
-- =============================================================================
-- RULES:
-- 1. All paths MUST include {yacht_id} as first segment
-- 2. Users can only access files in their yacht's folder
-- 3. Upload permissions based on role
-- =============================================================================

-- Create bucket (if not exists)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    '{bucket_name}',
    '{bucket_name}',
    false,  -- NOT public (requires auth)
    52428800,  -- 50MB limit
    ARRAY['application/pdf', 'image/jpeg', 'image/png']
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- SELECT POLICY: Users can view files from their yacht
-- =============================================================================
CREATE POLICY "{bucket_name}_select_own_yacht"
    ON storage.objects
    FOR SELECT
    TO authenticated
    USING (
        bucket_id = '{bucket_name}'
        AND (storage.foldername(name))[1] = (
            SELECT yacht_id::TEXT
            FROM public.user_profiles
            WHERE id = auth.uid()
            AND deleted_at IS NULL
        )
    );

-- =============================================================================
-- INSERT POLICY: Users with role can upload to their yacht folder
-- =============================================================================
CREATE POLICY "{bucket_name}_insert_own_yacht"
    ON storage.objects
    FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = '{bucket_name}'
        AND (storage.foldername(name))[1] = (
            SELECT yacht_id::TEXT
            FROM public.user_profiles
            WHERE id = auth.uid()
            AND deleted_at IS NULL
        )
        -- Role check (customize per bucket)
        AND EXISTS (
            SELECT 1 FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

-- =============================================================================
-- UPDATE POLICY: Same as INSERT
-- =============================================================================
CREATE POLICY "{bucket_name}_update_own_yacht"
    ON storage.objects
    FOR UPDATE
    TO authenticated
    USING (
        bucket_id = '{bucket_name}'
        AND (storage.foldername(name))[1] = (
            SELECT yacht_id::TEXT
            FROM public.user_profiles
            WHERE id = auth.uid()
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        bucket_id = '{bucket_name}'
        AND (storage.foldername(name))[1] = (
            SELECT yacht_id::TEXT
            FROM public.user_profiles
            WHERE id = auth.uid()
            AND deleted_at IS NULL
        )
    );

-- =============================================================================
-- DELETE POLICY: Only admins can delete
-- =============================================================================
CREATE POLICY "{bucket_name}_delete_own_yacht"
    ON storage.objects
    FOR DELETE
    TO authenticated
    USING (
        bucket_id = '{bucket_name}'
        AND (storage.foldername(name))[1] = (
            SELECT yacht_id::TEXT
            FROM public.user_profiles
            WHERE id = auth.uid()
            AND deleted_at IS NULL
        )
        AND EXISTS (
            SELECT 1 FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );
```

---

## ACTION → FILE MAPPING

Every micro-action has a **complete file set**:

| Action ID | Spec Doc | RPC SQL | Policy SQL | Frontend Component | Hook | Test |
|-----------|----------|---------|------------|-------------------|------|------|
| `report_fault` | `docs/action_specifications/cluster_01/report_fault.md` | `database/rpc/cluster_01/report_fault.sql` | `database/policies/faults.sql` | `components/actions/ReportFaultAction.tsx` | `hooks/useFault.ts` | `tests/test_rpc_report_fault.sql` |
| `acknowledge_fault` | `docs/action_specifications/cluster_01/acknowledge_fault.md` | `database/rpc/cluster_01/acknowledge_fault.sql` | `database/policies/faults.sql` | `components/situations/fault/FaultDetailView.tsx` | `hooks/useFault.ts` | `tests/test_rpc_acknowledge_fault.sql` |
| `diagnose_fault` | `docs/action_specifications/cluster_01/diagnose_fault.md` | `database/rpc/cluster_01/diagnose_fault.sql` | `database/policies/faults.sql` | `components/actions/DiagnoseFaultAction.tsx` | `hooks/useFault.ts` | `tests/test_rpc_diagnose_fault.sql` |
| `create_work_order_from_fault` | `docs/action_specifications/cluster_01/create_wo_from_fault.md` | `database/rpc/cluster_02/create_wo_from_fault.sql` | `database/policies/work_orders.sql` + `database/policies/faults.sql` | `components/actions/CreateWorkOrderFromFaultAction.tsx` | `hooks/useWorkOrder.ts` | `tests/test_rpc_create_wo_from_fault.sql` |
| `commit_receiving_session` | `docs/action_specifications/cluster_08/commit_receiving.md` | `database/rpc/cluster_08/commit_receiving_session.sql` | `database/policies/receiving_sessions.sql` + `database/policies/parts.sql` | `components/actions/CommitReceivingAction.tsx` | `hooks/useReceiving.ts` | `tests/test_rpc_commit_receiving.sql` |
| `semantic_search` | `docs/action_specifications/cluster_07/semantic_search.md` | `database/rpc/cluster_07/semantic_search.sql` | `database/policies/search_document_chunks.sql` | `components/situations/document/SemanticSearch.tsx` | `hooks/useSemanticSearch.ts` | `tests/test_rpc_semantic_search.sql` |

---

## DEPLOYMENT CHECKLIST

### Before Every Deployment

```bash
# 1. Run database tests
./scripts/test-rpc.sh

# 2. Deploy RPC functions
./scripts/deploy-rpc.sh

# 3. Deploy policies
./scripts/deploy-policies.sh

# 4. Deploy storage policies
./scripts/deploy-storage.sh

# 5. Verify CORS configuration
./scripts/verify-cors.sh

# 6. Generate TypeScript types
./scripts/generate-types.sh

# 7. Run e2e tests
npm run test:e2e
```

### CORS Verification Checklist

- [ ] Pipeline service has explicit origin list (no wildcard)
- [ ] Microaction service includes Vercel domain
- [ ] Supabase Storage CORS configured in dashboard
- [ ] Next.js CSP includes `blob:` in `frame-src` and `media-src`
- [ ] Preflight caching enabled (`max_age: 3600`)
- [ ] `Vary: Origin` header set on responses

---

## SUMMARY

This structure solves:

1. **CORS chaos** → Single `cors.py` file with explicit origins
2. **RPC scattered** → `database/rpc/cluster_XX/` folders
3. **Policy inconsistency** → Templates + standardized patterns
4. **Document viewer blocking** → Fixed CSP with `blob:` support
5. **No traceability** → Every action has complete file set

**Use this structure going forward. Do not deviate.**

---

**END OF DOCUMENT**

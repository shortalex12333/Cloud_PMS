-- ============================================================================
-- Migration: Seed Data
-- Version: 20250101000004
-- Description: Insert essential reference data (user roles, etc.)
-- ============================================================================

-- ============================================================================
-- USER ROLES: Define the 7 role types in CelesteOS
-- ============================================================================

INSERT INTO user_roles (role_name, display_name, description, permissions) VALUES
  (
    'chief_engineer',
    'Chief Engineer',
    'Head of engineering department with full equipment and maintenance permissions',
    '{
      "equipment": ["read", "create", "update", "delete"],
      "work_orders": ["read", "create", "update", "delete"],
      "faults": ["read", "create", "update", "delete"],
      "parts": ["read", "create", "update", "delete"],
      "inventory": ["read", "create", "update", "delete"],
      "suppliers": ["read", "create", "update", "delete"],
      "purchase_orders": ["read", "create", "update", "delete"],
      "documents": ["read"],
      "users": ["read", "create", "update", "delete"],
      "agents": ["read", "create", "update", "delete"],
      "api_keys": ["read", "create", "update", "delete"],
      "predictive": ["read", "acknowledge"]
    }'::jsonb
  ),
  (
    'eto',
    'Electro-Technical Officer',
    'Technical specialist for electrical and electronic systems',
    '{
      "equipment": ["read", "create", "update", "delete"],
      "work_orders": ["read", "create", "update"],
      "faults": ["read", "create", "update", "delete"],
      "parts": ["read", "create", "update"],
      "inventory": ["read", "create", "update"],
      "documents": ["read"],
      "predictive": ["read", "acknowledge"]
    }'::jsonb
  ),
  (
    'captain',
    'Captain',
    'Vessel master with managerial permissions',
    '{
      "equipment": ["read"],
      "work_orders": ["read", "create"],
      "faults": ["read", "create"],
      "handovers": ["read", "create", "update", "delete"],
      "documents": ["read"],
      "users": ["read", "create", "update", "delete"],
      "agents": ["read", "create", "update", "delete"],
      "api_keys": ["read", "create", "update", "delete"],
      "purchase_orders": ["read", "create", "update", "delete"],
      "suppliers": ["read", "create", "update", "delete"]
    }'::jsonb
  ),
  (
    'manager',
    'Manager',
    'Administrative manager with full system permissions',
    '{
      "equipment": ["read", "create", "update", "delete"],
      "work_orders": ["read", "create", "update", "delete"],
      "faults": ["read", "create", "update", "delete"],
      "parts": ["read", "create", "update", "delete"],
      "inventory": ["read", "create", "update", "delete"],
      "suppliers": ["read", "create", "update", "delete"],
      "purchase_orders": ["read", "create", "update", "delete"],
      "documents": ["read", "create", "update", "delete"],
      "users": ["read", "create", "update", "delete"],
      "agents": ["read", "create", "update", "delete"],
      "api_keys": ["read", "create", "update", "delete"],
      "handovers": ["read", "create", "update", "delete"],
      "predictive": ["read", "acknowledge"]
    }'::jsonb
  ),
  (
    'deck',
    'Deck Crew',
    'Deck department crew with operational permissions',
    '{
      "equipment": ["read"],
      "work_orders": ["read", "create"],
      "faults": ["read", "create"],
      "inventory": ["read", "update"],
      "handovers": ["read", "create"],
      "documents": ["read"]
    }'::jsonb
  ),
  (
    'interior',
    'Interior Crew',
    'Interior department crew with operational permissions',
    '{
      "equipment": ["read"],
      "work_orders": ["read", "create"],
      "faults": ["read", "create"],
      "inventory": ["read", "update"],
      "handovers": ["read", "create"],
      "documents": ["read"]
    }'::jsonb
  ),
  (
    'vendor',
    'Vendor/Contractor',
    'External vendor with limited read access',
    '{
      "equipment": ["read"],
      "work_orders": ["read"],
      "parts": ["read"],
      "documents": ["read"]
    }'::jsonb
  )
ON CONFLICT (role_name) DO NOTHING;

COMMENT ON TABLE user_roles IS 'Seeded with 7 standard roles for CelesteOS';

-- ============================================================================
-- VERIFICATION QUERY (run separately to verify)
-- ============================================================================
-- SELECT role_name, display_name, description FROM user_roles ORDER BY role_name;
-- Expected: 7 rows

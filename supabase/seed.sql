-- ============================================================================
-- CELESTEOS LOCAL SANDBOX - SEED DATA
-- ============================================================================
-- Purpose: Minimal test data for end-to-end local testing
-- Table names verified against actual migrations
-- ============================================================================

-- ============================================================================
-- 1. YACHT (table: yachts)
-- ============================================================================
INSERT INTO yachts (
  id,
  name,
  imo,
  mmsi,
  flag_state,
  length_m,
  signature,
  status,
  created_at,
  updated_at
) VALUES (
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'M/Y Test Vessel',
  '1234567',
  '123456789',
  'Marshall Islands',
  50.0,
  'test-vessel-signature-001',
  'active',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 2. AUTH USERS (must exist before profiles due to FK)
-- ============================================================================
-- Note: yacht_id passed in raw_user_meta_data so handle_new_user trigger
-- can create the profile with correct yacht assignment
-- Token columns must be empty strings (not NULL) for GoTrue compatibility
INSERT INTO auth.users (
  instance_id,
  id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at,
  raw_app_meta_data,
  raw_user_meta_data,
  confirmation_token,
  recovery_token,
  email_change_token_new,
  email_change_token_current,
  email_change,
  reauthentication_token,
  phone_change,
  phone_change_token
) VALUES
(
  '00000000-0000-0000-0000-000000000000',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  'authenticated',
  'authenticated',
  'admin@test.com',
  crypt('password123', gen_salt('bf')),
  NOW(),
  NOW(),
  NOW(),
  '{"provider":"email","providers":["email"]}',
  '{"yacht_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","name":"Test Admin"}',
  '',
  '',
  '',
  '',
  '',
  '',
  '',
  ''
),
(
  '00000000-0000-0000-0000-000000000000',
  'cccccccc-cccc-cccc-cccc-cccccccccccc',
  'authenticated',
  'authenticated',
  'crew@test.com',
  crypt('password123', gen_salt('bf')),
  NOW(),
  NOW(),
  NOW(),
  '{"provider":"email","providers":["email"]}',
  '{"yacht_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","name":"Test Crew"}',
  '',
  '',
  '',
  '',
  '',
  '',
  '',
  ''
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 3. USER PROFILES (table: auth_users_profiles)
-- ============================================================================
INSERT INTO auth_users_profiles (
  id,
  yacht_id,
  email,
  name,
  is_active,
  created_at,
  updated_at
) VALUES
(
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'admin@test.com',
  'Test Admin',
  true,
  NOW(),
  NOW()
),
(
  'cccccccc-cccc-cccc-cccc-cccccccccccc',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'crew@test.com',
  'Test Crew',
  true,
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 4. USER ROLES (table: auth_users_roles)
-- ============================================================================
INSERT INTO auth_users_roles (
  id,
  user_id,
  yacht_id,
  role,
  is_active,
  valid_from,
  assigned_at
) VALUES
(
  '11111111-1111-1111-1111-111111111111',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'chief_engineer',
  true,
  NOW(),
  NOW()
),
(
  '22222222-2222-2222-2222-222222222222',
  'cccccccc-cccc-cccc-cccc-cccccccccccc',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'crew',
  true,
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 5. EQUIPMENT (table: equipment)
-- ============================================================================
INSERT INTO equipment (
  id,
  yacht_id,
  name,
  manufacturer,
  model,
  serial_number,
  location,
  category,
  status,
  created_at,
  updated_at
) VALUES (
  'dddddddd-dddd-dddd-dddd-dddddddddddd',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'Main Generator #1',
  'Caterpillar',
  'C18 ACERT',
  'CAT12345',
  'Engine Room - Starboard',
  'generator',
  'operational',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 6. PARTS (table: parts)
-- ============================================================================
INSERT INTO parts (
  id,
  yacht_id,
  part_number,
  name,
  description,
  category,
  quantity_on_hand,
  minimum_quantity,
  unit,
  location,
  created_at,
  updated_at
) VALUES (
  'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'OF-CAT-1R0739',
  'Oil Filter - CAT 1R0739',
  'Oil filter for Caterpillar C18 generator',
  'filters',
  5,
  3,
  'ea',
  'Shelf A3, Box 12',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 7. FAULTS (table: faults)
-- ============================================================================
INSERT INTO faults (
  id,
  yacht_id,
  equipment_id,
  title,
  description,
  severity,
  reported_by,
  detected_at,
  created_at,
  updated_at
) VALUES (
  'ffffffff-ffff-ffff-ffff-ffffffffffff',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'dddddddd-dddd-dddd-dddd-dddddddddddd',
  'Generator oil pressure warning',
  'Low oil pressure light illuminated during operation',
  'medium',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  NOW(),
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 8. WORK ORDERS (table: work_orders)
-- ============================================================================
INSERT INTO work_orders (
  id,
  yacht_id,
  number,
  title,
  description,
  priority,
  status,
  equipment_id,
  fault_id,
  assigned_to,
  created_by,
  created_at,
  updated_at
) VALUES (
  '33333333-3333-3333-3333-333333333333',
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  'WO-2026-001',
  'Generator #1 - 500 Hour Maintenance',
  'Routine 500-hour maintenance including oil change and filter replacement',
  'normal',
  'open',
  'dddddddd-dddd-dddd-dddd-dddddddddddd',
  'ffffffff-ffff-ffff-ffff-ffffffffffff',
  'cccccccc-cccc-cccc-cccc-cccccccccccc',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  NOW(),
  NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
  yacht_count INTEGER;
  user_count INTEGER;
  equip_count INTEGER;
  part_count INTEGER;
  fault_count INTEGER;
  wo_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO yacht_count FROM yachts;
  SELECT COUNT(*) INTO user_count FROM auth_users_profiles;
  SELECT COUNT(*) INTO equip_count FROM equipment;
  SELECT COUNT(*) INTO part_count FROM parts;
  SELECT COUNT(*) INTO fault_count FROM faults;
  SELECT COUNT(*) INTO wo_count FROM work_orders;

  RAISE NOTICE '================================';
  RAISE NOTICE 'SEED DATA VERIFICATION';
  RAISE NOTICE '================================';
  RAISE NOTICE 'Yachts: %', yacht_count;
  RAISE NOTICE 'Users: %', user_count;
  RAISE NOTICE 'Equipment: %', equip_count;
  RAISE NOTICE 'Parts: %', part_count;
  RAISE NOTICE 'Faults: %', fault_count;
  RAISE NOTICE 'Work Orders: %', wo_count;
  RAISE NOTICE '================================';

  IF yacht_count >= 1 AND user_count >= 2 THEN
    RAISE NOTICE '✅ Seed data loaded successfully!';
  ELSE
    RAISE WARNING '⚠️  Some seed data may be missing';
  END IF;
END $$;

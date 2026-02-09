-- Configure test user roles in TENANT DB auth_users_roles
-- This enables proper action surfacing for inventory tests

-- HOD user: chief_engineer (elevated role - can MUTATE)
INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active, valid_from)
VALUES (
  '05a488fd-e099-4d18-bf86-d87afba4fcdf',
  '85fe1119-b04c-41ac-80f1-829d23322598',
  'chief_engineer',
  true,
  NOW()
)
ON CONFLICT (user_id, yacht_id, role)
DO UPDATE SET
  is_active = true,
  valid_from = NOW();

-- CREW user: crew (base role - READ-only)
INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active, valid_from)
VALUES (
  '57e82f78-0a2d-4a7c-a428-6287621d06c5',
  '85fe1119-b04c-41ac-80f1-829d23322598',
  'crew',
  true,
  NOW()
)
ON CONFLICT (user_id, yacht_id, role)
DO UPDATE SET
  is_active = true,
  valid_from = NOW();

-- Verify insertions
SELECT
  user_id,
  yacht_id,
  role,
  is_active,
  valid_from
FROM auth_users_roles
WHERE user_id IN (
  '05a488fd-e099-4d18-bf86-d87afba4fcdf',
  '57e82f78-0a2d-4a7c-a428-6287621d06c5'
)
AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ORDER BY user_id, role;

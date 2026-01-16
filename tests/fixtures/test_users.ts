/**
 * Test Users Configuration
 *
 * Role-based test accounts for RLS permission testing.
 *
 * IMPORTANT: These accounts must exist in Supabase Auth with:
 * - Matching email/password
 * - Linked user_accounts record with correct role
 * - Linked to test yacht (85fe1119-b04c-41ac-80f1-829d23322598)
 *
 * Roles hierarchy (from CLAUDE.md):
 * - member: Basic crew member, view-only + notes
 * - crew: Deck/engine crew, basic actions
 * - eto: Electro-Technical Officer, equipment specialist
 * - engineer: Junior engineer
 * - 2nd_engineer: Second engineer
 * - chief_engineer: Head of Department (HOD), full engineering authority
 * - chief_officer: Chief Officer, deck authority
 * - captain: Master, full authority
 * - manager: Shore-side management
 * - admin: System administrator
 * - owner: Yacht owner
 */

export type UserRole =
  | 'member'
  | 'crew'
  | 'eto'
  | 'engineer'
  | '2nd_engineer'
  | 'chief_engineer'
  | 'chief_officer'
  | 'captain'
  | 'manager'
  | 'admin'
  | 'owner';

export interface TestUser {
  email: string;
  password: string;
  role: UserRole;
  displayName: string;
  canApprove: boolean;
  isHOD: boolean;
}

/**
 * HOD (Head of Department) roles - can approve, assign, delete
 */
export const HOD_ROLES: UserRole[] = [
  'chief_engineer',
  'chief_officer',
  'captain',
  'manager',
  'admin',
  'owner',
];

/**
 * Purchase approver roles - can approve purchase orders
 * From p1_purchasing_handlers.py: PURCHASE_APPROVER_ROLES
 */
export const PURCHASE_APPROVER_ROLES: UserRole[] = [
  'captain',
  'chief_engineer',
  'chief_officer',
  'admin',
  'owner',
];

/**
 * Delivery receiver roles - can log delivery received
 * From purchasing_mutation_handlers.py
 */
export const DELIVERY_RECEIVER_ROLES: UserRole[] = [
  'chief_engineer',
  'chief_officer',
  'captain',
  'admin',
];

/**
 * Work order completion roles - can mark WO complete
 */
export const WO_COMPLETION_ROLES: UserRole[] = [
  'engineer',
  '2nd_engineer',
  'chief_engineer',
  'eto',
  'chief_officer',
  'captain',
  'admin',
];

/**
 * Work order assignment roles - HOD only
 */
export const WO_ASSIGNMENT_ROLES: UserRole[] = [
  'chief_engineer',
  'eto',
  'captain',
  'manager',
  'admin',
];

/**
 * Test users by role
 *
 * NOTE: For production testing, these users must be created in Supabase Auth
 * with matching credentials and user_accounts records.
 *
 * Current test environment uses single user: x@alex-short.com (chief_engineer)
 */
export const TEST_USERS: Record<string, TestUser> = {
  // Basic member - view only + notes
  member: {
    email: 'member@test.celeste7.ai',
    password: 'TestPass1!',
    role: 'member',
    displayName: 'Test Member',
    canApprove: false,
    isHOD: false,
  },

  // Crew member - basic actions
  crew: {
    email: 'crew@test.celeste7.ai',
    password: 'TestPass1!',
    role: 'crew',
    displayName: 'Test Crew',
    canApprove: false,
    isHOD: false,
  },

  // ETO - equipment specialist
  eto: {
    email: 'eto@test.celeste7.ai',
    password: 'TestPass1!',
    role: 'eto',
    displayName: 'Test ETO',
    canApprove: false,
    isHOD: false,
  },

  // Engineer - junior
  engineer: {
    email: 'engineer@test.celeste7.ai',
    password: 'TestPass1!',
    role: 'engineer',
    displayName: 'Test Engineer',
    canApprove: false,
    isHOD: false,
  },

  // Chief Engineer - HOD
  chief_engineer: {
    email: 'x@alex-short.com', // PRIMARY TEST USER
    password: 'Password2!',
    role: 'chief_engineer',
    displayName: 'Chief Engineer',
    canApprove: true,
    isHOD: true,
  },

  // Captain - full authority
  captain: {
    email: 'captain@test.celeste7.ai',
    password: 'TestPass1!',
    role: 'captain',
    displayName: 'Test Captain',
    canApprove: true,
    isHOD: true,
  },

  // Manager - shore-side
  manager: {
    email: 'manager@test.celeste7.ai',
    password: 'TestPass1!',
    role: 'manager',
    displayName: 'Test Manager',
    canApprove: true,
    isHOD: true,
  },

  // Admin - system admin
  admin: {
    email: 'admin@test.celeste7.ai',
    password: 'TestPass1!',
    role: 'admin',
    displayName: 'Test Admin',
    canApprove: true,
    isHOD: true,
  },
};

/**
 * Get the primary test user (chief_engineer)
 */
export function getPrimaryTestUser(): TestUser {
  return TEST_USERS.chief_engineer;
}

/**
 * Get users who CAN perform an action
 */
export function getUsersWithPermission(allowedRoles: UserRole[]): TestUser[] {
  return Object.values(TEST_USERS).filter((user) =>
    allowedRoles.includes(user.role)
  );
}

/**
 * Get users who CANNOT perform an action
 */
export function getUsersWithoutPermission(allowedRoles: UserRole[]): TestUser[] {
  return Object.values(TEST_USERS).filter(
    (user) => !allowedRoles.includes(user.role)
  );
}

/**
 * Check if a role can approve purchases
 */
export function canApprovePurchase(role: UserRole): boolean {
  return PURCHASE_APPROVER_ROLES.includes(role);
}

/**
 * Check if a role can log delivery received
 */
export function canLogDelivery(role: UserRole): boolean {
  return DELIVERY_RECEIVER_ROLES.includes(role);
}

/**
 * Check if a role is HOD
 */
export function isHOD(role: UserRole): boolean {
  return HOD_ROLES.includes(role);
}

/**
 * Test yacht ID for RLS testing
 */
export const TEST_YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

/**
 * Alternative yacht ID for cross-tenant testing
 * Users should NOT be able to access data from this yacht
 */
export const OTHER_YACHT_ID = '00000000-0000-0000-0000-000000000000';

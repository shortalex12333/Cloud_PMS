/**
 * Role-Specific Authentication for Part Lens E2E Tests
 * =======================================================
 * Provides login and storage state management for different roles:
 * - Crew: Read-only, no MUTATE/SIGNED actions
 * - Chief Engineer: Can execute MUTATE actions (head of engineering dept)
 * - Captain: Can execute SIGNED actions
 * - Manager: Storage delete permissions
 */

import { Page, BrowserContext } from '@playwright/test';
import { login, getBootstrap, AuthTokens, UserBootstrap } from '../../../helpers/auth';
import * as fs from 'fs';
import * as path from 'path';

export type Role = 'crew' | 'chief_engineer' | 'captain' | 'manager';

export interface RoleAuthState {
  tokens: AuthTokens;
  bootstrap: UserBootstrap;
  role: Role;
}

const STORAGE_STATE_DIR = path.join(process.cwd(), 'test-results', '.auth-states');

/**
 * Get email and password for a role
 */
function getRoleCredentials(role: Role): { email: string; password: string } {
  const envPrefix = role.toUpperCase();
  const email = process.env[`${envPrefix}_EMAIL`];
  const password = process.env[`${envPrefix}_PASSWORD`];

  if (!email || !password) {
    throw new Error(`${envPrefix}_EMAIL and ${envPrefix}_PASSWORD must be set in .env.e2e.local`);
  }

  return { email, password };
}

/**
 * Login as specific role and get auth state
 */
export async function loginAsRole(role: Role): Promise<RoleAuthState> {
  const { email, password } = getRoleCredentials(role);

  const tokens = await login(email, password);
  const bootstrap = await getBootstrap(tokens.accessToken);

  // Verify role matches expected
  const actualRole = bootstrap.role.toLowerCase();
  if (actualRole !== role && actualRole !== role.toUpperCase()) {
    console.warn(
      `[WARNING] Expected role '${role}', but user has role '${bootstrap.role}'. ` +
      `This may cause test failures if permissions don't match expectations.`
    );
  }

  return {
    tokens,
    bootstrap,
    role,
  };
}

/**
 * Save storage state for role (for reuse across tests)
 */
export function saveStorageState(role: Role, authState: RoleAuthState): void {
  fs.mkdirSync(STORAGE_STATE_DIR, { recursive: true });

  const statePath = path.join(STORAGE_STATE_DIR, `${role}-state.json`);

  // Playwright storage state format
  const storageState = {
    cookies: [],
    origins: [
      {
        origin: process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai',
        localStorage: [
          {
            name: 'sb-qvzmkaamzaqxpzbewjxe-auth-token',
            value: JSON.stringify({
              access_token: authState.tokens.accessToken,
              refresh_token: authState.tokens.refreshToken,
              expires_at: authState.tokens.expiresAt,
              token_type: 'bearer',
              user: {
                id: authState.bootstrap.userId,
                email: authState.bootstrap.email,
              },
            }),
          },
          {
            name: 'user-bootstrap',
            value: JSON.stringify(authState.bootstrap),
          },
        ],
      },
    ],
  };

  fs.writeFileSync(statePath, JSON.stringify(storageState, null, 2));
  console.log(`[AUTH] Saved ${role} storage state to ${statePath}`);
}

/**
 * Load storage state for role
 */
export function getStorageStatePath(role: Role): string | undefined {
  const statePath = path.join(STORAGE_STATE_DIR, `${role}-state.json`);

  if (fs.existsSync(statePath)) {
    return statePath;
  }

  return undefined;
}

/**
 * Setup auth for role in Playwright context
 */
export async function setupRoleAuth(context: BrowserContext, role: Role): Promise<RoleAuthState> {
  console.log(`[AUTH] Setting up authentication for role: ${role}`);

  const authState = await loginAsRole(role);
  saveStorageState(role, authState);

  return authState;
}

/**
 * Navigate to app and verify login state
 */
export async function navigateWithAuth(page: Page, role: Role): Promise<void> {
  const baseUrl = process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai';

  await page.goto(baseUrl);

  // Wait for app to be ready (check for search bar or nav)
  await page.waitForSelector('[data-testid="search-input"], input[placeholder*="Search"]', {
    timeout: 10000,
    state: 'visible',
  });

  console.log(`[AUTH] Navigated to ${baseUrl} as ${role}`);
}

/**
 * Get JWT token for API calls from page context
 */
export async function getJWTFromPage(page: Page): Promise<string> {
  // Extract JWT from localStorage
  const token = await page.evaluate(() => {
    const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
    if (!authKey) return null;

    const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
    return authData.access_token || null;
  });

  if (!token) {
    throw new Error('No JWT token found in page context');
  }

  return token;
}

/**
 * Setup all role storage states (run once in global setup)
 */
export async function setupAllRoleStorageStates(): Promise<void> {
  const roles: Role[] = ['crew', 'chief_engineer', 'captain'];

  // Try manager, but don't fail if not available
  const managerEmail = process.env.MANAGER_EMAIL;
  if (managerEmail && managerEmail !== 'manager.tenant@alex-short.com') {
    roles.push('manager');
  }

  console.log('[GLOBAL SETUP] Creating storage states for roles:', roles.join(', '));

  for (const role of roles) {
    try {
      const authState = await loginAsRole(role);
      saveStorageState(role, authState);
      console.log(`[GLOBAL SETUP] ✓ ${role} storage state created`);
    } catch (error) {
      if (role === 'manager') {
        console.log(`[GLOBAL SETUP] ⚠ Manager account not available, storage tests will be skipped`);
      } else {
        console.error(`[GLOBAL SETUP] ✗ Failed to create ${role} storage state:`, error);
        throw error;
      }
    }
  }
}

// e2e/global-setup.ts
//
// Generates auth state files with self-minted JWTs so that Playwright
// browser contexts have a valid Supabase session in localStorage.
//
// The JWT is signed with SUPABASE_JWT_SECRET (same key the API uses).
// The frontend Supabase client reads it from localStorage on init and
// uses the access_token for all /v1/ API calls via the Authorization header.
//
// All three role files (captain, hod, crew) currently use the same captain
// user — role differentiation is resolved server-side from auth_users_roles,
// not from the JWT claims. When dedicated role users are provisioned,
// update the sub/email per role.

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

const AUTH_DIR = path.join(__dirname, '../playwright/.auth');
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';

// Supabase project ref — derived from the frontend's NEXT_PUBLIC_SUPABASE_URL.
// This must match whatever project the running frontend is connected to, because
// the Supabase SDK looks for `sb-{ref}-auth-token` in localStorage.
//
// Local dev  (localhost:3001): NEXT_PUBLIC_SUPABASE_URL = vzsohavtuotocgrfkfyd → TENANT project
// Production (app.celeste7.ai): build uses qvzmkaamzaqxpzbewjxe  → MASTER project
//
// Pass NEXT_PUBLIC_SUPABASE_URL as an env var or it defaults to the tenant URL.
const _supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SUPABASE_PROJECT_REF = new URL(_supabaseUrl).hostname.split('.')[0];
const STORAGE_KEY = `sb-${SUPABASE_PROJECT_REF}-auth-token`;

// Per-role test users — each has the correct role in auth_users_roles for TEST_YACHT_ID.
// Verified 2026-04-13 against vzsohavtuotocgrfkfyd (tenant DB).
// auth.users.id values — verified 2026-04-13 via /auth/v1/admin/users.
// IMPORTANT: these MUST be auth.users.id (Supabase native user UUIDs).
//            auth_users_profiles.id is a SEPARATE surrogate key and will not work as JWT sub.
// hod.test@alex-short.com has NO auth.users entry → use eto.test (role: eto, also an HOD).
// captain.tenant@alex-short.com: auth.users.id = 5af9d61d (NOT b72c35ff which is profiles.id).
const USERS: Record<string, { sub: string; email: string }> = {
  crew:    { sub: '4a66036f-899c-40c8-9b2a-598cee24a62f', email: 'engineer.test@alex-short.com' },
  hod:     { sub: '81c239df-f8ef-4bba-9496-78bf8f46733c', email: 'eto.test@alex-short.com'      },
  captain: { sub: '5af9d61d-9b2e-4db4-a54c-a3c95eec70e5', email: 'captain.tenant@alex-short.com' },
  user:    { sub: 'f11f1247-b7bd-4017-bfe3-ebd3f8c9e871', email: 'fleet-test-1775570624@celeste7.ai' },
};

function mintJwt(sub: string, email: string, expiresInSeconds = 8 * 3600): string {
  const secretString = process.env.SUPABASE_JWT_SECRET;
  if (!secretString) {
    console.warn('[global-setup] SUPABASE_JWT_SECRET not set — writing empty auth state');
    return '';
  }
  const secretBytes = Buffer.from(secretString, 'utf8');
  const now = Math.floor(Date.now() / 1000);

  function b64url(obj: object | string): string {
    const json = typeof obj === 'string' ? obj : JSON.stringify(obj);
    return Buffer.from(json).toString('base64url');
  }

  const header = b64url({ alg: 'HS256', typ: 'JWT' });
  const payload = b64url({
    sub, aud: 'authenticated', role: 'authenticated',
    email, iat: now, exp: now + expiresInSeconds,
    iss: `${_supabaseUrl}/auth/v1`,
  });
  const sig = crypto.createHmac('sha256', secretBytes)
    .update(`${header}.${payload}`).digest('base64url');

  return `${header}.${payload}.${sig}`;
}

function buildAuthState(jwt: string, sub: string, email: string): string {
  if (!jwt) {
    return JSON.stringify({ cookies: [], origins: [] });
  }

  // Playwright storageState format: origins[].localStorage[] entries
  // are injected into the browser context before any page scripts run.
  const sessionData = JSON.stringify({
    access_token: jwt,
    token_type: 'bearer',
    expires_in: 28800,
    expires_at: Math.floor(Date.now() / 1000) + 28800,
    refresh_token: '',
    user: {
      id: sub,
      email,
      aud: 'authenticated',
      role: 'authenticated',
    },
  });

  return JSON.stringify({
    cookies: [],
    origins: [{
      origin: BASE_URL,
      localStorage: [
        { name: STORAGE_KEY, value: sessionData },
      ],
    }],
  }, null, 2);
}

async function globalSetup() {
  // Ensure auth directory exists
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  }

  // Mint per-role JWTs — each user has the correct role in auth_users_roles.
  // Also write a fleet_manager.json for FleetView tests.
  const roleFiles: Array<{ file: string; key: keyof typeof USERS }> = [
    { file: 'crew',          key: 'crew'    },
    { file: 'hod',           key: 'hod'     },
    { file: 'captain',       key: 'captain' },
    { file: 'user',          key: 'user'    },
    { file: 'fleet_manager', key: 'user'    }, // manager role — same user as 'user'
  ];

  for (const { file, key } of roleFiles) {
    const u = USERS[key];
    const jwt = mintJwt(u.sub, u.email);
    const filePath = path.join(AUTH_DIR, `${file}.json`);
    fs.writeFileSync(filePath, buildAuthState(jwt, u.sub, u.email));
  }

  const hasSecret = !!process.env.SUPABASE_JWT_SECRET;
  if (hasSecret) {
    console.log(`[global-setup] Auth state written for crew/hod/captain/user/fleet_manager (JWT valid 8h, project: ${SUPABASE_PROJECT_REF})`);
  } else {
    console.log(`[global-setup] Empty auth state — SUPABASE_JWT_SECRET not set`);
  }
}

export default globalSetup;

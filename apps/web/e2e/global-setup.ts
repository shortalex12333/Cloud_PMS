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

// Supabase project ref — extracted from NEXT_PUBLIC_SUPABASE_URL or hardcoded.
// The localStorage key is `sb-{ref}-auth-token`.
const SUPABASE_PROJECT_REF = 'vzsohavtuotocgrfkfyd';
const STORAGE_KEY = `sb-${SUPABASE_PROJECT_REF}-auth-token`;

// Captain user — all roles currently map to this user (see STAGE_3_HANDOVER.md §8)
const CAPTAIN_SUB = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';
const CAPTAIN_EMAIL = 'x@alex-short.com';

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
    iss: `https://${SUPABASE_PROJECT_REF}.supabase.co/auth/v1`,
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

  // Mint a captain JWT (all roles use the same user for now)
  const jwt = mintJwt(CAPTAIN_SUB, CAPTAIN_EMAIL);

  // Write auth state files — always overwrite to ensure fresh JWTs
  for (const role of ['captain', 'hod', 'crew', 'user']) {
    const filePath = path.join(AUTH_DIR, `${role}.json`);
    fs.writeFileSync(filePath, buildAuthState(jwt, CAPTAIN_SUB, CAPTAIN_EMAIL));
  }

  if (jwt) {
    console.log(`[global-setup] Auth state written for captain/hod/crew/user (JWT valid 8h)`);
  } else {
    console.log(`[global-setup] Empty auth state — SUPABASE_JWT_SECRET not set`);
  }
}

export default globalSetup;

// e2e/global-setup.ts
//
// Generates auth state files backed by REAL Supabase sessions.
//
// Previously this file self-minted HS256 JWTs and injected them into
// localStorage as `sb-{ref}-auth-token`. That shape is accepted by the
// API (same HMAC secret) but the Supabase JS client re-validates the
// session on page load via GET /auth/v1/user — because the JWT sub
// didn't correspond to an actual Supabase auth session, the client
// cleared the token and redirected to login. This caused BUG-HOR-4
// (UI tab-visibility tests permanently skipped).
//
// Fix: call supabase.auth.signInWithPassword() with real test users and
// write the returned session into storageState exactly the way the
// supabase-js client serialises it. The client then accepts the session
// on page load without redirecting.
//
// The legacy `mintJwt()` is kept (deprecated, un-exported) only as an
// offline fallback for rare scenarios where the auth service is
// unreachable.

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import { createClient, Session } from '@supabase/supabase-js';

const AUTH_DIR = path.join(__dirname, '../playwright/.auth');
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';

// Supabase project ref — derived from the frontend's NEXT_PUBLIC_SUPABASE_URL.
// This must match whatever project the running frontend is connected to, because
// the Supabase SDK looks for `sb-{ref}-auth-token` in localStorage.
//
// E2E setup authenticates against the SAME project the frontend targets.
// Prefer E2E_SUPABASE_URL; fall back to NEXT_PUBLIC_SUPABASE_URL; else tenant default.
const SUPABASE_URL =
  process.env.E2E_SUPABASE_URL ||
  process.env.NEXT_PUBLIC_SUPABASE_URL ||
  'https://vzsohavtuotocgrfkfyd.supabase.co';
const SUPABASE_ANON_KEY =
  process.env.E2E_SUPABASE_ANON_KEY ||
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  '';
const SUPABASE_PROJECT_REF = new URL(SUPABASE_URL).hostname.split('.')[0];
const STORAGE_KEY = `sb-${SUPABASE_PROJECT_REF}-auth-token`;

// Per-role test users — each has the correct role in auth_users_roles for TEST_YACHT_ID.
// Credentials confirmed in production (2026-04-17). Values may be overridden via env.
const CREDENTIALS = {
  crew: {
    email:    process.env.E2E_CREW_EMAIL    || 'engineer.test@alex-short.com',
    password: process.env.E2E_CREW_PASSWORD || 'Password2!',
  },
  hod: {
    email:    process.env.E2E_HOD_EMAIL    || 'eto.test@alex-short.com',
    password: process.env.E2E_HOD_PASSWORD || 'Password2!',
  },
  captain: {
    email:    process.env.E2E_CAPTAIN_EMAIL    || 'x@alex-short.com',
    password: process.env.E2E_CAPTAIN_PASSWORD || 'Password2!',
  },
  fleet_manager: {
    email:    process.env.E2E_FLEET_MANAGER_EMAIL    || 'fleet-test-1775570624@celeste7.ai',
    password: process.env.E2E_FLEET_MANAGER_PASSWORD || 'Password2!',
  },
};

/**
 * Log in as a real Supabase user and return the full session object.
 * The session is never persisted inside the client — we lift the tokens
 * out and write them to the Playwright storageState file ourselves.
 */
async function loginAs(email: string, password: string): Promise<Session> {
  const client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error || !data.session) {
    throw new Error(`[global-setup] E2E login failed for ${email}: ${error?.message || 'no session'}`);
  }
  return data.session;
}

/**
 * Build a Playwright storageState that contains the session in exactly the
 * shape `supabase-js` writes it under `sb-{ref}-auth-token`. On page load
 * the Supabase client reads this key, sees a valid session, and does not
 * redirect to login.
 */
function buildAuthState(session: Session): string {
  const sessionData = JSON.stringify({
    access_token:  session.access_token,
    refresh_token: session.refresh_token,
    expires_in:    session.expires_in,
    expires_at:    session.expires_at,
    token_type:    session.token_type || 'bearer',
    user:          session.user,
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

/**
 * @deprecated Offline fallback only. Real-session login via `loginAs()` is
 * the supported path — self-minted JWTs are rejected by the Supabase client
 * on page load (see BUG-HOR-4). This remains available for scenarios where
 * the auth service is unreachable and only the API-level HMAC check matters.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
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
    iss: `${SUPABASE_URL}/auth/v1`,
  });
  const sig = crypto.createHmac('sha256', secretBytes)
    .update(`${header}.${payload}`).digest('base64url');

  return `${header}.${payload}.${sig}`;
}

async function globalSetup() {
  // Ensure auth directory exists
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  }

  if (!SUPABASE_ANON_KEY) {
    console.warn('[global-setup] E2E_SUPABASE_ANON_KEY / NEXT_PUBLIC_SUPABASE_ANON_KEY not set — writing empty auth state.');
    for (const file of ['crew', 'hod', 'captain', 'user', 'fleet_manager']) {
      fs.writeFileSync(
        path.join(AUTH_DIR, `${file}.json`),
        JSON.stringify({ cookies: [], origins: [] }),
      );
    }
    return;
  }

  // Real Supabase logins — one per role. `user` and `fleet_manager` both
  // map to the fleet manager account (role-differentiation is resolved
  // server-side from auth_users_roles, not from the JWT claims).
  const crewSession    = await loginAs(CREDENTIALS.crew.email,          CREDENTIALS.crew.password);
  const hodSession     = await loginAs(CREDENTIALS.hod.email,           CREDENTIALS.hod.password);
  const captainSession = await loginAs(CREDENTIALS.captain.email,       CREDENTIALS.captain.password);
  const fmSession      = await loginAs(CREDENTIALS.fleet_manager.email, CREDENTIALS.fleet_manager.password);

  const roleFiles: Array<{ file: string; session: Session }> = [
    { file: 'crew',          session: crewSession    },
    { file: 'hod',           session: hodSession     },
    { file: 'captain',       session: captainSession },
    { file: 'user',          session: fmSession      },
    { file: 'fleet_manager', session: fmSession      },
  ];

  for (const { file, session } of roleFiles) {
    const filePath = path.join(AUTH_DIR, `${file}.json`);
    fs.writeFileSync(filePath, buildAuthState(session));
  }

  console.log(`[global-setup] Auth state written for crew/hod/captain/user/fleet_manager (real Supabase sessions, project: ${SUPABASE_PROJECT_REF})`);
}

export default globalSetup;

// CelesteOS Authentication & Authorization Middleware
// Handles JWT validation, yacht isolation, and role-based access

import { Context, Next } from 'hono';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import type { User, APIError } from '../types/index.js';

// ============================================================================
// TYPES
// ============================================================================

export interface AuthContext {
  user: User;
  yacht_id: string;
  role: string;
  supabase: SupabaseClient;
}

declare module 'hono' {
  interface ContextVariableMap {
    auth: AuthContext;
    supabase: SupabaseClient;
  }
}

// ============================================================================
// CONFIGURATION
// ============================================================================

const SUPABASE_URL = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || '';

// Role hierarchy for permission checks
const ROLE_HIERARCHY: Record<string, number> = {
  'guest': 0,
  'viewer': 1,
  'eto': 2,
  'deck': 2,
  'stew': 2,
  'engineer': 3,
  'chief_engineer': 4,
  'hod': 4,
  'captain': 5,
  'manager': 5,
  'admin': 10,
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function createError(code: string, message: string, status: number = 400): Response {
  const error: APIError = {
    status: 'error',
    error_code: code,
    message,
  };
  return new Response(JSON.stringify(error), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function getSupabaseClient(token?: string): SupabaseClient {
  if (token) {
    return createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      global: {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    });
  }
  return createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}

function getServiceClient(): SupabaseClient {
  return createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
}

// ============================================================================
// AUTH MIDDLEWARE
// ============================================================================

export async function authMiddleware(c: Context, next: Next) {
  const authHeader = c.req.header('Authorization');

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return createError('unauthorized', 'Missing or invalid authorization header', 401);
  }

  const token = authHeader.replace('Bearer ', '');
  const supabase = getSupabaseClient(token);

  try {
    // Verify token and get user
    const { data: { user: authUser }, error: authError } = await supabase.auth.getUser(token);

    if (authError || !authUser) {
      return createError('unauthorized', 'Invalid or expired token', 401);
    }

    // Get user profile with yacht info
    const { data: userProfile, error: profileError } = await supabase
      .from('users')
      .select('*')
      .eq('id', authUser.id)
      .single();

    if (profileError || !userProfile) {
      return createError('unauthorized', 'User profile not found', 401);
    }

    if (!userProfile.is_active) {
      return createError('forbidden', 'User account is deactivated', 403);
    }

    // Set auth context
    c.set('auth', {
      user: userProfile as User,
      yacht_id: userProfile.yacht_id,
      role: userProfile.role,
      supabase,
    });

    c.set('supabase', supabase);

    await next();
  } catch (err) {
    console.error('Auth middleware error:', err);
    return createError('internal_error', 'Authentication failed', 500);
  }
}

// ============================================================================
// YACHT ISOLATION MIDDLEWARE
// ============================================================================

export async function yachtIsolationMiddleware(c: Context, next: Next) {
  const auth = c.get('auth');

  if (!auth) {
    return createError('unauthorized', 'Not authenticated', 401);
  }

  // Check yacht signature header if present
  const yachtSignature = c.req.header('X-Yacht-Signature');
  if (yachtSignature) {
    // Validate signature matches user's yacht
    const serviceClient = getServiceClient();
    const { data: yacht } = await serviceClient
      .from('yachts')
      .select('id, signature')
      .eq('id', auth.yacht_id)
      .single();

    if (!yacht || yacht.signature !== yachtSignature) {
      return createError('yacht_mismatch', 'Yacht signature does not match', 403);
    }
  }

  // Validate yacht_id in request body/params matches user's yacht
  let requestYachtId: string | undefined;

  // Check body for POST/PUT/PATCH
  if (['POST', 'PUT', 'PATCH'].includes(c.req.method)) {
    try {
      const body = await c.req.json();
      requestYachtId = body?.context?.yacht_id || body?.yacht_id;
    } catch {
      // No JSON body, that's fine
    }
  }

  // Check query params for GET/DELETE
  if (!requestYachtId) {
    requestYachtId = c.req.query('yacht_id');
  }

  // If yacht_id is provided in request, it must match user's yacht
  if (requestYachtId && requestYachtId !== auth.yacht_id) {
    return createError('yacht_mismatch', 'Cannot access data from another yacht', 403);
  }

  await next();
}

// ============================================================================
// ROLE CHECK MIDDLEWARE FACTORY
// ============================================================================

export function requireRole(...allowedRoles: string[]) {
  return async (c: Context, next: Next) => {
    const auth = c.get('auth');

    if (!auth) {
      return createError('unauthorized', 'Not authenticated', 401);
    }

    const userRole = auth.role.toLowerCase();

    // Check if user has any of the allowed roles
    const hasRole = allowedRoles.some(role => {
      const normalizedRole = role.toLowerCase();
      // Exact match
      if (userRole === normalizedRole) return true;
      // Admin has all permissions
      if (userRole === 'admin') return true;
      // Check hierarchy - higher roles include lower permissions
      const userLevel = ROLE_HIERARCHY[userRole] || 0;
      const requiredLevel = ROLE_HIERARCHY[normalizedRole] || 0;
      return userLevel >= requiredLevel;
    });

    if (!hasRole) {
      return createError(
        'forbidden',
        `User role '${auth.role}' cannot perform this action. Required: ${allowedRoles.join(' or ')}`,
        403
      );
    }

    await next();
  };
}

// ============================================================================
// SERVICE AUTH MIDDLEWARE (for internal n8n calls)
// ============================================================================

export async function serviceAuthMiddleware(c: Context, next: Next) {
  const serviceKey = c.req.header('X-Service-Key');
  const expectedKey = process.env.INTERNAL_SERVICE_KEY;

  if (!expectedKey) {
    // If no service key configured, skip this check (development mode)
    c.set('supabase', getServiceClient());
    await next();
    return;
  }

  if (!serviceKey || serviceKey !== expectedKey) {
    return createError('unauthorized', 'Invalid service key', 401);
  }

  c.set('supabase', getServiceClient());
  await next();
}

// ============================================================================
// OPTIONAL AUTH MIDDLEWARE (for public endpoints)
// ============================================================================

export async function optionalAuthMiddleware(c: Context, next: Next) {
  const authHeader = c.req.header('Authorization');

  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.replace('Bearer ', '');
    const supabase = getSupabaseClient(token);

    try {
      const { data: { user: authUser } } = await supabase.auth.getUser(token);

      if (authUser) {
        const { data: userProfile } = await supabase
          .from('users')
          .select('*')
          .eq('id', authUser.id)
          .single();

        if (userProfile && userProfile.is_active) {
          c.set('auth', {
            user: userProfile as User,
            yacht_id: userProfile.yacht_id,
            role: userProfile.role,
            supabase,
          });
        }
      }
    } catch {
      // Ignore auth errors for optional auth
    }
  }

  // Always set a supabase client even without auth
  if (!c.get('supabase')) {
    c.set('supabase', getSupabaseClient());
  }

  await next();
}

// ============================================================================
// EXPORTS
// ============================================================================

export { getSupabaseClient, getServiceClient, createError };

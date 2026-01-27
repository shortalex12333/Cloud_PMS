/**
 * /api/debug/auth-dump - Development-only auth debugging endpoint
 *
 * SECURITY: Only enabled when ENABLE_DEBUG_ROUTES=true
 * DO NOT enable in production!
 *
 * Returns:
 * {
 *   hasBearer: boolean,
 *   bearerLength: number,
 *   validated: boolean,
 *   userId: string | null,
 *   error: string | null,
 *   supabaseProject: string,
 *   timestamp: string
 * }
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  // Security check: only allow in development
  const enableDebug = process.env.ENABLE_DEBUG_ROUTES === 'true';
  const isDev = process.env.NODE_ENV === 'development';

  if (!enableDebug && !isDev) {
    return NextResponse.json(
      { error: 'Debug routes disabled in production' },
      { status: 403 }
    );
  }

  const result: Record<string, any> = {
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV,
  };

  // Check Authorization header
  const authHeader = request.headers.get('authorization');
  result.hasBearer = !!authHeader && authHeader.startsWith('Bearer ');
  result.bearerLength = authHeader?.split(' ')[1]?.length || 0;

  if (!result.hasBearer) {
    result.validated = false;
    result.userId = null;
    result.error = 'No Bearer token in Authorization header';
    result.supabaseProject = 'N/A';
    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'no-store' }
    });
  }

  const token = authHeader!.split(' ')[1];

  // Get Supabase URL being used for validation
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

  result.supabaseProject = supabaseUrl.match(/https:\/\/([^.]+)/)?.[1] || 'unknown';
  result.supabaseUrlConfigured = !!supabaseUrl;
  result.supabaseKeyConfigured = !!supabaseKey;

  if (!supabaseUrl || !supabaseKey) {
    result.validated = false;
    result.userId = null;
    result.error = 'Supabase URL or key not configured';
    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'no-store' }
    });
  }

  try {
    // Create client and validate token
    const supabase = createClient(supabaseUrl, supabaseKey, {
      global: { headers: { Authorization: `Bearer ${token}` } }
    });

    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error) {
      result.validated = false;
      result.userId = null;
      result.error = error.message;
      result.errorCode = error.name;
    } else if (user) {
      result.validated = true;
      result.userId = user.id.substring(0, 8) + '...'; // Redacted
      result.userEmail = user.email?.substring(0, 3) + '***'; // Redacted
      result.error = null;
    } else {
      result.validated = false;
      result.userId = null;
      result.error = 'getUser returned null without error';
    }
  } catch (err: any) {
    result.validated = false;
    result.userId = null;
    result.error = err.message || 'Unknown error';
  }

  // Also check what project the JWT claims to be from (decode without verifying)
  try {
    const payload = JSON.parse(Buffer.from(token.split('.')[1], 'base64').toString());
    result.jwtIssuer = payload.iss;
    result.jwtAudience = payload.aud;
    result.jwtExpiry = new Date(payload.exp * 1000).toISOString();
    result.jwtIssuedAt = new Date(payload.iat * 1000).toISOString();

    // Extract project ref from issuer
    const issuerMatch = payload.iss?.match(/https:\/\/([^.]+)/);
    result.jwtProject = issuerMatch?.[1] || 'unknown';

    // Check if JWT project matches validation project
    result.projectMatch = result.jwtProject === result.supabaseProject;
    if (!result.projectMatch) {
      result.warning = `JWT from "${result.jwtProject}" but validating against "${result.supabaseProject}"`;
    }
  } catch {
    result.jwtDecodeError = 'Failed to decode JWT payload';
  }

  return NextResponse.json(result, {
    headers: { 'Cache-Control': 'no-store' }
  });
}

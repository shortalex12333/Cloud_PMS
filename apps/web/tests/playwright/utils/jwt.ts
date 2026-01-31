/**
 * JWT Utility Functions for Playwright Tests
 * ===========================================
 *
 * Handles JWT decoding, validation, and refresh for E2E tests.
 */

export interface JWTPayload {
  sub: string;           // user_id
  email: string;
  exp: number;           // Expiration timestamp (seconds)
  iat: number;           // Issued at timestamp (seconds)
  role?: string;
  yacht_id?: string;
  [key: string]: any;
}

export interface SupabaseSession {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  expires_at?: number;
  token_type: 'bearer';
  user: {
    id: string;
    email: string;
    [key: string]: any;
  };
}

/**
 * Decode JWT without verification (for inspection only)
 */
export function decodeJWT(token: string): JWTPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }

    const payload = parts[1];
    const decoded = Buffer.from(payload, 'base64').toString('utf-8');
    return JSON.parse(decoded);
  } catch (error) {
    console.error('Failed to decode JWT:', error);
    return null;
  }
}

/**
 * Check if JWT is expired or expiring soon
 */
export function isJWTExpiring(token: string, thresholdMinutes: number = 5): boolean {
  const payload = decodeJWT(token);
  if (!payload) {
    return true; // Treat invalid tokens as expired
  }

  const expiresAt = payload.exp * 1000; // Convert to milliseconds
  const now = Date.now();
  const timeUntilExpiry = expiresAt - now;
  const thresholdMs = thresholdMinutes * 60 * 1000;

  return timeUntilExpiry < thresholdMs;
}

/**
 * Get time until JWT expires (in milliseconds)
 */
export function getTimeUntilExpiry(token: string): number {
  const payload = decodeJWT(token);
  if (!payload) {
    return 0; // Already expired or invalid
  }

  const expiresAt = payload.exp * 1000;
  const now = Date.now();
  return Math.max(0, expiresAt - now);
}

/**
 * Format time remaining as human-readable string
 */
export function formatTimeRemaining(milliseconds: number): string {
  const minutes = Math.floor(milliseconds / 60000);
  const seconds = Math.floor((milliseconds % 60000) / 1000);

  if (minutes > 60) {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  }

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }

  return `${seconds}s`;
}

/**
 * Log JWT status for debugging
 */
export function logJWTStatus(token: string, label: string = 'JWT'): void {
  const payload = decodeJWT(token);
  if (!payload) {
    console.log(`❌ ${label}: Invalid or malformed`);
    return;
  }

  const timeRemaining = getTimeUntilExpiry(token);
  const isExpired = timeRemaining <= 0;
  const isExpiringSoon = isJWTExpiring(token, 5);

  const status = isExpired ? '❌ EXPIRED' : isExpiringSoon ? '⚠️  EXPIRING SOON' : '✅ VALID';
  const timeStr = formatTimeRemaining(timeRemaining);

  console.log(`${status} ${label}:`);
  console.log(`  User: ${payload.email} (${payload.sub})`);
  console.log(`  Expires in: ${timeStr}`);
  console.log(`  Issued at: ${new Date(payload.iat * 1000).toISOString()}`);
  console.log(`  Expires at: ${new Date(payload.exp * 1000).toISOString()}`);
}

/**
 * Validate Supabase session structure
 */
export function isValidSession(session: any): session is SupabaseSession {
  return (
    session &&
    typeof session === 'object' &&
    typeof session.access_token === 'string' &&
    typeof session.refresh_token === 'string' &&
    session.access_token.split('.').length === 3
  );
}

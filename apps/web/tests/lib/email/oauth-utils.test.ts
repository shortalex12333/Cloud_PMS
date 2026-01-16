/**
 * Email Transport Layer - OAuth Utilities Tests
 *
 * Tests for:
 * - State generation and parsing
 * - Scope checking (forbidden scopes)
 * - Watcher status determination
 * - Email hashing
 */

import { describe, it, expect } from 'vitest';
import {
  generateOAuthState,
  parseOAuthState,
  checkScopes,
  determineWatcherStatus,
  hashEmail,
  TokenRecord,
} from '@/lib/email/oauth-utils';

describe('OAuth State Management', () => {
  it('generates state with user_id and purpose', () => {
    const state = generateOAuthState('user-123', 'read');
    expect(state).toMatch(/^user-123:read:[a-f0-9]{32}$/);
  });

  it('generates different state for write purpose', () => {
    const state = generateOAuthState('user-123', 'write');
    expect(state).toMatch(/^user-123:write:[a-f0-9]{32}$/);
  });

  it('parses valid state correctly', () => {
    const state = 'user-123:read:abc123def456';
    const result = parseOAuthState(state);
    expect(result).toEqual({ userId: 'user-123', purpose: 'read' });
  });

  it('parses write state correctly', () => {
    const state = 'user-123:write:abc123def456';
    const result = parseOAuthState(state);
    expect(result).toEqual({ userId: 'user-123', purpose: 'write' });
  });

  it('returns null for invalid state', () => {
    expect(parseOAuthState('')).toBeNull();
    expect(parseOAuthState('invalid')).toBeNull();
    expect(parseOAuthState('user:invalid_purpose:random')).toBeNull();
  });
});

describe('Scope Guard', () => {
  it('accepts valid read scopes', () => {
    const result = checkScopes(['Mail.Read', 'User.Read', 'offline_access']);
    expect(result.valid).toBe(true);
    expect(result.forbidden).toHaveLength(0);
  });

  it('accepts valid write scopes', () => {
    const result = checkScopes(['Mail.Send', 'User.Read', 'offline_access']);
    expect(result.valid).toBe(true);
    expect(result.forbidden).toHaveLength(0);
  });

  it('rejects Mail.ReadWrite', () => {
    const result = checkScopes(['Mail.Read', 'Mail.ReadWrite', 'offline_access']);
    expect(result.valid).toBe(false);
    expect(result.forbidden).toContain('Mail.ReadWrite');
    expect(result.warning).toBeDefined();
  });

  it('rejects Mail.ReadWrite.All', () => {
    const result = checkScopes(['Mail.ReadWrite.All']);
    expect(result.valid).toBe(false);
    expect(result.forbidden).toContain('Mail.ReadWrite.All');
  });

  it('rejects Files.Read.All', () => {
    const result = checkScopes(['Mail.Read', 'Files.Read.All']);
    expect(result.valid).toBe(false);
    expect(result.forbidden).toContain('Files.Read.All');
  });

  it('rejects Sites.Read.All', () => {
    const result = checkScopes(['Mail.Read', 'Sites.Read.All']);
    expect(result.valid).toBe(false);
    expect(result.forbidden).toContain('Sites.Read.All');
  });

  it('rejects User.Read.All', () => {
    const result = checkScopes(['Mail.Read', 'User.Read.All']);
    expect(result.valid).toBe(false);
    expect(result.forbidden).toContain('User.Read.All');
  });

  it('detects multiple forbidden scopes', () => {
    const result = checkScopes(['Mail.ReadWrite', 'Files.Read.All', 'Sites.Read.All']);
    expect(result.valid).toBe(false);
    expect(result.forbidden).toHaveLength(3);
  });
});

describe('Watcher Status Determination', () => {
  const makeToken = (purpose: 'read' | 'write', expired = false): TokenRecord => ({
    user_id: 'user-123',
    yacht_id: 'yacht-456',
    provider: 'microsoft_graph',
    token_purpose: purpose,
    microsoft_access_token: 'access',
    microsoft_refresh_token: 'refresh',
    token_expires_at: expired
      ? new Date(Date.now() - 1000).toISOString()
      : new Date(Date.now() + 3600000).toISOString(),
    scopes: [],
    provider_email_hash: 'hash',
    provider_display_name: 'Test User',
    is_revoked: false,
  });

  it('returns active when both tokens valid', () => {
    const readToken = makeToken('read');
    const writeToken = makeToken('write');
    const status = determineWatcherStatus(readToken, writeToken, false);
    expect(status).toBe('active');
  });

  it('returns read_only when only read token valid', () => {
    const readToken = makeToken('read');
    const status = determineWatcherStatus(readToken, null, false);
    expect(status).toBe('read_only');
  });

  it('returns write_only when only write token valid', () => {
    const writeToken = makeToken('write');
    const status = determineWatcherStatus(null, writeToken, false);
    expect(status).toBe('write_only');
  });

  it('returns disconnected when no tokens', () => {
    const status = determineWatcherStatus(null, null, false);
    expect(status).toBe('disconnected');
  });

  it('returns degraded when forbidden scopes detected', () => {
    const readToken = makeToken('read');
    const writeToken = makeToken('write');
    const status = determineWatcherStatus(readToken, writeToken, true);
    expect(status).toBe('degraded');
  });

  it('returns disconnected when read token expired', () => {
    const readToken = makeToken('read', true);
    const status = determineWatcherStatus(readToken, null, false);
    expect(status).toBe('disconnected');
  });

  it('returns read_only when write token expired', () => {
    const readToken = makeToken('read');
    const writeToken = makeToken('write', true);
    const status = determineWatcherStatus(readToken, writeToken, false);
    expect(status).toBe('read_only');
  });
});

describe('Email Hashing', () => {
  it('hashes email consistently', () => {
    const hash1 = hashEmail('test@example.com');
    const hash2 = hashEmail('test@example.com');
    expect(hash1).toBe(hash2);
  });

  it('normalizes case', () => {
    const hash1 = hashEmail('TEST@EXAMPLE.COM');
    const hash2 = hashEmail('test@example.com');
    expect(hash1).toBe(hash2);
  });

  it('trims whitespace', () => {
    const hash1 = hashEmail('  test@example.com  ');
    const hash2 = hashEmail('test@example.com');
    expect(hash1).toBe(hash2);
  });

  it('produces different hashes for different emails', () => {
    const hash1 = hashEmail('user1@example.com');
    const hash2 = hashEmail('user2@example.com');
    expect(hash1).not.toBe(hash2);
  });
});

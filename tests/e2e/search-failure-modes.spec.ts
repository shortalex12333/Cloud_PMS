/**
 * Search Failure Mode Tests
 *
 * Targets: /webhook/search, /api/search
 *
 * Verify:
 * - Unauthorized (no token) → 401
 * - Cross-yacht (mismatched yacht_id) → 403/empty
 * - Malformed, empty, huge queries → 400 (not 500)
 * - Injection/XSS payloads → 400/escaped, no 500
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';

const API_BASE_URL = 'https://pipeline-core.int.celeste7.ai';
const YACHT_ID = 'd4cd63ce-bcf5-4005-9eec-fe58e5b5ba8d';
const OTHER_YACHT_ID = '00000000-0000-0000-0000-000000000001';

const CREW_AUTH_STATE = 'test-results/.auth-states/crew-state.json';

function extractToken(authStatePath: string): string {
  const state = JSON.parse(fs.readFileSync(authStatePath, 'utf-8'));
  const cookies = state.cookies || [];
  const authCookie = cookies.find((c: any) =>
    c.name === 'sb-access-token' ||
    c.name === 'sb-zfvtdepqqyvmjvcqapfy-auth-token'
  );
  return authCookie?.value || '';
}

async function searchRequest(
  token: string | null,
  query: string,
  yachtId: string = YACHT_ID,
  additionalParams: any = {}
): Promise<{ status: number; data: any; isJson: boolean }> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Yacht-Signature': `yacht_id=${yachtId}`
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/webhook/search`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      query,
      yacht_id: yachtId,
      ...additionalParams
    })
  });

  const text = await response.text();
  let data: any;
  let isJson = false;

  try {
    data = JSON.parse(text);
    isJson = true;
  } catch {
    data = { raw: text };
  }

  return { status: response.status, data, isJson };
}

test.describe('Search - Authentication Tests', () => {

  test('No Authorization header (expect 401)', async () => {
    const result = await searchRequest(null, 'oil filter');

    expect(result.status).toBe(401);
    expect(result.status).not.toBe(500);
  });

  test('Invalid Authorization token (expect 401)', async () => {
    const result = await searchRequest('invalid-token-here', 'oil filter');

    expect(result.status).toBe(401);
    expect(result.status).not.toBe(500);
  });

  test('Expired/malformed JWT (expect 401)', async () => {
    const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid';
    const result = await searchRequest(expiredToken, 'oil filter');

    expect(result.status).toBe(401);
    expect(result.status).not.toBe(500);
  });
});

test.describe('Search - Cross-Yacht RLS Tests', () => {

  test('Search with mismatched yacht_id (expect 403 or empty)', async () => {
    const token = extractToken(CREW_AUTH_STATE);

    // User belongs to YACHT_ID but requesting OTHER_YACHT_ID
    const result = await searchRequest(token, 'oil filter', OTHER_YACHT_ID);

    // Should either deny (403) or return empty results (filtered by RLS)
    if (result.status === 200 && result.data.results) {
      expect(result.data.results).toHaveLength(0);
    } else {
      expect([401, 403]).toContain(result.status);
    }
    expect(result.status).not.toBe(500);
  });

  test('Search with invalid yacht_id format (expect 400)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const result = await searchRequest(token, 'oil filter', 'not-a-valid-uuid');

    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });
});

test.describe('Search - Query Validation Tests', () => {

  test('Empty query string (expect 400 or empty results)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const result = await searchRequest(token, '');

    // Should either reject (400) or return empty results
    if (result.status === 200) {
      expect(result.data.results || []).toHaveLength(0);
    } else {
      expect([400, 422]).toContain(result.status);
    }
    expect(result.status).not.toBe(500);
  });

  test('Whitespace-only query (expect 400 or empty)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const result = await searchRequest(token, '   ');

    if (result.status === 200) {
      expect(result.data.results || []).toHaveLength(0);
    } else {
      expect([400, 422]).toContain(result.status);
    }
    expect(result.status).not.toBe(500);
  });

  test('Extremely long query (20KB) (expect 400 or truncated)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const longQuery = 'A'.repeat(20000);
    const result = await searchRequest(token, longQuery);

    // Should either reject (400/413) or handle gracefully
    expect(result.status).not.toBe(500);
  });

  test('Query with only special characters (expect handled)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const result = await searchRequest(token, '!@#$%^&*(){}[]|\\:";\'<>,.?/');

    // Should handle gracefully (empty results or 400)
    expect(result.status).not.toBe(500);
  });

  test('Null query (expect 400)', async () => {
    const token = extractToken(CREW_AUTH_STATE);

    const response = await fetch(`${API_BASE_URL}/webhook/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: JSON.stringify({
        query: null,
        yacht_id: YACHT_ID
      })
    });

    expect([400, 422]).toContain(response.status);
    expect(response.status).not.toBe(500);
  });
});

test.describe('Search - SQL Injection Tests', () => {

  test('Basic SQL injection attempt (expect sanitized, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const sqlInjection = "' OR '1'='1";
    const result = await searchRequest(token, sqlInjection);

    // Should handle safely (empty results or proper error)
    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);  // Should return JSON, not error page
  });

  test('DROP TABLE injection (expect sanitized, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const sqlInjection = "'; DROP TABLE pms_documents; --";
    const result = await searchRequest(token, sqlInjection);

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('UNION SELECT injection (expect sanitized, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const sqlInjection = "' UNION SELECT * FROM users --";
    const result = await searchRequest(token, sqlInjection);

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('Stacked queries injection (expect sanitized, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const sqlInjection = "oil filter; DELETE FROM pms_parts WHERE 1=1;";
    const result = await searchRequest(token, sqlInjection);

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('Time-based blind SQL injection (expect no delay)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const sqlInjection = "oil' AND SLEEP(5) --";

    const startTime = Date.now();
    const result = await searchRequest(token, sqlInjection);
    const elapsed = Date.now() - startTime;

    // Should not wait 5 seconds
    expect(elapsed).toBeLessThan(4000);
    expect(result.status).not.toBe(500);
  });
});

test.describe('Search - XSS Tests', () => {

  test('Basic XSS script tag (expect escaped, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const xssPayload = '<script>alert("XSS")</script>';
    const result = await searchRequest(token, xssPayload);

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);

    // If results returned, ensure XSS is not in response unescaped
    const responseText = JSON.stringify(result.data);
    expect(responseText).not.toContain('<script>alert');
  });

  test('IMG tag XSS (expect escaped, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const xssPayload = '<img src=x onerror=alert(1)>';
    const result = await searchRequest(token, xssPayload);

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('Event handler XSS (expect escaped, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const xssPayload = '" onmouseover="alert(1)"';
    const result = await searchRequest(token, xssPayload);

    expect(result.status).not.toBe(500);
  });

  test('SVG XSS (expect escaped, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const xssPayload = '<svg onload=alert(1)>';
    const result = await searchRequest(token, xssPayload);

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });
});

test.describe('Search - Unicode and Encoding Tests', () => {

  test('NULL byte injection (expect sanitized, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const payload = 'oil\u0000filter';
    const result = await searchRequest(token, payload);

    expect(result.status).not.toBe(500);
  });

  test('Unicode control characters (expect handled, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const payload = 'oil\u0001\u0002\u0003filter';
    const result = await searchRequest(token, payload);

    expect(result.status).not.toBe(500);
  });

  test('Unicode RTL override (expect handled, no 500)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const payload = 'oil\u202Efilter\u202C';
    const result = await searchRequest(token, payload);

    expect(result.status).not.toBe(500);
  });

  test('Unicode normalization test (expect handled)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    // Various representations of same character
    const payload = 'caf\u00e9 caf\u0065\u0301';
    const result = await searchRequest(token, payload);

    expect(result.status).not.toBe(500);
  });

  test('Emoji in query (expect handled)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const result = await searchRequest(token, 'oil filter 🛢️⚙️');

    expect(result.status).not.toBe(500);
  });
});

test.describe('Search - Request Format Tests', () => {

  test('Malformed JSON body (expect 400)', async () => {
    const token = extractToken(CREW_AUTH_STATE);

    const response = await fetch(`${API_BASE_URL}/webhook/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: '{invalid json'
    });

    expect([400, 422]).toContain(response.status);
    expect(response.status).not.toBe(500);
  });

  test('Wrong HTTP method GET (expect 405 or redirect)', async () => {
    const token = extractToken(CREW_AUTH_STATE);

    const response = await fetch(`${API_BASE_URL}/webhook/search?query=oil`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      }
    });

    expect([400, 405]).toContain(response.status);
  });

  test('Missing Content-Type header (expect handled)', async () => {
    const token = extractToken(CREW_AUTH_STATE);

    const response = await fetch(`${API_BASE_URL}/webhook/search`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: JSON.stringify({ query: 'oil filter', yacht_id: YACHT_ID })
    });

    // Should either accept or reject gracefully
    expect(response.status).not.toBe(500);
  });

  test('Very large request body (1MB) (expect 413 or handled)', async () => {
    const token = extractToken(CREW_AUTH_STATE);

    const largeBody = JSON.stringify({
      query: 'oil filter',
      yacht_id: YACHT_ID,
      extra: 'X'.repeat(1000000)
    });

    const response = await fetch(`${API_BASE_URL}/webhook/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: largeBody
    });

    // Should reject (413/400) or handle gracefully
    expect(response.status).not.toBe(500);
  });
});

test.describe('Search - Path Traversal and Injection', () => {

  test('Path traversal in query (expect sanitized)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const payload = '../../../etc/passwd';
    const result = await searchRequest(token, payload);

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('Command injection attempt (expect sanitized)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const payload = 'oil; cat /etc/passwd';
    const result = await searchRequest(token, payload);

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('LDAP injection attempt (expect sanitized)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const payload = '*)(uid=*))(|(uid=*';
    const result = await searchRequest(token, payload);

    expect(result.status).not.toBe(500);
  });

  test('XML injection attempt (expect sanitized)', async () => {
    const token = extractToken(CREW_AUTH_STATE);
    const payload = '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>';
    const result = await searchRequest(token, payload);

    expect(result.status).not.toBe(500);
  });
});

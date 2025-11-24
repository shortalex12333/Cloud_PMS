/**
 * CelesteOS Search API - Payload Validation Tests
 *
 * Tests the Option A (Minimal) payload contract
 */

import {
  validateAuthorizationHeader,
  validateYachtSignatureHeader,
  validateContentTypeHeader,
  validateHeaders,
  validateQuery,
  validateMode,
  validateFilters,
  validateSearchRequestBody,
  validateSearchRequest,
  checkForbiddenFields,
} from './validators';

// ============================================
// TEST UTILITIES
// ============================================

const VALID_JWT =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIiwieWFjaHRfaWQiOiI0NTYifQ.signature';
const VALID_SIGNATURE = 'a'.repeat(64); // Valid SHA256 (64 hex chars)
const VALID_UUID = '123e4567-e89b-12d3-a456-426614174000';

function validHeaders() {
  return {
    authorization: `Bearer ${VALID_JWT}`,
    'x-yacht-signature': VALID_SIGNATURE,
    'content-type': 'application/json' as const,
  };
}

function validBody() {
  return {
    query: 'main engine coolant leak',
  };
}

// ============================================
// HEADER VALIDATION TESTS
// ============================================

describe('validateAuthorizationHeader', () => {
  test('rejects missing header', () => {
    const error = validateAuthorizationHeader(undefined);
    expect(error).not.toBeNull();
    expect(error?.code).toBe('MISSING');
  });

  test('rejects header without Bearer prefix', () => {
    const error = validateAuthorizationHeader('token123');
    expect(error).not.toBeNull();
    expect(error?.code).toBe('INVALID');
  });

  test('rejects empty token after Bearer', () => {
    const error = validateAuthorizationHeader('Bearer ');
    expect(error).not.toBeNull();
    expect(error?.code).toBe('INVALID');
  });

  test('rejects invalid JWT structure', () => {
    const error = validateAuthorizationHeader('Bearer not.a.valid.jwt.token');
    expect(error).not.toBeNull();
    expect(error?.message).toContain('3 parts');
  });

  test('accepts valid JWT', () => {
    const error = validateAuthorizationHeader(`Bearer ${VALID_JWT}`);
    expect(error).toBeNull();
  });
});

describe('validateYachtSignatureHeader', () => {
  test('rejects missing header', () => {
    const error = validateYachtSignatureHeader(undefined);
    expect(error).not.toBeNull();
    expect(error?.code).toBe('MISSING');
  });

  test('rejects non-hex string', () => {
    const error = validateYachtSignatureHeader('not-a-valid-signature');
    expect(error).not.toBeNull();
    expect(error?.code).toBe('INVALID');
  });

  test('rejects wrong length', () => {
    const error = validateYachtSignatureHeader('abc123'); // Too short
    expect(error).not.toBeNull();
    expect(error?.message).toContain('64 hex');
  });

  test('accepts valid SHA256 hash', () => {
    const error = validateYachtSignatureHeader(VALID_SIGNATURE);
    expect(error).toBeNull();
  });

  test('accepts uppercase hex', () => {
    const error = validateYachtSignatureHeader('A'.repeat(64));
    expect(error).toBeNull();
  });
});

describe('validateContentTypeHeader', () => {
  test('rejects missing header', () => {
    const error = validateContentTypeHeader(undefined);
    expect(error).not.toBeNull();
    expect(error?.code).toBe('MISSING');
  });

  test('rejects non-JSON content type', () => {
    const error = validateContentTypeHeader('text/plain');
    expect(error).not.toBeNull();
    expect(error?.code).toBe('INVALID');
  });

  test('accepts application/json', () => {
    const error = validateContentTypeHeader('application/json');
    expect(error).toBeNull();
  });

  test('accepts application/json with charset', () => {
    const error = validateContentTypeHeader('application/json; charset=utf-8');
    expect(error).toBeNull();
  });
});

describe('validateHeaders', () => {
  test('returns valid for complete headers', () => {
    const result = validateHeaders(validHeaders());
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  test('returns all errors for empty headers', () => {
    const result = validateHeaders({});
    expect(result.valid).toBe(false);
    expect(result.errors.length).toBe(3); // All 3 headers missing
  });

  test('collects multiple errors', () => {
    const result = validateHeaders({
      authorization: 'invalid',
      'x-yacht-signature': 'bad',
    });
    expect(result.valid).toBe(false);
    expect(result.errors.length).toBeGreaterThan(1);
  });
});

// ============================================
// BODY VALIDATION TESTS
// ============================================

describe('checkForbiddenFields', () => {
  test('detects user_id in body', () => {
    const errors = checkForbiddenFields({ user_id: '123', query: 'test' });
    expect(errors.length).toBe(1);
    expect(errors[0].field).toBe('user_id');
    expect(errors[0].code).toBe('FORBIDDEN');
  });

  test('detects yacht_id in body', () => {
    const errors = checkForbiddenFields({ yacht_id: '456', query: 'test' });
    expect(errors.length).toBe(1);
    expect(errors[0].field).toBe('yacht_id');
    expect(errors[0].code).toBe('FORBIDDEN');
  });

  test('detects jwt/token in body', () => {
    const errors = checkForbiddenFields({ jwt: 'token123', query: 'test' });
    expect(errors.length).toBe(1);
    expect(errors[0].field).toBe('jwt');
  });

  test('detects NEXT_PUBLIC_ env vars', () => {
    const errors = checkForbiddenFields({
      NEXT_PUBLIC_SUPABASE_URL: 'https://...',
      query: 'test',
    });
    expect(errors.length).toBe(1);
    expect(errors[0].code).toBe('SECURITY_VIOLATION');
  });

  test('detects multiple forbidden fields', () => {
    const errors = checkForbiddenFields({
      user_id: '123',
      yacht_id: '456',
      NEXT_PUBLIC_API_KEY: 'secret',
      query: 'test',
    });
    expect(errors.length).toBe(3);
  });

  test('passes clean body', () => {
    const errors = checkForbiddenFields({ query: 'main engine fault' });
    expect(errors).toHaveLength(0);
  });
});

describe('validateQuery', () => {
  test('rejects missing query', () => {
    const error = validateQuery(undefined);
    expect(error).not.toBeNull();
    expect(error?.code).toBe('MISSING');
  });

  test('rejects null query', () => {
    const error = validateQuery(null);
    expect(error).not.toBeNull();
    expect(error?.code).toBe('MISSING');
  });

  test('rejects non-string query', () => {
    const error = validateQuery(123);
    expect(error).not.toBeNull();
    expect(error?.code).toBe('INVALID');
  });

  test('rejects empty string', () => {
    const error = validateQuery('');
    expect(error).not.toBeNull();
    expect(error?.code).toBe('INVALID');
  });

  test('rejects whitespace-only string', () => {
    const error = validateQuery('   ');
    expect(error).not.toBeNull();
    expect(error?.code).toBe('INVALID');
  });

  test('rejects query over 2000 chars', () => {
    const error = validateQuery('a'.repeat(2001));
    expect(error).not.toBeNull();
    expect(error?.message).toContain('2000');
  });

  test('accepts valid query', () => {
    const error = validateQuery('fault code E047 on main engine');
    expect(error).toBeNull();
  });
});

describe('validateMode', () => {
  test('accepts undefined (optional)', () => {
    const error = validateMode(undefined);
    expect(error).toBeNull();
  });

  test('accepts "auto"', () => {
    const error = validateMode('auto');
    expect(error).toBeNull();
  });

  test('accepts "standard"', () => {
    const error = validateMode('standard');
    expect(error).toBeNull();
  });

  test('accepts "deep"', () => {
    const error = validateMode('deep');
    expect(error).toBeNull();
  });

  test('rejects invalid mode', () => {
    const error = validateMode('turbo');
    expect(error).not.toBeNull();
    expect(error?.message).toContain('auto');
  });

  test('rejects non-string', () => {
    const error = validateMode(123);
    expect(error).not.toBeNull();
    expect(error?.code).toBe('INVALID');
  });
});

describe('validateFilters', () => {
  test('accepts undefined (optional)', () => {
    const errors = validateFilters(undefined);
    expect(errors).toHaveLength(0);
  });

  test('rejects non-object filters', () => {
    const errors = validateFilters('string');
    expect(errors.length).toBe(1);
    expect(errors[0].code).toBe('INVALID');
  });

  test('accepts empty filters object', () => {
    const errors = validateFilters({});
    expect(errors).toHaveLength(0);
  });

  test('accepts valid equipment_id UUID', () => {
    const errors = validateFilters({ equipment_id: VALID_UUID });
    expect(errors).toHaveLength(0);
  });

  test('rejects invalid equipment_id', () => {
    const errors = validateFilters({ equipment_id: 'not-a-uuid' });
    expect(errors.length).toBe(1);
    expect(errors[0].field).toBe('filters.equipment_id');
  });

  test('accepts valid document_type', () => {
    const errors = validateFilters({ document_type: 'manual' });
    expect(errors).toHaveLength(0);
  });

  test('rejects invalid document_type', () => {
    const errors = validateFilters({ document_type: 'unknown' });
    expect(errors.length).toBe(1);
    expect(errors[0].field).toBe('filters.document_type');
  });
});

describe('validateSearchRequestBody', () => {
  test('accepts minimal valid body', () => {
    const result = validateSearchRequestBody(validBody());
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  test('accepts body with all optional fields', () => {
    const result = validateSearchRequestBody({
      query: 'main engine fault',
      mode: 'deep',
      filters: {
        equipment_id: VALID_UUID,
        document_type: 'manual',
      },
    });
    expect(result.valid).toBe(true);
  });

  test('rejects non-object body', () => {
    const result = validateSearchRequestBody('string');
    expect(result.valid).toBe(false);
  });

  test('rejects body with forbidden fields', () => {
    const result = validateSearchRequestBody({
      query: 'test',
      user_id: '123', // FORBIDDEN
    });
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.field === 'user_id')).toBe(true);
  });

  test('rejects body with env vars', () => {
    const result = validateSearchRequestBody({
      query: 'test',
      NEXT_PUBLIC_SUPABASE_URL: 'https://example.com', // SECURITY VIOLATION
    });
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.code === 'SECURITY_VIOLATION')).toBe(true);
  });

  test('collects all errors', () => {
    const result = validateSearchRequestBody({
      // Missing query
      user_id: '123', // Forbidden
      mode: 'invalid', // Invalid
    });
    expect(result.valid).toBe(false);
    expect(result.errors.length).toBeGreaterThanOrEqual(3);
  });
});

// ============================================
// FULL REQUEST VALIDATION TESTS
// ============================================

describe('validateSearchRequest', () => {
  test('accepts valid complete request', () => {
    const result = validateSearchRequest(validHeaders(), validBody());
    expect(result.valid).toBe(true);
    expect(result.headerErrors).toHaveLength(0);
    expect(result.bodyErrors).toHaveLength(0);
  });

  test('separates header and body errors', () => {
    const result = validateSearchRequest(
      {}, // Missing all headers
      { user_id: '123' } // Missing query, has forbidden field
    );
    expect(result.valid).toBe(false);
    expect(result.headerErrors.length).toBe(3); // 3 missing headers
    expect(result.bodyErrors.length).toBe(2); // forbidden field + missing query
  });

  test('real-world attack payload is rejected', () => {
    // Simulating what user originally sent
    const result = validateSearchRequest(
      {
        // Missing Authorization header (JWT was in body)
        // Missing X-Yacht-Signature
        'content-type': 'application/json',
      },
      {
        NEXT_PUBLIC_SUPABASE_URL: 'https://vzsohavtuotocgrfkfyd.supabase.co',
        jwt: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        // Missing query
      }
    );

    expect(result.valid).toBe(false);

    // Should catch: missing auth header, missing signature, forbidden jwt field,
    // forbidden env var, missing query
    expect(result.errors.length).toBeGreaterThanOrEqual(4);
  });
});

// ============================================
// EDGE CASES
// ============================================

describe('edge cases', () => {
  test('handles unicode in query', () => {
    const result = validateSearchRequestBody({
      query: '主引擎冷却液泄漏', // Chinese characters
    });
    expect(result.valid).toBe(true);
  });

  test('handles special characters in query', () => {
    const result = validateSearchRequestBody({
      query: 'fault code "E047" & <main> engine',
    });
    expect(result.valid).toBe(true);
  });

  test('handles mixed case header values', () => {
    // Mixed case hex should be accepted (64 chars)
    const mixedCaseSig = 'AbCdEf1234567890'.repeat(4); // 64 chars
    const error1 = validateYachtSignatureHeader(mixedCaseSig);
    expect(error1).toBeNull();

    // Lowercase hex should also work
    const lowerSig = 'abcdef1234567890'.repeat(4); // 64 chars
    const error2 = validateYachtSignatureHeader(lowerSig);
    expect(error2).toBeNull();
  });
});

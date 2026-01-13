/**
 * Tenant Resolution Helper
 *
 * Maps yacht_id to tenant configuration
 */

export interface TenantConfig {
  yachtId: string;
  tenantKeyAlias: string;
  supabaseUrl: string;
  supabaseServiceKey: string;
}

/**
 * Resolve tenant configuration from yacht_id
 *
 * In production, this would query the fleet_registry
 * For tests, we use environment variables
 */
export function resolveTenant(yachtId: string): TenantConfig {
  // For test purposes, we use the configured tenant
  const expectedYachtId = process.env.TEST_USER_YACHT_ID;

  if (yachtId !== expectedYachtId) {
    throw new Error(
      `Test tenant resolution only supports ${expectedYachtId}, got ${yachtId}`
    );
  }

  const tenantKeyAlias = process.env.TEST_USER_TENANT_KEY;
  const supabaseUrl = process.env.TENANT_SUPABASE_URL;
  const supabaseServiceKey = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;

  if (!tenantKeyAlias || !supabaseUrl || !supabaseServiceKey) {
    throw new Error(
      'TEST_USER_TENANT_KEY, TENANT_SUPABASE_URL, and TENANT_SUPABASE_SERVICE_ROLE_KEY must be set'
    );
  }

  return {
    yachtId,
    tenantKeyAlias,
    supabaseUrl,
    supabaseServiceKey,
  };
}

/**
 * Get tenant key alias from yacht_id
 */
export function getTenantKeyAlias(yachtId: string): string {
  // Standard format: y<yacht_id>
  return `y${yachtId}`;
}

/**
 * Validate tenant key alias format
 */
export function isValidTenantKeyAlias(alias: string): boolean {
  // Must start with 'y' followed by alphanumeric and underscores
  return /^y[A-Za-z0-9_]+$/.test(alias);
}

/**
 * Extract yacht_id from tenant key alias
 */
export function yachtIdFromTenantKey(alias: string): string {
  if (!isValidTenantKeyAlias(alias)) {
    throw new Error(`Invalid tenant key alias format: ${alias}`);
  }
  return alias.substring(1);
}

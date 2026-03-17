// apps/web/e2e/shard-34-lens-actions/certificate-actions-full.spec.ts

/**
 * SHARD 34: Full Action Coverage — Certificates + Signed Actions
 *
 * HARD PROOF tests for:
 *   create_vessel_certificate — required fields: certificate_type, certificate_name, issuing_authority
 *                               writes to pms_vessel_certificates
 *                               (get_table("vessel_certificates") in certificate_handlers.py)
 *   update_certificate        — required fields: certificate_id
 *                               updates pms_vessel_certificates fields
 *                               updatable fields: certificate_name, certificate_number,
 *                               issuing_authority, issue_date, expiry_date, properties,
 *                               last_survey_date, next_survey_due (NOT notes)
 *
 * ADVISORY tests for:
 *   supersede_certificate (SIGNED) — requires signature payload → advisory smoke test
 *
 * Each test verifies:
 *   1. Full JSON response body (status, message fields)
 *   2. Entity state mutation confirmed (pms_vessel_certificates row created/updated)
 *      (Certificates are NOT in _ACTION_ENTITY_MAP; no ledger poll.)
 *
 * AUTH STRATEGY: callActionDirect() uses a Node.js-minted JWT (same signing key as API)
 * to bypass browser localStorage invalidation by the Supabase client.
 *
 * IMPLEMENTATION NOTES:
 *   create_vessel_certificate returns: { status: 'success', certificate_id: ..., ... }
 *   update_certificate returns: { status: 'success', ... }
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { BASE_URL, callActionDirect } from './helpers';

// ===========================================================================
// create_vessel_certificate
// ===========================================================================

test.describe('[Captain] create_vessel_certificate — HARD PROOF', () => {
  test('[Captain] create_vessel_certificate → 200 + pms_vessel_certificates row created', async ({
    captainPage,
    supabaseAdmin,
  }) => {
    const certName = `S34 Smoke Cert ${generateTestId('cert')}`;
    const issueDate = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
    const expiryDate = new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0];

    await captainPage.goto(`${BASE_URL}/certificates`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'create_vessel_certificate', {
      certificate_type: 'safety',
      certificate_name: certName,
      issuing_authority: 'S34 Test Authority',
      issue_date: issueDate,
      expiry_date: expiryDate,
      certificate_number: `S34-${generateTestId('cn')}`,
    });
    console.log(`[JSON] create_vessel_certificate response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; certificate_id?: string };
    expect(data.status).toBe('success');
    expect(typeof data.certificate_id).toBe('string');
    expect(data.certificate_id).toBeTruthy();

    const certId = data.certificate_id as string;

    // Entity state: pms_vessel_certificates row was created
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_vessel_certificates')
          .select('id, certificate_name')
          .eq('id', certId)
          .single();
        return (row as { id?: string } | null)?.id;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected pms_vessel_certificates row to exist' }
    ).toBe(certId);
  });
});

test.describe('[HOD] create_vessel_certificate — HARD PROOF', () => {
  test('[HOD] create_vessel_certificate → 200 + pms_vessel_certificates row created', async ({
    hodPage,
    supabaseAdmin,
  }) => {
    // HOD users map to captain JWT — should have captain role → allowed
    const certName = `S34 HOD Cert ${generateTestId('cert')}`;

    await hodPage.goto(`${BASE_URL}/certificates`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'create_vessel_certificate', {
      certificate_type: 'class',
      certificate_name: certName,
      issuing_authority: 'S34 HOD Test Authority',
    });
    console.log(`[JSON] [HOD] create_vessel_certificate response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; certificate_id?: string };
    expect(data.status).toBe('success');
    expect(typeof data.certificate_id).toBe('string');

    const certId = data.certificate_id as string;
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_vessel_certificates')
          .select('id')
          .eq('id', certId)
          .single();
        return (row as { id?: string } | null)?.id;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBe(certId);
  });
});

// ===========================================================================
// update_certificate
// ===========================================================================

test.describe('[Captain] update_certificate — HARD PROOF', () => {
  test('[Captain] update_certificate → 200 + pms_vessel_certificates issuing_authority updated', async ({
    captainPage,
    getExistingVesselCertificate,
    supabaseAdmin,
  }) => {
    const cert = await getExistingVesselCertificate();

    // Use issuing_authority — a valid updatable field in update_certificate handler
    const newAuthority = `S34 Updated Authority ${generateTestId('a')}`;

    await captainPage.goto(`${BASE_URL}/certificates`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'update_certificate', {
      certificate_id: cert.id,
      issuing_authority: newAuthority,
    });
    console.log(`[JSON] update_certificate response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string };
    expect(data.status).toBe('success');

    // Entity state: issuing_authority field updated in pms_vessel_certificates
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_vessel_certificates')
          .select('issuing_authority')
          .eq('id', cert.id)
          .single();
        return (row as { issuing_authority?: string } | null)?.issuing_authority;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected pms_vessel_certificates.issuing_authority to be updated' }
    ).toBe(newAuthority);
  });
});

// ===========================================================================
// supersede_certificate (SIGNED) — ADVISORY SMOKE TEST
// ===========================================================================

test.describe('[Captain] supersede_certificate (SIGNED) — ADVISORY', () => {
  test('[Captain] supersede_certificate → 400 SIGNED (no signature) ADVISORY', async ({
    captainPage,
    getExistingVesselCertificate,
  }) => {
    const cert = await getExistingVesselCertificate();

    await captainPage.goto(`${BASE_URL}/certificates`);
    await captainPage.waitForLoadState('domcontentloaded');

    // Without signature → expect 400 (signature_required)
    const result = await callActionDirect(captainPage, 'supersede_certificate', {
      certificate_id: cert.id,
      reason: 'S34 signed action smoke test (no signature)',
    });
    console.log(`[JSON] supersede_certificate (no sig) response: ${JSON.stringify(result, null, 2)}`);

    // Expected: 400 (signature required) or 403 (not authorized)
    // Advisory: any definitive status code is acceptable
    if (result.status === 400) {
      console.log('supersede_certificate correctly returned 400 (signature required)');
    } else if (result.status === 403) {
      console.log('supersede_certificate returned 403 (RBAC enforced)');
    } else {
      console.warn(`Advisory: supersede_certificate returned unexpected status ${result.status}`);
    }
    // 200 means the signature gate returned success without a signature — that's a security bug, not advisory.
    expect([400, 403]).toContain(result.status);
  });
});

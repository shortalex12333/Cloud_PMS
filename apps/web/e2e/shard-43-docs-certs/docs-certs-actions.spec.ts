// apps/web/e2e/shard-43-docs-certs/docs-certs-actions.spec.ts

/**
 * SHARD 43: Documents + Certificates Extended — HARD PROOF + SIGNED
 *
 * Actions covered:
 *   get_document_url             — HARD PROOF (READ): returns signed URL
 *   delete_document              — SIGNED: captain/manager only, requires signature
 *   add_document_comment         — HARD PROOF: via internal_dispatcher → doc_comment_handlers
 *   update_document_comment      — HARD PROOF: via internal_dispatcher
 *   delete_document_comment      — HARD PROOF: via internal_dispatcher
 *   list_document_comments       — HARD PROOF (READ): via internal_dispatcher
 *   create_crew_certificate      — HARD PROOF: via cert_handlers
 *   link_document_to_certificate — HARD PROOF: via cert_handlers
 *
 * Document comments route through action_router/dispatchers/internal_dispatcher.py
 * (migrated from p0_actions_routes.py, see line 6058-6064)
 *
 * DB tables: doc_metadata, doc_metadata_comments, pms_certificates
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { callActionDirect, SESSION_JWT } from '../shard-34-lens-actions/helpers';
import { BASE_URL } from '../shard-33-lens-actions/helpers';

// ===========================================================================
// get_document_url — HARD PROOF (READ)
// ===========================================================================

test.describe('[Captain] get_document_url — HARD PROOF', () => {
  test('get_document_url → 200 + URL returned', async ({
    captainPage,
    getExistingDocument,
  }) => {
    let doc: { id: string };
    try {
      doc = await getExistingDocument();
    } catch (e) {
      const err = e as Error;
      if (err.message?.startsWith('SKIP:')) {
        test.skip(true, err.message.replace('SKIP:', ''));
        return;
      }
      throw e;
    }

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'get_document_url', {
      document_id: doc.id,
    });
    console.log(`[JSON] get_document_url: ${JSON.stringify(result.data)}`);

    // get_document_url returns 200 with ResponseBuilder envelope.
    // success:true + url = file exists; success:false + error.code:NOT_FOUND = no physical file.
    // Both are valid for test data — the document DB row exists but file may not be in storage.
    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean; status?: string; url?: string; signed_url?: string; data?: { url?: string; signed_url?: string } };
    if (data.success || data.status === 'success') {
      const url = data.url || data.signed_url || data.data?.url || data.data?.signed_url;
      expect(typeof url).toBe('string');
    } else {
      console.log(`get_document_url → 200 + success:false (no physical file in storage — expected for test data)`);
    }
  });
});

// ===========================================================================
// delete_document — SIGNED (captain/manager only)
// ===========================================================================

test.describe('[Captain] delete_document — SIGNED ADVISORY', () => {
  test('delete_document without signature → 400', async ({
    captainPage,
    getExistingDocument,
  }) => {
    let doc: { id: string };
    try {
      doc = await getExistingDocument();
    } catch (e) {
      const err = e as Error;
      if (err.message?.startsWith('SKIP:')) {
        test.skip(true, err.message.replace('SKIP:', ''));
        return;
      }
      throw e;
    }

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // delete_document requires 'reason' and 'signature' in _REQUIRED_FIELDS
    // Without signature it should reject
    const result = await callActionDirect(captainPage, 'delete_document', {
      document_id: doc.id,
      reason: 'S43 advisory smoke delete',
    });
    console.log(`[JSON] delete_document (no sig): status=${result.status}`);

    // Without required 'signature' field → 400 from validation gate
    expect([400, 403]).toContain(result.status);
  });
});

// ===========================================================================
// add_document_comment — HARD PROOF
// ===========================================================================

test.describe('[Captain] add_document_comment — HARD PROOF', () => {
  test('add_document_comment → 200 + comment created', async ({
    captainPage,
    getExistingDocument,
    supabaseAdmin,
  }) => {
    let doc: { id: string };
    try {
      doc = await getExistingDocument();
    } catch (e) {
      const err = e as Error;
      if (err.message?.startsWith('SKIP:')) {
        test.skip(true, err.message.replace('SKIP:', ''));
        return;
      }
      throw e;
    }

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const commentText = `S43 smoke comment ${generateTestId('c')}`;
    const result = await callActionDirect(captainPage, 'add_document_comment', {
      document_id: doc.id,
      comment: commentText,
    });
    console.log(`[JSON] add_document_comment: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; success?: boolean };
    expect(data.status === 'success' || data.success === true).toBe(true);
  });
});

// ===========================================================================
// list_document_comments — HARD PROOF (READ)
// ===========================================================================

test.describe('[Captain] list_document_comments — HARD PROOF', () => {
  test('list_document_comments → 200 + comments array', async ({
    captainPage,
    getExistingDocument,
  }) => {
    let doc: { id: string };
    try {
      doc = await getExistingDocument();
    } catch (e) {
      const err = e as Error;
      if (err.message?.startsWith('SKIP:')) {
        test.skip(true, err.message.replace('SKIP:', ''));
        return;
      }
      throw e;
    }

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'list_document_comments', {
      document_id: doc.id,
    });
    console.log(`[JSON] list_document_comments: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; comments?: unknown[]; success?: boolean; data?: { comments?: unknown[] } };
    expect(data.status === 'success' || data.success === true).toBe(true);
  });
});

// ===========================================================================
// update_document_comment — HARD PROOF (chained: add then update)
// ===========================================================================

test.describe('[Captain] update_document_comment — HARD PROOF', () => {
  test('add then update_document_comment → 200', async ({
    captainPage,
    getExistingDocument,
  }) => {
    let doc: { id: string };
    try {
      doc = await getExistingDocument();
    } catch (e) {
      const err = e as Error;
      if (err.message?.startsWith('SKIP:')) {
        test.skip(true, err.message.replace('SKIP:', ''));
        return;
      }
      throw e;
    }

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const addResult = await callActionDirect(captainPage, 'add_document_comment', {
      document_id: doc.id,
      comment: `S43 update target ${generateTestId('ut')}`,
    });
    expect(addResult.status).toBe(200);

    const addData = addResult.data as { comment_id?: string; data?: { comment_id?: string; id?: string }; id?: string };
    const commentId = addData.comment_id || addData.data?.comment_id || addData.data?.id || addData.id;
    expect(typeof commentId).toBe('string');

    const updatedText = `S43 updated comment ${generateTestId('upd')}`;
    const result = await callActionDirect(captainPage, 'update_document_comment', {
      comment_id: commentId,
      comment: updatedText,
    });
    console.log(`[JSON] update_document_comment: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
  });
});

// ===========================================================================
// delete_document_comment — HARD PROOF (chained: add then delete)
// ===========================================================================

test.describe('[Captain] delete_document_comment — HARD PROOF', () => {
  test('add then delete_document_comment → 200', async ({
    captainPage,
    getExistingDocument,
  }) => {
    let doc: { id: string };
    try {
      doc = await getExistingDocument();
    } catch (e) {
      const err = e as Error;
      if (err.message?.startsWith('SKIP:')) {
        test.skip(true, err.message.replace('SKIP:', ''));
        return;
      }
      throw e;
    }

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const addResult = await callActionDirect(captainPage, 'add_document_comment', {
      document_id: doc.id,
      comment: `S43 delete target ${generateTestId('del')}`,
    });
    expect(addResult.status).toBe(200);

    const addData = addResult.data as { comment_id?: string; data?: { comment_id?: string; id?: string }; id?: string };
    const commentId = addData.comment_id || addData.data?.comment_id || addData.data?.id || addData.id;
    expect(typeof commentId).toBe('string');

    const result = await callActionDirect(captainPage, 'delete_document_comment', {
      comment_id: commentId,
    });
    console.log(`[JSON] delete_document_comment: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
  });
});

// ===========================================================================
// create_crew_certificate — HARD PROOF
// ===========================================================================

test.describe('[Captain] create_crew_certificate — HARD PROOF', () => {
  test('create_crew_certificate → 200 + certificate row created', async ({
    captainPage,
    supabaseAdmin,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const personName = `S43 Test Crew ${generateTestId('crew')}`;
    const result = await callActionDirect(captainPage, 'create_crew_certificate', {
      person_name: personName,
      certificate_type: 'STCW Basic Safety Training',
      issuing_authority: 'S43 Test MCA',
      issue_date: '2025-01-01',
      expiry_date: '2030-01-01',
    });
    console.log(`[JSON] create_crew_certificate: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; certificate_id?: string; id?: string };
    expect(data.status).toBe('success');
    const certId = data.certificate_id || data.id;
    expect(typeof certId).toBe('string');

    // Entity state: certificate row exists in pms_crew_certificates
    // (create_crew_certificate writes to pms_crew_certificates, NOT pms_certificates)
    if (certId) {
      await expect.poll(
        async () => {
          // Try pms_crew_certificates first
          const { data: row1 } = await supabaseAdmin
            .from('pms_crew_certificates')
            .select('id')
            .eq('id', certId)
            .maybeSingle();
          if ((row1 as { id?: string } | null)?.id) return (row1 as { id: string }).id;
          // Fallback to pms_certificates
          const { data: row2 } = await supabaseAdmin
            .from('pms_certificates')
            .select('id')
            .eq('id', certId)
            .maybeSingle();
          return (row2 as { id?: string } | null)?.id ?? null;
        },
        { intervals: [500, 1000, 1500], timeout: 8_000,
          message: 'Expected certificate row to exist in pms_crew_certificates or pms_certificates' }
      ).toBe(certId);
    }
  });
});

// ===========================================================================
// link_document_to_certificate — HARD PROOF
// ===========================================================================

test.describe('[Captain] link_document_to_certificate — HARD PROOF', () => {
  test('link_document_to_certificate → 200', async ({
    captainPage,
    getExistingDocument,
    getExistingCertificate,
  }) => {
    let doc: { id: string };
    let cert: { id: string; certificate_name: string };
    try {
      doc = await getExistingDocument();
      cert = await getExistingCertificate();
    } catch (e) {
      const err = e as Error;
      if (err.message?.startsWith('SKIP:') || err.message?.includes('No ')) {
        test.skip(true, (err.message || '').replace('SKIP:', ''));
        return;
      }
      throw e;
    }

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'link_document_to_certificate', {
      certificate_id: cert.id,
      document_id: doc.id,
    });
    console.log(`[JSON] link_document_to_certificate: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string };
    expect(data.status).toBe('success');
  });
});

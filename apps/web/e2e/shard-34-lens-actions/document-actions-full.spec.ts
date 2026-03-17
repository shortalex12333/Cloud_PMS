// apps/web/e2e/shard-34-lens-actions/document-actions-full.spec.ts

/**
 * SHARD 34: Full Action Coverage — Documents
 *
 * HARD PROOF tests for:
 *   upload_document  — required fields: file_name, mime_type
 *                      inserts doc_metadata record (no physical file needed)
 *                      centralized ledger write (action not in _ACTION_ENTITY_MAP → fallback entity_id)
 *   update_document  — required fields: document_id
 *                      updates doc_metadata fields
 *   add_document_tags — required fields: document_id, tags (array)
 *
 * Each test verifies:
 *   1. Full JSON response body (status, message fields)
 *   2. Entity state mutation confirmed (doc_metadata row created/updated)
 *
 * NOTE: upload_document/update_document/add_document_tags are NOT in _ACTION_ENTITY_MAP.
 * The centralized ledger write fires but entity_id is the fallback "00000000-...-000".
 * We verify entity state only (no ledger poll needed here).
 *
 * AUTH STRATEGY: callActionDirect() uses a Node.js-minted JWT (same signing key as API)
 * to bypass browser localStorage invalidation by the Supabase client.
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { BASE_URL, callActionDirect } from './helpers';

// ===========================================================================
// upload_document
// ===========================================================================

test.describe('[HOD] upload_document — HARD PROOF', () => {
  test('[HOD] upload_document → 200 + doc_metadata row created', async ({
    hodPage,
    supabaseAdmin,
  }) => {
    const fileName = `s34-hod-smoke-${generateTestId('doc')}.pdf`;

    await hodPage.goto(`${BASE_URL}/documents`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'upload_document', {
      file_name: fileName,
      mime_type: 'application/pdf',
      title: `S34 HOD Upload ${generateTestId('t')}`,
    });
    console.log(`[JSON] upload_document response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; document_id?: string; filename?: string };
    expect(data.status).toBe('success');
    expect(typeof data.document_id).toBe('string');
    expect(data.document_id).toBeTruthy();

    // Entity state: doc_metadata row was created
    const docId = data.document_id as string;
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('doc_metadata')
          .select('id')
          .eq('id', docId)
          .single();
        return (row as { id?: string } | null)?.id;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected doc_metadata row to exist' }
    ).toBe(docId);
  });
});

test.describe('[Captain] upload_document — HARD PROOF', () => {
  test('[Captain] upload_document → 200 + doc_metadata row created', async ({
    captainPage,
    supabaseAdmin,
  }) => {
    const fileName = `s34-captain-smoke-${generateTestId('doc')}.pdf`;

    await captainPage.goto(`${BASE_URL}/documents`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'upload_document', {
      file_name: fileName,
      mime_type: 'application/pdf',
      title: `S34 Captain Upload ${generateTestId('t')}`,
    });
    console.log(`[JSON] [Captain] upload_document response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; document_id?: string };
    expect(data.status).toBe('success');
    expect(typeof data.document_id).toBe('string');

    const docId = data.document_id as string;
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('doc_metadata')
          .select('id')
          .eq('id', docId)
          .single();
        return (row as { id?: string } | null)?.id;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBe(docId);
  });
});

// ===========================================================================
// update_document
// ===========================================================================

test.describe('[HOD] update_document — HARD PROOF', () => {
  test('[HOD] update_document → 200 + doc_metadata doc_type updated', async ({
    hodPage,
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

    await hodPage.goto(`${BASE_URL}/documents`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'update_document', {
      document_id: doc.id,
      doc_type: 'report',
      oem: 'S34-smoke-oem',
    });
    console.log(`[JSON] update_document response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; updated_fields?: string[] };
    expect(data.status).toBe('success');
    expect(Array.isArray(data.updated_fields)).toBe(true);
    console.log(`✅ update_document: status=success, updated_fields=${JSON.stringify(data.updated_fields)}`);

    // Entity state: doc_metadata.doc_type was updated (handler now writes for real)
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('doc_metadata')
          .select('doc_type')
          .eq('id', doc.id)
          .single();
        return (row as { doc_type?: string } | null)?.doc_type;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected doc_metadata.doc_type=report' }
    ).toBe('report');
  });
});

// ===========================================================================
// add_document_tags
// ===========================================================================

test.describe('[HOD] add_document_tags — HARD PROOF', () => {
  test('[HOD] add_document_tags → 200 + tags applied to doc_metadata', async ({
    hodPage,
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

    const tags = [`s34-smoke-${generateTestId('tag')}`, 'e2e-test'];

    await hodPage.goto(`${BASE_URL}/documents`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'add_document_tags', {
      document_id: doc.id,
      tags,
    });
    console.log(`[JSON] add_document_tags response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string };
    expect(data.status).toBe('success');

    // Entity state: tags were applied
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('doc_metadata')
          .select('tags')
          .eq('id', doc.id)
          .single();
        const rowTags = (row as { tags?: string[] } | null)?.tags ?? [];
        return rowTags.some(t => t.startsWith('s34-smoke-'));
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected doc_metadata.tags to contain s34 smoke tag' }
    ).toBe(true);
  });
});

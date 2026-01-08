/**
 * Storage Diagnostic API
 * Check what buckets/files exist vs what's in doc_metadata
 */

import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export async function GET() {
  try {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

    if (!supabaseUrl || !serviceRoleKey) {
      return NextResponse.json({
        error: 'Missing Supabase credentials in environment variables',
      }, { status: 500 });
    }

    // Create service role client (bypasses RLS)
    const supabase = createClient(supabaseUrl, serviceRoleKey);

    const results: any = {
      timestamp: new Date().toISOString(),
      buckets: [],
      sample_doc_metadata: [],
      storage_check: [],
    };

    // STEP 1: List all storage buckets
    const { data: buckets, error: bucketsError } = await supabase.storage.listBuckets();

    if (bucketsError) {
      results.buckets_error = bucketsError.message;
    } else {
      results.buckets = buckets.map(b => ({
        name: b.name,
        public: b.public,
        created_at: b.created_at,
      }));
    }

    // STEP 2: Get sample storage_paths from doc_metadata
    const { data: docs, error: docsError } = await supabase
      .from('doc_metadata')
      .select('id, storage_path')
      .limit(5);

    if (docsError) {
      results.doc_metadata_error = docsError.message;
    } else {
      results.sample_doc_metadata = docs;

      // STEP 3: For each doc, check if file actually exists in storage
      for (const doc of docs || []) {
        const storagePath = doc.storage_path;

        // Strip "documents/" prefix if present
        let pathToCheck = storagePath;
        if (pathToCheck.startsWith('documents/')) {
          pathToCheck = pathToCheck.substring('documents/'.length);
        }

        // Try to get file info
        const { data: fileList, error: listError } = await supabase.storage
          .from('documents')
          .list(pathToCheck.substring(0, pathToCheck.lastIndexOf('/')), {
            search: pathToCheck.split('/').pop(),
          });

        results.storage_check.push({
          doc_id: doc.id,
          storage_path: storagePath,
          path_checked: pathToCheck,
          exists: !listError && fileList && fileList.length > 0,
          error: listError?.message || null,
          files_found: fileList?.length || 0,
        });
      }
    }

    // STEP 4: If documents bucket exists, list some files
    if (results.buckets.some((b: any) => b.name === 'documents')) {
      const { data: files, error: filesError } = await supabase.storage
        .from('documents')
        .list('', {
          limit: 10,
        });

      if (filesError) {
        results.documents_bucket_error = filesError.message;
      } else {
        results.documents_bucket_root_files = files?.map(f => ({
          name: f.name,
          id: f.id || 'folder',
        }));
      }
    }

    return NextResponse.json(results, { status: 200 });
  } catch (error: any) {
    return NextResponse.json({
      error: 'Unexpected error',
      message: error.message,
      stack: error.stack,
    }, { status: 500 });
  }
}

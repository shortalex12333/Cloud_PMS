'use client';

import { useEffect, useState } from 'react';

/**
 * Storage Diagnostic Page
 * Shows what buckets/files exist vs what's in doc_metadata
 */
export default function StorageDiagnosticPage() {
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/debug/storage')
      .then(res => res.json())
      .then(data => {
        setResults(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold mb-4">Storage Diagnostic</h1>
        <p>Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold mb-4 text-red-600">Error</h1>
        <pre className="bg-red-50 p-4 rounded">{error}</pre>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Storage Diagnostic Report</h1>
      <p className="text-gray-600 mb-8">
        Generated: {results?.timestamp}
      </p>

      {/* Storage Buckets */}
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">📦 Storage Buckets</h2>
        {results?.buckets_error ? (
          <div className="bg-red-50 border border-red-200 p-4 rounded">
            <p className="text-red-800">Error: {results.buckets_error}</p>
          </div>
        ) : (
          <div className="bg-white border rounded overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left">Bucket Name</th>
                  <th className="px-4 py-2 text-left">Public</th>
                  <th className="px-4 py-2 text-left">Created</th>
                </tr>
              </thead>
              <tbody>
                {results?.buckets?.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-4 text-center text-red-600">
                      ❌ No storage buckets found!
                    </td>
                  </tr>
                ) : (
                  results?.buckets?.map((bucket: any) => (
                    <tr key={bucket.name} className="border-t">
                      <td className="px-4 py-2 font-mono">{bucket.name}</td>
                      <td className="px-4 py-2">{bucket.public ? '✅ Yes' : '❌ No'}</td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {new Date(bucket.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Documents Bucket Root Files */}
      {results?.documents_bucket_root_files && (
        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">
            📁 Files in &quot;documents&quot; Bucket (Root Level)
          </h2>
          <div className="bg-white border rounded p-4">
            {results.documents_bucket_root_files.length === 0 ? (
              <p className="text-red-600">❌ No files found in root of documents bucket</p>
            ) : (
              <ul className="space-y-2">
                {results.documents_bucket_root_files.map((file: any, i: number) => (
                  <li key={i} className="font-mono text-sm">
                    {file.id === 'folder' ? '📁' : '📄'} {file.name}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}

      {/* Sample Doc Metadata */}
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">💾 Sample doc_metadata Records</h2>
        {results?.doc_metadata_error ? (
          <div className="bg-red-50 border border-red-200 p-4 rounded">
            <p className="text-red-800">Error: {results.doc_metadata_error}</p>
          </div>
        ) : (
          <div className="bg-white border rounded overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left">Document ID</th>
                  <th className="px-4 py-2 text-left">Storage Path</th>
                </tr>
              </thead>
              <tbody>
                {results?.sample_doc_metadata?.map((doc: any) => (
                  <tr key={doc.id} className="border-t">
                    <td className="px-4 py-2 font-mono text-xs">{doc.id}</td>
                    <td className="px-4 py-2 font-mono text-xs break-all">
                      {doc.storage_path}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Storage Verification */}
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">🔍 File Existence Check</h2>
        <p className="text-gray-600 mb-4">
          Checking if files referenced in doc_metadata actually exist in storage...
        </p>
        <div className="space-y-4">
          {results?.storage_check?.map((check: any, i: number) => (
            <div
              key={i}
              className={`border rounded p-4 ${
                check.exists ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <p className="text-xs text-gray-500 mb-1">Document ID: {check.doc_id}</p>
                  <p className="font-mono text-sm break-all mb-2">
                    Path: {check.storage_path}
                  </p>
                </div>
                <div className="ml-4">
                  {check.exists ? (
                    <span className="text-2xl">✅</span>
                  ) : (
                    <span className="text-2xl">❌</span>
                  )}
                </div>
              </div>
              {check.error && (
                <p className="text-sm text-red-600">Error: {check.error}</p>
              )}
              {check.exists && (
                <p className="text-sm text-green-700">
                  ✓ Found {check.files_found} file(s) at this path
                </p>
              )}
              {!check.exists && !check.error && (
                <p className="text-sm text-red-700">
                  ✗ File does not exist in storage (metadata exists but file is missing)
                </p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Summary */}
      <section className="bg-blue-50 border border-blue-200 rounded p-6">
        <h2 className="text-xl font-semibold mb-4">📋 Summary</h2>
        <div className="space-y-2">
          <p>
            <strong>Buckets found:</strong> {results?.buckets?.length || 0}
          </p>
          <p>
            <strong>Doc metadata records checked:</strong>{' '}
            {results?.sample_doc_metadata?.length || 0}
          </p>
          <p>
            <strong>Files actually exist in storage:</strong>{' '}
            {results?.storage_check?.filter((c: any) => c.exists).length || 0} /{' '}
            {results?.storage_check?.length || 0}
          </p>

          {results?.storage_check?.some((c: any) => !c.exists) && (
            <div className="mt-4 p-4 bg-yellow-100 border border-yellow-300 rounded">
              <p className="font-semibold text-yellow-900 mb-2">⚠️ Issue Detected</p>
              <p className="text-sm text-yellow-800">
                Your doc_metadata table contains paths to files that don&apos;t exist in
                Supabase Storage. You need to either:
              </p>
              <ol className="list-decimal ml-6 mt-2 text-sm text-yellow-800">
                <li>Upload the missing PDF files to Supabase Storage</li>
                <li>Or remove the orphaned metadata records from doc_metadata</li>
              </ol>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

'use client';

/**
 * /handover-export/[id] — HandoverExport Lens Page
 *
 * Client-only page that fetches handover export data and renders
 * HandoverExportLens in edit or review mode based on user role and
 * current review_status.
 *
 * Uses /api/handover-export/[id]/content route which proxies to Render backend
 * to access Cloud_PMS database. Direct Supabase calls go to Cloud_HQ (auth only).
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { HandoverExportLens } from '@/components/lens/HandoverExportLens';

interface ExportData {
  id: string;
  sections: Section[];
  review_status: string | null;
  created_at: string;
  yacht_name: string | null;
  user_signature: SignatureData | null;
  user_signed_at: string | null;
  hod_signature: SignatureData | null;
  hod_signed_at: string | null;
}

interface Section {
  id: string;
  title: string;
  content: string;
  items: Array<{
    id: string;
    content: string;
    entity_type?: string;
    entity_id?: string;
    priority?: 'critical' | 'action' | 'fyi';
  }>;
  is_critical: boolean;
  order: number;
}

interface SignatureData {
  image_base64: string | null;
  signed_at: string | null;
  signer_name: string | null;
  signer_id: string | null;
}

export default function HandoverExportPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const exportId = params.id as string;
  const modeParam = searchParams.get('mode') as 'edit' | 'review' | null;

  const [exportData, setExportData] = useState<ExportData | null>(null);
  const [currentUser, setCurrentUser] = useState<{ id: string; name: string; role: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(true);

  useEffect(() => {
    async function fetchData() {
      // Check authentication and get session for API calls
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.replace('/login');
        return;
      }

      // Fetch user profile from Cloud_HQ (auth DB)
      const { data: profile } = await supabase
        .from('auth_users_profiles')
        .select('full_name, role')
        .eq('id', session.user.id)
        .single();

      setCurrentUser({
        id: session.user.id,
        name: profile?.full_name || session.user.email || 'Unknown',
        role: profile?.role || 'crew'
      });

      // Fetch handover export via API route (proxies to Cloud_PMS via Render backend)
      try {
        const response = await fetch(`/api/handover-export/${exportId}/content`, {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          setError(errorData.detail || errorData.error || 'Handover export not found');
          setLoading(false);
          return;
        }

        const data = await response.json();
        setExportData({
          id: data.id,
          sections: data.sections || [],
          review_status: data.review_status,
          created_at: data.created_at,
          yacht_name: data.yacht_name,
          user_signature: data.user_signature,
          user_signed_at: data.user_signed_at,
          hod_signature: data.hod_signature,
          hod_signed_at: data.hod_signed_at
        });
        setLoading(false);
      } catch (err) {
        console.error('Error fetching handover export:', err);
        setError('Failed to load handover export');
        setLoading(false);
      }
    }

    fetchData();
  }, [exportId, router]);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    router.back();
  }, [router]);

  const handleSubmit = useCallback(async (data: { sections: Section[]; userSignature: SignatureData }) => {
    const response = await fetch(`/api/handover-export/${exportId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Submit failed');
    router.refresh();
  }, [exportId, router]);

  const handleCountersign = useCallback(async (hodSignature: SignatureData) => {
    const response = await fetch(`/api/handover-export/${exportId}/countersign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hodSignature })
    });
    if (!response.ok) throw new Error('Countersign failed');
    router.refresh();
  }, [exportId, router]);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-surface-base flex items-center justify-center z-[var(--z-modal)]">
        <div className="text-txt-secondary">Loading handover export...</div>
      </div>
    );
  }

  if (error || !exportData || !currentUser) {
    return (
      <div className="fixed inset-0 bg-surface-base flex items-center justify-center z-[var(--z-modal)]">
        <div className="text-status-critical">{error || 'Unable to load export'}</div>
      </div>
    );
  }

  // Determine mode: respect URL param, but force review if already submitted
  let mode: 'edit' | 'review' = modeParam || 'edit';
  if (exportData.user_signature && exportData.review_status !== 'pending_review') {
    mode = 'review';
  }

  // Sections are already parsed by the API
  const sections: Section[] = exportData.sections || [];

  return (
    <HandoverExportLens
      exportId={exportId}
      isOpen={isOpen}
      mode={mode}
      title="Handover Export"
      generatedAt={exportData.created_at}
      yachtName={exportData.yacht_name || 'Unknown Yacht'}
      preparedBy={currentUser.name}
      reviewStatus={(exportData.review_status as 'pending_review' | 'pending_hod_signature' | 'complete') || 'pending_review'}
      initialSections={sections}
      userSignature={exportData.user_signature}
      hodSignature={exportData.hod_signature}
      currentUser={currentUser}
      onClose={handleClose}
      onSubmit={handleSubmit}
      onCountersign={handleCountersign}
    />
  );
}

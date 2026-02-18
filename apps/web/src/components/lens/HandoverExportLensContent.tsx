'use client';

/**
 * HandoverExportLensContent - Wrapper for HandoverExportLens in ContextPanel
 *
 * Fetches export data from Cloud_HQ and renders the HandoverExportLens component
 * with proper mode detection (edit vs review) based on user role and export status.
 */

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabaseClient';
import { HandoverExportLens, type HandoverExportLensProps } from './HandoverExportLens';
import { Loader2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

interface HandoverExportLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate: (type: string, id: string) => void;
  onRefresh?: () => void;
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

interface ExportData {
  id: string;
  title: string;
  yacht_id: string;
  created_by: string;
  item_count: number;
  review_status: 'pending_review' | 'pending_hod_signature' | 'complete';
  edited_content: {
    title?: string;
    generated_at?: string;
    yacht_name?: string;
    prepared_by?: string;
    sections?: Section[];
    signature_section?: {
      outgoing?: SignatureData | null;
      incoming?: SignatureData | null;
      hod?: SignatureData | null;
    };
  } | null;
  user_signature: SignatureData | null;
  hod_signature: SignatureData | null;
  created_at: string;
}

export function HandoverExportLensContent({
  id,
  data: initialData,
  onBack,
  onClose,
}: HandoverExportLensContentProps) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportData, setExportData] = useState<ExportData | null>(null);

  // Fetch export data from Cloud_HQ
  useEffect(() => {
    const fetchExportData = async () => {
      setLoading(true);
      setError(null);

      try {
        // Fetch from Cloud_HQ handover_exports table
        const { data, error: fetchError } = await supabase
          .from('handover_exports')
          .select('*')
          .eq('id', id)
          .single();

        if (fetchError) {
          throw new Error(fetchError.message);
        }

        if (!data) {
          throw new Error('Export not found');
        }

        // Validate yacht access
        if (data.yacht_id !== user?.yachtId) {
          throw new Error('Access denied: Export belongs to different yacht');
        }

        setExportData(data as ExportData);
      } catch (err) {
        console.error('[HandoverExportLensContent] Error fetching export:', err);
        setError(err instanceof Error ? err.message : 'Failed to load export');
      } finally {
        setLoading(false);
      }
    };

    if (id && user?.yachtId) {
      fetchExportData();
    }
  }, [id, user?.yachtId]);

  // Determine mode based on user role and export status
  const getMode = useCallback((): 'edit' | 'review' => {
    if (!exportData || !user) return 'edit';

    // If user is the creator and status is pending_review, they can edit
    if (exportData.created_by === user.id && exportData.review_status === 'pending_review') {
      return 'edit';
    }

    // If status is pending_hod_signature and user is HOD+, they review
    if (exportData.review_status === 'pending_hod_signature') {
      const hodRoles = ['hod', 'captain', 'manager', 'chief_engineer'];
      if (user.role && hodRoles.includes(user.role)) {
        return 'review';
      }
    }

    // Default to review for completed exports
    return 'review';
  }, [exportData, user]);

  // Handle user submit (sign and send for HOD approval)
  const handleSubmit = async (data: {
    sections: Section[];
    userSignature: SignatureData;
  }) => {
    if (!exportData || !user) return;

    try {
      const { error: updateError } = await supabase
        .from('handover_exports')
        .update({
          edited_content: {
            ...exportData.edited_content,
            sections: data.sections,
          },
          user_signature: data.userSignature,
          user_signed_at: data.userSignature.signed_at,
          user_submitted_at: new Date().toISOString(),
          review_status: 'pending_hod_signature',
        })
        .eq('id', id);

      if (updateError) throw updateError;

      // Update local state
      setExportData(prev => prev ? {
        ...prev,
        review_status: 'pending_hod_signature',
        user_signature: data.userSignature,
        edited_content: {
          ...prev.edited_content,
          sections: data.sections,
        },
      } : null);

      toast.success('Submitted for HOD approval');
    } catch (err) {
      console.error('[HandoverExportLensContent] Submit error:', err);
      throw err;
    }
  };

  // Handle HOD countersign
  const handleCountersign = async (hodSignature: SignatureData) => {
    if (!exportData || !user) return;

    try {
      const { error: updateError } = await supabase
        .from('handover_exports')
        .update({
          hod_signature: hodSignature,
          hod_signed_at: hodSignature.signed_at,
          hod_user_id: user.id,
          review_status: 'complete',
          completed_at: new Date().toISOString(),
        })
        .eq('id', id);

      if (updateError) throw updateError;

      // Queue for search indexing
      await supabase.from('search_index_queue').insert({
        entity_type: 'handover_export',
        entity_id: id,
        yacht_id: exportData.yacht_id,
        priority: 1,
        status: 'pending',
      });

      // Update local state
      setExportData(prev => prev ? {
        ...prev,
        review_status: 'complete',
        hod_signature: hodSignature,
      } : null);

      toast.success('Approved and countersigned');
    } catch (err) {
      console.error('[HandoverExportLensContent] Countersign error:', err);
      throw err;
    }
  };

  // Handle draft save
  const handleSaveDraft = async (sections: Section[]) => {
    if (!exportData) return;

    try {
      const { error: updateError } = await supabase
        .from('handover_exports')
        .update({
          edited_content: {
            ...exportData.edited_content,
            sections,
          },
          updated_at: new Date().toISOString(),
        })
        .eq('id', id);

      if (updateError) throw updateError;

      toast.success('Draft saved');
    } catch (err) {
      console.error('[HandoverExportLensContent] Save draft error:', err);
      toast.error('Failed to save draft');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-celeste-blue animate-spin mx-auto mb-3" />
          <p className="text-txt-tertiary text-sm">Loading export...</p>
        </div>
      </div>
    );
  }

  if (error || !exportData) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-3" />
          <p className="text-txt-tertiary text-sm mb-3">{error || 'Export not found'}</p>
          <button
            onClick={onClose}
            className="text-celeste-blue hover:text-celeste-blue-hover text-sm"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  const editedContent = exportData.edited_content || {};
  const sections = editedContent.sections || [];
  const mode = getMode();

  return (
    <HandoverExportLens
      exportId={exportData.id}
      isOpen={true}
      mode={mode}
      title={editedContent.title || exportData.title || 'Handover Export'}
      generatedAt={editedContent.generated_at || exportData.created_at}
      yachtName={editedContent.yacht_name || 'Unknown Yacht'}
      preparedBy={editedContent.prepared_by || 'Unknown'}
      reviewStatus={exportData.review_status}
      initialSections={sections}
      userSignature={exportData.user_signature}
      hodSignature={exportData.hod_signature}
      currentUser={{
        id: user?.id || '',
        name: user?.displayName || user?.email || 'User',
        role: user?.role || 'member',
      }}
      onClose={onClose}
      onSubmit={handleSubmit}
      onCountersign={handleCountersign}
      onSaveDraft={handleSaveDraft}
    />
  );
}

export default HandoverExportLensContent;

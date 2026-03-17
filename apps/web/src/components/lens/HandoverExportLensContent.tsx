'use client';

/**
 * HandoverExportLensContent - Handover export review/sign-off view.
 *
 * Renders inside EntityLensPage at /handover-export/{id}.
 * Entity data comes from useEntityLensContext() — zero props.
 *
 * IMPORTANT: The signature flow (SignatureCanvas → /api/handover-export/[id]/submit)
 * is independent of the p0 action router. handleSubmit and handleCountersign call
 * dedicated Next.js API routes directly — they do NOT go through executeAction/safeExecute.
 *
 * available_actions returns [] for handover_export (no p0 actions registered).
 * The shell action bar will be empty — correct behaviour.
 */

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { useAuth } from '@/hooks/useAuth';
import { HandoverExportLens } from './HandoverExportLens';
import { AlertCircle } from 'lucide-react';

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

export function HandoverExportLensContent() {
  const { entityId, entity } = useEntityLensContext();
  const { user, session } = useAuth();
  const router = useRouter();
  const token = session?.access_token ?? null;

  // Mode is derived from entity state only — no client-side role checks.
  // Backend enforces HOD authorization on the countersign endpoint.
  const getMode = useCallback((): 'edit' | 'review' => {
    if (!entity || !user) return 'review';
    const reviewStatus = entity.review_status as string | undefined;
    const createdBy = entity.created_by as string | undefined;
    // Only the creator can edit while status is still pending_review
    if (createdBy === user.id && reviewStatus === 'pending_review') return 'edit';
    return 'review';
  }, [entity, user]);

  // ---------------------------------------------------------------------------
  // Dedicated API routes — NOT safeExecute / executeAction
  // These call Next.js proxy routes that forward to the Python backend.
  // Both routes require Authorization: Bearer <token>.
  // ---------------------------------------------------------------------------

  // Handle user submit (sign and send for HOD approval)
  const handleSubmit = useCallback(async (data: {
    sections: Section[];
    userSignature: SignatureData;
  }) => {
    const response = await fetch(`/api/handover-export/${entityId}/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Submit failed');
    router.refresh();
  }, [entityId, token, router]);

  // Handle HOD countersign — backend enforces HOD role authorization
  const handleCountersign = useCallback(async (hodSignature: SignatureData) => {
    const response = await fetch(`/api/handover-export/${entityId}/countersign`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ hodSignature }),
    });
    if (!response.ok) throw new Error('Countersign failed');
    router.refresh();
  }, [entityId, token, router]);

  // No dedicated draft-save API route exists — onSaveDraft omitted from HandoverExportLens.

  // EntityLensPage handles isLoading and entity-not-found states before mounting this component.
  // The !user guard covers the edge case where auth session is missing.
  if (!entity || !user) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-3" />
          <p className="text-celeste-text-muted typo-body mb-3">
            {!user ? 'Not authenticated' : 'Export not found'}
          </p>
          <button
            onClick={() => router.back()}
            className="text-celeste-blue hover:text-celeste-blue-hover typo-body"
          >
            Go back
          </button>
        </div>
      </div>
    );
  }

  const editedContent = (entity.edited_content as Record<string, unknown> | null) ?? {};
  const sections = (editedContent.sections as Section[]) ?? [];
  const reviewStatus = (entity.review_status as 'pending_review' | 'pending_hod_signature' | 'complete') ?? 'pending_review';
  const userSignature = (entity.user_signature as SignatureData | null) ?? null;
  const hodSignature = (entity.hod_signature as SignatureData | null) ?? null;

  // Force review mode if user has already submitted their signature
  const mode: 'edit' | 'review' = userSignature ? 'review' : getMode();

  return (
    <HandoverExportLens
      exportId={entityId}
      isOpen={true}
      mode={mode}
      title={(editedContent.title as string) || (entity.title as string) || 'Handover Export'}
      generatedAt={(editedContent.generated_at as string) || (entity.created_at as string) || ''}
      yachtName={(editedContent.yacht_name as string) || (entity.yacht_name as string) || 'Unknown Yacht'}
      preparedBy={(editedContent.prepared_by as string) || user.displayName || user.email || 'User'}
      reviewStatus={reviewStatus}
      initialSections={sections}
      userSignature={userSignature}
      hodSignature={hodSignature}
      currentUser={{
        id: user.id || '',
        name: user.displayName || user.email || 'User',
        role: user.role || 'member',
      }}
      onClose={() => router.back()}
      onSubmit={handleSubmit}
      onCountersign={handleCountersign}
    />
  );
}

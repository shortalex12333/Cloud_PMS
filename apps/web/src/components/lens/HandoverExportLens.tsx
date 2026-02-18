'use client';

import { useState, useCallback } from 'react';
import { LensContainer } from '@/components/lens/LensContainer';
import { LensHeader, LensTitleBlock } from '@/components/lens/LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import {
  EditableSectionRenderer,
  SignatureSection,
  FinishButton
} from './handover-export-sections';
import { toast } from 'sonner';

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

export interface HandoverExportLensProps {
  exportId: string;
  isOpen: boolean;
  mode: 'edit' | 'review';
  title: string;
  generatedAt: string;
  yachtName: string;
  preparedBy: string;
  reviewStatus: 'pending_review' | 'pending_hod_signature' | 'complete';
  initialSections: Section[];
  userSignature: SignatureData | null;
  hodSignature: SignatureData | null;
  currentUser: {
    id: string;
    name: string;
    role: string;
  };
  onClose: () => void;
  onSubmit: (data: {
    sections: Section[];
    userSignature: SignatureData;
  }) => Promise<void>;
  onCountersign: (hodSignature: SignatureData) => Promise<void>;
  onSaveDraft?: (sections: Section[]) => Promise<void>;
}

const getStatusColor = (status: string): 'neutral' | 'warning' | 'success' => {
  switch (status) {
    case 'pending_review': return 'neutral';
    case 'pending_hod_signature': return 'warning';
    case 'complete': return 'success';
    default: return 'neutral';
  }
};

const getStatusLabel = (status: string): string => {
  switch (status) {
    case 'pending_review': return 'Pending Review';
    case 'pending_hod_signature': return 'Awaiting HOD';
    case 'complete': return 'Complete';
    default: return status;
  }
};

export function HandoverExportLens({
  exportId,
  isOpen,
  mode,
  title,
  generatedAt,
  yachtName,
  preparedBy,
  reviewStatus,
  initialSections,
  userSignature: initialUserSignature,
  hodSignature: initialHodSignature,
  currentUser,
  onClose,
  onSubmit,
  onCountersign,
  onSaveDraft
}: HandoverExportLensProps) {
  const [sections, setSections] = useState<Section[]>(initialSections);
  const [userSignature, setUserSignature] = useState<string | null>(
    initialUserSignature?.image_base64 ?? null
  );
  const [hodSignature, setHodSignature] = useState<string | null>(
    initialHodSignature?.image_base64 ?? null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  const handleSectionsChange = useCallback((newSections: Section[]) => {
    setSections(newSections);
    setIsDirty(true);
  }, []);

  const handleUserSignatureChange = useCallback((base64: string | null) => {
    setUserSignature(base64);
    setIsDirty(true);
  }, []);

  const handleHodSignatureChange = useCallback((base64: string | null) => {
    setHodSignature(base64);
  }, []);

  const handleSubmit = async () => {
    if (!userSignature) {
      toast.error('You must sign the handover before submitting');
      return;
    }

    setIsLoading(true);
    try {
      await onSubmit({
        sections,
        userSignature: {
          image_base64: userSignature,
          signed_at: new Date().toISOString(),
          signer_name: currentUser.name,
          signer_id: currentUser.id
        }
      });
      toast.success('Handover submitted for HOD approval');
    } catch (error) {
      toast.error('Failed to submit handover');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCountersign = async () => {
    if (!hodSignature) {
      toast.error('You must countersign before approving');
      return;
    }

    setIsLoading(true);
    try {
      await onCountersign({
        image_base64: hodSignature,
        signed_at: new Date().toISOString(),
        signer_name: currentUser.name,
        signer_id: currentUser.id
      });
      toast.success('Handover approved and countersigned');
    } catch (error) {
      toast.error('Failed to countersign handover');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const vitalSigns: VitalSign[] = [
    {
      label: 'Status',
      value: getStatusLabel(reviewStatus),
      color: getStatusColor(reviewStatus)
    },
    { label: 'Yacht', value: yachtName },
    { label: 'Prepared By', value: preparedBy },
    { label: 'Generated', value: new Date(generatedAt).toLocaleDateString() },
    { label: 'Sections', value: String(sections.length) }
  ];

  return (
    <LensContainer isOpen={isOpen} onClose={onClose}>
      {/* Fixed header */}
      <LensHeader
        entityType="Handover Export"
        title={title}
        subtitle={`Export ID: ${exportId}`}
        onBack={onClose}
        onClose={onClose}
      />

      {/* Scrollable content — pt-14 clears the 56px fixed header */}
      <div className="pt-14">
        {/* Title block */}
        <div className="px-6 pt-6 pb-4">
          <LensTitleBlock
            title={title}
            subtitle={`Export ID: ${exportId}`}
          />
        </div>

        {/* Vital signs row */}
        <div className="px-6 pb-4">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {/* Mode indicator */}
        <div className={`px-4 py-2 text-sm ${mode === 'edit' ? 'bg-brand-surface text-brand-interactive' : 'bg-surface-secondary text-txt-secondary'}`}>
          {mode === 'edit'
            ? 'Edit Mode — You can modify sections and sign'
            : 'Review Mode — Read-only, countersign to approve'}
        </div>

        {/* Action button */}
        <div className="px-6 py-4">
          <FinishButton
            mode={mode}
            hasUserSignature={!!userSignature}
            hasHodSignature={!!hodSignature}
            onSubmit={handleSubmit}
            onCountersign={handleCountersign}
            isLoading={isLoading}
          />
        </div>

        {/* Editable sections */}
        <div className="p-4">
          <EditableSectionRenderer
            sections={sections}
            onSectionsChange={handleSectionsChange}
            mode={mode}
          />

          {/* Signature section */}
          <SignatureSection
            mode={mode}
            userSignature={userSignature ? {
              image_base64: userSignature,
              signed_at: initialUserSignature?.signed_at ?? null,
              signer_name: initialUserSignature?.signer_name ?? currentUser.name,
              signer_id: initialUserSignature?.signer_id ?? currentUser.id
            } : null}
            hodSignature={hodSignature ? {
              image_base64: hodSignature,
              signed_at: initialHodSignature?.signed_at ?? null,
              signer_name: initialHodSignature?.signer_name ?? null,
              signer_id: initialHodSignature?.signer_id ?? null
            } : null}
            onUserSignatureChange={handleUserSignatureChange}
            onHodSignatureChange={handleHodSignatureChange}
            currentUserName={currentUser.name}
            currentUserId={currentUser.id}
          />
        </div>
      </div>
    </LensContainer>
  );
}

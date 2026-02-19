'use client';

import { SignatureCanvas } from './SignatureCanvas';

interface SignatureData {
  image_base64: string | null;
  signed_at: string | null;
  signer_name: string | null;
  signer_id: string | null;
}

interface SignatureSectionProps {
  mode: 'edit' | 'review';
  userSignature: SignatureData | null;
  hodSignature: SignatureData | null;
  onUserSignatureChange: (base64: string | null) => void;
  onHodSignatureChange: (base64: string | null) => void;
  currentUserName: string;
  currentUserId: string;
}

export function SignatureSection({
  mode,
  userSignature,
  hodSignature,
  onUserSignatureChange,
  onHodSignatureChange,
  currentUserName,
  currentUserId
}: SignatureSectionProps) {
  const isEditMode = mode === 'edit';
  const isReviewMode = mode === 'review';

  return (
    <div className="border-t border-surface-border pt-6 mt-6">
      <h3 className="typo-title font-semibold text-txt-primary mb-4">Signatures</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* User Signature */}
        <div className="flex flex-col gap-2">
          <div className="typo-body font-medium text-txt-secondary">Prepared By</div>
          {userSignature?.image_base64 ? (
            <div className="border border-surface-border rounded-lg p-4 bg-surface-secondary">
              <img
                src={userSignature.image_base64}
                alt="User signature"
                className="h-[100px] object-contain"
              />
              <div className="mt-2 typo-body text-txt-secondary">
                {userSignature.signer_name} — {userSignature.signed_at}
              </div>
            </div>
          ) : isEditMode ? (
            <SignatureCanvas
              label="Your Signature"
              onSignatureChange={onUserSignatureChange}
              disabled={false}
            />
          ) : (
            <div className="border border-surface-border rounded-lg p-4 bg-surface-secondary text-txt-tertiary">
              Not yet signed
            </div>
          )}
        </div>

        {/* HOD Countersignature */}
        <div className="flex flex-col gap-2">
          <div className="typo-body font-medium text-txt-secondary">Approved By (HOD)</div>
          {hodSignature?.image_base64 ? (
            <div className="border border-surface-border rounded-lg p-4 bg-surface-secondary">
              <img
                src={hodSignature.image_base64}
                alt="HOD signature"
                className="h-[100px] object-contain"
              />
              <div className="mt-2 typo-body text-txt-secondary">
                {hodSignature.signer_name} — {hodSignature.signed_at}
              </div>
            </div>
          ) : isReviewMode ? (
            <SignatureCanvas
              label="HOD Countersignature"
              onSignatureChange={onHodSignatureChange}
              disabled={!userSignature?.image_base64}
            />
          ) : (
            <div className="border border-surface-border rounded-lg p-4 bg-surface-secondary text-txt-tertiary">
              {userSignature?.image_base64
                ? 'Awaiting HOD countersignature'
                : 'User must sign first'}
            </div>
          )}
        </div>
      </div>

      {/* Status message */}
      {isEditMode && !userSignature?.image_base64 && (
        <p className="mt-4 typo-body text-status-warning" id="signature-required-message">
          You must sign the handover before submitting
        </p>
      )}
      {isReviewMode && userSignature?.image_base64 && !hodSignature?.image_base64 && (
        <p className="mt-4 typo-body text-brand-interactive">
          Please review the document and add your countersignature to approve
        </p>
      )}
    </div>
  );
}

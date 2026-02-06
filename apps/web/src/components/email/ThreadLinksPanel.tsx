'use client';

/**
 * ThreadLinksPanel - Shows objects linked to an email thread
 *
 * Used in EmailSurface when clicking "See related (N)".
 * Shows accepted links and suggestions, allows Accept/Change/Remove.
 */

import React, { useState, useCallback } from 'react';
import {
  X,
  Link as LinkIcon,
  Loader2,
  Check,
  RefreshCw,
  Unlink,
  AlertCircle,
  Wrench,
  Package,
  AlertTriangle,
  FileText,
  Users,
  ChevronRight,
} from 'lucide-react';
import {
  useThreadLinks,
  useAcceptLink,
  useRemoveLink,
  type ThreadLink,
  type LinkConfidence,
} from '@/hooks/useEmailData';
import { LinkEmailModal } from './LinkEmailModal';
import { cn } from '@/lib/utils';

// ============================================================================
// TYPES
// ============================================================================

interface ThreadLinksPanelProps {
  open: boolean;
  onClose: () => void;
  threadId: string;
  threadSubject?: string;
}

// Object type icons
const OBJECT_TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  work_order: Wrench,
  equipment: Package,
  part: Package,
  fault: AlertTriangle,
  purchase_order: FileText,
  supplier: Users,
};

const OBJECT_TYPE_LABELS: Record<string, string> = {
  work_order: 'Work Order',
  equipment: 'Equipment',
  part: 'Part',
  fault: 'Fault',
  purchase_order: 'PO',
  supplier: 'Supplier',
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function ThreadLinksPanel({
  open,
  onClose,
  threadId,
  threadSubject,
}: ThreadLinksPanelProps) {
  const [showChangeModal, setShowChangeModal] = useState(false);
  const [selectedLinkForChange, setSelectedLinkForChange] = useState<ThreadLink | null>(null);

  // Fetch links for this thread
  const { data: linksData, isLoading, error, refetch } = useThreadLinks(threadId, 0);
  const links = linksData?.links || [];

  // Separate accepted and suggested links
  const acceptedLinks = links.filter(l => l.accepted || l.confidence_level !== 'suggested');
  const suggestedLinks = links.filter(l => !l.accepted && l.confidence_level === 'suggested');

  // Handle opening change modal
  const handleOpenChange = useCallback((link: ThreadLink) => {
    setSelectedLinkForChange(link);
    setShowChangeModal(true);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1100] flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative w-full max-w-md bg-[#1c1c1e] shadow-2xl border-l border-[#3d3d3f] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#3d3d3f]">
          <div>
            <h2 className="text-[16px] font-semibold text-white flex items-center gap-2">
              <LinkIcon className="w-5 h-5 text-[#30d158]" />
              Linked Objects
            </h2>
            {threadSubject && (
              <p className="text-[12px] text-[#636366] mt-0.5 truncate max-w-[300px]">
                {threadSubject}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#98989f] hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100%-65px)]">
          {/* Loading */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-[#0a84ff]" />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-4 text-center">
              <AlertCircle className="w-8 h-8 text-[#ff453a] mx-auto mb-2" />
              <p className="text-[13px] text-[#ff453a] mb-2">
                {error instanceof Error ? error.message : 'Failed to load links'}
              </p>
              <button
                onClick={() => refetch()}
                className="text-[13px] text-[#0a84ff] hover:text-[#409cff]"
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty */}
          {!isLoading && !error && links.length === 0 && (
            <div className="p-8 text-center">
              <LinkIcon className="w-10 h-10 text-[#48484a] mx-auto mb-3" />
              <p className="text-[14px] text-[#98989f] mb-1">No linked objects</p>
              <p className="text-[12px] text-[#636366]">
                Use "Link to..." to connect this email to work orders, equipment, etc.
              </p>
            </div>
          )}

          {/* Accepted Links */}
          {!isLoading && !error && acceptedLinks.length > 0 && (
            <div className="border-b border-[#3d3d3f]">
              <div className="px-4 py-2 bg-[#2c2c2e]">
                <h3 className="text-[12px] font-medium text-[#98989f]">
                  Linked ({acceptedLinks.length})
                </h3>
              </div>
              <div className="divide-y divide-[#3d3d3f]/50">
                {acceptedLinks.map((link) => (
                  <LinkItem
                    key={link.id}
                    link={link}
                    onChangeClick={() => handleOpenChange(link)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Suggested Links */}
          {!isLoading && !error && suggestedLinks.length > 0 && (
            <div>
              <div className="px-4 py-2 bg-[#2c2c2e]">
                <h3 className="text-[12px] font-medium text-[#ff9f0a]">
                  Suggestions ({suggestedLinks.length})
                </h3>
              </div>
              <div className="divide-y divide-[#3d3d3f]/50">
                {suggestedLinks.map((link) => (
                  <LinkItem
                    key={link.id}
                    link={link}
                    isSuggested
                    onChangeClick={() => handleOpenChange(link)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Change Link Modal */}
      {selectedLinkForChange && (
        <LinkEmailModal
          open={showChangeModal}
          onOpenChange={setShowChangeModal}
          threadId={threadId}
          threadSubject={threadSubject}
          existingLinkId={selectedLinkForChange.id}
          existingObjectType={selectedLinkForChange.object_type}
          existingObjectId={selectedLinkForChange.object_id}
        />
      )}
    </div>
  );
}

// ============================================================================
// LINK ITEM COMPONENT
// ============================================================================

interface LinkItemProps {
  link: ThreadLink;
  isSuggested?: boolean;
  onChangeClick: () => void;
}

function LinkItem({ link, isSuggested, onChangeClick }: LinkItemProps) {
  const [showUnlinkConfirm, setShowUnlinkConfirm] = useState(false);

  const acceptMutation = useAcceptLink();
  const removeMutation = useRemoveLink();

  const Icon = OBJECT_TYPE_ICONS[link.object_type] || Package;
  const typeLabel = OBJECT_TYPE_LABELS[link.object_type] || link.object_type;

  const handleAccept = async () => {
    try {
      await acceptMutation.mutateAsync(link.id);
    } catch (err) {
      console.error('[ThreadLinksPanel] Accept failed:', err);
    }
  };

  const handleUnlink = async () => {
    try {
      await removeMutation.mutateAsync(link.id);
      setShowUnlinkConfirm(false);
    } catch (err) {
      console.error('[ThreadLinksPanel] Unlink failed:', err);
    }
  };

  return (
    <div className="p-3">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div
          className={cn(
            'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
            isSuggested ? 'bg-[#ff9f0a]/20' : 'bg-[#30d158]/20'
          )}
        >
          <Icon
            className={cn(
              'w-4 h-4',
              isSuggested ? 'text-[#ff9f0a]' : 'text-[#30d158]'
            )}
          />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-medium text-white truncate">
              {typeLabel}
            </span>
            {isSuggested && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#ff9f0a]/20 text-[#ff9f0a]">
                Suggested
              </span>
            )}
          </div>
          <p className="text-[12px] text-[#636366] truncate">
            ID: {link.object_id.substring(0, 8)}...
          </p>
          {link.suggested_reason && (
            <p className="text-[11px] text-[#48484a] mt-0.5 line-clamp-2">
              {link.suggested_reason}
            </p>
          )}
        </div>

        {/* Navigate */}
        <button className="p-1.5 rounded text-[#636366] hover:text-white hover:bg-white/10 transition-colors">
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 mt-2 ml-11">
        {/* Accept (only for suggested) */}
        {isSuggested && (
          <button
            onClick={handleAccept}
            disabled={acceptMutation.isPending}
            className={cn(
              'flex items-center gap-1 px-2 py-1 rounded text-[11px] transition-colors',
              'text-[#30d158] hover:bg-[#30d158]/20',
              acceptMutation.isPending && 'opacity-50'
            )}
          >
            {acceptMutation.isPending ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Check className="w-3 h-3" />
            )}
            Accept
          </button>
        )}

        {/* Change */}
        <button
          onClick={onChangeClick}
          className="flex items-center gap-1 px-2 py-1 rounded text-[11px] text-[#98989f] hover:bg-white/10 transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          Change
        </button>

        {/* Unlink */}
        {!showUnlinkConfirm ? (
          <button
            onClick={() => setShowUnlinkConfirm(true)}
            className="flex items-center gap-1 px-2 py-1 rounded text-[11px] text-[#ff453a] hover:bg-[#ff453a]/20 transition-colors"
          >
            <Unlink className="w-3 h-3" />
            Unlink
          </button>
        ) : (
          <div className="flex items-center gap-1">
            <button
              onClick={handleUnlink}
              disabled={removeMutation.isPending}
              className="flex items-center gap-1 px-2 py-1 rounded text-[11px] bg-[#ff453a] text-white hover:bg-[#ff453a]/80 transition-colors"
            >
              {removeMutation.isPending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                'Confirm'
              )}
            </button>
            <button
              onClick={() => setShowUnlinkConfirm(false)}
              className="px-2 py-1 rounded text-[11px] text-[#98989f] hover:bg-white/10 transition-colors"
            >
              Cancel
            </button>
          </div>
        )}

        {/* Error indicator */}
        {(acceptMutation.isError || removeMutation.isError) && (
          <span className="text-[#ff453a] text-[10px] flex items-center gap-0.5">
            <AlertCircle className="w-3 h-3" />
            Failed
          </span>
        )}
      </div>
    </div>
  );
}

export default ThreadLinksPanel;

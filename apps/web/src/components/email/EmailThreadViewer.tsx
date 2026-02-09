/**
 * EmailThreadViewer Component
 *
 * Shows thread messages with fetch-on-click for original content.
 *
 * Design principles:
 * - Messages are metadata until user clicks "View original"
 * - Original content is fetched from Graph API on demand
 * - Content is NEVER stored - only displayed
 * - Failures show explicit error state (no summarization)
 */

'use client';

import { useState } from 'react';
import {
  X,
  ChevronDown,
  ChevronRight,
  ArrowDownLeft,
  ArrowUpRight,
  Paperclip,
  Eye,
  Loader2,
  AlertCircle,
  FileText,
} from 'lucide-react';
import { useThread, useMessageContent, type EmailMessage, type MessageContent } from '@/hooks/useEmailData';
import { cn, formatEmailTimestamp } from '@/lib/utils';
import DocumentViewerOverlay from '@/components/viewer/DocumentViewerOverlay';

interface EmailThreadViewerProps {
  threadId: string;
  onClose?: () => void;
}

interface AttachmentViewerState {
  open: boolean;
  fileName: string;
  contentType: string;
  blobUrl: string;
  downloadUrl: string;
}

export function EmailThreadViewer({ threadId, onClose }: EmailThreadViewerProps) {
  const { data: thread, isLoading, error } = useThread(threadId);
  const [expandedMessageId, setExpandedMessageId] = useState<string | null>(null);
  const [attachmentViewer, setAttachmentViewer] = useState<AttachmentViewerState>({
    open: false,
    fileName: '',
    contentType: '',
    blobUrl: '',
    downloadUrl: '',
  });

  const handleAttachmentClick = (providerMessageId: string, attachmentId: string, fileName: string, contentType: string) => {
    // Build URL for inline viewing (not download)
    const viewUrl = `/api/email/message/${providerMessageId}/attachments/${attachmentId}/download?inline=true`;
    const downloadUrl = `/api/email/message/${providerMessageId}/attachments/${attachmentId}/download`;

    setAttachmentViewer({
      open: true,
      fileName,
      contentType,
      blobUrl: viewUrl,
      downloadUrl,
    });
  };

  const closeAttachmentViewer = () => {
    setAttachmentViewer({
      open: false,
      fileName: '',
      contentType: '',
      blobUrl: '',
      downloadUrl: '',
    });
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6 text-center">
        <AlertCircle className="h-6 w-6 text-red-500 mx-auto mb-2" />
        <p className="text-[13px] text-zinc-600 dark:text-zinc-400">
          {error instanceof Error ? error.message : 'Failed to load thread'}
        </p>
      </div>
    );
  }

  if (!thread) return null;

  return (
    <div className="bg-zinc-50 dark:bg-zinc-900/50">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <h3 className="text-[14px] font-medium text-zinc-800 dark:text-zinc-200">
            {thread.latest_subject || '(No subject)'}
          </h3>
          <p className="text-[12px] text-zinc-500">
            {thread.message_count} message{thread.message_count !== 1 ? 's' : ''}
            {thread.has_attachments && ' • Has attachments'}
          </p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded transition-colors"
          >
            <X className="h-4 w-4 text-zinc-500" />
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="divide-y divide-zinc-200 dark:divide-zinc-800 max-h-[400px] overflow-y-auto">
        {thread.messages.map((message) => (
          <MessageItem
            key={message.id}
            message={message}
            isExpanded={expandedMessageId === message.id}
            onToggle={() => setExpandedMessageId(
              expandedMessageId === message.id ? null : message.id
            )}
            onAttachmentClick={handleAttachmentClick}
          />
        ))}
      </div>

      {/* Attachment Viewer Overlay */}
      <DocumentViewerOverlay
        open={attachmentViewer.open}
        onClose={closeAttachmentViewer}
        fileName={attachmentViewer.fileName}
        contentType={attachmentViewer.contentType}
        blobUrl={attachmentViewer.blobUrl}
        downloadUrl={attachmentViewer.downloadUrl}
      />
    </div>
  );
}

// ============================================================================
// MESSAGE ITEM SUB-COMPONENT
// ============================================================================

interface MessageItemProps {
  message: EmailMessage;
  isExpanded: boolean;
  onToggle: () => void;
  onAttachmentClick: (providerMessageId: string, attachmentId: string, fileName: string, contentType: string) => void;
}

function MessageItem({ message, isExpanded, onToggle, onAttachmentClick }: MessageItemProps) {
  const [showOriginal, setShowOriginal] = useState(false);

  const isInbound = message.direction === 'inbound';
  const timestamp = message.sent_at || message.received_at;

  return (
    <div className="p-3">
      {/* Message Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-start gap-2 text-left"
      >
        {/* Direction Icon */}
        <div className={cn(
          'p-1 rounded',
          isInbound ? 'bg-blue-100 dark:bg-blue-900/30' : 'bg-green-100 dark:bg-green-900/30'
        )}>
          {isInbound ? (
            <ArrowDownLeft className="h-3 w-3 text-blue-600 dark:text-blue-400" />
          ) : (
            <ArrowUpRight className="h-3 w-3 text-green-600 dark:text-green-400" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[13px] font-medium text-zinc-800 dark:text-zinc-200 truncate">
              {message.from_display_name || 'Unknown'}
            </span>
            <div className="flex items-center gap-2 flex-shrink-0">
              {message.has_attachments && (
                <Paperclip className="h-3 w-3 text-zinc-400" />
              )}
              <span className="text-[11px] text-zinc-400">
                {timestamp ? formatEmailTimestamp(timestamp) : ''}
              </span>
              {isExpanded ? (
                <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 text-zinc-400" />
              )}
            </div>
          </div>
          <p className="text-[12px] text-zinc-500 truncate">
            {message.subject || '(No subject)'}
          </p>
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="mt-3 ml-7 pl-3 border-l-2 border-zinc-200 dark:border-zinc-700">
          {/* Attachments List (metadata only) */}
          {message.has_attachments && message.attachments && message.attachments.length > 0 && (
            <div className="mb-3">
              <p className="text-[11px] text-zinc-500 uppercase tracking-wider mb-1">
                Attachments
              </p>
              <div className="flex flex-wrap gap-1">
                {message.attachments.map((att) => (
                  <button
                    key={att.id}
                    onClick={() => onAttachmentClick(
                      message.provider_message_id,
                      att.id,
                      att.name,
                      att.contentType || 'application/octet-stream'
                    )}
                    className="inline-flex items-center gap-1 text-[12px] text-zinc-600 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 px-2 py-0.5 rounded transition-colors cursor-pointer"
                  >
                    <FileText className="h-3 w-3" />
                    {att.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* View Original Button */}
          {!showOriginal ? (
            <button
              onClick={() => setShowOriginal(true)}
              className="inline-flex items-center gap-1.5 text-[13px] text-blue-500 hover:text-blue-600 transition-colors"
            >
              <Eye className="h-3.5 w-3.5" />
              View original
            </button>
          ) : (
            <OriginalContentViewer
              providerMessageId={message.provider_message_id}
              onClose={() => setShowOriginal(false)}
              onAttachmentClick={onAttachmentClick}
            />
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// ORIGINAL CONTENT VIEWER SUB-COMPONENT
// ============================================================================

interface OriginalContentViewerProps {
  providerMessageId: string;
  onClose: () => void;
  onAttachmentClick: (providerMessageId: string, attachmentId: string, fileName: string, contentType: string) => void;
}

function OriginalContentViewer({ providerMessageId, onClose, onAttachmentClick }: OriginalContentViewerProps) {
  const { data: content, isLoading, error } = useMessageContent(providerMessageId);

  // Loading state
  if (isLoading) {
    return (
      <div className="py-4 flex items-center gap-2 text-zinc-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-[13px]">Fetching original from Outlook...</span>
      </div>
    );
  }

  // Error state - explicit, no summarization
  if (error) {
    return (
      <div className="py-4 px-3 bg-red-50 dark:bg-red-900/20 rounded">
        <div className="flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-[13px] font-medium text-red-700 dark:text-red-400">
              Can&apos;t retrieve original right now
            </p>
            <p className="text-[12px] text-red-600 dark:text-red-500 mt-0.5">
              Reason: {error instanceof Error ? error.message : 'Unknown error'}
            </p>
            <button
              onClick={onClose}
              className="text-[12px] text-red-500 hover:text-red-600 mt-2"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!content) return null;

  return (
    <div className="mt-2">
      {/* Original Content Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] text-zinc-500 uppercase tracking-wider">
          Original Content
        </span>
        <button
          onClick={onClose}
          className="text-[12px] text-zinc-500 hover:text-zinc-700"
        >
          Hide
        </button>
      </div>

      {/* Sender/Recipient Info */}
      <div className="text-[12px] text-zinc-500 mb-2 space-y-0.5">
        {content.from_address?.emailAddress && (
          <p>
            <span className="text-zinc-400">From:</span>{' '}
            {content.from_address.emailAddress.name || content.from_address.emailAddress.address}
          </p>
        )}
        {content.to_recipients.length > 0 && (
          <p>
            <span className="text-zinc-400">To:</span>{' '}
            {content.to_recipients.map(r => r.emailAddress?.name || r.emailAddress?.address).join(', ')}
          </p>
        )}
        {content.cc_recipients.length > 0 && (
          <p>
            <span className="text-zinc-400">Cc:</span>{' '}
            {content.cc_recipients.map(r => r.emailAddress?.name || r.emailAddress?.address).join(', ')}
          </p>
        )}
      </div>

      {/* Body Content - Sandboxed */}
      <div className="border border-zinc-200 dark:border-zinc-700 rounded bg-white dark:bg-zinc-900 p-3 max-h-[300px] overflow-y-auto">
        {content.body?.contentType === 'html' ? (
          // Use iframe for HTML content (fully sandboxed - no allow flags)
          // Trust > cosmetics: styling may degrade but security is absolute
          <iframe
            srcDoc={content.body.content}
            sandbox=""
            className="w-full min-h-[200px] border-0 bg-white"
            title="Email content"
          />
        ) : (
          // Plain text
          <pre className="text-[13px] text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap font-sans">
            {content.body?.content || content.body_preview || '(No content)'}
          </pre>
        )}
      </div>

      {/* Attachments from original */}
      {content.attachments && content.attachments.length > 0 && (
        <div className="mt-2">
          <p className="text-[11px] text-zinc-500 mb-1">
            Attachments ({content.attachments.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {content.attachments.map((att) => (
              <button
                key={att.id}
                onClick={() => onAttachmentClick(
                  providerMessageId,
                  att.id,
                  att.name,
                  att.contentType || 'application/octet-stream'
                )}
                className="inline-flex items-center gap-1 text-[12px] text-zinc-600 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 px-2 py-0.5 rounded transition-colors cursor-pointer"
              >
                <Paperclip className="h-3 w-3" />
                {att.name}
                <span className="text-zinc-400 text-[10px]">
                  ({Math.round(att.size / 1024)}KB)
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default EmailThreadViewer;

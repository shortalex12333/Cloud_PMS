'use client';

/**
 * Email Thread Detail Page - /email/[threadId]
 *
 * Tier 2 fragmented route for viewing a single email thread.
 * Provides full thread view with messages and attachments.
 *
 * @see REQUIREMENTS_TABLE.md - T2-EM-02
 */

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ChevronLeft, X as XIcon, ExternalLink, Wrench, Package, AlertTriangle, FileText, Link2 } from 'lucide-react';
import { LinkEmailModal } from '@/components/email/LinkEmailModal';
import { supabase } from '@/lib/supabaseClient';
import { getEntityRoute } from '@/lib/featureFlags';
import {
  useThread,
  useMessageContent,
  useThreadLinks,
  useMarkThreadRead,
  useRemoveLink,
  type EmailMessage,
  type ThreadLink,
} from '@/hooks/useEmailData';
import { StatusPill } from '@/components/ui/StatusPill';
import { cn } from '@/lib/utils';
import DOMPurify from 'isomorphic-dompurify';

const SANITIZE_CONFIG = {
  ALLOWED_TAGS: [
    'p', 'div', 'span', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'b', 'i', 'u', 's', 'strong', 'em', 'mark', 'small', 'sub', 'sup',
    'a',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption', 'colgroup', 'col',
    'blockquote', 'pre', 'code',
  ],
  ALLOWED_ATTR: [
    'class', 'id', 'style',
    'href', 'target', 'rel',
    'colspan', 'rowspan', 'scope',
  ],
  ADD_ATTR: ['target', 'rel'],
  ALLOW_DATA_ATTR: false,
  FORBID_TAGS: ['script', 'style', 'iframe', 'frame', 'object', 'embed', 'form', 'input', 'button', 'img'],
  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
};

function sanitizeHtml(html: string): string {
  if (!html) return '';
  // DOMPurify sanitizes the content to prevent XSS attacks
  let clean = DOMPurify.sanitize(html, SANITIZE_CONFIG);
  clean = clean.replace(/<a\s+([^>]*?)>/gi, '<a $1 target="_blank" rel="noopener noreferrer">');
  return clean;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-surface-border border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading thread...</p>
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-status-critical/10 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-status-critical">
          <circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">Failed to Load</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">{message}</p>
      <button onClick={onRetry} className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">Try Again</button>
    </div>
  );
}

function NotFoundState() {
  const router = useRouter();
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-surface-elevated flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-tertiary">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
          <polyline points="22,6 12,13 2,6" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">Thread Not Found</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">This email thread may have been deleted or you may not have access.</p>
      <button onClick={() => router.push('/email')} className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">Back to Email</button>
    </div>
  );
}

function MessageCard({ message, isExpanded, onToggle }: { message: EmailMessage; isExpanded: boolean; onToggle: () => void }) {
  const isInbound = message.direction === 'inbound';
  const date = message.received_at || message.sent_at;

  return (
    <div className={cn(
      'border rounded-lg overflow-hidden',
      isInbound ? 'border-surface-border' : 'border-brand-interactive/30 bg-brand-interactive/5'
    )}>
      <button
        onClick={onToggle}
        className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-surface-hover/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium',
            isInbound ? 'bg-surface-elevated text-txt-secondary' : 'bg-brand-interactive/20 text-brand-interactive'
          )}>
            {isInbound ? '←' : '→'}
          </div>
          <div>
            <p className="text-sm font-medium text-txt-primary">{message.from_display_name || 'Unknown'}</p>
            <p className="text-xs text-txt-tertiary">{date ? new Date(date).toLocaleString() : ''}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {message.has_attachments && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-txt-tertiary">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
            </svg>
          )}
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={cn('text-txt-tertiary transition-transform', isExpanded && 'rotate-180')}>
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
      </button>
      {isExpanded && (
        <MessageContentView
          providerMessageId={message.provider_message_id}
          attachments={message.attachments}
        />
      )}
    </div>
  );
}

function MessageContentView({ providerMessageId, attachments }: { providerMessageId: string; attachments?: EmailMessage['attachments'] }) {
  const { data: content, isLoading, error } = useMessageContent(providerMessageId);

  if (isLoading) {
    return (
      <div className="px-4 py-6 border-t border-surface-border">
        <div className="flex items-center gap-2 text-txt-secondary">
          <div className="w-4 h-4 border-2 border-surface-border border-t-txt-primary rounded-full animate-spin" />
          <span className="text-sm">Loading content...</span>
        </div>
      </div>
    );
  }

  if (error || !content) {
    return (
      <div className="px-4 py-6 border-t border-surface-border">
        <p className="text-sm text-status-critical">Failed to load message content</p>
      </div>
    );
  }

  // Sanitize HTML content using DOMPurify to prevent XSS
  const bodyHtml = content.body?.contentType === 'html'
    ? sanitizeHtml(content.body.content)
    : `<pre class="whitespace-pre-wrap">${DOMPurify.sanitize(content.body?.content || '')}</pre>`;

  return (
    <div className="border-t border-surface-border">
      {/* Recipients */}
      <div className="px-4 py-3 bg-surface-elevated/50 text-xs text-txt-tertiary space-y-1">
        {content.to_recipients?.length > 0 && (
          <p>To: {content.to_recipients.map(r => r.emailAddress?.address).filter(Boolean).join(', ')}</p>
        )}
        {content.cc_recipients?.length > 0 && (
          <p>Cc: {content.cc_recipients.map(r => r.emailAddress?.address).filter(Boolean).join(', ')}</p>
        )}
      </div>

      {/* Body - sanitized with DOMPurify */}
      <div
        className="px-4 py-4 prose prose-sm prose-invert max-w-none text-txt-primary [&_a]:text-brand-interactive [&_a:hover]:underline"
        dangerouslySetInnerHTML={{ __html: bodyHtml }}
      />

      {/* Attachments */}
      {(content.attachments?.length > 0 || attachments?.length) && (
        <div className="px-4 py-3 border-t border-surface-border bg-surface-elevated/30">
          <p className="text-xs font-medium text-txt-tertiary uppercase tracking-wider mb-2">Attachments</p>
          <div className="flex flex-wrap gap-2">
            {(content.attachments || attachments || []).map((att) => (
              <div key={att.id} className="flex items-center gap-2 px-3 py-2 bg-surface-elevated rounded-lg text-sm">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-txt-tertiary">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <span className="text-txt-primary truncate max-w-[200px]">{att.name}</span>
                <span className="text-txt-tertiary">{formatFileSize(att.size)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const ENTITY_TABLE_MAP: Record<string, { table: string; select: string; nameField: string; refField: string }> = {
  work_order: { table: 'pms_work_orders', select: 'id,title,wo_number,status', nameField: 'title', refField: 'wo_number' },
  equipment: { table: 'pms_equipment', select: 'id,name,serial_number', nameField: 'name', refField: 'serial_number' },
  fault: { table: 'pms_faults', select: 'id,title,fault_number', nameField: 'title', refField: 'fault_number' },
  part: { table: 'pms_parts', select: 'id,name,part_number', nameField: 'name', refField: 'part_number' },
  purchase_order: { table: 'pms_purchase_orders', select: 'id,title,po_number', nameField: 'title', refField: 'po_number' },
};

const ENTITY_ICONS: Record<string, React.ReactNode> = {
  work_order: <Wrench size={14} />,
  equipment: <Package size={14} />,
  fault: <AlertTriangle size={14} />,
  part: <FileText size={14} />,
};

function LinkedObjectsPanel({ links, threadId, onRefresh }: { links: ThreadLink[]; threadId: string; onRefresh: () => void }) {
  const router = useRouter();
  const removeLink = useRemoveLink();
  const [entityNames, setEntityNames] = React.useState<Record<string, { name: string; ref: string }>>({});

  // Resolve entity names from IDs
  React.useEffect(() => {
    if (links.length === 0) return;
    const resolve = async () => {
      const resolved: Record<string, { name: string; ref: string }> = {};
      for (const link of links) {
        const config = ENTITY_TABLE_MAP[link.object_type];
        if (!config) { resolved[link.object_id] = { name: link.object_id.slice(0, 8), ref: link.object_type }; continue; }
        try {
          const { data } = await supabase.from(config.table).select(config.select).eq('id', link.object_id).maybeSingle();
          if (data) {
            const d = data as Record<string, any>;
            resolved[link.object_id] = { name: d[config.nameField] || link.object_id.slice(0, 8), ref: d[config.refField] || '' };
          } else {
            resolved[link.object_id] = { name: link.object_id.slice(0, 8), ref: 'not found' };
          }
        } catch {
          resolved[link.object_id] = { name: link.object_id.slice(0, 8), ref: '' };
        }
      }
      setEntityNames(resolved);
    };
    resolve();
  }, [links]);

  const handleRemove = async (linkId: string) => {
    try {
      await removeLink.mutateAsync(linkId);
      onRefresh();
    } catch { /* toast handled by hook */ }
  };

  if (links.length === 0) return null;

  return (
    <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-sub)' }}>
      <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--txt3)', marginBottom: 10 }}>
        Linked Objects
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {links.map(link => {
          const entity = entityNames[link.object_id];
          const icon = ENTITY_ICONS[link.object_type] || <Link2 size={14} />;
          return (
            <div
              key={link.id}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 12px', borderRadius: 6,
                background: 'var(--surface-base)',
                border: '1px solid var(--border-sub)',
                minHeight: 44,
              }}
            >
              {/* Icon */}
              <div style={{
                width: 28, height: 28, borderRadius: 6,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: link.confidence === 'deterministic' ? 'var(--green-bg)' : 'var(--teal-bg)',
                color: link.confidence === 'deterministic' ? 'var(--green)' : 'var(--mark)',
                flexShrink: 0,
              }}>
                {icon}
              </div>

              {/* Name + ref */}
              <div style={{ flex: 1, minWidth: 0, cursor: 'pointer' }}
                onClick={() => router.push(getEntityRoute(link.object_type as any, link.object_id))}
              >
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--mark)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {entity?.name || '...'}
                </div>
                <div style={{ fontSize: 10, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', marginTop: 1, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ textTransform: 'uppercase' }}>{link.object_type.replace(/_/g, ' ')}</span>
                  {entity?.ref && <span>{entity.ref}</span>}
                  <span style={{
                    padding: '0 4px', borderRadius: 2, fontSize: 9, fontWeight: 600,
                    background: link.confidence === 'deterministic' ? 'var(--green-bg)' : 'var(--neutral-bg)',
                    color: link.confidence === 'deterministic' ? 'var(--green)' : 'var(--txt3)',
                    border: `1px solid ${link.confidence === 'deterministic' ? 'var(--green-border)' : 'var(--border-sub)'}`,
                    textTransform: 'uppercase',
                  }}>
                    {link.confidence === 'deterministic' ? 'exact' : link.confidence === 'user_confirmed' ? 'confirmed' : 'suggested'}
                  </span>
                </div>
              </div>

              {/* Open in lens */}
              <button
                onClick={() => router.push(getEntityRoute(link.object_type as any, link.object_id))}
                style={{ width: 28, height: 28, borderRadius: 5, border: 'none', background: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--txt-ghost)', flexShrink: 0 }}
                title="Open entity"
              >
                <ExternalLink size={13} />
              </button>

              {/* Remove link */}
              <button
                onClick={() => handleRemove(link.id)}
                style={{ width: 28, height: 28, borderRadius: 5, border: 'none', background: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--txt-ghost)', flexShrink: 0 }}
                title="Remove link"
              >
                <XIcon size={13} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ThreadContent({ threadId }: { threadId: string }) {
  const { data: thread, isLoading, error, refetch } = useThread(threadId);
  const { data: linksData } = useThreadLinks(threadId);
  const markRead = useMarkThreadRead();

  const [expandedMessages, setExpandedMessages] = React.useState<Set<string>>(new Set());
  const [showLinkModal, setShowLinkModal] = React.useState(false);
  const markedReadRef = React.useRef(false);

  // Mark thread as read on mount — once only, via ref (no re-render)
  React.useEffect(() => {
    if (thread && !thread.is_read && !markedReadRef.current) {
      markedReadRef.current = true;
      markRead.mutate(threadId);
    }
  }, [threadId]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleMessage = React.useCallback((messageId: string) => {
    setExpandedMessages(prev => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  }, []);

  if (isLoading) return <LoadingState />;
  if (error) {
    const msg = error instanceof Error ? error.message : 'An error occurred';
    return msg.includes('404') ? <NotFoundState /> : <ErrorState message={msg} onRetry={() => refetch()} />;
  }
  if (!thread) return <NotFoundState />;

  const links = linksData?.links || [];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="p-6 border-b border-surface-border">
        <div className="flex items-center gap-2 mb-2">
          {links.length > 0 ? (
            <StatusPill status="success" label={`${links.length} Linked`} />
          ) : (
            <StatusPill status="neutral" label="Unlinked" />
          )}
          {thread.has_attachments && (
            <StatusPill status="neutral" label="Has Attachments" />
          )}
        </div>
        <h1 className="text-2xl font-semibold text-txt-primary">{thread.latest_subject || '(No subject)'}</h1>
        <p className="text-sm text-txt-tertiary mt-1">
          {thread.message_count} message{thread.message_count !== 1 ? 's' : ''} in this thread
        </p>
      </div>

      {/* Linked objects */}
      <LinkedObjectsPanel links={links} threadId={threadId} onRefresh={() => refetch()} />

      {/* Messages */}
      <div className="p-6 space-y-4">
        {thread.messages.map(message => (
          <MessageCard
            key={message.id}
            message={message}
            isExpanded={expandedMessages.has(message.id)}
            onToggle={() => toggleMessage(message.id)}
          />
        ))}
      </div>

      {/* Actions */}
      <div className="p-6 border-t border-surface-border flex gap-3">
        <button
          onClick={() => setShowLinkModal(true)}
          className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
        >
          Link to Object
        </button>
      </div>

      {/* Link Modal */}
      {showLinkModal && (
        <LinkEmailModal
          open={showLinkModal}
          onOpenChange={(open) => { setShowLinkModal(open); if (!open) refetch(); }}
          threadId={threadId}
          threadSubject={thread.latest_subject || undefined}
        />
      )}
    </div>
  );
}

function EmailThreadDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const threadId = params.threadId as string;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--surface-base)' }}>
      {/* Topbar */}
      <div style={{
        height: 44, display: 'flex', alignItems: 'center', padding: '0 16px',
        borderBottom: '1px solid var(--border-sub)', background: 'var(--surface)', gap: 12,
      }}>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--mark)' }}>Celeste</span>
        <div style={{ flex: 1 }} />
      </div>

      {/* Content */}
      <div style={{ maxWidth: 700, margin: '0 auto', padding: '24px 20px 64px' }}>
        <button
          onClick={() => router.push('/email')}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 12, color: 'var(--txt3)', cursor: 'pointer',
            marginBottom: 20, background: 'none', border: 'none',
            fontFamily: 'var(--font-sans)',
          }}
        >
          <ChevronLeft size={14} /> Back to inbox
        </button>

        <div style={{
          background: 'var(--surface)',
          borderTop: '1px solid rgba(255,255,255,0.09)',
          borderRight: '1px solid rgba(255,255,255,0.05)',
          borderBottom: '1px solid rgba(255,255,255,0.03)',
          borderLeft: '1px solid rgba(255,255,255,0.05)',
          borderRadius: 8, overflow: 'hidden',
          boxShadow: '0 0 0 1px rgba(0,0,0,0.60), 0 28px 80px rgba(0,0,0,0.80)',
        }}>
          <ThreadContent threadId={threadId} />
        </div>
      </div>
    </div>
  );
}

export default function EmailThreadDetailPage() {
  return (
    <React.Suspense fallback={<LoadingState />}>
      <EmailThreadDetailPageContent />
    </React.Suspense>
  );
}

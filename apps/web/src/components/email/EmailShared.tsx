'use client';

/**
 * Shared email components used by both /email (split-pane) and /email/[threadId] (deep link).
 * Extracted to avoid duplication. All styling uses inline styles with design token variables.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  X as XIcon, ExternalLink, Wrench, Package, AlertTriangle, FileText, Link2,
  ChevronDown, Mail, Download,
} from 'lucide-react';
import { LinkEmailModal } from '@/components/email/LinkEmailModal';
import { supabase } from '@/lib/supabaseClient';
import { getEntityRoute } from '@/lib/featureFlags';
import {
  useThread, useMessageContent, useThreadLinks, useMarkThreadRead, useRemoveLink,
  fetchAttachmentBlob,
  type EmailMessage, type ThreadLink,
} from '@/hooks/useEmailData';
import DOMPurify from 'isomorphic-dompurify';

// ============================================================================
// SANITIZE CONFIG
// ============================================================================

const SANITIZE_CONFIG = {
  ALLOWED_TAGS: [
    'p', 'div', 'span', 'br', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'b', 'i', 'u', 's', 'strong', 'em', 'mark', 'small', 'sub', 'sup',
    'a', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption', 'colgroup', 'col',
    'blockquote', 'pre', 'code',
  ],
  ALLOWED_ATTR: ['class', 'id', 'style', 'href', 'target', 'rel', 'colspan', 'rowspan', 'scope'],
  ADD_ATTR: ['target', 'rel'],
  ALLOW_DATA_ATTR: false,
  FORBID_TAGS: ['script', 'style', 'iframe', 'frame', 'object', 'embed', 'form', 'input', 'button', 'img'],
  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
};

function sanitizeHtml(html: string): string {
  if (!html) return '';
  let clean = DOMPurify.sanitize(html, SANITIZE_CONFIG);
  clean = clean.replace(/<a\s+([^>]*?)>/gi, '<a $1 target="_blank" rel="noopener noreferrer">');
  return clean;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getInitials(name: string): string {
  return name.split(/[\s@.]/).filter(Boolean).slice(0, 2).map(w => w[0]?.toUpperCase() || '').join('');
}

function formatRelative(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(diff / 3600000);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(diff / 86400000);
  if (days < 7) return `${days}d`;
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    + ', ' + new Date(dateStr).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

// ============================================================================
// ENTITY RESOLUTION
// ============================================================================

const ENTITY_TABLE_MAP: Record<string, { table: string; select: string; nameField: string; refField: string }> = {
  work_order: { table: 'pms_work_orders', select: 'id,title,wo_number,status', nameField: 'title', refField: 'wo_number' },
  equipment: { table: 'pms_equipment', select: 'id,name,serial_number', nameField: 'name', refField: 'serial_number' },
  fault: { table: 'pms_faults', select: 'id,title,fault_number', nameField: 'title', refField: 'fault_number' },
  part: { table: 'pms_parts', select: 'id,name,part_number', nameField: 'name', refField: 'part_number' },
};

const ENTITY_ICONS: Record<string, React.ReactNode> = {
  work_order: <Wrench size={12} />,
  equipment: <Package size={12} />,
  fault: <AlertTriangle size={12} />,
  part: <FileText size={12} />,
};

// ============================================================================
// LINKED OBJECTS PANEL
// ============================================================================

export function LinkedObjectsSection({ links, threadId, onRefresh }: { links: ThreadLink[]; threadId: string; onRefresh: () => void }) {
  const router = useRouter();
  const removeLink = useRemoveLink();
  const [entityNames, setEntityNames] = useState<Record<string, { name: string; ref: string }>>({});
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
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
    try { await removeLink.mutateAsync(linkId); onRefresh(); } catch { /* handled */ }
  };

  return (
    <>
      <div style={{ borderTop: '1px solid var(--border-sub)', margin: '0 24px' }}>
        <div
          onClick={() => setCollapsed(!collapsed)}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '12px 0', cursor: 'pointer', userSelect: 'none' }}
        >
          <Link2 size={14} style={{ color: 'var(--txt3)', flexShrink: 0 }} />
          <span style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--txt3)', flex: 1 }}>
            Linked Objects
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)' }}>{links.length}</span>
          <button onClick={(e) => { e.stopPropagation(); setShowLinkModal(true); }} style={{ fontSize: 11, fontWeight: 500, color: 'var(--mark)', cursor: 'pointer', background: 'none', border: 'none', fontFamily: 'var(--font-sans)' }}>
            + Link
          </button>
          <ChevronDown size={12} style={{ color: 'var(--txt-ghost)', transition: 'transform 150ms', transform: collapsed ? 'rotate(-90deg)' : 'none' }} />
        </div>
        {!collapsed && (
          <div style={{ paddingBottom: 12 }}>
            {links.map(link => {
              const entity = entityNames[link.object_id];
              const icon = ENTITY_ICONS[link.object_type] || <Link2 size={12} />;
              return (
                <div key={link.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', minHeight: 36 }}>
                  <div style={{ width: 24, height: 24, borderRadius: 5, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, background: 'var(--teal-bg)', color: 'var(--mark)' }}>{icon}</div>
                  <div style={{ flex: 1, minWidth: 0, cursor: 'pointer' }} onClick={() => router.push(getEntityRoute(link.object_type as any, link.object_id))}>
                    <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--mark)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{entity?.name || '...'}</div>
                    <div style={{ fontSize: 9, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', marginTop: 1, display: 'flex', gap: 5, textTransform: 'uppercase' }}>
                      <span>{link.object_type.replace(/_/g, ' ')}</span>
                      {entity?.ref && <span>{entity.ref}</span>}
                      <span style={{ padding: '0 4px', borderRadius: 2, fontSize: 8, fontWeight: 600, background: link.confidence === 'deterministic' ? 'var(--green-bg)' : 'var(--neutral-bg)', color: link.confidence === 'deterministic' ? 'var(--green)' : 'var(--txt3)', border: `1px solid ${link.confidence === 'deterministic' ? 'var(--green-border)' : 'var(--border-sub)'}` }}>
                        {link.confidence === 'deterministic' ? 'EXACT' : link.confidence === 'user_confirmed' ? 'CONFIRMED' : 'SUGGESTED'}
                      </span>
                    </div>
                  </div>
                  <button onClick={() => handleRemove(link.id)} style={{ width: 20, height: 20, borderRadius: 3, border: 'none', background: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--txt-ghost)' }} title="Remove link"><XIcon size={11} /></button>
                </div>
              );
            })}
          </div>
        )}
      </div>
      {showLinkModal && (
        <LinkEmailModal open={showLinkModal} onOpenChange={(open) => { setShowLinkModal(open); if (!open) onRefresh(); }} threadId={threadId} />
      )}
    </>
  );
}

// ============================================================================
// ATTACHMENTS SECTION
// ============================================================================

export function AttachmentsSection({ messages }: { messages: EmailMessage[] }) {
  const allAttachments = messages.flatMap(m =>
    (m.attachments || []).map(a => ({ ...a, providerMessageId: m.provider_message_id }))
  );
  if (allAttachments.length === 0) return null;

  const handleOpen = async (providerMessageId: string, att: any) => {
    try {
      const result = await fetchAttachmentBlob(providerMessageId, att.id);
      const url = URL.createObjectURL(result.blob);
      window.open(url, '_blank');
    } catch { /* silent */ }
  };

  return (
    <div style={{ borderTop: '1px solid var(--border-sub)', margin: '0 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '12px 0' }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--txt3)' }}><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" /></svg>
        <span style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--txt3)', flex: 1 }}>Attachments</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)' }}>{allAttachments.length}</span>
      </div>
      {allAttachments.map((att, i) => {
        const isPdf = att.contentType?.includes('pdf');
        return (
          <div key={att.id || i} style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', minHeight: 44,
            cursor: 'pointer', borderRadius: 5, marginBottom: 4,
            background: 'var(--surface)', border: '1px solid var(--border-sub)',
          }}
            onClick={() => handleOpen(att.providerMessageId, att)}
          >
            <div style={{
              width: 36, height: 36, borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              background: isPdf ? 'rgba(192,80,58,0.1)' : 'var(--neutral-bg)',
            }}>
              <FileText size={16} style={{ color: isPdf ? 'var(--red)' : 'var(--txt3)' }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--txt)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{att.name}</div>
              <div style={{ fontSize: 10, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', marginTop: 1, display: 'flex', gap: 6 }}>
                <span>{isPdf ? 'PDF' : att.contentType?.split('/')[1]?.toUpperCase() || 'FILE'}</span>
                <span>{formatFileSize(att.size)}</span>
              </div>
            </div>
            <button onClick={(e) => { e.stopPropagation(); handleOpen(att.providerMessageId, att); }} style={{ width: 28, height: 28, borderRadius: 4, border: 'none', background: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--txt-ghost)' }} title="Download">
              <Download size={13} />
            </button>
            <button onClick={(e) => { e.stopPropagation(); handleOpen(att.providerMessageId, att); }} style={{ width: 28, height: 28, borderRadius: 4, border: 'none', background: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--txt-ghost)' }} title="Open">
              <ExternalLink size={13} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

// ============================================================================
// MESSAGE CARD
// ============================================================================

export function MessageCard({ message, defaultExpanded = false }: { message: EmailMessage; defaultExpanded?: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const { data: content, isLoading, error } = useMessageContent(expanded ? message.provider_message_id : null);
  const isOutbound = message.direction === 'outbound';
  const date = message.received_at || message.sent_at;

  const bodyHtml = content?.body?.contentType === 'html'
    ? sanitizeHtml(content.body.content)
    : content?.body?.content
      ? `<pre style="white-space:pre-wrap;font-family:var(--font-sans);font-size:13px;color:var(--txt);line-height:1.65;">${DOMPurify.sanitize(content.body.content)}</pre>`
      : '';

  return (
    <div style={{
      borderRadius: 6, overflow: 'hidden', marginBottom: 8,
      background: 'var(--surface)', border: '1px solid var(--border-sub)',
      borderLeft: isOutbound ? '2px solid var(--mark)' : '1px solid var(--border-sub)',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', cursor: 'pointer', minHeight: 44, transition: 'background 60ms' }}
      >
        <div style={{
          width: 28, height: 28, borderRadius: '50%', background: 'var(--teal-bg)', color: 'var(--mark)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, fontWeight: 600, fontFamily: 'var(--font-mono)', flexShrink: 0,
        }}>
          {getInitials(message.from_display_name || 'U')}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt)' }}>{message.from_display_name || 'Unknown'}</div>
          <div style={{ fontSize: 10, color: 'var(--txt-ghost)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>{formatDate(date)}</div>
        </div>
        {message.has_attachments && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--txt3)', flexShrink: 0 }}><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" /></svg>
        )}
        <ChevronDown size={12} style={{ color: 'var(--txt-ghost)', flexShrink: 0, transition: 'transform 150ms', transform: expanded ? 'rotate(180deg)' : 'none' }} />
      </div>

      {expanded && (
        <div style={{ borderTop: '1px solid var(--border-faint)' }}>
          {isLoading ? (
            <div style={{ padding: '16px 12px 16px 50px', fontSize: 12, color: 'var(--txt3)' }}>Loading content...</div>
          ) : error || !content ? (
            <div style={{ padding: '12px 12px 12px 50px', fontSize: 13, color: 'var(--txt)', lineHeight: 1.65, whiteSpace: 'pre-line', maxWidth: 560 }}>
              {'Content unavailable'}
            </div>
          ) : (
            <div style={{ padding: '12px 12px 12px 50px', fontSize: 13, color: 'var(--txt)', lineHeight: 1.65, maxWidth: 560 }} dangerouslySetInnerHTML={{ __html: bodyHtml }} />
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// THREAD DETAIL (right pane content)
// ============================================================================

export function ThreadDetail({ threadId }: { threadId: string }) {
  const { data: thread, isLoading, error, refetch } = useThread(threadId);
  const { data: linksData } = useThreadLinks(threadId);
  const markRead = useMarkThreadRead();
  const markedRef = useRef(false);

  useEffect(() => {
    if (thread && !thread.is_read && !markedRef.current) {
      markedRef.current = true;
      markRead.mutate(threadId);
    }
  }, [threadId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (isLoading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
      <div style={{ width: 20, height: 20, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  if (error) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: 48, textAlign: 'center' }}>
      <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--txt2)', marginBottom: 8 }}>Failed to load thread</div>
      <button onClick={() => refetch()} style={{ fontSize: 12, color: 'var(--mark)', cursor: 'pointer', background: 'none', border: 'none', fontFamily: 'var(--font-sans)' }}>Try again</button>
    </div>
  );

  if (!thread) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: 48, textAlign: 'center' }}>
      <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--txt2)' }}>Thread not found</div>
    </div>
  );

  const links = linksData?.links || [];
  const attCount = thread.messages?.reduce((n: number, m: EmailMessage) => n + (m.attachments?.length || 0), 0) || 0;
  const firstSender = thread.messages?.[0]?.from_display_name || '';

  return (
    <div>
      {/* Identity */}
      <div style={{ padding: '20px 24px 14px' }}>
        <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
          {links.length > 0 && (
            <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', padding: '2px 8px', borderRadius: 3, background: 'var(--green-bg)', color: 'var(--green)', border: '1px solid var(--green-border)' }}>{links.length} Linked</span>
          )}
          {attCount > 0 && (
            <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', padding: '2px 8px', borderRadius: 3, background: 'var(--neutral-bg)', color: 'var(--txt3)', border: '1px solid var(--border-sub)' }}>{attCount} Attachment{attCount !== 1 ? 's' : ''}</span>
          )}
        </div>
        <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--txt)', lineHeight: 1.3, marginBottom: 4 }}>{thread.latest_subject || '(No subject)'}</div>
        <div style={{ fontSize: 12, color: 'var(--txt3)', display: 'flex', alignItems: 'center', gap: 5, flexWrap: 'wrap' }}>
          <span style={{ color: 'var(--mark)', fontWeight: 500 }}>{firstSender}</span>
          <span>·</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{thread.message_count} message{thread.message_count !== 1 ? 's' : ''}</span>
          <span>·</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{formatDate(thread.last_activity_at)}</span>
        </div>
      </div>

      {/* Linked Objects */}
      <LinkedObjectsSection links={links} threadId={threadId} onRefresh={() => refetch()} />

      {/* Attachments */}
      {thread.messages && <AttachmentsSection messages={thread.messages} />}

      {/* Messages */}
      <div style={{ padding: '0 24px 16px' }}>
        <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--txt-ghost)', padding: '12px 0 8px', display: 'flex', alignItems: 'center', gap: 6, borderTop: '1px solid var(--border-sub)' }}>
          <Mail size={14} style={{ color: 'var(--txt3)' }} />
          Messages
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 400 }}>{thread.messages?.length || 0}</span>
        </div>
        {thread.messages?.map((msg: EmailMessage, i: number) => (
          <MessageCard key={msg.id} message={msg} defaultExpanded={i === 0} />
        ))}
      </div>

      {/* Footer */}
      <div style={{ borderTop: '1px solid var(--border-sub)', margin: '0 24px', padding: '14px 0', display: 'flex', gap: 6 }}>
        {thread.messages?.[0]?.web_link && (
          <a href={thread.messages[0].web_link} target="_blank" rel="noopener noreferrer" style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '7px 12px', borderRadius: 6,
            fontSize: 11, fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font-sans)',
            background: 'var(--teal-bg)', color: 'var(--mark)', border: '1px solid rgba(90,171,204,0.2)',
            textDecoration: 'none',
          }}>
            <ExternalLink size={12} /> Open in Outlook
          </a>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// THREAD LIST ROW
// ============================================================================

export function ThreadRow({ thread, isSelected, onClick }: { thread: any; isSelected: boolean; onClick: () => void }) {
  const isUnread = !thread.is_read;
  const sender = thread.messages?.[0]?.from_display_name || thread.latest_subject?.split(' ')[0] || '';

  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '7px 14px', minHeight: 44,
        cursor: 'pointer', transition: 'background 60ms',
        borderTop: '1px solid rgba(255,255,255,0.04)',
        background: isSelected ? 'var(--teal-bg)' : 'transparent',
        position: 'relative',
      }}
    >
      {isUnread && <div style={{ position: 'absolute', left: 0, top: 6, bottom: 6, width: 2, borderRadius: 1, background: 'var(--mark)' }} />}
      <Mail size={14} style={{ color: 'var(--txt3)', flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: isUnread ? 500 : 400, color: 'var(--txt)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', lineHeight: 1.3 }}>
          {thread.latest_subject || '(No subject)'}
        </div>
        <div style={{ fontSize: 10, color: 'var(--txt2)', fontFamily: 'var(--font-mono)', letterSpacing: '0.03em', marginTop: 1, display: 'flex', alignItems: 'center', gap: 4 }}>
          <span>{sender.toUpperCase().slice(0, 20)}</span>
          <span>·</span>
          <span>{thread.message_count}</span>
          {thread.has_attachments && (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--txt3)' }}><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" /></svg>
          )}
        </div>
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', flexShrink: 0 }}>
        {formatRelative(thread.last_activity_at)}
      </span>
    </div>
  );
}

// ============================================================================
// EMPTY STATE
// ============================================================================

export function EmptyDetail() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center', padding: 48 }}>
      <Mail size={40} style={{ color: 'var(--txt-ghost)', marginBottom: 10 }} />
      <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt2)', marginBottom: 4 }}>Select a thread</div>
      <div style={{ fontSize: 11, color: 'var(--txt3)', maxWidth: 220, lineHeight: 1.5 }}>Click an email on the left to view its contents, linked objects, and attachments.</div>
    </div>
  );
}

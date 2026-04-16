'use client';

/**
 * NotificationBell — Topbar notification bell with unread badge and dropdown panel.
 *
 * Polls for unread count every 30 seconds via React Query.
 * Click opens a dropdown showing recent notifications.
 * Click a notification row to navigate to the entity and mark it read.
 * "Mark all read" button at bottom.
 *
 * Styling follows Topbar.tsx patterns: design tokens, 28x28 button, same dropdown surface.
 */

import * as React from 'react';
import { Bell } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { formatRelativeTime } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Notification {
  id: string;
  title: string;
  body: string | null;
  entity_type: string | null;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
}

interface NotificationsResponse {
  status: string;
  data: Notification[];
}

/* ------------------------------------------------------------------ */
/*  Entity route mapping                                               */
/* ------------------------------------------------------------------ */

function getNotificationRoute(entityType: string, entityId: string): string {
  const routes: Record<string, string> = {
    certificate: '/certificates',
    warranty: '/warranties',
    work_order: '/work-orders',
    fault: '/faults',
    equipment: '/equipment',
    document: '/documents',
    handover: '/handover',
    hours_of_rest: '/hours-of-rest',
  };
  const base = routes[entityType] || `/${entityType}`;
  return `${base}?id=${entityId}`;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function NotificationBell() {
  const { session } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  const token = session?.access_token;

  // ---- Fetch notifications ----
  const { data: notifications = [] } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: async () => {
      if (!token) return [];
      const res = await fetch('/api/v1/notifications?unread_only=false&limit=20', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return [];
      const json: NotificationsResponse = await res.json();
      return json.data ?? [];
    },
    enabled: !!token,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  // ---- Close on outside click / Escape ----
  React.useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('mousedown', handleClick);
    window.addEventListener('keydown', handleKey);
    return () => {
      window.removeEventListener('mousedown', handleClick);
      window.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  // ---- Mark one as read ----
  const markRead = React.useCallback(
    async (id: string) => {
      if (!token) return;
      await fetch(`/api/v1/notifications/${id}/read`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` },
      });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
    [token, queryClient],
  );

  // ---- Mark all as read ----
  const markAllRead = React.useCallback(async () => {
    if (!token) return;
    await fetch('/api/v1/notifications/mark-all-read', {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token}` },
    });
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
  }, [token, queryClient]);

  // ---- Click notification row ----
  const handleRowClick = React.useCallback(
    (n: Notification) => {
      if (!n.is_read) markRead(n.id);
      setOpen(false);
      if (n.entity_type && n.entity_id) {
        router.push(getNotificationRoute(n.entity_type, n.entity_id));
      }
    },
    [markRead, router],
  );

  return (
    <div ref={ref} style={{ position: 'relative', flexShrink: 0 }}>
      {/* Bell button */}
      <button
        data-testid="notification-bell"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
        style={{
          width: 28,
          height: 28,
          borderRadius: 4,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          color: open ? 'var(--mark)' : 'var(--txt3)',
          transition: 'background 80ms, color 80ms',
          cursor: 'pointer',
          background: open ? 'var(--teal-bg)' : 'transparent',
          border: 'none',
        }}
        onMouseEnter={(e) => {
          if (!open) {
            e.currentTarget.style.background = 'var(--surface-hover)';
            e.currentTarget.style.color = 'var(--txt2)';
          }
        }}
        onMouseLeave={(e) => {
          if (!open) {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'var(--txt3)';
          }
        }}
      >
        <Bell style={{ width: 14, height: 14 }} />

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: 2,
              right: 2,
              minWidth: 14,
              height: 14,
              borderRadius: 7,
              background: 'var(--red)',
              color: 'white',
              fontSize: 9,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '0 3px',
              lineHeight: 1,
              pointerEvents: 'none',
            }}
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div
          data-testid="notification-dropdown"
          style={{
            position: 'absolute',
            top: 34,
            right: 0,
            width: 320,
            maxHeight: 420,
            background: 'var(--surface-el)',
            borderTop: '1px solid var(--border-top)',
            borderRight: '1px solid var(--border-side)',
            borderBottom: '1px solid var(--border-bottom)',
            borderLeft: '1px solid var(--border-side)',
            borderRadius: 4,
            boxShadow: 'var(--shadow-drop)',
            overflow: 'hidden',
            zIndex: 200,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: '10px 12px',
              borderBottom: '1px solid var(--border-faint)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexShrink: 0,
            }}
          >
            <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--txt)' }}>
              Notifications
            </span>
            {unreadCount > 0 && (
              <span
                style={{
                  fontSize: 9,
                  color: 'var(--txt-ghost)',
                  letterSpacing: '0.04em',
                }}
              >
                {unreadCount} unread
              </span>
            )}
          </div>

          {/* Notification list */}
          <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
            {notifications.length === 0 ? (
              <div
                style={{
                  padding: '24px 12px',
                  textAlign: 'center',
                  fontSize: 12,
                  color: 'var(--txt-ghost)',
                }}
              >
                No notifications
              </div>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => handleRowClick(n)}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 8,
                    width: '100%',
                    padding: '10px 12px',
                    background: 'transparent',
                    border: 'none',
                    borderBottom: '1px solid var(--border-faint)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background 60ms',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--surface-hover)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                  }}
                >
                  {/* Unread dot */}
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: n.is_read ? 'transparent' : 'var(--red)',
                      flexShrink: 0,
                      marginTop: 4,
                    }}
                  />

                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: n.is_read ? 400 : 500,
                        color: 'var(--txt)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {n.title}
                    </div>
                    {n.body && (
                      <div
                        style={{
                          fontSize: 11,
                          color: 'var(--txt2)',
                          marginTop: 2,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {n.body}
                      </div>
                    )}
                    <div
                      style={{
                        fontSize: 10,
                        color: 'var(--txt2)',
                        marginTop: 3,
                      }}
                    >
                      {formatRelativeTime(n.created_at)}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Footer: Mark all read */}
          {unreadCount > 0 && (
            <div
              style={{
                borderTop: '1px solid var(--border-faint)',
                flexShrink: 0,
              }}
            >
              <button
                onClick={markAllRead}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  fontSize: 11,
                  fontWeight: 500,
                  color: 'var(--mark)',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'background 60ms',
                  textAlign: 'center',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--surface-hover)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                }}
              >
                Mark all as read
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

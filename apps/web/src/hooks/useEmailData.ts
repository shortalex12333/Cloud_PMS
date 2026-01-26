/**
 * useEmailData - React Query hooks for Email Transport Layer
 *
 * Provides typed hooks for fetching email-related data:
 * - Related threads for an object
 * - Thread with messages
 * - Message content (fetch-on-click)
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';

// ============================================================================
// TYPES
// ============================================================================

export type LinkConfidence = 'deterministic' | 'suggested' | 'user_confirmed';

export type EmailThread = {
  id: string;
  provider_conversation_id: string;
  latest_subject: string | null;
  message_count: number;
  has_attachments: boolean;
  source: string;
  first_message_at: string | null;
  last_activity_at: string | null;
  // From link join
  link_id?: string;
  confidence?: LinkConfidence;
  suggested_reason?: string;
  accepted?: boolean;
};

export type EmailMessage = {
  id: string;
  provider_message_id: string;
  direction: 'inbound' | 'outbound';
  from_display_name: string | null;
  subject: string | null;
  sent_at: string | null;
  received_at: string | null;
  has_attachments: boolean;
  attachments?: Array<{
    id: string;
    name: string;
    contentType: string;
    size: number;
  }>;
};

export type ThreadWithMessages = EmailThread & {
  messages: EmailMessage[];
};

export type MessageContent = {
  id: string;
  subject: string | null;
  body: {
    contentType: string;
    content: string;
  };
  body_preview: string | null;
  from_address: {
    emailAddress?: {
      name?: string;
      address?: string;
    };
  };
  to_recipients: Array<{
    emailAddress?: {
      name?: string;
      address?: string;
    };
  }>;
  cc_recipients: Array<{
    emailAddress?: {
      name?: string;
      address?: string;
    };
  }>;
  received_at: string | null;
  sent_at: string | null;
  has_attachments: boolean;
  attachments: Array<{
    id: string;
    name: string;
    contentType: string;
    size: number;
  }>;
};

export type RelatedThreadsResponse = {
  threads: EmailThread[];
  count: number;
};

// ============================================================================
// API FUNCTIONS
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

async function getAuthHeaders(): Promise<HeadersInit> {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error('Not authenticated');
  }
  return {
    'Authorization': `Bearer ${session.access_token}`,
    'Content-Type': 'application/json',
  };
}

async function fetchRelatedThreads(
  objectType: string,
  objectId: string
): Promise<RelatedThreadsResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(
    `${API_BASE}/email/related?object_type=${objectType}&object_id=${objectId}`,
    { headers }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to fetch related threads');
  }

  return response.json();
}

async function fetchThread(threadId: string): Promise<ThreadWithMessages> {
  const headers = await getAuthHeaders();
  const response = await fetch(
    `${API_BASE}/email/thread/${threadId}`,
    { headers }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to fetch thread');
  }

  return response.json();
}

async function fetchMessageContent(providerMessageId: string): Promise<MessageContent> {
  const headers = await getAuthHeaders();
  const response = await fetch(
    `${API_BASE}/email/message/${providerMessageId}/render`,
    { headers }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to fetch message content');
  }

  return response.json();
}

async function acceptLink(linkId: string): Promise<{ success: boolean }> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/email/link/accept`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ link_id: linkId }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to accept link');
  }

  return response.json();
}

async function changeLink(
  linkId: string,
  newObjectType: string,
  newObjectId: string
): Promise<{ success: boolean }> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/email/link/change`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      link_id: linkId,
      new_object_type: newObjectType,
      new_object_id: newObjectId,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to change link');
  }

  return response.json();
}

async function removeLink(linkId: string): Promise<{ success: boolean }> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/email/link/remove`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ link_id: linkId }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to remove link');
  }

  return response.json();
}

// ============================================================================
// REACT QUERY HOOKS
// ============================================================================

/**
 * Fetch threads related to an object
 */
export function useRelatedThreads(objectType: string, objectId: string) {
  return useQuery({
    queryKey: ['email', 'related', objectType, objectId],
    queryFn: () => fetchRelatedThreads(objectType, objectId),
    enabled: !!objectType && !!objectId,
    staleTime: 30000, // 30 seconds
    retry: 1,
  });
}

/**
 * Fetch thread with messages
 */
export function useThread(threadId: string | null) {
  return useQuery({
    queryKey: ['email', 'thread', threadId],
    queryFn: () => fetchThread(threadId!),
    enabled: !!threadId,
    staleTime: 30000,
    retry: 1,
  });
}

/**
 * Fetch message content (fetch-on-click)
 */
export function useMessageContent(providerMessageId: string | null) {
  return useQuery({
    queryKey: ['email', 'message', providerMessageId],
    queryFn: () => fetchMessageContent(providerMessageId!),
    enabled: !!providerMessageId,
    staleTime: 60000, // 1 minute - content doesn't change
    retry: 1,
  });
}

/**
 * Accept a suggested link
 */
export function useAcceptLink() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: acceptLink,
    onSuccess: () => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['email', 'related'] });
    },
  });
}

/**
 * Change link target
 */
export function useChangeLink() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ linkId, newObjectType, newObjectId }: {
      linkId: string;
      newObjectType: string;
      newObjectId: string;
    }) => changeLink(linkId, newObjectType, newObjectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email', 'related'] });
    },
  });
}

/**
 * Remove (unlink) a link
 */
export function useRemoveLink() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: removeLink,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email', 'related'] });
    },
  });
}

/**
 * Create a new email-object link
 */
export function useCreateLink() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ threadId, objectType, objectId }: {
      threadId: string;
      objectType: string;
      objectId: string;
    }) => {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/email/link/add`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          thread_id: threadId,
          object_type: objectType,
          object_id: objectId,
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Failed to create link');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email', 'related'] });
      queryClient.invalidateQueries({ queryKey: ['email', 'inbox'] });
    },
  });
}

// ============================================================================
// INBOX THREADS HOOK
// ============================================================================

export type InboxResponse = {
  threads: EmailThread[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
};

/**
 * Fetch inbox threads (optionally unlinked only)
 * @param direction - 'inbound', 'outbound', or undefined for both
 */
export function useInboxThreads(
  page: number = 1,
  linked: boolean = false,
  searchQuery: string = '',
  direction?: 'inbound' | 'outbound'
) {
  return useQuery<InboxResponse>({
    queryKey: ['email', 'inbox', page, linked, searchQuery, direction],
    queryFn: async () => {
      const headers = await getAuthHeaders();
      const params = new URLSearchParams({
        page: String(page),
        linked: String(linked),
      });
      if (searchQuery && searchQuery.length >= 2) {
        params.set('q', searchQuery);
      }
      if (direction) {
        params.set('direction', direction);
      }
      const response = await fetch(
        `${API_BASE}/email/inbox?${params.toString()}`,
        { headers }
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Failed to fetch inbox');
      }

      return response.json();
    },
    staleTime: 30000,
    retry: 1,
  });
}

// ============================================================================
// OBJECT SEARCH HOOK
// ============================================================================

export type SearchResult = {
  type: string;
  id: string;
  label: string;
  status?: string;
};

export type SearchResponse = {
  results: SearchResult[];
};

/**
 * Search for linkable objects (work orders, equipment, parts, etc.)
 */
export function useObjectSearch(
  query: string,
  types: string[] = ['work_order', 'equipment', 'part']
) {
  return useQuery<SearchResponse>({
    queryKey: ['email', 'search-objects', query, types],
    queryFn: async () => {
      const headers = await getAuthHeaders();
      const response = await fetch(
        `${API_BASE}/email/search-objects?q=${encodeURIComponent(query)}&types=${types.join(',')}`,
        { headers }
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Search failed');
      }

      return response.json();
    },
    enabled: query.length >= 2,
    staleTime: 10000,
    retry: 1,
  });
}

// ============================================================================
// FEATURE FLAG CHECK
// ============================================================================

/**
 * Check if email features are enabled
 * Returns a simple boolean based on env var or API check
 */
export function useEmailFeatureEnabled() {
  // For now, check environment variable
  // In production, this could call an API endpoint
  const enabled = process.env.NEXT_PUBLIC_EMAIL_ENABLED === 'true';
  return { enabled, isLoading: false };
}

// ============================================================================
// WATCHER STATUS HOOK
// ============================================================================

export type WatcherStatus = {
  id: string;
  sync_status: 'active' | 'degraded' | 'error';
  last_sync_at: string | null;
  last_sync_error: string | null;
  is_connected: boolean;
};

/**
 * Check email watcher status for the current yacht
 * Used to show degraded mode warnings
 */
export function useWatcherStatus() {
  return useQuery<WatcherStatus | null>({
    queryKey: ['email', 'watcher-status'],
    queryFn: async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.user?.id) {
        return null;
      }

      // Get user's yacht
      const { data: crew } = await supabase
        .from('crew_members')
        .select('yacht_id')
        .eq('user_id', session.user.id)
        .single();

      if (!crew?.yacht_id) {
        return null;
      }

      // Get watcher for this yacht
      const { data: watcher, error } = await supabase
        .from('email_watchers')
        .select('id, sync_status, last_sync_at, last_sync_error')
        .eq('yacht_id', crew.yacht_id)
        .single();

      if (error || !watcher) {
        // No watcher = not connected
        return {
          id: '',
          sync_status: 'error' as const,
          last_sync_at: null,
          last_sync_error: null,
          is_connected: false,
        };
      }

      return {
        ...watcher,
        sync_status: watcher.sync_status as 'active' | 'degraded' | 'error',
        is_connected: true,
      };
    },
    staleTime: 60000, // 1 minute
    retry: 1,
  });
}

// ============================================================================
// ATTACHMENT DOWNLOAD
// ============================================================================

export type DownloadError = {
  code: 'OVERSIZE' | 'DISALLOWED_TYPE' | 'NOT_FOUND' | 'UNKNOWN';
  message: string;
};

/**
 * Download an attachment from an email message.
 * Returns a Blob on success, or throws a DownloadError.
 *
 * Error codes:
 * - OVERSIZE (413): File exceeds size limit
 * - DISALLOWED_TYPE (415): File type not permitted
 * - NOT_FOUND (404): Attachment not found
 * - UNKNOWN: Other errors
 */
export async function downloadAttachment(
  providerMessageId: string,
  attachmentId: string
): Promise<Blob> {
  const headers = await getAuthHeaders();
  const encodedMessageId = encodeURIComponent(providerMessageId);

  const response = await fetch(
    `${API_BASE}/email/message/${encodedMessageId}/attachments/${attachmentId}/download`,
    { headers }
  );

  if (!response.ok) {
    let errorDetail = 'Download failed';
    try {
      const errorData = await response.json();
      errorDetail = errorData.detail || errorDetail;
    } catch {
      // Response may not be JSON
    }

    const error: DownloadError = {
      code: 'UNKNOWN',
      message: errorDetail,
    };

    if (response.status === 413) {
      error.code = 'OVERSIZE';
      error.message = 'File is too large to download (max 50MB)';
    } else if (response.status === 415) {
      error.code = 'DISALLOWED_TYPE';
      error.message = 'This file type is not permitted for download';
    } else if (response.status === 404) {
      error.code = 'NOT_FOUND';
      error.message = 'Attachment not found';
    }

    throw error;
  }

  return response.blob();
}

/**
 * Download attachment and trigger browser save dialog
 */
export async function downloadAndSaveAttachment(
  providerMessageId: string,
  attachmentId: string,
  filename: string
): Promise<{ success: true } | { success: false; error: DownloadError }> {
  try {
    const blob = await downloadAttachment(providerMessageId, attachmentId);

    // Create download link and trigger save
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error as DownloadError,
    };
  }
}

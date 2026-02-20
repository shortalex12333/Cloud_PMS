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
import { getAuthHeaders as getCentralAuthHeaders, handle401, AuthError } from '@/lib/authHelpers';

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
  is_read?: boolean;
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
  web_link?: string | null;  // OWA link for "Open in Outlook"
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
  web_link?: string | null;  // OWA link for "Open in Outlook"
};

export type RelatedThreadsResponse = {
  threads: EmailThread[];
  count: number;
};

// ============================================================================
// API FUNCTIONS
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// Debug logging (only in development or when DEBUG_EMAIL=true)
const DEBUG = process.env.NODE_ENV === 'development' || process.env.NEXT_PUBLIC_DEBUG_EMAIL === 'true';
function debugLog(tag: string, msg: string, data?: unknown) {
  if (DEBUG) {
    console.log(`[EMAIL:${tag}] ${msg}`, data || '');
  }
}

/**
 * Get auth headers using centralized auth helper.
 * Wraps getCentralAuthHeaders with debug logging and Content-Type header.
 */
async function getAuthHeaders(): Promise<HeadersInit> {
  debugLog('AUTH', 'Getting auth headers...');
  try {
    const headers = await getCentralAuthHeaders();
    debugLog('AUTH', 'Auth headers obtained');
    return {
      ...headers,
      'Content-Type': 'application/json',
    };
  } catch (error) {
    debugLog('AUTH', 'Auth failed', error);
    throw error;
  }
}

/**
 * Outlook auth error - thrown when Outlook OAuth needs reconnection.
 * This is distinct from Celeste JWT expiry.
 */
class OutlookAuthError extends Error {
  constructor(
    public code: string,
    message: string
  ) {
    super(message);
    this.name = 'OutlookAuthError';
  }
}

/**
 * Check if a 401 response is an Outlook OAuth error (vs Celeste JWT error).
 * Outlook OAuth errors have a structured detail with error_code starting with 'outlook_'.
 */
async function isOutlookAuthError(response: Response): Promise<{ isOutlook: boolean; code?: string; message?: string }> {
  try {
    const cloned = response.clone();
    const data = await cloned.json();
    // Backend returns structured error: { error_code: "outlook_*", message: "...", requires_outlook_reconnect: true }
    if (data?.error_code?.startsWith('outlook_') || data?.requires_outlook_reconnect) {
      return {
        isOutlook: true,
        code: data.error_code,
        message: data.message || 'Please reconnect your Outlook account',
      };
    }
    // Also handle legacy format where detail is the message
    if (typeof data?.detail === 'object' && data.detail?.error_code?.startsWith('outlook_')) {
      return {
        isOutlook: true,
        code: data.detail.error_code,
        message: data.detail.message || 'Please reconnect your Outlook account',
      };
    }
  } catch {
    // Not JSON or parsing error - treat as regular 401
  }
  return { isOutlook: false };
}

/**
 * Authenticated fetch with 401 retry.
 * If server returns 401:
 * - Check if it's an Outlook OAuth error (requires reconnect, NOT JWT refresh)
 * - Otherwise, refresh Celeste JWT and retry
 */
async function authFetch(url: string, options?: RequestInit): Promise<Response> {
  const makeRequest = async (): Promise<Response> => {
    const headers = await getAuthHeaders();
    return fetch(url, {
      ...options,
      headers: {
        ...headers,
        ...options?.headers,
      },
    });
  };

  const response = await makeRequest();

  // Handle 401 - distinguish Outlook OAuth vs Celeste JWT
  if (response.status === 401) {
    const outlookCheck = await isOutlookAuthError(response);

    if (outlookCheck.isOutlook) {
      // Outlook OAuth issue - don't refresh Celeste JWT, throw specific error
      debugLog('AUTH', `Outlook auth error: ${outlookCheck.code}`);
      throw new OutlookAuthError(
        outlookCheck.code || 'outlook_auth_required',
        outlookCheck.message || 'Please reconnect your Outlook account'
      );
    }

    // Regular 401 - try refreshing Celeste JWT
    debugLog('AUTH', '401 received, attempting token refresh...');
    return handle401(makeRequest);
  }

  return response;
}

async function fetchRelatedThreads(
  objectType: string,
  objectId: string
): Promise<RelatedThreadsResponse> {
  const response = await authFetch(
    `${API_BASE}/email/related?object_type=${objectType}&object_id=${objectId}`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to fetch related threads');
  }

  return response.json();
}

async function fetchThread(threadId: string): Promise<ThreadWithMessages> {
  debugLog('THREAD', `Fetching thread: ${threadId}`);
  const url = `${API_BASE}/email/thread/${threadId}`;
  debugLog('THREAD', `URL: ${url}`);

  const response = await authFetch(url);
  debugLog('THREAD', `Response status: ${response.status}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    debugLog('THREAD', 'Fetch failed', { status: response.status, error });
    throw new Error(error.detail || 'Failed to fetch thread');
  }

  const data = await response.json();
  debugLog('THREAD', `Thread loaded: ${data.messages?.length || 0} messages`);
  return data;
}

async function fetchMessageContent(providerMessageId: string): Promise<MessageContent> {
  debugLog('CONTENT', `Fetching content for: ${providerMessageId.substring(0, 50)}...`);

  // CRITICAL: Encode provider ID - Microsoft IDs contain URL-special chars (+, /, =)
  const encodedId = encodeURIComponent(providerMessageId);
  const url = `${API_BASE}/email/message/${encodedId}/render`;
  debugLog('CONTENT', `URL: ${url.substring(0, 80)}...`);

  const response = await authFetch(url);
  debugLog('CONTENT', `Response status: ${response.status}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    debugLog('CONTENT', 'Fetch failed', { status: response.status, error });
    throw new Error(error.detail || 'Failed to fetch message content');
  }

  const data = await response.json();
  debugLog('CONTENT', `Content loaded: ${data.body?.contentType}, ${data.body?.content?.length || 0} chars`);
  return data;
}

async function acceptLink(linkId: string): Promise<{ success: boolean }> {
  const response = await authFetch(`${API_BASE}/email/link/accept`, {
    method: 'POST',
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
  const response = await authFetch(`${API_BASE}/email/link/change`, {
    method: 'POST',
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
  const response = await authFetch(`${API_BASE}/email/link/remove`, {
    method: 'POST',
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
function useRelatedThreads(objectType: string, objectId: string) {
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
 * Optimized with staleTime and no refetch on window focus for performance
 */
export function useThread(threadId: string | null) {
  debugLog('HOOK:THREAD', `Hook called with threadId: ${threadId || 'null'}, enabled: ${!!threadId}`);
  return useQuery({
    queryKey: ['email', 'thread', threadId],
    queryFn: () => {
      debugLog('HOOK:THREAD', 'Query function executing...');
      return fetchThread(threadId!);
    },
    enabled: !!threadId,
    staleTime: 60000, // 1 minute - threads don't change frequently
    gcTime: 300000, // Keep in cache for 5 minutes
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

/**
 * Mark a thread as read
 */
async function markThreadRead(threadId: string): Promise<{ success: boolean }> {
  debugLog('THREAD', `Marking thread as read: ${threadId}`);
  const url = `${API_BASE}/email/thread/${threadId}/mark-read`;

  const response = await authFetch(url, { method: 'POST' });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to mark thread as read');
  }

  return response.json();
}

/**
 * Hook to mark a thread as read
 * Updates local cache optimistically
 */
export function useMarkThreadRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: markThreadRead,
    onSuccess: (_, threadId) => {
      // Update the thread in cache to reflect read state
      queryClient.setQueryData(['email', 'thread', threadId], (old: ThreadWithMessages | undefined) => {
        if (!old) return old;
        return { ...old, is_read: true };
      });
      // Invalidate inbox to refresh unread indicators
      queryClient.invalidateQueries({ queryKey: ['email', 'inbox'] });
    },
  });
}

/**
 * Fetch message content (fetch-on-click)
 * Optimized with longer cache time - content doesn't change
 */
export function useMessageContent(providerMessageId: string | null) {
  debugLog('HOOK:CONTENT', `Hook called with providerMessageId: ${providerMessageId?.substring(0, 30) || 'null'}..., enabled: ${!!providerMessageId}`);
  return useQuery({
    queryKey: ['email', 'message', providerMessageId],
    queryFn: () => {
      debugLog('HOOK:CONTENT', 'Query function executing...');
      return fetchMessageContent(providerMessageId!);
    },
    enabled: !!providerMessageId,
    staleTime: 120000, // 2 minutes - content doesn't change
    gcTime: 600000, // Keep in cache for 10 minutes
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

/**
 * Accept a suggested link
 */
function useAcceptLink() {
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
function useRemoveLink() {
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
    gcTime: 120000, // Keep in cache for 2 minutes
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

// ============================================================================
// PREFETCH UTILITIES (Performance optimization)
// ============================================================================

/**
 * Prefetch thread and first message content on hover/click
 * Call this on thread row hover to pre-warm the cache
 */
export function usePrefetchThread() {
  const queryClient = useQueryClient();

  return async (threadId: string, firstMessageProviderMessageId?: string) => {
    // Prefetch thread data
    await queryClient.prefetchQuery({
      queryKey: ['email', 'thread', threadId],
      queryFn: () => fetchThread(threadId),
      staleTime: 60000,
    });

    // Prefetch first message content if available
    if (firstMessageProviderMessageId) {
      await queryClient.prefetchQuery({
        queryKey: ['email', 'message', firstMessageProviderMessageId],
        queryFn: () => fetchMessageContent(firstMessageProviderMessageId),
        staleTime: 120000,
      });
    }
  };
}

/**
 * Prefetch message content and attachments in parallel
 * Call this when selecting a message for optimized loading
 */
async function prefetchMessageData(
  queryClient: ReturnType<typeof useQueryClient>,
  providerMessageId: string,
  messageId: string
) {
  const startTime = performance.now();

  // Parallel prefetch of body and attachments
  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: ['email', 'message', providerMessageId],
      queryFn: () => fetchMessageContent(providerMessageId),
      staleTime: 120000,
    }),
    // Attachments are fetched as part of message content, but we can
    // log timing for performance tracking
  ]);

  const elapsed = performance.now() - startTime;
  debugLog('PREFETCH', `Message data prefetched in ${elapsed.toFixed(0)}ms`);
}

// ============================================================================
// EMAIL SEARCH HOOK (Semantic Search via /email/search)
// ============================================================================

export type EmailSearchResult = {
  id: string;
  thread_id: string;
  subject: string | null;
  from_display_name: string | null;
  preview_text: string | null;
  sent_at: string | null;
  has_attachments: boolean;
  similarity_score: number;
  match_reasons: string[];
};

export type EmailSearchResponse = {
  results: EmailSearchResult[];
  count: number;
  query: string;
  parsed: {
    free_text: string;
    operators_count: number;
    filters: Record<string, string>;
    match_reasons: string[];
    warnings: string[];
  };
  extracted_keywords: string[];
  telemetry: {
    total_ms: number;
    search_ms: number;
  };
};

/**
 * Semantic email search using /email/search endpoint
 * Supports operators: from:, to:, subject:, has:attachment, before:, after:
 * Uses hybrid search (vector similarity + entity keywords)
 */
export function useEmailSearch(
  query: string,
  options?: {
    limit?: number;
    direction?: 'inbound' | 'outbound';
  }
) {
  return useQuery<EmailSearchResponse>({
    queryKey: ['email', 'search', query, options?.direction, options?.limit],
    queryFn: async () => {
      const headers = await getAuthHeaders();
      const params = new URLSearchParams({
        q: query,
        limit: String(options?.limit || 20),
      });
      if (options?.direction) {
        params.set('direction', options.direction);
      }

      const response = await fetch(
        `${API_BASE}/email/search?${params.toString()}`,
        { headers }
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Search failed');
      }

      return response.json();
    },
    enabled: query.length >= 2,
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
// BACKFILL / IMPORT HOOK
// ============================================================================

export type BackfillStatus = {
  status: 'idle' | 'running' | 'completed' | 'error';
  progress: number; // 0-100
  totalEmails: number;
  processedEmails: number;
  error: string | null;
  startedAt: string | null;
};

/**
 * Trigger and monitor email backfill/import
 */
function useEmailBackfill() {
  const queryClient = useQueryClient();

  // Check backfill status
  const statusQuery = useQuery<BackfillStatus>({
    queryKey: ['email', 'backfill-status'],
    queryFn: async () => {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/email/worker/status`, { headers });

      if (!response.ok) {
        return {
          status: 'idle' as const,
          progress: 0,
          totalEmails: 0,
          processedEmails: 0,
          error: null,
          startedAt: null,
        };
      }

      const data = await response.json();
      return {
        status: data.status || 'idle',
        progress: data.progress || 0,
        totalEmails: data.total_emails || 0,
        processedEmails: data.processed_emails || 0,
        error: data.error || null,
        startedAt: data.started_at || null,
      };
    },
    staleTime: 5000, // Refresh frequently during import
    refetchInterval: (query) => (query.state.data?.status === 'running' ? 3000 : false),
    retry: 1,
  });

  // Trigger backfill mutation
  const triggerBackfill = useMutation({
    mutationFn: async () => {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/email/worker/backfill`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Failed to start import');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email', 'backfill-status'] });
      queryClient.invalidateQueries({ queryKey: ['email', 'inbox'] });
    },
  });

  return {
    status: statusQuery.data,
    isLoading: statusQuery.isLoading,
    isRunning: statusQuery.data?.status === 'running',
    triggerBackfill: triggerBackfill.mutate,
    isTriggering: triggerBackfill.isPending,
    triggerError: triggerBackfill.error,
    refetchStatus: statusQuery.refetch,
  };
}

// ============================================================================
// THREAD LINKS HOOK (for "See related" vs "Link to")
// ============================================================================

export type ThreadLink = {
  id: string;
  object_type: string;
  object_id: string;
  confidence: number;
  confidence_level: LinkConfidence;
  suggested_reason: string | null;
  accepted: boolean;
  created_at: string;
};

export type ThreadLinksResponse = {
  links: ThreadLink[];
  count: number;
};

/**
 * Fetch links for a specific thread
 * Used for "See related (N)" vs "Link to..." conditional
 */
export function useThreadLinks(threadId: string | null, confidenceThreshold: number = 0.6) {
  return useQuery<ThreadLinksResponse>({
    queryKey: ['email', 'thread-links', threadId],
    queryFn: async () => {
      if (!threadId) return { links: [], count: 0 };

      const headers = await getAuthHeaders();
      const response = await fetch(
        `${API_BASE}/email/thread/${threadId}/links`,
        { headers }
      );

      if (!response.ok) {
        // If endpoint doesn't exist, return empty
        if (response.status === 404) {
          return { links: [], count: 0 };
        }
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Failed to fetch links');
      }

      const data = await response.json();
      // Filter by confidence threshold
      const filteredLinks = (data.links || []).filter(
        (link: ThreadLink) => link.confidence >= confidenceThreshold
      );

      return {
        links: filteredLinks,
        count: filteredLinks.length,
      };
    },
    enabled: !!threadId,
    staleTime: 30000,
    retry: 1,
  });
}

// ============================================================================
// OUTLOOK CONNECTION STATUS HOOK
// ============================================================================

export type OutlookConnectionStatus = {
  isConnected: boolean;
  isExpired: boolean;
  email: string | null;
  expiresAt: string | null;
  error: string | null;
};

/**
 * Check Outlook OAuth connection status
 * Returns connection state and provides reconnect URL generator
 */
export function useOutlookConnection() {
  const queryClient = useQueryClient();

  const statusQuery = useQuery<OutlookConnectionStatus>({
    queryKey: ['email', 'outlook-connection'],
    queryFn: async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        return {
          isConnected: false,
          isExpired: false,
          email: null,
          expiresAt: null,
          error: 'Not authenticated',
        };
      }

      try {
        const response = await fetch('/api/integrations/outlook/status', {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        });

        if (!response.ok) {
          return {
            isConnected: false,
            isExpired: false,
            email: null,
            expiresAt: null,
            error: 'Failed to check status',
          };
        }

        const data = await response.json();

        // Backend returns flat structure: { connected, email, connectedAt }
        // Check if token is expired or expiring soon (within 5 minutes)
        const expiresAt = data.expires_at || data.connectedAt;
        const isExpired = expiresAt
          ? new Date(expiresAt).getTime() < Date.now() + 5 * 60 * 1000
          : false;

        return {
          isConnected: data.connected || false,
          isExpired,
          email: data.email || null,
          expiresAt,
          error: null,
        };
      } catch (err) {
        return {
          isConnected: false,
          isExpired: false,
          email: null,
          expiresAt: null,
          error: err instanceof Error ? err.message : 'Unknown error',
        };
      }
    },
    staleTime: 60000, // 1 minute
    retry: 1,
  });

  // Function to initiate reconnect
  const initiateReconnect = async (): Promise<string | null> => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) {
      return null;
    }

    try {
      const response = await fetch('/api/integrations/outlook/auth-url', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (!response.ok) {
        console.error('Failed to get auth URL');
        return null;
      }

      const data = await response.json();
      return data.url || null;
    } catch (err) {
      console.error('Error getting auth URL:', err);
      return null;
    }
  };

  return {
    ...statusQuery,
    initiateReconnect,
    refetchStatus: () => queryClient.invalidateQueries({ queryKey: ['email', 'outlook-connection'] }),
  };
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
 * Uses backend endpoint which handles MASTER/TENANT DB routing correctly
 */
export function useWatcherStatus() {
  return useQuery<WatcherStatus | null>({
    queryKey: ['email', 'watcher-status'],
    queryFn: async () => {
      try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE}/email/worker/status`, { headers });

        if (!response.ok) {
          // Not connected or error
          return {
            id: '',
            sync_status: 'error' as const,
            last_sync_at: null,
            last_sync_error: null,
            is_connected: false,
          };
        }

        const data = await response.json();

        return {
          id: data.id || '',
          sync_status: (data.sync_status || 'error') as 'active' | 'degraded' | 'error',
          last_sync_at: data.last_sync_at || null,
          last_sync_error: data.last_error || null,
          is_connected: data.connected || false,
        };
      } catch (error) {
        debugLog('WATCHER', 'Error fetching watcher status', error);
        return {
          id: '',
          sync_status: 'error' as const,
          last_sync_at: null,
          last_sync_error: null,
          is_connected: false,
        };
      }
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
async function downloadAttachment(
  providerMessageId: string,
  attachmentId: string
): Promise<Blob> {
  const headers = await getAuthHeaders();
  // CRITICAL: Encode both IDs - Microsoft IDs contain URL-special chars (+, /, =)
  const encodedMessageId = encodeURIComponent(providerMessageId);
  const encodedAttachmentId = encodeURIComponent(attachmentId);

  const response = await fetch(
    `${API_BASE}/email/message/${encodedMessageId}/attachments/${encodedAttachmentId}/download`,
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
 * Fetch attachment blob with metadata for inline viewing
 * Returns blob, contentType, and fileName for DocumentViewerOverlay
 */
export interface AttachmentBlobResult {
  blob: Blob;
  contentType: string;
  fileName: string;
}

export async function fetchAttachmentBlob(
  providerMessageId: string,
  attachmentId: string,
  inline: boolean = true
): Promise<AttachmentBlobResult> {
  const headers = await getAuthHeaders();
  // CRITICAL: Encode both IDs - Microsoft IDs contain URL-special chars (+, /, =)
  const encodedMessageId = encodeURIComponent(providerMessageId);
  const encodedAttachmentId = encodeURIComponent(attachmentId);

  const url = `${API_BASE}/email/message/${encodedMessageId}/attachments/${encodedAttachmentId}/download${inline ? '?inline=1' : ''}`;

  const response = await fetch(url, { headers });

  if (!response.ok) {
    let errorDetail = 'Attachment fetch failed';
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
      error.message = 'File is too large to preview (max 50MB)';
    } else if (response.status === 415) {
      error.code = 'DISALLOWED_TYPE';
      error.message = 'This file type is not permitted';
    } else if (response.status === 404) {
      error.code = 'NOT_FOUND';
      error.message = 'Attachment not found';
    }

    throw error;
  }

  // Extract content type from response
  const contentType = response.headers.get('content-type') || 'application/octet-stream';

  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers.get('content-disposition') || '';
  const filenameMatch = /filename[*]?=["']?(?:UTF-8'')?([^"';\n]+)["']?/i.exec(contentDisposition);
  const fileName = filenameMatch ? decodeURIComponent(filenameMatch[1]) : 'attachment';

  const blob = await response.blob();

  return { blob, contentType, fileName };
}

/**
 * Download attachment and trigger browser save dialog
 */
async function downloadAndSaveAttachment(
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

// ============================================================================
// SAVE ATTACHMENT FOR PREVIEW (with micro-actions support)
// ============================================================================

export type SaveAttachmentResult = {
  success: true;
  document_id: string;
  storage_path: string;
  already_saved?: boolean;
} | {
  success: false;
  error: string;
};

/**
 * Save an email attachment to storage for micro-actions.
 *
 * This persists the attachment to Supabase Storage and creates a
 * doc_yacht_library record, enabling document micro-actions like
 * "Add to Handover" or "Attach to Work Order".
 *
 * SOC-2 compliant:
 * - Yacht-scoped storage path ({yacht_id}/email-attachments/...)
 * - Audit logged
 * - Role-checked server-side
 * - Idempotent (won't duplicate if already saved)
 */
async function saveAttachmentForPreview(
  messageId: string,
  attachmentId: string,
  fileName: string,
  idempotencyKey?: string
): Promise<SaveAttachmentResult> {
  try {
    const headers = await getAuthHeaders();

    const response = await fetch(`${API_BASE}/email/evidence/save-attachment`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message_id: messageId,
        attachment_id: attachmentId,
        file_name: fileName,
        idempotency_key: idempotencyKey || `${messageId}:${attachmentId}`,
      }),
    });

    if (!response.ok) {
      let errorDetail = 'Failed to save attachment';
      try {
        const errorData = await response.json();
        errorDetail = errorData.detail || errorDetail;
      } catch {
        // Response may not be JSON
      }

      // Handle specific error cases
      if (response.status === 403) {
        errorDetail = 'Insufficient permissions to save attachments';
      } else if (response.status === 413) {
        errorDetail = 'File is too large (max 50MB)';
      } else if (response.status === 415) {
        errorDetail = 'This file type is not permitted';
      }

      return { success: false, error: errorDetail };
    }

    const data = await response.json();
    return {
      success: true,
      document_id: data.document_id,
      storage_path: data.storage_path,
      already_saved: data.already_saved,
    };
  } catch (error) {
    console.error('[saveAttachmentForPreview] Error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// ============================================================================
// DOCUMENT LINK/UNLINK API
// ============================================================================

export type DocumentLinkResult = {
  success: true;
  link_id: string;
  already_exists?: boolean;
} | {
  success: false;
  error: string;
};

export type DocumentUnlinkResult = {
  success: true;
  link_id?: string;
  already_unlinked?: boolean;
} | {
  success: false;
  error: string;
};

export type DocumentLink = {
  link_id: string;
  document_id: string;
  object_type: string;
  object_id: string;
  link_reason?: string;
  linked_at?: string;
};

/**
 * Link a document to an object (work order, equipment, handover, etc.)
 */
async function linkDocument(
  documentId: string,
  objectType: string,
  objectId: string,
  linkReason?: string,
  sourceContext?: Record<string, string>
): Promise<DocumentLinkResult> {
  try {
    const headers = await getAuthHeaders();

    const response = await fetch(`${API_BASE}/v1/documents/link`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        document_id: documentId,
        object_type: objectType,
        object_id: objectId,
        link_reason: linkReason || 'manual',
        source_context: sourceContext,
      }),
    });

    if (!response.ok) {
      let errorDetail = 'Failed to link document';
      try {
        const errorData = await response.json();
        errorDetail = errorData.detail || errorDetail;
      } catch {
        // Response may not be JSON
      }
      return { success: false, error: errorDetail };
    }

    const data = await response.json();
    return {
      success: true,
      link_id: data.link_id,
      already_exists: data.already_exists,
    };
  } catch (error) {
    console.error('[linkDocument] Error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Unlink a document from an object
 */
async function unlinkDocument(
  documentId: string,
  objectType: string,
  objectId: string
): Promise<DocumentUnlinkResult> {
  try {
    const headers = await getAuthHeaders();

    const response = await fetch(`${API_BASE}/v1/documents/unlink`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        document_id: documentId,
        object_type: objectType,
        object_id: objectId,
      }),
    });

    if (!response.ok) {
      let errorDetail = 'Failed to unlink document';
      try {
        const errorData = await response.json();
        errorDetail = errorData.detail || errorDetail;
      } catch {
        // Response may not be JSON
      }
      return { success: false, error: errorDetail };
    }

    const data = await response.json();
    return {
      success: true,
      link_id: data.link_id,
      already_unlinked: data.already_unlinked,
    };
  } catch (error) {
    console.error('[unlinkDocument] Error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Get all links for a document
 */
async function getDocumentLinks(documentId: string): Promise<{
  success: boolean;
  links?: DocumentLink[];
  error?: string;
}> {
  try {
    const headers = await getAuthHeaders();

    const response = await fetch(`${API_BASE}/v1/documents/${documentId}/links`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      let errorDetail = 'Failed to get document links';
      try {
        const errorData = await response.json();
        errorDetail = errorData.detail || errorDetail;
      } catch {
        // Response may not be JSON
      }
      return { success: false, error: errorDetail };
    }

    const data = await response.json();
    return {
      success: true,
      links: data.links || [],
    };
  } catch (error) {
    console.error('[getDocumentLinks] Error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

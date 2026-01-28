/**
 * useEmailDataDebug - Debug wrapper for email data hooks
 *
 * FAULT AUDIT - All potential failure points:
 *
 * ============================================================================
 * LAYER 1: AUTH (getAuthHeaders)
 * ============================================================================
 * F1.1 - Session not ready: supabase.auth.getSession() returns null on first render
 * F1.2 - Token expired: access_token exists but is expired
 * F1.3 - Token refresh fails: refresh_token invalid or network error
 * F1.4 - Wrong Supabase project: Token from MASTER, validating against TENANT
 *
 * ============================================================================
 * LAYER 2: THREAD FETCH (fetchThread)
 * ============================================================================
 * F2.1 - threadId null: Query disabled, never fires
 * F2.2 - Thread not found: API returns 404
 * F2.3 - Auth rejected: API returns 401/403
 * F2.4 - Empty messages array: Thread exists but has no messages
 * F2.5 - Messages lack provider_message_id: Field is null/undefined
 *
 * ============================================================================
 * LAYER 3: MESSAGE CONTENT FETCH (fetchMessageContent)
 * ============================================================================
 * F3.1 - providerMessageId null: Query disabled, never fires
 * F3.2 - Provider ID not encoded: URL breaks on +/=/characters
 * F3.3 - Message not found: API returns 404
 * F3.4 - Auth rejected: API returns 401/403
 * F3.5 - Graph API fails: Backend can't reach Microsoft
 * F3.6 - Body is null: response.body is null or undefined
 * F3.7 - Body.content empty: contentType exists but content is ""
 *
 * ============================================================================
 * LAYER 4: AUTO-SELECT (useEffect in EmailSearchView)
 * ============================================================================
 * F4.1 - selectedThread undefined: Thread query still loading
 * F4.2 - messages array empty: Thread has 0 messages
 * F4.3 - provider_message_id null: First message lacks this field
 * F4.4 - Effect doesn't re-run: Dependency array missing threadId
 *
 * ============================================================================
 * LAYER 5: UI RENDER (MessagePanel)
 * ============================================================================
 * F5.1 - contentLoading stuck: Query pending indefinitely
 * F5.2 - content null + no error: Query failed silently
 * F5.3 - HTML sanitized to empty: DOMPurify strips everything
 * F5.4 - CSS overflow clips: Container has max-height
 * F5.5 - contentType mismatch: Not 'html' or 'text', falls through
 * F5.6 - Prose class conflicts: Tailwind prose hides content
 *
 * ============================================================================
 * LAYER 6: REACT QUERY
 * ============================================================================
 * F6.1 - enabled never true: Condition check fails
 * F6.2 - Cache returns stale: Same key, different data expected
 * F6.3 - retry exhausted: All retries failed, no visible error
 * F6.4 - Query key collision: Same key for different messages
 */

import { supabase } from '@/lib/supabaseClient';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// Debug logging with timestamps
function debugLog(layer: string, fault: string, data?: unknown) {
  const timestamp = new Date().toISOString().split('T')[1].slice(0, 12);
  console.log(`[${timestamp}] [EMAIL-DEBUG] [${layer}] ${fault}`, data || '');
}

// Track all faults encountered
export const faultTracker: {
  faults: Array<{ layer: string; fault: string; data: unknown; timestamp: Date }>;
  lastSuccess: { layer: string; timestamp: Date } | null;
} = {
  faults: [],
  lastSuccess: null,
};

function trackFault(layer: string, fault: string, data?: unknown) {
  debugLog(layer, `FAULT: ${fault}`, data);
  faultTracker.faults.push({
    layer,
    fault,
    data,
    timestamp: new Date(),
  });
}

function trackSuccess(layer: string) {
  debugLog(layer, 'SUCCESS');
  faultTracker.lastSuccess = { layer, timestamp: new Date() };
}

/**
 * Debug version of getAuthHeaders with fault tracking
 */
export async function getAuthHeadersDebug(): Promise<{ headers: HeadersInit | null; fault: string | null }> {
  debugLog('AUTH', 'Getting session...');

  try {
    const { data: { session }, error } = await supabase.auth.getSession();

    // F1.1 - Session not ready
    if (!session) {
      trackFault('AUTH', 'F1.1 - Session null (not ready or not logged in)');
      return { headers: null, fault: 'F1.1' };
    }

    // F1.2 - Check if token expired
    if (session.expires_at) {
      const expiresAt = session.expires_at * 1000;
      const now = Date.now();
      const timeLeft = expiresAt - now;

      debugLog('AUTH', `Token expires in ${Math.round(timeLeft / 1000)}s`);

      if (timeLeft < 0) {
        trackFault('AUTH', 'F1.2 - Token expired', { expiresAt: new Date(expiresAt).toISOString() });

        // Try refresh
        debugLog('AUTH', 'Attempting token refresh...');
        const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();

        if (refreshError || !refreshData.session) {
          trackFault('AUTH', 'F1.3 - Token refresh failed', refreshError);
          return { headers: null, fault: 'F1.3' };
        }

        debugLog('AUTH', 'Token refreshed successfully');
        return {
          headers: {
            'Authorization': `Bearer ${refreshData.session.access_token}`,
            'Content-Type': 'application/json',
          },
          fault: null,
        };
      }
    }

    // F1.4 - Check token issuer matches expected project
    try {
      const tokenPayload = JSON.parse(atob(session.access_token.split('.')[1]));
      const issuer = tokenPayload.iss || '';
      const projectRef = issuer.match(/https:\/\/([^.]+)/)?.[1];
      debugLog('AUTH', `Token project: ${projectRef}`, { iss: issuer, aud: tokenPayload.aud });
    } catch {
      debugLog('AUTH', 'Could not decode token for project check');
    }

    trackSuccess('AUTH');
    return {
      headers: {
        'Authorization': `Bearer ${session.access_token}`,
        'Content-Type': 'application/json',
      },
      fault: null,
    };
  } catch (err) {
    trackFault('AUTH', 'Unexpected error', err);
    return { headers: null, fault: 'AUTH_ERROR' };
  }
}

/**
 * Debug version of fetchThread with fault tracking
 */
export async function fetchThreadDebug(threadId: string | null): Promise<{
  data: unknown | null;
  fault: string | null;
  httpStatus: number | null;
}> {
  // F2.1 - threadId null
  if (!threadId) {
    trackFault('THREAD', 'F2.1 - threadId is null');
    return { data: null, fault: 'F2.1', httpStatus: null };
  }

  debugLog('THREAD', `Fetching thread: ${threadId}`);

  const { headers, fault: authFault } = await getAuthHeadersDebug();
  if (authFault) {
    return { data: null, fault: authFault, httpStatus: null };
  }

  try {
    const url = `${API_BASE}/email/thread/${threadId}`;
    debugLog('THREAD', `URL: ${url}`);

    const response = await fetch(url, { headers: headers! });

    debugLog('THREAD', `Response status: ${response.status}`);

    // F2.2 - Thread not found
    if (response.status === 404) {
      trackFault('THREAD', 'F2.2 - Thread not found (404)', { threadId });
      return { data: null, fault: 'F2.2', httpStatus: 404 };
    }

    // F2.3 - Auth rejected
    if (response.status === 401 || response.status === 403) {
      const body = await response.json().catch(() => ({}));
      trackFault('THREAD', 'F2.3 - Auth rejected', { status: response.status, body });
      return { data: null, fault: 'F2.3', httpStatus: response.status };
    }

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      trackFault('THREAD', `Unexpected error: ${response.status}`, body);
      return { data: null, fault: 'THREAD_ERROR', httpStatus: response.status };
    }

    const data = await response.json();

    // F2.4 - Empty messages array
    if (!data.messages || data.messages.length === 0) {
      trackFault('THREAD', 'F2.4 - Thread has no messages', { threadId, messageCount: data.messages?.length });
      return { data, fault: 'F2.4', httpStatus: 200 };
    }

    // F2.5 - Messages lack provider_message_id
    const firstMsg = data.messages[0];
    if (!firstMsg.provider_message_id) {
      trackFault('THREAD', 'F2.5 - First message lacks provider_message_id', {
        messageId: firstMsg.id,
        keys: Object.keys(firstMsg)
      });
      return { data, fault: 'F2.5', httpStatus: 200 };
    }

    debugLog('THREAD', `Thread loaded: ${data.messages.length} messages`);
    trackSuccess('THREAD');
    return { data, fault: null, httpStatus: 200 };

  } catch (err) {
    trackFault('THREAD', 'Network/fetch error', err);
    return { data: null, fault: 'THREAD_NETWORK', httpStatus: null };
  }
}

/**
 * Debug version of fetchMessageContent with fault tracking
 */
export async function fetchMessageContentDebug(providerMessageId: string | null): Promise<{
  data: unknown | null;
  fault: string | null;
  httpStatus: number | null;
}> {
  // F3.1 - providerMessageId null
  if (!providerMessageId) {
    trackFault('CONTENT', 'F3.1 - providerMessageId is null');
    return { data: null, fault: 'F3.1', httpStatus: null };
  }

  debugLog('CONTENT', `Fetching content for: ${providerMessageId.substring(0, 50)}...`);

  const { headers, fault: authFault } = await getAuthHeadersDebug();
  if (authFault) {
    return { data: null, fault: authFault, httpStatus: null };
  }

  try {
    // F3.2 - Provider ID encoding
    const encodedId = encodeURIComponent(providerMessageId);
    const url = `${API_BASE}/email/message/${encodedId}/render`;

    debugLog('CONTENT', `URL: ${url.substring(0, 100)}...`);
    debugLog('CONTENT', `Encoded ID length: ${encodedId.length}, Original: ${providerMessageId.length}`);

    const response = await fetch(url, { headers: headers! });

    debugLog('CONTENT', `Response status: ${response.status}`);

    // F3.3 - Message not found
    if (response.status === 404) {
      trackFault('CONTENT', 'F3.3 - Message not found (404)', { providerMessageId: providerMessageId.substring(0, 50) });
      return { data: null, fault: 'F3.3', httpStatus: 404 };
    }

    // F3.4 - Auth rejected
    if (response.status === 401 || response.status === 403) {
      const body = await response.json().catch(() => ({}));
      trackFault('CONTENT', 'F3.4 - Auth rejected', { status: response.status, body });
      return { data: null, fault: 'F3.4', httpStatus: response.status };
    }

    // F3.5 - Backend error (often Graph API failure)
    if (response.status >= 500) {
      const body = await response.json().catch(() => ({}));
      trackFault('CONTENT', 'F3.5 - Backend error (possible Graph API failure)', { status: response.status, body });
      return { data: null, fault: 'F3.5', httpStatus: response.status };
    }

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      trackFault('CONTENT', `Unexpected error: ${response.status}`, body);
      return { data: null, fault: 'CONTENT_ERROR', httpStatus: response.status };
    }

    const data = await response.json();

    // F3.6 - Body is null
    if (!data.body) {
      trackFault('CONTENT', 'F3.6 - Body is null/undefined', { keys: Object.keys(data) });
      return { data, fault: 'F3.6', httpStatus: 200 };
    }

    // F3.7 - Body.content empty
    if (!data.body.content || data.body.content.trim() === '') {
      trackFault('CONTENT', 'F3.7 - Body.content is empty', {
        contentType: data.body.contentType,
        contentLength: data.body.content?.length,
        hasBodyPreview: !!data.body_preview
      });
      return { data, fault: 'F3.7', httpStatus: 200 };
    }

    debugLog('CONTENT', `Content loaded: ${data.body.contentType}, ${data.body.content.length} chars`);
    trackSuccess('CONTENT');
    return { data, fault: null, httpStatus: 200 };

  } catch (err) {
    trackFault('CONTENT', 'Network/fetch error', err);
    return { data: null, fault: 'CONTENT_NETWORK', httpStatus: null };
  }
}

/**
 * Run full diagnostic flow
 */
export async function runEmailRenderDiagnostic(threadId: string): Promise<{
  success: boolean;
  faults: typeof faultTracker.faults;
  summary: string;
}> {
  // Clear previous faults
  faultTracker.faults = [];
  faultTracker.lastSuccess = null;

  debugLog('DIAGNOSTIC', '=== Starting Email Render Diagnostic ===');
  debugLog('DIAGNOSTIC', `Thread ID: ${threadId}`);

  // Step 1: Fetch thread
  const threadResult = await fetchThreadDebug(threadId);

  if (threadResult.fault && !['F2.4', 'F2.5'].includes(threadResult.fault)) {
    return {
      success: false,
      faults: faultTracker.faults,
      summary: `Thread fetch failed: ${threadResult.fault}`,
    };
  }

  if (!threadResult.data) {
    return {
      success: false,
      faults: faultTracker.faults,
      summary: 'Thread fetch returned no data',
    };
  }

  const thread = threadResult.data as { messages: Array<{ provider_message_id: string }> };

  // Step 2: Get provider_message_id
  const providerMessageId = thread.messages?.[0]?.provider_message_id;

  if (!providerMessageId) {
    return {
      success: false,
      faults: faultTracker.faults,
      summary: 'No provider_message_id in first message',
    };
  }

  // Step 3: Fetch content
  const contentResult = await fetchMessageContentDebug(providerMessageId);

  if (contentResult.fault && !['F3.6', 'F3.7'].includes(contentResult.fault)) {
    return {
      success: false,
      faults: faultTracker.faults,
      summary: `Content fetch failed: ${contentResult.fault}`,
    };
  }

  if (!contentResult.data) {
    return {
      success: false,
      faults: faultTracker.faults,
      summary: 'Content fetch returned no data',
    };
  }

  const content = contentResult.data as { body?: { content?: string; contentType?: string } };

  // Step 4: Validate content
  if (!content.body?.content) {
    return {
      success: false,
      faults: faultTracker.faults,
      summary: 'Content has no body',
    };
  }

  debugLog('DIAGNOSTIC', '=== Diagnostic Complete - SUCCESS ===');
  return {
    success: true,
    faults: faultTracker.faults,
    summary: `Success: ${content.body.contentType}, ${content.body.content.length} chars`,
  };
}

/**
 * Export fault tracker for UI display
 */
export function getFaultSummary(): string {
  if (faultTracker.faults.length === 0) {
    return 'No faults detected';
  }

  return faultTracker.faults
    .map((f) => `[${f.layer}] ${f.fault}`)
    .join('\n');
}

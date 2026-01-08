# API Security Guide

## Overview

Every backend request to CelesteOS **MUST** include:
1. **JWT** (Authorization: Bearer <token>)
2. **Yacht Signature** (X-Yacht-Signature: <hash>)

This document explains how to make secure API calls across all CelesteOS endpoints.

## Quick Start

### ✅ Correct: Use the API Client

```typescript
import { celesteApi } from '@/lib/apiClient';

// GET request
const data = await celesteApi.get('/v1/equipment/list');

// POST request
const result = await celesteApi.post('/v1/work-orders/create', {
  title: 'Fix engine',
  priority: 'high'
});
```

### ❌ Wrong: Direct fetch without auth

```typescript
// DON'T DO THIS - missing JWT + yacht signature
const response = await fetch('https://api.celeste7.ai/search', {
  method: 'POST',
  body: JSON.stringify({ query: 'fault' })
});
```

## API Client Functions

### Standard HTTP Methods

```typescript
import { celesteApi, callCelesteApi } from '@/lib/apiClient';

// GET
const equipment = await celesteApi.get<Equipment[]>('/v1/equipment/list');

// POST
const workOrder = await celesteApi.post<WorkOrder>('/v1/work-orders/create', {
  title: 'Fix',
  priority: 'high'
});

// PATCH
const updated = await celesteApi.patch<WorkOrder>('/v1/work-orders/123', {
  status: 'completed'
});

// DELETE
await celesteApi.delete('/v1/documents/456');

// Custom request
const data = await callCelesteApi<MyType>('/custom-endpoint', {
  method: 'PUT',
  body: JSON.stringify({ foo: 'bar' })
});
```

### Search (Streaming)

```typescript
import { searchWithStream } from '@/lib/apiClient';

const stream = await searchWithStream('fault code E047');

// Read streaming results
const reader = stream?.getReader();
if (reader) {
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // Process chunk
  }
}
```

### Document Viewing

```typescript
import { documentsApi } from '@/lib/apiClient';
import { useSecureDocument } from '@/hooks/useSecureDocument';

// React hook (recommended)
function DocumentViewer({ documentId }: { documentId: string }) {
  const { documentUrl, loading, error } = useSecureDocument(documentId);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return <iframe src={documentUrl} />;
}

// Direct API (advanced)
const blobUrl = await documentsApi.streamDocument('doc-123');
// Use blobUrl in <iframe> or <img>

// Pre-signed URL (for downloads)
const { url, expiresAt } = await documentsApi.getSecureUrl('doc-123', 'cloud');
```

### Integrations (OAuth)

```typescript
import { integrationsApi } from '@/lib/apiClient';

// Microsoft Outlook
const { url } = await integrationsApi.outlook.getAuthUrl();
window.location.href = url; // Redirect to OAuth

const status = await integrationsApi.outlook.getStatus();
// { connected: true, email: 'user@example.com' }

// LinkedIn
const linkedInStatus = await integrationsApi.linkedin.getStatus();
```

## Error Handling

### Auth Errors

```typescript
import { AuthError, CelesteApiError } from '@/lib/apiClient';

try {
  const data = await celesteApi.get('/v1/data');
} catch (error) {
  if (error instanceof AuthError) {
    // User not logged in or token expired
    // AuthContext will handle redirect to login
    console.error('Authentication required:', error.code);
  } else if (error instanceof CelesteApiError) {
    // Backend error (404, 500, etc.)
    console.error('API error:', error.status, error.message);
  } else {
    // Network error
    console.error('Network error:', error);
  }
}
```

### Automatic Token Refresh

The API client automatically handles 401 errors:
1. Detects 401 Unauthorized
2. Refreshes Supabase token
3. Retries request once with new token
4. If refresh fails, throws `AuthError` (triggers logout)

You don't need to handle this manually!

## Advanced Usage

### Custom Auth Headers

If you need to make a request outside the API client:

```typescript
import { getAuthHeaders, getYachtId } from '@/lib/authHelpers';

const yachtId = await getYachtId();
const headers = await getAuthHeaders(yachtId);

// headers contains:
// {
//   Authorization: 'Bearer <jwt>',
//   'X-Yacht-Signature': '<hash>'
// }

const response = await fetch('https://api.celeste7.ai/custom', {
  method: 'POST',
  headers: {
    ...headers,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ data })
});
```

### JWT Management

```typescript
import { getValidJWT, getJWTMetadata, isAuthenticated } from '@/lib/authHelpers';

// Get valid JWT (auto-refreshes if expired)
const jwt = await getValidJWT();

// Check if user is authenticated (non-throwing)
const isLoggedIn = await isAuthenticated();

// Get JWT metadata (for debugging)
const metadata = await getJWTMetadata();
console.log('Token expires at:', new Date(metadata.expiresAt * 1000));
```

### Yacht Signature

```typescript
import { getYachtSignature, getYachtId } from '@/lib/authHelpers';

const yachtId = await getYachtId();
const signature = await getYachtSignature(yachtId);

// signature = sha256(yacht_id + YACHT_SALT)
```

## Security Checklist

### ✅ DO:
- Use `celesteApi.get/post/patch/delete` for all backend calls
- Use `searchWithStream` for search
- Use `documentsApi` or `useSecureDocument` for documents
- Use `getAuthHeaders()` for custom requests
- Handle `AuthError` and `CelesteApiError` properly

### ❌ DON'T:
- Don't call `fetch()` directly to Celeste backend
- Don't store JWT in localStorage or sessionStorage
- Don't log JWT, yacht_signature, or Authorization header
- Don't put JWT in query strings or URLs
- Don't create "temporary insecure shortcuts"
- Don't hardcode yacht IDs or salts

## Common Patterns

### React Query Integration

```typescript
import { useQuery } from '@tanstack/react-query';
import { celesteApi } from '@/lib/apiClient';

function useEquipmentList() {
  return useQuery({
    queryKey: ['equipment', 'list'],
    queryFn: () => celesteApi.get<Equipment[]>('/v1/equipment/list')
  });
}

// Usage
const { data, isLoading, error } = useEquipmentList();
```

### Form Submission

```typescript
import { useMutation } from '@tanstack/react-query';
import { celesteApi } from '@/lib/apiClient';

function useCreateWorkOrder() {
  return useMutation({
    mutationFn: (payload: CreateWorkOrderPayload) =>
      celesteApi.post('/v1/work-orders/create', payload),
    onSuccess: () => {
      // Invalidate queries, show toast, etc.
    }
  });
}

// Usage
const { mutate, isPending } = useCreateWorkOrder();
mutate({ title: 'Fix', priority: 'high' });
```

### Streaming with Error Handling

```typescript
import { searchWithStream, CelesteApiError, AuthError } from '@/lib/apiClient';

async function performSearch(query: string) {
  try {
    const stream = await searchWithStream(query);
    if (!stream) return;

    const reader = stream.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      // Process chunk
    }
  } catch (error) {
    if (error instanceof AuthError) {
      // Token expired during stream
      // Close and reconnect
      console.log('Auth expired, reconnecting...');
      return performSearch(query); // Retry with new token
    } else if (error instanceof CelesteApiError && error.status === 401) {
      // Stream-specific auth error
      console.error('Stream auth failed');
    }
  }
}
```

## Troubleshooting

### "No active session" error
- User is not logged in
- AuthContext will redirect to login page
- Don't try to make API calls before user is authenticated

### "Invalid yacht signature" (403)
- yacht_id is wrong or missing
- YACHT_SALT environment variable not configured
- Backend and frontend salts don't match

### "Token expired" errors
- Should auto-refresh transparently
- If persistent, user needs to log in again
- Check browser dev tools for 401 responses

### Streaming fails mid-search
- Token expired during long-lived stream
- Close stream and reconnect with new token
- Consider limiting stream duration

### CORS errors
- Backend must allow custom headers
- Check `Authorization` and `X-Yacht-Signature` are in CORS allowed headers

## Environment Variables

Required in `.env.local`:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=https://api.celeste7.ai

# Yacht signature salt (must match backend)
NEXT_PUBLIC_YACHT_SALT=your-secret-salt-here

# Supabase (for JWT)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## React Query Configuration

If you want React Query to automatically handle auth errors:

```typescript
import { QueryClient } from '@tanstack/react-query';
import { AuthError } from '@/lib/apiClient';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Don't retry on auth errors
        if (error instanceof AuthError) {
          return false;
        }
        return failureCount < 3;
      },
    },
  },
});
```

## Testing

When writing tests, mock the API client:

```typescript
import { celesteApi } from '@/lib/apiClient';

jest.mock('@/lib/apiClient', () => ({
  celesteApi: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  },
}));

// In test
(celesteApi.get as jest.Mock).mockResolvedValue({ data: 'test' });
```

## Migration Guide

If you have existing code that uses direct `fetch()`:

### Before
```typescript
const response = await fetch('https://api.celeste7.ai/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`, // Manual token
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ query })
});
```

### After
```typescript
import { celesteApi } from '@/lib/apiClient';

const data = await celesteApi.post('/search', { query });
```

## Support

For questions or issues:
1. Check this documentation
2. Review code examples in `/src/lib/apiClient.ts`
3. Check `/src/hooks/useSecureDocument.ts` for document viewing
4. Ask in #frontend-dev Slack channel

// CelesteOS Cloud Backend API
// Main entry point - Hono server

import { serve } from '@hono/node-server';
import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { secureHeaders } from 'hono/secure-headers';
import { timing } from 'hono/timing';

// Routes
import dashboard from './routes/dashboard.js';
import actions from './routes/actions.js';
import predictive from './routes/predictive.js';

// ============================================================================
// APP CONFIGURATION
// ============================================================================

const app = new Hono();

// Global middleware
app.use('*', logger());
app.use('*', timing());
app.use('*', secureHeaders());
app.use('*', cors({
  origin: (origin) => {
    // Allow configured origins
    const allowedOrigins = (process.env.ALLOWED_ORIGINS || '').split(',');
    if (allowedOrigins.includes(origin) || process.env.NODE_ENV === 'development') {
      return origin;
    }
    return null;
  },
  allowMethods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization', 'X-Yacht-Signature', 'X-Service-Key'],
  exposeHeaders: ['X-Request-Id', 'X-Response-Time'],
  credentials: true,
  maxAge: 86400,
}));

// ============================================================================
// HEALTH CHECK
// ============================================================================

app.get('/v1/health', (c) => {
  return c.json({
    status: 'ok',
    service: 'celesteos-api',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});

// ============================================================================
// API ROUTES
// ============================================================================

// Dashboard routes
app.route('/v1/dashboard', dashboard);

// Action router
app.route('/v1/actions', actions);

// Predictive engine
app.route('/v1/predictive', predictive);

// ============================================================================
// SEARCH ENDPOINT (Proxy to search microservice)
// ============================================================================

app.post('/v1/search', async (c) => {
  const searchServiceUrl = process.env.SEARCH_SERVICE_URL || 'http://localhost:3001';

  try {
    const body = await c.req.json();
    const authHeader = c.req.header('Authorization');

    const response = await fetch(`${searchServiceUrl}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return c.json(data, response.status as any);

  } catch (error) {
    console.error('Search proxy error:', error);
    return c.json({
      status: 'error',
      error_code: 'search_unavailable',
      message: 'Search service is temporarily unavailable',
    }, 503);
  }
});

// ============================================================================
// INGESTION ENDPOINTS (for local agent)
// ============================================================================

app.post('/v1/ingest/init', async (c) => {
  const n8nUrl = process.env.N8N_WEBHOOK_URL || 'https://n8n.celeste7.ai/webhook';

  try {
    const body = await c.req.json();
    const yachtSignature = c.req.header('X-Yacht-Signature');

    const response = await fetch(`${n8nUrl}/ingest/init`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(yachtSignature ? { 'X-Yacht-Signature': yachtSignature } : {}),
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return c.json(data, response.status as any);

  } catch (error) {
    console.error('Ingest init error:', error);
    return c.json({
      status: 'error',
      error_code: 'ingest_failed',
      message: 'Failed to initialize upload',
    }, 500);
  }
});

app.patch('/v1/ingest/upload_chunk', async (c) => {
  const n8nUrl = process.env.N8N_WEBHOOK_URL || 'https://n8n.celeste7.ai/webhook';

  try {
    const uploadId = c.req.header('Upload-ID');
    const chunkIndex = c.req.header('Chunk-Index');
    const chunkSha = c.req.header('Chunk-SHA256');
    const yachtSignature = c.req.header('X-Yacht-Signature');
    const body = await c.req.arrayBuffer();

    const response = await fetch(`${n8nUrl}/ingest/chunk`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/octet-stream',
        'Upload-ID': uploadId || '',
        'Chunk-Index': chunkIndex || '',
        'Chunk-SHA256': chunkSha || '',
        ...(yachtSignature ? { 'X-Yacht-Signature': yachtSignature } : {}),
      },
      body: body,
    });

    const data = await response.json();
    return c.json(data, response.status as any);

  } catch (error) {
    console.error('Chunk upload error:', error);
    return c.json({ status: 'error' }, 500);
  }
});

app.post('/v1/ingest/complete', async (c) => {
  const n8nUrl = process.env.N8N_WEBHOOK_URL || 'https://n8n.celeste7.ai/webhook';

  try {
    const body = await c.req.json();
    const yachtSignature = c.req.header('X-Yacht-Signature');

    const response = await fetch(`${n8nUrl}/ingest/complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(yachtSignature ? { 'X-Yacht-Signature': yachtSignature } : {}),
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return c.json(data, response.status as any);

  } catch (error) {
    console.error('Ingest complete error:', error);
    return c.json({
      status: 'error',
      error_code: 'ingest_failed',
      message: 'Failed to complete upload',
    }, 500);
  }
});

// ============================================================================
// NOTES ENDPOINT
// ============================================================================

app.post('/v1/notes/create', async (c) => {
  // This is handled by the action router, but we provide a direct endpoint for compatibility
  const body = await c.req.json();

  // Transform to action format
  const actionBody = {
    action: 'add_note',
    context: {
      yacht_id: body.yacht_id,
      equipment_id: body.equipment_id,
    },
    payload: {
      note_text: body.note_text,
    },
  };

  // Forward to actions endpoint
  const newReq = new Request(c.req.url.replace('/notes/create', '/actions/execute'), {
    method: 'POST',
    headers: c.req.raw.headers,
    body: JSON.stringify(actionBody),
  });

  return app.fetch(newReq, c.env);
});

// ============================================================================
// WORK ORDER ENDPOINTS
// ============================================================================

app.post('/v1/work-orders/create', async (c) => {
  const body = await c.req.json();

  const actionBody = {
    action: 'create_work_order',
    context: {
      yacht_id: body.yacht_id,
      equipment_id: body.equipment_id,
    },
    payload: {
      title: body.title,
      description: body.description,
      priority: body.priority,
    },
  };

  const newReq = new Request(c.req.url.replace('/work-orders/create', '/actions/execute'), {
    method: 'POST',
    headers: c.req.raw.headers,
    body: JSON.stringify(actionBody),
  });

  return app.fetch(newReq, c.env);
});

app.post('/v1/work-orders/add-note', async (c) => {
  const body = await c.req.json();

  const actionBody = {
    action: 'add_note_to_work_order',
    context: {
      yacht_id: body.yacht_id,
      work_order_id: body.work_order_id,
    },
    payload: {
      note_text: body.note_text,
    },
  };

  const newReq = new Request(c.req.url.replace('/work-orders/add-note', '/actions/execute'), {
    method: 'POST',
    headers: c.req.raw.headers,
    body: JSON.stringify(actionBody),
  });

  return app.fetch(newReq, c.env);
});

app.post('/v1/work-orders/close', async (c) => {
  const body = await c.req.json();

  const actionBody = {
    action: 'close_work_order',
    context: {
      yacht_id: body.yacht_id,
      work_order_id: body.work_order_id,
    },
    payload: {},
  };

  const newReq = new Request(c.req.url.replace('/work-orders/close', '/actions/execute'), {
    method: 'POST',
    headers: c.req.raw.headers,
    body: JSON.stringify(actionBody),
  });

  return app.fetch(newReq, c.env);
});

// ============================================================================
// HANDOVER ENDPOINTS
// ============================================================================

app.post('/v1/handover/add-item', async (c) => {
  const body = await c.req.json();

  const actionBody = {
    action: 'add_to_handover',
    context: {
      yacht_id: body.yacht_id,
      equipment_id: body.equipment_id,
    },
    payload: {
      summary_text: body.summary_text,
    },
  };

  const newReq = new Request(c.req.url.replace('/handover/add-item', '/actions/execute'), {
    method: 'POST',
    headers: c.req.raw.headers,
    body: JSON.stringify(actionBody),
  });

  return app.fetch(newReq, c.env);
});

app.post('/v1/handover/add-document', async (c) => {
  const body = await c.req.json();

  const actionBody = {
    action: 'add_document_to_handover',
    context: {
      yacht_id: body.yacht_id,
      document_id: body.document_id,
    },
    payload: {
      context: body.context,
    },
  };

  const newReq = new Request(c.req.url.replace('/handover/add-document', '/actions/execute'), {
    method: 'POST',
    headers: c.req.raw.headers,
    body: JSON.stringify(actionBody),
  });

  return app.fetch(newReq, c.env);
});

app.post('/v1/handover/add-predictive', async (c) => {
  const body = await c.req.json();

  const actionBody = {
    action: 'add_predictive_to_handover',
    context: {
      yacht_id: body.yacht_id,
      equipment_id: body.equipment_id,
    },
    payload: {
      insight_id: body.insight_id,
      summary: body.summary,
    },
  };

  const newReq = new Request(c.req.url.replace('/handover/add-predictive', '/actions/execute'), {
    method: 'POST',
    headers: c.req.raw.headers,
    body: JSON.stringify(actionBody),
  });

  return app.fetch(newReq, c.env);
});

app.post('/v1/handover/export', async (c) => {
  const body = await c.req.json();

  const actionBody = {
    action: 'export_handover',
    context: {
      yacht_id: body.yacht_id,
    },
    payload: {
      format: body.format || 'pdf',
    },
  };

  const newReq = new Request(c.req.url.replace('/handover/export', '/actions/execute'), {
    method: 'POST',
    headers: c.req.raw.headers,
    body: JSON.stringify(actionBody),
  });

  return app.fetch(newReq, c.env);
});

// ============================================================================
// DOCUMENT ENDPOINTS
// ============================================================================

app.post('/v1/documents/open', async (c) => {
  const body = await c.req.json();

  const actionBody = {
    action: 'open_document',
    context: {
      yacht_id: body.yacht_id,
    },
    payload: {
      storage_path: body.storage_path,
    },
  };

  const newReq = new Request(c.req.url.replace('/documents/open', '/actions/execute'), {
    method: 'POST',
    headers: c.req.raw.headers,
    body: JSON.stringify(actionBody),
  });

  return app.fetch(newReq, c.env);
});

// ============================================================================
// INVENTORY ENDPOINTS
// ============================================================================

app.post('/v1/inventory/order-part', async (c) => {
  const body = await c.req.json();

  const actionBody = {
    action: 'order_part',
    context: {
      yacht_id: body.yacht_id,
    },
    payload: {
      part_id: body.part_id,
      qty: body.qty,
    },
  };

  const newReq = new Request(c.req.url.replace('/inventory/order-part', '/actions/execute'), {
    method: 'POST',
    headers: c.req.raw.headers,
    body: JSON.stringify(actionBody),
  });

  return app.fetch(newReq, c.env);
});

// ============================================================================
// 404 HANDLER
// ============================================================================

app.notFound((c) => {
  return c.json({
    status: 'error',
    error_code: 'not_found',
    message: `Route not found: ${c.req.method} ${c.req.path}`,
  }, 404);
});

// ============================================================================
// ERROR HANDLER
// ============================================================================

app.onError((err, c) => {
  console.error('Unhandled error:', err);
  return c.json({
    status: 'error',
    error_code: 'internal_error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Internal server error',
  }, 500);
});

// ============================================================================
// START SERVER
// ============================================================================

const port = parseInt(process.env.PORT || '3000');

console.log(`🚀 CelesteOS API starting on port ${port}`);

serve({
  fetch: app.fetch,
  port,
});

export default app;

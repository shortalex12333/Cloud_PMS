// CelesteOS Action Routes
// POST /v1/actions/execute - Single endpoint for all mutations

import { Hono } from 'hono';
import type { Context } from 'hono';
import { authMiddleware, yachtIsolationMiddleware, createError } from '../middleware/auth.js';
import { ActionRouterService } from '../services/action-router.js';
import { genericActionRequestSchema } from '../schemas/index.js';

const actions = new Hono();

// Apply middleware
actions.use('*', authMiddleware);
actions.use('*', yachtIsolationMiddleware);

// ============================================================================
// POST /v1/actions/execute
// ============================================================================

actions.post('/execute', async (c: Context) => {
  const auth = c.get('auth');
  const supabase = c.get('supabase');

  try {
    const body = await c.req.json();

    // Validate basic structure
    const parseResult = genericActionRequestSchema.safeParse(body);
    if (!parseResult.success) {
      return createError('schema_invalid', parseResult.error.message, 400);
    }

    const { action, context, payload } = parseResult.data;

    // Inject yacht_id if not provided
    const enrichedContext = {
      ...context,
      yacht_id: context.yacht_id || auth.yacht_id,
    };

    // Create action router and execute
    const router = new ActionRouterService(supabase, auth.user, auth.yacht_id);
    const result = await router.execute(action, enrichedContext, payload || {});

    if (result.status === 'error') {
      const statusCode = result.error_code === 'forbidden' ? 403 :
                        result.error_code === 'not_found' ? 404 :
                        result.error_code === 'schema_invalid' ? 400 : 500;
      return c.json(result, statusCode);
    }

    return c.json(result);

  } catch (error) {
    console.error('Action execute error:', error);
    return createError('internal_error', 'Failed to execute action', 500);
  }
});

export default actions;

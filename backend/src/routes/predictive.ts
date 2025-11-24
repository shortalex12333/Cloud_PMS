// CelesteOS Predictive Routes
// GET /v1/predictive/state
// GET /v1/predictive/insight

import { Hono } from 'hono';
import type { Context } from 'hono';
import { authMiddleware, yachtIsolationMiddleware, serviceAuthMiddleware, createError } from '../middleware/auth.js';
import type { PredictiveStateResponse, PredictiveInsightResponse } from '../types/index.js';

const predictive = new Hono();

// ============================================================================
// PUBLIC ROUTES (require auth)
// ============================================================================

// Apply middleware to public routes
predictive.use('/state', authMiddleware);
predictive.use('/state', yachtIsolationMiddleware);
predictive.use('/insight', authMiddleware);
predictive.use('/insight', yachtIsolationMiddleware);
predictive.use('/insights', authMiddleware);
predictive.use('/insights', yachtIsolationMiddleware);

// GET /v1/predictive/state?equipment_id=<uuid>
predictive.get('/state', async (c: Context) => {
  const auth = c.get('auth');
  const supabase = c.get('supabase');
  const equipmentId = c.req.query('equipment_id');

  if (!equipmentId) {
    return createError('missing_field', 'equipment_id is required', 400);
  }

  try {
    const { data, error } = await supabase
      .from('predictive_state')
      .select(`
        *,
        equipment:equipment_id (name, system_type)
      `)
      .eq('yacht_id', auth.yacht_id)
      .eq('equipment_id', equipmentId)
      .single();

    if (error || !data) {
      // Return default state if not calculated yet
      const { data: equipment } = await supabase
        .from('equipment')
        .select('name')
        .eq('id', equipmentId)
        .single();

      return c.json({
        equipment_id: equipmentId,
        equipment_name: equipment?.name || 'Unknown',
        risk_score: 0,
        risk_level: 'normal',
        trend: 'stable',
        confidence: 0,
        contributing_factors: {
          fault_signal: 0,
          work_order_signal: 0,
          notes_signal: 0,
          corrective_signal: 0,
          criticality_signal: 0,
          fault_count: 0,
          overdue_count: 0,
          note_count: 0,
          corrective_count: 0,
        },
        last_calculated_at: null,
      } as PredictiveStateResponse);
    }

    return c.json({
      equipment_id: data.equipment_id,
      equipment_name: data.equipment?.name || 'Unknown',
      risk_score: data.risk_score,
      risk_level: data.risk_level,
      trend: data.trend || 'stable',
      confidence: data.confidence,
      contributing_factors: data.contributing_factors,
      last_calculated_at: data.last_calculated_at,
    } as PredictiveStateResponse);

  } catch (error) {
    console.error('Predictive state error:', error);
    return createError('internal_error', 'Failed to get predictive state', 500);
  }
});

// GET /v1/predictive/insight?id=<uuid>
predictive.get('/insight', async (c: Context) => {
  const auth = c.get('auth');
  const supabase = c.get('supabase');
  const insightId = c.req.query('id');

  if (!insightId) {
    return createError('missing_field', 'id is required', 400);
  }

  try {
    const { data, error } = await supabase
      .from('predictive_insights')
      .select(`
        *,
        equipment:equipment_id (name)
      `)
      .eq('yacht_id', auth.yacht_id)
      .eq('id', insightId)
      .single();

    if (error || !data) {
      return createError('not_found', 'Insight not found', 404);
    }

    return c.json({
      id: data.id,
      insight_type: data.insight_type,
      title: data.title,
      description: data.description,
      recommendation: data.recommendation,
      severity: data.severity,
      equipment_id: data.equipment_id,
      equipment_name: data.equipment?.name,
      acknowledged: data.acknowledged,
      created_at: data.created_at,
    } as PredictiveInsightResponse);

  } catch (error) {
    console.error('Predictive insight error:', error);
    return createError('internal_error', 'Failed to get insight', 500);
  }
});

// GET /v1/predictive/insights - List all active insights
predictive.get('/insights', async (c: Context) => {
  const auth = c.get('auth');
  const supabase = c.get('supabase');
  const limit = parseInt(c.req.query('limit') || '20');
  const offset = parseInt(c.req.query('offset') || '0');
  const includeAcknowledged = c.req.query('include_acknowledged') === 'true';

  try {
    let query = supabase
      .from('predictive_insights')
      .select(`
        *,
        equipment:equipment_id (name)
      `, { count: 'exact' })
      .eq('yacht_id', auth.yacht_id)
      .eq('dismissed', false)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (!includeAcknowledged) {
      query = query.eq('acknowledged', false);
    }

    const { data, count, error } = await query;

    if (error) {
      throw error;
    }

    return c.json({
      insights: (data || []).map(d => ({
        id: d.id,
        insight_type: d.insight_type,
        title: d.title,
        description: d.description,
        recommendation: d.recommendation,
        severity: d.severity,
        equipment_id: d.equipment_id,
        equipment_name: d.equipment?.name,
        acknowledged: d.acknowledged,
        created_at: d.created_at,
      })),
      total: count || 0,
      limit,
      offset,
    });

  } catch (error) {
    console.error('Predictive insights list error:', error);
    return createError('internal_error', 'Failed to list insights', 500);
  }
});

// POST /v1/predictive/insight/:id/acknowledge
predictive.post('/insight/:id/acknowledge', authMiddleware, yachtIsolationMiddleware, async (c: Context) => {
  const auth = c.get('auth');
  const supabase = c.get('supabase');
  const insightId = c.req.param('id');

  try {
    const { error } = await supabase
      .from('predictive_insights')
      .update({
        acknowledged: true,
        acknowledged_by: auth.user.id,
        acknowledged_at: new Date().toISOString(),
      })
      .eq('id', insightId)
      .eq('yacht_id', auth.yacht_id);

    if (error) {
      throw error;
    }

    return c.json({ status: 'success', acknowledged: true });

  } catch (error) {
    console.error('Acknowledge insight error:', error);
    return createError('internal_error', 'Failed to acknowledge insight', 500);
  }
});

// POST /v1/predictive/insight/:id/dismiss
predictive.post('/insight/:id/dismiss', authMiddleware, yachtIsolationMiddleware, async (c: Context) => {
  const auth = c.get('auth');
  const supabase = c.get('supabase');
  const insightId = c.req.param('id');

  try {
    const { error } = await supabase
      .from('predictive_insights')
      .update({
        dismissed: true,
        dismissed_at: new Date().toISOString(),
      })
      .eq('id', insightId)
      .eq('yacht_id', auth.yacht_id);

    if (error) {
      throw error;
    }

    return c.json({ status: 'success', dismissed: true });

  } catch (error) {
    console.error('Dismiss insight error:', error);
    return createError('internal_error', 'Failed to dismiss insight', 500);
  }
});

// ============================================================================
// INTERNAL ROUTES (for n8n workflows)
// ============================================================================

// POST /internal/predictive/recompute-all - Trigger full recompute
predictive.post('/internal/recompute-all', serviceAuthMiddleware, async (c: Context) => {
  const supabase = c.get('supabase');
  const body = await c.req.json().catch(() => ({}));
  const yachtId = body.yacht_id;

  try {
    // Get all equipment for the yacht
    const { data: equipment } = await supabase
      .from('equipment')
      .select('id, yacht_id')
      .eq(yachtId ? 'yacht_id' : 'id', yachtId || 'id')
      .is('yacht_id', yachtId ? yachtId : null);

    const n8nUrl = process.env.N8N_WEBHOOK_URL || 'https://n8n.celeste7.ai/webhook';

    // Trigger recompute for each
    const results = await Promise.allSettled(
      (equipment || []).map(e =>
        fetch(`${n8nUrl}/internal/predictive-recompute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            equipment_id: e.id,
            yacht_id: e.yacht_id,
            event: 'manual_recompute',
          }),
        })
      )
    );

    const succeeded = results.filter(r => r.status === 'fulfilled').length;
    const failed = results.filter(r => r.status === 'rejected').length;

    return c.json({
      status: 'success',
      total: equipment?.length || 0,
      succeeded,
      failed,
    });

  } catch (error) {
    console.error('Recompute all error:', error);
    return createError('internal_error', 'Failed to trigger recompute', 500);
  }
});

export default predictive;

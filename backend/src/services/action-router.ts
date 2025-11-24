// CelesteOS Action Router Service
// Single gatekeeper for all user-triggered mutations

import { SupabaseClient } from '@supabase/supabase-js';
import type {
  ActionExecuteResponse,
  ActionLogEntry,
  User,
} from '../types/index.js';

// ============================================================================
// ACTION REGISTRY
// ============================================================================

interface ActionDefinition {
  endpoint: string;  // 'internal:<handler>' or 'n8n:<workflow>'
  roles: string[];
  requires: string[];
}

const ACTION_REGISTRY: Record<string, ActionDefinition> = {
  // Notes
  add_note: {
    endpoint: 'internal:add_note',
    roles: ['Engineer', 'HOD', 'Chief_Engineer', 'Captain', 'Admin'],
    requires: ['equipment_id', 'note_text'],
  },

  // Work Orders
  create_work_order: {
    endpoint: 'n8n:create_work_order',
    roles: ['Engineer', 'HOD', 'Chief_Engineer', 'Admin'],
    requires: ['equipment_id', 'title'],
  },
  add_note_to_work_order: {
    endpoint: 'internal:add_work_order_note',
    roles: ['Engineer', 'HOD', 'Chief_Engineer', 'Admin'],
    requires: ['work_order_id', 'note_text'],
  },
  close_work_order: {
    endpoint: 'n8n:close_work_order',
    roles: ['Engineer', 'HOD', 'Chief_Engineer', 'Admin'],
    requires: ['work_order_id'],
  },

  // Handover
  add_to_handover: {
    endpoint: 'internal:add_equipment_to_handover',
    roles: ['Engineer', 'HOD', 'Chief_Engineer', 'Admin'],
    requires: ['equipment_id', 'summary_text'],
  },
  add_document_to_handover: {
    endpoint: 'n8n:add_document_to_handover',
    roles: ['Engineer', 'HOD', 'Chief_Engineer', 'Admin'],
    requires: ['document_id'],
  },
  add_predictive_to_handover: {
    endpoint: 'internal:add_predictive_to_handover',
    roles: ['Engineer', 'HOD', 'Chief_Engineer', 'Admin'],
    requires: ['equipment_id', 'insight_id', 'summary'],
  },
  edit_handover_section: {
    endpoint: 'internal:edit_handover_section',
    roles: ['HOD', 'Chief_Engineer', 'Admin'],
    requires: ['handover_id', 'section_name', 'new_text'],
  },
  export_handover: {
    endpoint: 'n8n:export_handover',
    roles: ['HOD', 'Chief_Engineer', 'Admin'],
    requires: [],
  },

  // Documents
  open_document: {
    endpoint: 'internal:open_document',
    roles: ['Engineer', 'HOD', 'Chief_Engineer', 'ETO', 'Admin'],
    requires: ['storage_path'],
  },

  // Inventory
  order_part: {
    endpoint: 'n8n:order_part',
    roles: ['Engineer', 'HOD', 'Chief_Engineer', 'Admin'],
    requires: ['part_id', 'qty'],
  },
};

// ============================================================================
// ACTION ROUTER SERVICE
// ============================================================================

export class ActionRouterService {
  private supabase: SupabaseClient;
  private user: User;
  private yachtId: string;
  private n8nWebhookUrl: string;

  constructor(supabase: SupabaseClient, user: User, yachtId: string) {
    this.supabase = supabase;
    this.user = user;
    this.yachtId = yachtId;
    this.n8nWebhookUrl = process.env.N8N_WEBHOOK_URL || 'https://n8n.celeste7.ai/webhook';
  }

  async execute(
    action: string,
    context: Record<string, unknown>,
    payload: Record<string, unknown>
  ): Promise<ActionExecuteResponse> {
    const startTime = Date.now();
    let logEntry: Partial<ActionLogEntry> = {
      yacht_id: this.yachtId,
      user_id: this.user.id,
      action_name: action,
      action_status: 'pending',
      request_payload: { context, payload },
      started_at: new Date().toISOString(),
    };

    try {
      // Step 1: Validate action exists
      const actionDef = ACTION_REGISTRY[action];
      if (!actionDef) {
        throw new ActionError('invalid_action', `Unknown action: ${action}`);
      }

      // Step 2: Validate role
      const userRole = this.user.role.toLowerCase();
      const allowedRoles = actionDef.roles.map(r => r.toLowerCase());
      if (!allowedRoles.includes(userRole) && userRole !== 'admin') {
        throw new ActionError(
          'forbidden',
          `User role '${this.user.role}' cannot perform '${action}'`
        );
      }

      // Step 3: Validate yacht isolation
      const contextYachtId = context.yacht_id as string;
      if (contextYachtId && contextYachtId !== this.yachtId) {
        throw new ActionError('yacht_mismatch', 'Cannot perform actions on another yacht');
      }

      // Step 4: Validate required fields
      const combinedData = { ...context, ...payload };
      for (const field of actionDef.requires) {
        if (combinedData[field] === undefined || combinedData[field] === null) {
          throw new ActionError('missing_field', `Missing required field: ${field}`);
        }
      }

      // Step 5: Dispatch to handler
      let result: Record<string, unknown>;

      if (actionDef.endpoint.startsWith('internal:')) {
        const handler = actionDef.endpoint.replace('internal:', '');
        result = await this.dispatchInternal(handler, context, payload);
      } else {
        const workflow = actionDef.endpoint.replace('n8n:', '');
        result = await this.dispatchToN8n(workflow, context, payload);
      }

      // Step 6: Log success
      logEntry = {
        ...logEntry,
        action_status: 'completed',
        response_payload: result,
        completed_at: new Date().toISOString(),
        duration_ms: Date.now() - startTime,
      };
      await this.logAction(logEntry);

      return {
        status: 'success',
        action,
        result,
      };

    } catch (error) {
      // Log failure
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const errorCode = error instanceof ActionError ? error.code : 'internal_error';

      logEntry = {
        ...logEntry,
        action_status: 'failed',
        error_code: errorCode,
        error_message: errorMessage,
        completed_at: new Date().toISOString(),
        duration_ms: Date.now() - startTime,
      };
      await this.logAction(logEntry);

      return {
        status: 'error',
        action,
        error: errorMessage,
        error_code: errorCode,
      };
    }
  }

  // ============================================================================
  // INTERNAL HANDLERS
  // ============================================================================

  private async dispatchInternal(
    handler: string,
    context: Record<string, unknown>,
    payload: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    switch (handler) {
      case 'add_note':
        return this.handleAddNote(context, payload);

      case 'add_work_order_note':
        return this.handleAddWorkOrderNote(context, payload);

      case 'add_equipment_to_handover':
        return this.handleAddEquipmentToHandover(context, payload);

      case 'add_predictive_to_handover':
        return this.handleAddPredictiveToHandover(context, payload);

      case 'edit_handover_section':
        return this.handleEditHandoverSection(context, payload);

      case 'open_document':
        return this.handleOpenDocument(payload);

      default:
        throw new ActionError('internal_error', `Unknown internal handler: ${handler}`);
    }
  }

  private async handleAddNote(
    context: Record<string, unknown>,
    payload: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const { data, error } = await this.supabase
      .from('notes')
      .insert({
        yacht_id: this.yachtId,
        equipment_id: context.equipment_id,
        user_id: this.user.id,
        note_text: payload.note_text,
      })
      .select('id')
      .single();

    if (error) throw new ActionError('workflow_failed', error.message);

    // Trigger predictive recompute
    await this.triggerPredictiveEvent('note_added', context.equipment_id as string);

    return { note_id: data.id };
  }

  private async handleAddWorkOrderNote(
    context: Record<string, unknown>,
    payload: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    // Get work order to find equipment_id
    const { data: wo } = await this.supabase
      .from('work_orders')
      .select('equipment_id')
      .eq('id', context.work_order_id)
      .eq('yacht_id', this.yachtId)
      .single();

    const { data, error } = await this.supabase
      .from('work_order_history')
      .insert({
        yacht_id: this.yachtId,
        work_order_id: context.work_order_id,
        equipment_id: wo?.equipment_id,
        completed_by: this.user.id,
        notes: payload.note_text,
        status_on_completion: 'note_added',
      })
      .select('id')
      .single();

    if (error) throw new ActionError('workflow_failed', error.message);

    return { note_id: data.id };
  }

  private async handleAddEquipmentToHandover(
    context: Record<string, unknown>,
    payload: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    // Get or create active handover draft
    let { data: draft } = await this.supabase
      .from('handover_drafts')
      .select('id')
      .eq('yacht_id', this.yachtId)
      .eq('status', 'draft')
      .order('created_at', { ascending: false })
      .limit(1)
      .single();

    if (!draft) {
      const { data: newDraft, error: draftError } = await this.supabase
        .from('handover_drafts')
        .insert({
          yacht_id: this.yachtId,
          title: `Handover - ${new Date().toISOString().split('T')[0]}`,
          created_by: this.user.id,
          status: 'draft',
        })
        .select('id')
        .single();

      if (draftError) throw new ActionError('workflow_failed', draftError.message);
      draft = newDraft;
    }

    const { data, error } = await this.supabase
      .from('handover_items')
      .insert({
        yacht_id: this.yachtId,
        handover_id: draft.id,
        source_type: 'equipment',
        source_id: context.equipment_id,
        equipment_id: context.equipment_id,
        summary: payload.summary_text,
      })
      .select('id')
      .single();

    if (error) throw new ActionError('workflow_failed', error.message);

    return { handover_item_id: data.id };
  }

  private async handleAddPredictiveToHandover(
    context: Record<string, unknown>,
    payload: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    // Get or create active handover draft
    let { data: draft } = await this.supabase
      .from('handover_drafts')
      .select('id')
      .eq('yacht_id', this.yachtId)
      .eq('status', 'draft')
      .order('created_at', { ascending: false })
      .limit(1)
      .single();

    if (!draft) {
      const { data: newDraft, error: draftError } = await this.supabase
        .from('handover_drafts')
        .insert({
          yacht_id: this.yachtId,
          title: `Handover - ${new Date().toISOString().split('T')[0]}`,
          created_by: this.user.id,
          status: 'draft',
        })
        .select('id')
        .single();

      if (draftError) throw new ActionError('workflow_failed', draftError.message);
      draft = newDraft;
    }

    const { data, error } = await this.supabase
      .from('handover_items')
      .insert({
        yacht_id: this.yachtId,
        handover_id: draft.id,
        source_type: 'predictive',
        source_id: payload.insight_id,
        equipment_id: context.equipment_id,
        summary: payload.summary,
        importance: 'high',
      })
      .select('id')
      .single();

    if (error) throw new ActionError('workflow_failed', error.message);

    // Mark insight as acknowledged
    await this.supabase
      .from('predictive_insights')
      .update({
        acknowledged: true,
        acknowledged_by: this.user.id,
        acknowledged_at: new Date().toISOString(),
      })
      .eq('id', payload.insight_id);

    return { handover_item_id: data.id };
  }

  private async handleEditHandoverSection(
    context: Record<string, unknown>,
    payload: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    // This would update a specific section of the handover
    // For MVP, we store section edits as items
    const { data, error } = await this.supabase
      .from('handover_items')
      .upsert({
        yacht_id: this.yachtId,
        handover_id: context.handover_id,
        source_type: 'section',
        summary: payload.section_name as string,
        detail: payload.new_text,
      })
      .select('id')
      .single();

    if (error) throw new ActionError('workflow_failed', error.message);

    return { item_id: data.id };
  }

  private async handleOpenDocument(
    payload: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const storagePath = payload.storage_path as string;

    const { data, error } = await this.supabase.storage
      .from('documents')
      .createSignedUrl(storagePath, 3600); // 1 hour expiry

    if (error) throw new ActionError('workflow_failed', error.message);

    return { url: data.signedUrl };
  }

  // ============================================================================
  // N8N DISPATCHER
  // ============================================================================

  private async dispatchToN8n(
    workflow: string,
    context: Record<string, unknown>,
    payload: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    const url = `${this.n8nWebhookUrl}/${workflow}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Service-Key': process.env.INTERNAL_SERVICE_KEY || '',
      },
      body: JSON.stringify({
        yacht_id: this.yachtId,
        user_id: this.user.id,
        ...context,
        ...payload,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ActionError('workflow_failed', `n8n workflow failed: ${errorText}`);
    }

    return await response.json();
  }

  // ============================================================================
  // PREDICTIVE EVENT TRIGGER
  // ============================================================================

  private async triggerPredictiveEvent(event: string, equipmentId: string): Promise<void> {
    try {
      const url = `${this.n8nWebhookUrl}/internal/predictive-event`;

      await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Service-Key': process.env.INTERNAL_SERVICE_KEY || '',
        },
        body: JSON.stringify({
          event,
          equipment_id: equipmentId,
          yacht_id: this.yachtId,
        }),
      });
    } catch (err) {
      // Log but don't fail the action
      console.error('Failed to trigger predictive event:', err);
    }
  }

  // ============================================================================
  // ACTION LOGGING
  // ============================================================================

  private async logAction(entry: Partial<ActionLogEntry>): Promise<void> {
    try {
      await this.supabase.from('action_logs').insert(entry);
    } catch (err) {
      console.error('Failed to log action:', err);
    }
  }
}

// ============================================================================
// ACTION ERROR CLASS
// ============================================================================

export class ActionError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'ActionError';
  }
}

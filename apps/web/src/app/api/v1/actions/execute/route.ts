/**
 * Action Router - Unified Action Execution Endpoint
 *
 * Endpoint: POST /v1/actions/execute
 *
 * Handles all domain-agnostic actions across the application.
 * Frontend calls this endpoint with action name and payload.
 * Backend determines available actions based on user role (RBAC).
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

interface ActionResponse {
  success: boolean;
  data?: any;
  message?: string;
  error?: string;
  code?: string;
}

// User-scoped client (RLS enforced via user token)
function getUserClient(accessToken: string) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Supabase environment variables not configured');
  }

  return createClient(supabaseUrl, supabaseAnonKey, {
    global: {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  });
}

// Service role client (bypasses RLS for lookups, use with caution)
function getServiceClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceKey) {
    throw new Error('Supabase service role not configured');
  }

  return createClient(supabaseUrl, serviceKey);
}

// Get user's yacht_id from auth_role_assignments
async function getUserYachtId(userId: string): Promise<string | null> {
  const serviceClient = getServiceClient();
  const { data } = await serviceClient
    .from('auth_role_assignments')
    .select('yacht_id')
    .eq('user_id', userId)
    .eq('is_active', true)
    .single();
  return data?.yacht_id || null;
}

export async function POST(request: NextRequest): Promise<NextResponse<ActionResponse>> {
  try {
    const { action, context, payload } = await request.json();

    if (!action) {
      return NextResponse.json(
        { success: false, error: 'Missing action parameter', code: 'MISSING_REQUIRED_FIELD' },
        { status: 400 }
      );
    }

    // Extract JWT from Authorization header
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { success: false, error: 'Missing or invalid Authorization header', code: 'UNAUTHORIZED' },
        { status: 401 }
      );
    }

    const accessToken = authHeader.replace('Bearer ', '');

    // Create clients - user client for auth, service client for lookups
    const userClient = getUserClient(accessToken);
    const supabase = getServiceClient(); // Use service role for data operations

    // Verify the token and get user
    const { data: { user }, error: authError } = await userClient.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { success: false, error: 'Invalid or expired token', code: 'UNAUTHORIZED' },
        { status: 401 }
      );
    }

    // Get user's yacht_id for tenant isolation
    const userYachtId = await getUserYachtId(user.id);
    if (!userYachtId) {
      return NextResponse.json(
        { success: false, error: 'User not assigned to any yacht', code: 'NO_YACHT_ASSIGNMENT' },
        { status: 403 }
      );
    }

    const enrichedContext = { ...context, user_id: user.id, yacht_id: userYachtId };

    // ===== INVENTORY ACTIONS =====
    if (action === 'check_part_stock') {
      const { part_id } = payload;
      if (!part_id) {
        return NextResponse.json(
          { success: false, error: 'Missing part_id', code: 'MISSING_REQUIRED_FIELD' },
          { status: 400 }
        );
      }

      const { data, error } = await supabase
        .from('pms_parts')
        .select('part_id, part_name, on_hand, min_quantity, unit_cost, location, bin')
        .eq('part_id', part_id)
        .eq('yacht_id', enrichedContext.yacht_id)
        .single();

      if (error) {
        return NextResponse.json(
          { success: false, error: error.message, code: 'DATABASE_ERROR' },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        data: {
          ...data,
          low_stock: data.on_hand < data.min_quantity,
          out_of_stock: data.on_hand === 0,
        },
        message: `Current stock: ${data.on_hand} ${data.part_name}`,
      });
    }

    if (action === 'view_part_details') {
      const { part_id } = payload;
      if (!part_id) {
        return NextResponse.json(
          { success: false, error: 'Missing part_id', code: 'MISSING_REQUIRED_FIELD' },
          { status: 400 }
        );
      }

      const { data, error } = await supabase
        .from('pms_parts')
        .select('*')
        .eq('part_id', part_id)
        .eq('yacht_id', enrichedContext.yacht_id)
        .single();

      if (error) {
        return NextResponse.json(
          { success: false, error: error.message, code: 'DATABASE_ERROR' },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        data,
        message: `Part details for ${data.part_name}`,
      });
    }

    if (action === 'view_part_usage_history') {
      const { part_id } = payload;
      if (!part_id) {
        return NextResponse.json(
          { success: false, error: 'Missing part_id', code: 'MISSING_REQUIRED_FIELD' },
          { status: 400 }
        );
      }

      const { data, error } = await supabase
        .from('pms_part_usage_log')
        .select('*')
        .eq('part_id', part_id)
        .eq('yacht_id', enrichedContext.yacht_id)
        .order('logged_at', { ascending: false })
        .limit(50);

      if (error && error.code !== '42P01') {
        return NextResponse.json(
          { success: false, error: error.message, code: 'DATABASE_ERROR' },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        data: data || [],
        message: `Found ${data?.length || 0} usage records`,
      });
    }

    if (action === 'log_part_usage') {
      const { part_id, quantity, usage_reason, notes, work_order_id } = payload;

      if (!part_id || !quantity || !usage_reason) {
        return NextResponse.json(
          { success: false, error: 'Missing required fields', code: 'MISSING_REQUIRED_FIELD' },
          { status: 400 }
        );
      }

      if (quantity <= 0) {
        return NextResponse.json(
          { success: false, error: 'Quantity must be greater than 0', code: 'VALIDATION_ERROR' },
          { status: 400 }
        );
      }

      // RBAC check - get user role from bootstrap
      const { data: bootstrap, error: bootstrapError } = await supabase.rpc('get_my_bootstrap');

      if (bootstrapError || !bootstrap) {
        return NextResponse.json(
          { success: false, error: 'Failed to get user permissions', code: 'PERMISSION_ERROR' },
          { status: 500 }
        );
      }

      const allowedRoles = ['chief_engineer', 'captain', 'fleet_manager', 'hod'];
      if (!allowedRoles.includes(bootstrap.role.toLowerCase())) {
        return NextResponse.json(
          { success: false, error: 'Permission denied: Insufficient privileges', code: 'FORBIDDEN' },
          { status: 403 }
        );
      }

      // Stock check
      const { data: partData, error: partError } = await supabase
        .from('pms_parts')
        .select('on_hand, part_name')
        .eq('part_id', part_id)
        .eq('yacht_id', enrichedContext.yacht_id)
        .single();

      if (partError) {
        return NextResponse.json(
          { success: false, error: 'Part not found', code: 'NOT_FOUND' },
          { status: 404 }
        );
      }

      if (partData.on_hand < quantity) {
        return NextResponse.json(
          { success: false, error: `Insufficient stock: Available ${partData.on_hand}, Requested ${quantity}`, code: 'INSUFFICIENT_STOCK' },
          { status: 400 }
        );
      }

      // Log usage
      await supabase
        .from('pms_part_usage_log')
        .insert({
          part_id,
          yacht_id: enrichedContext.yacht_id,
          quantity,
          usage_reason,
          notes,
          work_order_id,
          logged_by: user.id,
          logged_at: new Date().toISOString(),
        });

      // Update stock
      const { error: updateError } = await supabase
        .from('pms_parts')
        .update({ on_hand: partData.on_hand - quantity })
        .eq('part_id', part_id)
        .eq('yacht_id', enrichedContext.yacht_id);

      if (updateError) {
        return NextResponse.json(
          { success: false, error: 'Failed to update stock', code: 'DATABASE_ERROR' },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        data: {
          part_id,
          part_name: partData.part_name,
          quantity_used: quantity,
          new_stock: partData.on_hand - quantity,
          usage_reason,
        },
        message: `Part usage logged: ${quantity} ${partData.part_name} consumed`,
      });
    }

    // ===== WORK ORDER ACTIONS =====

    if (action === 'add_work_order_note') {
      const { work_order_id } = enrichedContext;
      const { note_text, note_type = 'general' } = payload;

      if (!work_order_id) {
        return NextResponse.json(
          { success: false, error: 'Missing work_order_id in context', code: 'MISSING_REQUIRED_FIELD' },
          { status: 400 }
        );
      }

      if (!note_text || note_text.trim() === '') {
        return NextResponse.json(
          { success: false, error: 'Note text is required', code: 'MISSING_REQUIRED_FIELD' },
          { status: 400 }
        );
      }

      // Verify work order exists
      const { data: workOrder, error: woError } = await supabase
        .from('pms_work_orders')
        .select('id, title, yacht_id')
        .eq('id', work_order_id)
        .single();

      if (woError || !workOrder) {
        return NextResponse.json(
          { success: false, error: 'Work order not found', code: 'NOT_FOUND' },
          { status: 404 }
        );
      }

      // Validate user has access to this work order's yacht
      if (workOrder.yacht_id !== userYachtId) {
        console.error('[Action Router] Yacht mismatch:', { workOrderYacht: workOrder.yacht_id, userYacht: userYachtId });
        return NextResponse.json(
          { success: false, error: 'Access denied - work order belongs to different yacht', code: 'ACCESS_DENIED' },
          { status: 403 }
        );
      }

      // Insert note
      const { data: note, error: insertError } = await supabase
        .from('pms_work_order_notes')
        .insert({
          work_order_id,
          note_text: note_text.trim(),
          note_type,
          created_by: user.id,
          created_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (insertError) {
        console.error('[Action Router] Insert note error:', insertError);
        return NextResponse.json(
          { success: false, error: 'Failed to add note', code: 'DATABASE_ERROR' },
          { status: 500 }
        );
      }

      // Create audit log entry
      await supabase.from('pms_audit_log').insert({
        yacht_id: workOrder.yacht_id,
        action: 'add_work_order_note',
        entity_type: 'work_order_note',
        entity_id: note.id,
        user_id: user.id,
        actor_id: user.id,
        new_values: { note_text, note_type, work_order_id },
        created_at: new Date().toISOString(),
      });

      return NextResponse.json({
        success: true,
        data: note,
        message: 'Note added to work order',
      });
    }

    if (action === 'add_parts_to_work_order') {
      const { work_order_id } = enrichedContext;
      const { part_id, quantity = 1, notes } = payload;

      if (!work_order_id) {
        return NextResponse.json(
          { success: false, error: 'Missing work_order_id in context', code: 'MISSING_REQUIRED_FIELD' },
          { status: 400 }
        );
      }

      if (!part_id) {
        return NextResponse.json(
          { success: false, error: 'Missing part_id', code: 'MISSING_REQUIRED_FIELD' },
          { status: 400 }
        );
      }

      if (quantity <= 0) {
        return NextResponse.json(
          { success: false, error: 'Quantity must be greater than 0', code: 'VALIDATION_ERROR' },
          { status: 400 }
        );
      }

      // Verify work order exists
      const { data: workOrder, error: woError } = await supabase
        .from('pms_work_orders')
        .select('id, title, yacht_id')
        .eq('id', work_order_id)
        .single();

      if (woError || !workOrder) {
        return NextResponse.json(
          { success: false, error: 'Work order not found or access denied', code: 'NOT_FOUND' },
          { status: 404 }
        );
      }

      // Verify part exists
      const { data: part, error: partError } = await supabase
        .from('pms_parts')
        .select('part_id, part_name, on_hand')
        .eq('part_id', part_id)
        .single();

      if (partError || !part) {
        return NextResponse.json(
          { success: false, error: 'Part not found', code: 'NOT_FOUND' },
          { status: 404 }
        );
      }

      // Insert work order part link
      const { data: woPart, error: insertError } = await supabase
        .from('pms_work_order_parts')
        .insert({
          work_order_id,
          part_id,
          quantity,
          notes: notes || null,
          created_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (insertError) {
        console.error('[Action Router] Insert part link error:', insertError);
        return NextResponse.json(
          { success: false, error: 'Failed to link part to work order', code: 'DATABASE_ERROR' },
          { status: 500 }
        );
      }

      // Create audit log entry
      await supabase.from('pms_audit_log').insert({
        yacht_id: workOrder.yacht_id,
        action: 'add_parts_to_work_order',
        entity_type: 'work_order_part',
        entity_id: woPart.id,
        user_id: user.id,
        actor_id: user.id,
        new_values: { part_id, part_name: part.part_name, quantity, work_order_id },
        created_at: new Date().toISOString(),
      });

      return NextResponse.json({
        success: true,
        data: { ...woPart, part_name: part.part_name },
        message: `Added ${quantity}x ${part.part_name} to work order`,
      });
    }

    if (action === 'add_checklist_note' || action === 'add_checklist_item') {
      const { work_order_id, yacht_id } = enrichedContext;
      const { title, description, is_required = true } = payload;

      if (!work_order_id) {
        return NextResponse.json(
          { success: false, error: 'Missing work_order_id in context', code: 'MISSING_REQUIRED_FIELD' },
          { status: 400 }
        );
      }

      if (!title || title.trim() === '') {
        return NextResponse.json(
          { success: false, error: 'Checklist item title is required', code: 'MISSING_REQUIRED_FIELD' },
          { status: 400 }
        );
      }

      // Verify work order exists
      const { data: workOrder, error: woError } = await supabase
        .from('pms_work_orders')
        .select('id, title, yacht_id')
        .eq('id', work_order_id)
        .single();

      if (woError || !workOrder) {
        return NextResponse.json(
          { success: false, error: 'Work order not found', code: 'NOT_FOUND' },
          { status: 404 }
        );
      }

      // Validate user has access to this work order's yacht
      if (workOrder.yacht_id !== userYachtId) {
        console.error('[Action Router] Yacht mismatch:', { workOrderYacht: workOrder.yacht_id, userYacht: userYachtId });
        return NextResponse.json(
          { success: false, error: 'Access denied - work order belongs to different yacht', code: 'ACCESS_DENIED' },
          { status: 403 }
        );
      }

      // Get next sequence number
      const { data: existingItems } = await supabase
        .from('pms_work_order_checklist')
        .select('sequence')
        .eq('work_order_id', work_order_id)
        .order('sequence', { ascending: false })
        .limit(1);

      const nextSequence = (existingItems?.[0]?.sequence || 0) + 1;

      // Insert checklist item
      const { data: checklistItem, error: insertError } = await supabase
        .from('pms_work_order_checklist')
        .insert({
          yacht_id: workOrder.yacht_id,
          work_order_id,
          title: title.trim(),
          description: description || null,
          sequence: nextSequence,
          is_completed: false,
          is_required,
          requires_photo: false,
          requires_signature: false,
          created_by: user.id,
          created_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (insertError) {
        console.error('[Action Router] Insert checklist item error:', insertError);
        return NextResponse.json(
          { success: false, error: 'Failed to add checklist item', code: 'DATABASE_ERROR' },
          { status: 500 }
        );
      }

      // Create audit log entry
      await supabase.from('pms_audit_log').insert({
        yacht_id: workOrder.yacht_id,
        action: 'add_checklist_item',
        entity_type: 'work_order_checklist',
        entity_id: checklistItem.id,
        user_id: user.id,
        actor_id: user.id,
        new_values: { title, work_order_id, sequence: nextSequence },
        created_at: new Date().toISOString(),
      });

      return NextResponse.json({
        success: true,
        data: checklistItem,
        message: 'Checklist item added',
      });
    }

    // Unknown action
    return NextResponse.json(
      { success: false, error: `Unknown action: ${action}`, code: 'UNKNOWN_ACTION' },
      { status: 400 }
    );

  } catch (error: any) {
    console.error('[Action Router] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Internal server error', code: 'INTERNAL_ERROR' },
      { status: 500 }
    );
  }
}

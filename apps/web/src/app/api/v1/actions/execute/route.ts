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
import { createClient } from '@/lib/supabase/server';

interface ActionResponse {
  success: boolean;
  data?: any;
  message?: string;
  error?: string;
  code?: string;
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

    const supabase = await createClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { success: false, error: 'Unauthorized', code: 'UNAUTHORIZED' },
        { status: 401 }
      );
    }

    const enrichedContext = { ...context, user_id: user.id };

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
        .from('parts')
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
        .from('parts')
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
        .from('part_usage_log')
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

      // RBAC check
      const { data: userData, error: userError } = await supabase
        .from('users')
        .select('role')
        .eq('id', user.id)
        .eq('yacht_id', enrichedContext.yacht_id)
        .single();

      if (userError) {
        return NextResponse.json(
          { success: false, error: 'Failed to verify permissions', code: 'PERMISSION_ERROR' },
          { status: 500 }
        );
      }

      const allowedRoles = ['HOD', 'CAPTAIN', 'CHIEF_ENGINEER', 'FLEET_MANAGER'];
      if (!allowedRoles.includes(userData.role)) {
        return NextResponse.json(
          { success: false, error: 'Permission denied: Insufficient privileges', code: 'FORBIDDEN' },
          { status: 403 }
        );
      }

      // Stock check
      const { data: partData, error: partError } = await supabase
        .from('parts')
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
        .from('part_usage_log')
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
        .from('parts')
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

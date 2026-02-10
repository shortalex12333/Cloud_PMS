/**
 * Search Fallback Endpoint - Database-based Search
 *
 * Used when external pipeline API is down or unavailable.
 * Provides basic search across parts, documents, equipment, etc.
 *
 * This is a FALLBACK only - the primary search should use the pipeline API
 * for better relevance, ranking, and cross-entity search.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

interface SearchResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  metadata: Record<string, any>;
  primary_id?: string;
  source_table?: string;
}

// Master DB client (using env vars)
function getMasterClient(accessToken: string) {
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

export async function POST(request: NextRequest) {
  try {
    const { query, yacht_id, limit = 20 } = await request.json();

    if (!query || query.trim().length === 0) {
      return NextResponse.json({
        success: true,
        results: [],
        total_count: 0,
        message: 'Empty query',
      });
    }

    // Extract JWT from Authorization header
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { success: false, error: 'Missing or invalid Authorization header' },
        { status: 401 }
      );
    }

    const accessToken = authHeader.replace('Bearer ', '');

    // Create client with user's token
    const supabase = getMasterClient(accessToken);

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { success: false, error: 'Invalid or expired token' },
        { status: 401 }
      );
    }

    const searchTerm = query.toLowerCase().trim();
    const results: SearchResult[] = [];

    // ====================================================================
    // PARTS SEARCH (Inventory Lens)
    // ====================================================================
    const { data: parts, error: partsError } = await supabase
      .from('pms_parts')
      .select('*')
      .eq('yacht_id', yacht_id)
      .or(`part_name.ilike.%${searchTerm}%,part_number.ilike.%${searchTerm}%,manufacturer.ilike.%${searchTerm}%,category.ilike.%${searchTerm}%,description.ilike.%${searchTerm}%`)
      .limit(limit);

    if (!partsError && parts) {
      parts.forEach((part: any) => {
        results.push({
          id: part.part_id,
          primary_id: part.part_id,
          type: 'part',
          source_table: 'parts',
          title: part.part_name || `Part ${part.part_number}`,
          subtitle: [
            part.part_number && `P/N: ${part.part_number}`,
            part.manufacturer && `Mfr: ${part.manufacturer}`,
            part.location && `Location: ${part.location}`,
            `Stock: ${part.on_hand || 0}`,
          ]
            .filter(Boolean)
            .join(' | '),
          metadata: part,
        });
      });
    }

    // ====================================================================
    // EQUIPMENT SEARCH
    // ====================================================================
    const { data: equipment, error: equipmentError } = await supabase
      .from('pms_equipment')
      .select('*')
      .eq('yacht_id', yacht_id)
      .or(`equipment_name.ilike.%${searchTerm}%,serial_number.ilike.%${searchTerm}%,manufacturer.ilike.%${searchTerm}%,equipment_type.ilike.%${searchTerm}%`)
      .limit(limit);

    if (!equipmentError && equipment) {
      equipment.forEach((eq: any) => {
        results.push({
          id: eq.equipment_id,
          primary_id: eq.equipment_id,
          type: 'equipment',
          source_table: 'equipment',
          title: eq.equipment_name || 'Unnamed Equipment',
          subtitle: [
            eq.equipment_type && `Type: ${eq.equipment_type}`,
            eq.manufacturer && `Mfr: ${eq.manufacturer}`,
            eq.location && `Location: ${eq.location}`,
          ]
            .filter(Boolean)
            .join(' | '),
          metadata: eq,
        });
      });
    }

    // ====================================================================
    // WORK ORDERS SEARCH
    // ====================================================================
    const { data: workOrders, error: workOrdersError } = await supabase
      .from('pms_work_orders')
      .select('*')
      .eq('yacht_id', yacht_id)
      .or(`title.ilike.%${searchTerm}%,description.ilike.%${searchTerm}%,work_order_number.ilike.%${searchTerm}%`)
      .limit(limit);

    if (!workOrdersError && workOrders) {
      workOrders.forEach((wo: any) => {
        results.push({
          id: wo.work_order_id,
          primary_id: wo.work_order_id,
          type: 'work_order',
          source_table: 'work_orders',
          title: wo.title || `Work Order ${wo.work_order_number}`,
          subtitle: [
            wo.status && `Status: ${wo.status}`,
            wo.priority && `Priority: ${wo.priority}`,
            wo.assigned_to_name && `Assigned to: ${wo.assigned_to_name}`,
          ]
            .filter(Boolean)
            .join(' | '),
          metadata: wo,
        });
      });
    }

    // ====================================================================
    // SHOPPING LIST ITEMS
    // ====================================================================
    const { data: shoppingItems, error: shoppingError } = await supabase
      .from('pms_shopping_list_items')
      .select('*')
      .eq('yacht_id', yacht_id)
      .or(`part_name.ilike.%${searchTerm}%,part_number.ilike.%${searchTerm}%,manufacturer.ilike.%${searchTerm}%,notes.ilike.%${searchTerm}%`)
      .limit(limit);

    if (!shoppingError && shoppingItems) {
      shoppingItems.forEach((item: any) => {
        results.push({
          id: item.shopping_list_item_id,
          primary_id: item.shopping_list_item_id,
          type: 'shopping_list_item',
          source_table: 'shopping_list_items',
          title: item.part_name || 'Unnamed Part',
          subtitle: [
            item.part_number && `P/N: ${item.part_number}`,
            item.status && `Status: ${item.status}`,
            item.quantity && `Qty: ${item.quantity}`,
          ]
            .filter(Boolean)
            .join(' | '),
          metadata: item,
        });
      });
    }

    // Sort results by relevance (simple: exact matches first, then contains)
    results.sort((a, b) => {
      const aTitle = a.title.toLowerCase();
      const bTitle = b.title.toLowerCase();
      const aExact = aTitle === searchTerm;
      const bExact = bTitle === searchTerm;
      const aStarts = aTitle.startsWith(searchTerm);
      const bStarts = bTitle.startsWith(searchTerm);

      if (aExact && !bExact) return -1;
      if (!aExact && bExact) return 1;
      if (aStarts && !bStarts) return -1;
      if (!aStarts && bStarts) return 1;
      return 0;
    });

    // Limit total results
    const limitedResults = results.slice(0, limit);

    return NextResponse.json({
      success: true,
      results: limitedResults,
      total_count: limitedResults.length,
      timing_ms: 0,
      fallback: true, // Flag indicating this is fallback search
      message: limitedResults.length === 0 ? 'No results found' : undefined,
    });
  } catch (error: any) {
    console.error('[Search Fallback] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Search failed',
        results: [],
        total_count: 0,
      },
      { status: 500 }
    );
  }
}

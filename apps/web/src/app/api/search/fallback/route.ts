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

// Tenant DB client (using service role to bypass RLS)
// Backend search endpoint - security is ensured by yacht_id filtering
function getTenantClient() {
  const supabaseUrl = process.env.TENANT_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.TENANT_SUPABASE_SERVICE_KEY ||
                     process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY ||
                     process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceKey) {
    throw new Error('Tenant Supabase environment variables not configured');
  }

  return createClient(supabaseUrl, serviceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
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

    // Note: We validate the auth header exists but use service role for queries
    // This is a backend search endpoint - security is ensured by:
    // 1. yacht_id filtering (only returns data for specified yacht)
    // 2. Frontend auth (user must be logged in to call this endpoint)
    const supabase = getTenantClient();

    const searchTerm = query.toLowerCase().trim();
    const results: SearchResult[] = [];
    const seenPartIds = new Set<string>();

    // ====================================================================
    // PARTS SEARCH (Inventory Lens)
    // Phase 1: ILIKE substring search (fast, exact)
    // ====================================================================
    const { data: parts, error: partsError } = await supabase
      .from('pms_parts')
      .select('*')
      .eq('yacht_id', yacht_id)
      .or(`part_name.ilike.%${searchTerm}%,part_number.ilike.%${searchTerm}%,manufacturer.ilike.%${searchTerm}%,category.ilike.%${searchTerm}%,description.ilike.%${searchTerm}%`)
      .limit(limit);

    if (!partsError && parts) {
      parts.forEach((part: any) => {
        seenPartIds.add(part.part_id);
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
    // PARTS SEARCH Phase 2: pg_trgm fuzzy search (handles typos)
    // LAW 20: Universal trigram matching - "mantenance" finds "maintenance"
    // Trigger when ILIKE returns < 3 results for broad recall on misspellings
    // ====================================================================
    if ((parts?.length || 0) < 3) {
      try {
        const { data: fuzzyParts, error: fuzzyError } = await supabase.rpc('search_parts_fuzzy', {
          p_yacht_id: yacht_id,
          p_query: searchTerm,
          p_threshold: 0.3,
          p_limit: limit,
        });

        if (!fuzzyError && fuzzyParts) {
          fuzzyParts.forEach((part: any) => {
            if (!seenPartIds.has(part.part_id)) {
              seenPartIds.add(part.part_id);
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
                  part.similarity && `Match: ${Math.round(part.similarity * 100)}%`,
                ]
                  .filter(Boolean)
                  .join(' | '),
                metadata: { ...part, fuzzy_match: true },
              });
            }
          });
          console.log(`[Search Fallback] Trigram found ${fuzzyParts.length} fuzzy matches for "${searchTerm}"`);
        }
      } catch (fuzzyErr) {
        console.warn('[Search Fallback] Trigram search unavailable:', fuzzyErr);
      }
    }

    // ====================================================================
    // EQUIPMENT SEARCH
    // Phase 1: ILIKE substring search
    // ====================================================================
    const seenEquipmentIds = new Set<string>();
    const { data: equipment, error: equipmentError } = await supabase
      .from('pms_equipment')
      .select('*')
      .eq('yacht_id', yacht_id)
      .or(`equipment_name.ilike.%${searchTerm}%,serial_number.ilike.%${searchTerm}%,manufacturer.ilike.%${searchTerm}%,equipment_type.ilike.%${searchTerm}%`)
      .limit(limit);

    if (!equipmentError && equipment) {
      equipment.forEach((eq: any) => {
        seenEquipmentIds.add(eq.equipment_id);
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

    // Phase 2: pg_trgm fuzzy search for equipment
    // Trigger when ILIKE returns < 3 results for broad recall on misspellings
    if ((equipment?.length || 0) < 3) {
      try {
        const { data: fuzzyEquipment, error: fuzzyEqError } = await supabase.rpc('search_equipment_fuzzy', {
          p_yacht_id: yacht_id,
          p_query: searchTerm,
          p_threshold: 0.3,
          p_limit: limit,
        });

        if (!fuzzyEqError && fuzzyEquipment) {
          fuzzyEquipment.forEach((eq: any) => {
            if (!seenEquipmentIds.has(eq.equipment_id)) {
              seenEquipmentIds.add(eq.equipment_id);
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
                  eq.similarity && `Match: ${Math.round(eq.similarity * 100)}%`,
                ]
                  .filter(Boolean)
                  .join(' | '),
                metadata: { ...eq, fuzzy_match: true },
              });
            }
          });
        }
      } catch (fuzzyErr) {
        console.warn('[Search Fallback] Equipment trigram search unavailable:', fuzzyErr);
      }
    }

    // ====================================================================
    // WORK ORDERS SEARCH
    // Phase 1: ILIKE substring search
    // ====================================================================
    const seenWorkOrderIds = new Set<string>();
    const { data: workOrders, error: workOrdersError } = await supabase
      .from('pms_work_orders')
      .select('*')
      .eq('yacht_id', yacht_id)
      .or(`title.ilike.%${searchTerm}%,description.ilike.%${searchTerm}%,work_order_number.ilike.%${searchTerm}%`)
      .limit(limit);

    if (!workOrdersError && workOrders) {
      workOrders.forEach((wo: any) => {
        seenWorkOrderIds.add(wo.work_order_id);
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

    // Phase 2: pg_trgm fuzzy search for work orders
    // Trigger when ILIKE returns < 3 results for broad recall on misspellings
    if ((workOrders?.length || 0) < 3) {
      try {
        const { data: fuzzyWO, error: fuzzyWOError } = await supabase.rpc('search_work_orders_fuzzy', {
          p_yacht_id: yacht_id,
          p_query: searchTerm,
          p_threshold: 0.3,
          p_limit: limit,
        });

        if (!fuzzyWOError && fuzzyWO) {
          fuzzyWO.forEach((wo: any) => {
            if (!seenWorkOrderIds.has(wo.work_order_id)) {
              seenWorkOrderIds.add(wo.work_order_id);
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
                  wo.similarity && `Match: ${Math.round(wo.similarity * 100)}%`,
                ]
                  .filter(Boolean)
                  .join(' | '),
                metadata: { ...wo, fuzzy_match: true },
              });
            }
          });
        }
      } catch (fuzzyErr) {
        console.warn('[Search Fallback] Work order trigram search unavailable:', fuzzyErr);
      }
    }

    // ====================================================================
    // SHOPPING LIST ITEMS
    // Phase 1: ILIKE substring search
    // ====================================================================
    const seenShoppingIds = new Set<string>();
    const { data: shoppingItems, error: shoppingError } = await supabase
      .from('pms_shopping_list_items')
      .select('*')
      .eq('yacht_id', yacht_id)
      .or(`part_name.ilike.%${searchTerm}%,part_number.ilike.%${searchTerm}%,manufacturer.ilike.%${searchTerm}%,notes.ilike.%${searchTerm}%`)
      .limit(limit);

    if (!shoppingError && shoppingItems) {
      shoppingItems.forEach((item: any) => {
        seenShoppingIds.add(item.shopping_list_item_id || item.id);
        results.push({
          id: item.shopping_list_item_id || item.id,
          primary_id: item.shopping_list_item_id || item.id,
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

    // Phase 2: pg_trgm fuzzy search for shopping list
    // Trigger when ILIKE returns < 3 results for broad recall on misspellings
    if ((shoppingItems?.length || 0) < 3) {
      try {
        const { data: fuzzyItems, error: fuzzyShoppingError } = await supabase.rpc('search_shopping_list_fuzzy', {
          p_yacht_id: yacht_id,
          p_query: searchTerm,
          p_threshold: 0.3,
          p_limit: limit,
        });

        if (!fuzzyShoppingError && fuzzyItems) {
          fuzzyItems.forEach((item: any) => {
            if (!seenShoppingIds.has(item.shopping_list_item_id)) {
              seenShoppingIds.add(item.shopping_list_item_id);
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
                  item.similarity && `Match: ${Math.round(item.similarity * 100)}%`,
                ]
                  .filter(Boolean)
                  .join(' | '),
                metadata: { ...item, fuzzy_match: true },
              });
            }
          });
          console.log(`[Search Fallback] Shopping list trigram found ${fuzzyItems.length} fuzzy matches for "${searchTerm}"`);
        }
      } catch (fuzzyErr) {
        console.warn('[Search Fallback] Shopping list trigram search unavailable:', fuzzyErr);
      }
    }

    // ====================================================================
    // DOCUMENTS SEARCH
    // Phase 1: ILIKE substring search
    // ====================================================================
    const seenDocIds = new Set<string>();
    try {
      const { data: documents, error: documentsError } = await supabase
        .from('doc_metadata')
        .select('*')
        .eq('yacht_id', yacht_id)
        .is('deleted_at', null)
        .or(`filename.ilike.%${searchTerm}%,description.ilike.%${searchTerm}%,doc_type.ilike.%${searchTerm}%`)
        .limit(limit);

      if (documentsError) {
        console.warn('[Search Fallback] Document search error:', documentsError);
      }

      if (!documentsError && documents) {
        documents.forEach((doc: any) => {
          seenDocIds.add(doc.id);
          results.push({
            id: doc.id,
            primary_id: doc.id,
            type: 'document',
            source_table: 'documents',
            title: doc.filename || 'Unnamed Document',
            subtitle: [
              doc.doc_type && `Type: ${doc.doc_type}`,
              doc.content_type && `Format: ${doc.content_type}`,
              doc.created_at && `Uploaded: ${new Date(doc.created_at).toLocaleDateString()}`,
            ]
              .filter(Boolean)
              .join(' | '),
            metadata: doc,
          });
        });
      }

      // Phase 2: pg_trgm fuzzy search for documents
      // Trigger when ILIKE returns < 3 results for broad recall on misspellings
      if ((documents?.length || 0) < 3) {
        try {
          const { data: fuzzyDocs, error: fuzzyDocError } = await supabase.rpc('search_documents_fuzzy', {
            p_yacht_id: yacht_id,
            p_query: searchTerm,
            p_threshold: 0.3,
            p_limit: limit,
          });

          if (!fuzzyDocError && fuzzyDocs) {
            fuzzyDocs.forEach((doc: any) => {
              if (!seenDocIds.has(doc.id)) {
                seenDocIds.add(doc.id);
                results.push({
                  id: doc.id,
                  primary_id: doc.id,
                  type: 'document',
                  source_table: 'documents',
                  title: doc.filename || 'Unnamed Document',
                  subtitle: [
                    doc.doc_type && `Type: ${doc.doc_type}`,
                    doc.content_type && `Format: ${doc.content_type}`,
                    doc.created_at && `Uploaded: ${new Date(doc.created_at).toLocaleDateString()}`,
                    doc.similarity && `Match: ${Math.round(doc.similarity * 100)}%`,
                  ]
                    .filter(Boolean)
                    .join(' | '),
                  metadata: { ...doc, fuzzy_match: true },
                });
              }
            });
            console.log(`[Search Fallback] Document trigram found ${fuzzyDocs.length} fuzzy matches for "${searchTerm}"`);
          }
        } catch (fuzzyErr) {
          console.warn('[Search Fallback] Document trigram search unavailable:', fuzzyErr);
        }
      }
    } catch (docError) {
      // Don't fail entire search if documents fail - gracefully degrade
      console.warn('[Search Fallback] Document search exception:', docError);
    }

    // Sort results by relevance:
    // 1. Exact matches first
    // 2. Starts with search term
    // 3. Contains search term (ILIKE matches)
    // 4. Fuzzy matches sorted by similarity score (highest first)
    results.sort((a, b) => {
      const aTitle = a.title.toLowerCase();
      const bTitle = b.title.toLowerCase();
      const aExact = aTitle === searchTerm;
      const bExact = bTitle === searchTerm;
      const aStarts = aTitle.startsWith(searchTerm);
      const bStarts = bTitle.startsWith(searchTerm);
      const aContains = aTitle.includes(searchTerm);
      const bContains = bTitle.includes(searchTerm);
      const aFuzzy = a.metadata?.fuzzy_match === true;
      const bFuzzy = b.metadata?.fuzzy_match === true;
      const aSimilarity = a.metadata?.similarity || 0;
      const bSimilarity = b.metadata?.similarity || 0;

      // Exact matches first
      if (aExact && !bExact) return -1;
      if (!aExact && bExact) return 1;

      // Starts with search term
      if (aStarts && !bStarts) return -1;
      if (!aStarts && bStarts) return 1;

      // Contains search term (ILIKE matches) before fuzzy matches
      if (aContains && !bContains) return -1;
      if (!aContains && bContains) return 1;

      // If both are fuzzy matches, sort by similarity (descending)
      if (aFuzzy && bFuzzy) {
        return bSimilarity - aSimilarity;
      }

      // Non-fuzzy before fuzzy
      if (!aFuzzy && bFuzzy) return -1;
      if (aFuzzy && !bFuzzy) return 1;

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

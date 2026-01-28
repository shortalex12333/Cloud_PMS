import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import OpenAI from 'openai';

// Force dynamic rendering - no static generation
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  // Initialize clients inside handler to avoid build-time errors
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
  });
  try {
    const body = await request.json();
    const { query, limit = 20, yacht_id } = body;

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      );
    }

    // Get yacht_id from auth or use provided one
    // For now, use the test yacht_id if not provided
    const targetYachtId = yacht_id || '85fe1119-b04c-41ac-80f1-829d23322598';

    // Generate embedding for query
    const embeddingResponse = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: query.slice(0, 8000), // Truncate if too long
    });

    const queryEmbedding = embeddingResponse.data[0].embedding;

    // Call the hybrid search function
    const { data, error } = await supabase.rpc('search_email_hybrid', {
      p_yacht_id: targetYachtId,
      p_embedding: queryEmbedding,
      p_entity_keywords: [], // Could extract keywords from query
      p_date_from: null,
      p_date_to: null,
      p_limit: limit,
      p_similarity_threshold: 0.1, // Low threshold - ranking handles relevance
    });

    if (error) {
      console.error('[email/search] RPC error:', error);
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      results: data || [],
      query,
      embedding_tokens: embeddingResponse.usage?.total_tokens || 0,
    });
  } catch (error) {
    console.error('[email/search] Error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}

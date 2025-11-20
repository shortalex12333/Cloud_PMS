/**
 * Search API client
 */

const SEARCH_API_URL = process.env.NEXT_PUBLIC_SEARCH_API_URL || 'http://localhost:8000'

export interface SearchRequest {
  query: string
  mode?: 'auto' | 'rag' | 'graph_rag'
  filters?: Record<string, any>
  top_k?: number
}

export interface SearchResponse {
  query_id: string
  query: string
  entities: any
  intent: any
  results: any[]
  latency_ms: number
  sources_searched: string[]
}

/**
 * Perform search query
 */
export async function search(
  request: SearchRequest,
  accessToken: string,
  yachtSignature: string
): Promise<SearchResponse> {
  const response = await fetch(`${SEARCH_API_URL}/v1/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
      'X-Yacht-Signature': yachtSignature,
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Search failed')
  }

  return response.json()
}

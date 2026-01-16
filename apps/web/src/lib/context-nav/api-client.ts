/**
 * Context Navigation API Client
 *
 * Calls backend endpoints for situational continuity.
 * All endpoints are at /api/context/*
 */

import { supabase } from '@/lib/supabaseClient';

// ============================================================================
// TYPES (matching backend schemas)
// ============================================================================

export interface NavigationContext {
  id: string;
  yacht_id: string;
  created_by_user_id: string;
  created_at: string;
  ended_at: string | null;
  active_anchor_type: string;
  active_anchor_id: string;
  extracted_entities: Record<string, any>;
  temporal_bias: string;
}

export interface RelatedItem {
  artefact_type: string;
  artefact_id: string;
  title: string;
  subtitle?: string;
  metadata?: Record<string, any>;
}

export interface RelatedGroup {
  domain: string;
  items: RelatedItem[];
}

export interface RelatedResponse {
  situation_id: string;
  anchor_type: string;
  anchor_id: string;
  groups: RelatedGroup[];
}

export interface AddRelatedResponse {
  relation_id: string;
  created_at: string;
}

// ============================================================================
// API CLIENT
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

/**
 * Get authorization header with Supabase session token.
 */
async function getAuthHeader(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  if (!data.session) return null;
  return `Bearer ${data.session.access_token}`;
}

/**
 * Create a new navigation context when user opens artifact from search.
 */
export async function createNavigationContext(params: {
  yacht_id: string;
  user_id: string;
  artefact_type: string;
  artefact_id: string;
}): Promise<NavigationContext> {
  const authHeader = await getAuthHeader();
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }

  const response = await fetch(`${API_BASE}/api/context/create`, {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to create context: ${error}`);
  }

  return response.json();
}

/**
 * Update active anchor when user navigates to different artifact.
 */
export async function updateActiveAnchor(params: {
  context_id: string;
  anchor_type: string;
  anchor_id: string;
  yacht_id: string;
  user_id: string;
}): Promise<NavigationContext> {
  const authHeader = await getAuthHeader();
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }

  const response = await fetch(
    `${API_BASE}/api/context/${params.context_id}/update-anchor?anchor_type=${params.anchor_type}&anchor_id=${params.anchor_id}&yacht_id=${params.yacht_id}&user_id=${params.user_id}`,
    {
      method: 'PUT',
      headers,
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to update anchor: ${error}`);
  }

  return response.json();
}

/**
 * Get related artifacts (deterministic FK/JOIN only).
 * CRITICAL: Does NOT write audit event.
 */
export async function getRelatedArtifacts(params: {
  situation_id: string;
  anchor_type: string;
  anchor_id: string;
  tenant_id: string;
  user_id: string;
  allowed_domains: string[];
}): Promise<RelatedResponse> {
  const authHeader = await getAuthHeader();
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }

  const response = await fetch(`${API_BASE}/api/context/related`, {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to get related: ${error}`);
  }

  return response.json();
}

/**
 * Add explicit user relation between two artifacts.
 */
export async function addUserRelation(params: {
  yacht_id: string;
  user_id: string;
  from_artefact_type: string;
  from_artefact_id: string;
  to_artefact_type: string;
  to_artefact_id: string;
}): Promise<AddRelatedResponse> {
  const authHeader = await getAuthHeader();
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }

  const response = await fetch(`${API_BASE}/api/context/add-relation`, {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const error = await response.text();
    if (response.status === 409) {
      throw new Error('Relation already exists');
    }
    throw new Error(`Failed to add relation: ${error}`);
  }

  return response.json();
}

/**
 * End navigation context when user returns to search home.
 */
export async function endNavigationContext(params: {
  context_id: string;
  yacht_id: string;
  user_id: string;
}): Promise<{ status: string; message: string }> {
  const authHeader = await getAuthHeader();
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }

  const response = await fetch(
    `${API_BASE}/api/context/${params.context_id}/end?yacht_id=${params.yacht_id}&user_id=${params.user_id}`,
    {
      method: 'POST',
      headers,
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to end context: ${error}`);
  }

  return response.json();
}

'use client';

/**
 * useSituationContext Hook
 *
 * Manages UI state for situation context (V2 - no behavioral tracking).
 */

import { useState, useCallback, useEffect } from 'react';
import type {
  SituationContext,
  EntityType,
  SituationDomain,
  UserRole,
} from '../types';

interface UseSituationContextOptions {
  /** Yacht ID */
  yachtId: string;
  /** User ID */
  userId: string;
  /** User role */
  userRole: UserRole;
}

interface UseSituationContextReturn {
  /** Current situation context */
  context: SituationContext;
  /** Set search mode */
  setSearchMode: (query: string) => void;
  /** Set entity view mode */
  setEntityView: (entityType: EntityType, entityId: string, domain?: SituationDomain) => void;
  /** Clear situation (back to no_situation) */
  clearSituation: () => void;
  /** Add query to recent queries */
  addQuery: (query: string) => void;
  /** Update last activity timestamp */
  updateActivity: () => void;
  /** Check if in search mode */
  isInSearchMode: boolean;
  /** Check if in entity view */
  isInEntityView: boolean;
}

/**
 * Generate a session ID
 */
function generateSessionId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Detect device type
 */
function getDeviceType(): 'mobile' | 'desktop' {
  if (typeof window === 'undefined') return 'desktop';
  return window.innerWidth < 768 ? 'mobile' : 'desktop';
}

export function useSituationContext(
  options: UseSituationContextOptions
): UseSituationContextReturn {
  const { yachtId, userId, userRole } = options;

  const [context, setContext] = useState<SituationContext>(() => ({
    yacht_id: yachtId,
    user_id: userId,
    role: userRole,
    device_type: getDeviceType(),
    primary_entity_type: null,
    primary_entity_id: null,
    domain: null,
    session_id: generateSessionId(),
    created_at: Date.now(),
    last_activity_at: Date.now(),
    ui_state: 'no_situation',
    recent_queries: [],
  }));

  // Update device type on resize
  useEffect(() => {
    const handleResize = () => {
      setContext((prev) => ({
        ...prev,
        device_type: getDeviceType(),
      }));
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  /**
   * Set search mode
   */
  const setSearchMode = useCallback((query: string) => {
    setContext((prev) => ({
      ...prev,
      ui_state: 'search_mode',
      primary_entity_type: null,
      primary_entity_id: null,
      last_activity_at: Date.now(),
      recent_queries: [query, ...prev.recent_queries.filter((q) => q !== query)].slice(0, 5),
    }));
  }, []);

  /**
   * Set entity view mode
   */
  const setEntityView = useCallback(
    (entityType: EntityType, entityId: string, domain?: SituationDomain) => {
      setContext((prev) => ({
        ...prev,
        ui_state: 'entity_view',
        primary_entity_type: entityType,
        primary_entity_id: entityId,
        domain: domain || inferDomain(entityType),
        last_activity_at: Date.now(),
      }));
    },
    []
  );

  /**
   * Clear situation
   */
  const clearSituation = useCallback(() => {
    setContext((prev) => ({
      ...prev,
      ui_state: 'no_situation',
      primary_entity_type: null,
      primary_entity_id: null,
      domain: null,
      last_activity_at: Date.now(),
    }));
  }, []);

  /**
   * Add query to recent queries
   */
  const addQuery = useCallback((query: string) => {
    setContext((prev) => ({
      ...prev,
      last_activity_at: Date.now(),
      recent_queries: [query, ...prev.recent_queries.filter((q) => q !== query)].slice(0, 5),
    }));
  }, []);

  /**
   * Update last activity timestamp
   */
  const updateActivity = useCallback(() => {
    setContext((prev) => ({
      ...prev,
      last_activity_at: Date.now(),
    }));
  }, []);

  const isInSearchMode = context.ui_state === 'search_mode';
  const isInEntityView = context.ui_state === 'entity_view';

  return {
    context,
    setSearchMode,
    setEntityView,
    clearSituation,
    addQuery,
    updateActivity,
    isInSearchMode,
    isInEntityView,
  };
}

/**
 * Infer domain from entity type
 */
function inferDomain(entityType: EntityType): SituationDomain {
  const domainMap: Record<EntityType, SituationDomain> = {
    document: 'manuals',
    equipment: 'maintenance',
    part: 'inventory',
    work_order: 'maintenance',
    fault: 'maintenance',
    location: 'maintenance',
    person: 'people',
    inventory: 'inventory',
    symptom: 'maintenance',
  };

  return domainMap[entityType] || 'maintenance';
}

export default useSituationContext;

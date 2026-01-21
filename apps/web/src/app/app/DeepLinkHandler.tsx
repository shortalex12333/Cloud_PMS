'use client';

/**
 * DeepLinkHandler - URL Query Parameter Support for E2E Testing
 *
 * Reads URL query parameters and programmatically opens the context panel.
 * Supports deep links like: /app?entity=fault&id=xxx
 *
 * This enables deterministic E2E testing of entity detail views.
 *
 * Query Parameters:
 * - entity: Entity type (fault, work_order, equipment, part, document)
 * - id: Entity UUID
 *
 * Example URLs:
 * - /app?entity=fault&id=123e4567-e89b-12d3-a456-426614174000
 * - /app?entity=work_order&id=abc123
 * - /app?entity=equipment&id=def456
 */

import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useSurface } from '@/contexts/SurfaceContext';
import { useAuth } from '@/contexts/AuthContext';

// Entity fetch configuration
const PIPELINE_URL = process.env.NEXT_PUBLIC_PIPELINE_URL || 'https://pipeline-core.int.celeste7.ai';

interface DeepLinkHandlerProps {
  /** Called when deep link is processed */
  onDeepLinkProcessed?: (entityType: string, entityId: string) => void;
}

export function DeepLinkHandler({ onDeepLinkProcessed }: DeepLinkHandlerProps) {
  const searchParams = useSearchParams();
  const { showContext } = useSurface();
  const { session, isLoading: authLoading } = useAuth();
  const processedRef = useRef(false);
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

  useEffect(() => {
    // Only process once per mount
    if (processedRef.current) return;

    // Wait for auth to be ready
    if (authLoading) return;

    const entityType = searchParams.get('entity');
    const entityId = searchParams.get('id');

    // No deep link parameters
    if (!entityType || !entityId) return;

    // Mark as processed to prevent re-execution
    processedRef.current = true;

    console.log('[DeepLinkHandler] Processing deep link:', { entityType, entityId });
    setStatus('loading');

    // Fetch entity data from API
    const fetchEntityData = async () => {
      try {
        if (!session?.access_token) {
          console.warn('[DeepLinkHandler] No auth token, using minimal data');
          // Still open panel with minimal data
          showContext(entityType, entityId, {
            id: entityId,
            title: `${entityType} ${entityId.substring(0, 8)}`,
            description: 'Loading...',
          });
          setStatus('success');
          onDeepLinkProcessed?.(entityType, entityId);
          return;
        }

        // Try to fetch full entity data
        const response = await fetch(
          `${PIPELINE_URL}/v1/entity/${entityType}/${entityId}`,
          {
            headers: {
              Authorization: `Bearer ${session.access_token}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          console.log('[DeepLinkHandler] Entity data fetched:', data);
          showContext(entityType, entityId, data);
        } else {
          // API might not support this endpoint yet - use minimal data
          console.warn('[DeepLinkHandler] Entity fetch failed, using minimal data');
          showContext(entityType, entityId, {
            id: entityId,
            title: `${entityType.charAt(0).toUpperCase() + entityType.slice(1).replace('_', ' ')}`,
            description: 'Details pending',
          });
        }

        setStatus('success');
        onDeepLinkProcessed?.(entityType, entityId);
      } catch (error) {
        console.error('[DeepLinkHandler] Error fetching entity:', error);
        // Still open panel with minimal data on error
        showContext(entityType, entityId, {
          id: entityId,
          title: `${entityType} ${entityId.substring(0, 8)}`,
          description: 'Error loading details',
        });
        setStatus('error');
        onDeepLinkProcessed?.(entityType, entityId);
      }
    };

    // Small delay to ensure context is ready
    const timer = setTimeout(fetchEntityData, 100);
    return () => clearTimeout(timer);
  }, [searchParams, showContext, session, authLoading, onDeepLinkProcessed]);

  // Reset processed flag when URL changes
  useEffect(() => {
    const entityType = searchParams.get('entity');
    const entityId = searchParams.get('id');

    if (!entityType || !entityId) {
      processedRef.current = false;
      setStatus('idle');
    }
  }, [searchParams]);

  // Hidden status indicator for E2E tests
  return (
    <div
      data-testid="deep-link-handler"
      data-deep-link-status={status}
      data-deep-link-entity={searchParams.get('entity') || ''}
      data-deep-link-id={searchParams.get('id') || ''}
      style={{ display: 'none' }}
    />
  );
}

export default DeepLinkHandler;

'use client';

/**
 * DeepLinkHandler - URL Query Parameter Support for E2E Testing & Handover Links
 *
 * Reads URL query parameters and programmatically opens the context panel.
 * Supports deep links like: /app?entity=fault&id=xxx
 *
 * Also handles handover export link resolution:
 * - /open?t=<token> resolves and redirects to /app?open_resolved=1
 * - This handler reads the resolution from sessionStorage and focuses the entity
 *
 * Query Parameters:
 * - entity: Entity type (fault, work_order, equipment, part, document)
 * - id: Entity UUID
 * - open_resolved: Flag indicating handover link was resolved (read from sessionStorage)
 *
 * Example URLs:
 * - /app?entity=fault&id=123e4567-e89b-12d3-a456-426614174000
 * - /app?entity=work_order&id=abc123
 * - /app?entity=equipment&id=def456
 * - /app?open_resolved=1 (after /open?t=... resolution)
 */

import { useEffect, useRef, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useSurface } from '@/contexts/SurfaceContext';
import { useAuth } from '@/hooks/useAuth';
import type { ResolveResponse } from '@/lib/handoverExportClient';

// Entity fetch configuration
const PIPELINE_URL = process.env.NEXT_PUBLIC_PIPELINE_URL || 'https://pipeline-core.int.celeste7.ai';

interface DeepLinkHandlerProps {
  /** Called when deep link is processed */
  onDeepLinkProcessed?: (entityType: string, entityId: string) => void;
}

export function DeepLinkHandler({ onDeepLinkProcessed }: DeepLinkHandlerProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { showContext } = useSurface();
  const { session, loading: authLoading } = useAuth();
  const processedRef = useRef(false);
  const openResolvedRef = useRef(false);
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

  // Handle handover open resolution (from /open?t=... -> /app?open_resolved=1)
  useEffect(() => {
    if (openResolvedRef.current) return;
    if (authLoading) return;

    const openResolved = searchParams.get('open_resolved');
    if (openResolved !== '1') return;

    openResolvedRef.current = true;

    // Read resolution result from sessionStorage
    const storedResult = sessionStorage.getItem('handover_open_result');
    if (!storedResult) {
      console.warn('[DeepLinkHandler] No handover open result in sessionStorage');
      // Clean up URL
      router.replace('/app');
      return;
    }

    try {
      const result: ResolveResponse = JSON.parse(storedResult);
      console.log('[DeepLinkHandler] Processing handover open result:', result);

      // Clean up sessionStorage
      sessionStorage.removeItem('handover_open_result');

      // Open context panel with the resolved entity
      const { focus } = result;
      showContext(focus.type, focus.id, {
        id: focus.id,
        title: focus.title || `${focus.type.charAt(0).toUpperCase() + focus.type.slice(1).replace('_', ' ')}`,
        _handover_resolved: true,
      });

      setStatus('success');
      onDeepLinkProcessed?.(focus.type, focus.id);

      // Clean up URL (remove open_resolved param)
      router.replace('/app');
    } catch (error) {
      console.error('[DeepLinkHandler] Error parsing handover open result:', error);
      sessionStorage.removeItem('handover_open_result');
      router.replace('/app');
    }
  }, [searchParams, showContext, authLoading, router, onDeepLinkProcessed]);

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

  // Reset processed flags when URL changes
  useEffect(() => {
    const entityType = searchParams.get('entity');
    const entityId = searchParams.get('id');
    const openResolved = searchParams.get('open_resolved');

    if (!entityType || !entityId) {
      processedRef.current = false;
    }
    if (!openResolved) {
      openResolvedRef.current = false;
    }
    if (!entityType && !entityId && !openResolved) {
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
      data-handover-resolved={searchParams.get('open_resolved') || ''}
      style={{ display: 'none' }}
    />
  );
}

export default DeepLinkHandler;

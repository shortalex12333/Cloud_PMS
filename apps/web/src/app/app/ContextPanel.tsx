'use client';

/**
 * ContextPanel - Full-Screen Entity Lens Container
 *
 * Per rules.md 1-URL philosophy:
 * - All entity views render here at app.celeste7.ai
 * - NO fragmented URLs (no /work-orders/[id], etc.)
 * - Slides from right when context-open state is active
 * - Renders full lens components (not cards) via LensRenderer
 * - Integrated with NavigationContext for back/forward stack navigation
 *
 * Phase 14: Refactored to render lenses instead of cards, per 1-URL architecture.
 * - LensRenderer maps entity types to their lens content components
 * - No UUID displayed anywhere (lens header shows human-readable titles)
 * - Cross-lens navigation via NavigationContext
 */

import React, { useEffect, useCallback } from 'react';
import { useSurface } from '@/contexts/SurfaceContext';
import { useAuth } from '@/hooks/useAuth';
import { AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { supabase } from '@/lib/supabaseClient';
import { LensRenderer } from '@/components/lens/LensRenderer';

export default function ContextPanel() {
  const { contextPanel, hideContext } = useSurface();
  const { user } = useAuth();
  const { visible, entityType, entityId, entityData: initialData } = contextPanel;

  const [entityData, setEntityData] = React.useState<Record<string, unknown> | undefined>(initialData);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Fetch fresh entity data when panel opens
  useEffect(() => {
    if (!visible || !entityType || !entityId) {
      setError(null);
      return;
    }

    const fetchEntityData = async () => {
      setLoading(true);
      setError(null);

      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session?.access_token) {
          console.warn('[ContextPanel] No auth session');
          setEntityData(initialData);
          setLoading(false);
          return;
        }

        const PIPELINE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
        const response = await fetch(
          `${PIPELINE_URL}/v1/entity/${entityType}/${entityId}`,
          {
            headers: {
              'Authorization': `Bearer ${session.access_token}`,
              'Content-Type': 'application/json',
            },
          }
        );

        if (response.ok) {
          const freshData = await response.json();
          console.log('[ContextPanel] ✅ Fresh data fetched:', entityType, entityId);

          // Validate yacht_id for security
          if (freshData.yacht_id && user?.yachtId && freshData.yacht_id !== user.yachtId) {
            throw new Error('Unauthorized: Entity belongs to different yacht');
          }

          setEntityData(freshData);
        } else {
          console.warn('[ContextPanel] Failed to fetch entity, using cached data:', response.status);
          setEntityData(initialData);
        }
      } catch (err) {
        console.error('[ContextPanel] Error fetching entity:', err);
        setError(err instanceof Error ? err.message : 'Failed to load entity');
        setEntityData(initialData); // Fallback to cached data
      } finally {
        setLoading(false);
      }
    };

    fetchEntityData();
  }, [visible, entityType, entityId, user?.yachtId, initialData]);

  // Update local state when initialData changes from parent
  useEffect(() => {
    if (initialData) {
      setEntityData(initialData);
    }
  }, [initialData]);

  // Handle ESC key to close panel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && visible) {
        e.preventDefault();
        e.stopPropagation();
        hideContext();
      }
    };

    if (visible) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [visible, hideContext]);

  // Refresh handler for lens actions
  const handleRefresh = useCallback(async () => {
    if (!entityType || !entityId) return;

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const PIPELINE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
      const response = await fetch(
        `${PIPELINE_URL}/v1/entity/${entityType}/${entityId}`,
        {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.ok) {
        const freshData = await response.json();
        setEntityData(freshData);
      }
    } catch (err) {
      console.error('[ContextPanel] Refresh failed:', err);
    }
  }, [entityType, entityId]);

  // Full-screen lens container - slides from right
  return (
    <div
      className={cn(
        'absolute inset-y-0 right-0 bg-surface-base',
        'flex flex-col',
        'transform transition-all duration-300 ease-out z-[10001]',
        'border-l border-surface-border',
        'w-[calc(100vw-80px)]', // Full-screen minus left nav
        visible ? 'translate-x-0' : 'translate-x-full'
      )}
      data-testid="context-panel"
      data-entity-type={entityType}
      data-entity-id={entityId}
      data-expanded="true"
    >
      {/* No separate header - LensRenderer includes LensHeader */}
      {/* This prevents duplicate headers and UUID display */}

      {/* Content - Lens components handle their own layout */}
      <div
        className="flex-1 overflow-hidden"
        data-testid="context-panel-content"
      >
        {loading ? (
          <div className="flex items-center justify-center h-full" data-testid="context-panel-loading">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-celeste-blue animate-spin mx-auto mb-3" />
              <p className="text-celeste-text-muted typo-body">
                Loading...
              </p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full" data-testid="context-panel-error">
            <div className="text-center">
              <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-3" />
              <p className="text-celeste-text-muted typo-body mb-3">
                {error}
              </p>
              <button
                onClick={() => window.location.reload()}
                className="text-celeste-blue hover:text-celeste-blue-hover typo-body"
              >
                Reload
              </button>
            </div>
          </div>
        ) : visible && entityType && entityId && entityData ? (
          <LensRenderer
            entityType={entityType}
            entityId={entityId}
            entityData={entityData}
            loading={loading}
            onRefresh={handleRefresh}
          />
        ) : (
          <div className="flex items-center justify-center h-full" data-testid="context-panel-empty">
            <div className="text-center">
              <AlertCircle className="w-8 h-8 text-celeste-text-secondary mx-auto mb-3" />
              <p className="text-celeste-text-muted typo-body">
                Select an item to view details
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

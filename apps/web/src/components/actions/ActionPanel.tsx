'use client';

/**
 * ActionPanel Component
 *
 * Phase 11.2: Server-driven action rendering per E020.
 *
 * "The UI must render decisions, not make them."
 *
 * This component demonstrates the correct pattern for displaying actions:
 * 1. Call useActionDecisions hook to get decisions from server
 * 2. Render actions based on allowed/blocked status
 * 3. Show disabled reason for blocked actions
 * 4. Group by tier (primary, conditional, rare)
 */

import React from 'react';
import { useActionDecisions, EntityInput, ActionDecision } from '@/lib/microactions/hooks';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { LockIcon, InfoIcon, ChevronDown } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface ActionPanelProps {
  /** Detected user intents from search/context */
  detected_intents?: string[];
  /** Entities in context */
  entities?: EntityInput[];
  /** Handler when action is clicked */
  onAction: (actionName: string, decision: ActionDecision) => void;
  /** Show confidence indicators (dev mode) */
  showConfidence?: boolean;
  /** Additional class name */
  className?: string;
}

/**
 * Renders action buttons grouped by tier per E020:
 * - Primary: First in list, solid button
 * - Conditional: After primary, outline button
 * - Rare: In overflow dropdown
 */
export function ActionPanel({
  detected_intents = [],
  entities = [],
  onAction,
  showConfidence = false,
  className = '',
}: ActionPanelProps) {
  const {
    byTier,
    isAllowed,
    getDisabledReason,
    isLoading,
    error,
  } = useActionDecisions({
    detected_intents,
    entities,
    include_blocked: true,
  });

  if (isLoading) {
    return (
      <div className={`flex gap-2 ${className}`}>
        <div className="h-9 w-24 animate-pulse bg-muted rounded" />
        <div className="h-9 w-24 animate-pulse bg-muted rounded" />
      </div>
    );
  }

  if (error) {
    console.error('[ActionPanel] Decision fetch error:', error);
    // Graceful degradation - show nothing rather than broken UI
    return null;
  }

  const { primary, conditional, rare } = byTier;

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {/* Primary tier - always visible if allowed */}
      {primary.map((decision) => (
        <ActionButton
          key={decision.action}
          decision={decision}
          variant="primary"
          onClick={() => onAction(decision.action, decision)}
          showConfidence={showConfidence}
        />
      ))}

      {/* Conditional tier - shown inline if space, max 2 visible */}
      {conditional.slice(0, 2).map((decision) => (
        <ActionButton
          key={decision.action}
          decision={decision}
          variant="secondary"
          onClick={() => onAction(decision.action, decision)}
          showConfidence={showConfidence}
        />
      ))}

      {/* More conditional actions in dropdown */}
      {conditional.length > 2 && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              More <ChevronDown className="ml-1 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {conditional.slice(2).map((decision) => (
              <DropdownMenuItem
                key={decision.action}
                onClick={() => onAction(decision.action, decision)}
              >
                {formatActionLabel(decision.action)}
                {showConfidence && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({Math.round(decision.confidence * 100)}%)
                  </span>
                )}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}

      {/* Rare tier - always in dropdown */}
      {rare.length > 0 && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <InfoIcon className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {rare.map((decision) => (
              <DropdownMenuItem
                key={decision.action}
                onClick={() => onAction(decision.action, decision)}
              >
                {formatActionLabel(decision.action)}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}

interface ActionButtonProps {
  decision: ActionDecision;
  variant: 'primary' | 'secondary' | 'ghost';
  onClick: () => void;
  showConfidence?: boolean;
}

function ActionButton({
  decision,
  variant,
  onClick,
  showConfidence,
}: ActionButtonProps) {
  const label = formatActionLabel(decision.action);
  const disabled = !decision.allowed;
  const disabledReason = decision.blocked_by?.detail;

  if (disabled && disabledReason) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span>
            <Button variant={variant} size="sm" disabled>
              <LockIcon className="mr-1 h-3 w-3" />
              {label}
            </Button>
          </span>
        </TooltipTrigger>
        <TooltipContent>
          <p>{disabledReason}</p>
        </TooltipContent>
      </Tooltip>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant={variant}
          size="sm"
          onClick={onClick}
          disabled={disabled}
        >
          {label}
          {showConfidence && (
            <span className="ml-1 text-xs opacity-60">
              {Math.round(decision.confidence * 100)}%
            </span>
          )}
        </Button>
      </TooltipTrigger>
      <TooltipContent>
        <p className="font-medium">{decision.explanation || label}</p>
        {decision.reasons.length > 0 && (
          <ul className="mt-1 text-xs text-muted-foreground">
            {decision.reasons.slice(0, 2).map((reason, i) => (
              <li key={i}>• {reason}</li>
            ))}
          </ul>
        )}
      </TooltipContent>
    </Tooltip>
  );
}

/**
 * Format action name to human-readable label
 */
function formatActionLabel(actionName: string): string {
  return actionName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace('Work Order', 'WO')
    .replace('From Fault', '');
}

export default ActionPanel;

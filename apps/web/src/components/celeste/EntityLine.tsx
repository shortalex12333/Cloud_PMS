'use client';

/**
 * EntityLine
 * Shows what Celeste understood from the query.
 * Grounds trust before action.
 *
 * Rules (from UX spec):
 * - Lives directly under search bar
 * - Smaller text than results
 * - Neutral color
 * - No icons
 * - No interactivity (read-only)
 *
 * Brand tokens: semantic.textMuted (#86868B), semantic.textSecondary (#98989F)
 */

import { cn } from '@/lib/utils';

interface Entity {
  label: string;
  value: string;
}

interface UncertainMatch {
  type: string;
  value: string;
}

interface EntityLineProps {
  entities?: Entity[];
  uncertainMatches?: UncertainMatch[];
  className?: string;
}

export default function EntityLine({
  entities,
  uncertainMatches,
  className,
}: EntityLineProps) {
  const hasEntities = entities && entities.length > 0;
  const hasUncertainty = uncertainMatches && uncertainMatches.length > 0;

  if (!hasEntities && !hasUncertainty) return null;

  return (
    <div
      className={cn(
        'px-4 py-2',
        'text-celeste-sm text-celeste-text-muted',
        'font-body',
        className
      )}
    >
      {hasEntities && (
        <div>
          <span className="text-celeste-text-secondary">Understood:</span>
          <ul className="mt-1 space-y-0.5">
            {entities.map((entity, i) => (
              <li key={i}>
                • {entity.label}: {entity.value}
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasUncertainty && (
        <div className={hasEntities ? 'mt-2' : ''}>
          <span className="text-celeste-text-secondary">Possible matches:</span>
          <ul className="mt-1 space-y-0.5">
            {uncertainMatches.map((match, i) => (
              <li key={i}>
                • {match.type}: {match.value}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

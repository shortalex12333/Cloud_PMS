import * as React from 'react';
import { cn } from '@/lib/utils';

/**
 * SectionContainer - Card container with optional sticky header
 * Uses semantic design tokens exclusively - zero raw hex values.
 *
 * @example
 * <SectionContainer
 *   title="Work Orders"
 *   icon={<WrenchIcon />}
 *   count={12}
 *   action={{ label: "Add", onClick: () => {} }}
 * >
 *   <WorkOrderList />
 * </SectionContainer>
 */
export interface SectionContainerProps {
  title: string;
  icon?: React.ReactNode;
  count?: number;
  action?: { label: string; onClick: () => void };
  children: React.ReactNode;
  className?: string;
}

export const SectionContainer = React.forwardRef<
  HTMLDivElement,
  SectionContainerProps
>(({ title, icon, count, action, children, className }, ref) => {
  const [isPinned, setIsPinned] = React.useState(false);
  const headerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const header = headerRef.current;
    if (!header) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        // When header is stuck (not intersecting at its natural position)
        setIsPinned(!entry.isIntersecting);
      },
      {
        threshold: 1,
        rootMargin: '-1px 0px 0px 0px',
      }
    );

    observer.observe(header);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={cn(
        // Container: surface primary with rounded corners
        'bg-surface-primary rounded-md overflow-hidden',
        className
      )}
    >
      {/* Sticky header - 44px height */}
      <div
        ref={headerRef}
        className={cn(
          // Header layout
          'sticky top-0 z-10 flex items-center justify-between',
          'h-11 px-4',
          // Transitions between states
          'transition-colors duration-200',
          // Normal state: transparent/surface-primary
          // Pinned state: elevated surface
          isPinned ? 'bg-surface-elevated' : 'bg-surface-primary',
          // Bottom border when pinned for visual separation
          isPinned && 'border-b border-surface-border'
        )}
      >
        <div className="flex items-center gap-2">
          {icon && (
            <span className="text-txt-secondary flex-shrink-0">{icon}</span>
          )}
          <h2 className="text-[14px] font-semibold text-txt-primary">{title}</h2>
          {typeof count === 'number' && (
            <span className="text-[12px] text-txt-tertiary font-medium">
              ({count})
            </span>
          )}
        </div>

        {action && (
          <button
            onClick={action.onClick}
            className={cn(
              // Ghost button style for action
              'text-[13px] font-medium text-brand-interactive',
              'hover:text-brand-hover transition-colors',
              'px-2 py-1 -mr-2 rounded-sm',
              'hover:bg-brand-muted'
            )}
          >
            {action.label}
          </button>
        )}
      </div>

      {/* Content area */}
      <div className="px-4 pb-4">{children}</div>
    </div>
  );
});

SectionContainer.displayName = 'SectionContainer';

export default SectionContainer;

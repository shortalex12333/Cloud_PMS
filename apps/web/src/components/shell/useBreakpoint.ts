'use client';

/**
 * useBreakpoint — responsive breakpoint hook for the shell layout
 *
 * Breakpoints (per V5 spec):
 *   1280px+: full 3-column Vessel Surface grid, sidebar visible
 *   1024px–1279px: 2-column Surface grid, sidebar visible
 *   < 1024px: single column Surface, sidebar collapses to icon-only
 */

import * as React from 'react';

type Breakpoint = 'wide' | 'medium' | 'narrow';

export function useBreakpoint(): Breakpoint {
  const [bp, setBp] = React.useState<Breakpoint>('wide');

  React.useEffect(() => {
    function update() {
      const w = window.innerWidth;
      if (w >= 1280) setBp('wide');
      else if (w >= 1024) setBp('medium');
      else setBp('narrow');
    }
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  return bp;
}

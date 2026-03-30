'use client';

/**
 * useBreakpoint — responsive breakpoint hook for the shell layout
 *
 * Breakpoints (per V5 spec + V2 review §04):
 *   1280px+ (desktop): full 3-column Surface, 192px sidebar, full topbar
 *   1024–1279px (laptop): 2-column Surface, 192px sidebar, full topbar
 *   900–1023px (tablet-lg): 2-column Surface, 48px icon sidebar, compact topbar
 *   640–899px (tablet): 1-column Surface, 48px icon sidebar, compact topbar
 *   < 640px (mobile): 1-column Surface, no sidebar (hamburger), minimal topbar
 */

import * as React from 'react';

export type Breakpoint = 'desktop' | 'laptop' | 'tablet' | 'mobile';

export function useBreakpoint(): Breakpoint {
  const [bp, setBp] = React.useState<Breakpoint>('desktop');

  React.useEffect(() => {
    function update() {
      const w = window.innerWidth;
      if (w >= 1280) setBp('desktop');
      else if (w >= 900) setBp('laptop');
      else if (w >= 640) setBp('tablet');
      else setBp('mobile');
    }
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  return bp;
}

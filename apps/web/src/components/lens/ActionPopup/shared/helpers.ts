import s from '../../popup.module.css';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const BACKDROP_CLASS: Record<string, string> = {
  read: s.backdropRead,
  l0: s.backdropRead,
  l1: s.backdropL1,
  l2: s.backdropL2,
  l3: s.backdropL3,
  l4: s.backdropL4,
  l5: s.backdropL5,
};

export function backdropClass(mode: 'read' | 'mutate', level: number): string {
  if (mode === 'read') return BACKDROP_CLASS.read;
  return BACKDROP_CLASS[`l${level}`] ?? BACKDROP_CLASS.l1;
}

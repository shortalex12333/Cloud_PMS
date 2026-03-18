/**
 * Lens Palette Config
 * Each route gets an ambient color identity — three orbs (top-left, bottom-right, center).
 * Only colors change between lenses; positions are fixed so transitions feel calm.
 */

export interface LensPalette {
  label: string;
  /** [primary, secondary, accent] — rgba strings for the three orbs */
  orbs: [string, string, string];
}

/** Route prefix → palette */
export const LENS_PALETTES: Record<string, LensPalette> = {
  default: {
    label: 'Dashboard',
    orbs: [
      'rgba(58, 124, 157, 0.60)',   // brand teal — top-left
      'rgba(30, 90, 130, 0.45)',    // deep teal — bottom-right
      'rgba(20, 70, 110, 0.28)',    // midnight blue — center
    ],
  },
  faults: {
    label: 'Faults',
    orbs: [
      'rgba(200, 100, 30, 0.60)',   // amber-orange — urgency
      'rgba(160, 60, 20, 0.45)',    // deep burnt
      'rgba(180, 50, 10, 0.28)',    // ember red — center
    ],
  },
  equipment: {
    label: 'Equipment',
    orbs: [
      'rgba(60, 100, 150, 0.60)',   // steel blue
      'rgba(40, 70, 120, 0.45)',    // deep navy steel
      'rgba(30, 60, 110, 0.28)',    // dark machine blue
    ],
  },
  inventory: {
    label: 'Inventory / Parts',
    orbs: [
      'rgba(50, 90, 140, 0.60)',    // slate blue — precision
      'rgba(30, 60, 110, 0.45)',    // deep slate
      'rgba(20, 50, 100, 0.28)',    // midnight slate
    ],
  },
  certificates: {
    label: 'Certificates',
    orbs: [
      'rgba(30, 140, 90, 0.60)',    // emerald — compliance/green flag
      'rgba(20, 110, 70, 0.45)',    // deep emerald
      'rgba(15, 90, 60, 0.28)',     // forest center
    ],
  },
  documents: {
    label: 'Documents',
    orbs: [
      'rgba(70, 90, 160, 0.60)',    // indigo — paperwork
      'rgba(50, 70, 140, 0.45)',    // deep indigo
      'rgba(40, 60, 130, 0.28)',    // midnight indigo
    ],
  },
  email: {
    label: 'Email',
    orbs: [
      'rgba(120, 70, 160, 0.60)',   // violet — communication
      'rgba(90, 50, 140, 0.45)',    // deep violet
      'rgba(70, 40, 130, 0.28)',    // dark purple center
    ],
  },
  purchasing: {
    label: 'Purchasing',
    orbs: [
      'rgba(140, 100, 30, 0.60)',   // gold — commerce
      'rgba(110, 80, 20, 0.45)',    // deep gold
      'rgba(90, 60, 15, 0.28)',     // antique center
    ],
  },
  'shopping-list': {
    label: 'Shopping List',
    orbs: [
      'rgba(150, 120, 30, 0.60)',   // warm amber
      'rgba(120, 95, 20, 0.45)',    // deep warm
      'rgba(100, 75, 15, 0.28)',    // honey center
    ],
  },
  receiving: {
    label: 'Receiving',
    orbs: [
      'rgba(20, 140, 160, 0.60)',   // cyan — incoming / arrival
      'rgba(15, 110, 130, 0.45)',   // deep cyan
      'rgba(10, 90, 110, 0.28)',    // dark teal center
    ],
  },
  'hours-of-rest': {
    label: 'Hours of Rest',
    orbs: [
      'rgba(20, 50, 100, 0.60)',    // deep navy — calm/sleep
      'rgba(15, 35, 80, 0.45)',     // deeper navy
      'rgba(10, 25, 70, 0.28)',     // midnight center
    ],
  },
  warranties: {
    label: 'Warranties',
    orbs: [
      'rgba(160, 40, 40, 0.60)',    // dignified red — risk/alerts
      'rgba(130, 30, 30, 0.45)',    // deep red
      'rgba(110, 20, 20, 0.28)',    // dark crimson center
    ],
  },
};

/** Match a pathname to a palette. Falls back to default. */
export function matchLensPalette(pathname: string): LensPalette {
  // Exact or prefix matches
  const segments: [string, string][] = [
    ['/faults', 'faults'],
    ['/equipment', 'equipment'],
    ['/inventory', 'inventory'],
    ['/parts', 'inventory'],
    ['/certificates', 'certificates'],
    ['/documents', 'documents'],
    ['/email', 'email'],
    ['/purchasing', 'purchasing'],
    ['/shopping-list', 'shopping-list'],
    ['/receiving', 'receiving'],
    ['/hours-of-rest', 'hours-of-rest'],
    ['/warranties', 'warranties'],
  ];

  for (const [prefix, key] of segments) {
    if (pathname.startsWith(prefix)) {
      return LENS_PALETTES[key];
    }
  }

  return LENS_PALETTES.default;
}

/** Scoring engine for the Needs Attention system */

import type { EntitySource, CrewRole, Severity } from './types';

// ── Role Visibility Matrix ──
// true = visible, 'dept' = filtered by department, 'assigned' = filtered by assigned_to, 'own' = filtered by user_id
type Scope = true | 'dept' | 'assigned' | 'own';

const ROLE_VISIBILITY: Record<CrewRole, Partial<Record<EntitySource, Scope>>> = {
  captain: {
    fault: true, work_order: true, parts: true, certificate: true,
    equipment: true, hor_warning: true, hor_signoff: true,
    receiving: true, handover: true, shopping_list: true,
  },
  chief_engineer: {
    fault: true, work_order: true, parts: true, equipment: true,
    hor_warning: 'dept', hor_signoff: 'dept',
    receiving: true, handover: true, shopping_list: true,
  },
  eto: {
    fault: true, work_order: true, parts: true, equipment: true,
    hor_warning: 'dept', hor_signoff: 'dept',
  },
  manager: {
    work_order: true, parts: true, certificate: true,
    hor_warning: 'dept', hor_signoff: 'dept',
    receiving: true, shopping_list: true,
  },
  engineer: {
    fault: 'dept', work_order: 'assigned', parts: true,
    equipment: true, hor_warning: 'own', handover: true,
  },
  crew: {
    work_order: 'assigned', hor_warning: 'own',
  },
  deck: {
    work_order: 'assigned', hor_warning: 'own',
  },
  interior: {
    work_order: 'assigned', hor_warning: 'own',
  },
};

// ── Role Priority Boost (+15 to final score) ──
const ROLE_PRIORITY_BOOST: Record<CrewRole, EntitySource[]> = {
  captain: ['certificate', 'hor_signoff', 'handover'],
  chief_engineer: ['fault', 'equipment', 'parts'],
  eto: ['fault', 'equipment'],
  manager: ['receiving', 'shopping_list', 'certificate'],
  engineer: ['work_order', 'fault'],
  crew: ['hor_warning', 'work_order'],
  deck: ['hor_warning', 'work_order'],
  interior: ['hor_warning', 'work_order'],
};

// ── Time-of-Day Boosts ──
type TodBucket = 'morning' | 'afternoon' | 'evening';

const TOD_BOOSTS: Record<TodBucket, Partial<Record<EntitySource, number>>> = {
  morning:   { handover: 100, hor_signoff: 90, fault: 80 },
  afternoon: { work_order: 100, parts: 90, receiving: 80 },
  evening:   { hor_warning: 100, hor_signoff: 90, certificate: 80 },
};

function getTodBucket(hour: number): TodBucket {
  if (hour >= 6 && hour < 12) return 'morning';
  if (hour >= 12 && hour < 18) return 'afternoon';
  return 'evening';
}

// ── Public API ──

export function isSourceVisible(role: CrewRole, source: EntitySource): boolean {
  const normalised = normaliseRole(role);
  return !!ROLE_VISIBILITY[normalised]?.[source];
}

export function getSourceScope(role: CrewRole, source: EntitySource): Scope | undefined {
  const normalised = normaliseRole(role);
  return ROLE_VISIBILITY[normalised]?.[source];
}

export function normaliseRole(role: string): CrewRole {
  const lower = role.toLowerCase().replace(/\s+/g, '_');
  if (lower in ROLE_VISIBILITY) return lower as CrewRole;
  // Map common variants
  if (lower === 'chief_eng' || lower === 'chiefengineer') return 'chief_engineer';
  if (lower === 'member' || lower === 'steward' || lower === 'cook' || lower === 'bosun') return 'crew';
  if (lower === 'deckhand') return 'deck';
  return 'crew'; // safe default
}

export function computeScore(
  source: EntitySource,
  baseSeverity: number,
  timeUrgency: number,
  role: CrewRole,
): number {
  const hour = new Date().getHours();
  const bucket = getTodBucket(hour);
  const todScore = TOD_BOOSTS[bucket][source] ?? 40;

  // Role relevance: visible = 80, boosted sources = 100
  const boosted = ROLE_PRIORITY_BOOST[role]?.includes(source);
  const roleRelevance = boosted ? 100 : 80;

  let score = baseSeverity * 0.40 + timeUrgency * 0.25 + roleRelevance * 0.20 + todScore * 0.15;

  // Role priority boost
  if (boosted) score += 15;

  return Math.min(100, Math.round(score));
}

// ── Severity Mappers ──

export function faultSeverityScore(severity: string | null): number {
  // DB enum: low, medium, high (no 'critical' in pms_faults)
  switch (severity?.toLowerCase()) {
    case 'high': return 90;
    case 'medium': return 55;
    case 'low': return 25;
    default: return 55;
  }
}

export function faultToSeverity(severity: string | null): Severity {
  // DB enum: low, medium, high (no 'critical' in pms_faults)
  switch (severity?.toLowerCase()) {
    case 'high': return 'critical';
    case 'medium': return 'warning';
    default: return 'info';
  }
}

export function woSeverityScore(priority: string | null, isOverdue: boolean): number {
  // DB enum: routine, important, critical, emergency
  const p = priority?.toLowerCase();
  if (p === 'emergency' && isOverdue) return 100;
  if (p === 'emergency') return 95;
  if (p === 'critical' && isOverdue) return 90;
  if (p === 'critical') return 85;
  if (isOverdue) return 75;
  if (p === 'important') return 65;
  return 45; // routine
}

export function certSeverityScore(daysUntilExpiry: number): number {
  if (daysUntilExpiry <= 0) return 100;
  if (daysUntilExpiry <= 7) return 90;
  if (daysUntilExpiry <= 30) return 70;
  return 40;
}

export function certToSeverity(daysUntilExpiry: number): Severity {
  if (daysUntilExpiry <= 0) return 'critical';
  if (daysUntilExpiry <= 7) return 'critical';
  if (daysUntilExpiry <= 30) return 'warning';
  return 'info';
}

// ── Time Urgency ──

export function eventTimeUrgency(dateStr: string | null): number {
  if (!dateStr) return 15;
  const hoursAgo = (Date.now() - new Date(dateStr).getTime()) / 3_600_000;
  if (hoursAgo < 1) return 100;
  if (hoursAgo < 6) return 90;
  if (hoursAgo < 24) return 75;
  if (hoursAgo < 72) return 55;
  if (hoursAgo < 168) return 35;
  return 15;
}

export function deadlineTimeUrgency(dateStr: string | null): number {
  if (!dateStr) return 15;
  const hoursUntil = (new Date(dateStr).getTime() - Date.now()) / 3_600_000;
  if (hoursUntil <= 0) return 100;
  if (hoursUntil < 24) return 90;
  if (hoursUntil < 72) return 75;
  if (hoursUntil < 168) return 55;
  if (hoursUntil < 720) return 35;
  return 15;
}

export function timeDelta(date: string | null): string {
  if (!date) return '';
  const diff = Date.now() - new Date(date).getTime();
  const absDiff = Math.abs(diff);
  const days = Math.floor(absDiff / 86_400_000);
  const hours = Math.floor(absDiff / 3_600_000);

  if (diff < 0) {
    // Future date
    if (days > 0) return `in ${days}d`;
    if (hours > 0) return `in ${hours}h`;
    return 'soon';
  }
  // Past date
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  return 'now';
}

// ── Pill Configs per Role ──

import type { PillConfig, CrewRole as CR } from './types';

export const ROLE_PILLS: Record<CR, PillConfig[]> = {
  captain: [
    { label: 'Certificates', countKey: 'certificates', route: '/certificates' },
    { label: 'Open Faults', countKey: 'faults', route: '/faults' },
    { label: 'HoR Compliance', countKey: 'hor_signoffs', route: '/hours-of-rest/signoffs' },
    { label: 'All W/O', countKey: 'work_orders', route: '/work-orders' },
    { label: 'Handover', countKey: 'handover', route: '/work-orders' },
    { label: 'Log HoR', countKey: null, route: '/hours-of-rest', action: true },
  ],
  chief_engineer: [
    { label: 'Faults', countKey: 'faults', route: '/faults' },
    { label: 'Overdue W/O', countKey: 'work_orders', route: '/work-orders' },
    { label: 'Low Stock', countKey: 'parts', route: '/inventory' },
    { label: 'Receiving', countKey: 'receiving', route: '/receiving' },
    { label: 'Log HoR', countKey: null, route: '/hours-of-rest', action: true },
  ],
  eto: [
    { label: 'Faults', countKey: 'faults', route: '/faults' },
    { label: 'Overdue W/O', countKey: 'work_orders', route: '/work-orders' },
    { label: 'Low Stock', countKey: 'parts', route: '/inventory' },
    { label: 'Log HoR', countKey: null, route: '/hours-of-rest', action: true },
  ],
  manager: [
    { label: 'Receiving', countKey: 'receiving', route: '/receiving' },
    { label: 'Shopping List', countKey: 'shopping_list', route: '/shopping-list' },
    { label: 'Certificates', countKey: 'certificates', route: '/certificates' },
    { label: 'W/O', countKey: 'work_orders', route: '/work-orders' },
    { label: 'Log HoR', countKey: null, route: '/hours-of-rest', action: true },
  ],
  engineer: [
    { label: 'My W/O', countKey: 'work_orders', route: '/work-orders' },
    { label: 'Open Faults', countKey: 'faults', route: '/faults' },
    { label: 'Log HoR', countKey: null, route: '/hours-of-rest', action: true },
  ],
  crew: [
    { label: 'My Tasks', countKey: 'work_orders', route: '/work-orders' },
    { label: 'Log HoR', countKey: null, route: '/hours-of-rest', action: true },
  ],
  deck: [
    { label: 'My Tasks', countKey: 'work_orders', route: '/work-orders' },
    { label: 'Log HoR', countKey: null, route: '/hours-of-rest', action: true },
  ],
  interior: [
    { label: 'My Tasks', countKey: 'work_orders', route: '/work-orders' },
    { label: 'Log HoR', countKey: null, route: '/hours-of-rest', action: true },
  ],
};

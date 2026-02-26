export const DOMAIN_CATALOG = {
  '/work-orders':   { objectType: 'pms_work_orders',    label: 'Work Orders',   apiPath: '/v1/work-orders' },
  '/faults':        { objectType: 'pms_faults',         label: 'Faults',        apiPath: '/v1/faults' },
  '/equipment':     { objectType: 'pms_equipment',      label: 'Equipment',     apiPath: '/v1/equipment' },
  '/inventory':     { objectType: 'pms_parts',          label: 'Inventory',     apiPath: '/v1/parts' },
  '/receiving':     { objectType: 'pms_receiving',      label: 'Receiving',     apiPath: '/v1/receiving' },
  '/shopping-list': { objectType: 'pms_shopping_list',  label: 'Shopping List', apiPath: '/v1/shopping-list' },
  '/email':         { objectType: 'email_threads',      label: 'Email',         apiPath: '/v1/email' },
} as const;

export type DomainRoute = keyof typeof DOMAIN_CATALOG;
export type DomainConfig = typeof DOMAIN_CATALOG[DomainRoute];
export type ObjectType = DomainConfig['objectType'];

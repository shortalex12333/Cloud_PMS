import type { ListRecord } from '../DomainListView';

export const MOCK_CERTIFICATE_RECORDS: ListRecord[] = [
  { id: 'C-004', ref: 'C\u00b7004', title: 'Safety Equipment Certificate', meta: 'Expires 8 Apr 2026 \u00b7 Lloyd\u2019s Register', assignedTo: undefined, status: 'Expiring', statusVariant: 'warn', severity: 'warning', age: '12d', searchText: 'c-004 safety equipment certificate expiring lloyds register 8 apr' },
  { id: 'C-009', ref: 'C\u00b7009', title: 'ISM Document of Compliance', meta: 'Expires 3 May 2026 \u00b7 Flag State', assignedTo: undefined, status: 'Expiring', statusVariant: 'warn', severity: 'warning', age: '38d', searchText: 'c-009 ism document compliance expiring flag state 3 may' },
  { id: 'C-001', ref: 'C\u00b7001', title: 'Certificate of Registry', meta: 'Expires 15 Dec 2026 \u00b7 Cayman Islands', assignedTo: undefined, status: 'Valid', statusVariant: 'open', age: '\u2014', searchText: 'c-001 certificate of registry valid cayman islands 15 dec' },
  { id: 'C-006', ref: 'C\u00b7006', title: 'IOPP Certificate', meta: 'Expires 22 Nov 2026 \u00b7 DNV', assignedTo: undefined, status: 'Valid', statusVariant: 'open', age: '\u2014', searchText: 'c-006 iopp certificate valid dnv 22 nov' },
  { id: 'C-011', ref: 'C\u00b7011', title: 'MLC Maritime Labour Certificate', meta: 'Expires 30 Sep 2026 \u00b7 Flag State', assignedTo: undefined, status: 'Valid', statusVariant: 'open', age: '\u2014', searchText: 'c-011 mlc maritime labour certificate valid flag state 30 sep' },
];

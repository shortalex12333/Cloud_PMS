import type { ListRecord } from '../DomainListView';

export const MOCK_WARRANTY_RECORDS: ListRecord[] = [
  { id: 'W-008', ref: 'W\u00b7008', title: 'CAT C32 Extended Warranty', meta: 'E-007 Main Engine \u00b7 Caterpillar Marine \u00b7 Expires 15 Jun 2027', assignedTo: undefined, status: 'Active', statusVariant: 'signed', age: '\u2014', searchText: 'w-008 cat c32 extended warranty e-007 main engine caterpillar marine active' },
  { id: 'W-005', ref: 'W\u00b7005', title: 'Watermaker Membrane Warranty', meta: 'E-022 Watermaker \u00b7 Village Marine \u00b7 Expires 1 Apr 2026', assignedTo: undefined, status: 'Expiring', statusVariant: 'warn', severity: 'warning', age: '5d', searchText: 'w-005 watermaker membrane warranty e-022 village marine expiring' },
  { id: 'W-012', ref: 'W\u00b7012', title: 'AC Unit 3 Compressor', meta: 'E-041 AC Unit 3 \u00b7 Marine Air \u00b7 Claimed 12 Mar', assignedTo: 'R. Costa', status: 'Claimed', statusVariant: 'pending', age: '15d', searchText: 'w-012 ac unit 3 compressor e-041 marine air claimed' },
  { id: 'W-003', ref: 'W\u00b7003', title: 'Bow Thruster Motor', meta: 'E-019 Bow Thruster \u00b7 Vetus \u00b7 Expired 28 Feb 2026', assignedTo: undefined, status: 'Expired', statusVariant: 'critical', severity: 'critical', age: '27d', searchText: 'w-003 bow thruster motor e-019 vetus expired' },
];

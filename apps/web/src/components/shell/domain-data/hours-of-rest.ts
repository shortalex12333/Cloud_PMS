import type { ListRecord } from '../DomainListView';

export const MOCK_HOURS_OF_REST_RECORDS: ListRecord[] = [
  { id: 'HOR-0327-MC', ref: 'HOR\u00b70327', title: 'Morrison, J. \u2014 27 Mar 2026', meta: 'Deck \u00b7 10h work \u00b7 14h rest', assignedTo: 'J. Morrison', status: 'Compliant', statusVariant: 'signed', age: '0d', searchText: 'hor-0327 morrison deck compliant 27 mar' },
  { id: 'HOR-0327-RC', ref: 'HOR\u00b70327', title: 'Costa, R. \u2014 27 Mar 2026', meta: 'Engine \u00b7 12h work \u00b7 12h rest', assignedTo: 'R. Costa', status: 'Compliant', statusVariant: 'signed', age: '0d', searchText: 'hor-0327 costa engine compliant 27 mar' },
  { id: 'HOR-0326-MC', ref: 'HOR\u00b70326', title: 'Morrison, J. \u2014 26 Mar 2026', meta: 'Deck \u00b7 14h work \u00b7 10h rest \u00b7 BELOW THRESHOLD', assignedTo: 'J. Morrison', status: 'Non-Compliant', statusVariant: 'critical', severity: 'critical', age: '1d', searchText: 'hor-0326 morrison deck non-compliant below threshold 26 mar' },
  { id: 'HOR-0325-PS', ref: 'HOR\u00b70325', title: 'Pending Sign-off \u2014 25 Mar', meta: '3 crew members unsigned', assignedTo: undefined, status: 'Pending', statusVariant: 'pending', age: '2d', searchText: 'hor-0325 pending sign-off unsigned 25 mar' },
];

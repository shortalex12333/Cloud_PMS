import type { ListRecord } from '../DomainListView';

export const MOCK_HANDOVER_RECORDS: ListRecord[] = [
  { id: 'HO-019', ref: 'HO\u00b7019', title: 'Morrison \u2192 Costa', meta: '22 Mar 2026 \u00b7 Full vessel handover', assignedTo: 'R. Costa', status: 'Signed', statusVariant: 'signed', severity: 'info', age: '5d', searchText: 'ho-019 morrison costa full vessel handover signed' },
  { id: 'HO-018', ref: 'HO\u00b7018', title: 'Costa \u2192 Morrison', meta: '15 Feb 2026 \u00b7 Full vessel handover', assignedTo: 'J. Morrison', status: 'Signed', statusVariant: 'signed', age: '40d', searchText: 'ho-018 costa morrison full vessel handover signed' },
  { id: 'HO-017', ref: 'HO\u00b7017', title: 'Morrison \u2192 Costa', meta: '10 Jan 2026 \u00b7 Full vessel handover', assignedTo: 'R. Costa', status: 'Signed', statusVariant: 'signed', age: '76d', searchText: 'ho-017 morrison costa full vessel handover signed' },
];

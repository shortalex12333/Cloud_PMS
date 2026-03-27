import type { ListRecord } from '../DomainListView';

export const MOCK_RECEIVING_RECORDS: ListRecord[] = [
  { id: 'RX-031', ref: 'RX\u00b7031', title: 'PO-0086 \u2014 FilterMax GmbH', meta: '2 items received \u00b7 18 Mar 2026 \u00b7 Inspected', assignedTo: 'J. Morrison', status: 'Accepted', statusVariant: 'signed', age: '9d', searchText: 'rx-031 po-0086 filtermax gmbh received inspected accepted' },
  { id: 'RX-030', ref: 'RX\u00b7030', title: 'PO-0084 \u2014 Marine Parts Co.', meta: '1 item \u00b7 15 Mar 2026 \u00b7 Quantity mismatch', assignedTo: 'R. Costa', status: 'Rejected', statusVariant: 'critical', severity: 'critical', age: '12d', searchText: 'rx-030 po-0084 marine parts co quantity mismatch rejected' },
  { id: 'RX-029', ref: 'RX\u00b7029', title: 'PO-0088 \u2014 Pending Delivery', meta: 'Expected 28 Mar 2026', assignedTo: undefined, status: 'Pending', statusVariant: 'pending', age: '1d', searchText: 'rx-029 po-0088 pending delivery expected 28 mar' },
];

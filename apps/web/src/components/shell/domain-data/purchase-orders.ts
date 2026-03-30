import type { ListRecord } from '../DomainListView';

export const MOCK_PURCHASE_ORDER_RECORDS: ListRecord[] = [
  { id: 'PO-0088', ref: 'PO\u00b70088', title: 'Marine Parts Co. \u2014 Engine Spares', meta: '3 line items \u00b7 \u20ac1,240.00 \u00b7 Sent 20 Mar', assignedTo: 'J. Morrison', status: 'Sent', statusVariant: 'pending', age: '7d', searchText: 'po-0088 marine parts co engine spares sent' },
  { id: 'PO-0087', ref: 'PO\u00b70087', title: 'Yacht Supplies Ltd \u2014 Anodes', meta: '1 line item \u00b7 \u20ac320.00 \u00b7 Overdue delivery', assignedTo: 'R. Costa', status: 'Overdue', statusVariant: 'overdue', severity: 'critical', age: '14d', searchText: 'po-0087 yacht supplies ltd anodes overdue delivery' },
  { id: 'PO-0086', ref: 'PO\u00b70086', title: 'FilterMax GmbH \u2014 Filters', meta: '2 line items \u00b7 \u20ac186.00 \u00b7 Received 18 Mar', assignedTo: 'J. Morrison', status: 'Received', statusVariant: 'signed', age: '9d', searchText: 'po-0086 filtermax gmbh filters received' },
  { id: 'PO-0085', ref: 'PO\u00b70085', title: 'Draft \u2014 Navigation Bulbs', meta: '1 line item \u00b7 \u20ac42.00 \u00b7 Not yet sent', assignedTo: undefined, status: 'Draft', statusVariant: 'open', age: '2d', searchText: 'po-0085 draft navigation bulbs not sent' },
];

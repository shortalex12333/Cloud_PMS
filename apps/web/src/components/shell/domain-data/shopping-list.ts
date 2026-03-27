import type { ListRecord } from '../DomainListView';

export const MOCK_SHOPPING_LIST_RECORDS: ListRecord[] = [
  { id: 'SL-042', ref: 'SL\u00b7042', title: 'Impeller \u2014 Jabsco 17937 \u00d72', meta: 'P-0312 \u00b7 Engine Room \u00b7 Zero stock', assignedTo: 'J. Morrison', status: 'Pending', statusVariant: 'pending', severity: 'critical', age: '3d', searchText: 'sl-042 impeller jabsco 17937 p-0312 engine room zero stock pending' },
  { id: 'SL-041', ref: 'SL\u00b7041', title: 'Oil Filter 20W-50 \u00d73', meta: 'P-0441 \u00b7 Engine Room', assignedTo: 'J. Morrison', status: 'Approved', statusVariant: 'signed', age: '5d', searchText: 'sl-041 oil filter 20w-50 p-0441 engine room approved' },
  { id: 'SL-040', ref: 'SL\u00b7040', title: 'Zinc Anode M8 \u00d74', meta: 'P-0587 \u00b7 Lazarette', assignedTo: undefined, status: 'Pending', statusVariant: 'pending', age: '8d', searchText: 'sl-040 zinc anode m8 p-0587 lazarette pending' },
  { id: 'SL-039', ref: 'SL\u00b7039', title: 'Raw Water Pump Seal Kit \u00d71', meta: 'P-0099 \u00b7 Engine Room', assignedTo: 'R. Costa', status: 'Ordered', statusVariant: 'open', age: '12d', searchText: 'sl-039 raw water pump seal kit p-0099 engine room ordered' },
];

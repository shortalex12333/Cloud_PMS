/**
 * Faults — static mock data for Phase 1E list view.
 * Replace with live data from ENGINEER01's
 * GET /api/vessel/{id}/domain/faults/records endpoint.
 */

import type { ListRecord } from '../DomainListView';

export const MOCK_FAULT_RECORDS: ListRecord[] = [
  {
    id: 'F-088',
    ref: 'F\u00b7088',
    title: 'Port Engine Abnormal Vibration',
    meta: 'E-007 Main Engine \u00b7 CRITICAL \u00b7 ESCALATED',
    assignedTo: 'J. Morrison',
    status: 'Critical',
    statusVariant: 'critical',
    severity: 'critical',
    age: '2d',
    searchText: 'f-088 f·088 port engine abnormal vibration e-007 main engine critical escalated j. morrison',
  },
  {
    id: 'F-085',
    ref: 'F\u00b7085',
    title: 'AC Unit 3 — Low Refrigerant',
    meta: 'E-041 AC Unit 3 \u00b7 WARNING \u00b7 MONITORING',
    assignedTo: 'R. Costa',
    status: 'Warning',
    statusVariant: 'warn',
    severity: 'warning',
    age: '4d',
    searchText: 'f-085 f·085 ac unit 3 low refrigerant e-041 warning monitoring r. costa',
  },
  {
    id: 'F-082',
    ref: 'F\u00b7082',
    title: 'Bow Thruster Seal Leak',
    meta: 'E-019 Bow Thruster \u00b7 OPEN',
    assignedTo: 'Unassigned',
    status: 'Open',
    statusVariant: 'open',
    age: '7d',
    searchText: 'f-082 f·082 bow thruster seal leak e-019 open unassigned',
  },
  {
    id: 'F-079',
    ref: 'F\u00b7079',
    title: 'Watermaker High Pressure Alarm',
    meta: 'E-022 Watermaker \u00b7 OPEN \u00b7 PENDING PARTS',
    assignedTo: 'J. Morrison',
    status: 'Open',
    statusVariant: 'open',
    age: '12d',
    searchText: 'f-079 f·079 watermaker high pressure alarm e-022 open pending parts j. morrison',
  },
  {
    id: 'F-076',
    ref: 'F\u00b7076',
    title: 'Stbd Generator Oil Pressure Sensor Drift',
    meta: 'E-012 Stbd Generator \u00b7 WARNING',
    assignedTo: 'R. Costa',
    status: 'Monitoring',
    statusVariant: 'monitor',
    severity: 'warning',
    age: '15d',
    searchText: 'f-076 f·076 stbd generator oil pressure sensor drift e-012 warning monitoring r. costa',
  },
];

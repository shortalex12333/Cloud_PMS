import type { ListRecord } from '../DomainListView';

export const MOCK_EQUIPMENT_RECORDS: ListRecord[] = [
  { id: 'E-007', ref: 'E\u00b7007', title: 'Main Engine', meta: 'CAT C32 \u00b7 Engine Room \u00b7 1 open fault', assignedTo: undefined, status: 'Fault Logged', statusVariant: 'critical', severity: 'critical', age: '2d', searchText: 'e-007 main engine cat c32 engine room fault logged critical' },
  { id: 'E-012', ref: 'E\u00b7012', title: 'Stbd Generator', meta: 'Onan 27kW \u00b7 Engine Room \u00b7 Service due', assignedTo: undefined, status: 'Due Service', statusVariant: 'warn', severity: 'warning', age: '2d', searchText: 'e-012 stbd generator onan 27kw engine room due service warning' },
  { id: 'E-019', ref: 'E\u00b7019', title: 'Bow Thruster', meta: 'Vetus 95kgf \u00b7 Bow \u00b7 1 open fault', assignedTo: undefined, status: 'Fault Logged', statusVariant: 'warn', severity: 'warning', age: '7d', searchText: 'e-019 bow thruster vetus 95kgf bow fault logged warning' },
  { id: 'E-022', ref: 'E\u00b7022', title: 'Watermaker', meta: 'Village Marine Tec \u00b7 Engine Room', assignedTo: undefined, status: 'Active', statusVariant: 'open', age: '\u2014', searchText: 'e-022 watermaker village marine tec engine room active' },
  { id: 'E-041', ref: 'E\u00b7041', title: 'AC Unit 3', meta: 'Marine Air 48k BTU \u00b7 Crew Mess', assignedTo: undefined, status: 'Active', statusVariant: 'open', age: '\u2014', searchText: 'e-041 ac unit 3 marine air 48k btu crew mess active' },
  { id: 'E-001', ref: 'E\u00b7001', title: 'Hull', meta: 'GRP \u00b7 56m LOA', assignedTo: undefined, status: 'Active', statusVariant: 'open', age: '\u2014', searchText: 'e-001 hull grp 56m loa active' },
];

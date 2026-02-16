/**
 * TEST PAGE: WorkOrderDetail Component
 *
 * Route: /test/work-order-detail
 * Purpose: Verify WorkOrderDetail component renders correctly in dark mode
 *
 * This page uses mock data to demonstrate the component without requiring
 * authentication or database access.
 */

'use client';

import { WorkOrderDetail, type WorkOrderData } from '@/components/cards/WorkOrderDetail';

// Mock data for testing
const mockWorkOrder: WorkOrderData = {
  id: '0142',
  title: 'Replace hydraulic pump seals',
  subtitle: 'Engine Room - Main Generator',
  status: 'In Progress',
  priority: 'High',
  createdAt: '2026-02-10 09:15',
  createdBy: 'Alex Chen',
  equipment: 'Caterpillar 3512B Generator',
  location: 'Engine Room - Starboard',
  category: 'Preventive Maintenance',
  dueDate: '2026-02-20',
  assignedTo: 'Marcus Webb',
  linkedFault: 'FLT-0089 - Oil leak detected',
  description: `During routine inspection, hydraulic pump seals showed signs of wear and minor leakage.

Scope of work:
1. Isolate hydraulic system
2. Drain hydraulic fluid into approved containers
3. Remove pump assembly
4. Replace all seals (kit P/N: HYD-SEAL-3512)
5. Reinstall pump and refill system
6. Bleed air from lines
7. Test under load for 30 minutes
8. Verify no leaks

Note: Coordinate with Chief Engineer before system isolation. Expected downtime: 4 hours.`,
  evidence: [
    {
      id: 'ev-001',
      type: 'email',
      title: 'Re: Generator maintenance schedule',
      timestamp: '2026-02-10 08:30',
      source: 'operations@yachtname.com',
    },
    {
      id: 'ev-002',
      type: 'photo',
      title: 'IMG_2024_hydraulic_leak.jpg',
      timestamp: '2026-02-09 14:22',
    },
    {
      id: 'ev-003',
      type: 'manual',
      title: 'Caterpillar 3512B Service Manual',
      timestamp: 'Section 4.3.2',
      source: 'Page 142',
    },
    {
      id: 'ev-004',
      type: 'log',
      title: 'Engine room inspection log',
      timestamp: '2026-02-09 11:00',
      source: 'Daily Rounds',
    },
  ],
  activity: [
    {
      id: 'act-001',
      timestamp: '2026-02-14 09:32',
      action: 'Status changed',
      user: 'Alex Chen',
      oldValue: 'Open',
      newValue: 'In Progress',
    },
    {
      id: 'act-002',
      timestamp: '2026-02-12 15:45',
      action: 'Assigned to Marcus Webb',
      user: 'Alex Chen',
    },
    {
      id: 'act-003',
      timestamp: '2026-02-10 09:15',
      action: 'Work order created',
      user: 'Alex Chen',
    },
  ],
};

export default function WorkOrderDetailTestPage() {
  return (
    <div className="min-h-screen bg-wo-bg-main dark">
      {/* Force dark mode for testing */}
      <div className="dark bg-wo-bg-main min-h-screen py-wo-py">
        <div className="max-w-wo-container mx-auto px-wo-px">
          {/* Page header */}
          <div className="mb-wo-gap">
            <h1 className="text-wo-text-primary font-semibold text-lg mb-2">
              WorkOrderDetail Component Test
            </h1>
            <p className="text-wo-text-meta text-sm">
              This page demonstrates the tokenized Work Order detail view in dark mode.
            </p>
          </div>

          {/* Component under test */}
          <WorkOrderDetail
            workOrder={mockWorkOrder}
            onStatusChange={(newStatus) => {
              console.log('[Test] Status changed to:', newStatus);
            }}
            onAddEvidence={() => {
              console.log('[Test] Add evidence clicked');
            }}
            onClose={() => {
              console.log('[Test] Close work order clicked');
            }}
          />
        </div>
      </div>
    </div>
  );
}

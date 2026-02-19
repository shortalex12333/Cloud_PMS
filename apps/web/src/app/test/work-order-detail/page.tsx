/**
 * TEST PAGE: WorkOrderDetail Component
 *
 * Route: /test/work-order-detail
 * Purpose: Verify WorkOrderDetail component renders correctly in light and dark mode
 *
 * This page uses mock data to demonstrate the component without requiring
 * authentication or database access.
 */

'use client';

import { useState } from 'react';
import { WorkOrderDetail, type WorkOrderData } from '@/components/cards/WorkOrderDetail';

// Mock data matching the mockup exactly
const mockWorkOrder: WorkOrderData = {
  id: '0142',
  title: 'Hydraulic Pump Inspection',
  status: 'In Progress',
  priority: 'Medium',
  createdAt: 'Feb 10, 2026 at 08:45 AM',
  createdBy: 'John Doe',
  equipment: 'Hydraulic Pump HX-23',
  location: 'Engine Room',
  category: 'Mechanical',
  dueDate: 'Feb 15, 2026',
  assignedTo: 'Alex Johnson',
  linkedFault: 'Oil Leak #1087',
  description: `Inspect and repair hydraulic pump HX-23. Check for abnormal noise and reduced pressure output.

Additional details:
- Verify seal integrity
- Check pressure readings at inlet and outlet
- Document any unusual vibration
- Replace filters if necessary`,
  evidence: [
    {
      id: 'ev-001',
      type: 'email',
      title: '"Pump Noise Issue"',
      timestamp: 'Feb 10, 2026, 09:02 AM',
    },
    {
      id: 'ev-002',
      type: 'photo',
      title: 'leak_hx23.jpg',
      timestamp: 'Feb 10, 2026, 08:50 AM',
    },
    {
      id: 'ev-003',
      type: 'manual',
      title: 'Maintenance Manual, Page 47',
      timestamp: '',
    },
    {
      id: 'ev-004',
      type: 'log',
      title: 'Engine Room Inspection',
      timestamp: 'Feb 09, 2026, 02:15 PM',
    },
  ],
  activity: [
    {
      id: 'act-001',
      timestamp: 'Feb 12, 2026 10:14',
      action: 'Status changed',
      user: 'Alex Johnson',
      oldValue: 'Open',
      newValue: 'In Progress',
    },
    {
      id: 'act-002',
      timestamp: 'Feb 10, 2026 09:00',
      action: 'Work Order created',
      user: 'John Doe',
    },
  ],
};

export default function WorkOrderDetailTestPage() {
  const [isDarkMode, setIsDarkMode] = useState(false);

  return (
    <div className={`min-h-screen ${isDarkMode ? 'dark' : ''}`}>
      <div
        className="min-h-screen py-wo-py"
        style={{ background: 'var(--wo-bg-main)' }}
      >
        <div className="max-w-wo-container mx-auto px-wo-px">
          {/* Page header with mode toggle */}
          <div className="mb-wo-gap flex items-center justify-between">
            <div>
              <h1
                className="font-semibold typo-title mb-2"
                style={{ color: 'var(--wo-text-primary)' }}
              >
                WorkOrderDetail Component Test
              </h1>
              <p
                className="typo-body"
                style={{ color: 'var(--wo-text-meta)' }}
              >
                Testing tokenized Work Order detail view - {isDarkMode ? 'Dark' : 'Light'} Mode
              </p>
            </div>

            {/* Dark/Light mode toggle */}
            <button
              type="button"
              onClick={() => setIsDarkMode(!isDarkMode)}
              className="wo-btn-secondary"
            >
              Switch to {isDarkMode ? 'Light' : 'Dark'} Mode
            </button>
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

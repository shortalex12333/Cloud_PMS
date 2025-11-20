'use client';

import EquipmentOverview from '@/components/DashboardWidgets/EquipmentOverview';
import PredictiveOverview from '@/components/DashboardWidgets/PredictiveOverview';
import WorkOrderStatus from '@/components/DashboardWidgets/WorkOrderStatus';
import InventoryStatus from '@/components/DashboardWidgets/InventoryStatus';
import { Suspense } from 'react';
import { withAuth } from '@/components/withAuth';
import { useAuth } from '@/hooks/useAuth';

function DashboardPage() {
  const { user } = useAuth();
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold">Dashboard</h1>
              <p className="text-sm text-muted-foreground mt-1">
                HOD Overview & Configuration {user && `• ${user.displayName || user.email}`}
              </p>
            </div>
            <div className="flex gap-2">
              <a
                href="/settings"
                className="px-4 py-2 text-sm border border-border rounded-md hover:bg-accent"
              >
                Settings
              </a>
              <a
                href="/search"
                className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                ← Back to Search
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-6 text-sm">
            <button className="py-3 border-b-2 border-primary font-medium">
              Overview
            </button>
            <button className="py-3 text-muted-foreground hover:text-foreground">
              Equipment
            </button>
            <button className="py-3 text-muted-foreground hover:text-foreground">
              Inventory
            </button>
            <button className="py-3 text-muted-foreground hover:text-foreground">
              Work Orders
            </button>
            <button className="py-3 text-muted-foreground hover:text-foreground">
              Predictive
            </button>
            <button className="py-3 text-muted-foreground hover:text-foreground">
              Settings
            </button>
          </nav>
        </div>
      </div>

      {/* Dashboard Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Predictive Overview */}
          <Suspense fallback={<WidgetSkeleton />}>
            <PredictiveOverview />
          </Suspense>

          {/* Work Order Status */}
          <Suspense fallback={<WidgetSkeleton />}>
            <WorkOrderStatus />
          </Suspense>

          {/* Equipment Overview */}
          <Suspense fallback={<WidgetSkeleton />}>
            <EquipmentOverview />
          </Suspense>

          {/* Inventory Status */}
          <Suspense fallback={<WidgetSkeleton />}>
            <InventoryStatus />
          </Suspense>
        </div>
      </main>
    </div>
  );
}

// Loading skeleton for widgets
function WidgetSkeleton() {
  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="skeleton h-6 w-32 mb-4" />
      <div className="space-y-3">
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-5/6" />
        <div className="skeleton h-4 w-4/6" />
      </div>
    </div>
  );
}

// Export with HOD-only protection
export default withAuth(DashboardPage, { requireHOD: true });

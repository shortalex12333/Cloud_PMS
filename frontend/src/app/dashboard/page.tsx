'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { DashboardLayout } from '@/components/DashboardLayout'
import { RiskOverviewWidget } from '@/components/widgets/RiskOverviewWidget'
import { WorkOrdersWidget } from '@/components/widgets/WorkOrdersWidget'
import { InventoryWidget } from '@/components/widgets/InventoryWidget'
import { FaultsWidget } from '@/components/widgets/FaultsWidget'
import { UpcomingTasksWidget } from '@/components/widgets/UpcomingTasksWidget'
import { FleetWidget } from '@/components/widgets/FleetWidget'
import {
  RiskOverviewData,
  WorkOrdersData,
  InventoryData,
  FaultsData,
  UpcomingTasksData,
  FleetData,
} from '@/types/dashboard'
import {
  mockRiskOverviewData,
  mockWorkOrdersData,
  mockInventoryData,
  mockFaultsData,
  mockUpcomingTasksData,
  mockFleetData,
} from '@/lib/mockData'

export default function DashboardPage() {
  const { user, isHOD, loading: authLoading } = useAuth()
  const router = useRouter()
  const [loading, setLoading] = useState(true)

  // Dashboard data state
  const [riskData, setRiskData] = useState<RiskOverviewData | null>(null)
  const [workOrdersData, setWorkOrdersData] = useState<WorkOrdersData | null>(null)
  const [inventoryData, setInventoryData] = useState<InventoryData | null>(null)
  const [faultsData, setFaultsData] = useState<FaultsData | null>(null)
  const [tasksData, setTasksData] = useState<UpcomingTasksData | null>(null)
  const [fleetData, setFleetData] = useState<FleetData | null>(null)

  // Role-based access control
  useEffect(() => {
    if (!authLoading && !isHOD()) {
      router.push('/search')
    }
  }, [user, authLoading, router, isHOD])

  // Fetch dashboard data
  useEffect(() => {
    if (!authLoading && isHOD()) {
      fetchDashboardData()
    }
  }, [authLoading, isHOD])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)

      // TODO: Replace with real API calls when backend is ready
      // For now, using mock data with simulated delay
      await new Promise(resolve => setTimeout(resolve, 500))

      setRiskData(mockRiskOverviewData)
      setWorkOrdersData(mockWorkOrdersData)
      setInventoryData(mockInventoryData)
      setFaultsData(mockFaultsData)
      setTasksData(mockUpcomingTasksData)
      setFleetData(mockFleetData)

      /* Real API calls would look like:
      const [risk, workOrders, inventory, faults, tasks] = await Promise.all([
        api.predictive.getInsights(),
        api.dashboard.getWorkOrders(),
        api.dashboard.getInventory(),
        api.dashboard.getFaults(),
        api.dashboard.getUpcomingTasks(),
      ])
      setRiskData(risk.insights)
      setWorkOrdersData(workOrders)
      setInventoryData(inventory)
      setFaultsData(faults)
      setTasksData({ tasks, total_count: tasks.length })
      */
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleNavigateToSearch = (query: string) => {
    router.push(`/search?q=${encodeURIComponent(query)}`)
  }

  if (authLoading || !isHOD()) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    )
  }

  return (
    <DashboardLayout>
      {/* Page Header */}
      <div className="mb-8">
        <h2 className="text-3xl font-bold">Dashboard</h2>
        <p className="text-muted-foreground mt-1">
          System overview, configuration, and monitoring
        </p>
      </div>

      {/* Dashboard Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Risk Overview - Top Left */}
        <RiskOverviewWidget
          data={riskData}
          loading={loading}
          onNavigateToSearch={handleNavigateToSearch}
          className="md:col-span-1"
        />

        {/* Work Orders - Top Middle */}
        <WorkOrdersWidget
          data={workOrdersData}
          loading={loading}
          onNavigateToSearch={handleNavigateToSearch}
          className="md:col-span-1"
        />

        {/* Inventory - Top Right */}
        <InventoryWidget
          data={inventoryData}
          loading={loading}
          onNavigateToSearch={handleNavigateToSearch}
          className="md:col-span-1"
        />

        {/* Faults - Middle Left */}
        <FaultsWidget
          data={faultsData}
          loading={loading}
          onNavigateToSearch={handleNavigateToSearch}
          className="md:col-span-1"
        />

        {/* Upcoming Tasks - Middle/Bottom */}
        <UpcomingTasksWidget
          data={tasksData}
          loading={loading}
          onNavigateToSearch={handleNavigateToSearch}
          className="md:col-span-2 lg:col-span-1"
        />

        {/* Fleet Widget - Optional, only show if data exists */}
        {fleetData && (
          <FleetWidget
            data={fleetData}
            loading={loading}
            className="md:col-span-2 lg:col-span-1"
          />
        )}
      </div>
    </DashboardLayout>
  )
}

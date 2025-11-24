'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  Package,
  Search,
  Settings,
  TrendingUp,
  Wrench,
  ChevronRight,
  RefreshCw,
  Zap,
  ClipboardList,
  ArrowLeft,
} from 'lucide-react';
import { withAuth } from '@/components/withAuth';
import { useAuth, isHOD } from '@/contexts/AuthContext';

// ============================================================================
// TYPES
// ============================================================================

interface DailySummary {
  summary: string;
  bullet_points: string[];
  generated_at: string;
}

interface PredictiveRisk {
  equipment_id: string;
  equipment_name: string;
  risk_score: number;
  summary: string;
  contributing_factors: string[];
}

interface PendingApproval {
  id: string;
  type: 'work_order' | 'purchase_request';
  title: string;
  urgency: 'low' | 'medium' | 'high' | 'critical';
  created_by: string;
  created_at: string;
}

interface OverdueWorkOrder {
  id: string;
  title: string;
  equipment_name: string;
  days_overdue: number;
}

interface LowStockItem {
  id: string;
  name: string;
  quantity: number;
  min_quantity: number;
}

interface EquipmentAlert {
  id: string;
  name: string;
  status: string;
}

interface TimelineEvent {
  id: string;
  timestamp: string;
  type: 'fault' | 'wo_completed' | 'risk_spike' | 'note' | 'inventory';
  description: string;
}

// ============================================================================
// MOCK DATA (fallback when APIs unavailable)
// ============================================================================

const MOCK_SUMMARY: DailySummary = {
  summary: 'Operations running smoothly with 2 items requiring attention.',
  bullet_points: [
    'Port Generator coolant temperature elevated - monitoring recommended',
    'Stabiliser pump showing early wear patterns - schedule inspection',
    '3 work orders completed successfully yesterday',
    'All hours of rest compliance met',
  ],
  generated_at: new Date().toISOString(),
};

const MOCK_RISKS: PredictiveRisk[] = [
  {
    equipment_id: '1',
    equipment_name: 'HVAC Chiller #3',
    risk_score: 0.78,
    summary: 'Repeated high-pressure faults detected',
    contributing_factors: ['Pressure spikes', 'Frequent restarts'],
  },
  {
    equipment_id: '2',
    equipment_name: 'Stabiliser Pump Port',
    risk_score: 0.65,
    summary: 'Leak pattern emerging',
    contributing_factors: ['Seal degradation', 'Increased maintenance'],
  },
  {
    equipment_id: '3',
    equipment_name: 'Port Generator',
    risk_score: 0.58,
    summary: 'Coolant temperature trending high',
    contributing_factors: ['Thermostat aging', 'Cooling system load'],
  },
];

const MOCK_APPROVALS: PendingApproval[] = [
  {
    id: 'wo-123',
    type: 'work_order',
    title: 'Replace HVAC compressor bearings',
    urgency: 'high',
    created_by: 'Chief Engineer',
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'pr-456',
    type: 'purchase_request',
    title: 'MTU Coolant Sensor (x2)',
    urgency: 'medium',
    created_by: '2nd Engineer',
    created_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
  },
];

const MOCK_OVERDUE_WOS: OverdueWorkOrder[] = [
  { id: '1', title: 'Replace HVAC filters', equipment_name: 'HVAC System', days_overdue: 5 },
  { id: '2', title: 'Generator coolant flush', equipment_name: 'Port Generator', days_overdue: 3 },
];

const MOCK_LOW_STOCK: LowStockItem[] = [
  { id: '1', name: 'Racor 2040 Filter', quantity: 1, min_quantity: 4 },
  { id: '2', name: 'MTU Coolant Temp Sensor', quantity: 0, min_quantity: 2 },
];

const MOCK_EQUIPMENT_ALERTS: EquipmentAlert[] = [
  { id: '1', name: 'Stabiliser System', status: 'needs_attention' },
  { id: '2', name: 'Port Generator', status: 'monitoring' },
];

const MOCK_TIMELINE: TimelineEvent[] = [
  { id: '1', timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(), type: 'wo_completed', description: 'Work Order #234 completed - Bilge pump inspection' },
  { id: '2', timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(), type: 'risk_spike', description: 'Risk spike detected for HVAC Chiller #3' },
  { id: '3', timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(), type: 'note', description: 'New note logged on Port Generator' },
  { id: '4', timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(), type: 'fault', description: 'New fault recorded - Stabiliser pressure variance' },
  { id: '5', timestamp: new Date(Date.now() - 18 * 60 * 60 * 1000).toISOString(), type: 'inventory', description: 'Parts received - 4x O-Ring kits' },
];

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function formatTime(dateString: string): string {
  return new Date(dateString).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getUrgencyColor(urgency: string): string {
  switch (urgency) {
    case 'critical': return 'text-destructive bg-destructive/10 border-destructive/20';
    case 'high': return 'text-orange-600 bg-orange-500/10 border-orange-500/20';
    case 'medium': return 'text-yellow-600 bg-yellow-500/10 border-yellow-500/20';
    default: return 'text-muted-foreground bg-muted border-border';
  }
}

function getTimelineIcon(type: string) {
  switch (type) {
    case 'fault': return <AlertTriangle className="h-3 w-3 text-destructive" />;
    case 'wo_completed': return <CheckCircle className="h-3 w-3 text-green-600" />;
    case 'risk_spike': return <TrendingUp className="h-3 w-3 text-orange-600" />;
    case 'note': return <FileText className="h-3 w-3 text-blue-600" />;
    case 'inventory': return <Package className="h-3 w-3 text-purple-600" />;
    default: return <Clock className="h-3 w-3 text-muted-foreground" />;
  }
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

function BriefingContent() {
  const router = useRouter();
  const { user } = useAuth();

  // State for all sections
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [risks, setRisks] = useState<PredictiveRisk[]>([]);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [overdueWOs, setOverdueWOs] = useState<OverdueWorkOrder[]>([]);
  const [lowStock, setLowStock] = useState<LowStockItem[]>([]);
  const [equipmentAlerts, setEquipmentAlerts] = useState<EquipmentAlert[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.celeste7.ai/webhook').replace(/\/+$/, '');

  // Fetch all data
  const fetchAllData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      // Fetch all endpoints in parallel
      const [
        summaryRes,
        risksRes,
        approvalsRes,
        workOrdersRes,
        inventoryRes,
        equipmentRes,
        activityRes,
      ] = await Promise.allSettled([
        // Section 1: Daily Summary
        fetch(`${baseUrl}/workflows/view`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action_name: 'view_smart_summary',
            context: { user_id: user?.id, yacht_id: user?.yachtId },
            parameters: {},
          }),
        }),
        // Section 2: Priority Risks
        fetch(`${baseUrl}/v1/predictive/top-risks`),
        // Section 3: Pending Approvals
        fetch(`${baseUrl}/workflows/view`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action_name: 'view_pending_approvals',
            parameters: {},
          }),
        }),
        // Section 4: Work Orders Status
        fetch(`${baseUrl}/v1/work-orders/status`),
        // Section 4: Inventory
        fetch(`${baseUrl}/v1/inventory/low-stock`),
        // Section 4: Equipment
        fetch(`${baseUrl}/v1/equipment/overview`),
        // Section 5: Recent Activity
        fetch(`${baseUrl}/workflows/view`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action_name: 'view_recent_activity',
            parameters: { time_range: '24h' },
          }),
        }),
      ]);

      // Process results with fallbacks
      if (summaryRes.status === 'fulfilled' && summaryRes.value.ok) {
        const data = await summaryRes.value.json();
        setSummary(data);
      } else {
        setSummary(MOCK_SUMMARY);
      }

      if (risksRes.status === 'fulfilled' && risksRes.value.ok) {
        const data = await risksRes.value.json();
        setRisks((data.risks || data).slice(0, 3));
      } else {
        setRisks(MOCK_RISKS);
      }

      if (approvalsRes.status === 'fulfilled' && approvalsRes.value.ok) {
        const data = await approvalsRes.value.json();
        setApprovals(data.approvals || data || []);
      } else {
        setApprovals(MOCK_APPROVALS);
      }

      if (workOrdersRes.status === 'fulfilled' && workOrdersRes.value.ok) {
        const data = await workOrdersRes.value.json();
        setOverdueWOs((data.overdue_items || []).slice(0, 3));
      } else {
        setOverdueWOs(MOCK_OVERDUE_WOS);
      }

      if (inventoryRes.status === 'fulfilled' && inventoryRes.value.ok) {
        const data = await inventoryRes.value.json();
        setLowStock((data.low_stock_items || []).slice(0, 3));
      } else {
        setLowStock(MOCK_LOW_STOCK);
      }

      if (equipmentRes.status === 'fulfilled' && equipmentRes.value.ok) {
        const data = await equipmentRes.value.json();
        setEquipmentAlerts((data.alerts || []).slice(0, 3));
      } else {
        setEquipmentAlerts(MOCK_EQUIPMENT_ALERTS);
      }

      if (activityRes.status === 'fulfilled' && activityRes.value.ok) {
        const data = await activityRes.value.json();
        setTimeline((data.events || data || []).slice(0, 5));
      } else {
        setTimeline(MOCK_TIMELINE);
      }
    } catch (err) {
      console.error('[Briefing] Error fetching data:', err);
      // Use all mock data on error
      setSummary(MOCK_SUMMARY);
      setRisks(MOCK_RISKS);
      setApprovals(MOCK_APPROVALS);
      setOverdueWOs(MOCK_OVERDUE_WOS);
      setLowStock(MOCK_LOW_STOCK);
      setEquipmentAlerts(MOCK_EQUIPMENT_ALERTS);
      setTimeline(MOCK_TIMELINE);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [baseUrl, user?.id, user?.yachtId]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Navigation helper
  const handleSearch = (query: string) => {
    router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  // Check if user has HOD access
  const hasAccess = isHOD(user);

  if (!hasAccess) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <AlertTriangle className="h-12 w-12 text-yellow-600 mx-auto mb-4" />
          <h1 className="text-xl font-semibold mb-2">Briefing Access Restricted</h1>
          <p className="text-muted-foreground mb-4">
            Daily Briefings are available for Heads of Department, Captains, and Management.
          </p>
          <Link
            href="/search"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <Search className="h-4 w-4" />
            Go to Search
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="max-w-2xl mx-auto px-4 py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 w-48 bg-muted rounded" />
            <div className="h-32 bg-muted rounded-lg" />
            <div className="h-48 bg-muted rounded-lg" />
            <div className="h-32 bg-muted rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-24">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur-sm">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link
                href="/search"
                className="p-2 -ml-2 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors"
              >
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <div>
                <h1 className="text-lg font-semibold">Daily Briefing</h1>
                <p className="text-xs text-muted-foreground">
                  {new Date().toLocaleDateString('en-GB', {
                    weekday: 'long',
                    day: 'numeric',
                    month: 'long',
                  })}
                </p>
              </div>
            </div>
            <button
              onClick={() => fetchAllData(true)}
              disabled={refreshing}
              className="p-2 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-5 w-5 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* ================================================================ */}
        {/* SECTION 1: Daily Summary */}
        {/* ================================================================ */}
        <section>
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-start gap-3 mb-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Zap className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <h2 className="font-semibold">Operational Summary</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  {summary?.summary}
                </p>
              </div>
            </div>
            {summary?.bullet_points && summary.bullet_points.length > 0 && (
              <ul className="space-y-2 mt-4 pl-2">
                {summary.bullet_points.map((point, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="text-primary mt-1">-</span>
                    <span className="text-muted-foreground">{point}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        {/* ================================================================ */}
        {/* SECTION 2: Priority Risks */}
        {/* ================================================================ */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Priority Risks
          </h2>
          <div className="space-y-3">
            {risks.length === 0 ? (
              <div className="bg-card border border-border rounded-lg p-4 text-center">
                <CheckCircle className="h-8 w-8 text-green-600 mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">No high-risk items detected</p>
              </div>
            ) : (
              risks.map((risk) => (
                <div
                  key={risk.equipment_id}
                  className="bg-card border border-border rounded-lg p-4"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <AlertTriangle
                        className={`h-4 w-4 ${
                          risk.risk_score >= 0.7 ? 'text-destructive' : 'text-yellow-600'
                        }`}
                      />
                      <span className="font-medium text-sm">{risk.equipment_name}</span>
                    </div>
                    <span
                      className={`text-xs font-semibold px-2 py-0.5 rounded ${
                        risk.risk_score >= 0.7
                          ? 'bg-destructive/10 text-destructive'
                          : 'bg-yellow-500/10 text-yellow-600'
                      }`}
                    >
                      {Math.round(risk.risk_score * 100)}% risk
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">{risk.summary}</p>
                  <div className="flex flex-wrap gap-1 mb-3">
                    {risk.contributing_factors.map((factor, i) => (
                      <span
                        key={i}
                        className="text-xs px-2 py-0.5 bg-muted rounded-full text-muted-foreground"
                      >
                        {factor}
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSearch(risk.equipment_name)}
                      className="flex-1 text-xs px-3 py-1.5 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 transition-colors"
                    >
                      View Equipment
                    </button>
                    <button
                      onClick={() => handleSearch(`add ${risk.equipment_name} to handover`)}
                      className="flex-1 text-xs px-3 py-1.5 border border-border rounded hover:bg-muted transition-colors"
                    >
                      Add to Handover
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* ================================================================ */}
        {/* SECTION 3: Action Queue */}
        {/* ================================================================ */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <ClipboardList className="h-4 w-4" />
            Needs Your Action
          </h2>
          {approvals.length === 0 ? (
            <div className="bg-card border border-border rounded-lg p-4 text-center">
              <CheckCircle className="h-8 w-8 text-green-600 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No pending approvals</p>
            </div>
          ) : (
            <div className="space-y-3">
              {approvals.map((item) => (
                <div
                  key={item.id}
                  className="bg-card border border-border rounded-lg p-4"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {item.type === 'work_order' ? (
                        <Wrench className="h-4 w-4 text-primary" />
                      ) : (
                        <Package className="h-4 w-4 text-purple-600" />
                      )}
                      <span className="font-medium text-sm">{item.title}</span>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded border ${getUrgencyColor(item.urgency)}`}>
                      {item.urgency}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    {item.created_by} - {formatTimeAgo(item.created_at)}
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSearch(`approve ${item.type === 'work_order' ? 'work order' : 'purchase request'} ${item.id}`)}
                      className="flex-1 text-xs px-3 py-1.5 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleSearch(`${item.type === 'work_order' ? 'work order' : 'purchase request'} ${item.id}`)}
                      className="flex-1 text-xs px-3 py-1.5 border border-border rounded hover:bg-muted transition-colors"
                    >
                      View Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ================================================================ */}
        {/* SECTION 4: Operational Alerts */}
        {/* ================================================================ */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            Operational Alerts
          </h2>
          <div className="bg-card border border-border rounded-lg divide-y divide-border">
            {/* Overdue Work Orders */}
            {overdueWOs.length > 0 && (
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-destructive flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Overdue Work Orders
                  </span>
                  <button
                    onClick={() => handleSearch('overdue work orders')}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    View all
                  </button>
                </div>
                <div className="space-y-2">
                  {overdueWOs.map((wo) => (
                    <div
                      key={wo.id}
                      onClick={() => handleSearch(wo.equipment_name)}
                      className="flex items-center justify-between text-sm cursor-pointer hover:bg-muted -mx-2 px-2 py-1 rounded transition-colors"
                    >
                      <span className="truncate">{wo.title}</span>
                      <span className="text-xs text-destructive font-medium whitespace-nowrap ml-2">
                        {wo.days_overdue}d overdue
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Low Stock */}
            {lowStock.length > 0 && (
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-yellow-600 flex items-center gap-1">
                    <Package className="h-3 w-3" />
                    Low Stock Items
                  </span>
                  <button
                    onClick={() => handleSearch('low stock inventory')}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    View all
                  </button>
                </div>
                <div className="space-y-2">
                  {lowStock.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => handleSearch(item.name)}
                      className="flex items-center justify-between text-sm cursor-pointer hover:bg-muted -mx-2 px-2 py-1 rounded transition-colors"
                    >
                      <span className="truncate">{item.name}</span>
                      <span className={`text-xs font-medium whitespace-nowrap ml-2 ${
                        item.quantity === 0 ? 'text-destructive' : 'text-yellow-600'
                      }`}>
                        {item.quantity}/{item.min_quantity}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Equipment Alerts */}
            {equipmentAlerts.length > 0 && (
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-orange-600 flex items-center gap-1">
                    <Settings className="h-3 w-3" />
                    Equipment Attention
                  </span>
                  <button
                    onClick={() => handleSearch('equipment needs attention')}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    View all
                  </button>
                </div>
                <div className="space-y-2">
                  {equipmentAlerts.map((eq) => (
                    <div
                      key={eq.id}
                      onClick={() => handleSearch(eq.name)}
                      className="flex items-center justify-between text-sm cursor-pointer hover:bg-muted -mx-2 px-2 py-1 rounded transition-colors"
                    >
                      <span className="truncate">{eq.name}</span>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty state */}
            {overdueWOs.length === 0 && lowStock.length === 0 && equipmentAlerts.length === 0 && (
              <div className="p-4 text-center">
                <CheckCircle className="h-8 w-8 text-green-600 mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">All systems operational</p>
              </div>
            )}
          </div>
        </section>

        {/* ================================================================ */}
        {/* SECTION 5: What Changed Timeline */}
        {/* ================================================================ */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <Clock className="h-4 w-4" />
            What Changed (Last 24h)
          </h2>
          <div className="bg-card border border-border rounded-lg p-4">
            {timeline.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-2">
                No recent activity
              </p>
            ) : (
              <div className="space-y-3">
                {timeline.map((event, i) => (
                  <div key={event.id} className="flex items-start gap-3">
                    <div className="flex flex-col items-center">
                      <div className="p-1.5 bg-muted rounded-full">
                        {getTimelineIcon(event.type)}
                      </div>
                      {i < timeline.length - 1 && (
                        <div className="w-px h-full bg-border mt-1 flex-1 min-h-[20px]" />
                      )}
                    </div>
                    <div className="flex-1 pb-3">
                      <p className="text-sm">{event.description}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {formatTime(event.timestamp)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 border-t border-border bg-background/95 backdrop-blur-sm">
        <div className="max-w-2xl mx-auto px-4 py-3 flex justify-center gap-8">
          <Link
            href="/briefing"
            className="flex items-center gap-2 px-4 py-2 text-sm text-foreground bg-muted rounded-md"
          >
            <Zap className="h-4 w-4" />
            <span>Briefing</span>
          </Link>
          <Link
            href="/settings"
            className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
          >
            <Settings className="h-4 w-4" />
            <span>Settings</span>
          </Link>
        </div>
      </nav>
    </div>
  );
}

// Export with authentication protection (HOD+ only)
export default withAuth(BriefingContent, { requireHOD: true });

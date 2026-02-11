'use client';

/**
 * =============================================================================
 * EQUIPMENT LENS - Full Page View
 * =============================================================================
 *
 * CREATED: 2026-02-05
 * PURPOSE: Full-page lens for equipment entities accessed via handover export links
 *
 * HANDOVER EXPORT FLOW:
 * ---------------------
 * 1. User clicks link in handover PDF/HTML: https://app.celeste7.ai/open?t=<JWS_TOKEN>
 * 2. /open page resolves token via POST /api/v1/open/resolve (handover-export service)
 * 3. Token returns: { focus: { type: "equipment", id: "uuid" }, yacht_id, scope }
 * 4. /open page redirects to this lens: /equipment/{id}
 * 5. This page fetches full equipment data and renders it
 *
 * DATA FETCHING:
 * --------------
 * - Uses microaction handler: viewEquipmentDetails() from @/lib/microactions/handlers/equipment
 * - Requires ActionContext with yacht_id (from useAuth bootstrap)
 * - Queries Supabase table: pms_equipment
 *
 * =============================================================================
 * WHAT THIS SKELETON PROVIDES:
 * =============================================================================
 * - Route structure: /equipment/[id]
 * - Auth check pattern (wait for authLoading + bootstrapping)
 * - Data fetching via microaction handler
 * - Loading/error/success states
 * - Basic layout with status and risk badges
 * - Equipment details grid (manufacturer, model, serial, running hours, etc.)
 * - RelatedEmailsPanel integration
 *
 * =============================================================================
 * WHAT'S MISSING (for engineers to implement):
 * =============================================================================
 * - [ ] Edit equipment action + modal
 * - [ ] View maintenance history (past work orders on this equipment)
 * - [ ] View active faults on this equipment
 * - [ ] Create fault from equipment action
 * - [ ] Create work order from equipment action
 * - [ ] Update running hours action
 * - [ ] View manual/documentation action
 * - [ ] Predictive maintenance display (if AI predictions available)
 * - [ ] Photo gallery for equipment
 * - [ ] Service schedule display
 * - [ ] Spare parts linked to this equipment
 * - [ ] QR code / asset tag display
 * - [ ] Equipment hierarchy (parent/child relationships)
 * - [ ] Telemetry data display (if IoT connected)
 *
 * =============================================================================
 * RELATED FILES:
 * =============================================================================
 * - /src/lib/microactions/handlers/equipment.ts - Data fetching logic
 * - /src/components/cards/EquipmentCard.tsx - Card component (has all action modals)
 * - /src/app/open/page.tsx - Token resolution (redirects here)
 * - /src/app/app/DeepLinkHandler.tsx - Query param handling (redirects here)
 *
 * =============================================================================
 */

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { viewEquipmentDetails } from '@/lib/microactions/handlers/equipment';
import type { ActionContext } from '@/lib/microactions/types';
import {
  Loader2,
  ArrowLeft,
  AlertTriangle,
  Settings,
  MapPin,
  Hash,
  Factory,
  Clock,
  Gauge,
  Activity
} from 'lucide-react';
import { RelatedEmailsPanel } from '@/components/email/RelatedEmailsPanel';
import { cn } from '@/lib/utils';

/**
 * Equipment data shape returned from viewEquipmentDetails handler
 * Maps to pms_equipment table + computed fields
 */
interface EquipmentData {
  id: string;
  name: string;
  equipment_type?: string;    // Type classification (Engine, Generator, etc.)
  category?: string;          // Category grouping
  manufacturer?: string;      // Equipment manufacturer
  model?: string;             // Model number/name
  serial_number?: string;     // Unique serial identifier
  location?: string;          // Physical location on yacht
  status: string;             // operational, faulty, maintenance, offline
  running_hours?: number;     // Current running hours meter
  risk_score?: number;        // Computed 0-100 risk score from predictive maintenance
  installation_date?: string; // When equipment was installed
  last_maintenance?: string;  // Date of last maintenance
  next_maintenance?: string;  // Scheduled next maintenance date
  created_at?: string;        // Record creation time
}

export default function EquipmentLensPage() {
  // ---------------------------------------------------------------------------
  // ROUTING & AUTH
  // ---------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // ---------------------------------------------------------------------------
  // STATE
  // ---------------------------------------------------------------------------
  const [equipment, setEquipment] = useState<EquipmentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Extract equipment ID from URL: /equipment/[id]
  const equipmentId = params.id as string;

  // ---------------------------------------------------------------------------
  // DATA FETCHING
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // Wait for auth AND bootstrap to complete
    if (authLoading || bootstrapping) return;

    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    const fetchEquipment = async () => {
      try {
        // Build ActionContext for microaction handler
        const context: ActionContext = {
          yacht_id: user.yachtId!,
          user_id: user.id,
          user_role: user.role || 'member',
          entity_id: equipmentId,
          entity_type: 'equipment',
        };

        // Call microaction handler
        // See: /src/lib/microactions/handlers/equipment.ts
        const result = await viewEquipmentDetails(context, { equipment_id: equipmentId });

        if (!result.success || !result.data) {
          setError(result.error?.message || 'Equipment not found');
          setLoading(false);
          return;
        }

        const data = result.data as { equipment: EquipmentData };
        setEquipment(data.equipment);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load equipment');
        setLoading(false);
      }
    };

    fetchEquipment();
  }, [equipmentId, user, authLoading, bootstrapping]);

  // ---------------------------------------------------------------------------
  // STYLING HELPERS
  // ---------------------------------------------------------------------------

  /** Map status to visual style */
  const getStatusStyle = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'operational':
        return { bg: 'bg-green-500/10', text: 'text-green-400', label: 'Operational' };
      case 'faulty':
        return { bg: 'bg-red-500/10', text: 'text-red-400', label: 'Faulty' };
      case 'maintenance':
        return { bg: 'bg-amber-500/10', text: 'text-amber-400', label: 'Under Maintenance' };
      case 'offline':
        return { bg: 'bg-celeste-text-disabled/10', text: 'text-celeste-text-muted', label: 'Offline' };
      default:
        return { bg: 'bg-celeste-accent-subtle', text: 'text-celeste-accent', label: status || 'Unknown' };
    }
  };

  /** Map risk score (0-100) to visual style */
  const getRiskStyle = (score: number) => {
    if (score >= 75) return { bg: 'bg-red-500/10', text: 'text-red-400', label: 'High Risk' };
    if (score >= 50) return { bg: 'bg-amber-500/10', text: 'text-amber-400', label: 'Medium Risk' };
    if (score >= 25) return { bg: 'bg-yellow-500/10', text: 'text-yellow-400', label: 'Low Risk' };
    return { bg: 'bg-green-500/10', text: 'text-green-400', label: 'Minimal Risk' };
  };

  /** Format date for display */
  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  // ---------------------------------------------------------------------------
  // LOADING STATE
  // ---------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-celeste-black flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-celeste-accent animate-spin mx-auto mb-4" />
          <p className="text-celeste-text-muted">Loading equipment details...</p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // ERROR STATE
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div className="min-h-screen bg-celeste-black flex items-center justify-center p-4">
        <div className="bg-celeste-bg-tertiary rounded-lg p-8 max-w-md w-full text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Error</h2>
          <p className="text-celeste-text-muted mb-6">{error}</p>
          <button
            onClick={() => router.push('/app')}
            className="px-4 py-2 bg-celeste-accent hover:bg-celeste-accent-hover text-white rounded-lg transition-colors"
          >
            Return to App
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // NULL CHECK
  // ---------------------------------------------------------------------------
  if (!equipment) {
    return null;
  }

  const status = getStatusStyle(equipment.status);
  const risk = equipment.risk_score !== undefined ? getRiskStyle(equipment.risk_score) : null;

  // ---------------------------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-celeste-black">
      {/* ===================================================================
          HEADER
          TODO: Add action buttons (Edit, Create Fault, Create WO, etc.)
          =================================================================== */}
      <header className="bg-celeste-bg-tertiary/50 border-b border-celeste-text-secondary/50 sticky top-0 z-10 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-celeste-text-secondary/50 rounded-lg transition-colors"
              aria-label="Go back"
            >
              <ArrowLeft className="w-5 h-5 text-celeste-text-muted" />
            </button>
            <div className="flex items-center gap-2">
              <Settings className="w-5 h-5 text-celeste-accent" />
              <span className="text-sm text-celeste-text-muted uppercase tracking-wider">Equipment</span>
            </div>
            {/* TODO: Add action buttons
            <div className="ml-auto flex gap-2">
              <button onClick={() => setShowEdit(true)}>Edit</button>
              <button onClick={() => setShowCreateFault(true)}>Report Fault</button>
              <button onClick={() => setShowCreateWO(true)}>Create Work Order</button>
            </div>
            */}
          </div>
        </div>
      </header>

      {/* ===================================================================
          MAIN CONTENT
          =================================================================== */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* -----------------------------------------------------------------
            TITLE SECTION
            ----------------------------------------------------------------- */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-4">
            {equipment.name}
          </h1>

          {/* Status & Risk Badges */}
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <span className={cn('px-3 py-1 rounded-full text-sm font-medium', status.bg, status.text)}>
              {status.label}
            </span>
            {risk && (
              <span className={cn('px-3 py-1 rounded-full text-sm font-medium', risk.bg, risk.text)}>
                {risk.label}
              </span>
            )}
          </div>

          {/* Type / Category - TODO: Make clickable to filter by type */}
          {(equipment.equipment_type || equipment.category) && (
            <div className="flex items-center gap-2 text-celeste-text-muted mb-2">
              <Settings className="w-4 h-4" />
              <span>{equipment.equipment_type || equipment.category}</span>
            </div>
          )}

          {/* Location */}
          {equipment.location && (
            <div className="flex items-center gap-2 text-celeste-text-muted">
              <MapPin className="w-4 h-4" />
              <span>{equipment.location}</span>
            </div>
          )}
        </div>

        {/* -----------------------------------------------------------------
            TODO: ACTIVE FAULTS SECTION
            Show any open faults associated with this equipment
            Query: pms_faults WHERE equipment_id = {id} AND resolved_at IS NULL
            ----------------------------------------------------------------- */}

        {/* -----------------------------------------------------------------
            TODO: MAINTENANCE SCHEDULE SECTION
            Show upcoming scheduled maintenance
            ----------------------------------------------------------------- */}

        {/* -----------------------------------------------------------------
            DETAILS GRID
            ----------------------------------------------------------------- */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Manufacturer */}
          {equipment.manufacturer && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <Factory className="w-5 h-5 text-celeste-text-disabled" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Manufacturer</p>
                  <p className="text-celeste-border">{equipment.manufacturer}</p>
                </div>
              </div>
            </div>
          )}

          {/* Model */}
          {equipment.model && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <Hash className="w-5 h-5 text-celeste-text-disabled" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Model</p>
                  <p className="text-celeste-border">{equipment.model}</p>
                </div>
              </div>
            </div>
          )}

          {/* Serial Number */}
          {equipment.serial_number && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <Hash className="w-5 h-5 text-celeste-text-disabled" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Serial Number</p>
                  <p className="text-celeste-border font-mono">{equipment.serial_number}</p>
                </div>
              </div>
            </div>
          )}

          {/* Running Hours */}
          {equipment.running_hours !== undefined && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-celeste-text-disabled" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Running Hours</p>
                  <p className="text-celeste-border">{equipment.running_hours.toLocaleString()} hrs</p>
                </div>
              </div>
            </div>
          )}

          {/* Risk Score */}
          {equipment.risk_score !== undefined && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <Activity className={cn('w-5 h-5', risk?.text || 'text-celeste-text-disabled')} />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Risk Score</p>
                  <p className={cn(risk?.text || 'text-celeste-border')}>{equipment.risk_score}%</p>
                </div>
              </div>
            </div>
          )}

          {/* Installation Date */}
          {equipment.installation_date && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <Gauge className="w-5 h-5 text-celeste-text-disabled" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Installed</p>
                  <p className="text-celeste-border">{formatDate(equipment.installation_date)}</p>
                </div>
              </div>
            </div>
          )}

          {/* Last Maintenance */}
          {equipment.last_maintenance && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-celeste-text-disabled" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Last Maintenance</p>
                  <p className="text-celeste-border">{formatDate(equipment.last_maintenance)}</p>
                </div>
              </div>
            </div>
          )}

          {/* Next Maintenance */}
          {equipment.next_maintenance && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Next Maintenance</p>
                  <p className="text-amber-400">{formatDate(equipment.next_maintenance)}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* -----------------------------------------------------------------
            TODO: MAINTENANCE HISTORY SECTION
            Show past work orders for this equipment
            Query: pms_work_orders WHERE equipment_id = {id}
            ----------------------------------------------------------------- */}

        {/* -----------------------------------------------------------------
            TODO: SPARE PARTS SECTION
            Show parts linked to this equipment
            ----------------------------------------------------------------- */}

        {/* -----------------------------------------------------------------
            TODO: DOCUMENTATION SECTION
            Link to manuals and documentation for this equipment
            ----------------------------------------------------------------- */}

        {/* -----------------------------------------------------------------
            RELATED EMAILS
            ----------------------------------------------------------------- */}
        <div className="bg-celeste-bg-tertiary/50 rounded-lg p-6 border border-celeste-text-secondary/50">
          <h2 className="text-sm font-semibold text-celeste-text-muted uppercase tracking-wider mb-4">
            Related Emails
          </h2>
          <RelatedEmailsPanel
            objectType="equipment"
            objectId={equipment.id}
          />
        </div>
      </main>
    </div>
  );
}

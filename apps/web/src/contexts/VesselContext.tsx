'use client';

/**
 * VesselContext — Multi-vessel state management
 *
 * Provides the active vessel ID for all data queries.
 * Single-vessel users: static, no dropdown, same as before.
 * Fleet managers: switchable via topbar dropdown.
 *
 * Default: primary vessel (user.yachtId), not "All Vessels".
 * "All Vessels" is an explicit user choice via dropdown.
 */

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';
import type { FleetVessel } from './AuthContext';

interface VesselState {
  /** Currently active vessel ID. null = "All Vessels" mode. */
  vesselId: string | null;
  /** Display name for the active vessel */
  vesselName: string;
  /** All vessels this user has access to */
  vessels: FleetVessel[];
  /** Whether user can switch vessels */
  isFleetUser: boolean;
  /** Whether "All Vessels" mode is active */
  isAllVessels: boolean;
  /** Switch active vessel. null = All Vessels. */
  setActiveVessel: (id: string | null) => void;
}

const VesselContext = React.createContext<VesselState | null>(null);

export function VesselProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  // Parse fleet_vessels from bootstrap data
  const fleetVessels: FleetVessel[] = React.useMemo(() => {
    if (Array.isArray(user?.fleet_vessels) && user.fleet_vessels.length > 0) return user.fleet_vessels;
    // Single vessel fallback
    if (user?.yachtId) {
      return [{ yacht_id: user.yachtId, yacht_name: user.yachtName || 'Vessel' }];
    }
    return [];
  }, [user]);

  const isFleetUser = fleetVessels.length > 1;

  // Default to primary vessel (user.yachtId), not "All Vessels"
  const [activeVesselId, setActiveVesselId] = React.useState<string | null>(null);

  // Initialise active vessel when user loads
  React.useEffect(() => {
    if (user?.yachtId && activeVesselId === null) {
      setActiveVesselId(user.yachtId);
    }
  }, [user?.yachtId, activeVesselId]);

  const activeVesselName = React.useMemo(() => {
    if (activeVesselId === null) return 'All Vessels';
    const vessel = fleetVessels.find((v) => v.yacht_id === activeVesselId);
    return vessel?.yacht_name || user?.yachtName || 'Vessel';
  }, [activeVesselId, fleetVessels, user?.yachtName]);

  const value = React.useMemo<VesselState>(
    () => ({
      vesselId: activeVesselId,
      vesselName: activeVesselName,
      vessels: fleetVessels,
      isFleetUser,
      isAllVessels: activeVesselId === null,
      setActiveVessel: setActiveVesselId,
    }),
    [activeVesselId, activeVesselName, fleetVessels, isFleetUser]
  );

  return (
    <VesselContext.Provider value={value}>
      {children}
    </VesselContext.Provider>
  );
}

/**
 * useActiveVessel — reads the current vessel context.
 * Returns vesselId (string when single vessel, null for "All Vessels").
 * Callers must check for null and omit .eq('yacht_id') when null.
 */
export function useActiveVessel(): VesselState {
  const ctx = React.useContext(VesselContext);
  if (!ctx) {
    // Fallback for components outside VesselProvider
    return {
      vesselId: null,
      vesselName: 'Vessel',
      vessels: [],
      isFleetUser: false,
      isAllVessels: false,
      setActiveVessel: () => {},
    };
  }
  return ctx;
}

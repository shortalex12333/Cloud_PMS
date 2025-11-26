'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Settings, AlertCircle, CheckCircle, Search } from 'lucide-react';

interface EquipmentStats {
  total: number;
  critical: number;
  operational: number;
  needs_attention: number;
}

// Mock data fallback
const MOCK_STATS: EquipmentStats = {
  total: 156,
  critical: 12,
  operational: 144,
  needs_attention: 8,
};

export default function EquipmentOverview() {
  const router = useRouter();
  const [stats, setStats] = useState<EquipmentStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.celeste7.ai/webhook').replace(/\/+$/, '');
        const response = await fetch(`${baseUrl}/v1/equipment/overview`);

        if (!response.ok) throw new Error('API unavailable');

        const data = await response.json();
        setStats(data);
      } catch (err) {
        console.log('[EquipmentOverview] Using mock data:', err);
        setStats(MOCK_STATS);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleSearch = (query: string) => {
    router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  if (loading || !stats) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-6 w-40 bg-muted rounded mb-4" />
          <div className="space-y-3">
            <div className="h-12 bg-muted rounded" />
            <div className="h-12 bg-muted rounded" />
            <div className="h-12 bg-muted rounded" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Settings className="h-5 w-5 text-primary" />
          Equipment Overview
        </h2>
        <span className="text-xs text-muted-foreground">
          {stats.total} systems
        </span>
      </div>

      <div className="space-y-3">
        {/* Operational */}
        <div
          onClick={() => handleSearch('operational equipment')}
          className="flex items-center justify-between p-3 bg-background border border-border rounded-md cursor-pointer hover:bg-accent/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <span className="text-sm">Operational</span>
          </div>
          <span className="text-sm font-medium text-green-600">{stats.operational}</span>
        </div>

        {/* Needs Attention */}
        <div
          onClick={() => handleSearch('equipment needs attention')}
          className="flex items-center justify-between p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-md cursor-pointer hover:bg-yellow-500/20 transition-colors"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-yellow-600" />
            <span className="text-sm text-yellow-600">Needs Attention</span>
          </div>
          <span className="text-sm font-medium text-yellow-600">
            {stats.needs_attention}
          </span>
        </div>

        {/* Critical Systems */}
        <div
          onClick={() => handleSearch('critical equipment systems')}
          className="flex items-center justify-between p-3 bg-background border border-border rounded-md cursor-pointer hover:bg-accent/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Settings className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">Critical Systems</span>
          </div>
          <span className="text-sm font-medium">{stats.critical}</span>
        </div>
      </div>

      {/* Search prompt */}
      <button
        onClick={() => handleSearch('equipment')}
        className="w-full mt-4 px-4 py-2 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 flex items-center justify-center gap-2"
      >
        <Search className="h-4 w-4" />
        Search Equipment
      </button>

      {/* Read-only notice */}
      <p className="mt-2 text-xs text-muted-foreground text-center">
        View details via Search bar
      </p>
    </div>
  );
}

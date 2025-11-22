'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { TrendingUp, AlertTriangle, Search } from 'lucide-react';

interface PredictiveInsight {
  equipment_id: string;
  equipment_name: string;
  risk_score: number;
  summary: string;
  contributing_factors: string[];
}

// Mock data fallback
const MOCK_INSIGHTS: PredictiveInsight[] = [
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

export default function PredictiveOverview() {
  const router = useRouter();
  const [insights, setInsights] = useState<PredictiveInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.celeste7.ai/webhook';
        const response = await fetch(`${baseUrl}/v1/predictive/top-risks`);

        if (!response.ok) throw new Error('API unavailable');

        const data = await response.json();
        setInsights(data.risks || data);
      } catch (err) {
        console.log('[PredictiveOverview] Using mock data:', err);
        setInsights(MOCK_INSIGHTS);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleItemClick = (equipmentName: string) => {
    router.push(`/search?q=${encodeURIComponent(equipmentName + ' risk analysis')}`);
  };

  if (loading) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-6 w-40 bg-muted rounded mb-4" />
          <div className="space-y-3">
            <div className="h-20 bg-muted rounded" />
            <div className="h-20 bg-muted rounded" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Predictive Overview
        </h2>
        <span className="text-xs text-muted-foreground">
          {insights.length} high-risk systems
        </span>
      </div>

      <div className="space-y-3">
        {insights.map((insight) => (
          <div
            key={insight.equipment_id}
            onClick={() => handleItemClick(insight.equipment_name)}
            className="p-3 bg-background border border-border rounded-md hover:bg-accent/50 transition-colors cursor-pointer group"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className={`h-4 w-4 ${
                  insight.risk_score >= 0.7 ? 'text-destructive' : 'text-yellow-600'
                }`} />
                <span className="font-medium text-sm">
                  {insight.equipment_name}
                </span>
              </div>
              <span className={`text-xs font-medium ${
                insight.risk_score >= 0.7 ? 'text-destructive' : 'text-yellow-600'
              }`}>
                {Math.round(insight.risk_score * 100)}% risk
              </span>
            </div>
            <p className="text-xs text-muted-foreground mb-2">
              {insight.summary}
            </p>
            <div className="flex items-center gap-1 text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
              <Search className="h-3 w-3" />
              <span>Click to search for details</span>
            </div>
          </div>
        ))}
      </div>

      {/* Read-only notice */}
      <div className="mt-4 p-2 bg-muted/50 rounded text-xs text-muted-foreground text-center">
        Use the Search bar to take action on equipment
      </div>
    </div>
  );
}

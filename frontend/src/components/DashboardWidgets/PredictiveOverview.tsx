'use client';

import { TrendingUp, AlertTriangle } from 'lucide-react';
import type { PredictiveInsight } from '@/types/dashboard';

export default function PredictiveOverview() {
  // TODO: Fetch from API
  const mockInsights: PredictiveInsight[] = [
    {
      equipment_id: '1',
      equipment_name: 'HVAC Chiller #3',
      risk_score: 0.78,
      summary: 'Repeated high-pressure faults detected',
      contributing_factors: ['Pressure spikes', 'Frequent restarts'],
      recommended_actions: ['Inspect compressor', 'Check refrigerant levels'],
      trend: 'degrading',
    },
    {
      equipment_id: '2',
      equipment_name: 'Stabiliser Pump Port',
      risk_score: 0.65,
      summary: 'Leak pattern emerging',
      contributing_factors: ['Seal degradation', 'Increased maintenance'],
      recommended_actions: ['Replace seal kit', 'Monitor oil levels'],
      trend: 'stable',
    },
  ];

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Predictive Overview
        </h2>
        <span className="text-xs text-muted-foreground">
          {mockInsights.length} high-risk systems
        </span>
      </div>

      <div className="space-y-4">
        {mockInsights.map((insight) => (
          <div
            key={insight.equipment_id}
            className="p-3 bg-background border border-border rounded-md hover:bg-accent/50 transition-colors cursor-pointer"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                <span className="font-medium text-sm">
                  {insight.equipment_name}
                </span>
              </div>
              <span className="text-xs font-medium text-yellow-600">
                {Math.round(insight.risk_score * 100)}% risk
              </span>
            </div>
            <p className="text-xs text-muted-foreground mb-2">
              {insight.summary}
            </p>
            <div className="flex gap-2">
              <button className="text-xs px-2 py-1 bg-primary text-primary-foreground rounded hover:bg-primary/90">
                Inspect
              </button>
              <button className="text-xs px-2 py-1 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80">
                View Details
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * SmartSummaryCard Component
 *
 * Displays AI-generated daily briefing / situational awareness
 */

'use client';

import { Sparkles, TrendingUp, AlertTriangle, Info } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import type { MicroAction } from '@/types/actions';

interface SmartSummaryCardProps {
  summary: {
    title: string;
    generated_at: string;
    overview: string;
    insights: {
      type: 'info' | 'warning' | 'trend' | 'prediction';
      title: string;
      description: string;
      confidence?: number;
    }[];
    recommendations: {
      priority: 'low' | 'medium' | 'high';
      action: string;
      reason: string;
    }[];
  };
  actions?: MicroAction[];
}

export function SmartSummaryCard({ summary, actions = [] }: SmartSummaryCardProps) {
  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-orange-600" />;
      case 'trend':
        return <TrendingUp className="h-4 w-4 text-blue-600" />;
      case 'prediction':
        return <Sparkles className="h-4 w-4 text-purple-600" />;
      default:
        return <Info className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        {/* AI Icon */}
        <div className="mt-1 text-purple-600">
          <Sparkles className="h-5 w-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title & Badge */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-foreground">{summary.title}</h3>
            <span className="text-xs px-2 py-0.5 rounded-full border border-purple-200 bg-purple-50 text-purple-700 font-medium">
              AI-Generated
            </span>
          </div>

          {/* Generated At */}
          <p className="text-xs text-muted-foreground mb-3">
            Generated: {new Date(summary.generated_at).toLocaleString()}
          </p>

          {/* Overview */}
          <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
            {summary.overview}
          </p>

          {/* Insights */}
          {summary.insights.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-medium text-muted-foreground uppercase mb-2">
                Key Insights
              </p>
              <ul className="space-y-2">
                {summary.insights.map((insight, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 text-sm border-l-2 border-muted pl-3"
                  >
                    <div className="mt-0.5">{getInsightIcon(insight.type)}</div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium">{insight.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {insight.description}
                      </p>
                      {insight.confidence && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Confidence: {(insight.confidence * 100).toFixed(0)}%
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {summary.recommendations.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-medium text-muted-foreground uppercase mb-2">
                Recommendations
              </p>
              <ul className="space-y-2">
                {summary.recommendations.map((rec, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 text-sm p-2 rounded border border-muted"
                  >
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full border font-medium uppercase flex-shrink-0 ${getPriorityColor(
                        rec.priority
                      )}`}
                    >
                      {rec.priority}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium">{rec.action}</p>
                      <p className="text-xs text-muted-foreground">{rec.reason}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{}}
                variant="secondary"
                size="sm"
                showIcon={true}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

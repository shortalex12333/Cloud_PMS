/**
 * CelesteOS API Client - Usage Examples
 *
 * This file demonstrates how to use the API client for common operations.
 */

import api, { CelesteApiClient, SearchRequest } from './api';

// ============================================
// Example 1: Initialize API Client
// ============================================

// In your app initialization (e.g., main.ts, _app.tsx)
function initializeApp() {
  api.init({
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'https://api.celesteos.com',
    searchEngineUrl: process.env.NEXT_PUBLIC_SEARCH_ENGINE_URL,
    predictiveEngineUrl: process.env.NEXT_PUBLIC_PREDICTIVE_ENGINE_URL || 'https://celeste-predictive-api.onrender.com',

    // Get JWT token from your auth system
    getAuthToken: () => {
      // Example: From localStorage
      return localStorage.getItem('auth_token');

      // Or from your auth context
      // return authContext.getToken();
    },

    // Get yacht signature from your session
    getYachtSignature: () => {
      return localStorage.getItem('yacht_signature');
    },
  });
}

// ============================================
// Example 2: Search with Streaming
// ============================================

async function streamingSearchExample() {
  const client = api.get();

  const searchRequest: SearchRequest = {
    query: 'fault code E047 on main engine',
    mode: 'auto',
  };

  console.log('Streaming search results...');

  try {
    for await (const card of client.searchStream(searchRequest)) {
      console.log('Received card:', card);

      // Update UI with each card as it arrives
      // displaySearchCard(card);

      if (card.type === 'predictive') {
        console.log(`Predictive insight: ${card.summary}`);
        console.log(`Risk score: ${card.risk_score}`);
      }
    }

    console.log('Search complete!');
  } catch (error) {
    console.error('Search error:', error);
  }
}

// ============================================
// Example 3: Search Without Streaming
// ============================================

async function standardSearchExample() {
  const client = api.get();

  const response = await client.search({
    query: 'HVAC maintenance manual',
    mode: 'standard',
    filters: {
      document_type: 'manual',
    },
  });

  console.log('Search results:', response);
  console.log(`Intent detected: ${response.intent}`);
  console.log(`Found ${response.results.length} results`);

  // Display micro-actions
  response.actions.forEach((action) => {
    console.log(`Action available: ${action.label}`);
  });
}

// ============================================
// Example 4: Get Predictive State
// ============================================

async function getPredictiveStateExample() {
  const client = api.get();
  const yachtId = 'your-yacht-uuid-here';

  const predictiveState = await client.getPredictiveState(yachtId);

  console.log('Predictive state:', predictiveState);
  console.log(`High risk equipment: ${predictiveState.high_risk_count}`);
  console.log(`Emerging risk: ${predictiveState.emerging_risk_count}`);

  // Display top 5 highest risk equipment
  const topRisks = predictiveState.equipment_risks.slice(0, 5);
  topRisks.forEach((equipment) => {
    console.log(
      `${equipment.equipment_name}: ${equipment.risk_score.toFixed(2)} ${equipment.trend}`
    );
  });
}

// ============================================
// Example 5: Get Predictive Insights
// ============================================

async function getPredictiveInsightsExample() {
  const client = api.get();
  const yachtId = 'your-yacht-uuid-here';

  const insights = await client.getPredictiveInsights(yachtId, 'high', 20);

  console.log('Predictive insights:', insights);
  console.log(`Critical insights: ${insights.critical_count}`);

  insights.insights.forEach((insight) => {
    console.log(`\n[${insight.severity.toUpperCase()}] ${insight.summary}`);
    console.log(`Explanation: ${insight.explanation}`);
    if (insight.recommended_action) {
      console.log(`Recommended: ${insight.recommended_action}`);
    }
  });
}

// ============================================
// Example 6: Get Predictive Card for Equipment
// ============================================

async function getPredictiveCardExample() {
  const client = api.get();
  const equipmentId = 'equipment-uuid-here';

  const card = await client.getPredictiveCard(equipmentId);

  console.log('Predictive card:', card);
  console.log(`Equipment: ${card.equipment}`);
  console.log(`Risk: ${card.risk_score} ${card.trend}`);
  console.log(`Severity: ${card.severity}`);

  // Display recommendations
  card.recommendations?.forEach((rec) => {
    console.log(`- ${rec}`);
  });
}

// ============================================
// Example 7: Create Work Order from Search
// ============================================

async function createWorkOrderExample() {
  const client = api.get();

  // After user clicks "Create Work Order" micro-action
  const workOrder = await client.createWorkOrder({
    equipment_id: 'equipment-uuid',
    title: 'Fix stabiliser pump leak',
    description: 'Hydraulic leak observed at starboard stabiliser pump',
    priority: 'important',
    type: 'corrective',
  });

  console.log('Work order created:', workOrder.work_order_id);
}

// ============================================
// Example 8: Add to Handover
// ============================================

async function addToHandoverExample() {
  const client = api.get();

  // Create handover draft first
  const handover = await client.createHandover(
    'Weekly Engineering Handover',
    '2024-11-13',
    '2024-11-20'
  );

  // Add fault to handover
  const item = await client.addToHandover({
    handover_id: handover.handover_id,
    source_type: 'fault',
    source_id: 'fault-uuid',
    summary: 'Main engine E047 overheat behavior',
    importance: 'high',
  });

  console.log('Added to handover:', item.item_id);
}

// ============================================
// Example 9: Create Note
// ============================================

async function createNoteExample() {
  const client = api.get();

  const note = await client.createNote({
    text: 'Oil leak observed at 14:23 near starboard generator. Monitoring.',
    equipment_id: 'generator-uuid',
    tags: ['leak', 'monitoring'],
  });

  console.log('Note created:', note.note_id);
}

// ============================================
// Example 10: Get Dashboard Summary
// ============================================

async function getDashboardExample() {
  const client = api.get();
  const yachtId = 'your-yacht-uuid-here';

  const dashboard = await client.getDashboardSummary(yachtId);

  console.log('Dashboard summary:', dashboard);
  console.log(`High risk equipment count: ${dashboard.high_risk_equipment.length}`);
  console.log(`Recent insights: ${dashboard.recent_insights.length}`);
}

// ============================================
// Example 11: Trigger Predictive Computation
// ============================================

async function runPredictiveExample() {
  const client = api.get();
  const yachtId = 'your-yacht-uuid-here';

  console.log('Triggering predictive computation...');

  const result = await client.runPredictive(yachtId, false);

  console.log('Predictive run complete:', result);
  console.log(`Computed at: ${result.computed_at}`);
  console.log('Summary:', result.summary);
}

// ============================================
// Example 12: Get Anomalies
// ============================================

async function getAnomaliesExample() {
  const client = api.get();
  const yachtId = 'your-yacht-uuid-here';

  const anomalies = await client.getAnomalies(yachtId);

  console.log('Detected anomalies:', anomalies);
  console.log(`Critical anomalies: ${anomalies.critical_anomalies}`);

  anomalies.anomalies.forEach((anomaly) => {
    console.log(`\nAnomaly: ${anomaly.equipment_name}`);
    console.log(`Type: ${anomaly.anomaly_type}`);
    console.log(`Severity: ${anomaly.severity}`);
    console.log(`Description: ${anomaly.description}`);
  });
}

// ============================================
// Example 13: Error Handling
// ============================================

async function errorHandlingExample() {
  const client = api.get();

  try {
    const result = await client.search({
      query: 'test query',
    });
    console.log('Success:', result);
  } catch (error) {
    if (error instanceof Error && 'status' in error) {
      const apiError = error as any;

      switch (apiError.status) {
        case 401:
          console.error('Unauthorized - please log in');
          // Redirect to login
          break;
        case 403:
          console.error('Forbidden - insufficient permissions');
          break;
        case 404:
          console.error('Not found');
          break;
        case 500:
          console.error('Server error:', apiError.data);
          break;
        default:
          console.error('API error:', apiError.statusText);
      }
    } else {
      console.error('Unknown error:', error);
    }
  }
}

// ============================================
// Example 14: React Hook Integration
// ============================================

// Example React hook using the API client
/*
import { useState, useEffect } from 'react';
import api from '@/lib/api';

export function useSearchResults(query: string) {
  const [results, setResults] = useState<SearchResultCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!query) return;

    const performSearch = async () => {
      setLoading(true);
      setError(null);
      setResults([]);

      try {
        const client = api.get();
        const cards: SearchResultCard[] = [];

        for await (const card of client.searchStream({ query })) {
          setResults((prev) => [...prev, card]);
        }

        setLoading(false);
      } catch (err) {
        setError(err as Error);
        setLoading(false);
      }
    };

    performSearch();
  }, [query]);

  return { results, loading, error };
}

export function usePredictiveState(yachtId: string) {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchState = async () => {
      try {
        const client = api.get();
        const data = await client.getPredictiveState(yachtId);
        setState(data);
      } catch (error) {
        console.error('Failed to fetch predictive state:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchState();
  }, [yachtId]);

  return { state, loading };
}
*/

// ============================================
// Export examples for testing
// ============================================

export {
  initializeApp,
  streamingSearchExample,
  standardSearchExample,
  getPredictiveStateExample,
  getPredictiveInsightsExample,
  getPredictiveCardExample,
  createWorkOrderExample,
  addToHandoverExample,
  createNoteExample,
  getDashboardExample,
  runPredictiveExample,
  getAnomaliesExample,
  errorHandlingExample,
};

/**
 * CelesteOS Situation Engine
 *
 * Thin situation detection + policy recommendation engine.
 * Facts come from DB (Supabase). Logic lives here.
 *
 * Patterns supported (v1):
 * - RECURRENT_SYMPTOM: Same symptom on same equipment >= 3 times in 60 days
 * - RECURRENT_SYMPTOM_PRE_EVENT: Same as above, but critical event within 72h
 * - HIGH_RISK_EQUIPMENT: Equipment with risk_score > 0.7 mentioned
 */

import { createClient } from '@/lib/supabaseClient';
import type {
  Situation,
  Recommendation,
  ResolvedEntity,
  VesselContext,
  RecurrenceCheckResult,
  WorkOrderSummary,
  UserRole,
  Urgency,
} from './types';

// Palliative fix indicators (temporary fixes that don't address root cause)
const PALLIATIVE_KEYWORDS = [
  'top-up', 'top up', 'topped up', 'temporary', 'temp fix',
  'reset', 'cleared', 'silenced', 'bypassed', 'workaround',
  'pending', 'deferred', 'monitor', 'watching',
];

/**
 * Main Situation Engine class
 */
export class SituationEngine {
  /**
   * Detect situation from resolved entities and vessel context
   */
  async detectSituation(
    yachtId: string,
    resolvedEntities: ResolvedEntity[],
    vesselContext: VesselContext
  ): Promise<Situation | null> {
    if (!resolvedEntities || resolvedEntities.length === 0) {
      return null;
    }

    // Extract equipment and symptoms from resolved entities
    const equipmentEntities = resolvedEntities.filter((e) => e.type === 'equipment');
    const symptomEntities = resolvedEntities.filter((e) => e.type === 'symptom');

    // Pattern 1: Recurrent symptom on equipment
    if (equipmentEntities.length > 0 && symptomEntities.length > 0) {
      const situation = await this.checkRecurrentSymptom(
        yachtId,
        equipmentEntities[0],
        symptomEntities[0],
        vesselContext
      );
      if (situation) return situation;
    }

    // Pattern 2: High risk equipment mentioned (no symptom required)
    if (equipmentEntities.length > 0) {
      const situation = await this.checkHighRiskEquipment(
        yachtId,
        equipmentEntities[0]
      );
      if (situation) return situation;
    }

    return null;
  }

  /**
   * Check for recurrent symptom pattern
   */
  private async checkRecurrentSymptom(
    yachtId: string,
    equipment: ResolvedEntity,
    symptom: ResolvedEntity,
    vesselContext: VesselContext
  ): Promise<Situation | null> {
    const equipmentLabel = equipment.canonical || equipment.value || '';
    const symptomCode = symptom.canonical || symptom.value || '';

    if (!equipmentLabel || !symptomCode) {
      return null;
    }

    const supabase = createClient();

    try {
      // Call DB function to check recurrence
      const { data, error } = await supabase.rpc('check_symptom_recurrence', {
        p_yacht_id: yachtId,
        p_equipment_label: equipmentLabel,
        p_symptom_code: symptomCode,
        p_threshold_count: 3,
        p_threshold_days: 60,
      });

      if (error || !data) {
        return null;
      }

      const recurrence: RecurrenceCheckResult = Array.isArray(data) ? data[0] : data;

      if (!recurrence?.is_recurrent) {
        return null;
      }

      // Build evidence
      const evidence: string[] = [
        `${recurrence.occurrence_count} ${symptomCode} events in ${recurrence.span_days} days`,
      ];

      // Check last fix type
      const lastWo = await this.getLastWorkOrder(yachtId, equipmentLabel);
      if (lastWo && this.isPalliative(lastWo)) {
        evidence.push(`Last fix was palliative (${lastWo.title || 'unknown'})`);
      }

      // Check if there are still open reports
      if (recurrence.open_count > 0) {
        evidence.push(`${recurrence.open_count} unresolved occurrence(s)`);
      }

      // Determine if pre-critical-event
      const hoursUntilEvent = vesselContext.hours_until_event;
      const nextEventType = vesselContext.next_event_type;
      const isCriticalWindow =
        hoursUntilEvent !== undefined &&
        hoursUntilEvent < 72 &&
        ['charter', 'survey', 'crossing'].includes(nextEventType || '');

      return {
        type: isCriticalWindow ? 'RECURRENT_SYMPTOM_PRE_EVENT' : 'RECURRENT_SYMPTOM',
        label: `${equipmentLabel} ${symptomCode} (recurring)`,
        severity: isCriticalWindow ? 'high' : 'medium',
        context: isCriticalWindow
          ? `${nextEventType?.charAt(0).toUpperCase()}${nextEventType?.slice(1)} in ${Math.floor(hoursUntilEvent)}h`
          : null,
        evidence,
      };
    } catch (err) {
      console.error('Error checking symptom recurrence:', err);
      return null;
    }
  }

  /**
   * Check if equipment has elevated risk score
   */
  private async checkHighRiskEquipment(
    yachtId: string,
    equipment: ResolvedEntity
  ): Promise<Situation | null> {
    const equipmentId = equipment.entity_id;
    const equipmentLabel = equipment.canonical || equipment.value || '';

    if (!equipmentId) {
      return null;
    }

    const supabase = createClient();

    try {
      const { data, error } = await supabase
        .from('predictive_state')
        .select('risk_score, confidence')
        .eq('equipment_id', equipmentId)
        .single();

      if (error || !data) {
        return null;
      }

      const riskScore = data.risk_score || 0;
      const confidence = data.confidence || 0;

      if (riskScore < 0.7) {
        return null;
      }

      return {
        type: 'HIGH_RISK_EQUIPMENT',
        label: `${equipmentLabel} at elevated risk`,
        severity: riskScore > 0.85 ? 'high' : 'medium',
        context: null,
        evidence: [
          `Risk score: ${Math.round(riskScore * 100)}%`,
          `Confidence: ${Math.round(confidence * 100)}%`,
        ],
      };
    } catch (err) {
      console.warn('Error checking equipment risk:', err);
      return null;
    }
  }

  /**
   * Get recommended actions for a detected situation
   */
  getRecommendations(
    situation: Situation | null,
    yachtId: string,
    resolvedEntities: ResolvedEntity[],
    userRole: UserRole = 'crew'
  ): Recommendation[] {
    if (!situation) {
      return [];
    }

    // Branch by role: captain/management get high-level recs, engineers get actionable recs
    if (userRole === 'captain' || userRole === 'management') {
      return this.getRecommendationsForCaptain(situation, yachtId, resolvedEntities);
    }
    return this.getRecommendationsForEngineering(situation, yachtId, resolvedEntities);
  }

  /**
   * Engineering-focused recommendations: actionable WOs and diagnostics
   */
  private getRecommendationsForEngineering(
    situation: Situation,
    _yachtId: string,
    _resolvedEntities: ResolvedEntity[]
  ): Recommendation[] {
    if (situation.type === 'RECURRENT_SYMPTOM' || situation.type === 'RECURRENT_SYMPTOM_PRE_EVENT') {
      return this.policyRecurrentSymptomEngineering(situation);
    }

    if (situation.type === 'HIGH_RISK_EQUIPMENT') {
      return this.policyHighRiskEngineering(situation);
    }

    return [];
  }

  /**
   * Captain/management-focused recommendations: risk framing and coordination
   */
  private getRecommendationsForCaptain(
    situation: Situation,
    _yachtId: string,
    _resolvedEntities: ResolvedEntity[]
  ): Recommendation[] {
    if (situation.type === 'RECURRENT_SYMPTOM' || situation.type === 'RECURRENT_SYMPTOM_PRE_EVENT') {
      return this.policyRecurrentSymptomCaptain(situation);
    }

    if (situation.type === 'HIGH_RISK_EQUIPMENT') {
      return this.policyHighRiskCaptain(situation);
    }

    return [];
  }

  /**
   * Engineering policy for recurrent symptom situations
   */
  private policyRecurrentSymptomEngineering(situation: Situation): Recommendation[] {
    const recommendations: Recommendation[] = [];

    // Primary action: Create root cause investigation WO
    recommendations.push({
      action: 'create_work_order',
      template: 'inspection_root_cause',
      reason: 'Recurring issue suggests underlying cause not addressed',
      parts_available: true,
      urgency: situation.severity === 'high' ? 'urgent' : 'normal',
    });

    // If pre-event critical window, add diagnostic
    if (situation.type === 'RECURRENT_SYMPTOM_PRE_EVENT') {
      recommendations.push({
        action: 'run_diagnostic',
        template: null,
        reason: 'Verify system health before critical period',
        parts_available: true,
        urgency: 'high',
      });

      // Also suggest monitoring
      recommendations.push({
        action: 'configure_alert',
        template: null,
        reason: 'Lower alert thresholds during critical period',
        parts_available: true,
        urgency: 'normal',
      });
    }

    return recommendations;
  }

  /**
   * Captain policy for recurrent symptom situations
   */
  private policyRecurrentSymptomCaptain(situation: Situation): Recommendation[] {
    const recommendations: Recommendation[] = [];

    if (situation.type === 'RECURRENT_SYMPTOM_PRE_EVENT') {
      recommendations.push({
        action: 'review_charter_risk',
        template: null,
        reason: 'Recurring issue before charter - assess operational risk',
        parts_available: true,
        urgency: 'high',
      });
      recommendations.push({
        action: 'coordinate_with_engineering',
        template: null,
        reason: 'Confirm engineering team has root cause investigation underway',
        parts_available: true,
        urgency: 'high',
      });
    } else {
      recommendations.push({
        action: 'review_maintenance_status',
        template: null,
        reason: 'Recurring issue - review with chief engineer',
        parts_available: true,
        urgency: 'normal',
      });
    }

    // For high severity, suggest contingency planning
    if (situation.severity === 'high') {
      recommendations.push({
        action: 'prepare_contingency',
        template: null,
        reason: 'High-severity recurring issue - consider backup plans',
        parts_available: true,
        urgency: 'elevated',
      });
    }

    return recommendations;
  }

  /**
   * Engineering policy for high risk equipment situations
   */
  private policyHighRiskEngineering(situation: Situation): Recommendation[] {
    return [
      {
        action: 'view_predictive_analysis',
        template: null,
        reason: 'Review failure modes and recommended preventive actions',
        parts_available: true,
        urgency: 'normal',
      },
      {
        action: 'schedule_inspection',
        template: 'predictive_inspection',
        reason: 'Proactive inspection before potential failure',
        parts_available: true,
        urgency: situation.severity === 'high' ? 'elevated' : 'normal',
      },
    ];
  }

  /**
   * Captain policy for high risk equipment situations
   */
  private policyHighRiskCaptain(situation: Situation): Recommendation[] {
    const recommendations: Recommendation[] = [
      {
        action: 'review_risk_summary',
        template: null,
        reason: 'Equipment flagged as elevated risk - review status',
        parts_available: true,
        urgency: 'normal',
      },
    ];

    if (situation.severity === 'high') {
      recommendations.push({
        action: 'coordinate_with_engineering',
        template: null,
        reason: 'High-risk equipment - ensure proactive inspection scheduled',
        parts_available: true,
        urgency: 'elevated',
      });
    }

    return recommendations;
  }

  /**
   * Get the most recent work order for equipment
   */
  private async getLastWorkOrder(
    yachtId: string,
    equipmentLabel: string
  ): Promise<WorkOrderSummary | null> {
    const supabase = createClient();

    try {
      // Query work_orders by equipment label
      const { data, error } = await supabase
        .from('pms_work_orders')
        .select('id, title, created_at')
        .eq('yacht_id', yachtId)
        .ilike('title', `%${equipmentLabel}%`)
        .order('created_at', { ascending: false })
        .limit(1)
        .single();

      if (error || !data) {
        return null;
      }

      return {
        id: data.id,
        title: data.title || '',
        created_at: data.created_at,
      };
    } catch {
      return null;
    }
  }

  /**
   * Check if a work order was a palliative (temporary) fix
   */
  private isPalliative(wo: WorkOrderSummary): boolean {
    const title = (wo.title || '').toLowerCase();
    const notes = ((wo.properties as Record<string, string>)?.notes || '').toLowerCase();
    const combinedText = `${title} ${notes}`;

    return PALLIATIVE_KEYWORDS.some((kw) => combinedText.includes(kw));
  }

  /**
   * Log suggestion for future learning
   */
  async logSuggestion(
    yachtId: string,
    userId: string | null,
    queryText: string,
    intent: string | null,
    situation: Situation | null,
    recommendations: Recommendation[],
    searchQueryId?: string
  ): Promise<string | null> {
    const supabase = createClient();

    try {
      const { data, error } = await supabase
        .from('suggestion_log')
        .insert({
          yacht_id: yachtId,
          user_id: userId,
          query_text: queryText,
          intent,
          search_query_id: searchQueryId,
          situation_detected: situation !== null,
          situation_type: situation?.type,
          suggested_actions: recommendations.map((r) => ({
            action: r.action,
            template: r.template,
            reason: r.reason,
            parts_available: r.parts_available,
            urgency: r.urgency,
          })),
        })
        .select('id')
        .single();

      if (error) {
        console.error('Error logging suggestion:', error);
        return null;
      }

      return data?.id || null;
    } catch (err) {
      console.error('Error logging suggestion:', err);
      return null;
    }
  }

  /**
   * Log symptom occurrence from search query
   */
  async logSymptomReport(
    yachtId: string,
    equipmentLabel: string,
    symptomCode: string,
    symptomLabel: string,
    userId?: string,
    searchQueryId?: string
  ): Promise<string | null> {
    const supabase = createClient();

    try {
      const { data, error } = await supabase
        .from('symptom_reports')
        .insert({
          yacht_id: yachtId,
          equipment_label: equipmentLabel,
          symptom_code: symptomCode,
          symptom_label: symptomLabel,
          reported_by: userId,
          search_query_id: searchQueryId,
          source: 'search',
        })
        .select('id')
        .single();

      if (error) {
        console.error('Error logging symptom report:', error);
        return null;
      }

      return data?.id || null;
    } catch (err) {
      console.error('Error logging symptom report:', err);
      return null;
    }
  }
}

// Singleton instance
let engineInstance: SituationEngine | null = null;

/**
 * Get or create singleton SituationEngine instance
 */
export function getSituationEngine(): SituationEngine {
  if (!engineInstance) {
    engineInstance = new SituationEngine();
  }
  return engineInstance;
}

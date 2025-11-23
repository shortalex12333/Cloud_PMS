-- ============================================
-- CelesteOS Situational Search - ONE FAT FUNCTION
-- All brain in SQL, n8n just glues
-- ============================================

-- Drop if exists to allow updates
DROP FUNCTION IF EXISTS public.situational_search(TEXT, VECTOR(1536), UUID, TEXT, INT, JSONB, TEXT);

CREATE OR REPLACE FUNCTION public.situational_search(
  p_query_text TEXT,
  p_embedding VECTOR(1536),
  p_yacht_id UUID,
  p_intent TEXT DEFAULT 'search_knowledge',
  p_match_count INT DEFAULT 10,
  p_entity_hints JSONB DEFAULT '[]'::JSONB,
  p_user_role TEXT DEFAULT 'crew'
) RETURNS JSONB AS $$
DECLARE
  v_resolved_entities JSONB := '[]'::JSONB;
  v_equipment_entity JSONB;
  v_symptom_entity JSONB;
  v_equipment_id UUID;
  v_equipment_label TEXT;
  v_symptom_code TEXT;
  v_symptom_label TEXT;
  v_vessel_context JSONB;
  v_situation JSONB;
  v_recommendations JSONB := '[]'::JSONB;
  v_disambiguation JSONB;
  v_cards JSONB;
  v_recurrence RECORD;
  v_risk_score FLOAT;
  v_hours_until_event FLOAT;
  v_is_pre_charter BOOLEAN := FALSE;
  v_situation_type TEXT;
  v_severity TEXT := 'low';
BEGIN
  -- ============================================
  -- 1. RESOLVE ENTITIES from GPT hints
  -- ============================================

  -- Process each entity hint from GPT extraction
  FOR v_equipment_entity IN SELECT * FROM jsonb_array_elements(p_entity_hints) WHERE value->>'type' = 'equipment'
  LOOP
    -- Try to resolve via graph_nodes
    SELECT jsonb_build_object(
      'type', 'equipment',
      'value', v_equipment_entity->>'value',
      'canonical', COALESCE(gn.label, v_equipment_entity->>'value'),
      'entity_id', gn.id,
      'confidence', COALESCE((v_equipment_entity->>'confidence')::FLOAT, 0.5)
    )
    INTO v_resolved_entities
    FROM graph_nodes gn
    WHERE gn.yacht_id = p_yacht_id
      AND gn.node_type = 'equipment'
      AND (
        gn.normalized_label = lower(trim(v_equipment_entity->>'value'))
        OR gn.label ILIKE '%' || (v_equipment_entity->>'value') || '%'
      )
    ORDER BY
      CASE WHEN gn.normalized_label = lower(trim(v_equipment_entity->>'value')) THEN 0 ELSE 1 END,
      gn.created_at DESC
    LIMIT 1;

    IF v_resolved_entities IS NOT NULL THEN
      v_equipment_id := (v_resolved_entities->>'entity_id')::UUID;
      v_equipment_label := v_resolved_entities->>'canonical';
    ELSE
      -- No match found, use raw value
      v_equipment_label := v_equipment_entity->>'value';
      v_resolved_entities := jsonb_build_object(
        'type', 'equipment',
        'value', v_equipment_entity->>'value',
        'canonical', v_equipment_entity->>'value',
        'entity_id', NULL,
        'confidence', COALESCE((v_equipment_entity->>'confidence')::FLOAT, 0.3)
      );
    END IF;
  END LOOP;

  -- Get symptom entity
  SELECT value INTO v_symptom_entity
  FROM jsonb_array_elements(p_entity_hints)
  WHERE value->>'type' = 'symptom'
  LIMIT 1;

  IF v_symptom_entity IS NOT NULL THEN
    v_symptom_code := COALESCE(v_symptom_entity->>'canonical', v_symptom_entity->>'value');
    v_symptom_label := v_symptom_entity->>'value';
  END IF;

  -- ============================================
  -- 2. GET VESSEL CONTEXT
  -- ============================================

  SELECT jsonb_build_object(
    'current_status', COALESCE(vc.current_status, 'in_port'),
    'next_event_type', vc.next_event_type,
    'next_event_at', vc.next_event_at,
    'hours_until_event',
      CASE WHEN vc.next_event_at IS NOT NULL
           THEN EXTRACT(EPOCH FROM (vc.next_event_at - NOW())) / 3600
           ELSE NULL END,
    'is_pre_charter_critical',
      CASE WHEN vc.next_event_type = 'charter'
            AND vc.next_event_at <= NOW() + INTERVAL '72 hours'
           THEN TRUE ELSE FALSE END,
    'hot_work_permitted', COALESCE(vc.hot_work_permitted, TRUE),
    'guests_on_board', COALESCE(vc.guests_on_board, FALSE)
  )
  INTO v_vessel_context
  FROM vessel_context vc
  WHERE vc.yacht_id = p_yacht_id;

  -- Default if no context
  IF v_vessel_context IS NULL THEN
    v_vessel_context := jsonb_build_object(
      'current_status', 'in_port',
      'next_event_type', NULL,
      'next_event_at', NULL,
      'hours_until_event', NULL,
      'is_pre_charter_critical', FALSE,
      'hot_work_permitted', TRUE,
      'guests_on_board', FALSE
    );
  END IF;

  v_hours_until_event := (v_vessel_context->>'hours_until_event')::FLOAT;
  v_is_pre_charter := (v_vessel_context->>'is_pre_charter_critical')::BOOLEAN;

  -- ============================================
  -- 3. DETECT SITUATION
  -- ============================================

  v_situation := NULL;

  -- Pattern 1: Recurrent symptom
  IF v_equipment_label IS NOT NULL AND v_symptom_code IS NOT NULL THEN
    SELECT * INTO v_recurrence
    FROM check_symptom_recurrence(
      p_yacht_id,
      v_equipment_label,
      v_symptom_code,
      3,  -- threshold count
      60  -- threshold days
    );

    IF v_recurrence IS NOT NULL AND v_recurrence.is_recurrent THEN
      -- Determine if pre-event critical
      IF v_is_pre_charter OR (v_hours_until_event IS NOT NULL AND v_hours_until_event < 72) THEN
        v_situation_type := 'RECURRENT_SYMPTOM_PRE_EVENT';
        v_severity := 'high';
      ELSE
        v_situation_type := 'RECURRENT_SYMPTOM';
        v_severity := 'medium';
      END IF;

      v_situation := jsonb_build_object(
        'type', v_situation_type,
        'label', v_equipment_label || ' ' || v_symptom_code || ' (recurring)',
        'severity', v_severity,
        'context', CASE WHEN v_is_pre_charter
                        THEN 'Charter in ' || ROUND(v_hours_until_event) || 'h'
                        ELSE NULL END,
        'evidence', jsonb_build_array(
          v_recurrence.occurrence_count || ' ' || v_symptom_code || ' events in ' || v_recurrence.span_days || ' days',
          CASE WHEN v_recurrence.open_count > 0
               THEN v_recurrence.open_count || ' unresolved occurrence(s)'
               ELSE NULL END
        )
      );
    END IF;
  END IF;

  -- Pattern 2: High risk equipment (if no recurrent symptom found)
  IF v_situation IS NULL AND v_equipment_id IS NOT NULL THEN
    SELECT ps.risk_score INTO v_risk_score
    FROM predictive_state ps
    WHERE ps.equipment_id = v_equipment_id;

    IF v_risk_score IS NOT NULL AND v_risk_score > 0.7 THEN
      v_situation := jsonb_build_object(
        'type', 'HIGH_RISK_EQUIPMENT',
        'label', v_equipment_label || ' at elevated risk',
        'severity', CASE WHEN v_risk_score > 0.85 THEN 'high' ELSE 'medium' END,
        'context', NULL,
        'evidence', jsonb_build_array(
          'Risk score: ' || ROUND(v_risk_score * 100) || '%'
        )
      );
      v_severity := CASE WHEN v_risk_score > 0.85 THEN 'high' ELSE 'medium' END;
    END IF;
  END IF;

  -- ============================================
  -- 4. BUILD RECOMMENDATIONS (role-aware)
  -- ============================================

  IF v_situation IS NOT NULL THEN
    IF p_user_role IN ('captain', 'management') THEN
      -- Captain/management recommendations
      IF v_situation_type IN ('RECURRENT_SYMPTOM', 'RECURRENT_SYMPTOM_PRE_EVENT') THEN
        IF v_situation_type = 'RECURRENT_SYMPTOM_PRE_EVENT' THEN
          v_recommendations := jsonb_build_array(
            jsonb_build_object(
              'action', 'review_charter_risk',
              'label', 'Review Charter Risk',
              'reason', 'Recurring issue before charter - assess operational risk',
              'payload', jsonb_build_object(),
              'urgency', 'high'
            ),
            jsonb_build_object(
              'action', 'coordinate_with_engineering',
              'label', 'Coordinate with Engineering',
              'reason', 'Confirm root cause investigation underway',
              'payload', jsonb_build_object(),
              'urgency', 'high'
            )
          );
        ELSE
          v_recommendations := jsonb_build_array(
            jsonb_build_object(
              'action', 'review_maintenance_status',
              'label', 'Review Maintenance Status',
              'reason', 'Recurring issue - review with chief engineer',
              'payload', jsonb_build_object(),
              'urgency', 'normal'
            )
          );
        END IF;
      ELSIF v_situation->>'type' = 'HIGH_RISK_EQUIPMENT' THEN
        v_recommendations := jsonb_build_array(
          jsonb_build_object(
            'action', 'review_risk_summary',
            'label', 'Review Risk Summary',
            'reason', 'Equipment flagged as elevated risk',
            'payload', jsonb_build_object(),
            'urgency', 'normal'
          )
        );
      END IF;
    ELSE
      -- Engineering recommendations
      IF v_situation_type IN ('RECURRENT_SYMPTOM', 'RECURRENT_SYMPTOM_PRE_EVENT') THEN
        v_recommendations := jsonb_build_array(
          jsonb_build_object(
            'action', 'create_work_order',
            'label', 'Create work order: ' || v_equipment_label || ' ' || COALESCE(v_symptom_code, ''),
            'reason', 'Recurring issue suggests underlying cause not addressed',
            'payload', jsonb_build_object(
              'equipment_id', v_equipment_id,
              'equipment_label', v_equipment_label,
              'title', v_equipment_label || ' ' || COALESCE(v_symptom_code, ''),
              'priority', CASE WHEN v_severity = 'high' THEN 'high' ELSE 'normal' END,
              'due_before', CASE WHEN v_is_pre_charter THEN v_vessel_context->>'next_event_at' ELSE NULL END
            ),
            'urgency', CASE WHEN v_severity = 'high' THEN 'urgent' ELSE 'normal' END
          )
        );

        -- Add diagnostic if pre-event
        IF v_situation_type = 'RECURRENT_SYMPTOM_PRE_EVENT' THEN
          v_recommendations := v_recommendations || jsonb_build_array(
            jsonb_build_object(
              'action', 'run_diagnostic',
              'label', 'Run Diagnostic',
              'reason', 'Verify system health before critical period',
              'payload', jsonb_build_object('equipment_id', v_equipment_id),
              'urgency', 'high'
            )
          );
        END IF;
      ELSIF v_situation->>'type' = 'HIGH_RISK_EQUIPMENT' THEN
        v_recommendations := jsonb_build_array(
          jsonb_build_object(
            'action', 'schedule_inspection',
            'label', 'Schedule Inspection',
            'reason', 'Proactive inspection before potential failure',
            'payload', jsonb_build_object(
              'equipment_id', v_equipment_id,
              'equipment_label', v_equipment_label
            ),
            'urgency', CASE WHEN v_severity = 'high' THEN 'elevated' ELSE 'normal' END
          )
        );
      END IF;
    END IF;
  END IF;

  -- ============================================
  -- 5. RUN GRAPHRAG SEARCH (unified_search_v2)
  -- ============================================

  SELECT result INTO v_cards
  FROM public.unified_search_v2(
    p_query_text,
    p_embedding,
    p_yacht_id,
    p_intent,
    p_match_count
  ) AS result;

  -- Extract just the cards array if it's wrapped
  IF v_cards ? 'cards' THEN
    v_cards := v_cards->'cards';
  END IF;

  -- ============================================
  -- 6. BUILD FINAL RESPONSE
  -- ============================================

  RETURN jsonb_build_object(
    'situation', v_situation,
    'risk', CASE WHEN v_situation IS NOT NULL THEN
      jsonb_build_object(
        'if_ignored', v_severity,
        'if_acted', 'low',
        'confidence', 'approximate'
      )
    ELSE NULL END,
    'recommended_actions', v_recommendations,
    'disambiguation', v_disambiguation,
    'cards', COALESCE(v_cards, '[]'::JSONB),
    'meta', jsonb_build_object(
      'yacht_id', p_yacht_id,
      'user_role', p_user_role,
      'query', p_query_text,
      'intent', p_intent,
      'resolved_entities', jsonb_build_array(v_resolved_entities),
      'vessel_context', v_vessel_context
    )
  );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION public.situational_search IS 'One fat function: resolves entities, detects situation, builds recommendations, runs GraphRAG - returns complete agent response';

GRANT EXECUTE ON FUNCTION public.situational_search TO authenticated, service_role;

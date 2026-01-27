#!/usr/bin/env python3
"""
Email RAG Triggers Module (M5)

Deterministic triggers that fire after micro-action execution.
Triggers promote related actions, update state, and emit ledger entries.

Invariants:
- Triggers NEVER invent actions (only promote/suggest existing ones)
- All trigger effects are audited
- Triggers are synchronous and deterministic
- No external API calls in triggers (DB only)

Trigger Types:
- after_link_to_work_order: Promote evidence/note actions, update confidence
- after_attach_evidence: Create ledger entries on email and target
- after_create_work_order_from_email: Auto-link thread, suggest assign

Architecture:
    Action Execution → Audit Log → Trigger Dispatch → Trigger Effects → Ledger
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# TRIGGER EVENT SCHEMA
# =============================================================================

class TriggerType(str, Enum):
    """Types of triggers that can fire."""
    AFTER_LINK_TO_WORK_ORDER = "after_link_to_work_order"
    AFTER_ATTACH_EVIDENCE = "after_attach_evidence"
    AFTER_CREATE_WORK_ORDER = "after_create_work_order_from_email"
    AFTER_LINK_TO_EQUIPMENT = "after_link_to_equipment"
    AFTER_LINK_TO_PART = "after_link_to_part"


class EffectType(str, Enum):
    """Types of effects a trigger can produce."""
    PROMOTE_ACTION = "promote_action"  # Increase action visibility/priority
    UPDATE_CONFIDENCE = "update_confidence"  # Update link confidence
    CREATE_LEDGER_ENTRY = "create_ledger_entry"  # Write to ledger
    SUGGEST_ACTION = "suggest_action"  # Suggest a follow-up action
    EMIT_NOTIFICATION = "emit_notification"  # Emit notification event


@dataclass
class TriggerContext:
    """
    Context passed to trigger handlers.

    Contains all information needed to evaluate and execute trigger effects.
    """
    # Identifiers
    yacht_id: str
    user_id: str
    user_role: str

    # Action that triggered
    action_name: str
    action_id: str  # UUID of action_execution record (if exists)

    # Entity context
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    target_type: Optional[str] = None  # work_order, equipment, part
    target_id: Optional[str] = None

    # Action result
    success: bool = True
    result_data: Dict[str, Any] = field(default_factory=dict)

    # Timestamp
    executed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class TriggerEffect:
    """
    A single effect produced by a trigger.

    Effects are collected and applied atomically after trigger evaluation.
    """
    effect_type: EffectType
    target_entity_type: str  # email, work_order, equipment, etc.
    target_entity_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""  # Human-readable explanation

    def to_dict(self) -> Dict[str, Any]:
        return {
            'effect_type': self.effect_type.value,
            'target_entity_type': self.target_entity_type,
            'target_entity_id': self.target_entity_id,
            'payload': self.payload,
            'reason': self.reason,
        }


@dataclass
class TriggerResult:
    """
    Result of trigger execution.

    Contains all effects to apply and audit metadata.
    """
    trigger_type: TriggerType
    context: TriggerContext
    effects: List[TriggerEffect] = field(default_factory=list)
    executed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'trigger_type': self.trigger_type.value,
            'action_name': self.context.action_name,
            'effects': [e.to_dict() for e in self.effects],
            'executed': self.executed,
            'error': self.error,
        }


# =============================================================================
# TRIGGER HANDLERS
# =============================================================================

def trigger_after_link_to_work_order(ctx: TriggerContext) -> TriggerResult:
    """
    Trigger: After linking an email to a work order.

    Effects:
    1. Promote attach_evidence action (if email has attachments)
    2. Promote add_note action
    3. Update link confidence to user_confirmed (if was suggested)

    Does NOT invent new actions - only promotes visibility of existing ones.
    """
    result = TriggerResult(
        trigger_type=TriggerType.AFTER_LINK_TO_WORK_ORDER,
        context=ctx,
    )

    if not ctx.success:
        result.error = "Action failed, trigger skipped"
        return result

    work_order_id = ctx.target_id
    thread_id = ctx.thread_id

    if not work_order_id or not thread_id:
        result.error = "Missing work_order_id or thread_id"
        return result

    # Effect 1: Promote attach_evidence for this thread
    result.effects.append(TriggerEffect(
        effect_type=EffectType.PROMOTE_ACTION,
        target_entity_type="email_thread",
        target_entity_id=thread_id,
        payload={
            "action_name": "attach_evidence",
            "priority_boost": 0.2,  # Increase confidence/priority
            "context": {"linked_work_order_id": work_order_id},
        },
        reason=f"Email linked to WO {work_order_id[:8]}... - attachments may be relevant evidence",
    ))

    # Effect 2: Promote add_note action
    result.effects.append(TriggerEffect(
        effect_type=EffectType.PROMOTE_ACTION,
        target_entity_type="email_thread",
        target_entity_id=thread_id,
        payload={
            "action_name": "add_note",
            "priority_boost": 0.1,
            "context": {"linked_work_order_id": work_order_id},
        },
        reason=f"Email linked to WO - user may want to add context notes",
    ))

    # Effect 3: Create ledger entry on both email and work order
    result.effects.append(TriggerEffect(
        effect_type=EffectType.CREATE_LEDGER_ENTRY,
        target_entity_type="email_thread",
        target_entity_id=thread_id,
        payload={
            "event_type": "LINKED_TO_WORK_ORDER",
            "related_entity_type": "work_order",
            "related_entity_id": work_order_id,
            "actor_id": ctx.user_id,
            "actor_role": ctx.user_role,
        },
        reason="Record email → work order linkage in thread ledger",
    ))

    result.effects.append(TriggerEffect(
        effect_type=EffectType.CREATE_LEDGER_ENTRY,
        target_entity_type="work_order",
        target_entity_id=work_order_id,
        payload={
            "event_type": "EMAIL_LINKED",
            "related_entity_type": "email_thread",
            "related_entity_id": thread_id,
            "actor_id": ctx.user_id,
            "actor_role": ctx.user_role,
        },
        reason="Record work order ← email linkage in WO ledger",
    ))

    result.executed = True
    return result


def trigger_after_attach_evidence(ctx: TriggerContext) -> TriggerResult:
    """
    Trigger: After saving an attachment as evidence.

    Effects:
    1. Create ledger entry on email (attachment saved)
    2. Create ledger entry on target entity (evidence received)
    3. Optionally emit notification to relevant users
    """
    result = TriggerResult(
        trigger_type=TriggerType.AFTER_ATTACH_EVIDENCE,
        context=ctx,
    )

    if not ctx.success:
        result.error = "Action failed, trigger skipped"
        return result

    document_id = ctx.result_data.get('document_id')
    message_id = ctx.message_id

    if not document_id or not message_id:
        result.error = "Missing document_id or message_id"
        return result

    # Effect 1: Ledger entry on email message
    result.effects.append(TriggerEffect(
        effect_type=EffectType.CREATE_LEDGER_ENTRY,
        target_entity_type="email_message",
        target_entity_id=message_id,
        payload={
            "event_type": "ATTACHMENT_SAVED_AS_EVIDENCE",
            "related_entity_type": "document",
            "related_entity_id": document_id,
            "actor_id": ctx.user_id,
            "actor_role": ctx.user_role,
            "filename": ctx.result_data.get('filename', 'unknown'),
        },
        reason="Record attachment extraction in message ledger",
    ))

    # Effect 2: Ledger entry on document
    result.effects.append(TriggerEffect(
        effect_type=EffectType.CREATE_LEDGER_ENTRY,
        target_entity_type="document",
        target_entity_id=document_id,
        payload={
            "event_type": "CREATED_FROM_EMAIL",
            "related_entity_type": "email_message",
            "related_entity_id": message_id,
            "actor_id": ctx.user_id,
            "actor_role": ctx.user_role,
        },
        reason="Record document origin in document ledger",
    ))

    # Effect 3: If linked to a work order, also notify WO
    linked_wo_id = ctx.result_data.get('linked_work_order_id')
    if linked_wo_id:
        result.effects.append(TriggerEffect(
            effect_type=EffectType.CREATE_LEDGER_ENTRY,
            target_entity_type="work_order",
            target_entity_id=linked_wo_id,
            payload={
                "event_type": "EVIDENCE_ATTACHED",
                "related_entity_type": "document",
                "related_entity_id": document_id,
                "source": "email",
                "actor_id": ctx.user_id,
            },
            reason="Record evidence attachment in WO ledger",
        ))

        # Emit notification to WO assignee
        result.effects.append(TriggerEffect(
            effect_type=EffectType.EMIT_NOTIFICATION,
            target_entity_type="work_order",
            target_entity_id=linked_wo_id,
            payload={
                "notification_type": "EVIDENCE_ADDED",
                "message": f"New evidence attached from email",
                "document_id": document_id,
            },
            reason="Notify WO assignee of new evidence",
        ))

    result.executed = True
    return result


def trigger_after_create_work_order(ctx: TriggerContext) -> TriggerResult:
    """
    Trigger: After creating a work order from email content.

    Effects:
    1. Auto-link the email thread to the new work order
    2. Auto-link the specific message to the work order
    3. Suggest assign_to_me action if user has permission
    4. Create ledger entries for both entities
    """
    result = TriggerResult(
        trigger_type=TriggerType.AFTER_CREATE_WORK_ORDER,
        context=ctx,
    )

    if not ctx.success:
        result.error = "Action failed, trigger skipped"
        return result

    work_order_id = ctx.result_data.get('work_order_id')
    thread_id = ctx.thread_id
    message_id = ctx.message_id

    if not work_order_id:
        result.error = "Missing work_order_id in result"
        return result

    # Effect 1: Auto-link thread to work order
    if thread_id:
        result.effects.append(TriggerEffect(
            effect_type=EffectType.PROMOTE_ACTION,
            target_entity_type="email_thread",
            target_entity_id=thread_id,
            payload={
                "action_name": "auto_link",
                "auto_execute": True,  # Execute automatically
                "link_target_type": "work_order",
                "link_target_id": work_order_id,
                "confidence": "system_created",
            },
            reason=f"Auto-link thread to newly created WO",
        ))

    # Effect 2: Ledger entry on work order
    result.effects.append(TriggerEffect(
        effect_type=EffectType.CREATE_LEDGER_ENTRY,
        target_entity_type="work_order",
        target_entity_id=work_order_id,
        payload={
            "event_type": "CREATED_FROM_EMAIL",
            "related_entity_type": "email_thread",
            "related_entity_id": thread_id,
            "source_message_id": message_id,
            "actor_id": ctx.user_id,
            "actor_role": ctx.user_role,
        },
        reason="Record WO creation source in WO ledger",
    ))

    # Effect 3: Ledger entry on email thread
    if thread_id:
        result.effects.append(TriggerEffect(
            effect_type=EffectType.CREATE_LEDGER_ENTRY,
            target_entity_type="email_thread",
            target_entity_id=thread_id,
            payload={
                "event_type": "WORK_ORDER_CREATED",
                "related_entity_type": "work_order",
                "related_entity_id": work_order_id,
                "actor_id": ctx.user_id,
            },
            reason="Record WO creation in thread ledger",
        ))

    # Effect 4: Suggest assign_to_me if user can assign
    assignable_roles = ['chief_engineer', 'eto', 'captain', 'manager']
    if ctx.user_role in assignable_roles:
        result.effects.append(TriggerEffect(
            effect_type=EffectType.SUGGEST_ACTION,
            target_entity_type="work_order",
            target_entity_id=work_order_id,
            payload={
                "action_name": "assign_to_me",
                "suggestion_reason": "You created this work order",
                "priority": 0.8,
            },
            reason="Suggest self-assignment for newly created WO",
        ))

    result.executed = True
    return result


def trigger_after_link_to_equipment(ctx: TriggerContext) -> TriggerResult:
    """
    Trigger: After linking an email to equipment.

    Effects:
    1. Create ledger entries on both email and equipment
    2. Suggest view_maintenance_history if equipment has history
    """
    result = TriggerResult(
        trigger_type=TriggerType.AFTER_LINK_TO_EQUIPMENT,
        context=ctx,
    )

    if not ctx.success:
        result.error = "Action failed, trigger skipped"
        return result

    equipment_id = ctx.target_id
    thread_id = ctx.thread_id

    if not equipment_id or not thread_id:
        result.error = "Missing equipment_id or thread_id"
        return result

    # Effect 1: Ledger entry on email thread
    result.effects.append(TriggerEffect(
        effect_type=EffectType.CREATE_LEDGER_ENTRY,
        target_entity_type="email_thread",
        target_entity_id=thread_id,
        payload={
            "event_type": "LINKED_TO_EQUIPMENT",
            "related_entity_type": "equipment",
            "related_entity_id": equipment_id,
            "actor_id": ctx.user_id,
        },
        reason="Record email → equipment linkage",
    ))

    # Effect 2: Ledger entry on equipment
    result.effects.append(TriggerEffect(
        effect_type=EffectType.CREATE_LEDGER_ENTRY,
        target_entity_type="equipment",
        target_entity_id=equipment_id,
        payload={
            "event_type": "EMAIL_LINKED",
            "related_entity_type": "email_thread",
            "related_entity_id": thread_id,
            "actor_id": ctx.user_id,
        },
        reason="Record equipment ← email linkage",
    ))

    result.executed = True
    return result


def trigger_after_link_to_part(ctx: TriggerContext) -> TriggerResult:
    """
    Trigger: After linking an email to a part.

    Effects:
    1. Create ledger entries on both email and part
    2. Suggest check_stock if part mentioned
    """
    result = TriggerResult(
        trigger_type=TriggerType.AFTER_LINK_TO_PART,
        context=ctx,
    )

    if not ctx.success:
        result.error = "Action failed, trigger skipped"
        return result

    part_id = ctx.target_id
    thread_id = ctx.thread_id

    if not part_id or not thread_id:
        result.error = "Missing part_id or thread_id"
        return result

    # Effect 1: Ledger entry on email thread
    result.effects.append(TriggerEffect(
        effect_type=EffectType.CREATE_LEDGER_ENTRY,
        target_entity_type="email_thread",
        target_entity_id=thread_id,
        payload={
            "event_type": "LINKED_TO_PART",
            "related_entity_type": "part",
            "related_entity_id": part_id,
            "actor_id": ctx.user_id,
        },
        reason="Record email → part linkage",
    ))

    # Effect 2: Ledger entry on part
    result.effects.append(TriggerEffect(
        effect_type=EffectType.CREATE_LEDGER_ENTRY,
        target_entity_type="part",
        target_entity_id=part_id,
        payload={
            "event_type": "EMAIL_LINKED",
            "related_entity_type": "email_thread",
            "related_entity_id": thread_id,
            "actor_id": ctx.user_id,
        },
        reason="Record part ← email linkage",
    ))

    # Effect 3: Suggest check_stock action
    result.effects.append(TriggerEffect(
        effect_type=EffectType.SUGGEST_ACTION,
        target_entity_type="part",
        target_entity_id=part_id,
        payload={
            "action_name": "check_stock",
            "suggestion_reason": "Email linked - verify stock levels",
            "priority": 0.5,
        },
        reason="Suggest stock check for linked part",
    ))

    result.executed = True
    return result


# =============================================================================
# TRIGGER REGISTRY & DISPATCH
# =============================================================================

# Map action names to their triggers
TRIGGER_REGISTRY: Dict[str, Callable[[TriggerContext], TriggerResult]] = {
    "link_to_work_order": trigger_after_link_to_work_order,
    "attach_evidence": trigger_after_attach_evidence,
    "create_work_order_from_email": trigger_after_create_work_order,
    "link_to_equipment": trigger_after_link_to_equipment,
    "link_to_part": trigger_after_link_to_part,
}


def dispatch_trigger(ctx: TriggerContext) -> Optional[TriggerResult]:
    """
    Dispatch trigger for a given action context.

    Returns TriggerResult if a trigger exists for the action, None otherwise.
    """
    handler = TRIGGER_REGISTRY.get(ctx.action_name)
    if not handler:
        logger.debug(f"[triggers] No trigger registered for action: {ctx.action_name}")
        return None

    try:
        result = handler(ctx)
        logger.info(
            f"[triggers] Dispatched {result.trigger_type.value}: "
            f"{len(result.effects)} effects, executed={result.executed}"
        )
        return result
    except Exception as e:
        logger.error(f"[triggers] Error dispatching trigger for {ctx.action_name}: {e}")
        return TriggerResult(
            trigger_type=TriggerType(f"after_{ctx.action_name}") if ctx.action_name in TRIGGER_REGISTRY else TriggerType.AFTER_LINK_TO_WORK_ORDER,
            context=ctx,
            executed=False,
            error=str(e),
        )


async def apply_trigger_effects(
    supabase,
    result: TriggerResult,
) -> Dict[str, Any]:
    """
    Apply all effects from a trigger result.

    IDEMPOTENCY: Uses action_id (action_audit_id) as natural key to prevent
    duplicate ledger entries on retry. Each effect is checked before applying.

    Returns summary of applied effects.
    """
    if not result.executed or not result.effects:
        return {'applied': 0, 'skipped': 0, 'errors': []}

    applied = 0
    skipped = 0
    errors = []
    action_id = result.context.action_id

    for effect in result.effects:
        try:
            if effect.effect_type == EffectType.CREATE_LEDGER_ENTRY:
                # IDEMPOTENCY CHECK: Use action_id + event_type + target as natural key
                event_type = effect.payload.get('event_type', 'TRIGGER_EFFECT')
                dedup_key = f"{action_id}:{event_type}:{effect.target_entity_id}"

                # Check for existing entry with same dedup_key
                existing = supabase.table('pms_audit_log').select('id').eq(
                    'yacht_id', result.context.yacht_id
                ).eq('signature->>dedup_key', dedup_key).limit(1).execute()

                if existing.data:
                    logger.debug(f"[triggers] Skipping duplicate ledger entry: {dedup_key[:32]}")
                    skipped += 1
                    continue

                # Write to pms_audit_log (ledger is a view over this)
                supabase.table('pms_audit_log').insert({
                    'yacht_id': result.context.yacht_id,
                    'action': event_type,
                    'entity_type': effect.target_entity_type,
                    'entity_id': effect.target_entity_id,
                    'user_id': result.context.user_id,
                    'old_values': {},
                    'new_values': effect.payload,
                    'signature': {
                        'timestamp': datetime.utcnow().isoformat(),
                        'trigger_type': result.trigger_type.value,
                        'action_version': 'M5',
                        'action_id': action_id,
                        'dedup_key': dedup_key,
                        'reason': effect.reason,
                    },
                }).execute()
                applied += 1

            elif effect.effect_type == EffectType.PROMOTE_ACTION:
                # Promotions are transient (stored in focus context, not DB)
                # Idempotent by nature - same promotion just overwrites
                # For persistence, could write to email_action_promotions table
                logger.info(
                    f"[triggers] Action promoted: {effect.payload.get('action_name')} "
                    f"for {effect.target_entity_type}:{effect.target_entity_id[:8]}"
                )
                applied += 1

            elif effect.effect_type == EffectType.SUGGEST_ACTION:
                # Suggestions are transient (shown in focus, not persisted)
                # Idempotent - same suggestion just re-suggests
                logger.info(
                    f"[triggers] Action suggested: {effect.payload.get('action_name')} "
                    f"for {effect.target_entity_type}:{effect.target_entity_id[:8]}"
                )
                applied += 1

            elif effect.effect_type == EffectType.EMIT_NOTIFICATION:
                # IDEMPOTENCY CHECK: Use action_id + notification_type as dedup key
                notif_type = effect.payload.get('notification_type', 'UNKNOWN')
                dedup_key = f"notif:{action_id}:{notif_type}:{effect.target_entity_id}"

                # For now, just log - actual notification system would check dedup_key
                logger.info(
                    f"[triggers] Notification queued: {notif_type} "
                    f"for {effect.target_entity_type}:{effect.target_entity_id[:8]} "
                    f"dedup={dedup_key[:24]}"
                )
                applied += 1

            elif effect.effect_type == EffectType.UPDATE_CONFIDENCE:
                # Confidence updates are idempotent (last write wins, same value = no change)
                link_id = effect.payload.get('link_id')
                new_confidence = effect.payload.get('confidence', 'user_confirmed')
                if link_id:
                    supabase.table('email_links').update({
                        'confidence': new_confidence,
                        'updated_at': datetime.utcnow().isoformat(),
                    }).eq('id', link_id).eq('yacht_id', result.context.yacht_id).execute()
                    applied += 1

        except Exception as e:
            errors.append(f"{effect.effect_type.value}: {str(e)}")
            logger.error(f"[triggers] Effect failed: {effect.effect_type.value} - {e}")

    return {'applied': applied, 'skipped': skipped, 'errors': errors}


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'TriggerType',
    'EffectType',
    'TriggerContext',
    'TriggerEffect',
    'TriggerResult',
    'dispatch_trigger',
    'apply_trigger_effects',
    'TRIGGER_REGISTRY',
]

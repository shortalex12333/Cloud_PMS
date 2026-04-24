// apps/web/src/types/actions.ts
//
// DISPLAY METADATA ONLY — Phase 3
//
// The backend (Phase 2) now returns available_actions on every entity GET endpoint.
// Backend provides: action_id, label, variant, disabled, disabled_reason,
//                   requires_signature, prefill, required_fields, optional_fields.
// Frontend role filtering (canPerformAction, role_restricted) has been removed.
// This file owns only: icon (rendering concern) and cluster (placement: shell bar vs inline).

export type ActionCluster =
  | 'lifecycle'
  | 'entity'
  | 'notes'
  | 'inventory'
  | 'documents'
  | 'maintenance'
  | 'compliance';

export const ACTION_DISPLAY: Record<string, { icon: string; cluster: ActionCluster }> = {
  // Work Order — lifecycle (shell action bar)
  start_work_order:               { icon: 'play',          cluster: 'lifecycle'    },
  close_work_order:               { icon: 'check',         cluster: 'lifecycle'    },
  cancel_work_order:              { icon: 'x',             cluster: 'lifecycle'    },
  reopen_work_order:              { icon: 'rotate-ccw',    cluster: 'lifecycle'    },
  // Work Order — entity (shell action bar)
  archive_work_order:             { icon: 'archive',       cluster: 'entity'       },
  reassign_work_order:            { icon: 'user',          cluster: 'entity'       },
  update_work_order:              { icon: 'edit',          cluster: 'entity'       },
  // Work Order — inline content
  // Canonical long-form action_ids (matches registry + entity_prefill).
  // Short aliases kept for backward-compat with in-flight callers.
  add_work_order_note:            { icon: 'message',       cluster: 'notes'        },
  add_note_to_work_order:         { icon: 'message',       cluster: 'notes'        },
  add_wo_note:                    { icon: 'message',       cluster: 'notes'        },
  add_parts_to_work_order:        { icon: 'package',       cluster: 'inventory'    },
  add_wo_part:                    { icon: 'package',       cluster: 'inventory'    },
  add_work_order_hours:           { icon: 'clock',         cluster: 'notes'        },
  add_wo_hours:                   { icon: 'clock',         cluster: 'notes'        },
  add_work_order_photo:           { icon: 'camera',        cluster: 'notes'        },
  add_wo_photo:                   { icon: 'camera',        cluster: 'notes'        },
  assign_work_order:              { icon: 'user',          cluster: 'entity'       },
  view_checklist:                 { icon: 'list',          cluster: 'compliance'   },
  add_checklist_note:             { icon: 'message',       cluster: 'compliance'   },
  add_checklist_photo:            { icon: 'camera',        cluster: 'compliance'   },
  mark_checklist_item_complete:   { icon: 'check',         cluster: 'compliance'   },
  update_worklist_progress:       { icon: 'activity',      cluster: 'lifecycle'    },
  add_to_handover:                { icon: 'clipboard',     cluster: 'entity'       },
  // Fault — lifecycle
  close_fault:                    { icon: 'check',         cluster: 'lifecycle'    },
  reopen_fault:                   { icon: 'rotate-ccw',   cluster: 'lifecycle'    },
  acknowledge_fault:              { icon: 'check-circle',  cluster: 'lifecycle'    },
  mark_fault_false_alarm:         { icon: 'x-circle',     cluster: 'lifecycle'    },
  // Fault — entity / inline
  report_fault:                   { icon: 'alert',         cluster: 'entity'       },
  create_work_order_from_fault:   { icon: 'clipboard',     cluster: 'entity'       },
  update_fault:                   { icon: 'edit',          cluster: 'entity'       },
  add_fault_note:                 { icon: 'message',       cluster: 'notes'        },
  add_fault_photo:                { icon: 'camera',        cluster: 'notes'        },
  // Equipment — lifecycle
  decommission_equipment:         { icon: 'trash',         cluster: 'lifecycle'    },
  // Equipment — entity / inline
  update_equipment_status:        { icon: 'edit',          cluster: 'entity'       },
  flag_equipment_attention:       { icon: 'flag',          cluster: 'entity'       },
  add_equipment_note:             { icon: 'message',       cluster: 'notes'        },
  create_work_order_for_equipment:{ icon: 'clipboard',     cluster: 'entity'       },
  // Parts / Inventory — lifecycle
  write_off_part:                 { icon: 'trash',         cluster: 'lifecycle'    },
  // Parts — inline
  log_part_usage:                 { icon: 'minus',         cluster: 'inventory'    },
  transfer_part:                  { icon: 'arrow-right',   cluster: 'inventory'    },
  adjust_stock_quantity:          { icon: 'edit',          cluster: 'inventory'    },
  add_to_shopping_list:           { icon: 'shopping-cart', cluster: 'inventory'    },
  // Receiving — lifecycle
  accept_receiving:               { icon: 'check',         cluster: 'lifecycle'    },
  reject_receiving:               { icon: 'x',             cluster: 'lifecycle'    },
  // Receiving — inline
  add_receiving_item:             { icon: 'plus',          cluster: 'inventory'    },
  update_receiving:               { icon: 'edit',          cluster: 'entity'       },
  // Certificate
  update_certificate:             { icon: 'edit',          cluster: 'entity'       },
  // Hours of rest — legacy action IDs removed (view/update/export_hours_of_rest).
  // Migrate to Crew Lens v3 (get_hours_of_rest / upsert_hours_of_rest).
  // Documents
  view_document:                  { icon: 'file',          cluster: 'documents'    },
  // Handover
  export_handover:                { icon: 'download',      cluster: 'entity'       },
  edit_handover_section:          { icon: 'edit',          cluster: 'notes'        },
};

/**
 * Returns display metadata with a safe fallback for unknown action IDs.
 * Unknown actions (new backend actions not yet added here) get a generic icon
 * and land in the shell action bar until someone adds the display entry.
 */
export function getActionDisplay(actionId: string): { icon: string; cluster: ActionCluster } {
  return ACTION_DISPLAY[actionId] ?? { icon: 'circle', cluster: 'entity' };
}

from handlers.equipment_handlers import HANDLERS


def test_all_actions_registered():
    expected = {
        # READ
        "view_equipment",
        "view_equipment_details",
        "view_equipment_history",
        "view_maintenance_history",
        "view_equipment_parts",
        "view_linked_faults",
        "view_equipment_manual",
        # MUTATION
        "update_equipment_status",
        "set_equipment_status",
        "add_equipment_note",
        "attach_file_to_equipment",
        "create_work_order_for_equipment",
        "link_part_to_equipment",
        "flag_equipment_attention",
        "decommission_equipment",
        "record_equipment_hours",
        "create_equipment",
        "assign_parent_equipment",
        "archive_equipment",
        "restore_archived_equipment",
        "get_open_faults_for_equipment",
        "get_related_entities_for_equipment",
        "add_entity_link",
        "link_document_to_equipment",
        "attach_image_with_comment",
        "decommission_and_replace_equipment",
        "suggest_parts",
    }
    assert set(HANDLERS.keys()) == expected


def test_set_equipment_status_is_alias():
    assert HANDLERS["set_equipment_status"] is HANDLERS["update_equipment_status"]

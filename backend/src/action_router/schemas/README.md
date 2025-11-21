# Action Router JSON Schemas

This directory contains JSON schemas for validating action payloads.

## Schema Files

Each action can optionally have a schema file defined in the action registry. The schema validator will validate the action payload against this schema before execution.

## Schema Format

Schemas follow JSON Schema Draft 7 specification: https://json-schema.org/draft-07/schema

## Example Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "note_text": {
      "type": "string",
      "minLength": 1,
      "maxLength": 5000,
      "description": "The text content of the note"
    },
    "priority": {
      "type": "string",
      "enum": ["low", "medium", "high", "critical"],
      "description": "Priority level"
    }
  },
  "required": ["note_text"],
  "additionalProperties": false
}
```

## Schema Files to Create

Based on the action registry, the following schema files should be created:

- [x] `add_note.json`
- [ ] `add_note_to_work_order.json`
- [ ] `create_work_order.json`
- [ ] `create_work_order_fault.json`
- [ ] `close_work_order.json`
- [ ] `add_to_handover.json`
- [ ] `add_document_to_handover.json`
- [ ] `add_part_to_handover.json`
- [ ] `add_predictive_to_handover.json`
- [ ] `edit_handover_section.json`
- [ ] `export_handover.json`
- [ ] `open_document.json`
- [ ] `order_part.json`

## Validation Behavior

- If `schema_file` is specified in action registry but file doesn't exist: validation is skipped with warning
- If `schema_file` is not specified: schema validation is skipped
- If schema validation fails: action execution is blocked with 400 error

## Dependencies

The schema validator requires the `jsonschema` Python package:

```bash
pip install jsonschema
```

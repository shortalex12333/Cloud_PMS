## 1. Conceptual rules (lock these)

Before the schema, these are **non-negotiable invariants**:

1. Every action has **one canonical ID** (never renamed)
2. Every action is either `READ` or `MUTATE` (no third state)
3. UI never invents actions — registry is the source of truth
4. Dropdown logic is data-driven, not hardcoded
5. Security, signing, logging are *declared*, not inferred

---

## 2. Minimal schema (JSON)

```json
{
  "action_id": "string",                 
  "label": "string",                     
  "variant": "READ | MUTATE",             

  "domain": "inventory | maintenance | manuals | hor | people | system",

  "ui": {
    "primary": true,                     
    "dropdown_only": false,              
    "row_level": true,                   
    "global_level": false                
  },

  "execution": {
    "handler": "string",                 
    "supports_inline": true              
  },

  "mutation": {
    "requires_signature": false,         
    "signature_type": "none | faceid | passcode | typed",
    "preview_diff": false,               
    "undoable": false                    
  },

  "audit": {
    "level": "none | standard | critical"
  }
}
```

That’s it.
No opinions. No explanations. No magic.

---

## 3. READ action example (inventory)

```json
{
  "action_id": "view_inventory_item",
  "label": "View",
  "variant": "READ",

  "domain": "inventory",

  "ui": {
    "primary": true,
    "dropdown_only": false,
    "row_level": true,
    "global_level": false
  },

  "execution": {
    "handler": "read_handlers.view_inventory_item",
    "supports_inline": true
  },

  "mutation": {
    "requires_signature": false,
    "signature_type": "none",
    "preview_diff": false,
    "undoable": false
  },

  "audit": {
    "level": "none"
  }
}
```

No signature.
No diff.
No ceremony.

---

## 4. MUTATE action example (edit inventory)

```json
{
  "action_id": "edit_inventory_quantity",
  "label": "Edit",
  "variant": "MUTATE",

  "domain": "inventory",

  "ui": {
    "primary": false,
    "dropdown_only": true,
    "row_level": true,
    "global_level": false
  },

  "execution": {
    "handler": "mutate_handlers.update_inventory",
    "supports_inline": true
  },

  "mutation": {
    "requires_signature": true,
    "signature_type": "faceid",
    "preview_diff": true,
    "undoable": false
  },

  "audit": {
    "level": "critical"
  }
}
```

This guarantees:

* never auto-executes
* never appears unless user opens dropdown
* always signed
* always logged

---

## 5. Why this schema is *deliberately small*

What’s **intentionally missing**:

* no “why”
* no intent confidence
* no entity requirements
* no permissions
* no UX copy
* no ranking hints

Those belong in:

* gating
* attachment
* execution
* renderer
* logs

If you put them here, this file will rot.

---

## 6. How this drives your UX rules automatically

With just this schema, the frontend can already know:

* Should I show this as a button or hide behind ▼?
* Can this mutate state?
* Do I need to block execution until signed?
* Should I show a diff preview?
* Do I need to log aggressively?

No extra conditionals.

---

## 7. Validation rules you should enforce at load time

When loading the registry, **fail fast** if:

* `variant = MUTATE` and `requires_signature = false`
* `primary = true` and `variant = MUTATE`
* `dropdown_only = true` and `primary = true`
* `audit.level = none` on MUTATE
* duplicate `action_id`

These are *logic bugs*, not runtime errors.

---

## 8. This schema scales cleanly later

You can later add (without breaking anything):

* `rate_limit`
* `allowed_roles`
* `allowed_domains`
* `bulk_supported`
* `feature_flag`

But MVP does **not** need them.

---

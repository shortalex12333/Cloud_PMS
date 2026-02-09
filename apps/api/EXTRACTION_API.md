# Extraction Layer API Contract

## 1. Overview

This document defines the official API contract for the output of the Extraction Layer. All components within the `extraction/` directory must adhere to this contract. The `orchestration/` layer will consume this data structure.

The primary principle is to provide a rich, unfiltered list of potential signals (entities) from the user's query. The Extraction Layer's job is to generate signals, not to interpret or filter them.

## 2. Data Structure

The Extraction Layer must output a JSON object containing a single key: `entities`.

```json
{
  "entities": [
    // ... list of Entity objects
  ]
}
```

### 2.1. The `Entity` Object

The `entities` key contains a flat list of `Entity` objects. Each `Entity` object represents a single, detected signal in the source text and has the following structure:

| Field        | Type                 | Required | Description                                                                                                                              |
|--------------|----------------------|----------|------------------------------------------------------------------------------------------------------------------------------------------|
| `text`       | `string`             | Yes      | The exact text of the extracted entity from the original query.                                                                          |
| `type`       | `string`             | Yes      | The type of the entity (e.g., `part_number`, `brand`, `location`, `measurement`).                                                          |
| `span`       | `Tuple[int, int]`    | Yes      | A tuple representing the start and end character indices of the entity in the original, normalized query text.                           |
| `confidence` | `float`              | Yes      | A score from 0.0 to 1.0 indicating the extractor's confidence in the accuracy of the extraction. Should be based on source, not context. |
| `source`     | `string`             | Yes      | The origin of the extraction (e.g., `regex`, `gazetteer`, `fuzzy`, `ai`).                                                                  |
| `negated`    | `boolean`            | No       | `true` if the entity is preceded by a negation term (e.g., "not", "without"). Defaults to `false`.                                       |
| `qualifier`  | `string`             | No       | For measurements, a descriptor of the value (e.g., `above`, `below`, `limit`, `setpoint`).                                                |
| `metadata`   | `Dict[string, any]`  | No       | An open dictionary for additional, source-specific information (e.g., `{ "original_term": "Caterpiller" }` for a fuzzy match).            |

### 2.2. Example `Entity` Objects

**A simple brand extraction:**
```json
{
  "text": "Caterpillar",
  "type": "org",
  "span": [32, 43],
  "confidence": 0.8,
  "source": "gazetteer"
}
```

**A negated equipment extraction:**
```json
{
  "text": "pump",
  "type": "equipment",
  "span": [12, 16],
  "confidence": 0.9,
  "source": "regex",
  "negated": true
}
```

**A qualified measurement extraction:**
```json
{
  "text": "90°C",
  "type": "measurement",
  "span": [25, 29],
  "confidence": 0.99,
  "source": "regex",
  "qualifier": "above"
}
```

## 3. Guiding Principles for Implementers

*   **No Filtering:** The `entities` list should include all entities found, even if they have low confidence or their spans overlap. The `orchestration` layer is responsible for resolving these ambiguities.
*   **Richness over Precision:** It is better to provide a slightly noisy but rich set of signals than a "clean" but incomplete one. The downstream `PrepareModule` is designed to handle this richness.
*   **Consistent Confidence Scores:** Confidence scores should be based on the extraction method, not on the context of the query. For example:
    *   `regex`: 0.9 (High confidence in pattern match)
    *   `gazetteer`: 0.8 (High confidence in dictionary match)
    *   `fuzzy`: 0.7 (Lower confidence due to fuzzy matching)
    *   `ai`: Varies based on the model's own confidence score.
*   **Complete Span Information:** The `span` is critical for the `orchestration` layer to understand the relationships between entities. It must be accurate.

This API contract is the single source of truth for the data format passed between the `extraction` and `orchestration` layers. All future changes to the extraction process must conform to this contract.

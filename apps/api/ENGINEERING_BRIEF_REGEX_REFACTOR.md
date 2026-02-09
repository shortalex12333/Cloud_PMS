# Engineering Brief: Refactoring `RegexExtractor` for Signal Purity

## 1. Objective

This document outlines the architectural refactoring required for `extraction/regex_extractor.py`. The primary goal is to transform the `RegexExtractor` from a hybrid extraction-and-interpretation engine into a **pure signal generator**. It should identify all potential entities and their attributes (negation, qualifiers, etc.) without making any assumptions about their relative importance or the user's ultimate intent.

## 2. Guiding Principles

*   **Extraction is Not Interpretation:** The `RegexExtractor`'s sole responsibility is to find potential signals in the text. It should not try to guess which signal is the "right" one.
*   **No More "Magic" Ordering:** The concept of a `PRECEDENCE_ORDER` will be deprecated. The ranking and fusion of entities will be handled downstream by the `PrepareModule` (`execute/result_ranker.py`).
*   **All Signals are Potentially Valuable:** The extractor should return all possible entities it finds, even if they overlap. The `PrepareModule` will decide how to handle these overlaps.
*   **Preserve Signal Richness:** Attributes like negation, qualifiers, and fuzzy matching are valuable parts of the signal and should be preserved and enhanced.

## 3. Specific Architectural Changes

### 3.1. To Be Removed

*   **`PRECEDENCE_ORDER`:** This entire list must be removed. The order of pattern application should not imply importance.
*   **`CONTEXT_PATTERNS`:** This dictionary and its associated logic should be removed. Confidence boosting based on context is a form of interpretation that belongs in the `PrepareModule`.
*   **Special Priority Logic in `extract()`:** The special handling for `doc_priority_types` and the ordered application of patterns must be removed. All patterns should be applied, and all matches returned.
*   **Span Overlap Prevention:** The logic that prevents overlapping spans (`is_overlapping` checks) should be removed. If "CAT" is a brand and "CAT-123" is a part number, both should be extracted. The `PrepareModule` will use the spans to understand the relationship between these entities.

### 3.2. To Be Kept & Enhanced

*   **All Regex Patterns:** The patterns themselves are valuable and should be kept.
*   **Gazetteer Loading:** The logic for loading the gazetteer (`_load_gazetteer`) is correct and should be maintained.
*   **Negation & Qualifiers:** The detection of negation (`NEGATION_PATTERNS`) and qualifiers (`QUALIFIER_PATTERNS`) is a critical part of the signal and must be preserved.
*   **Fuzzy Matching:** The fuzzy matching for brands (`_fuzzy_brand_extract`) is an important feature for improving recall and should be kept.
*   **Normalization:** The Unicode normalization (`_normalize_unicode`) and measurement normalization (`_normalize_measurement`) are essential for consistent output.

### 3.3. To Be Modified

*   **`extract()` Method:** This method should be simplified significantly. It should iterate through all patterns, find all matches, and create `Entity` objects for them. It should not contain any special ordering or filtering logic.
*   **`Entity` Class:** The `confidence` attribute of the `Entity` class should be re-evaluated. Since we are removing the contextual confidence boosting, we may want to assign a default confidence based on the source (e.g., `regex: 0.9`, `gazetteer: 0.8`, `fuzzy: 0.7`). This will be a simple, consistent signal for the `PrepareModule`.

## 4. New API Contract: The `RegexExtractor` Output

The `extract` method will now return a single, flat list of `Entity` objects. It will be the responsibility of the caller (the `orchestration` layer) to process this list.

**Example:**

For the input text: "Show me the CAT-123 part from Caterpillar."

The **old** extractor, with its precedence rules, might only return:
```
[Entity(text='CAT-123', type='part_number', ...)]
```

The **new** extractor will return:
```
[
  Entity(text='CAT-123', type='part_number', span=(15, 22), ...),
  Entity(text='Caterpillar', type='org', span=(32, 43), source='gazetteer', ...),
  // Note: Depending on the patterns, it might also extract "CAT" as a brand.
  Entity(text='CAT', type='org', span=(15, 18), source='gazetteer', ...)
]
```
The `PrepareModule` will then use the spans and types to understand that "CAT-123" is a part number, "Caterpillar" is an organization, and that the text "CAT" is part of the part number *and* a potential brand mention. This is a much richer signal for the downstream layers to work with.

This refactoring is the first and most critical step in our transition to the new Fan-Out/Fan-In architecture. It will provide a clean, stable foundation for the subsequent phases of the project.

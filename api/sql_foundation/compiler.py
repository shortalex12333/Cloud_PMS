"""
SQL FOUNDATION — PROBE COMPILER
================================
Maps: entity → variants → columns → operator → universal template

This is the ONLY place where probes are constructed.
No ad-hoc SQL generation allowed anywhere else.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .operators import Operator, OPERATOR_WAVES
from .probe import Probe, Variant, VariantType, WhereClause, Conjunction, probe_single, probe_or_multicolumn, probe_and_conjunction
from .column_config import TABLES, get_columns_for_entity, get_table

@dataclass
class Entity:
    """Extracted entity with strength classification."""
    type: str
    raw_value: str
    variants: List[Variant]
    strength: str  # "strong", "medium", "weak"

    @staticmethod
    def classify_strength(entity_type: str) -> str:
        """Classify entity strength for gating."""
        strong = {"PART_NUMBER", "EQUIPMENT_CODE", "SERIAL_NUMBER", "FAULT_CODE", "PO_NUMBER"}
        medium = {"EQUIPMENT_NAME", "PART_NAME", "SUPPLIER_NAME", "LOCATION"}
        # Everything else is weak

        if entity_type in strong:
            return "strong"
        elif entity_type in medium:
            return "medium"
        else:
            return "weak"

class ProbeCompiler:
    """
    Compiles entities into executable Probes.

    Rules enforced:
    1. yacht_id ALWAYS first filter
    2. Variants tried in priority order
    3. conjunction_only columns require anchor entity
    4. Operators match column capability
    """

    def __init__(self, yacht_id: str):
        self.yacht_id = yacht_id

    def compile_single_entity(self, entity: Entity) -> List[Probe]:
        """
        Compile probes for a single entity.
        Returns probes grouped by wave.
        """
        probes = []
        columns = get_columns_for_entity(entity.type)

        if not columns:
            return []

        for table_name, col_name, operators, isolated_ok, conjunction_only in columns:
            # Skip conjunction_only columns for single entity
            if conjunction_only:
                continue

            if not isolated_ok:
                continue

            table = get_table(table_name)
            if not table:
                continue

            # For each operator, try variants in priority order
            for op in operators:
                # Match variant type to operator
                variant = self._get_variant_for_operator(entity.variants, op)
                if not variant:
                    continue

                probe = probe_single(
                    table=table_name,
                    column=col_name,
                    operator=op,
                    term=variant.value,
                    yacht_id=self.yacht_id,
                    select_cols=table.default_select,
                    entity_type=entity.type,
                    variant_type=variant.type,
                    limit=table.default_limit
                )
                probes.append(probe)

        return probes

    def compile_or_multicolumn(self, entity: Entity, table_name: str) -> Optional[Probe]:
        """
        Compile OR probe for same entity across multiple columns in one table.
        Shape B: (name ILIKE ...) OR (part_number = ...)
        """
        table = get_table(table_name)
        if not table:
            return None

        # Find all columns that support this entity type
        matching_cols = []
        for col_name, col in table.columns.items():
            if entity.type in col.entity_types and col.isolated_ok:
                matching_cols.append(col_name)

        if len(matching_cols) < 2:
            return None  # Need multiple columns for OR

        # Use ILIKE as common operator for OR
        variant = self._get_variant_for_operator(entity.variants, Operator.ILIKE)
        if not variant:
            return None

        return probe_or_multicolumn(
            table=table_name,
            columns=matching_cols,
            operator=Operator.ILIKE,
            term=variant.value,
            yacht_id=self.yacht_id,
            select_cols=table.default_select,
            entity_type=entity.type,
            limit=table.default_limit
        )

    def compile_conjunction(self, entities: List[Entity], table_name: str) -> Optional[Probe]:
        """
        Compile AND probe for multiple entities.
        Shape C: name ILIKE '%fuel filter%' AND location = 'Engine Room'

        RULE: Only runs when 2+ entities, at least one strong/medium.
        """
        if len(entities) < 2:
            return None

        # Check entity strength
        strengths = [e.strength for e in entities]
        if "strong" not in strengths and "medium" not in strengths:
            return None  # All weak = no conjunction

        table = get_table(table_name)
        if not table:
            return None

        # Build column-term pairs
        column_terms = []
        for entity in entities:
            # Find first matching column for this entity
            for col_name, col in table.columns.items():
                if entity.type in col.entity_types:
                    # Get best operator for this column
                    op = col.operators[0]  # First operator = highest priority
                    variant = self._get_variant_for_operator(entity.variants, op)
                    if variant:
                        column_terms.append((col_name, op, variant.value))
                        break

        if len(column_terms) < 2:
            return None

        return probe_and_conjunction(
            table=table_name,
            column_terms=column_terms,
            yacht_id=self.yacht_id,
            select_cols=table.default_select,
            limit=table.default_limit
        )

    def compile_search(self, entities: List[Entity]) -> Dict[int, List[Probe]]:
        """
        Main entry point: compile all probes for a search.

        Returns probes grouped by wave number.
        """
        probes_by_wave: Dict[int, List[Probe]] = {0: [], 1: [], 2: [], 3: []}

        # Gate 1: Entity sufficiency check
        strengths = [e.strength for e in entities]
        has_strong = "strong" in strengths
        has_medium = "medium" in strengths

        if not has_strong and not has_medium:
            # All weak entities - limited search
            # Only search primary columns, wave 1 max
            for entity in entities:
                probes = self._compile_limited_weak(entity)
                for p in probes:
                    if p.wave <= 1:
                        probes_by_wave[p.wave].append(p)
            return probes_by_wave

        # Full search for strong/medium entities
        for entity in entities:
            probes = self.compile_single_entity(entity)
            for p in probes:
                probes_by_wave[p.wave].append(p)

        # Try conjunctions if multiple entities
        if len(entities) >= 2:
            for table_name in TABLES:
                conj_probe = self.compile_conjunction(entities, table_name)
                if conj_probe:
                    probes_by_wave[conj_probe.wave].append(conj_probe)

        return probes_by_wave

    def _get_variant_for_operator(self, variants: List[Variant], operator: Operator) -> Optional[Variant]:
        """Get appropriate variant for operator type."""
        if operator == Operator.EXACT:
            # Prefer canonical/normalized for exact
            for v in variants:
                if v.type in (VariantType.CANONICAL, VariantType.NORMALIZED):
                    return v
            return variants[0] if variants else None

        elif operator in (Operator.ILIKE, Operator.ARRAY_ANY_ILIKE, Operator.JSONB_PATH_ILIKE):
            # Prefer fuzzy (pattern-wrapped) for ILIKE
            for v in variants:
                if v.type == VariantType.FUZZY:
                    return v
            # Fallback: wrap raw
            if variants:
                return Variant(VariantType.FUZZY, f"%{variants[0].value}%", priority=4)
            return None

        elif operator == Operator.TRIGRAM:
            # Use normalized for trigram
            for v in variants:
                if v.type == VariantType.NORMALIZED:
                    return v
            return variants[0] if variants else None

        else:
            return variants[0] if variants else None

    def _compile_limited_weak(self, entity: Entity) -> List[Probe]:
        """Limited search for weak entities - only primary text columns."""
        probes = []
        columns = get_columns_for_entity(entity.type)

        for table_name, col_name, operators, isolated_ok, conjunction_only in columns:
            if conjunction_only:
                continue
            if not isolated_ok:
                continue

            # Only ILIKE for weak entities
            if Operator.ILIKE in operators:
                table = get_table(table_name)
                if not table:
                    continue

                variant = self._get_variant_for_operator(entity.variants, Operator.ILIKE)
                if variant:
                    probe = probe_single(
                        table=table_name,
                        column=col_name,
                        operator=Operator.ILIKE,
                        term=variant.value,
                        yacht_id=self.yacht_id,
                        select_cols=table.default_select,
                        entity_type=entity.type,
                        variant_type=variant.type,
                        limit=table.default_limit
                    )
                    probes.append(probe)

        return probes


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_entity(entity_type: str, raw_value: str) -> Entity:
    """Create entity with auto-generated variants."""
    return Entity(
        type=entity_type,
        raw_value=raw_value,
        variants=Variant.from_raw(raw_value),
        strength=Entity.classify_strength(entity_type)
    )

def compile_probes(yacht_id: str, entities: List[Dict]) -> Dict[int, List[Probe]]:
    """
    Main API: compile probes from extracted entities.

    entities: [{"type": "PART_NUMBER", "value": "ENG-0008-103"}, ...]
    """
    compiler = ProbeCompiler(yacht_id)

    entity_objects = [
        create_entity(e["type"], e["value"])
        for e in entities
    ]

    return compiler.compile_search(entity_objects)

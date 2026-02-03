#!/usr/bin/env python3
"""
COMPREHENSIVE GROUND TRUTH TEST SUITE
=====================================

Auto-generated from 598-query corpus.
Tests extraction accuracy against manually-inferred expected entities.

Usage:
    python -m pytest tests/test_comprehensive_accuracy.py -v
"""

import os
import sys
import pytest
import asyncio
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ExpectedEntity:
    type: str
    value: Optional[str] = None
    required: bool = True


@dataclass
class GroundTruthCase:
    id: str
    query: str
    lens: str
    description: str
    expected_entities: List[ExpectedEntity]
    forbidden_entities: List[str] = field(default_factory=list)
    expected_capability: Optional[str] = None
    min_results: int = 0


# =============================================================================
# GROUND TRUTH TEST CASES (Auto-generated)
# =============================================================================

GROUND_TRUTH: List[GroundTruthCase] = [
    GroundTruthCase(
        id="parts_001",
        query='Racor',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_002",
        query='Volvo Penta',
        lens="parts",
        description="Expects: brand 'volvo'",
        expected_entities=[
            ExpectedEntity(type="brand", value='volvo', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_004",
        query='Racor fuel filters',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_005",
        query='Racor or Caterpillar',
        lens="parts",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_006",
        query='RACOR',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_008",
        query='Northern Lights',
        lens="parts",
        description="Expects: brand 'northern lights'",
        expected_entities=[
            ExpectedEntity(type="brand", value='northern lights', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_009",
        query='MTU',
        lens="parts",
        description="Expects: brand 'mtu'",
        expected_entities=[
            ExpectedEntity(type="brand", value='mtu', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_010",
        query='Wartsila',
        lens="parts",
        description="Expects: brand 'wartsila'",
        expected_entities=[
            ExpectedEntity(type="brand", value='wartsila', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_013",
        query='Racor ABC-123',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_016",
        query='I need part number ABC-123 for the engine',
        lens="parts",
        description="Expects: equipment 'engine'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_025",
        query='racor',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_026",
        query='RaCoR',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_030",
        query='Volvo  Penta',
        lens="parts",
        description="Expects: brand 'volvo'",
        expected_entities=[
            ExpectedEntity(type="brand", value='volvo', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_031",
        query='Racor fuel filter',
        lens="parts",
        description="Expects: brand 'racor', equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_032",
        query='Caterpillar 12345',
        lens="parts",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_033",
        query='Racor ABC-123 fuel filter',
        lens="parts",
        description="Expects: brand 'racor', equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_034",
        query='Racor not Caterpillar',
        lens="parts",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_035",
        query='Racor to Yanmar',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_036",
        query='5 Racor filters',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_037",
        query='Racor and Caterpillar parts',
        lens="parts",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_038",
        query='Caterpillar 3516 parts',
        lens="parts",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_039",
        query='Racor 12V filters',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_040",
        query='Racor in engine room',
        lens="parts",
        description="Expects: brand 'racor', equipment 'engine', location 'engine room'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_041",
        query='Do we have any Racor parts?',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_042",
        query='What parts do we have from Caterpillar?',
        lens="parts",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_043",
        query='Can you please show me Racor filters?',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_044",
        query='URGENT: Need Racor filter ASAP',
        lens="parts",
        description="Expects: brand 'racor', equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_045",
        query='Hey so I was thinking we might need some parts maybe Racor or something for the engine',
        lens="parts",
        description="Expects: brand 'racor', equipment 'engine'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='engine', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_047",
        query='Racor, filter, urgently',
        lens="parts",
        description="Expects: brand 'racor', equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_048",
        query='Need part Racor filter urgently no more',
        lens="parts",
        description="Expects: brand 'racor', equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_049",
        query='Racor filtro de combustible',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_050",
        query='Racor 🔧 filters',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_051",
        query='Racor parts added this week',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_052",
        query='Parts from Caterpillar last month',
        lens="parts",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_053",
        query='Racor parts needed next week',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_054",
        query='Caterpillar parts between Jan 1 and Jan 15',
        lens="parts",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_055",
        query='Racor parts from 3 days ago',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_063",
        query='Racor Caterpillar filter',
        lens="parts",
        description="Expects: brand 'caterpillar', equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_064",
        query='Racor ABC-123 if exists',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_065",
        query='Cat parts',
        lens="parts",
        description="Expects: brand 'cat'",
        expected_entities=[
            ExpectedEntity(type="brand", value='cat', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_066",
        query='12 volt Racor',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_068",
        query='Volvo',
        lens="parts",
        description="Expects: brand 'volvo'",
        expected_entities=[
            ExpectedEntity(type="brand", value='volvo', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_069",
        query='Parts not from Racor',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_071",
        query='Racor that is not Racor',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_072",
        query='Racor filter and its parts',
        lens="parts",
        description="Expects: brand 'racor', equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_073",
        query='I need to find parts from Racor specifically the fuel filter models that are compatible with the main engine in the engine room and I need them urgently because we are running low on inventory and the captain has requested that we restock immediately',
        lens="parts",
        description="Expects: brand 'racor', equipment 'engine', part 'filter', location 'engine room'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="part", value='filter', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_078",
        query='<script>Racor</script>',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_081",
        query='Parts from https://racor.com',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_083",
        query='Racor Caterpillar MTU Yanmar Volvo Kohler ABC-123 DEF-456 filter pump valve gasket',
        lens="parts",
        description="Expects: brand 'volvo', equipment 'filter', part 'gasket'",
        expected_entities=[
            ExpectedEntity(type="brand", value='volvo', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='gasket', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_084",
        query='Racor Racor Racor',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_085",
        query='Racor RACOR racor RaCoR',
        lens="parts",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_086",
        query='filter',
        lens="parts",
        description="Expects: equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_089",
        query='Racor filter',
        lens="parts",
        description="Expects: brand 'racor', equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="parts_090",
        query='Racor                    filter',
        lens="parts",
        description="Expects: brand 'racor', equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_001",
        query='pending shopping list items',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_002",
        query='shopping list items',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_003",
        query='shopping list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_004",
        query='order list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_005",
        query='buy list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_007",
        query='parts request',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_009",
        query='purchase list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_012",
        query='requisition',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_013",
        query='supply request',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_015",
        query='inventory request',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_016",
        query='show shopping list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_017",
        query='view shopping list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_018",
        query='get shopping list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_019",
        query='display shopping list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_020",
        query='find shopping list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_021",
        query='pending',
        lens="shopping_list",
        description="Expects: approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_022",
        query='approved',
        lens="shopping_list",
        description="Expects: approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_023",
        query='rejected',
        lens="shopping_list",
        description="Expects: approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_024",
        query='draft',
        lens="shopping_list",
        description="Expects: approval 'draft'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='draft', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_025",
        query='under review',
        lens="shopping_list",
        description="Expects: approval 'under review'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='under review', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_030",
        query='submitted',
        lens="shopping_list",
        description="Expects: approval 'submitted'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='submitted', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_031",
        query='pending orders',
        lens="shopping_list",
        description="Expects: approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_032",
        query='approved orders',
        lens="shopping_list",
        description="Expects: approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_033",
        query='rejected orders',
        lens="shopping_list",
        description="Expects: approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_034",
        query='show pending',
        lens="shopping_list",
        description="Expects: approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_035",
        query='view approved',
        lens="shopping_list",
        description="Expects: approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_036",
        query='get rejected',
        lens="shopping_list",
        description="Expects: approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_037",
        query='find draft',
        lens="shopping_list",
        description="Expects: approval 'draft'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='draft', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_038",
        query='list pending',
        lens="shopping_list",
        description="Expects: approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_039",
        query='show all approved',
        lens="shopping_list",
        description="Expects: approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_040",
        query='display rejected',
        lens="shopping_list",
        description="Expects: approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_042",
        query='approved shopping list items',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_043",
        query='rejected shopping list items',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_044",
        query='draft shopping list items',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'draft'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='draft', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_045",
        query='pending shopping list orders',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_046",
        query='approved shopping list orders',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_047",
        query='rejected shopping list orders',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_048",
        query='pending parts list',
        lens="shopping_list",
        description="Expects: approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_049",
        query='approved parts list',
        lens="shopping_list",
        description="Expects: approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_050",
        query='rejected parts list',
        lens="shopping_list",
        description="Expects: approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_051",
        query='pending order list',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_052",
        query='approved order list',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_053",
        query='rejected order list',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_054",
        query='pending procurement list',
        lens="shopping_list",
        description="Expects: approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_055",
        query='approved procurement list',
        lens="shopping_list",
        description="Expects: approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_056",
        query='show pending shopping list',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_057",
        query='view approved shopping list',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_058",
        query='get rejected shopping list',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_059",
        query='find pending parts request',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_060",
        query='display approved requisition',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_061",
        query='show me pending shopping list items',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_062",
        query='can you show pending shopping list',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_063",
        query='I need to see approved shopping list',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_064",
        query="what's on the shopping list",
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_065",
        query='show all pending items',
        lens="shopping_list",
        description="Expects: approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_066",
        query='give me the shopping list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_067",
        query='where is my shopping list',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_068",
        query='show pending orders',
        lens="shopping_list",
        description="Expects: approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_069",
        query='display approved items',
        lens="shopping_list",
        description="Expects: approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_070",
        query='list all rejected',
        lens="shopping_list",
        description="Expects: approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_071",
        query='Racor shopping list',
        lens="shopping_list",
        description="Expects: brand 'racor', shopping list term",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_072",
        query='Caterpillar shopping list items',
        lens="shopping_list",
        description="Expects: brand 'caterpillar', shopping list term",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_073",
        query='MTU parts list',
        lens="shopping_list",
        description="Expects: brand 'mtu'",
        expected_entities=[
            ExpectedEntity(type="brand", value='mtu', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_074",
        query='Cummins order list',
        lens="shopping_list",
        description="Expects: brand 'cummins', shopping list term",
        expected_entities=[
            ExpectedEntity(type="brand", value='cummins', required=True),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_075",
        query='pending Racor shopping list',
        lens="shopping_list",
        description="Expects: brand 'racor', shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_076",
        query='approved Caterpillar parts list',
        lens="shopping_list",
        description="Expects: brand 'caterpillar', approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True),
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_077",
        query='rejected MTU procurement list',
        lens="shopping_list",
        description="Expects: brand 'mtu', approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="brand", value='mtu', required=True),
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_078",
        query='Racor pending shopping list',
        lens="shopping_list",
        description="Expects: brand 'racor', shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_079",
        query='show Caterpillar shopping list',
        lens="shopping_list",
        description="Expects: brand 'caterpillar', shopping list term",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_080",
        query='find MTU parts request',
        lens="shopping_list",
        description="Expects: brand 'mtu', shopping list term",
        expected_entities=[
            ExpectedEntity(type="brand", value='mtu', required=True),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_081",
        query='oil filter shopping list',
        lens="shopping_list",
        description="Expects: equipment 'filter', part 'filter', shopping list term",
        expected_entities=[
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_082",
        query='impeller parts list',
        lens="shopping_list",
        description="Expects: part 'impeller'",
        expected_entities=[
            ExpectedEntity(type="part", value='impeller', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_083",
        query='membrane shopping list items',
        lens="shopping_list",
        description="Expects: part 'membrane', shopping list term",
        expected_entities=[
            ExpectedEntity(type="part", value='membrane', required=False),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_084",
        query='gasket order list',
        lens="shopping_list",
        description="Expects: part 'gasket', shopping list term",
        expected_entities=[
            ExpectedEntity(type="part", value='gasket', required=False),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_085",
        query='pending oil filter shopping list',
        lens="shopping_list",
        description="Expects: equipment 'filter', part 'filter', shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False),
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_086",
        query='approved impeller parts list',
        lens="shopping_list",
        description="Expects: part 'impeller', approval 'approved'",
        expected_entities=[
            ExpectedEntity(type="part", value='impeller', required=False),
            ExpectedEntity(type="approval_status", value='approved', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_087",
        query='rejected membrane procurement list',
        lens="shopping_list",
        description="Expects: part 'membrane', approval 'rejected'",
        expected_entities=[
            ExpectedEntity(type="part", value='membrane', required=False),
            ExpectedEntity(type="approval_status", value='rejected', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_088",
        query='show oil filter shopping list',
        lens="shopping_list",
        description="Expects: equipment 'filter', part 'filter', shopping list term",
        expected_entities=[
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_089",
        query='find impeller parts request',
        lens="shopping_list",
        description="Expects: part 'impeller', shopping list term",
        expected_entities=[
            ExpectedEntity(type="part", value='impeller', required=False),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_090",
        query='display membrane order list',
        lens="shopping_list",
        description="Expects: part 'membrane', shopping list term",
        expected_entities=[
            ExpectedEntity(type="part", value='membrane', required=False),
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_091",
        query='PENDING SHOPPING LIST ITEMS',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_092",
        query='Pending Shopping List Items',
        lens="shopping_list",
        description="Expects: shopping list term, approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True),
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_093",
        query='pending shoping list items',
        lens="shopping_list",
        description="Expects: approval 'pending'",
        expected_entities=[
            ExpectedEntity(type="approval_status", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_097",
        query='things to buy',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_098",
        query='purchase requisition',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="shopping_list_099",
        query='shopping list for yacht',
        lens="shopping_list",
        description="Expects: shopping list term",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_005",
        query='active warnings',
        lens="crew",
        description="Expects: status 'active'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='active', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_006",
        query='active alerts',
        lens="crew",
        description="Expects: status 'active'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='active', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_007",
        query='acknowledged warnings',
        lens="crew",
        description="Expects: status 'acknowledged'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='acknowledged', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_008",
        query='dismissed warnings',
        lens="crew",
        description="Expects: status 'dismissed'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='dismissed', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_010",
        query='pending alerts',
        lens="crew",
        description="Expects: status 'pending'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_011",
        query='compliant crew rest',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_012",
        query='non-compliant rest',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_013",
        query='rest violations',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_014",
        query='compliance violation',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_015",
        query='high severity active warnings',
        lens="crew",
        description="Expects: status 'active'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='active', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_018",
        query='insufficient rest',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_019",
        query='not enough rest',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_032",
        query='non complaint rest',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_036",
        query='active alrets',
        lens="crew",
        description="Expects: status 'active'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='active', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_039",
        query='active  warnings',
        lens="crew",
        description="Expects: status 'active'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='active', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_041",
        query='people not getting enough rest',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_051",
        query='high severity acknowledged warnings',
        lens="crew",
        description="Expects: status 'acknowledged'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='acknowledged', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_052",
        query='critical or high warnings',
        lens="crew",
        description="Expects: severity 'critical'",
        expected_entities=[
            ExpectedEntity(type="WARNING_SEVERITY", value='critical', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_053",
        query='active or pending warnings',
        lens="crew",
        description="Expects: status 'pending'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='pending', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_054",
        query='non-compliant crew with critical warnings',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_055",
        query='high severity active warnings for non-compliant crew',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_057",
        query='open to acknowledged warnings',
        lens="crew",
        description="Expects: status 'acknowledged'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='acknowledged', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_058",
        query='critical warnings and violations',
        lens="crew",
        description="Expects: severity 'critical'",
        expected_entities=[
            ExpectedEntity(type="WARNING_SEVERITY", value='critical', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_059",
        query='active warnings not dismissed',
        lens="crew",
        description="Expects: status 'dismissed'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='dismissed', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_066",
        query='critical critical warnings warnings',
        lens="crew",
        description="Expects: severity 'critical'",
        expected_entities=[
            ExpectedEntity(type="WARNING_SEVERITY", value='critical', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_069",
        query='show me all the critical warnings please',
        lens="crew",
        description="Expects: severity 'critical'",
        expected_entities=[
            ExpectedEntity(type="WARNING_SEVERITY", value='critical', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_071",
        query='bad rest',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_072",
        query='good compliance',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_076",
        query='MLC compliance',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_077",
        query='STCW rest requirements',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_082",
        query='engine department critical warnings',
        lens="crew",
        description="Expects: equipment 'engine', severity 'critical'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="WARNING_SEVERITY", value='critical', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_083",
        query='John Smith critical warnings',
        lens="crew",
        description="Expects: severity 'critical'",
        expected_entities=[
            ExpectedEntity(type="WARNING_SEVERITY", value='critical', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_084",
        query='deck crew active warnings this week',
        lens="crew",
        description="Expects: location 'deck', status 'active'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='deck', required=True),
            ExpectedEntity(type="WARNING_STATUS", value='active', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_085",
        query='watchkeeping crew non-compliant rest',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_087",
        query='chief engineer acknowledged warnings',
        lens="crew",
        description="Expects: status 'acknowledged'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='acknowledged', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_088",
        query='captain dismissed warnings',
        lens="crew",
        description="Expects: status 'dismissed'",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value='dismissed', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_090",
        query='rest complaince violations',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_091",
        query='high severity active warnings deck crew',
        lens="crew",
        description="Expects: location 'deck', status 'active'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='deck', required=True),
            ExpectedEntity(type="WARNING_STATUS", value='active', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="crew_092",
        query='non compliant crew rest records',
        lens="crew",
        description="Expects: rest compliance",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE", value=None, required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_001",
        query='port engine maintenance',
        lens="work_order",
        description="Expects: equipment 'engine', location 'port' (optional)",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='port', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_002",
        query='starboard generator oil change',
        lens="work_order",
        description="Expects: equipment 'generator', location 'starboard' (optional), action 'change'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='generator', required=False),
            ExpectedEntity(type="location_on_board", value='starboard', required=False),
            ExpectedEntity(type="action", value='change', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_003",
        query='main engine fuel filter replacement',
        lens="work_order",
        description="Expects: equipment 'engine', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_004",
        query='hydraulic pump repair in engine room',
        lens="work_order",
        description="Expects: equipment 'engine', part 'pump', location 'engine room', action 'repair'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="part", value='pump', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True),
            ExpectedEntity(type="action", value='repair', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_005",
        query='bow thruster service scheduled for tomorrow',
        lens="work_order",
        description="Expects: equipment 'thruster', location 'bow' (optional), action 'service'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='thruster', required=False),
            ExpectedEntity(type="location_on_board", value='bow', required=False),
            ExpectedEntity(type="action", value='service', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_006",
        query='check port side cooling pump pressure',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump', location 'port', action 'check'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False),
            ExpectedEntity(type="location_on_board", value='port', required=True),
            ExpectedEntity(type="action", value='check', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_007",
        query='replace starboard engine turbocharger',
        lens="work_order",
        description="Expects: equipment 'engine', location 'starboard' (optional), action 'replace'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='starboard', required=False),
            ExpectedEntity(type="action", value='replace', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_008",
        query='inspect fire suppression system valves',
        lens="work_order",
        description="Expects: action 'inspect'",
        expected_entities=[
            ExpectedEntity(type="action", value='inspect', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_009",
        query='emergency generator battery replacement',
        lens="work_order",
        description="Expects: equipment 'generator'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='generator', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_010",
        query='clean bilge pump strainer',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump', location 'bilge', action 'clean'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False),
            ExpectedEntity(type="location_on_board", value='bilge', required=True),
            ExpectedEntity(type="action", value='clean', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_011",
        query='calibrate navigation radar',
        lens="work_order",
        description="Expects: equipment 'radar', action 'calibrate'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='radar', required=False),
            ExpectedEntity(type="action", value='calibrate', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_012",
        query='troubleshoot air conditioning compressor noise',
        lens="work_order",
        description="Expects: equipment 'compressor', action 'troubleshoot'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='compressor', required=False),
            ExpectedEntity(type="action", value='troubleshoot', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_013",
        query='flush freshwater system with descaler',
        lens="work_order",
        description="Expects: action 'flush'",
        expected_entities=[
            ExpectedEntity(type="action", value='flush', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_014",
        query='test steering hydraulic pressure',
        lens="work_order",
        description="Expects: action 'test'",
        expected_entities=[
            ExpectedEntity(type="action", value='test', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_015",
        query='overhaul main engine cylinder head',
        lens="work_order",
        description="Expects: equipment 'engine', action 'overhaul'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="action", value='overhaul', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_018",
        query='adjust bow thruster control panel settings',
        lens="work_order",
        description="Expects: equipment 'thruster', location 'bow' (optional), action 'adjust'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='thruster', required=False),
            ExpectedEntity(type="location_on_board", value='bow', required=False),
            ExpectedEntity(type="action", value='adjust', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_019",
        query='lubricate windlass gearbox',
        lens="work_order",
        description="Expects: equipment 'windlass'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='windlass', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_020",
        query='investigate galley refrigerator cooling issue',
        lens="work_order",
        description="Expects: equipment 'refrigerator', location 'galley'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='refrigerator', required=False),
            ExpectedEntity(type="location_on_board", value='galley', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_021",
        query='port engine',
        lens="work_order",
        description="Expects: equipment 'engine', location 'port' (optional)",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='port', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_022",
        query='starboard generator',
        lens="work_order",
        description="Expects: equipment 'generator', location 'starboard' (optional)",
        expected_entities=[
            ExpectedEntity(type="equipment", value='generator', required=False),
            ExpectedEntity(type="location_on_board", value='starboard', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_023",
        query='main pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_024",
        query='backup compressor',
        lens="work_order",
        description="Expects: equipment 'compressor'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='compressor', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_025",
        query='auxiliary thruster',
        lens="work_order",
        description="Expects: equipment 'thruster'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='thruster', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_026",
        query='emergency fire pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_028",
        query='aft stabilizer fin',
        lens="work_order",
        description="Expects: location 'aft'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='aft', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_029",
        query='upper deck crane',
        lens="work_order",
        description="Expects: equipment 'crane', location 'deck'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='crane', required=False),
            ExpectedEntity(type="location_on_board", value='deck', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_030",
        query='engine room ventilation fan',
        lens="work_order",
        description="Expects: equipment 'engine', location 'engine room'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_031",
        query='port side bow thruster',
        lens="work_order",
        description="Expects: equipment 'thruster', location 'port' (optional)",
        expected_entities=[
            ExpectedEntity(type="equipment", value='thruster', required=False),
            ExpectedEntity(type="location_on_board", value='port', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_032",
        query='starboard engine cylinder liner',
        lens="work_order",
        description="Expects: equipment 'engine', part 'liner', location 'starboard' (optional)",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="part", value='liner', required=False),
            ExpectedEntity(type="location_on_board", value='starboard', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_033",
        query='main engine fuel injection pump',
        lens="work_order",
        description="Expects: equipment 'engine', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_034",
        query='primary cooling water pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_035",
        query='secondary hydraulic steering motor',
        lens="work_order",
        description="Expects: equipment 'motor'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='motor', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_044",
        query='work order 999 engine repair',
        lens="work_order",
        description="Expects: equipment 'engine', action 'repair'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="action", value='repair', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_047",
        query='oil chnge on port engin',
        lens="work_order",
        description="Expects: location 'port'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='port', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_048",
        query='recieving shipment for pump parst',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_053",
        query='bilge pum not working',
        lens="work_order",
        description="Expects: location 'bilge'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='bilge', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_054",
        query='starborad engine troubleshoot',
        lens="work_order",
        description="Expects: equipment 'engine', action 'troubleshoot'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="action", value='troubleshoot', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_056",
        query='enjine room fire pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_057",
        query='steerin gear adjust',
        lens="work_order",
        description="Expects: action 'adjust'",
        expected_entities=[
            ExpectedEntity(type="action", value='adjust', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_059",
        query='battry charger replacement',
        lens="work_order",
        description="Expects: equipment 'charger'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='charger', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_060",
        query='emergancy generator test',
        lens="work_order",
        description="Expects: equipment 'generator', action 'test'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='generator', required=False),
            ExpectedEntity(type="action", value='test', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_070",
        query='check that thing',
        lens="work_order",
        description="Expects: action 'check'",
        expected_entities=[
            ExpectedEntity(type="action", value='check', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_072",
        query='something in engine room',
        lens="work_order",
        description="Expects: equipment 'engine', location 'engine room'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_076",
        query='overhaul port engine',
        lens="work_order",
        description="Expects: equipment 'engine', location 'port' (optional), action 'overhaul'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='port', required=False),
            ExpectedEntity(type="action", value='overhaul', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_077",
        query='troubleshoot generator alarm',
        lens="work_order",
        description="Expects: equipment 'generator', action 'troubleshoot'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='generator', required=False),
            ExpectedEntity(type="action", value='troubleshoot', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_078",
        query='diagnose cooling system',
        lens="work_order",
        description="Expects: action 'diagnose'",
        expected_entities=[
            ExpectedEntity(type="action", value='diagnose', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_079",
        query='recondition fuel injection pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_080",
        query='rebuild gearbox',
        lens="work_order",
        description="Expects: equipment 'gearbox', action 'rebuild'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='gearbox', required=False),
            ExpectedEntity(type="action", value='rebuild', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_084",
        query='assess battery condition',
        lens="work_order",
        description="Expects: equipment 'battery'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='battery', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_085",
        query='monitor engine temperature',
        lens="work_order",
        description="Expects: equipment 'engine'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_086",
        query='show me that thing captain mentioned yesterday about starboard generator leak',
        lens="work_order",
        description="Expects: equipment 'generator', location 'starboard' (optional)",
        expected_entities=[
            ExpectedEntity(type="equipment", value='generator', required=False),
            ExpectedEntity(type="location_on_board", value='starboard', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_087",
        query='main engine starboard cylinder 3 injector replacement due to carbon buildup',
        lens="work_order",
        description="Expects: equipment 'engine', part 'injector', location 'starboard'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="part", value='injector', required=False),
            ExpectedEntity(type="location_on_board", value='starboard', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_088",
        query='port engine 1800 RPM vibration above 50Hz during acceleration',
        lens="work_order",
        description="Expects: equipment 'engine', location 'port' (optional)",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='port', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_089",
        query='hydraulic steering gear port side leak 3 bar pressure drop in 2 hours',
        lens="work_order",
        description="Expects: location 'port'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='port', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_090",
        query='emergency generator failed to start battery voltage 22V needs replacement',
        lens="work_order",
        description="Expects: equipment 'generator'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='generator', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_091",
        query='bilge pump float switch stuck causing automatic cycle every 5 minutes',
        lens="work_order",
        description="Expects: equipment 'switch', part 'pump', location 'bilge'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='switch', required=False),
            ExpectedEntity(type="part", value='pump', required=False),
            ExpectedEntity(type="location_on_board", value='bilge', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_092",
        query='main engine oil pressure fluctuating between 45-60 psi replace pressure sensor',
        lens="work_order",
        description="Expects: equipment 'engine', action 'replace'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="action", value='replace', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_094",
        query='fresh water maker produces cloudy water TDS reading 850 ppm membrane replacement needed',
        lens="work_order",
        description="Expects: part 'membrane'",
        expected_entities=[
            ExpectedEntity(type="part", value='membrane', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_095",
        query='HVAC starboard cabin not cooling compressor running but no cold air from vents',
        lens="work_order",
        description="Expects: equipment 'compressor', location 'starboard'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='compressor', required=False),
            ExpectedEntity(type="location_on_board", value='starboard', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_100",
        query='port starboard main backup emergency primary secondary auxiliary',
        lens="work_order",
        description="Expects: location 'starboard'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='starboard', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_100",
        query='oil change',
        lens="work_order",
        description="Expects: action 'change'",
        expected_entities=[
            ExpectedEntity(type="action", value='change', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_103",
        query='engine',
        lens="work_order",
        description="Expects: equipment 'engine'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_104",
        query='fuel filter',
        lens="work_order",
        description="Expects: equipment 'filter', part 'filter'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_106",
        query='hydraulic pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_107",
        query='repair',
        lens="work_order",
        description="Expects: action 'repair'",
        expected_entities=[
            ExpectedEntity(type="action", value='repair', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_108",
        query='engine room',
        lens="work_order",
        description="Expects: equipment 'engine', location 'engine room'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_109",
        query='bow thruster',
        lens="work_order",
        description="Expects: equipment 'thruster', location 'bow' (optional)",
        expected_entities=[
            ExpectedEntity(type="equipment", value='thruster', required=False),
            ExpectedEntity(type="location_on_board", value='bow', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_110",
        query='service',
        lens="work_order",
        description="Expects: action 'service'",
        expected_entities=[
            ExpectedEntity(type="action", value='service', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_112",
        query='check',
        lens="work_order",
        description="Expects: action 'check'",
        expected_entities=[
            ExpectedEntity(type="action", value='check', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_113",
        query='port',
        lens="work_order",
        description="Expects: location 'port'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='port', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_114",
        query='cooling pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_116",
        query='replace',
        lens="work_order",
        description="Expects: action 'replace'",
        expected_entities=[
            ExpectedEntity(type="action", value='replace', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_117",
        query='starboard',
        lens="work_order",
        description="Expects: location 'starboard'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='starboard', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_119",
        query='inspect',
        lens="work_order",
        description="Expects: action 'inspect'",
        expected_entities=[
            ExpectedEntity(type="action", value='inspect', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_123",
        query='generator',
        lens="work_order",
        description="Expects: equipment 'generator'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='generator', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_124",
        query='battery',
        lens="work_order",
        description="Expects: equipment 'battery'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='battery', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_125",
        query='clean',
        lens="work_order",
        description="Expects: action 'clean'",
        expected_entities=[
            ExpectedEntity(type="action", value='clean', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_126",
        query='bilge pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump', location 'bilge'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False),
            ExpectedEntity(type="location_on_board", value='bilge', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_128",
        query='calibrate',
        lens="work_order",
        description="Expects: action 'calibrate'",
        expected_entities=[
            ExpectedEntity(type="action", value='calibrate', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_129",
        query='navigation radar',
        lens="work_order",
        description="Expects: equipment 'radar'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='radar', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_130",
        query='troubleshoot',
        lens="work_order",
        description="Expects: action 'troubleshoot'",
        expected_entities=[
            ExpectedEntity(type="action", value='troubleshoot', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_131",
        query='air conditioning compressor',
        lens="work_order",
        description="Expects: equipment 'compressor'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='compressor', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_133",
        query='flush',
        lens="work_order",
        description="Expects: action 'flush'",
        expected_entities=[
            ExpectedEntity(type="action", value='flush', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_136",
        query='test',
        lens="work_order",
        description="Expects: action 'test'",
        expected_entities=[
            ExpectedEntity(type="action", value='test', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_139",
        query='overhaul',
        lens="work_order",
        description="Expects: action 'overhaul'",
        expected_entities=[
            ExpectedEntity(type="action", value='overhaul', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_140",
        query='cylinder head',
        lens="work_order",
        description="Expects: equipment 'head'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='head', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_149",
        query='adjust',
        lens="work_order",
        description="Expects: action 'adjust'",
        expected_entities=[
            ExpectedEntity(type="action", value='adjust', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_153",
        query='windlass',
        lens="work_order",
        description="Expects: equipment 'windlass'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='windlass', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_154",
        query='gearbox',
        lens="work_order",
        description="Expects: equipment 'gearbox'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='gearbox', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_156",
        query='galley',
        lens="work_order",
        description="Expects: location 'galley'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='galley', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_157",
        query='refrigerator',
        lens="work_order",
        description="Expects: equipment 'refrigerator'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='refrigerator', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_159",
        query='upper deck',
        lens="work_order",
        description="Expects: location 'deck'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='deck', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_160",
        query='crane',
        lens="work_order",
        description="Expects: equipment 'crane'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='crane', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_163",
        query='bow',
        lens="work_order",
        description="Expects: location 'bow'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='bow', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_164",
        query='thruster',
        lens="work_order",
        description="Expects: equipment 'thruster'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='thruster', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_165",
        query='cylinder liner',
        lens="work_order",
        description="Expects: part 'liner'",
        expected_entities=[
            ExpectedEntity(type="part", value='liner', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_167",
        query='pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_173",
        query='motor',
        lens="work_order",
        description="Expects: equipment 'motor'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='motor', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_190",
        query='compressor',
        lens="work_order",
        description="Expects: equipment 'compressor'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='compressor', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_195",
        query='fire pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_199",
        query='battery charger',
        lens="work_order",
        description="Expects: equipment 'charger'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='charger', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_209",
        query='diagnose',
        lens="work_order",
        description="Expects: action 'diagnose'",
        expected_entities=[
            ExpectedEntity(type="action", value='diagnose', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_211",
        query='fuel injection pump',
        lens="work_order",
        description="Expects: equipment 'pump', part 'pump'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_212",
        query='rebuild',
        lens="work_order",
        description="Expects: action 'rebuild'",
        expected_entities=[
            ExpectedEntity(type="action", value='rebuild', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_225",
        query='injector',
        lens="work_order",
        description="Expects: part 'injector'",
        expected_entities=[
            ExpectedEntity(type="part", value='injector', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_238",
        query='float switch',
        lens="work_order",
        description="Expects: equipment 'switch'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='switch', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_245",
        query='pressure sensor',
        lens="work_order",
        description="Expects: equipment 'sensor'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='sensor', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_255",
        query='membrane',
        lens="work_order",
        description="Expects: part 'membrane'",
        expected_entities=[
            ExpectedEntity(type="part", value='membrane', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="work_order_257",
        query='cabin',
        lens="work_order",
        description="Expects: location 'cabin'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='cabin', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_007",
        query='need too reorder',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_011",
        query='stok depleted',
        lens="inventory",
        description="Expects: stock_status 'depleted'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='depleted', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_021",
        query='insufficient stock',
        lens="inventory",
        description="Expects: stock_status 'insufficient'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='insufficient', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_022",
        query='supply shortage',
        lens="inventory",
        description="Expects: stock_status 'shortage'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='shortage', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_025",
        query='empty shelves',
        lens="inventory",
        description="Expects: stock_status 'empty'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='empty', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_026",
        query='empty',
        lens="inventory",
        description="Expects: stock_status 'empty'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='empty', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_028",
        query='inventory depleted',
        lens="inventory",
        description="Expects: stock_status 'depleted'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='depleted', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_033",
        query='stock alert',
        lens="inventory",
        description="Expects: stock_status 'stock alert'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='stock alert', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_035",
        query='reorder point reached',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_036",
        query='reorder point',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_039",
        query='low stock yesterday',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_040",
        query='low stock',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_042",
        query='out of stock last week',
        lens="inventory",
        description="Expects: stock_status 'out of stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='out of stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_043",
        query='out of stock',
        lens="inventory",
        description="Expects: stock_status 'out of stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='out of stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_048",
        query='reorder needed by Friday',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_049",
        query='reorder needed',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_051",
        query='inventory depleted this morning',
        lens="inventory",
        description="Expects: stock_status 'depleted'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='depleted', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_053",
        query='low stock for 3 days',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_057",
        query='urgent reorder',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_058",
        query='reorder',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_060",
        query='stock shortage next month',
        lens="inventory",
        description="Expects: stock_status 'shortage'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='shortage', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_061",
        query='stock shortage',
        lens="inventory",
        description="Expects: stock_status 'shortage'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='shortage', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_066",
        query='my low stock parts',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_067",
        query='low stock parts',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_068",
        query='low stock in my department',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_073",
        query='engine room stock',
        lens="inventory",
        description="Expects: equipment 'engine', location 'engine room'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_075",
        query='engine room',
        lens="inventory",
        description="Expects: equipment 'engine', location 'engine room'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_076",
        query='bridge supplies low',
        lens="inventory",
        description="Expects: location 'bridge'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='bridge', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_078",
        query='bridge',
        lens="inventory",
        description="Expects: location 'bridge'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='bridge', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_079",
        query='galley inventory',
        lens="inventory",
        description="Expects: location 'galley'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='galley', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_081",
        query='galley',
        lens="inventory",
        description="Expects: location 'galley'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='galley', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_082",
        query='all low stock items',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_083",
        query='low stock items',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_089",
        query='department reorder report',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_091",
        query='low stock in ER',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_092",
        query='inventory in engine room',
        lens="inventory",
        description="Expects: equipment 'engine', location 'engine room'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_095",
        query='aft deck supplies',
        lens="inventory",
        description="Expects: location 'deck'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='deck', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_096",
        query='aft deck',
        lens="inventory",
        description="Expects: location 'deck'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='deck', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_097",
        query='wheelhouse low stock',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_099",
        query='galley out of stock',
        lens="inventory",
        description="Expects: location 'galley', stock_status 'out of stock'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='galley', required=True),
            ExpectedEntity(type="stock_status", value='out of stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_103",
        query='lazarette inventory',
        lens="inventory",
        description="Expects: location 'lazarette'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='lazarette', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_104",
        query='lazarette',
        lens="inventory",
        description="Expects: location 'lazarette'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='lazarette', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_105",
        query='port side storage low',
        lens="inventory",
        description="Expects: location 'port'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='port', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_106",
        query='port side storage',
        lens="inventory",
        description="Expects: location 'port'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='port', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_107",
        query='starboard locker empty',
        lens="inventory",
        description="Expects: location 'starboard', stock_status 'empty'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='starboard', required=True),
            ExpectedEntity(type="stock_status", value='empty', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_108",
        query='starboard locker',
        lens="inventory",
        description="Expects: location 'starboard'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='starboard', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_118",
        query='low stock below 20',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_126",
        query='half empty stock',
        lens="inventory",
        description="Expects: stock_status 'empty'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='empty', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_128",
        query='low stock but adequate',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_130",
        query='out of stock available',
        lens="inventory",
        description="Expects: stock_status 'out of stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='out of stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_133",
        query='need reorder don',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_134",
        query='need reorder',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_138",
        query='reorder soon not urgent',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_139",
        query='reorder soon',
        lens="inventory",
        description="Expects: stock_status 'reorder'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='reorder', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_143",
        query='empty but full',
        lens="inventory",
        description="Expects: stock_status 'empty'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='empty', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_157",
        query='low stock filters in engine room yesterday',
        lens="inventory",
        description="Expects: equipment 'engine', location 'engine room', stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True),
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_158",
        query='critically low Racor filters need reorder by Friday in ER',
        lens="inventory",
        description="Expects: brand 'racor', stock_status 'critically low'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="stock_status", value='critically low', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_160",
        query='Racor',
        lens="inventory",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_161",
        query='galley out of stock items below 5 units urgent reorder',
        lens="inventory",
        description="Expects: location 'galley', stock_status 'out of stock'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='galley', required=True),
            ExpectedEntity(type="stock_status", value='out of stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_162",
        query='out of stock items',
        lens="inventory",
        description="Expects: stock_status 'out of stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='out of stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_164",
        query='my department low stock parts last week over 20 items',
        lens="inventory",
        description="Expects: stock_status 'low stock'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='low stock', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_166",
        query='bridge and galley inventory depleted restock needed today',
        lens="inventory",
        description="Expects: location 'bridge', stock_status 'depleted'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='bridge', required=True),
            ExpectedEntity(type="stock_status", value='depleted', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_168",
        query='Caterpillar parts running low port side 10 units reorder asap',
        lens="inventory",
        description="Expects: brand 'caterpillar', location 'port', stock_status 'running low'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True),
            ExpectedEntity(type="location_on_board", value='port', required=True),
            ExpectedEntity(type="stock_status", value='running low', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_169",
        query='Caterpillar',
        lens="inventory",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_170",
        query='running low',
        lens="inventory",
        description="Expects: stock_status 'running low'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='running low', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_171",
        query='port side',
        lens="inventory",
        description="Expects: location 'port'",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value='port', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_174",
        query='engine room and aft deck stock below minimum my team needs 50 by next Monday',
        lens="inventory",
        description="Expects: equipment 'engine', location 'engine room', stock_status 'below minimum'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="location_on_board", value='engine room', required=True),
            ExpectedEntity(type="stock_status", value='below minimum', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_175",
        query='below minimum',
        lens="inventory",
        description="Expects: stock_status 'below minimum'",
        expected_entities=[
            ExpectedEntity(type="stock_status", value='below minimum', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="inventory_180",
        query='Yanmar',
        lens="inventory",
        description="Expects: brand 'yanmar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='yanmar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="document_001",
        query='DNV-123456 certificate',
        lens="document",
        description="Expects: document_type 'certificate', class society 'dnv'",
        expected_entities=[
            ExpectedEntity(type="document_type", value='certificate', required=True),
            ExpectedEntity(type="document_id", value=None, required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="document_002",
        query='find DNV-123456 loadline certificate',
        lens="document",
        description="Expects: document_type 'certificate', class society 'dnv'",
        expected_entities=[
            ExpectedEntity(type="document_type", value='certificate', required=True),
            ExpectedEntity(type="document_id", value=None, required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="document_005",
        query='DNV-123456',
        lens="document",
        description="Expects: class society 'dnv'",
        expected_entities=[
            ExpectedEntity(type="document_id", value=None, required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="document_007",
        query='DNV class certificate',
        lens="document",
        description="Expects: document_type 'class certificate', class society 'dnv'",
        expected_entities=[
            ExpectedEntity(type="document_type", value='class certificate', required=True),
            ExpectedEntity(type="document_id", value=None, required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="document_008",
        query='DNV certificate',
        lens="document",
        description="Expects: document_type 'certificate', class society 'dnv'",
        expected_entities=[
            ExpectedEntity(type="document_type", value='certificate', required=True),
            ExpectedEntity(type="document_id", value=None, required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="document_009",
        query='dnv-123456',
        lens="document",
        description="Expects: class society 'dnv'",
        expected_entities=[
            ExpectedEntity(type="document_id", value=None, required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="document_022",
        query='DNV',
        lens="document",
        description="Expects: class society 'dnv'",
        expected_entities=[
            ExpectedEntity(type="document_id", value=None, required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="document_023",
        query='loadline',
        lens="document",
        description="Expects: document_type 'loadline'",
        expected_entities=[
            ExpectedEntity(type="document_type", value='loadline', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="document_027",
        query='DNV class',
        lens="document",
        description="Expects: class society 'dnv'",
        expected_entities=[
            ExpectedEntity(type="document_id", value=None, required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_1",
        query='Racor receiving',
        lens="receiving",
        description="Expects: brand 'racor', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_2",
        query='Caterpillar invoice',
        lens="receiving",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_3",
        query='MTU engine parts delivery',
        lens="receiving",
        description="Expects: brand 'mtu', equipment 'engine', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="brand", value='mtu', required=True),
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_4",
        query='Kohler generator receiving',
        lens="receiving",
        description="Expects: brand 'kohler', equipment 'generator', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="brand", value='kohler', required=True),
            ExpectedEntity(type="equipment", value='generator', required=False),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_5",
        query='Volvo Penta shipment',
        lens="receiving",
        description="Expects: brand 'volvo', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='volvo', required=True),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_6",
        query='Yanmar parts invoice',
        lens="receiving",
        description="Expects: brand 'yanmar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='yanmar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_8",
        query='John Deere PO tracking',
        lens="receiving",
        description="Expects: brand 'john deere'",
        expected_entities=[
            ExpectedEntity(type="brand", value='john deere', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_9",
        query='Northern Lights receiving',
        lens="receiving",
        description="Expects: brand 'northern lights', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="brand", value='northern lights', required=True),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_10",
        query='Separ filter shipment',
        lens="receiving",
        description="Expects: brand 'separ', equipment 'filter', part 'filter', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='separ', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_11",
        query='Parker Hannifin parts',
        lens="receiving",
        description="Expects: brand 'parker hannifin'",
        expected_entities=[
            ExpectedEntity(type="brand", value='parker hannifin', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_12",
        query='Perkins engine delivery',
        lens="receiving",
        description="Expects: brand 'perkins', equipment 'engine', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="brand", value='perkins', required=True),
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_13",
        query='Cummins parts receiving',
        lens="receiving",
        description="Expects: brand 'cummins', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="brand", value='cummins', required=True),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_14",
        query='Detroit Diesel invoice',
        lens="receiving",
        description="Expects: brand 'detroit diesel'",
        expected_entities=[
            ExpectedEntity(type="brand", value='detroit diesel', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_15",
        query='Twin Disc shipment tracking',
        lens="receiving",
        description="Expects: brand 'twin disc', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='twin disc', required=True),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_16",
        query='ZF Marine transmission delivery',
        lens="receiving",
        description="Expects: brand 'zf', equipment 'transmission', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="brand", value='zf', required=True),
            ExpectedEntity(type="equipment", value='transmission', required=False),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_17",
        query='Aquadrive coupling receiving',
        lens="receiving",
        description="Expects: part 'coupling', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="part", value='coupling', required=False),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_18",
        query='Reverso pump shipment',
        lens="receiving",
        description="Expects: brand 'reverso', equipment 'pump', part 'pump', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='reverso', required=True),
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_19",
        query='Victron charger invoice',
        lens="receiving",
        description="Expects: equipment 'charger'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='charger', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_20",
        query='Mastervolt battery delivery',
        lens="receiving",
        description="Expects: equipment 'battery', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='battery', required=False),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_21",
        query='rejected receiving',
        lens="receiving",
        description="Expects: receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_22",
        query='approved delivery',
        lens="receiving",
        description="Expects: receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_23",
        query='pending shipment',
        lens="receiving",
        description="Expects: receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_24",
        query='received goods',
        lens="receiving",
        description="Expects: receiving 'received'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='received', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_25",
        query='incomplete delivery',
        lens="receiving",
        description="Expects: receiving 'incomplete'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='incomplete', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_26",
        query='damaged receiving',
        lens="receiving",
        description="Expects: receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_27",
        query='delayed shipment',
        lens="receiving",
        description="Expects: receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_29",
        query='backordered parts',
        lens="receiving",
        description="Expects: receiving 'backordered'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='backordered', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_30",
        query='partial delivery received',
        lens="receiving",
        description="Expects: receiving 'received'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='received', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_32",
        query='disputed receiving',
        lens="receiving",
        description="Expects: receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_33",
        query='verified shipment',
        lens="receiving",
        description="Expects: receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_34",
        query='processing delivery',
        lens="receiving",
        description="Expects: receiving 'processing'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='processing', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_35",
        query='held at customs receiving',
        lens="receiving",
        description="Expects: receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_36",
        query='rejected Racor invoice delivery',
        lens="receiving",
        description="Expects: brand 'racor', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_37",
        query='approved Caterpillar parts shipment',
        lens="receiving",
        description="Expects: brand 'caterpillar', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_38",
        query='pending MTU engine delivery invoice',
        lens="receiving",
        description="Expects: brand 'mtu', equipment 'engine', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="brand", value='mtu', required=True),
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_39",
        query='damaged Kohler generator receiving',
        lens="receiving",
        description="Expects: brand 'kohler', equipment 'generator', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="brand", value='kohler', required=True),
            ExpectedEntity(type="equipment", value='generator', required=False),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_40",
        query='incomplete Yanmar parts delivery',
        lens="receiving",
        description="Expects: brand 'yanmar', receiving 'incomplete'",
        expected_entities=[
            ExpectedEntity(type="brand", value='yanmar', required=True),
            ExpectedEntity(type="receiving_status", value='incomplete', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_41",
        query='delayed Volvo Penta shipment invoice',
        lens="receiving",
        description="Expects: brand 'volvo', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='volvo', required=True),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_42",
        query='partial Cummins parts receiving',
        lens="receiving",
        description="Expects: brand 'cummins', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="brand", value='cummins', required=True),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_43",
        query='verified Parker filter delivery',
        lens="receiving",
        description="Expects: brand 'parker', equipment 'filter', part 'filter', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="brand", value='parker', required=True),
            ExpectedEntity(type="equipment", value='filter', required=False),
            ExpectedEntity(type="part", value='filter', required=False),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_44",
        query='disputed Separ parts invoice',
        lens="receiving",
        description="Expects: brand 'separ'",
        expected_entities=[
            ExpectedEntity(type="brand", value='separ', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_45",
        query='backordered Northern Lights generator',
        lens="receiving",
        description="Expects: brand 'northern lights', equipment 'generator', receiving 'backordered'",
        expected_entities=[
            ExpectedEntity(type="brand", value='northern lights', required=True),
            ExpectedEntity(type="equipment", value='generator', required=False),
            ExpectedEntity(type="receiving_status", value='backordered', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_46",
        query='cancelled Perkins engine PO',
        lens="receiving",
        description="Expects: brand 'perkins', equipment 'engine'",
        expected_entities=[
            ExpectedEntity(type="brand", value='perkins', required=True),
            ExpectedEntity(type="equipment", value='engine', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_47",
        query='overdue Onan shipment invoice',
        lens="receiving",
        description="Expects: brand 'onan', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='onan', required=True),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_48",
        query='processing Detroit Diesel parts delivery',
        lens="receiving",
        description="Expects: brand 'detroit diesel', receiving 'processing'",
        expected_entities=[
            ExpectedEntity(type="brand", value='detroit diesel', required=True),
            ExpectedEntity(type="receiving_status", value='processing', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_49",
        query='received ZF Marine transmission shipment',
        lens="receiving",
        description="Expects: brand 'zf', equipment 'transmission', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='zf', required=True),
            ExpectedEntity(type="equipment", value='transmission', required=False),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_50",
        query='held at customs Twin Disc parts',
        lens="receiving",
        description="Expects: brand 'twin disc'",
        expected_entities=[
            ExpectedEntity(type="brand", value='twin disc', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_51",
        query='rejected Victron charger invoice with damage',
        lens="receiving",
        description="Expects: equipment 'charger'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='charger', required=False)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_52",
        query='approved Mastervolt battery delivery packing slip',
        lens="receiving",
        description="Expects: equipment 'battery', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="equipment", value='battery', required=False),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_53",
        query='pending Reverso pump shipment tracking number',
        lens="receiving",
        description="Expects: brand 'reverso', equipment 'pump', part 'pump', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='reverso', required=True),
            ExpectedEntity(type="equipment", value='pump', required=False),
            ExpectedEntity(type="part", value='pump', required=False),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_54",
        query='damaged Aquadrive coupling receiving report',
        lens="receiving",
        description="Expects: part 'coupling', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="part", value='coupling', required=False),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_55",
        query='incomplete John Deere parts purchase order',
        lens="receiving",
        description="Expects: brand 'john deere', receiving 'incomplete'",
        expected_entities=[
            ExpectedEntity(type="brand", value='john deere', required=True),
            ExpectedEntity(type="receiving_status", value='incomplete', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_59",
        query='delivery',
        lens="receiving",
        description="Expects: receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_62",
        query='that shipment',
        lens="receiving",
        description="Expects: receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_70",
        query='items waiting',
        lens="receiving",
        description="Expects: receiving 'waiting'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='waiting', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_71",
        query='recieving Racor',
        lens="receiving",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_72",
        query='reciving Caterpillar',
        lens="receiving",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_73",
        query='RACOR RECEIVING',
        lens="receiving",
        description="Expects: brand 'racor', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_74",
        query='racer receiving',
        lens="receiving",
        description="Expects: receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_75",
        query='p.o. tracking MTU',
        lens="receiving",
        description="Expects: brand 'mtu'",
        expected_entities=[
            ExpectedEntity(type="brand", value='mtu', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_76",
        query='p/o Kohler parts',
        lens="receiving",
        description="Expects: brand 'kohler'",
        expected_entities=[
            ExpectedEntity(type="brand", value='kohler', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_79",
        query='Racor;Caterpillar;MTU',
        lens="receiving",
        description="Expects: brand 'mtu'",
        expected_entities=[
            ExpectedEntity(type="brand", value='mtu', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_80",
        query='Racor/Caterpillar parts',
        lens="receiving",
        description="Expects: brand 'caterpillar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_81",
        query='goods received note Yanmar',
        lens="receiving",
        description="Expects: brand 'yanmar', receiving 'received'",
        expected_entities=[
            ExpectedEntity(type="brand", value='yanmar', required=True),
            ExpectedEntity(type="receiving_status", value='received', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_82",
        query='purchase order Volvo',
        lens="receiving",
        description="Expects: brand 'volvo'",
        expected_entities=[
            ExpectedEntity(type="brand", value='volvo', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_83",
        query='!@#$% Racor receiving',
        lens="receiving",
        description="Expects: brand 'racor', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_84",
        query='123 Racor parts 456',
        lens="receiving",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_85",
        query='Racor    receiving',
        lens="receiving",
        description="Expects: brand 'racor', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_86",
        query='Can you show me all the Racor parts that have been received?',
        lens="receiving",
        description="Expects: brand 'racor', receiving 'received'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True),
            ExpectedEntity(type="receiving_status", value='received', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_87",
        query='I need to check if the Caterpillar invoice arrived today',
        lens="receiving",
        description="Expects: brand 'caterpillar', receiving 'arrived'",
        expected_entities=[
            ExpectedEntity(type="brand", value='caterpillar', required=True),
            ExpectedEntity(type="receiving_status", value='arrived', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_88",
        query="What's the status of the MTU engine shipment we were expecting?",
        lens="receiving",
        description="Expects: brand 'mtu', equipment 'engine', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='mtu', required=True),
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_89",
        query='Did we reject any deliveries from Kohler this week?',
        lens="receiving",
        description="Expects: brand 'kohler'",
        expected_entities=[
            ExpectedEntity(type="brand", value='kohler', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_90",
        query="I'm looking for the Yanmar parts that were supposed to arrive yesterday",
        lens="receiving",
        description="Expects: brand 'yanmar'",
        expected_entities=[
            ExpectedEntity(type="brand", value='yanmar', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_91",
        query='Please help me find any pending shipments from Volvo Penta',
        lens="receiving",
        description="Expects: brand 'volvo'",
        expected_entities=[
            ExpectedEntity(type="brand", value='volvo', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_92",
        query='Where is the Onan generator delivery? It should have been here by now.',
        lens="receiving",
        description="Expects: brand 'onan', equipment 'generator', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="brand", value='onan', required=True),
            ExpectedEntity(type="equipment", value='generator', required=False),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_93",
        query='Can someone verify if the Perkins engine parts were approved for receiving?',
        lens="receiving",
        description="Expects: brand 'perkins', equipment 'engine', receiving 'receiving'",
        expected_entities=[
            ExpectedEntity(type="brand", value='perkins', required=True),
            ExpectedEntity(type="equipment", value='engine', required=False),
            ExpectedEntity(type="receiving_status", value='receiving', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_94",
        query="There's a problem with the Cummins shipment, it arrived damaged",
        lens="receiving",
        description="Expects: brand 'cummins', receiving 'shipment'",
        expected_entities=[
            ExpectedEntity(type="brand", value='cummins', required=True),
            ExpectedEntity(type="receiving_status", value='shipment', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_95",
        query='Need to track down incomplete delivery from Detroit Diesel last month',
        lens="receiving",
        description="Expects: brand 'detroit diesel', receiving 'incomplete'",
        expected_entities=[
            ExpectedEntity(type="brand", value='detroit diesel', required=True),
            ExpectedEntity(type="receiving_status", value='incomplete', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_96",
        query='Has anyone checked whether the ZF Marine transmission invoice matched the delivery?',
        lens="receiving",
        description="Expects: brand 'zf', equipment 'transmission', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="brand", value='zf', required=True),
            ExpectedEntity(type="equipment", value='transmission', required=False),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_97",
        query="We're still waiting for the backordered Parker filters, any update?",
        lens="receiving",
        description="Expects: brand 'parker', receiving 'backordered'",
        expected_entities=[
            ExpectedEntity(type="brand", value='parker', required=True),
            ExpectedEntity(type="receiving_status", value='backordered', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_98",
        query="The Separ parts arrived but they're being held at customs, what do we do?",
        lens="receiving",
        description="Expects: brand 'separ', receiving 'arrived'",
        expected_entities=[
            ExpectedEntity(type="brand", value='separ', required=True),
            ExpectedEntity(type="receiving_status", value='arrived', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_99",
        query='Just got notification that Northern Lights generator delivery is delayed by two weeks',
        lens="receiving",
        description="Expects: brand 'northern lights', equipment 'generator', receiving 'delivery'",
        expected_entities=[
            ExpectedEntity(type="brand", value='northern lights', required=True),
            ExpectedEntity(type="equipment", value='generator', required=False),
            ExpectedEntity(type="receiving_status", value='delivery', required=True)
        ],
        min_results=1,
    ),
    GroundTruthCase(
        id="receiving_100",
        query='Boss wants to know about all rejected invoices from suppliers this quarter, starting with Racor',
        lens="receiving",
        description="Expects: brand 'racor'",
        expected_entities=[
            ExpectedEntity(type="brand", value='racor', required=True)
        ],
        min_results=1,
    ),
]


# Type aliases for scoring - semantically equivalent entity types
# Maps expected type -> list of acceptable actual types
TYPE_ALIASES = {
    'brand': ['brand', 'equipment_brand', 'manufacturer'],
    'equipment_brand': ['brand', 'equipment_brand', 'manufacturer'],
    'manufacturer': ['brand', 'equipment_brand', 'manufacturer'],
    'equipment': ['equipment', 'equipment_type'],
    'equipment_type': ['equipment', 'equipment_type'],
    'part': ['part', 'part_type', 'subcomponent'],
    'status': ['status', 'receiving_status', 'stock_status', 'approval_status'],
}


def normalize_entities(entities: Dict[str, List[str]]) -> Dict[str, Set[str]]:
    """Normalize entity dict for comparison."""
    normalized = {}
    for entity_type, values in entities.items():
        if values:
            normalized[entity_type.lower()] = {v.lower() if isinstance(v, str) else str(v).lower() for v in values}
    return normalized


def get_equivalent_types(entity_type: str) -> List[str]:
    """Get all types that are equivalent to the given type."""
    entity_type = entity_type.lower()
    return TYPE_ALIASES.get(entity_type, [entity_type])


def calculate_extraction_score(case: GroundTruthCase, actual_entities: Dict) -> float:
    """
    Calculate how well actual extraction matches expected.
    Returns 0.0 to 1.0.
    """
    normalized = normalize_entities(actual_entities)

    required_entities = [e for e in case.expected_entities if e.required]
    optional_entities = [e for e in case.expected_entities if not e.required]

    required_matched = 0
    for expected in required_entities:
        exp_type = expected.type.lower()
        # Check all equivalent types
        equivalent_types = get_equivalent_types(exp_type)
        matched = False
        for check_type in equivalent_types:
            if check_type in normalized:
                if expected.value is None:
                    required_matched += 1
                    matched = True
                    break
                elif expected.value.lower() in normalized[check_type]:
                    required_matched += 1
                    matched = True
                    break
                elif any(expected.value.lower() in v for v in normalized[check_type]):
                    required_matched += 0.8
                    matched = True
                    break
        # If no match found in equivalent types, don't add anything

    optional_matched = 0
    for expected in optional_entities:
        exp_type = expected.type.lower()
        # Check all equivalent types
        equivalent_types = get_equivalent_types(exp_type)
        for check_type in equivalent_types:
            if check_type in normalized:
                optional_matched += 1
                break

    required_score = required_matched / len(required_entities) if required_entities else 1.0
    optional_score = optional_matched / len(optional_entities) if optional_entities else 1.0

    return 0.8 * required_score + 0.2 * optional_score


class TestComprehensiveAccuracy:
    """Comprehensive accuracy tests from 598-query corpus."""

    @pytest.fixture(scope="class")
    def orchestrator(self):
        from extraction.orchestrator import ExtractionOrchestrator
        return ExtractionOrchestrator()

    @pytest.mark.asyncio
    async def test_all_ground_truth(self, orchestrator):
        """Run all ground truth tests."""

        results = {
            'total': len(GROUND_TRUTH),
            'passed': 0,
            'partial': 0,
            'failed': 0,
            'by_lens': {},
            'failures': []
        }

        for case in GROUND_TRUTH:
            result = await orchestrator.extract(case.query)
            entities = result.get('entities', {})
            score = calculate_extraction_score(case, entities)

            if case.lens not in results['by_lens']:
                results['by_lens'][case.lens] = {'passed': 0, 'partial': 0, 'failed': 0}

            if score >= 0.8:
                results['passed'] += 1
                results['by_lens'][case.lens]['passed'] += 1
            elif score >= 0.5:
                results['partial'] += 1
                results['by_lens'][case.lens]['partial'] += 1
            else:
                results['failed'] += 1
                results['by_lens'][case.lens]['failed'] += 1
                results['failures'].append({
                    'id': case.id,
                    'query': case.query,
                    'expected': [e.type for e in case.expected_entities],
                    'actual': list(entities.keys()),
                    'score': score
                })

        # Print report
        print(f"\n{'='*70}")
        print("COMPREHENSIVE ACCURACY REPORT")
        print(f"{'='*70}")
        print(f"Total: {results['total']}")
        print(f"Passed (>=80%): {results['passed']} ({100*results['passed']/results['total']:.1f}%)")
        print(f"Partial (50-79%): {results['partial']} ({100*results['partial']/results['total']:.1f}%)")
        print(f"Failed (<50%): {results['failed']} ({100*results['failed']/results['total']:.1f}%)")

        print(f"\nBy lens:")
        for lens, lens_results in sorted(results['by_lens'].items()):
            total = lens_results['passed'] + lens_results['partial'] + lens_results['failed']
            print(f"  {lens}: {lens_results['passed']}/{total} passed")

        if results['failures']:
            print(f"\nFirst 10 failures:")
            for f in results['failures'][:10]:
                print(f"  [{f['id']}] {f['query'][:40]}...")
                print(f"    Expected: {f['expected']}")
                print(f"    Actual: {f['actual']}")

        # Assert overall accuracy >= 80%
        accuracy = results['passed'] / results['total']
        assert accuracy >= 0.80, f"Overall accuracy {accuracy:.1%} below 80% threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

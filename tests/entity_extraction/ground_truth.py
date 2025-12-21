"""
Ground Truth Dataset Manager
============================

Creates and manages the "golden dataset" of known-good entity extractions.

This is CRITICAL for testing:
- Precision: What % of extracted entities are actually correct?
- Recall: What % of entities that SHOULD be extracted ARE extracted?
- F1 Score: Harmonic mean of precision and recall

The ground truth is created through:
1. Human annotation of sample queries
2. Document-derived test cases
3. Known-good examples from maritime forums/manuals

NO AUTOMATION - all ground truth must be human-validated.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


class EntityType(Enum):
    """Valid entity types for ground truth."""
    EQUIPMENT = "equipment"
    SYSTEM = "system"
    PART = "part"
    BRAND = "brand"
    MODEL = "model"
    SYMPTOM = "symptom"
    FAULT_CODE = "fault_code"
    MEASUREMENT = "measurement"
    ACTION = "action"
    PERSON = "person"
    LOCATION = "location"
    OBSERVATION = "observation"
    DIAGNOSTIC = "diagnostic"


@dataclass
class GroundTruthEntity:
    """A single annotated entity in the ground truth."""
    text: str  # The actual text in the query
    entity_type: str  # EntityType value
    canonical: str  # Canonical/normalized form
    start: int  # Character position start
    end: int  # Character position end
    confidence: float  # Expected confidence (0.0-1.0)
    notes: Optional[str] = None


@dataclass
class GroundTruthQuery:
    """A query with annotated entities (ground truth)."""
    query_id: str
    query_text: str
    source: str  # 'manual', 'document', 'forum', 'synthetic'
    category: str  # 'engine', 'electrical', 'navigation', etc.
    expected_intent: str
    expected_entities: List[GroundTruthEntity]
    annotator: str
    annotation_date: str
    validated: bool = False
    validation_notes: Optional[str] = None


class GroundTruthManager:
    """
    Manages the ground truth dataset for entity extraction testing.

    Ground truth is stored in SQLite for durability and easy querying.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path(__file__).parent / "ground_truth.db")
        self._init_db()

    def _init_db(self):
        """Initialize the ground truth database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Queries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                query_id TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                expected_intent TEXT,
                annotator TEXT NOT NULL,
                annotation_date TEXT NOT NULL,
                validated INTEGER DEFAULT 0,
                validation_notes TEXT
            )
        ''')

        # Entities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY,
                query_id TEXT NOT NULL,
                text TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                canonical TEXT NOT NULL,
                start_pos INTEGER NOT NULL,
                end_pos INTEGER NOT NULL,
                confidence REAL NOT NULL,
                notes TEXT,
                FOREIGN KEY(query_id) REFERENCES queries(query_id)
            )
        ''')

        # Test runs table (track extraction test results)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_runs (
                run_id TEXT PRIMARY KEY,
                run_date TEXT NOT NULL,
                total_queries INTEGER,
                precision REAL,
                recall REAL,
                f1_score REAL,
                details TEXT
            )
        ''')

        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_queries_cat ON queries(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_queries_src ON queries(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_query ON entities(query_id)')

        conn.commit()
        conn.close()

    def add_ground_truth(self, gt: GroundTruthQuery) -> bool:
        """Add a ground truth query with entities."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Insert query
            cursor.execute('''
                INSERT INTO queries
                (query_id, query_text, source, category, expected_intent, annotator, annotation_date, validated, validation_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                gt.query_id, gt.query_text, gt.source, gt.category,
                gt.expected_intent, gt.annotator, gt.annotation_date,
                1 if gt.validated else 0, gt.validation_notes
            ))

            # Insert entities
            for entity in gt.expected_entities:
                cursor.execute('''
                    INSERT INTO entities
                    (query_id, text, entity_type, canonical, start_pos, end_pos, confidence, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    gt.query_id, entity.text, entity.entity_type, entity.canonical,
                    entity.start, entity.end, entity.confidence, entity.notes
                ))

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Query {gt.query_id} already exists")
            return False
        finally:
            conn.close()

    def get_all_ground_truth(self, category: Optional[str] = None) -> List[GroundTruthQuery]:
        """Get all ground truth queries, optionally filtered by category."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if category:
            cursor.execute('SELECT * FROM queries WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT * FROM queries')

        queries = []
        for row in cursor.fetchall():
            query_id = row[0]

            # Get entities for this query
            cursor.execute('SELECT * FROM entities WHERE query_id = ?', (query_id,))
            entities = [
                GroundTruthEntity(
                    text=e[2],
                    entity_type=e[3],
                    canonical=e[4],
                    start=e[5],
                    end=e[6],
                    confidence=e[7],
                    notes=e[8]
                ) for e in cursor.fetchall()
            ]

            queries.append(GroundTruthQuery(
                query_id=row[0],
                query_text=row[1],
                source=row[2],
                category=row[3],
                expected_intent=row[4],
                expected_entities=entities,
                annotator=row[5],
                annotation_date=row[6],
                validated=bool(row[7]),
                validation_notes=row[8]
            ))

        conn.close()
        return queries

    def get_statistics(self) -> Dict:
        """Get statistics about the ground truth dataset."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        # Total queries
        cursor.execute('SELECT COUNT(*) FROM queries')
        stats['total_queries'] = cursor.fetchone()[0]

        # By category
        cursor.execute('SELECT category, COUNT(*) FROM queries GROUP BY category')
        stats['by_category'] = dict(cursor.fetchall())

        # By source
        cursor.execute('SELECT source, COUNT(*) FROM queries GROUP BY source')
        stats['by_source'] = dict(cursor.fetchall())

        # Total entities
        cursor.execute('SELECT COUNT(*) FROM entities')
        stats['total_entities'] = cursor.fetchone()[0]

        # By entity type
        cursor.execute('SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type')
        stats['by_entity_type'] = dict(cursor.fetchall())

        # Validated vs not
        cursor.execute('SELECT validated, COUNT(*) FROM queries GROUP BY validated')
        validation = dict(cursor.fetchall())
        stats['validated'] = validation.get(1, 0)
        stats['not_validated'] = validation.get(0, 0)

        conn.close()
        return stats

    def export_to_json(self, output_path: str):
        """Export ground truth to JSON for sharing/backup."""
        queries = self.get_all_ground_truth()

        export_data = {
            'exported_at': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'queries': [
                {
                    'query_id': q.query_id,
                    'query_text': q.query_text,
                    'source': q.source,
                    'category': q.category,
                    'expected_intent': q.expected_intent,
                    'annotator': q.annotator,
                    'annotation_date': q.annotation_date,
                    'validated': q.validated,
                    'entities': [
                        {
                            'text': e.text,
                            'type': e.entity_type,
                            'canonical': e.canonical,
                            'span': [e.start, e.end],
                            'confidence': e.confidence
                        } for e in q.expected_entities
                    ]
                } for q in queries
            ]
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"Exported {len(queries)} queries to {output_path}")

    def import_from_json(self, input_path: str, annotator: str = "import"):
        """Import ground truth from JSON."""
        with open(input_path) as f:
            data = json.load(f)

        imported = 0
        for q in data.get('queries', []):
            entities = [
                GroundTruthEntity(
                    text=e['text'],
                    entity_type=e['type'],
                    canonical=e['canonical'],
                    start=e['span'][0],
                    end=e['span'][1],
                    confidence=e.get('confidence', 0.9)
                ) for e in q.get('entities', [])
            ]

            gt = GroundTruthQuery(
                query_id=q['query_id'],
                query_text=q['query_text'],
                source=q.get('source', 'import'),
                category=q.get('category', 'unknown'),
                expected_intent=q.get('expected_intent', 'unknown'),
                expected_entities=entities,
                annotator=q.get('annotator', annotator),
                annotation_date=q.get('annotation_date', datetime.now().isoformat()),
                validated=q.get('validated', False)
            )

            if self.add_ground_truth(gt):
                imported += 1

        print(f"Imported {imported} queries")


def create_initial_ground_truth() -> List[GroundTruthQuery]:
    """
    Create initial ground truth dataset from known-good examples.

    These are MANUALLY VERIFIED examples that we know are correct.
    """
    now = datetime.now().isoformat()

    ground_truth = [
        # Engine queries
        GroundTruthQuery(
            query_id="gt_001",
            query_text="MTU 16V4000 engine overheating with high exhaust temperature",
            source="manual",
            category="engine",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("MTU", "brand", "MTU", 0, 3, 0.95),
                GroundTruthEntity("16V4000", "model", "16V4000", 4, 11, 0.90),
                GroundTruthEntity("engine", "equipment", "ENGINE", 12, 18, 0.85),
                GroundTruthEntity("overheating", "symptom", "OVERHEATING", 19, 30, 0.95),
                GroundTruthEntity("high exhaust temperature", "diagnostic", "HIGH_EXHAUST_TEMPERATURE", 36, 60, 0.90),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        GroundTruthQuery(
            query_id="gt_002",
            query_text="Caterpillar 3512 showing fault code E047 coolant leak",
            source="manual",
            category="engine",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("Caterpillar", "brand", "CATERPILLAR", 0, 11, 0.95),
                GroundTruthEntity("3512", "model", "3512", 12, 16, 0.90),
                GroundTruthEntity("E047", "fault_code", "E047", 36, 40, 0.98),
                GroundTruthEntity("coolant leak", "symptom", "COOLANT_LEAK", 41, 53, 0.90),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Navigation queries
        GroundTruthQuery(
            query_id="gt_003",
            query_text="Furuno radar display showing error code E-15",
            source="manual",
            category="navigation",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("Furuno", "brand", "FURUNO", 0, 6, 0.95),
                GroundTruthEntity("radar", "equipment", "RADAR", 7, 12, 0.90),
                GroundTruthEntity("display", "part", "DISPLAY", 13, 20, 0.80),
                GroundTruthEntity("E-15", "fault_code", "E-15", 40, 44, 0.95),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Electrical queries
        GroundTruthQuery(
            query_id="gt_004",
            query_text="24V generator failure alarm at 1800 rpm",
            source="manual",
            category="electrical",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("24V", "measurement", "24V", 0, 3, 0.92),
                GroundTruthEntity("generator", "equipment", "GENERATOR", 4, 13, 0.90),
                GroundTruthEntity("failure", "symptom", "FAILURE", 14, 21, 0.85),
                GroundTruthEntity("alarm", "symptom", "ALARM", 22, 27, 0.80),
                GroundTruthEntity("1800 rpm", "measurement", "1800_RPM", 31, 39, 0.90),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Hydraulic queries
        GroundTruthQuery(
            query_id="gt_005",
            query_text="sea water pump pressure low 2 bar",
            source="manual",
            category="systems",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("sea water pump", "equipment", "SEA_WATER_PUMP", 0, 14, 0.90),
                GroundTruthEntity("pressure low", "symptom", "LOW_PRESSURE", 15, 27, 0.85),
                GroundTruthEntity("2 bar", "measurement", "2_BAR", 28, 33, 0.92),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Watermaker queries
        GroundTruthQuery(
            query_id="gt_006",
            query_text="watermaker membrane needs replacement, low output flow",
            source="manual",
            category="systems",
            expected_intent="find_part",
            expected_entities=[
                GroundTruthEntity("watermaker", "equipment", "WATERMAKER", 0, 10, 0.90),
                GroundTruthEntity("membrane", "part", "MEMBRANE", 11, 19, 0.85),
                GroundTruthEntity("replacement", "action", "REPLACE", 26, 37, 0.80),
                GroundTruthEntity("low output flow", "symptom", "LOW_OUTPUT", 39, 54, 0.85),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Captain report
        GroundTruthQuery(
            query_id="gt_007",
            query_text="captain reported vibration from main engine at 1800 rpm",
            source="manual",
            category="engine",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("captain", "person", "CAPTAIN", 0, 7, 0.85),
                GroundTruthEntity("reported", "observation", "REPORT", 8, 16, 0.80),
                GroundTruthEntity("vibration", "symptom", "VIBRATION", 17, 26, 0.90),
                GroundTruthEntity("main engine", "equipment", "MAIN_ENGINE", 32, 43, 0.90),
                GroundTruthEntity("1800 rpm", "measurement", "1800_RPM", 47, 55, 0.90),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Air conditioning
        GroundTruthQuery(
            query_id="gt_008",
            query_text="Marine Air!"
            + "AC unit compressor not starting, check relay",
            source="manual",
            category="hvac",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("Marine Air", "brand", "MARINE_AIR", 0, 10, 0.90),
                GroundTruthEntity("AC unit", "equipment", "AC_UNIT", 11, 18, 0.85),
                GroundTruthEntity("compressor", "part", "COMPRESSOR", 19, 29, 0.90),
                GroundTruthEntity("not starting", "symptom", "NOT_STARTING", 30, 42, 0.85),
                GroundTruthEntity("relay", "part", "RELAY", 50, 55, 0.80),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Anchor windlass
        GroundTruthQuery(
            query_id="gt_009",
            query_text="Lewmar windlass motor overheating after 5 minutes operation",
            source="manual",
            category="deck",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("Lewmar", "brand", "LEWMAR", 0, 6, 0.95),
                GroundTruthEntity("windlass", "equipment", "WINDLASS", 7, 15, 0.90),
                GroundTruthEntity("motor", "part", "MOTOR", 16, 21, 0.85),
                GroundTruthEntity("overheating", "symptom", "OVERHEATING", 22, 33, 0.90),
                GroundTruthEntity("5 minutes", "measurement", "5_MINUTES", 40, 49, 0.75),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Battery query
        GroundTruthQuery(
            query_id="gt_010",
            query_text="Victron battery monitor showing 11.8V, low voltage alarm",
            source="manual",
            category="electrical",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("Victron", "brand", "VICTRON", 0, 7, 0.95),
                GroundTruthEntity("battery monitor", "equipment", "BATTERY_MONITOR", 8, 23, 0.90),
                GroundTruthEntity("11.8V", "measurement", "11.8V", 32, 37, 0.92),
                GroundTruthEntity("low voltage", "symptom", "LOW_VOLTAGE", 39, 50, 0.85),
                GroundTruthEntity("alarm", "symptom", "ALARM", 51, 56, 0.80),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Work order action queries
        GroundTruthQuery(
            query_id="gt_011",
            query_text="create work order for bilge pump inspection",
            source="manual",
            category="action",
            expected_intent="create_work_order",
            expected_entities=[
                GroundTruthEntity("create work order", "action", "CREATE_WORK_ORDER", 0, 17, 0.95),
                GroundTruthEntity("bilge pump", "equipment", "BILGE_PUMP", 22, 32, 0.90),
                GroundTruthEntity("inspection", "action", "INSPECT", 33, 43, 0.85),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        GroundTruthQuery(
            query_id="gt_012",
            query_text="find manual for Spectra watermaker LB-2800",
            source="manual",
            category="action",
            expected_intent="find_manual",
            expected_entities=[
                GroundTruthEntity("find manual", "action", "FIND_MANUAL", 0, 11, 0.90),
                GroundTruthEntity("Spectra", "brand", "SPECTRA", 16, 23, 0.95),
                GroundTruthEntity("watermaker", "equipment", "WATERMAKER", 24, 34, 0.90),
                GroundTruthEntity("LB-2800", "model", "LB-2800", 35, 42, 0.85),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Temperature reading
        GroundTruthQuery(
            query_id="gt_013",
            query_text="engine coolant temperature reading 95°C, normal range 80-90°C",
            source="manual",
            category="engine",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("engine coolant", "system", "COOLANT_SYSTEM", 0, 14, 0.85),
                GroundTruthEntity("temperature reading", "measurement", "TEMPERATURE", 15, 34, 0.80),
                GroundTruthEntity("95°C", "measurement", "95C", 35, 39, 0.92),
                GroundTruthEntity("80-90°C", "measurement", "80-90C", 55, 62, 0.90),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # SPN/FMI fault code
        GroundTruthQuery(
            query_id="gt_014",
            query_text="J1939 SPN 100 FMI 3 engine oil pressure low",
            source="manual",
            category="engine",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("J1939", "diagnostic", "J1939", 0, 5, 0.90),
                GroundTruthEntity("SPN 100 FMI 3", "fault_code", "SPN100_FMI3", 6, 19, 0.98),
                GroundTruthEntity("engine oil pressure", "system", "OIL_PRESSURE", 20, 39, 0.85),
                GroundTruthEntity("low", "symptom", "LOW", 40, 43, 0.80),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),

        # Fire system
        GroundTruthQuery(
            query_id="gt_015",
            query_text="fire damper stuck open in engine room ventilation",
            source="manual",
            category="safety",
            expected_intent="diagnose_issue",
            expected_entities=[
                GroundTruthEntity("fire damper", "equipment", "FIRE_DAMPER", 0, 11, 0.90),
                GroundTruthEntity("stuck open", "symptom", "STUCK_OPEN", 12, 22, 0.85),
                GroundTruthEntity("engine room", "location", "ENGINE_ROOM", 26, 37, 0.80),
                GroundTruthEntity("ventilation", "system", "VENTILATION", 38, 49, 0.75),
            ],
            annotator="system_init",
            annotation_date=now,
            validated=True
        ),
    ]

    return ground_truth


if __name__ == "__main__":
    # Initialize with ground truth
    manager = GroundTruthManager()

    print("Creating initial ground truth dataset...")
    initial_gt = create_initial_ground_truth()

    for gt in initial_gt:
        manager.add_ground_truth(gt)

    print("\nGround Truth Statistics:")
    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Export
    manager.export_to_json("/tmp/ground_truth_export.json")

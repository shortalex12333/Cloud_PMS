"""
CSV Parser for the import pipeline.
Handles: encoding detection, delimiter detection, header identification,
date format detection, and row extraction.

Supports IDEA Yacht (semicolon, UPPER_SNAKE, Latin-1),
Seahub (comma, snake_case, UTF-8), Sealogical (comma, Title Case, Windows-1252),
and generic CSV files.
"""

import csv
import io
import re
import logging
from typing import Optional

from charset_normalizer import from_bytes

from parsers.base_parser import ParseResult, ColumnInfo, FileWarning

logger = logging.getLogger("import.csv_parser")

# Maximum bytes to read for encoding/dialect detection
DETECTION_SAMPLE_SIZE = 16384

# Maximum sample values to store per column
MAX_SAMPLE_VALUES = 5

# Date patterns to check (ordered by specificity)
DATE_PATTERNS = [
    (r"\d{4}-\d{2}-\d{2}", "ISO"),                          # 2025-01-15
    (r"\d{2}-[A-Z]{3}-\d{4}", "DD-MMM-YYYY"),               # 15-JAN-2025
    (r"\d{2}/\d{2}/\d{4}", None),                            # ambiguous: DD/MM or MM/DD
    (r"\d{2}-\d{2}-\d{4}", None),                            # ambiguous: DD-MM or MM-DD
    (r"\d{2}\.\d{2}\.\d{4}", None),                          # ambiguous: DD.MM or MM.DD
]


def detect_encoding(raw: bytes) -> str:
    """Detect file encoding from raw bytes."""
    result = from_bytes(raw).best()
    if result is None:
        return "utf-8"
    encoding = result.encoding
    # Normalize common aliases
    if encoding in ("ascii", "us-ascii"):
        encoding = "utf-8"
    logger.info(f"Encoding detected: {encoding}")
    return encoding


def detect_delimiter(text: str) -> str:
    """Detect CSV delimiter using csv.Sniffer, with fallback to frequency analysis."""
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
        logger.info(f"Delimiter detected via Sniffer: {repr(dialect.delimiter)}")
        return dialect.delimiter
    except csv.Error:
        pass

    # Fallback: count occurrences in first 5 lines
    lines = text.split("\n")[:5]
    sample = "\n".join(lines)
    counts = {
        ",": sample.count(","),
        ";": sample.count(";"),
        "\t": sample.count("\t"),
        "|": sample.count("|"),
    }
    delimiter = max(counts, key=counts.get)
    if counts[delimiter] == 0:
        delimiter = ","  # ultimate fallback
    logger.info(f"Delimiter detected via frequency: {repr(delimiter)}")
    return delimiter


def find_header_row(lines: list[list[str]], max_scan: int = 20) -> int:
    """
    Find the header row by scanning the first N rows.
    The header row is the first row where:
    - More than half the cells are non-empty strings
    - Cells look like column names (not numeric data)
    This handles Sealogical-style metadata rows above the header.
    """
    # First pass: find the row with the MOST non-empty columns that look like headers
    best_idx = 0
    best_score = 0
    for i, row in enumerate(lines[:max_scan]):
        non_empty = [c for c in row if c and c.strip()]
        if len(non_empty) < 2:
            continue  # headers should have at least 2 columns
        fill_ratio = len(non_empty) / max(len(row), 1)
        if fill_ratio < 0.4:
            continue
        # Check if cells look like headers (mostly alpha, not mostly numeric)
        alpha_count = sum(1 for c in non_empty if re.search(r"[a-zA-Z]", c))
        if alpha_count < len(non_empty) * 0.7:
            continue
        # Score = number of non-empty cells (prefer the row with the most columns)
        score = len(non_empty)
        if score > best_score:
            best_score = score
            best_idx = i
    return best_idx


def detect_date_format(values: list[str]) -> Optional[str]:
    """
    Detect date format from sample values.
    Returns: 'ISO', 'DD-MMM-YYYY', 'DD/MM/YYYY', 'MM/DD/YYYY', 'ambiguous', or None.
    """
    if not values:
        return None

    for pattern, fmt in DATE_PATTERNS:
        matches = [v for v in values if re.fullmatch(pattern, v.strip())]
        if len(matches) >= 2:
            if fmt is not None:
                return fmt
            # Ambiguous format — check if first component > 12 to disambiguate
            dayfirst_evidence = 0
            monthfirst_evidence = 0
            for v in matches:
                parts = re.split(r"[/\-.]", v.strip())
                if len(parts) >= 2:
                    try:
                        first, second = int(parts[0]), int(parts[1])
                        if first > 12 and second <= 12:
                            dayfirst_evidence += 1
                        elif second > 12 and first <= 12:
                            monthfirst_evidence += 1
                    except ValueError:
                        continue
            if dayfirst_evidence > monthfirst_evidence:
                return "DD/MM/YYYY"
            elif monthfirst_evidence > dayfirst_evidence:
                return "MM/DD/YYYY"
            else:
                return "ambiguous"
    return None


def infer_domain(headers: list[str]) -> Optional[str]:
    """
    Infer which CelesteOS domain this file belongs to based on column names.
    Order matters: check specific domains BEFORE equipment, since equipment
    columns (equip_id, equipment_name) appear as cross-references in many domains.
    """
    header_set = {h.lower().replace(" ", "_") for h in headers}

    # Work order indicators — check BEFORE equipment (WOs reference equipment)
    wo_signals = {"wo_number", "work_order_id", "task_id", "due_date", "completed_date",
                  "assigned_to", "interval_hours", "interval_days", "wo_type", "work_order_type",
                  "wo_number", "description", "remarks", "planned_date", "last_done_date"}
    wo_strong = {"wo_number", "work_order_id", "task_id", "wo_type", "work_order_type",
                 "interval_hours", "interval_days", "last_done_date", "planned_date"}
    if header_set & wo_strong:
        return "work_orders"
    if len(header_set & wo_signals) >= 3:
        return "work_orders"

    # Fault / defect indicators — check BEFORE equipment (faults reference equipment)
    fault_signals = {"defect_id", "fault_id", "fault_code", "severity", "root_cause",
                     "corrective_action", "reported_by", "detected_at", "closed_by",
                     "closed_date", "reported_date"}
    fault_strong = {"defect_id", "fault_id", "fault_code", "root_cause", "corrective_action"}
    if header_set & fault_strong:
        return "faults"
    if len(header_set & fault_signals) >= 2:
        return "faults"

    # Parts / inventory indicators
    parts_signals = {"part_number", "part_id", "rob_qty", "min_qty", "quantity_on_hand",
                     "minimum_quantity", "part_name", "stock", "last_ordered"}
    parts_strong = {"part_number", "part_id", "rob_qty", "quantity_on_hand", "min_qty"}
    if header_set & parts_strong:
        return "parts"
    if len(header_set & parts_signals) >= 2:
        return "parts"

    # Certificate indicators
    cert_signals = {"certificate_type", "cert_type", "certificate_number", "cert_number",
                    "issuing_authority", "expiry_date", "issue_date", "survey_due",
                    "certificate_name", "cert_name", "certificate_id", "cert_id"}
    cert_strong = {"certificate_type", "cert_type", "certificate_number", "cert_number",
                   "issuing_authority", "certificate_id", "cert_id"}
    if header_set & cert_strong:
        return "certificates"
    if len(header_set & cert_signals) >= 2:
        return "certificates"

    # Crew indicators
    crew_signals = {"person_name", "rank", "nationality", "stcw", "eng1", "gmdss",
                    "date_of_birth", "passport_number"}
    if len(header_set & crew_signals) >= 2:
        return "crew"

    # Equipment indicators — checked LAST because equipment columns appear everywhere
    equipment_signals = {"serial_number", "serial_no", "maker", "manufacturer", "running_hours",
                         "equip_name", "equip_id", "equip_code", "equipment_name", "equipment_id",
                         "equipment_code", "equipment_name", "service_interval_hours",
                         "criticality", "system_category"}
    equipment_strong = {"equip_name", "equip_code", "equip_id", "running_hours",
                        "service_interval_hours", "serial_no", "equipment_code"}
    if header_set & equipment_strong:
        return "equipment"
    if len(header_set & equipment_signals) >= 3:
        return "equipment"

    return None


def parse_csv(raw_data: bytes, filename: str = "unknown.csv") -> ParseResult:
    """
    Parse a CSV file from raw bytes.
    Returns a ParseResult with detected encoding, delimiter, headers, rows, and warnings.
    """
    warnings: list[FileWarning] = []

    # 1. Detect encoding
    sample = raw_data[:DETECTION_SAMPLE_SIZE]
    encoding = detect_encoding(sample)

    try:
        text = raw_data.decode(encoding, errors="replace")
    except (UnicodeDecodeError, LookupError):
        encoding = "utf-8"
        text = raw_data.decode(encoding, errors="replace")
        warnings.append(FileWarning(
            field=None,
            message=f"Encoding detection failed, fell back to UTF-8",
            severity="amber",
        ))

    # Strip BOM if present
    if text.startswith("\ufeff"):
        text = text[1:]

    # Strip null bytes (corrupted files)
    if "\x00" in text:
        text = text.replace("\x00", "")
        warnings.append(FileWarning(
            field=None,
            message="File contains null bytes (possible corruption). Null bytes stripped.",
            severity="amber",
        ))

    # 2. Detect delimiter
    delimiter = detect_delimiter(text)

    # 3. Parse all rows
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    all_rows = []
    for row in reader:
        all_rows.append(row)

    if not all_rows:
        return ParseResult(
            filename=filename,
            encoding_detected=encoding,
            delimiter_detected=delimiter,
            header_row=0,
            row_count=0,
            warnings=[FileWarning(field=None, message="File is empty", severity="red")],
        )

    # 4. Find header row (handles Sealogical metadata rows)
    header_idx = find_header_row(all_rows)
    headers = [h.strip() for h in all_rows[header_idx]]
    data_rows = all_rows[header_idx + 1:]

    if header_idx > 0:
        warnings.append(FileWarning(
            field=None,
            message=f"Skipped {header_idx} metadata row(s) before header",
            severity="info",
            row=header_idx,
        ))

    # 5. Build column info with sample values
    columns: list[ColumnInfo] = []
    for col_idx, header in enumerate(headers):
        if not header:
            continue
        samples = []
        for row in data_rows[:MAX_SAMPLE_VALUES]:
            if col_idx < len(row) and row[col_idx].strip():
                samples.append(row[col_idx].strip())
        columns.append(ColumnInfo(
            source_name=header,
            sample_values=samples,
        ))

    # 6. Detect date format from all date-looking columns
    all_date_values = []
    for col in columns:
        for val in col.sample_values:
            if re.search(r"\d{2,4}[/\-.]", val):
                all_date_values.append(val)
    date_format = detect_date_format(all_date_values)

    if date_format == "ambiguous":
        warnings.append(FileWarning(
            field=None,
            message="Date format is ambiguous (DD/MM vs MM/DD). User must confirm during mapping.",
            severity="amber",
        ))

    # 7. Convert data rows to dicts
    row_dicts = []
    for row_idx, row in enumerate(data_rows):
        if not any(cell.strip() for cell in row):
            continue  # skip empty rows
        row_dict = {}
        for col_idx, header in enumerate(headers):
            if not header:
                continue
            value = row[col_idx].strip() if col_idx < len(row) else ""
            row_dict[header] = value
        row_dicts.append(row_dict)

    # 8. Infer domain
    domain = infer_domain(headers)

    # 9. Check for common issues
    # Warn about empty required-looking columns
    for col in columns:
        if not col.sample_values:
            warnings.append(FileWarning(
                field=col.source_name,
                message=f"Column '{col.source_name}' has no values in sample rows",
                severity="info",
            ))

    logger.info(
        f"Parsed {filename}: {encoding} encoding, "
        f"{repr(delimiter)} delimiter, {len(row_dicts)} rows, "
        f"{len(columns)} columns, domain={domain}"
    )

    return ParseResult(
        filename=filename,
        encoding_detected=encoding,
        delimiter_detected=delimiter,
        header_row=header_idx,
        row_count=len(row_dicts),
        columns=columns,
        rows=row_dicts,
        date_format_detected=date_format,
        warnings=warnings,
        domain_hint=domain,
    )

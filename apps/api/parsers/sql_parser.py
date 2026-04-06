"""
SQL Parser for the import pipeline.
Handles IDEA Yacht SQL dumps — both INSERT INTO statements and pg_dump COPY blocks.

Two formats supported:
1. INSERT INTO table (col1, col2) VALUES ('val1', 'val2');
2. COPY table (col1, col2) FROM stdin;
   val1\tval2
   \.
"""

import re
import io
import logging
from typing import Optional

from parsers.base_parser import ParseResult, ColumnInfo, FileWarning
from parsers.csv_parser import infer_domain

logger = logging.getLogger("import.sql_parser")

MAX_SAMPLE_VALUES = 5

# Regex for CREATE TABLE
RE_CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?"
    r"[\"']?(\w+)[\"']?\s*\((.*?)\);",
    re.DOTALL | re.IGNORECASE,
)

# Regex for INSERT INTO
RE_INSERT = re.compile(
    r"INSERT\s+INTO\s+(?:public\.)?[\"']?(\w+)[\"']?\s*"
    r"\(([^)]+)\)\s*VALUES\s*",
    re.IGNORECASE,
)

# Regex for individual VALUES tuple
RE_VALUES_TUPLE = re.compile(r"\(([^)]+)\)")

# Regex for COPY blocks
RE_COPY_BLOCK = re.compile(
    r"COPY\s+(?:public\.)?[\"']?(\w+)[\"']?\s*\(([^)]+)\)\s+FROM\s+stdin;\n(.*?)\n\\.",
    re.DOTALL | re.IGNORECASE,
)


def _parse_sql_value(raw: str) -> str:
    """Clean a SQL value: strip quotes, handle NULL."""
    raw = raw.strip()
    if raw.upper() == "NULL":
        return ""
    if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
        raw = raw[1:-1]
    # Unescape SQL quotes
    raw = raw.replace("''", "'").replace('\\"', '"')
    return raw


def _split_values(values_str: str) -> list[str]:
    """Split a VALUES tuple string respecting quoted commas."""
    result = []
    current = []
    in_quote = False
    quote_char = None

    for char in values_str:
        if char in ("'", '"') and not in_quote:
            in_quote = True
            quote_char = char
            current.append(char)
        elif char == quote_char and in_quote:
            # Check for escaped quote (doubled)
            current.append(char)
            in_quote = False
        elif char == "," and not in_quote:
            result.append("".join(current))
            current = []
        else:
            current.append(char)

    if current:
        result.append("".join(current))

    return result


def _extract_create_tables(sql_text: str) -> dict[str, list[str]]:
    """Extract table schemas from CREATE TABLE statements.
    Returns {table_name: [column_names]}."""
    tables = {}
    for match in RE_CREATE_TABLE.finditer(sql_text):
        table_name = match.group(1).lower()
        body = match.group(2)
        # Extract column names (first word of each line before type)
        columns = []
        for line in body.split(","):
            line = line.strip()
            if not line or line.upper().startswith(("CONSTRAINT", "PRIMARY", "UNIQUE", "CHECK", "FOREIGN", "INDEX")):
                continue
            # Column name is the first word
            col_match = re.match(r"[\"']?(\w+)[\"']?", line)
            if col_match:
                columns.append(col_match.group(1))
        if columns:
            tables[table_name] = columns
    return tables


def _extract_inserts(sql_text: str) -> dict[str, dict]:
    """Extract INSERT INTO statements.
    Returns {table_name: {"columns": [...], "rows": [...]}}."""
    results = {}

    for match in RE_INSERT.finditer(sql_text):
        table_name = match.group(1).lower()
        columns = [c.strip().strip('"').strip("'") for c in match.group(2).split(",")]

        # Find all VALUES tuples after this INSERT
        rest = sql_text[match.end():]
        rows = []
        for val_match in RE_VALUES_TUPLE.finditer(rest):
            values = _split_values(val_match.group(1))
            cleaned = [_parse_sql_value(v) for v in values]
            if len(cleaned) == len(columns):
                rows.append(dict(zip(columns, cleaned)))
            # Stop if we hit another SQL statement
            if ";" in rest[val_match.end():val_match.end() + 5]:
                break

        if table_name not in results:
            results[table_name] = {"columns": columns, "rows": []}
        results[table_name]["rows"].extend(rows)

    return results


def _extract_copy_blocks(sql_text: str) -> dict[str, dict]:
    """Extract COPY ... FROM stdin blocks (pg_dump format).
    Returns {table_name: {"columns": [...], "rows": [...]}}."""
    results = {}

    for match in RE_COPY_BLOCK.finditer(sql_text):
        table_name = match.group(1).lower()
        columns = [c.strip().strip('"') for c in match.group(2).split(",")]
        data_block = match.group(3)

        rows = []
        for line in data_block.split("\n"):
            line = line.rstrip()
            if not line:
                continue
            values = line.split("\t")
            cleaned = [("" if v == "\\N" else v) for v in values]
            if len(cleaned) == len(columns):
                rows.append(dict(zip(columns, cleaned)))

        results[table_name] = {"columns": columns, "rows": rows}

    return results


def parse_sql(raw_data: bytes, filename: str = "unknown.sql") -> list[ParseResult]:
    """
    Parse a SQL dump file. Returns a list of ParseResult (one per table found).
    Handles both INSERT INTO and COPY FROM stdin formats.
    """
    warnings: list[FileWarning] = []

    # Detect encoding
    from charset_normalizer import from_bytes
    sample = raw_data[:16384]
    result = from_bytes(sample).best()
    encoding = result.encoding if result else "utf-8"

    try:
        sql_text = raw_data.decode(encoding, errors="replace")
    except (UnicodeDecodeError, LookupError):
        encoding = "utf-8"
        sql_text = raw_data.decode(encoding, errors="replace")

    # Strip BOM
    if sql_text.startswith("\ufeff"):
        sql_text = sql_text[1:]

    # Extract schemas
    schemas = _extract_create_tables(sql_text)

    # Extract data from both formats
    insert_data = _extract_inserts(sql_text)
    copy_data = _extract_copy_blocks(sql_text)

    # Merge — COPY takes precedence (more data-dense)
    all_tables = {}
    for table_name, data in insert_data.items():
        all_tables[table_name] = data
    for table_name, data in copy_data.items():
        all_tables[table_name] = data  # overwrite INSERT if COPY exists

    if not all_tables:
        return [ParseResult(
            filename=filename,
            encoding_detected=encoding,
            delimiter_detected=None,
            header_row=0,
            row_count=0,
            warnings=[FileWarning(
                field=None,
                message="No INSERT or COPY statements found in SQL file",
                severity="red",
            )],
        )]

    results = []
    for table_name, data in all_tables.items():
        columns = data["columns"]
        rows = data["rows"]

        # Build ColumnInfo
        col_infos = []
        for col_name in columns:
            samples = []
            for row in rows[:MAX_SAMPLE_VALUES]:
                val = row.get(col_name, "")
                if val:
                    samples.append(val)
            col_infos.append(ColumnInfo(source_name=col_name, sample_values=samples))

        # Infer domain from column names
        domain = infer_domain(columns)

        # Detect date format from values
        from parsers.csv_parser import detect_date_format
        date_values = []
        for row in rows[:20]:
            for v in row.values():
                if v and re.search(r"\d{2,4}[/\-.]", v):
                    date_values.append(v)
        date_format = detect_date_format(date_values) if date_values else None

        parse_result = ParseResult(
            filename=f"{filename}:{table_name}",
            encoding_detected=encoding,
            delimiter_detected=None,
            header_row=0,
            row_count=len(rows),
            columns=col_infos,
            rows=rows,
            date_format_detected=date_format,
            warnings=warnings.copy(),
            domain_hint=domain,
        )
        results.append(parse_result)

        logger.info(f"Parsed {filename}:{table_name}: {len(rows)} rows, {len(columns)} columns, domain={domain}")

    return results

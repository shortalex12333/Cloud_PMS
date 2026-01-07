"""
Security Gate
==============

First-line defense against injection attacks.
Runs BEFORE entity extraction (Module A/B) to block malicious queries.

Current Problem:
    Security tests show 57.1% "pass" but for the WRONG reason.
    Attacks fail at sql_execution because no entity named "SELECT * FROM users" exists.
    That's not security - that's accidental failure.

Solution:
    Block attacks at the GATE before they ever reach extraction or SQL.

Patterns Detected:
    - SQL injection (SELECT, UNION, DROP, INSERT, UPDATE, DELETE)
    - Comment injection (-- , /* */)
    - String termination attacks (' OR '1'='1)
    - Schema enumeration (information_schema, pg_catalog)
    - Command injection (;, &&, |)
    - XSS attempts (<script>, javascript:, onerror)

Usage:
    gate = SecurityGate()
    result = gate.check(query)
    if result.blocked:
        return {"error": "Query blocked", "reason": result.reason}
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum


class ThreatType(str, Enum):
    """Types of security threats detected"""
    SQL_INJECTION = "sql_injection"
    COMMENT_INJECTION = "comment_injection"
    STRING_TERMINATION = "string_termination"
    SCHEMA_ENUMERATION = "schema_enumeration"
    COMMAND_INJECTION = "command_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    NONE = "none"


@dataclass
class SecurityCheckResult:
    """Result of security gate check"""
    blocked: bool
    threat_type: ThreatType
    reason: str
    matched_pattern: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "blocked": self.blocked,
            "threat_type": self.threat_type.value,
            "reason": self.reason,
            "matched_pattern": self.matched_pattern,
            "confidence": self.confidence,
        }


class SecurityGate:
    """
    Security gate to block injection attacks before processing.

    Design Principles:
    1. Block EARLY - before extraction or SQL execution
    2. Block CLEARLY - with specific threat type and reason
    3. Minimize false positives - don't block legitimate maritime queries
    4. High recall for attacks - better to block a few legit queries than miss attacks
    """

    def __init__(self):
        # SQL injection patterns
        # These detect SQL keywords in suspicious contexts
        self.sql_injection_patterns: List[Tuple[str, float, str]] = [
            # Direct SQL statements (very high confidence)
            (r"^\s*SELECT\s+.+\s+FROM\s+", 0.98, "Direct SELECT statement"),
            (r"^\s*INSERT\s+INTO\s+", 0.98, "Direct INSERT statement"),
            (r"^\s*UPDATE\s+\w+\s+SET\s+", 0.98, "Direct UPDATE statement"),
            (r"^\s*DELETE\s+FROM\s+", 0.98, "Direct DELETE statement"),
            (r"^\s*DROP\s+(TABLE|DATABASE|INDEX)", 0.98, "Direct DROP statement"),
            (r"^\s*TRUNCATE\s+", 0.98, "Direct TRUNCATE statement"),
            (r"^\s*ALTER\s+TABLE\s+", 0.98, "Direct ALTER statement"),
            (r"^\s*CREATE\s+(TABLE|DATABASE|INDEX)", 0.98, "Direct CREATE statement"),

            # UNION injection (very high confidence)
            (r"\bUNION\s+(ALL\s+)?SELECT\b", 0.97, "UNION SELECT injection"),
            (r"\bUNION\s+(ALL\s+)?\(\s*SELECT\b", 0.97, "UNION subquery injection"),

            # OR/AND injection (high confidence)
            (r"'\s*OR\s+['\d]", 0.95, "OR injection"),
            (r"'\s*AND\s+['\d]", 0.95, "AND injection"),
            (r'"\s*OR\s+["\d]', 0.95, "OR injection (double quote)"),
            (r"=\s*'\s*'\s*OR", 0.95, "Empty string OR injection"),

            # Stacked queries (high confidence)
            (r";\s*SELECT\s+", 0.96, "Stacked SELECT query"),
            (r";\s*INSERT\s+", 0.96, "Stacked INSERT query"),
            (r";\s*UPDATE\s+", 0.96, "Stacked UPDATE query"),
            (r";\s*DELETE\s+", 0.96, "Stacked DELETE query"),
            (r";\s*DROP\s+", 0.96, "Stacked DROP query"),

            # Information schema enumeration (high confidence)
            (r"\binformation_schema\b", 0.95, "Information schema access"),
            (r"\bpg_catalog\b", 0.95, "PostgreSQL catalog access"),
            (r"\bsys\.(tables|columns|databases)\b", 0.95, "System table access"),
            (r"\bsysobjects\b", 0.95, "SQL Server sysobjects access"),

            # Common injection payloads
            (r"'\s*;\s*--", 0.94, "String termination with comment"),
            (r"--\s*$", 0.90, "Trailing comment injection"),
            (r"#\s*$", 0.85, "MySQL comment injection"),

            # Obfuscation attempts (high confidence - indicates malicious intent)
            (r"/\*.*\*/.*SELECT", 0.96, "Comment-obfuscated SELECT"),
            (r"/\*.*\*/.*UNION", 0.96, "Comment-obfuscated UNION"),
            (r"S\s*E\s*L\s*E\s*C\s*T", 0.94, "Space-obfuscated SELECT"),
            (r"U\s*N\s*I\s*O\s*N", 0.94, "Space-obfuscated UNION"),

            # NULL/boolean injection
            (r"'\s*=\s*'", 0.88, "Empty string comparison"),
            (r"1\s*=\s*1", 0.85, "Tautology injection"),
            (r"'\s*LIKE\s*'", 0.85, "LIKE injection"),

            # Function-based injection
            (r"\bSLEEP\s*\(", 0.92, "Time-based blind injection (SLEEP)"),
            (r"\bBENCHMARK\s*\(", 0.92, "Time-based blind injection (BENCHMARK)"),
            (r"\bWAITFOR\s+DELAY", 0.92, "Time-based blind injection (WAITFOR)"),
            (r"\bPG_SLEEP\s*\(", 0.92, "PostgreSQL time-based injection"),

            # Column/table enumeration
            (r"ORDER\s+BY\s+\d{2,}", 0.88, "Column count enumeration"),
            (r"GROUP\s+BY\s+\d{2,}", 0.88, "Group by enumeration"),
        ]

        # Comment injection patterns
        self.comment_patterns: List[Tuple[str, float, str]] = [
            (r"/\*[\s\S]*?\*/", 0.85, "Block comment"),
            (r"--[^\n]*", 0.80, "Line comment"),
            (r"#[^\n]*$", 0.75, "Hash comment"),
        ]

        # XSS patterns
        self.xss_patterns: List[Tuple[str, float, str]] = [
            (r"<\s*script", 0.95, "Script tag"),
            (r"javascript\s*:", 0.95, "JavaScript protocol"),
            (r"on\w+\s*=", 0.90, "Event handler attribute"),
            (r"<\s*img[^>]+onerror", 0.95, "IMG onerror injection"),
            (r"<\s*svg[^>]+onload", 0.95, "SVG onload injection"),
            (r"<\s*iframe", 0.90, "IFrame injection"),
            (r"<\s*object", 0.85, "Object tag injection"),
            (r"<\s*embed", 0.85, "Embed tag injection"),
            (r"expression\s*\(", 0.90, "CSS expression"),
            (r"url\s*\(\s*['\"]?\s*data:", 0.88, "Data URL injection"),
        ]

        # Path traversal patterns
        self.path_traversal_patterns: List[Tuple[str, float, str]] = [
            (r"\.\./", 0.90, "Directory traversal"),
            (r"\.\.\\", 0.90, "Windows directory traversal"),
            (r"/etc/passwd", 0.95, "Unix passwd file access"),
            (r"/etc/shadow", 0.95, "Unix shadow file access"),
            (r"c:\\windows", 0.90, "Windows system path"),
        ]

        # Command injection patterns
        self.command_patterns: List[Tuple[str, float, str]] = [
            (r";\s*\w+\s+", 0.75, "Command chaining (semicolon)"),
            (r"\|\s*\w+", 0.75, "Command piping"),
            (r"&&\s*\w+", 0.75, "Command chaining (AND)"),
            (r"\$\(.*\)", 0.80, "Command substitution"),
            (r"`.*`", 0.80, "Backtick command execution"),
        ]

        # Whitelist patterns - things that LOOK like attacks but aren't
        # These override attack detection
        self.whitelist_patterns: List[str] = [
            # Maritime equipment that contains "OR" or other SQL keywords
            r"\b(motor|sensor|selector|operator|governor|separator)\b",
            # Work order abbreviations
            r"\bwo\s*#?\d",
            # Maritime locations
            r"\b(port|starboard)\b",
            # Common phrases with "or"
            r"\bwork\s+order\b",
            r"\breport\b",
            r"\bexport\b",
            r"\bsupport\b",
        ]

    def check(self, query: str) -> SecurityCheckResult:
        """
        Check a query for security threats.

        Args:
            query: User's input query

        Returns:
            SecurityCheckResult indicating if blocked and why
        """
        if not query or not query.strip():
            return SecurityCheckResult(
                blocked=False,
                threat_type=ThreatType.NONE,
                reason="Empty query",
                confidence=1.0
            )

        query_lower = query.lower()

        # Check whitelist first - legitimate queries that might trigger false positives
        for pattern in self.whitelist_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                # Still check for obvious attacks even with whitelist match
                if not self._is_obvious_attack(query):
                    return SecurityCheckResult(
                        blocked=False,
                        threat_type=ThreatType.NONE,
                        reason="Whitelisted pattern matched",
                        confidence=0.8
                    )

        # Check SQL injection patterns
        for pattern, confidence, description in self.sql_injection_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return SecurityCheckResult(
                    blocked=True,
                    threat_type=ThreatType.SQL_INJECTION,
                    reason=f"SQL injection detected: {description}",
                    matched_pattern=pattern,
                    confidence=confidence
                )

        # Check XSS patterns
        for pattern, confidence, description in self.xss_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return SecurityCheckResult(
                    blocked=True,
                    threat_type=ThreatType.XSS,
                    reason=f"XSS attempt detected: {description}",
                    matched_pattern=pattern,
                    confidence=confidence
                )

        # Check path traversal
        for pattern, confidence, description in self.path_traversal_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return SecurityCheckResult(
                    blocked=True,
                    threat_type=ThreatType.PATH_TRAVERSAL,
                    reason=f"Path traversal detected: {description}",
                    matched_pattern=pattern,
                    confidence=confidence
                )

        # Check command injection (lower priority - more false positives)
        for pattern, confidence, description in self.command_patterns:
            if re.search(pattern, query) and self._looks_like_command(query):
                return SecurityCheckResult(
                    blocked=True,
                    threat_type=ThreatType.COMMAND_INJECTION,
                    reason=f"Command injection detected: {description}",
                    matched_pattern=pattern,
                    confidence=confidence
                )

        # No threats detected
        return SecurityCheckResult(
            blocked=False,
            threat_type=ThreatType.NONE,
            reason="No security threats detected",
            confidence=0.95
        )

    def _is_obvious_attack(self, query: str) -> bool:
        """Check for obvious attacks that override whitelist"""
        obvious_patterns = [
            r"\bUNION\b.*\bSELECT\b",
            r"\bSELECT\b.*\bFROM\b.*\bWHERE\b",
            r"'\s*OR\s+'",
            r";\s*(DROP|DELETE|UPDATE|INSERT)",
            # Catch "word OR 1=1" patterns where word could be legitimate
            r"\bOR\s+\d+\s*=\s*\d+",  # OR 1=1
            r"\bOR\s+'\d+'\s*=\s*'\d+'",  # OR '1'='1'
            r"--\s*$",  # Trailing comment
            r";\s*--",  # Statement terminator with comment
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in obvious_patterns)

    def _looks_like_command(self, query: str) -> bool:
        """Check if query looks like a shell command vs legitimate text"""
        command_indicators = [
            r"^\s*(ls|cat|rm|mv|cp|chmod|wget|curl)\s",
            r"\b(bash|sh|cmd|powershell)\b",
            r"/bin/",
            r"\.exe\b",
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in command_indicators)


# Singleton instance
_gate_instance = None

def get_security_gate() -> SecurityGate:
    """Get or create singleton security gate instance"""
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = SecurityGate()
    return _gate_instance


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    gate = SecurityGate()

    # Test cases: (query, should_be_blocked, expected_threat_type)
    test_cases = [
        # SQL Injection - should block
        ("SELECT * FROM users", True, ThreatType.SQL_INJECTION),
        ("SELECT * FROM pms_parts", True, ThreatType.SQL_INJECTION),
        ("1' OR '1'='1", True, ThreatType.SQL_INJECTION),
        ("name UNION SELECT password FROM users", True, ThreatType.SQL_INJECTION),
        ("name UNION ALL SELECT * FROM users", True, ThreatType.SQL_INJECTION),
        ("1; DROP TABLE parts--", True, ThreatType.SQL_INJECTION),
        ("1' ORDER BY 100--", True, ThreatType.SQL_INJECTION),
        ("1' UNION SELECT NULL--", True, ThreatType.SQL_INJECTION),
        ("/**/UNION/**/SELECT/**/password/**/FROM/**/users", True, ThreatType.SQL_INJECTION),
        ("' OR ''='", True, ThreatType.SQL_INJECTION),
        ("admin'--", True, ThreatType.SQL_INJECTION),
        ("1; UPDATE pms_parts SET name='hacked'", True, ThreatType.SQL_INJECTION),

        # XSS - should block
        ("<script>alert('xss')</script>", True, ThreatType.XSS),
        ("javascript:alert(1)", True, ThreatType.XSS),
        ("<img src=x onerror=alert(1)>", True, ThreatType.XSS),

        # Path traversal - should block
        ("../../../etc/passwd", True, ThreatType.PATH_TRAVERSAL),
        ("..\\..\\windows\\system32", True, ThreatType.PATH_TRAVERSAL),

        # Legitimate queries - should NOT block
        ("show equipment ME-S-001", False, ThreatType.NONE),
        ("pending work orders", False, ThreatType.NONE),
        ("diagnose E047", False, ThreatType.NONE),
        ("main engine port side", False, ThreatType.NONE),
        ("oil filter for generator", False, ThreatType.NONE),
        ("show motor status", False, ThreatType.NONE),  # Contains "or" in "motor"
        ("export work orders", False, ThreatType.NONE),  # Contains "or" in "export"
        ("sensor reading", False, ThreatType.NONE),  # Contains "or" in "sensor"
        ("starboard thruster", False, ThreatType.NONE),  # Contains "or" in "starboard"
        ("support documentation", False, ThreatType.NONE),  # Contains "or" in "support"
        ("governor malfunction", False, ThreatType.NONE),  # Contains "or" in "governor"
    ]

    print("=" * 70)
    print("SECURITY GATE TESTS")
    print("=" * 70)

    passed = 0
    failed = 0

    for query, should_block, expected_threat in test_cases:
        result = gate.check(query)

        block_match = result.blocked == should_block
        threat_match = result.threat_type == expected_threat if should_block else True

        all_match = block_match and threat_match

        if all_match:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        print(f"\n{status}: '{query[:50]}{'...' if len(query) > 50 else ''}'")
        print(f"  Expected: blocked={should_block}, threat={expected_threat.value}")
        print(f"  Got:      blocked={result.blocked}, threat={result.threat_type.value}")
        if result.blocked:
            print(f"  Reason: {result.reason}")

    print(f"\n{'=' * 70}")
    print(f"Results: {passed}/{len(test_cases)} passed ({100*passed/len(test_cases):.1f}%)")
    print(f"{'=' * 70}")

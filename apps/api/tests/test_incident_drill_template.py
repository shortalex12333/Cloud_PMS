"""
Tests for incident drill template validation and dry-run simulation.

Validates:
- Template placeholders are complete and well-formed
- A dry-run series of admin actions produces expected artifact list
- Drill phases are properly sequenced
- Success criteria are measurable
"""

import pytest
import re
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any


# Path to the incident drill template
TEMPLATE_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "compliance" / "INCIDENT_DRILL_TEMPLATE.md"


class TestIncidentDrillTemplatePlaceholders:
    """Validate template placeholders are complete and well-formed."""

    def test_template_exists(self):
        """Template file must exist."""
        assert TEMPLATE_PATH.exists(), f"Template not found at {TEMPLATE_PATH}"

    def test_template_has_required_sections(self):
        """Template must have all required sections."""
        content = TEMPLATE_PATH.read_text()

        required_sections = [
            "# Security Incident Response Drill Template",
            "## Drill Information",
            "## 2. Drill Scenario",
            "## 4. Drill Steps",
            "### Phase 1: Detection",
            "### Phase 2: Containment",
            "### Phase 3: Investigation",
            "### Phase 4: Resolution",
            "### Phase 5: Post-Drill",
            "## 6. Success Criteria",
            "## 5. Artifacts Checklist",
        ]

        for section in required_sections:
            assert section in content, f"Missing required section: {section}"

    def test_template_has_placeholder_fields(self):
        """Template must have fillable placeholder fields."""
        content = TEMPLATE_PATH.read_text()

        # Placeholders should be in format [PLACEHOLDER] or bracketed values
        placeholder_patterns = [
            r"\[YYYY-MM-DD\]",           # Date placeholder
            r"\[NAME\]",                  # Name placeholder
            r"\[Scenario Name\]",         # Scenario placeholder
            r"\[Expected Duration\]",     # Duration placeholder
        ]

        for pattern in placeholder_patterns:
            assert re.search(pattern, content), f"Missing placeholder: {pattern}"

    def test_template_has_command_examples(self):
        """Template must include command examples for drill actions."""
        content = TEMPLATE_PATH.read_text()
        content_lower = content.lower()

        # Should have admin commands for incident mode (via API or DB)
        assert "/admin/incident/enable" in content or "enable incident mode" in content_lower, \
            "Missing incident mode enable command"
        assert "/admin/incident/disable" in content or "disable incident mode" in content_lower, \
            "Missing incident mode disable command"

    def test_template_has_timing_guidance(self):
        """Template must have timing guidance for each phase."""
        content = TEMPLATE_PATH.read_text()

        # Should have time estimates or SLO references
        time_patterns = [
            r"\d+\s*(min|minute|hour|sec)",
            r"T\+\d+",
            r"SLO",
            r"target.*time",
        ]

        found_timing = any(re.search(p, content, re.IGNORECASE) for p in time_patterns)
        assert found_timing, "Template should include timing guidance"

    def test_template_has_roles_defined(self):
        """Template must define participant roles."""
        content = TEMPLATE_PATH.read_text()

        role_indicators = [
            "incident commander",
            "security analyst",
            "platform engineer",
            "communications lead",
            "scribe",
            "coordinator",
        ]

        found_roles = sum(1 for role in role_indicators if role.lower() in content.lower())
        assert found_roles >= 2, "Template should define at least 2 participant roles"


class TestIncidentDrillDryRun:
    """Test that dry-run drill produces expected artifacts."""

    @pytest.fixture
    def mock_db_client(self):
        """Create mock database client for dry-run."""
        client = MagicMock()
        client.table = MagicMock(return_value=client)
        client.select = MagicMock(return_value=client)
        client.insert = MagicMock(return_value=client)
        client.update = MagicMock(return_value=client)
        client.eq = MagicMock(return_value=client)
        client.execute = MagicMock(return_value=MagicMock(data=[]))
        return client

    @pytest.fixture
    def drill_context(self) -> Dict[str, Any]:
        """Standard drill context."""
        return {
            "drill_id": "DRILL-2024-Q1-001",
            "yacht_id": "yacht-drill-test",
            "facilitator_id": "user-facilitator",
            "start_time": datetime.utcnow(),
            "scenario_type": "credential_compromise",
        }

    def test_drill_produces_detection_artifacts(self, drill_context):
        """Detection phase should produce alert/detection artifacts."""
        expected_artifacts = [
            "alert_timestamp",
            "detection_source",
            "initial_severity",
            "affected_scope",
        ]

        # Simulate detection phase output
        detection_output = simulate_detection_phase(drill_context)

        for artifact in expected_artifacts:
            assert artifact in detection_output, f"Missing detection artifact: {artifact}"

    def test_drill_produces_containment_artifacts(self, drill_context):
        """Containment phase should produce containment action artifacts."""
        expected_artifacts = [
            "incident_mode_enabled_at",
            "containment_actions",
            "affected_users_count",
            "sessions_terminated",
        ]

        # Simulate containment phase output
        containment_output = simulate_containment_phase(drill_context)

        for artifact in expected_artifacts:
            assert artifact in containment_output, f"Missing containment artifact: {artifact}"

    def test_drill_produces_investigation_artifacts(self, drill_context):
        """Investigation phase should produce audit trail artifacts."""
        expected_artifacts = [
            "audit_records_reviewed",
            "timeline_reconstructed",
            "root_cause_hypothesis",
            "evidence_preserved",
        ]

        # Simulate investigation phase output
        investigation_output = simulate_investigation_phase(drill_context)

        for artifact in expected_artifacts:
            assert artifact in investigation_output, f"Missing investigation artifact: {artifact}"

    def test_drill_produces_resolution_artifacts(self, drill_context):
        """Resolution phase should produce remediation artifacts."""
        expected_artifacts = [
            "incident_mode_disabled_at",
            "remediation_actions",
            "verification_checks",
            "all_clear_timestamp",
        ]

        # Simulate resolution phase output
        resolution_output = simulate_resolution_phase(drill_context)

        for artifact in expected_artifacts:
            assert artifact in resolution_output, f"Missing resolution artifact: {artifact}"

    def test_drill_produces_postmortem_artifacts(self, drill_context):
        """Post-drill phase should produce postmortem artifacts."""
        expected_artifacts = [
            "lessons_learned",
            "process_improvements",
            "drill_duration",
            "success_criteria_met",
        ]

        # Simulate post-drill phase output
        postmortem_output = simulate_postmortem_phase(drill_context)

        for artifact in expected_artifacts:
            assert artifact in postmortem_output, f"Missing postmortem artifact: {artifact}"

    def test_full_drill_produces_complete_artifact_bundle(self, drill_context):
        """Full drill should produce complete artifact bundle."""
        # Run full drill simulation
        bundle = simulate_full_drill(drill_context)

        # Check bundle structure
        assert "drill_id" in bundle
        assert "phases" in bundle
        assert len(bundle["phases"]) == 5

        # Check all phases present
        phase_names = [p["name"] for p in bundle["phases"]]
        assert "detection" in phase_names
        assert "containment" in phase_names
        assert "investigation" in phase_names
        assert "resolution" in phase_names
        assert "post_drill" in phase_names

        # Check success criteria evaluation
        assert "success_criteria" in bundle
        assert "overall_success" in bundle

    def test_drill_timing_is_recorded(self, drill_context):
        """Drill should record timing for each phase."""
        bundle = simulate_full_drill(drill_context)

        for phase in bundle["phases"]:
            assert "start_time" in phase
            assert "end_time" in phase
            assert "duration_seconds" in phase

    def test_drill_captures_action_sequence(self, drill_context):
        """Drill should capture the sequence of admin actions taken."""
        bundle = simulate_full_drill(drill_context)

        # Should have action log
        assert "action_log" in bundle

        # Key actions should be logged
        action_types = [a["action"] for a in bundle["action_log"]]
        assert "admin_enable_incident_mode" in action_types
        assert "admin_disable_incident_mode" in action_types


class TestDrillSuccessCriteria:
    """Test success criteria evaluation."""

    def test_containment_time_criterion(self):
        """Containment should happen within target time."""
        # Target: containment within 15 minutes of detection
        target_minutes = 15

        # Simulate good case
        detection_time = datetime.utcnow()
        containment_time = detection_time + timedelta(minutes=10)

        result = evaluate_containment_time(detection_time, containment_time, target_minutes)
        assert result["passed"] is True
        assert result["actual_minutes"] == 10

        # Simulate bad case
        containment_time_late = detection_time + timedelta(minutes=20)
        result_late = evaluate_containment_time(detection_time, containment_time_late, target_minutes)
        assert result_late["passed"] is False

    def test_incident_mode_activation_criterion(self):
        """Incident mode must be activated during drill."""
        # Good case: incident mode was activated
        actions = [
            {"action": "admin_enable_incident_mode", "timestamp": datetime.utcnow()},
            {"action": "admin_disable_incident_mode", "timestamp": datetime.utcnow()},
        ]

        result = evaluate_incident_mode_used(actions)
        assert result["passed"] is True

        # Bad case: incident mode never activated
        actions_missing = [
            {"action": "view_audit_log", "timestamp": datetime.utcnow()},
        ]

        result_missing = evaluate_incident_mode_used(actions_missing)
        assert result_missing["passed"] is False

    def test_audit_review_criterion(self):
        """Audit records must be reviewed during investigation."""
        # Good case: audit records reviewed
        investigation_data = {
            "audit_records_reviewed": 50,
            "timeline_reconstructed": True,
        }

        result = evaluate_audit_review(investigation_data)
        assert result["passed"] is True

        # Bad case: no audit review
        investigation_data_missing = {
            "audit_records_reviewed": 0,
            "timeline_reconstructed": False,
        }

        result_missing = evaluate_audit_review(investigation_data_missing)
        assert result_missing["passed"] is False

    def test_lessons_learned_criterion(self):
        """Lessons learned must be documented."""
        # Good case: lessons documented
        postmortem = {
            "lessons_learned": [
                "Need faster alert escalation",
                "Improve incident runbook",
            ],
            "process_improvements": [
                "Add PagerDuty integration",
            ],
        }

        result = evaluate_lessons_learned(postmortem)
        assert result["passed"] is True

        # Bad case: no lessons documented
        postmortem_empty = {
            "lessons_learned": [],
            "process_improvements": [],
        }

        result_empty = evaluate_lessons_learned(postmortem_empty)
        assert result_empty["passed"] is False


# --- Drill simulation helpers ---

def simulate_detection_phase(context: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate detection phase and return artifacts."""
    return {
        "alert_timestamp": context["start_time"].isoformat(),
        "detection_source": "security_monitoring",
        "initial_severity": "high",
        "affected_scope": context["yacht_id"],
        "alert_id": f"ALERT-{context['drill_id']}",
    }


def simulate_containment_phase(context: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate containment phase and return artifacts."""
    return {
        "incident_mode_enabled_at": (context["start_time"] + timedelta(minutes=5)).isoformat(),
        "containment_actions": [
            "enabled_incident_mode",
            "blocked_external_api_access",
            "terminated_active_sessions",
        ],
        "affected_users_count": 3,
        "sessions_terminated": 5,
    }


def simulate_investigation_phase(context: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate investigation phase and return artifacts."""
    return {
        "audit_records_reviewed": 127,
        "timeline_reconstructed": True,
        "root_cause_hypothesis": "Compromised API token",
        "evidence_preserved": True,
        "suspicious_actions": [],
    }


def simulate_resolution_phase(context: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate resolution phase and return artifacts."""
    return {
        "incident_mode_disabled_at": (context["start_time"] + timedelta(hours=1)).isoformat(),
        "remediation_actions": [
            "rotated_api_tokens",
            "revoked_suspicious_sessions",
            "updated_access_policies",
        ],
        "verification_checks": [
            "confirmed_no_data_exfiltration",
            "verified_system_integrity",
        ],
        "all_clear_timestamp": (context["start_time"] + timedelta(hours=1, minutes=15)).isoformat(),
    }


def simulate_postmortem_phase(context: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate post-drill phase and return artifacts."""
    return {
        "lessons_learned": [
            "Detection was fast but containment could be faster",
            "Need clearer escalation path",
        ],
        "process_improvements": [
            "Add automated containment trigger",
            "Create pre-approved response playbook",
        ],
        "drill_duration": 75,  # minutes
        "success_criteria_met": True,
        "participants_feedback": "positive",
    }


def simulate_full_drill(context: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate complete drill and return artifact bundle."""
    start = context["start_time"]

    phases = [
        {
            "name": "detection",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=5)).isoformat(),
            "duration_seconds": 300,
            "artifacts": simulate_detection_phase(context),
        },
        {
            "name": "containment",
            "start_time": (start + timedelta(minutes=5)).isoformat(),
            "end_time": (start + timedelta(minutes=15)).isoformat(),
            "duration_seconds": 600,
            "artifacts": simulate_containment_phase(context),
        },
        {
            "name": "investigation",
            "start_time": (start + timedelta(minutes=15)).isoformat(),
            "end_time": (start + timedelta(minutes=45)).isoformat(),
            "duration_seconds": 1800,
            "artifacts": simulate_investigation_phase(context),
        },
        {
            "name": "resolution",
            "start_time": (start + timedelta(minutes=45)).isoformat(),
            "end_time": (start + timedelta(minutes=60)).isoformat(),
            "duration_seconds": 900,
            "artifacts": simulate_resolution_phase(context),
        },
        {
            "name": "post_drill",
            "start_time": (start + timedelta(minutes=60)).isoformat(),
            "end_time": (start + timedelta(minutes=75)).isoformat(),
            "duration_seconds": 900,
            "artifacts": simulate_postmortem_phase(context),
        },
    ]

    action_log = [
        {"action": "drill_started", "timestamp": start.isoformat(), "actor": context["facilitator_id"]},
        {"action": "admin_enable_incident_mode", "timestamp": (start + timedelta(minutes=5)).isoformat(), "actor": context["facilitator_id"]},
        {"action": "session_termination", "timestamp": (start + timedelta(minutes=6)).isoformat(), "actor": context["facilitator_id"]},
        {"action": "audit_export", "timestamp": (start + timedelta(minutes=20)).isoformat(), "actor": context["facilitator_id"]},
        {"action": "admin_disable_incident_mode", "timestamp": (start + timedelta(minutes=60)).isoformat(), "actor": context["facilitator_id"]},
        {"action": "drill_completed", "timestamp": (start + timedelta(minutes=75)).isoformat(), "actor": context["facilitator_id"]},
    ]

    success_criteria = {
        "containment_within_15min": True,
        "incident_mode_activated": True,
        "audit_reviewed": True,
        "lessons_documented": True,
    }

    return {
        "drill_id": context["drill_id"],
        "yacht_id": context["yacht_id"],
        "scenario_type": context["scenario_type"],
        "phases": phases,
        "action_log": action_log,
        "success_criteria": success_criteria,
        "overall_success": all(success_criteria.values()),
        "total_duration_minutes": 75,
    }


def evaluate_containment_time(
    detection_time: datetime,
    containment_time: datetime,
    target_minutes: int,
) -> Dict[str, Any]:
    """Evaluate if containment happened within target time."""
    delta = containment_time - detection_time
    actual_minutes = delta.total_seconds() / 60

    return {
        "criterion": "containment_time",
        "target_minutes": target_minutes,
        "actual_minutes": actual_minutes,
        "passed": actual_minutes <= target_minutes,
    }


def evaluate_incident_mode_used(actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate if incident mode was activated during drill."""
    action_types = [a["action"] for a in actions]
    activated = "admin_enable_incident_mode" in action_types

    return {
        "criterion": "incident_mode_activated",
        "passed": activated,
    }


def evaluate_audit_review(investigation_data: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate if audit records were reviewed."""
    reviewed = investigation_data.get("audit_records_reviewed", 0) > 0
    timeline = investigation_data.get("timeline_reconstructed", False)

    return {
        "criterion": "audit_reviewed",
        "records_reviewed": investigation_data.get("audit_records_reviewed", 0),
        "timeline_reconstructed": timeline,
        "passed": reviewed and timeline,
    }


def evaluate_lessons_learned(postmortem: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate if lessons learned were documented."""
    lessons = postmortem.get("lessons_learned", [])
    improvements = postmortem.get("process_improvements", [])

    return {
        "criterion": "lessons_documented",
        "lessons_count": len(lessons),
        "improvements_count": len(improvements),
        "passed": len(lessons) > 0 or len(improvements) > 0,
    }

#!/usr/bin/env python3
"""
Lens Ops Template Generator

Instantiates the Lens Ops Template for a specific lens.

Usage:
    python3 create_lens_ops_template.py \\
        --lens-id faults \\
        --domain faults \\
        --feature-flags FAULT_LENS_V1_ENABLED,FAULT_LENS_SUGGESTIONS_ENABLED \\
        --roles crew,chief_engineer,chief_officer,captain,manager \\
        --output-dir .

Generates:
- tools/ops/monitors/{lens_id}_health_worker.py
- tests/ci/{lens_id}_signed_flow_acceptance.py
- tests/stress/{lens_id}_actions_endpoints.py
- .github/workflows/{lens_id}-staging-acceptance.yml
- .github/workflows/{lens_id}-stress.yml
- docs/pipeline/{lens_id.upper()}_FEATURE_FLAGS.md

Purpose:
Replace ad-hoc canary scripts with production-grade, repeatable infrastructure.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List

# Template directory
# Navigate from tools/ops/monitors/ to project root, then to templates
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "docs" / "pipeline" / "templates" / "lens_ops"


def load_template(template_name: str) -> str:
    """Load template file content."""
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text()


def instantiate_template(template: str, replacements: Dict[str, str]) -> str:
    """Replace placeholders in template with actual values."""
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(f"{{{placeholder}}}", value)
    return result


def write_file(output_path: Path, content: str):
    """Write content to file, creating parent directories if needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    print(f"✅ Created: {output_path}")


def generate_health_worker(lens_id: str, domain: str, feature_flags: List[str], output_dir: Path, config: Dict[str, str]):
    """Generate health worker script."""
    template = load_template("health_worker_template.py")

    # Build feature flags list for template
    flags_code = "\n    ".join([f'"{flag}",' for flag in feature_flags])

    replacements = {
        "LENS_ID": lens_id,
        "DOMAIN": domain,
        "FEATURE_FLAG_1": feature_flags[0] if len(feature_flags) > 0 else "LENS_V1_ENABLED",
        "FEATURE_FLAG_2": feature_flags[1] if len(feature_flags) > 1 else "LENS_SUGGESTIONS_ENABLED",
        "FEATURE_FLAG_3": feature_flags[2] if len(feature_flags) > 2 else "LENS_SIGNED_ACTIONS_ENABLED",
        **config
    }

    content = instantiate_template(template, replacements)
    output_path = output_dir / "tools" / "ops" / "monitors" / f"{lens_id}_health_worker.py"
    write_file(output_path, content)


def generate_acceptance_test(lens_id: str, domain: str, output_dir: Path, config: Dict[str, str]):
    """Generate acceptance test script."""
    template = load_template("acceptance_test_template.py")

    replacements = {
        "LENS_ID": lens_id,
        "DOMAIN": domain,
        **config
    }

    content = instantiate_template(template, replacements)
    output_path = output_dir / "tests" / "ci" / f"{lens_id}_signed_flow_acceptance.py"
    write_file(output_path, content)


def generate_stress_test(lens_id: str, domain: str, output_dir: Path, config: Dict[str, str]):
    """Generate stress test script."""
    template = load_template("stress_test_template.py")

    replacements = {
        "LENS_ID": lens_id,
        "DOMAIN": domain,
        **config
    }

    content = instantiate_template(template, replacements)
    output_path = output_dir / "tests" / "stress" / f"{lens_id}_actions_endpoints.py"
    write_file(output_path, content)


def generate_ci_workflows(lens_id: str, output_dir: Path):
    """Generate GitHub Actions workflow files."""

    # Acceptance workflow
    acceptance_workflow = f"""name: {lens_id} - Staging Acceptance

on:
  push:
    branches: [main]
    paths:
      - 'apps/api/handlers/{lens_id}_*.py'
      - 'apps/api/routes/{lens_id}_*.py'
      - 'tests/ci/{lens_id}_*.py'
  workflow_dispatch:

jobs:
  acceptance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run Acceptance Tests
        env:
          STAGING_API_URL: https://pipeline-core.int.celeste7.ai
          STAGING_JWT_SECRET: ${{{{ secrets.STAGING_JWT_SECRET }}}}
          SUPABASE_SERVICE_KEY: ${{{{ secrets.SUPABASE_SERVICE_KEY }}}}
        run: python3 tests/ci/{lens_id}_signed_flow_acceptance.py
      - name: Upload Evidence
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: {lens_id}-acceptance-evidence
          path: verification_handoff/phase*/
"""

    acceptance_path = output_dir / ".github" / "workflows" / f"{lens_id}-staging-acceptance.yml"
    write_file(acceptance_path, acceptance_workflow)

    # Stress workflow
    stress_workflow = f"""name: {lens_id} - Stress Testing

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily
  workflow_dispatch:

jobs:
  stress:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run Stress Tests
        env:
          STAGING_API_URL: https://pipeline-core.int.celeste7.ai
          STAGING_JWT_SECRET: ${{{{ secrets.STAGING_JWT_SECRET }}}}
        run: python3 tests/stress/{lens_id}_actions_endpoints.py
      - name: Upload Results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: {lens_id}-stress-results
          path: verification_handoff/phase*/*STRESS*.md
"""

    stress_path = output_dir / ".github" / "workflows" / f"{lens_id}-stress.yml"
    write_file(stress_path, stress_workflow)


def generate_feature_flags_doc(lens_id: str, domain: str, feature_flags: List[str], output_dir: Path):
    """Generate feature flags documentation."""

    # Build flags section
    flags_section = ""
    for i, flag in enumerate(feature_flags, 1):
        flag_desc = flag.replace(f"{lens_id.upper()}_", "").replace("_", " ").title()
        flags_section += f"""
### {i}. `{flag}`

**Description:** {flag_desc}

**Default:** `false` (OFF on main branch)

**Type:** Boolean (environment variable)

**Usage:**
```python
from integrations.feature_flags import {flag}

if not {flag}:
    raise HTTPException(
        status_code=503,
        detail={{
            "status": "error",
            "error_code": "FEATURE_DISABLED",
            "message": "{lens_id.title()} feature disabled (canary flag off)"
        }}
    )
```

**Behavior:**
- `true`: Feature enabled
- `false`: Returns 503 FEATURE_DISABLED

---
"""

    doc_content = f"""# {lens_id.title()} Feature Flags

**Purpose:** Gradual rollout and fail-closed behavior for {lens_id.title()} lens features

**Philosophy:** All new features default to **OFF** on main branch. Features are enabled progressively:
1. **Local development:** Manual toggle for testing
2. **Staging canary:** Enable for one test yacht
3. **Staging full:** Enable for all staging yachts
4. **Production canary:** Enable for 10% of traffic
5. **Production rollout:** Gradually increase to 100%

**Fail-Closed Behavior:** When a feature flag is OFF, the system returns `503 FEATURE_DISABLED` instead of attempting the operation.

---

## Feature Flags

{flags_section}

## Environment Variables

Set these in Render dashboard (staging) or production environment:

```bash
# {lens_id.title()} Flags
{chr(10).join([f'{flag}=false  # Default OFF' for flag in feature_flags])}
```

**Staging Canary Configuration:**

```bash
# Enable for canary testing
{chr(10).join([f'{flag}=true' for flag in feature_flags])}
```

---

## Toggle Procedures

### Enable {lens_id.title()} (Canary)

1. **Render Dashboard → Environment**
   ```
{chr(10).join([f'   {flag}=true' for flag in feature_flags])}
   ```

2. **Trigger Deployment**
   ```bash
   curl -X POST "https://api.render.com/deploy/srv-YOUR-SERVICE-ID?key=YOUR-KEY"
   ```

3. **Verify Deployment**
   ```bash
   curl -s https://pipeline-core.int.celeste7.ai/v1/actions/health | jq '.status'
   # Expected: "healthy"
   ```

4. **Test Feature Availability**
   ```bash
   curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/suggestions \\
     -H "Authorization: Bearer {{JWT}}" \\
     -H "Content-Type: application/json" \\
     -d '{{"domain": "{domain}"}}'

   # Should return 200 with action suggestions (not 503)
   ```

---

### Disable {lens_id.title()} (Rollback)

**Scenario:** Canary shows errors or performance issues.

1. **Render Dashboard → Environment**
   ```
   {feature_flags[0]}=false
   ```

2. **Trigger Deployment** (same as above)

3. **Verify Rollback**
   ```bash
   # Expected: 503 FEATURE_DISABLED
   ```

---

## Monitoring

### Feature Flag Status (Startup Logs)

When the service starts, all feature flags are logged:

```
INFO:integrations.feature_flags:[FeatureFlags] {feature_flags[0]}=True
{chr(10).join([f'INFO:integrations.feature_flags:[FeatureFlags] {flag}=True' for flag in feature_flags[1:]])}
```

**Check Logs:**
```bash
# Render dashboard → Logs tab
# Search for: [FeatureFlags]
```

---

## Current Status

**{lens_id.title()} Flags (as of {import_date()}):**

| Flag | Status | Ready for Canary |
|------|--------|------------------|
{chr(10).join([f'| `{flag}` | OFF (main) | ⏳ Not tested |' for flag in feature_flags])}

**Recommended Canary Configuration:**
```bash
{chr(10).join([f'{flag}=true' for flag in feature_flags])}
```

**Next Steps:**
1. Enable canary flags in staging
2. Monitor for 24h (0×500, P99 latency)
3. Expand to staging full
4. Enable production canary (10%)
5. Gradual rollout to 100%
"""

    doc_path = output_dir / "docs" / "pipeline" / f"{lens_id.upper()}_FEATURE_FLAGS.md"
    write_file(doc_path, doc_content)


def import_date():
    """Get current date for documentation."""
    from datetime import date
    return date.today().isoformat()


def main():
    parser = argparse.ArgumentParser(description="Generate Lens Ops Template for a specific lens")
    parser.add_argument("--lens-id", required=True, help="Lens identifier (e.g., faults, certificates)")
    parser.add_argument("--domain", required=True, help="Action router domain (e.g., faults)")
    parser.add_argument("--feature-flags", required=True, help="Comma-separated feature flags")
    parser.add_argument("--roles", required=True, help="Comma-separated canon roles")
    parser.add_argument("--output-dir", default=".", help="Output directory (default: current directory)")
    parser.add_argument("--yacht-id", default="85fe1119-b04c-41ac-80f1-829d23322598", help="Test yacht ID")
    parser.add_argument("--hod-user-id", default="05a488fd-e099-4d18-bf86-d87afba4fcdf", help="HOD user ID")
    parser.add_argument("--crew-user-id", default="57e82f78-0a2d-4a7c-a428-6287621d06c5", help="CREW user ID")
    parser.add_argument("--captain-user-id", default="c2f980b6-9a69-4953-bc33-3324f08602fe", help="CAPTAIN user ID")
    parser.add_argument("--test-entity-id", default="00000000-0000-0000-0000-000000000001", help="Test entity ID")
    parser.add_argument("--signed-action", default="create_work_order_from_fault", help="SIGNED action name")
    parser.add_argument("--entity-type", default="work_order", help="Entity type created by SIGNED action")
    parser.add_argument("--entity-id-key", default="fault_id", help="Payload key for entity ID")
    parser.add_argument("--read-action", default="view_fault_detail", help="READ action for stress testing")

    args = parser.parse_args()

    lens_id = args.lens_id.lower()
    domain = args.domain.lower()
    feature_flags = [f.strip() for f in args.feature_flags.split(",")]
    roles = [r.strip() for r in args.roles.split(",")]
    output_dir = Path(args.output_dir).resolve()

    # Configuration dict
    config = {
        "YACHT_ID": args.yacht_id,
        "TEST_USER_ID": args.hod_user_id,
        "TEST_USER_EMAIL": "hod.test@alex-short.com",
        "HOD_USER_ID": args.hod_user_id,
        "CREW_USER_ID": args.crew_user_id,
        "CAPTAIN_USER_ID": args.captain_user_id,
        "TEST_ENTITY_ID": args.test_entity_id,
        "SIGNED_ACTION": args.signed_action,
        "ENTITY_TYPE": args.entity_type,
        "ENTITY_ID_KEY": args.entity_id_key,
        "READ_ACTION": args.read_action,
    }

    print("=" * 80)
    print("LENS OPS TEMPLATE GENERATOR")
    print("=" * 80)
    print(f"\nLens ID: {lens_id}")
    print(f"Domain: {domain}")
    print(f"Feature Flags: {', '.join(feature_flags)}")
    print(f"Roles: {', '.join(roles)}")
    print(f"Output Directory: {output_dir}")
    print()

    # Generate files
    print("Generating files...")
    print("-" * 80)

    try:
        generate_health_worker(lens_id, domain, feature_flags, output_dir, config)
        generate_acceptance_test(lens_id, domain, output_dir, config)
        generate_stress_test(lens_id, domain, output_dir, config)
        generate_ci_workflows(lens_id, output_dir)
        generate_feature_flags_doc(lens_id, domain, feature_flags, output_dir)

        print()
        print("=" * 80)
        print("✅ GENERATION COMPLETE")
        print("=" * 80)
        print()
        print("Generated files:")
        print(f"  - tools/ops/monitors/{lens_id}_health_worker.py")
        print(f"  - tests/ci/{lens_id}_signed_flow_acceptance.py")
        print(f"  - tests/stress/{lens_id}_actions_endpoints.py")
        print(f"  - .github/workflows/{lens_id}-staging-acceptance.yml")
        print(f"  - .github/workflows/{lens_id}-stress.yml")
        print(f"  - docs/pipeline/{lens_id.upper()}_FEATURE_FLAGS.md")
        print()
        print("Next steps:")
        print("  1. Review generated files")
        print("  2. Update test data (entity IDs, user IDs) if needed")
        print("  3. Deploy health worker to Render")
        print("  4. Enable CI workflows in GitHub")
        print("  5. Run acceptance tests to verify")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

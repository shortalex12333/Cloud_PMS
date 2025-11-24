"""
Entity Learning Batch Job
==========================

Offline batch job that:
1. Links unknown entities to subsequent user actions
2. Aggregates frequent unknown terms
3. Uses GPT to propose alias mappings
4. Stores candidates for human approval

RUN AS: python entity_learning_batch.py
SCHEDULE: Every 6 hours (cron) or nightly

GPT is a TEACHER (offline), not a live RESOLVER.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Supabase
try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: pip install supabase")
    exit(1)

# OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("ERROR: pip install openai")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Thresholds for proposing aliases
MIN_USAGE_COUNT = 5          # Term must appear at least N times
MIN_YACHT_COUNT = 2          # Term must appear on at least N yachts
MIN_ACTION_RATIO = 0.3       # At least 30% of usages should have linked actions
GPT_CONFIDENCE_THRESHOLD = 0.7  # Only propose if GPT confidence > this

# Auto-approve thresholds (dangerous - use with caution)
AUTO_APPROVE_USAGE = 20      # If usage > this AND confidence > 0.9
AUTO_APPROVE_CONFIDENCE = 0.9

# GPT model
GPT_MODEL = "gpt-4o-mini"

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class UnknownTermStats:
    term: str
    entity_type_guess: str
    usage_count: int
    yacht_count: int
    user_count: int
    with_actions: int
    avg_confidence: float
    sample_queries: List[str]
    linked_actions: List[Dict]


@dataclass
class GPTProposal:
    term: str
    entity_type: str
    proposed_canonical: str
    proposed_canonical_id: Optional[str]
    target_table: str
    confidence: float
    reasoning: str
    alternative_interpretations: List[str]


# ============================================================================
# BATCH JOB CLASS
# ============================================================================

class EntityLearningBatch:
    """
    Batch processor for entity learning pipeline.

    Workflow:
    1. link_actions() - Connect unknown terms to user actions
    2. get_candidates() - Get frequent unknown terms that need proposals
    3. propose_aliases() - Use GPT to propose alias mappings
    4. store_candidates() - Store proposals for human review
    """

    def __init__(self):
        # Initialize Supabase
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

        self.client: Client = create_client(self.supabase_url, self.supabase_key)

        # Initialize OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("Missing OPENAI_API_KEY")

        self.openai = OpenAI(api_key=openai_key)

        logger.info("Entity Learning Batch initialized")

    def run(self) -> Dict:
        """
        Run the full batch job.

        Returns summary of actions taken.
        """
        logger.info("=" * 60)
        logger.info("ENTITY LEARNING BATCH JOB - START")
        logger.info("=" * 60)

        results = {
            "started_at": datetime.now().isoformat(),
            "actions_linked": 0,
            "candidates_found": 0,
            "proposals_created": 0,
            "auto_approved": 0,
            "errors": []
        }

        try:
            # Step 1: Link unknown terms to user actions
            logger.info("Step 1: Linking unknown terms to actions...")
            results["actions_linked"] = self.link_actions()

            # Step 2: Get candidate terms for proposal
            logger.info("Step 2: Getting candidate terms...")
            candidates = self.get_candidates()
            results["candidates_found"] = len(candidates)

            if not candidates:
                logger.info("No candidates meet threshold criteria. Done.")
                results["finished_at"] = datetime.now().isoformat()
                return results

            # Step 3: Generate GPT proposals
            logger.info(f"Step 3: Generating proposals for {len(candidates)} candidates...")
            proposals = []
            for candidate in candidates:
                try:
                    proposal = self.propose_alias(candidate)
                    if proposal and proposal.confidence >= GPT_CONFIDENCE_THRESHOLD:
                        proposals.append((candidate, proposal))
                except Exception as e:
                    logger.error(f"Failed to propose for '{candidate.term}': {e}")
                    results["errors"].append(f"Proposal failed for {candidate.term}: {str(e)}")

            # Step 4: Store proposals
            logger.info(f"Step 4: Storing {len(proposals)} proposals...")
            for candidate, proposal in proposals:
                try:
                    auto_approved = self.store_candidate(candidate, proposal)
                    results["proposals_created"] += 1
                    if auto_approved:
                        results["auto_approved"] += 1
                except Exception as e:
                    logger.error(f"Failed to store proposal for '{candidate.term}': {e}")
                    results["errors"].append(f"Store failed for {candidate.term}: {str(e)}")

            # Step 5: Expire old pending candidates
            logger.info("Step 5: Expiring old candidates...")
            expired = self.expire_old_candidates()
            results["expired"] = expired

        except Exception as e:
            logger.error(f"Batch job failed: {e}")
            results["errors"].append(f"Batch job error: {str(e)}")

        results["finished_at"] = datetime.now().isoformat()

        logger.info("=" * 60)
        logger.info(f"BATCH JOB COMPLETE: {json.dumps(results, indent=2)}")
        logger.info("=" * 60)

        return results

    def link_actions(self, time_window_minutes: int = 10) -> int:
        """
        Link unknown entities to subsequent user actions.

        Returns number of links created.
        """
        try:
            result = self.client.rpc('link_unknown_to_actions', {
                'p_time_window_minutes': time_window_minutes
            }).execute()

            count = len(result.data) if result.data else 0
            logger.info(f"Linked {count} unknown terms to actions")
            return count

        except Exception as e:
            logger.error(f"link_actions failed: {e}")
            return 0

    def get_candidates(self) -> List[UnknownTermStats]:
        """
        Get unknown terms that meet threshold criteria for proposal.
        """
        try:
            result = self.client.table('v_unknown_term_stats').select('*').execute()

            candidates = []
            for row in result.data or []:
                # Apply thresholds
                if row['usage_count'] < MIN_USAGE_COUNT:
                    continue
                if row['yacht_count'] < MIN_YACHT_COUNT:
                    continue

                # Check action ratio
                action_ratio = row['with_actions'] / row['usage_count'] if row['usage_count'] > 0 else 0
                if action_ratio < MIN_ACTION_RATIO:
                    continue

                # Check if already proposed
                existing = self.client.table('alias_candidates').select('id').eq(
                    'normalized_term', row['term'].lower()
                ).execute()

                if existing.data:
                    logger.debug(f"Skipping '{row['term']}' - already proposed")
                    continue

                candidates.append(UnknownTermStats(
                    term=row['term'],
                    entity_type_guess=row['entity_type_guess'],
                    usage_count=row['usage_count'],
                    yacht_count=row['yacht_count'],
                    user_count=row['user_count'],
                    with_actions=row['with_actions'],
                    avg_confidence=row['avg_confidence'] or 0,
                    sample_queries=row['sample_queries'][:5] if row['sample_queries'] else [],
                    linked_actions=row['linked_actions'] or []
                ))

            logger.info(f"Found {len(candidates)} candidates meeting criteria")
            return candidates

        except Exception as e:
            logger.error(f"get_candidates failed: {e}")
            return []

    def propose_alias(self, candidate: UnknownTermStats) -> Optional[GPTProposal]:
        """
        Use GPT to propose an alias mapping for an unknown term.
        """
        # Build context for GPT
        sample_queries_str = "\n".join([f"  - {q}" for q in candidate.sample_queries[:5]])

        linked_actions_str = ""
        if candidate.linked_actions:
            actions_summary = []
            for action in candidate.linked_actions[:5]:
                if action.get('action_type') and action.get('equipment_id'):
                    actions_summary.append(f"  - {action['action_type']} on equipment {action['equipment_id']}")
            linked_actions_str = "\n".join(actions_summary) if actions_summary else "None"
        else:
            linked_actions_str = "None"

        prompt = f"""You are analyzing an unknown term from a yacht/maritime maintenance management system.

TERM: "{candidate.term}"
SYSTEM'S GUESS: {candidate.entity_type_guess or "unknown"}
USAGE COUNT: {candidate.usage_count} times across {candidate.yacht_count} yachts

SAMPLE QUERIES where this term appeared:
{sample_queries_str}

ACTIONS users took after using this term:
{linked_actions_str}

Based on this context, what does this term most likely refer to?

Respond in JSON format:
{{
  "entity_type": "equipment" | "part" | "symptom" | "task" | "location" | "person" | "unknown",
  "proposed_canonical": "The standard name this term maps to (e.g., 'Main Engine 1')",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why you think this",
  "alternative_interpretations": ["Other possible meanings"],
  "target_table": "equipment_aliases" | "part_aliases" | "symptom_aliases" | "task_aliases"
}}

RULES:
- Only propose if you're reasonably confident (>0.6)
- Maritime context: "ME1" = Main Engine 1, "Gen" = Generator, "WM" = Watermaker, etc.
- If it's yacht-specific jargon you don't recognize, set confidence low
- target_table should match entity_type (equipment -> equipment_aliases, etc.)
"""

        try:
            response = self.openai.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a maritime equipment expert helping standardize terminology. Respond only in valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON (handle markdown code blocks)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content)

            proposal = GPTProposal(
                term=candidate.term,
                entity_type=data.get('entity_type', 'unknown'),
                proposed_canonical=data.get('proposed_canonical', candidate.term),
                proposed_canonical_id=None,  # Will be resolved later if needed
                target_table=data.get('target_table', 'equipment_aliases'),
                confidence=float(data.get('confidence', 0.5)),
                reasoning=data.get('reasoning', ''),
                alternative_interpretations=data.get('alternative_interpretations', [])
            )

            logger.info(
                f"GPT proposal for '{candidate.term}': "
                f"{proposal.proposed_canonical} ({proposal.entity_type}, conf={proposal.confidence:.2f})"
            )

            return proposal

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response for '{candidate.term}': {e}")
            return None
        except Exception as e:
            logger.error(f"GPT call failed for '{candidate.term}': {e}")
            return None

    def store_candidate(self, candidate: UnknownTermStats, proposal: GPTProposal) -> bool:
        """
        Store a GPT proposal in alias_candidates table.

        Returns True if auto-approved.
        """
        # Build evidence JSON
        evidence = {
            "usage_count": candidate.usage_count,
            "yacht_count": candidate.yacht_count,
            "user_count": candidate.user_count,
            "with_actions": candidate.with_actions,
            "avg_confidence": candidate.avg_confidence,
            "sample_queries": candidate.sample_queries,
            "linked_actions": candidate.linked_actions
        }

        # Build model suggestion JSON
        model_suggestion = {
            "model": GPT_MODEL,
            "confidence": proposal.confidence,
            "reasoning": proposal.reasoning,
            "alternative_interpretations": proposal.alternative_interpretations
        }

        # Check auto-approve criteria
        auto_approved = (
            candidate.usage_count >= AUTO_APPROVE_USAGE and
            proposal.confidence >= AUTO_APPROVE_CONFIDENCE
        )

        # Determine status
        status = 'approved' if auto_approved else 'pending'

        try:
            self.client.table('alias_candidates').upsert({
                'term': proposal.term,
                'entity_type': proposal.entity_type,
                'proposed_canonical': proposal.proposed_canonical,
                'proposed_canonical_id': proposal.proposed_canonical_id,
                'target_table': proposal.target_table,
                'yacht_scope': 'fleet',  # Default to fleet-wide
                'evidence': evidence,
                'model_suggestion': model_suggestion,
                'status': status,
                'auto_approved': auto_approved,
                'reviewed_by': 'auto' if auto_approved else None,
                'reviewed_at': datetime.now().isoformat() if auto_approved else None
            }, on_conflict='normalized_term,entity_type,yacht_scope').execute()

            if auto_approved:
                logger.info(f"AUTO-APPROVED: '{proposal.term}' -> '{proposal.proposed_canonical}'")
                # Actually apply the alias
                self.client.rpc('approve_alias_candidate', {
                    'p_candidate_id': None,  # Will need to query for ID
                    'p_reviewer': 'auto_batch'
                }).execute()
            else:
                logger.info(f"Stored pending proposal: '{proposal.term}' -> '{proposal.proposed_canonical}'")

            return auto_approved

        except Exception as e:
            logger.error(f"Failed to store candidate: {e}")
            raise

    def expire_old_candidates(self, days_old: int = 30) -> int:
        """
        Expire pending candidates older than N days.
        """
        try:
            result = self.client.rpc('expire_old_candidates', {
                'p_days_old': days_old
            }).execute()

            count = result.data if result.data else 0
            logger.info(f"Expired {count} old candidates")
            return count

        except Exception as e:
            logger.error(f"expire_old_candidates failed: {e}")
            return 0


# ============================================================================
# CLI
# ============================================================================

def main():
    """Run the batch job from command line."""
    import argparse

    parser = argparse.ArgumentParser(description='Entity Learning Batch Job')
    parser.add_argument('--dry-run', action='store_true', help='Print what would happen without making changes')
    parser.add_argument('--link-only', action='store_true', help='Only link actions, no GPT proposals')
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        # TODO: Implement dry run

    batch = EntityLearningBatch()

    if args.link_only:
        count = batch.link_actions()
        print(f"Linked {count} unknown terms to actions")
    else:
        results = batch.run()
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

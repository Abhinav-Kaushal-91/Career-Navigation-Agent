"""Prompt construction for optional constrained plan wording synthesis."""

import json

from ai_career_navigator.domain import CareerPlan

PROMPT_VERSION = "7A-v1"
SYSTEM_PROMPT = """You refine wording for a validated career-plan skeleton.
Keep every milestone key, phase, type, gap ID, evidence artifact, dependency, target role,
bridge role, risk, and assumption unchanged. Do not add skills, credentials, market claims,
roles, gaps, milestones, or guarantees. Return only the requested structured object."""


def build_plan_prompt(plan: CareerPlan) -> str:
    """Send only the bounded deterministic draft, never raw profile or job content."""

    payload = {
        "target_role": plan.target_role,
        "bridge_roles": [item.bridge_role for item in plan.bridge_roles if item.bridge_role],
        "milestones": [
            {
                "milestone_key": f"milestone-{index}",
                "phase": item.phase,
                "milestone_type": item.milestone_type.value,
                "action": item.action,
                "linked_gap_ids": [str(value) for value in item.linked_gap_ids],
                "measurable_outcome": item.measurable_outcome,
                "evidence_to_create": item.evidence_to_create,
                "dependencies": item.dependencies,
            }
            for index, item in enumerate(plan.milestones)
        ],
        "risks": plan.risks,
        "assumptions": plan.assumptions,
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)

"""Generic career-transition interpretation; no profession-specific verdict rules."""

from typing import Literal

from pydantic import Field

from ai_career_navigator.domain import GoalType

from .same_role import (
    Action,
    AssessmentReply,
    AssessmentReview,
    Competency,
    Record,
    SameRoleAssessment,
    assess_consolidated,
    build_inputs,
    reference_issues,
)
from .transition_prompts import REVIEW_INSTRUCTIONS, RULE_VERSION, SYSTEM_PROMPT


class TransitionCompetency(Competency):
    status: Literal[
        "DEMONSTRATED",
        "TRANSFERABLE",
        "PARTIALLY_DEMONSTRATED",
        "NOT_ESTABLISHED",
        "NOT_RELEVANT",
    ]
    transfer_explanation: str | None = Field(default=None, max_length=500)
    remaining_need: Literal["NONE", "CLARIFY", "LEARN", "BUILD_EXPERIENCE"]
    development_focus: str | None = Field(default=None, max_length=350)


class DemonstratedStrength(Record):
    name: str = Field(min_length=1, max_length=100)
    why_it_helps: str = Field(min_length=1, max_length=350)
    candidate_refs: list[str] = Field(min_length=1, max_length=5)


class TransitionAction(Action):
    action_type: Literal[
        "SKILL",
        "EXPERIENCE",
        "PROJECT",
        "EVIDENCE",
        "APPLICATION_READINESS",
        "REASSESSMENT",
    ]


class TransitionReply(AssessmentReply):
    rationale: str = Field(
        min_length=1,
        max_length=1000,
        description="Current readiness for the supplied opportunities and its decisive reason.",
    )
    role_picture: str = Field(
        min_length=1,
        max_length=1000,
        description=(
            "Credible transition direction and relevant foundations, distinct from readiness now; "
            "include important differences among sampled role directions."
        ),
    )
    competencies: list[TransitionCompetency] = Field(default_factory=list, max_length=20)
    demonstrated_strengths: list[DemonstratedStrength] = Field(default_factory=list, max_length=8)
    actions: list[TransitionAction] = Field(default_factory=list, max_length=6)


class TransitionReview(AssessmentReview):
    assessment: TransitionReply


class TransitionAssessment(SameRoleAssessment):
    competencies: list[TransitionCompetency]
    demonstrated_strengths: list[DemonstratedStrength]
    actions: list[TransitionAction]


def is_career_transition(profile, goal):
    return bool(
        profile and goal and goal.target_role and goal.goal_type == GoalType.ROLE_TRANSITION
    )


def uses_consolidated_target_assessment(profile, goal):
    """Share assessment mechanics without rewriting the user's chosen direction."""
    return bool(
        profile
        and goal
        and goal.target_role
        and goal.goal_type in {GoalType.ROLE_TRANSITION, GoalType.TARGET_CAREER_PATH}
    )


def transition_reference_issues(reply, sources, lines, evidence):
    issues = reference_issues(reply, sources, lines, evidence)
    for n, strength in enumerate(reply.demonstrated_strengths):
        if not set(strength.candidate_refs) <= evidence.keys():
            issues.append(f"demonstrated_strengths[{n}]: unknown candidate reference")
    for n, item in enumerate(reply.competencies):
        if item.status == "TRANSFERABLE" and not (item.transfer_explanation or "").strip():
            issues.append(f"competencies[{n}]: explain what transfers and its boundary")
        if item.remaining_need != "NONE" and not (item.development_focus or "").strip():
            issues.append(f"competencies[{n}]: identify the outstanding need")
    return issues


def build_transition_inputs(profile, goal, evidence):
    payload, sources, lines, candidates = build_inputs(profile, goal, evidence)
    payload["goal_context"] = goal.model_dump(
        mode="json",
        include={
            "goal_type",
            "target_seniority",
            "target_industries",
            "geography_scopes",
            "bridge_role_willingness",
            "search_expansion_permission",
            "exclusions",
        },
    )
    payload["candidate"]["career_stage"] = profile.career_stage
    return payload, sources, lines, candidates


def assess_career_transition(profile, goal, evidence, gateway):
    result = assess_consolidated(
        profile,
        goal,
        evidence,
        gateway,
        system_prompt=SYSTEM_PROMPT,
        rule_version=RULE_VERSION,
        task_prefix="career_transition",
        reply_schema=TransitionReply,
        review_schema=TransitionReview,
        result_schema=TransitionAssessment,
        check_references=transition_reference_issues,
        input_builder=build_transition_inputs,
        review_instructions=REVIEW_INSTRUCTIONS,
    )
    # A bad proposed strength cannot become a confirmed-looking retained fact.
    return result.model_copy(
        update={
            "demonstrated_strengths": [
                item
                for item in result.demonstrated_strengths
                if set(item.candidate_refs) <= result.candidate_sources.keys()
            ]
        }
    )

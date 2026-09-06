"""Deterministic CareerGoal assembly, review formatting, and approval."""

from datetime import UTC, datetime

from ai_career_navigator.domain import ApprovalStatus, CareerGoal, GoalType
from ai_career_navigator.goal.configuration import goal_intent_config, goal_type_label
from ai_career_navigator.goal.schemas import GoalDraft


class GoalValidationError(ValueError):
    """The draft does not satisfy the selected V1 intent policy."""


def validate_goal_draft(draft: GoalDraft) -> None:
    config = goal_intent_config(draft.goal_type)
    if config.requires_target and not draft.target_role:
        raise GoalValidationError("Enter a target role for this career direction.")


def build_career_goal(
    draft: GoalDraft,
    *,
    approved: bool = False,
    now: datetime | None = None,
) -> CareerGoal:
    validate_goal_draft(draft)
    timestamp = now or datetime.now(UTC)
    return CareerGoal(
        goal_version=1,
        goal_type=draft.goal_type,
        target_role=draft.target_role,
        target_seniority=draft.target_seniority,
        target_timeline_months=draft.target_timeline_months,
        target_location=draft.target_location,
        target_industries=draft.target_industries,
        preferred_work_modes=draft.preferred_work_modes,
        geography_scopes=draft.geography_scopes,
        bridge_role_willingness=draft.bridge_role_willingness,
        search_expansion_permission=draft.search_expansion_permission,
        exploration_mode=draft.goal_type is GoalType.CAREER_EXPLORATION,
        exclusions=draft.exclusions,
        approval_status=ApprovalStatus.APPROVED if approved else ApprovalStatus.DRAFT,
        created_at=timestamp,
        approved_at=timestamp if approved else None,
    )


def confirm_career_goal(draft: GoalDraft, *, now: datetime | None = None) -> CareerGoal:
    return build_career_goal(draft, approved=True, now=now)


def _friendly_bridge(value: bool | None) -> str:
    if value is True:
        return "Open to an intermediate role"
    if value is False:
        return "Direct path only"
    return "Unsure"


def format_goal_review(draft: GoalDraft) -> tuple[tuple[str, str], ...]:
    """Return compact user-facing review rows without raw enum values."""

    config = goal_intent_config(draft.goal_type)
    rows: list[tuple[str, str]] = [
        ("Direction", goal_type_label(draft.goal_type)),
    ]
    if config.target_label:
        rows.extend(
            [
                ("Target", draft.target_role or "No specific target"),
                ("Target seniority", draft.target_seniority or "Not specified"),
            ]
        )
    if config.show_timeline:
        rows.append(
            (
                "Timeline",
                f"{draft.target_timeline_months} months"
                if draft.target_timeline_months
                else "No fixed timeline",
            )
        )
    rows.extend(
        [
            ("Location", draft.target_location or "Not specified"),
            ("Work mode", " / ".join(draft.preferred_work_modes) or "No preference"),
            (
                "Geography scope",
                " / ".join(
                    scope.value.replace("_", " ").title() for scope in draft.geography_scopes
                )
                or "Strict city",
            ),
        ]
    )
    if config.show_bridge_willingness:
        rows.append(("Bridge role", _friendly_bridge(draft.bridge_role_willingness)))
    if config.show_search_expansion:
        rows.append(
            (
                "Related-title expansion",
                "Allowed" if draft.search_expansion_permission else "Exact scope only",
            )
        )
    rows.extend(
        [
            ("Industries", " / ".join(draft.target_industries) or "No preference"),
            ("Constraints", "; ".join(draft.exclusions) or "None added"),
        ]
    )
    return tuple(rows)

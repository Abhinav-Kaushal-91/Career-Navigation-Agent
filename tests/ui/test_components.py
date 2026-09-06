from ai_career_navigator.ui.components.roadmap import group_milestones
from ai_career_navigator.ui.demo_data import PLAN_MILESTONES
from ai_career_navigator.ui.pages.live_views import _analysis_view_available, _display_value
from ai_career_navigator.ui.theme import badge_tone


def test_badge_tone_uses_semantic_mapping_and_safe_fallback() -> None:
    assert badge_tone("HIGH") == "success"
    assert badge_tone("ASPIRATIONAL") == "warning"
    assert badge_tone("unknown") == "neutral"


def test_milestones_group_in_display_order() -> None:
    grouped = group_milestones(PLAN_MILESTONES)

    assert list(grouped) == [
        "Common evidence foundation",
        "Bridge-role readiness",
        "Target-role readiness",
    ]
    assert [len(items) for items in grouped.values()] == [5, 1, 1]


def test_market_enum_labels_do_not_expose_underscores() -> None:
    assert _display_value("INSUFFICIENT_EVIDENCE") == "Not enough evidence"


def test_market_evidence_opens_analysis_even_without_role_assessment() -> None:
    assert _analysis_view_available({"market_snapshot": object(), "role_assessment": None})
    assert not _analysis_view_available({"market_snapshot": None})

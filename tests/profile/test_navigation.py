from ai_career_navigator.profile import (
    PROFILE_ONBOARDING_STEPS,
    ProfileDraft,
    can_navigate_profile_step,
    next_profile_highest,
    profile_step_states,
)


def test_onboarding_step_order_matches_product_flow() -> None:
    assert PROFILE_ONBOARDING_STEPS == (
        "About You",
        "Professional Profile",
        "Portfolio Projects",
        "Education",
        "AI Strength Identification",
        "Review",
    )


def test_backward_navigation_preserves_highest_reached_step() -> None:
    assert (
        next_profile_highest("Portfolio Projects", "Professional Profile") == "Portfolio Projects"
    )
    assert can_navigate_profile_step("Professional Profile", "Portfolio Projects")


def test_future_step_is_unavailable_until_reached() -> None:
    assert not can_navigate_profile_step("Review", "Professional Profile")


def test_reached_future_step_remains_available_after_edit_navigation() -> None:
    states = profile_step_states("AI Strength Identification", "Review")

    assert states[-1].label == "Review"
    assert states[-1].available
    assert states[-1].status == "available"


def test_navigation_state_changes_do_not_mutate_profile_data() -> None:
    draft = ProfileDraft()
    serialized = draft.model_dump(mode="json")

    assert next_profile_highest("Review", "Professional Profile") == "Review"
    assert ProfileDraft.model_validate(serialized) == draft

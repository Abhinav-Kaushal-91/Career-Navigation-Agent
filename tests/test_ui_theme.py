from ai_career_navigator.ui.theme import RADII, SEMANTIC_STATES, SPACING


def test_foundational_theme_tokens() -> None:
    assert tuple(SPACING.values()) == (4, 8, 12, 16, 24, 32, 48)
    assert tuple(RADII) == ("small", "medium", "large")
    assert set(SEMANTIC_STATES) == {
        "success",
        "warning",
        "critical",
        "neutral",
        "information",
    }

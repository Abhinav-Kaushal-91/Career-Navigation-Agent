"""Categorized gap presentation."""

from collections.abc import Sequence

from ai_career_navigator.ui.components.cards import render_card


def render_gap_card(category: str, gaps: Sequence[str]) -> None:
    if gaps:
        render_card(
            category.replace("_", " ").title(),
            "Evidence-backed differences to address.",
            items=gaps,
        )
    else:
        render_card(
            category.replace("_", " ").title(), "None identified in the synthetic evidence."
        )

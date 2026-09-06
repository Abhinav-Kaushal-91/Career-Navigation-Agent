"""Candidate and market evidence presentation."""

from ai_career_navigator.ui.components.cards import render_card


def render_evidence_item(title: str, description: str, source: str) -> None:
    render_card(title, description, items=(f"Evidence source: {source}",))


def render_inferred_capability(title: str, evidence: str, confidence: str) -> None:
    render_card(title, evidence, items=(f"Confidence: {confidence}",), accent=True)

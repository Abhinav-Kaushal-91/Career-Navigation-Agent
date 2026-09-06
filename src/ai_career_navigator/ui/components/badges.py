"""Accessible text badges."""

import streamlit as st

from ai_career_navigator.ui.theme import badge_tone


def render_status_badge(label: str, *, prefix: str | None = None) -> None:
    visible = f"{prefix}: {label}" if prefix else label
    color = {
        "success": "green",
        "information": "blue",
        "warning": "orange",
        "critical": "red",
        "neutral": "gray",
    }[badge_tone(label)]
    st.badge(visible, color=color)

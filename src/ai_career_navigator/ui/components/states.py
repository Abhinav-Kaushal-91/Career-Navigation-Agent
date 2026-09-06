"""Honest loading, empty, limitation, and error states."""

import streamlit as st


def render_state(title: str, message: str, *, tone: str = "information") -> None:
    callout = st.error if tone == "critical" else st.warning if tone == "warning" else st.info
    callout(f"**{title}**\n\n{message}")


def render_loading_state() -> None:
    render_state(
        "Analyzing market evidence…",
        "Validated progress will be preserved as each stage completes.",
    )


def render_partial_evidence_state() -> None:
    render_state(
        "Partial evidence",
        "3 sources could not be retrieved. Analysis continues using 12 validated sources.",
        tone="warning",
    )


def render_insufficient_evidence_state() -> None:
    render_state(
        "Insufficient evidence",
        "We don’t have enough reliable evidence to assess this role yet.",
        tone="warning",
    )


def render_empty_state() -> None:
    render_state("No profile yet", "Build your structured career profile to begin.")


def render_error_state() -> None:
    render_state(
        "Step not completed",
        "We couldn’t complete this step. Your previous progress is preserved.",
        tone="critical",
    )

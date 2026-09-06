"""Reusable content-card patterns."""

from collections.abc import Sequence

import streamlit as st


def render_card(
    title: str,
    body: str,
    *,
    items: Sequence[str] = (),
    accent: bool = False,
    height: int | None = None,
) -> None:
    del accent
    with st.container(border=True, height=height or "content"):
        st.markdown(f"**{title}**")
        st.write(body)
        for item in items:
            st.write(f"- {item}")


def render_card_pair(
    *,
    left_title: str,
    left_body: str,
    left_items: Sequence[str] = (),
    right_title: str,
    right_body: str,
) -> None:
    """Render parallel cards in one equal-height responsive grid."""

    left, right = st.columns(2)
    with left:
        render_card(left_title, left_body, items=left_items, accent=True)
    with right:
        render_card(right_title, right_body)


def render_role_card(title: str, explanation: str, *, items: Sequence[str] = ()) -> None:
    render_card(title, explanation, items=items, accent=True)

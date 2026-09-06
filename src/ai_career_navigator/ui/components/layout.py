"""Application layout helpers."""

import streamlit as st


def render_page_header(eyebrow: str, title: str, description: str) -> None:
    """Render a native heading hierarchy."""

    st.caption(eyebrow.upper())
    st.title(title)
    st.write(description)


def render_caption(text: str) -> None:
    st.caption(text)

"""Market and plan summary metrics."""

import streamlit as st


def render_metric_card(value: str | int, label: str, detail: str | None = None) -> None:
    st.metric(label, value, delta=detail, delta_color="off")

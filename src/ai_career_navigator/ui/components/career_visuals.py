"""Read-only visual summaries of the same rows and milestones shown below them."""

from collections import Counter, defaultdict
from html import escape
from math import cos, pi, sin
from textwrap import wrap

import plotly.graph_objects as go
import streamlit as st

from ai_career_navigator.ui.components.charts import BLUE, GREY, style

DIMENSIONS = {
    "TECHNICAL": "Technical / trade skills",
    "DESIGN": "Problem solving / design",
    "DELIVERY": "Delivery / operations",
    "COLLABORATION": "Communication / collaboration",
    "LEADERSHIP": "Leadership / ownership",
    "DOMAIN": "Business / domain",
}
STATUSES = ("Demonstrated", "Transferable", "Partial", "Unconfirmed", "Needs development")


def unique_comparison_rows(rows):
    """Remove exact duplicate display rows, not distinct qualifications or conditions."""
    seen = set()
    result = []
    for row in rows:
        key = (row["Competency"].strip().casefold(), row["Your position"])
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def snapshot_data(rows, dimensions=None):
    """Count final display rows; never infer accessibility, skills or group membership."""
    dimensions = dimensions or {}
    counts = Counter({status: 0 for status in STATUSES})
    groups = defaultdict(list)
    for row in unique_comparison_rows(rows):
        status = row["Your position"]
        status = "Partial" if status == "Partially demonstrated" else status
        if status not in STATUSES:
            status = "Unconfirmed"
        counts[status] += 1
        dimension = dimensions.get(row["Competency"])
        if dimension in DIMENSIONS:
            groups[dimension].append(status)
    # User-approved display rule: unconfirmed = no demonstrated coverage, not inability.
    coverage = {
        key: values.count("Demonstrated") / len(values)
        for key, values in groups.items()
    }
    return dict(counts), coverage


def _lines(value, width=22):
    return "<br>".join(escape(line) for line in wrap(str(value), width=width))


def build_coverage_radar(coverage):
    """Centered vertex labels, no 0% label, no manufactured axes or unknown polygon."""
    keys = [key for key in DIMENSIONS if key in coverage]
    if len(keys) < 3 or any(coverage[key] is None for key in keys):
        return None
    angles = [pi / 2 - 2 * pi * i / len(keys) for i in range(len(keys))]
    unit = [(cos(angle), sin(angle)) for angle in angles]
    figure = go.Figure()
    for radius in (0.25, 0.5, 0.75, 1):
        points = [(x * radius, y * radius) for x, y in unit]
        points.append(points[0])
        figure.add_trace(
            go.Scatter(
                x=[x for x, _ in points],
                y=[y for _, y in points],
                mode="lines",
                line=dict(color=GREY, width=1),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    for x, y in unit:
        figure.add_shape(type="line", x0=0, y0=0, x1=x, y1=y, line=dict(color=GREY, width=1))
    values = [coverage[key] for key in keys]
    points = [(x * value, y * value) for (x, y), value in zip(unit, values, strict=True)]
    points.append(points[0])
    figure.add_trace(
        go.Scatter(
            x=[x for x, _ in points],
            y=[y for _, y in points],
            mode="lines+markers",
            fill="toself",
            fillcolor="rgba(31,79,216,0.18)",
            line=dict(color=BLUE, width=2),
            marker=dict(size=7),
            customdata=[DIMENSIONS[key] for key in keys] + [DIMENSIONS[keys[0]]],
            hovertemplate="%{customdata}<extra></extra>",
            showlegend=False,
        )
    )
    for key, (x, y) in zip(keys, unit, strict=True):
        figure.add_annotation(
            x=x * 1.28,
            y=y * 1.28,
            text="<br>".join(escape(part.strip()) for part in DIMENSIONS[key].split("/")),
            showarrow=False,
            xanchor="center",
            yanchor="middle",
            align="center",
        )
    for radius in (0.5, 1):
        figure.add_annotation(
            x=0.07,
            y=radius,
            text=f"{radius:.0%}",
            showarrow=False,
            font=dict(size=10, color="#707586"),
        )
    style(figure, height=380, xaxis=False)
    figure.update_xaxes(range=[-2.0, 2.0], visible=False, fixedrange=True)
    figure.update_yaxes(
        range=[-1.55, 1.55], visible=False, fixedrange=True, scaleanchor="x", scaleratio=1
    )
    return figure


def render_competency_snapshot(rows, dimensions=None, *, processing_issue=False):
    if not rows:
        return
    counts, coverage = snapshot_data(rows, dimensions)
    st.subheader("Your competency snapshot")
    # Native bordered panels separate the two readings and stack on narrow screens.
    left, right = st.columns([1.2, 1], gap="large", border=True)
    with left:
        st.markdown("**Coverage by dimension**")
        figure = None if processing_issue else build_coverage_radar(coverage)
        if figure is None:
            st.caption("Dimension view unavailable for this result; your comparisons remain below.")
        else:
            st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})
            st.caption(
                "Demonstrated coverage · Unconfirmed counts as zero here, not as a skill gap."
            )
    with right:
        st.markdown("**Your competency matches**")
        for pair in (STATUSES[:2], STATUSES[2:4]):
            for column, name in zip(st.columns(2), pair, strict=True):
                with column, st.container(border=True):
                    st.metric(name, counts[name])
        if counts["Needs development"]:
            st.caption(f"Also: {counts['Needs development']} confirmed to need development.")
        if processing_issue:
            st.caption("Available comparisons only; processing checks remain unresolved.")


def render_path_map(plan, milestones=None, *, processing_issue=False, clean=str):
    from ai_career_navigator.ui.components.career_story import render_journey

    render_journey(plan, milestones, processing_issue=processing_issue, clean=clean)

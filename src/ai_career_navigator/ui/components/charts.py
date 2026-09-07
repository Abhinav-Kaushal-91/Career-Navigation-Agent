"""Native Plotly charts built only from already-calculated workflow values."""

from collections.abc import Sequence

import plotly.graph_objects as go
import streamlit as st

BLUE = "#1F4FD8"
BLUE_MID = "#5B84E0"
BLUE_PALE = "#A8BDEE"
GREEN = "#8FC7A6"
AMBER = "#E8B84B"
GREY = "#D5D7DE"
CHART_COLORS = (BLUE, BLUE_MID, BLUE_PALE, GREEN, AMBER, GREY)


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, value))


def style(figure: go.Figure, *, height: int = 260, xaxis: bool = True) -> go.Figure:
    """Apply the shared chart treatment from the approved visual handoff."""

    figure.update_layout(
        height=height,
        showlegend=False,
        margin=dict(l=0, r=8, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Source Sans 3, sans-serif", size=12, color="#31333F"),
        hoverlabel=dict(bgcolor="#31333F", font_size=12),
    )
    figure.update_xaxes(showgrid=True, gridcolor="#E5E5E5", zeroline=False, visible=xaxis)
    figure.update_yaxes(showgrid=False, zeroline=False)
    return figure


def _render_figure(figure: go.Figure) -> None:
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def build_requirement_frequency_figure(
    items: Sequence[tuple[str, float, int, int]],
) -> go.Figure:
    """Build semantic frequency bars from validated occurrence counts."""

    labels = [label for label, _, _, _ in items]
    values = [_bounded(value) for _, value, _, _ in items]
    colors = [
        BLUE if value >= 0.60 else BLUE_MID if value >= 0.35 else AMBER if value >= 0.15 else GREY
        for _, value, _, _ in items
    ]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"{count} of {sample}" for _, _, count, sample in items],
            textposition="outside",
            constraintext="none",
            cliponaxis=False,
            customdata=[[count, sample] for _, _, count, sample in items],
            hovertemplate="%{y}: %{customdata[0]} of %{customdata[1]} postings<extra></extra>",
        )
    )
    figure.update_xaxes(range=[0, 1.3], tickvals=[0, 0.25, 0.5, 0.75, 1], tickformat=".0%")
    figure.update_layout(bargap=0.35, yaxis=dict(autorange="reversed"))
    styled = style(figure, height=max(260, 42 * len(items)))
    # Explicit left space plus automatic expansion keeps category names visible
    # inside Streamlit's clipped chart frame, including narrow desktop columns.
    styled.update_yaxes(automargin=True)
    styled.update_xaxes(automargin=True)
    label_margin = min(214, max(132, max((len(label) for label in labels), default=0) * 7 + 24))
    styled.update_layout(margin=dict(l=label_margin, r=56, t=8, b=32))
    return styled


def build_segmented_bar_figure(
    items: Sequence[tuple[str, int]], *, axis_label: str = "Postings"
) -> go.Figure:
    """Build a real stacked bar, omitting zero-value segments entirely."""

    positive = [(label, count) for label, count in items if count > 0]
    total = sum(count for _, count in positive)
    figure = go.Figure()
    for index, (label, count) in enumerate(positive):
        percentage = count / total * 100 if total else 0
        # Below ~12% width there isn't room for "N (NN%)" without spilling into the
        # next segment, so drop the inline label and rely on the legend/hover instead.
        label_text = f"{count} ({percentage:.0f}%)" if percentage >= 12 else ""
        figure.add_bar(
            name=label,
            x=[count],
            y=[axis_label],
            orientation="h",
            marker_color=CHART_COLORS[index % len(CHART_COLORS)],
            text=[label_text],
            textposition="inside",
            insidetextanchor="middle",
            constraintext="both",
            customdata=[[percentage]],
            hovertemplate=f"{label}: {count} (%{{customdata[0]:.0f}}%)<extra></extra>",
        )
    style(figure, height=165, xaxis=False)
    figure.update_layout(
        barmode="stack",
        showlegend=True,
        margin=dict(l=88, r=8, t=8, b=70),
        legend=dict(orientation="h", y=-0.62, x=0, font_size=11),
    )
    return figure


def build_roadmap_figure(phases: Sequence[tuple[str, int, int]]) -> go.Figure:
    """Build a month-offset roadmap from existing plan phase bounds."""

    figure = go.Figure()
    for index, (name, start, end) in enumerate(phases):
        figure.add_bar(
            y=[f"Phase {index + 1}"],
            x=[max(0, end - start)],
            base=[start],
            orientation="h",
            marker_color=(BLUE, BLUE_MID, GREEN)[index % 3],
            text=[name],
            textposition="inside",
            hovertemplate=f"{name}: months {start}–{end}<extra></extra>",
        )
    maximum = max((end for _, _, end in phases), default=1)
    figure.update_layout(barmode="overlay")
    tick_values = list(range(0, maximum + 1, 6)) or [0]
    if maximum not in tick_values:
        tick_values.append(maximum)
    figure.update_xaxes(
        range=[0, maximum],
        tickvals=tick_values,
        ticksuffix=" mo",
        showgrid=True,
        gridcolor="#E5E5E5",
    )
    figure.update_yaxes(autorange="reversed")
    return style(figure, height=max(180, 58 * len(phases)))


def build_seniority_figure(labels: Sequence[str], counts: Sequence[int]) -> go.Figure:
    """Build the compact seniority distribution from observed counts."""

    top = max(counts, default=0)
    colors = [
        BLUE if count == top else BLUE_MID if count >= top * 0.55 else BLUE_PALE for count in counts
    ]
    figure = go.Figure(
        go.Bar(
            x=list(labels),
            y=list(counts),
            text=list(counts),
            textposition="outside",
            cliponaxis=False,
            marker_color=colors,
        )
    )
    figure.update_yaxes(showgrid=True, gridcolor="#E5E5E5", range=[0, top + 1.4])
    return style(figure, height=220)


def build_compensation_figure(points: Sequence[int]) -> go.Figure:
    """Build the orientation-only compensation distribution."""

    figure = go.Figure(
        go.Box(
            x=list(points),
            boxpoints=False,
            orientation="h",
            name="",
            marker_color=BLUE,
            fillcolor="#7C9BE8",
            line_width=1.5,
        )
    )
    figure.update_xaxes(tickprefix="$", ticksuffix="K", showgrid=True, gridcolor="#E5E5E5")
    figure.update_yaxes(visible=False)
    return style(figure, height=150)


def render_horizontal_bars(title: str, subtitle: str, items: Sequence[tuple[str, float]]) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(subtitle)
        if not items:
            st.info("No validated values are available.")
            return
        labels = [
            label.replace(" ", "<br>", 1) if len(label) > 12 and " " in label else label
            for label, _ in items
        ]
        values = [_bounded(value) * 100 for _, value in items]
        colors = [
            BLUE if value >= 60 else BLUE_MID if value >= 35 else AMBER if value >= 15 else GREY
            for value in values
        ]
        figure = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=colors))
        figure.update_traces(text=[f"{value:.0f}%" for value in values], textposition="outside")
        figure.update_xaxes(range=[0, 105], ticksuffix="%")
        figure.update_yaxes(autorange="reversed")
        style(figure, height=max(260, 42 * len(items)))
        _render_figure(figure)


def render_donut(
    title: str,
    subtitle: str,
    value: float,
    center_label: str,
    remainder_label: str,
    *,
    sample_size: int | None = None,
) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(subtitle)
        if sample_size == 0:
            st.info("No validated employer sample is available.")
            return
        percent = _bounded(value) * 100
        figure = go.Figure(
            go.Pie(
                labels=[center_label, remainder_label],
                values=[percent, 100 - percent],
                hole=0.68,
                marker_colors=[BLUE, GREY],
                textinfo="none",
            )
        )
        style(figure, height=200, xaxis=False)
        figure.update_layout(
            showlegend=False,
            margin=dict(l=12, r=12, t=8, b=8),
            annotations=[
                dict(
                    text=f"<b>{percent:.0f}%</b><br><span style='font-size:11px'>top 3</span>",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font_size=20,
                )
            ],
        )
        _render_figure(figure)
        st.caption(f"{center_label}: {percent:.0f}% · {remainder_label}: {100 - percent:.0f}%")


def render_segmented_bar(
    title: str,
    subtitle: str,
    items: Sequence[tuple[str, int]],
    *,
    wide: bool = False,
) -> None:
    del wide
    safe_items = [(label, max(0, count)) for label, count in items]
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(subtitle)
        if not sum(count for _, count in safe_items):
            st.info("No validated values are available.")
            return
        figure = build_segmented_bar_figure(safe_items)
        _render_figure(figure)


def render_radar(title: str, subtitle: str, items: Sequence[tuple[str, float]]) -> None:
    """Render a 0-100 radar from explicitly supplied assessment values."""

    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(subtitle)
        if not items:
            st.info("No scored assessment dimensions are available.")
            return
        labels = [label for label, _ in items]
        values = [min(100, max(0, value)) for _, value in items]
        figure = go.Figure(
            go.Scatterpolar(
                r=[*values, values[0]],
                theta=[*labels, labels[0]],
                fill="toself",
                name="Your evidence",
                line_color="#1F4FD8",
                fillcolor="rgba(31,79,216,0.22)",
            )
        )
        figure.add_trace(
            go.Scatterpolar(
                r=[100] * len(labels) + [100],
                theta=[*labels, labels[0]],
                mode="lines",
                name="Market expectation",
                line=dict(color=GREEN, dash="dash", width=1.5),
            )
        )
        figure.data = (figure.data[-1], figure.data[0])
        style(figure, height=360, xaxis=False)
        figure.update_polars(
            domain=dict(x=[0.02, 0.82], y=[0.1, 1]),
            radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor="#ECEAE4"),
            angularaxis=dict(gridcolor="#F0EFE9", tickfont=dict(size=10)),
        )
        figure.update_layout(
            showlegend=True,
            margin=dict(l=70, r=48, t=36, b=72),
            legend=dict(orientation="v", x=0.18, y=-0.12, font_size=10),
        )
        _render_figure(figure)

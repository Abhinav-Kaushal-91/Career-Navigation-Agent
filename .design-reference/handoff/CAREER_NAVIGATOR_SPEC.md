# Career Navigator — Streamlit redesign spec

Single-file handoff. Give this whole document to an AI coding agent (Claude Code, Cursor, Copilot) along with `screens/*.png`. It contains the design intent, the exact widget mapping, the chart code, and the demo dataset. **No custom CSS is required or wanted.**

Target: Streamlit ≥ 1.40. Charts: Plotly.

---

## 0. What we are building and why

A five-stage evidence-grounded career planning app: **Profile → Goal → Market → Analysis → Plan.**

The redesign fixes three problems in the current build:

1. **Numbers were buried in prose.** Market and Analysis stages listed findings as bulleted sentences. They are now charts with a stated sample size next to each figure.
2. **The Plan stage presented one path as fact.** It now presents **three comparable options** (Direct climb / Bridge route / Depth first) scored on time, likelihood, effort and risk; selecting one drives the roadmap below it.
3. **Honesty was in footnotes.** Every figure now carries its confidence and limitation inline, using Streamlit's native callouts.

Non-negotiable product principle: never present synthetic or inferred data as validated. Every screen shows what kind of evidence it is standing on.

Reference screenshots: `screens/01-home.png` … `screens/06-plan.png`.

---

## 1. Theme — the only styling in the project

`.streamlit/config.toml`

```toml
[theme]
base = "light"
primaryColor = "#1F4FD8"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#31333F"
borderColor = "rgba(49,51,63,0.2)"
baseRadius = "medium"
font = "sans-serif"

[theme.sidebar]
backgroundColor = "#F0F2F6"
```

Chart palette — use these six colours and no others:

```python
BLUE, BLUE_MID, BLUE_PALE = "#1F4FD8", "#5B84E0", "#A8BDEE"
GREEN, AMBER, GREY        = "#8FC7A6", "#E8B84B", "#D5D7DE"
```

Semantic use: `BLUE` = your data / primary series / "common ≥70%". `BLUE_MID` = secondary series / "frequent 40–69%". `BLUE_PALE` = tertiary / "occasional <40%". `GREEN` = market expectation, good status, final phase. `AMBER` = gaps, moderate confidence. `GREY` = not observable / long tail.

**Do not inject CSS.** If a visual need seems to require it, change the design instead.

---

## 2. File layout

```
app.py                  # page config, sidebar, router
data.py                 # the demo dataset (section 8)
charts.py               # every Plotly figure builder (section 6)
pages_/
  home.py profile.py goal.py market.py analysis.py plan.py
.streamlit/config.toml
```

Each page module exposes one function: `def render() -> None`.

---

## 3. Shell — `app.py`

```python
import streamlit as st
from pages_ import home, profile, goal, market, analysis, plan

st.set_page_config(page_title="Career Navigator", layout="wide")

STAGES = {"Home": home, "Profile": profile, "Goal": goal,
          "Market": market, "Analysis": analysis, "Plan": plan}

st.session_state.setdefault("path", "bridge")
st.session_state.setdefault("direction", 1)

with st.sidebar:
    st.title("Career Navigator")
    st.caption("Evidence-grounded career strategy")
    st.divider()
    stage = st.radio("Stage", list(STAGES), index=0)
    st.divider()
    st.write("Profile completeness")
    st.progress(0.60, text="60% · 14 confirmed items")
    st.badge("Synthetic data", color="orange")
    st.badge("Demo mode", color="blue")
    st.caption("Nothing is saved in demo mode.")

STAGES[stage].render()
```

`st.radio` is the stage nav: selected state, keyboard access and a single rerun, free. If you prefer real URLs use `st.navigation([st.Page(...)])` and delete the radio — never run both.

---

## 4. Widget mapping

| Design element | Streamlit call |
|---|---|
| Page title | `st.title` |
| Lead paragraph | `st.write` |
| Grey sub-line, chart caption, chart legend | `st.caption` |
| Section heading | `st.subheader` |
| White bordered card | `with st.container(border=True):` |
| Card heading | `st.markdown("**…**")` |
| Number row | `st.columns(4)` + `st.metric(label, value, delta)` |
| Bar under a metric | `st.progress(0.5)` |
| Status pill | `st.badge("Confidence: moderate", color="blue")` |
| Blue / yellow / red / green callout | `st.info` / `st.warning` / `st.error` / `st.success` |
| Tab strip | `st.tabs([...])` |
| Scope selector | `st.segmented_control` |
| Text field, long text | `st.text_input`, `st.text_area(max_chars=600)` |
| Dropdown | `st.selectbox` |
| Numeric stepper | `st.number_input(step=0.5, format="%.2f")` |
| Removable pills | `st.multiselect` |
| Table with inline bars | `st.dataframe(..., column_config={… ProgressColumn …})` |
| Collapsed detail | `st.expander("Sources and limitations")` |
| Buttons | `st.button(..., type="primary" \| "secondary")` |
| Grouped form with one submit | `st.form` + `st.form_submit_button` |
| Any chart | `st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})` |

Layout rules: `st.columns` ratios are `[1.4, 1]` on Market and `[1, 1]` on Analysis; every chart lives inside `st.container(border=True)` so it reads as a card; modebars are off everywhere.

---

## 5. Screen-by-screen

### Home — `screens/01-home.png`
`st.title` + `st.write` + `st.caption`. Two buttons side by side (`st.columns([1,1,4])` so they don't stretch): primary "Build my career profile", secondary "Explore demo". Then `st.subheader("What Career Navigator helps you do")` and four `st.container(border=True)` in `st.columns(4)`: Explore roles / Understand market / Identify gaps / Build your path. Close with `st.info` about synthetic data and an `st.expander("Preview honest system states")`.

### Profile — `screens/02-profile.png`
`st.tabs(["About you","Experience","Skills","Projects","Education","Review"])`.

About you tab, inside `st.form("about")`: two columns — `st.selectbox("Career stage")` / `st.number_input("Years of professional experience", step=0.5, format="%.2f")`, then `st.text_input("Current role (optional)")` / `st.text_input("Current location (optional)")`, then full-width `st.text_area("Career summary (optional)", max_chars=600)`. `st.form_submit_button("Save and continue", type="primary")`.

Below the form: `st.divider()`, `st.subheader("Profile snapshot")`, four `st.metric`s (Roles captured 2 / Skills confirmed 9 / Projects 0 with delta "Raises confidence" / Evidence strength Moderate), then two cards — skills-by-category bar chart and a section-status list.

### Goal — `screens/03-goal.png`
`st.subheader("Direction")` then six cards in `st.columns(3)` × 2 rows. Each card: `st.markdown("**title**")`, `st.caption(body)`, `st.caption("Needs: …")`, and a button — `type="primary"`, label `"Selected ✓"`, `disabled=True` when `st.session_state.direction == i`, else secondary `"Choose this direction"`.

Then `st.divider()`, `st.subheader("Target and preferences")`: target role, timeline, location, `st.multiselect("Preferred work modes", default=["Hybrid","Remote"])`, and `st.segmented_control("How far may the location search extend?", ["City only","Metro area","Province","Country"], default="City only")`.

Two cards below: the scope-impact bar chart (15 / 38 / 63 postings) and a confirmed-goal summary ending in `st.success("Goal approved — ready for market analysis.")`.

### Market — `screens/04-market.png` — chart-heaviest screen
Title, `st.write` scope line, `st.caption("Retrieved 2 Sep 2026 · synthetic demonstration data · not a complete market count")`.

Four metrics: Validated postings 15 (delta "4 vs 30 days ago"), Distinct employers 11 ("1.4 postings each"), Opportunity availability Strong + `st.progress(0.78)`, Evidence confidence Moderate + `st.progress(0.50)`.

`st.tabs(["Overview","Requirements","Employers","Related titles","Compensation"])`. Overview tab, `st.columns([1.4, 1])`:
- Left card: **requirement frequency** horizontal bars + `st.caption("Common ≥70% · Frequent 40–69% · Occasional <40%")`.
- Right column, two stacked cards: **market concentration** donut (40% top-3) + `st.success("Low concentration — demand is spread across employers.")`; **seniority mix** columns.

Then `st.columns(2)`: related-titles `st.dataframe` with a `ProgressColumn`; compensation box plot + `st.warning("Sample of 6 is too small to treat as a market rate. Use for orientation only.")`.

Close with `st.expander("Sources and limitations")`.

### Analysis — `screens/05-analysis.png`
Title, `st.write` verdict, two `st.badge`s (Accessibility: aspirational / Confidence: moderate).

Four metrics: Strong matches 4, Transferable 3, Open gaps 4 (delta "2 far from target", `delta_color="inverse"`), Requirements covered 50% + `st.progress(0.5)`.

`st.columns(2)`: left card = **readiness radar** (your evidence vs market expectation); right column = **requirement coverage** stacked bar, then two small cards listing strong matches and transferable capabilities as bullets.

`st.subheader("Gap analysis")` + the gap `st.dataframe` with two `ProgressColumn`s. Then `st.columns(2)` with `st.info` (path assessment) and `st.warning` (limitations).

### Plan — `screens/06-plan.png` — the three options
Title, `st.write`, two badges (Plan status: draft / Candidate accessibility: aspirational).

`st.subheader("Compare your options")` then three cards in `st.columns(3)` — code in section 7. Below: `st.subheader(f"Phased roadmap — {selected}")`, the gantt chart, three phase cards in `st.columns(3)`, then `st.columns(2)` with `st.error("Grounded risks…")` and a bordered container of assumptions. Finish with `st.info` about plan version 1 and a button row: Approve plan (primary) / Save as draft / Reject recommendation / Back to analysis.

---

## 6. Charts — `charts.py`

```python
import plotly.graph_objects as go

BLUE, BLUE_MID, BLUE_PALE = "#1F4FD8", "#5B84E0", "#A8BDEE"
GREEN, AMBER, GREY        = "#8FC7A6", "#E8B84B", "#D5D7DE"

def style(fig, h=260, xaxis=True):
    fig.update_layout(
        height=h, showlegend=False,
        margin=dict(l=0, r=8, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Source Sans 3, sans-serif", size=12, color="#31333F"),
        hoverlabel=dict(bgcolor="#31333F", font_size=12))
    fig.update_xaxes(showgrid=True, gridcolor="#E5E5E5", zeroline=False, visible=xaxis)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


def requirement_frequency(names, vals):
    colors = [BLUE if v >= .70 else BLUE_MID if v >= .40 else BLUE_PALE for v in vals]
    fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker_color=colors,
                           text=[f"{v:.0%}" for v in vals],
                           textposition="outside", cliponaxis=False))
    fig.update_xaxes(range=[0, 1.06], tickformat=".0%")
    fig.update_layout(bargap=.35, yaxis=dict(autorange="reversed"))
    return style(fig, 300)


def concentration(values=(6, 3, 6)):
    fig = go.Figure(go.Pie(values=list(values),
                           labels=["Top 3 employers", "Next 4", "Long tail"],
                           hole=.62, sort=False, direction="clockwise",
                           marker_colors=[BLUE, BLUE_MID, "#C9D5F2"], textinfo="none"))
    share = values[0] / sum(values)
    fig.add_annotation(text=f"<b>{share:.0%}</b><br>"
                            "<span style='font-size:11px;color:#808495'>top 3</span>",
                       showarrow=False, font_size=20)
    fig.update_layout(showlegend=True,
                      legend=dict(orientation="v", x=1, y=.5, font_size=12))
    return style(fig, 200, xaxis=False)


def seniority(labels, counts):
    top = max(counts)
    fig = go.Figure(go.Bar(x=labels, y=counts, text=counts,
                           textposition="outside", cliponaxis=False,
                           marker_color=[BLUE if c == top else
                                         BLUE_MID if c >= top * .55 else BLUE_PALE
                                         for c in counts]))
    fig.update_yaxes(showgrid=True, gridcolor="#E5E5E5", range=[0, top + 1.4])
    return style(fig, 220)


def readiness_radar(dims, you):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[1] * len(dims) + [1], theta=dims + [dims[0]],
                  mode="lines", name="Market expectation",
                  line=dict(color=GREEN, dash="dash", width=1.5)))
    fig.add_trace(go.Scatterpolar(r=you + [you[0]], theta=dims + [dims[0]],
                  fill="toself", name="Your evidence",
                  fillcolor="rgba(31,79,216,.18)", line=dict(color=BLUE, width=2)))
    fig.update_polars(radialaxis=dict(range=[0, 1], showticklabels=False,
                                      gridcolor="#ECEAE4"),
                      angularaxis=dict(gridcolor="#F0EFE9", tickfont=dict(size=11.5)))
    fig.update_layout(showlegend=True,
                      legend=dict(orientation="h", y=-.08, font_size=11))
    return style(fig, 300, xaxis=False)


def coverage(strong=4, transferable=3, gap=4, unknown=3):
    segs = [("Strong match", strong, BLUE), ("Transferable", transferable, BLUE_MID),
            ("Gap", gap, AMBER), ("Not observable", unknown, GREY)]
    fig = go.Figure([go.Bar(y=[""], x=[n], orientation="h", name=lbl, marker_color=c,
                            text=[n], textposition="inside", insidetextfont_size=13)
                     for lbl, n, c in segs])
    fig.update_layout(barmode="stack", showlegend=True,
                      legend=dict(orientation="h", y=-.4, font_size=11.5))
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    return style(fig, 120, xaxis=False)


def roadmap(phases):
    """phases: [(name, start_month, end_month), ...]"""
    colors = [BLUE, BLUE_MID, GREEN]
    fig = go.Figure([
        go.Bar(y=[f"Phase {i+1}"], x=[e - s], base=s, orientation="h", width=.5,
               marker_color=colors[i % 3], text=name,
               textposition="inside", insidetextanchor="start",
               insidetextfont=dict(size=13,
                   color="#1c3d29" if colors[i % 3] == GREEN else "#ffffff"))
        for i, (name, s, e) in enumerate(phases)])
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(range=[0, max(e for _, _, e in phases)],
                     tickvals=[0, 6, 12, 18, 24], ticksuffix=" mo",
                     showgrid=True, gridcolor="#E5E5E5")
    fig.update_yaxes(autorange="reversed")
    return style(fig, 200)


def compensation(points):
    fig = go.Figure(go.Box(x=points, boxpoints=False, orientation="h", name="",
                           marker_color=BLUE, fillcolor="#7C9BE8", line_width=1.5))
    fig.update_xaxes(tickprefix="$", ticksuffix="K",
                     showgrid=True, gridcolor="#E5E5E5")
    fig.update_yaxes(visible=False)
    return style(fig, 150)
```

Use months-as-integers for the roadmap axis, never datetimes — `px.timeline` forces a date axis and the "0 / 6 / 12 / 18 / 24" ruler reads better as an offset.

---

## 7. Plan options — the only genuinely interactive piece

```python
import streamlit as st
from data import PATHS
import charts

def render():
    st.title("Your career strategy")
    st.write("Three ways to reach the same target. Choose one to see its roadmap — "
             "a draft evidence-building path, not a guarantee of role attainment.")
    st.badge("Plan status: draft", color="grey")
    st.badge("Candidate accessibility: aspirational", color="orange")

    st.subheader("Compare your options")
    for col, p in zip(st.columns(3), PATHS):
        chosen = st.session_state.path == p["id"]
        with col, st.container(border=True):
            head, tag = st.columns([2, 1])
            head.markdown(f"**{p['title']}**")
            with tag:
                st.badge(p["tag"],
                         color="green" if p["tag"] == "Recommended" else "grey")
            st.caption(p["body"])
            st.caption(p["route"])

            m1, m2 = st.columns(2)
            m1.metric("Time to target", p["time"])
            m2.metric("Evidence items", p["items"])

            for label, (val, txt) in p["scores"].items():
                st.progress(val, text=f"{label} — {txt}")

            (st.info if chosen else st.caption)(p["trade"])

            st.button("Selected ✓" if chosen else "Choose this path",
                      key=f"path_{p['id']}", use_container_width=True,
                      type="primary" if chosen else "secondary", disabled=chosen,
                      on_click=lambda i=p["id"]: st.session_state.update(path=i))

    sel = next(p for p in PATHS if p["id"] == st.session_state.path)
    st.subheader(f"Phased roadmap — {sel['title']}")
    st.plotly_chart(charts.roadmap(sel["phases"]), use_container_width=True,
                    config={"displayModeBar": False})
    # …phase cards, risks, assumptions, approval row
```

The selected card is marked by the **filled primary button + `✓`**, not an inverted background — Streamlit owns container backgrounds and fighting that is where CSS hacks begin. Everything below the cards reads `st.session_state.path`, so selection propagates on the natural rerun with no extra wiring.

---

## 8. Demo dataset — `data.py`

```python
REQUIREMENTS = [("Python", .87), ("Solution architecture", .80),
                ("Cloud AI platforms", .73), ("RAG / retrieval", .53),
                ("LLM deployment", .47), ("Stakeholder leadership", .27)]

SENIORITY = (["Mid", "Senior", "Lead", "Principal"], [2, 7, 4, 2])
WORK_MODE = {"Hybrid": .60, "Remote": .27, "On-site": .13}
CONCENTRATION = (6, 3, 6)          # top 3 / next 4 / long tail
COMPENSATION = [110, 132, 148, 158, 172, 186, 215]   # $K, 6 disclosed postings

RELATED_TITLES = [
    {"title": "GenAI Solutions Architect", "postings": 9, "overlap": "High"},
    {"title": "AI Platform Architect",     "postings": 7, "overlap": "High"},
    {"title": "AI Automation Architect",   "postings": 5, "overlap": "Medium"},
    {"title": "Cloud AI Architect",        "postings": 4, "overlap": "Medium"},
]

RADAR_DIMS = ["Solution design", "Delivery", "Stakeholder",
              "Architecture", "AI depth"]
RADAR_YOU  = [.60, .67, .65, .32, .38]

GAPS = [
    {"dim": "Skill",      "title": "RAG and cloud AI depth",
     "weight": .73, "distance": .68, "evidence": "0 items"},
    {"dim": "Leadership", "title": "Architecture ownership",
     "weight": .80, "distance": .60, "evidence": "0 items"},
    {"dim": "Experience", "title": "Production LLM delivery",
     "weight": .47, "distance": .45, "evidence": "1 partial"},
    {"dim": "Evidence",   "title": "AI architecture case study",
     "weight": .40, "distance": .35, "evidence": "0 items"},
]

PATHS = [
    {"id": "direct", "title": "Direct climb", "tag": "Fastest",
     "time": "18 mo", "items": "5",
     "body": "Stay in your current role and build all missing evidence in place, "
             "then apply straight to the target.",
     "route": "Senior UiPath Developer → AI Solutions Architect",
     "scores": {"Likelihood": (.40, "Low–moderate"),
                "Effort load": (.85, "High"),
                "Risk if market shifts": (.80, "High")},
     "trade": "Fastest on paper, but everything rests on one unproven jump.",
     "phases": [("Evidence build", 0, 12), ("Apply", 12, 18)]},

    {"id": "bridge", "title": "Bridge route", "tag": "Recommended",
     "time": "24 mo", "items": "4",
     "body": "Take an AI Automation Engineer step first — it converts your "
             "automation background into AI delivery evidence.",
     "route": "Senior UiPath Developer → AI Automation Engineer "
              "→ AI Solutions Architect",
     "scores": {"Likelihood": (.80, "High"),
                "Effort load": (.60, "Moderate"),
                "Risk if market shifts": (.40, "Low–moderate")},
     "trade": "Strong overlap with what you already have; adds six months.",
     "phases": [("Evidence foundation", 0, 6),
                ("Bridge-role readiness", 6, 14),
                ("Target-role readiness", 14, 24)]},

    {"id": "lateral", "title": "Depth first", "tag": "Lowest load",
     "time": "30 mo", "items": "3",
     "body": "Go deep on AI engineering craft before any title change, then move "
             "once with unusually strong evidence.",
     "route": "Senior UiPath Developer → deep AI practice "
              "→ AI Solutions Architect",
     "scores": {"Likelihood": (.60, "Moderate"),
                "Effort load": (.40, "Low–moderate"),
                "Risk if market shifts": (.60, "Moderate")},
     "trade": "Lowest weekly load and best evidence, slowest to a new title.",
     "phases": [("Deep practice", 0, 20), ("Move", 20, 30)]},
]

MARKET_META = {"postings": 15, "employers": 11, "retrieved": "2 Sep 2026",
               "availability": ("Strong", .78),
               "confidence": ("Moderate", .50),
               "disclosed_comp": 6}
```

All of it is synthetic. Keep the `st.badge("Synthetic data")` and the "not a complete market count" caption until real retrieval is wired in.

---

## 9. Copy rules

- Sentence case for every label and heading. No title case.
- State the sample next to the claim: "Share of 15 validated postings", "6 of 15 postings disclosed a range".
- Name confidence in words (Strong / Moderate / Low), never as a bare percentage.
- Assumptions are labelled as assumptions. Risks are labelled with severity.
- Never write "guaranteed", "will", or "you should". Write "observed", "may", "supported by".

---

## 10. Build order

1. `config.toml`, then `charts.py` with `style()` + `requirement_frequency()` — confirms the palette on screen.
2. `app.py` shell and sidebar router.
3. Market page (proves the whole chart layer).
4. Analysis page (radar, coverage, `ProgressColumn` table).
5. Plan page (option cards → session state → roadmap).
6. Home, Profile, Goal — almost entirely stock widgets.

## 11. Accepted constraints

Choices, not compromises — they are why no CSS is needed:

- Cards are `st.container(border=True)`; no custom padding or shadows.
- Selection shows as button state, never an inverted card.
- Metric type sizes are Streamlit's.
- Chart legends become `st.caption` lines wherever a Plotly legend would crowd.
- Page is fluid `layout="wide"`; the mock is drawn at 1280px but nothing breaks wider.
- Chart modebars off everywhere.

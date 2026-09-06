# Career Navigator — Streamlit redesign handoff

Hand this folder to an AI coding agent.

**Prompt to paste:**

> Read `CAREER_NAVIGATOR_SPEC.md` in full and look at the screenshots in `screens/`.
> Build the Streamlit app exactly as specified. Use only the widgets and Plotly code
> given in the spec — do not inject custom CSS. Start with `.streamlit/config.toml`,
> then `charts.py`, then `app.py`, then the pages in the build order in section 10.

## Contents

- `CAREER_NAVIGATOR_SPEC.md` — the complete spec: design intent, theme config, widget mapping, screen-by-screen breakdown, all Plotly chart code, the demo dataset, and copy rules.
- `screens/01-home.png` … `screens/06-plan.png` — reference screenshots of every screen.

## The short version

Five stages: Profile → Goal → Market → Analysis → Plan.

Three things changed from the current build:

1. Market and Analysis findings became charts with stated sample sizes, instead of bulleted prose.
2. The Plan stage now offers **three comparable options** (Direct climb / Bridge route / Depth first) scored on time, likelihood, effort and risk; picking one drives the roadmap below.
3. Confidence and limitations sit inline next to each figure, using Streamlit's native callouts.

Everything is built from stock Streamlit widgets plus Plotly. No CSS.

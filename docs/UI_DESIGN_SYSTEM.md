# UI Design System

## Current V1 presentation contract — September 7, 2026

The final `Career Navigator redesign (1).zip` native-Streamlit handoff governs the theme and
widgets: light gray sidebar, readable native radio navigation, native bordered cards and Plotly.
It supersedes earlier dark-toolbar/custom-CSS experiments. Later approved synthesis requirements
supersede the handoff's synthetic radar scores, fixed three-route options and fabricated durations.
Live pages must not manufacture those values merely to resemble a screenshot.

Market uses explicit discovery/validation/analysis denominators, primary-cohort frequencies,
and source limitations. Analysis presents confirmed strengths, structured match mix, synthesis
gaps and calibrated accessibility. Plan renders actual validated milestones; no fixed timeline
means an ordinal roadmap. Summaries follow the roadmap. Provisional evidence is called out on
all three pages. Missing role evidence produces an honest safe stop, not an empty success chart.

Sidebar evidence counts are not a profile-completeness or readiness percentage. Graphs may leave
space for outside labels, but frequency axis ticks never exceed 100%. Responsive chart labels
and legends must remain readable. Validation replays use the production page functions while
remaining visibly synthetic; they are not proof of provider quality or persisted plan approval.

## 1. Purpose

The Career Navigator UI is a production-quality user interface for evidence-based career decisions. Its direction is a clean, professional AI SaaS product with the clarity and restraint expected in financial-services software.

This document defines the visual and interaction foundation. Activity 3A established configuration and structure. Activity 3C implements the production UI shell with synthetic views and temporary UI interactions; live workflow behavior remains deferred.

## 2. Design Principles

1. **Evidence first.** Recommendations appear with their basis, source scope, confidence, and limitations.
2. **Clear hierarchy.** Each screen has one purpose, one primary action, and a predictable reading order.
3. **Trust through precision.** Confirmed facts, inferences, market evidence, and recommendations remain visually distinct.
4. **Progressive disclosure.** Show the decision summary first and make detailed evidence available without overwhelming the user.
5. **Restrained presentation.** Use whitespace, typography, borders, and limited semantic color instead of decoration.
6. **Native where suitable.** Prefer accessible Streamlit controls. Add project-owned components only when they improve consistency or comprehension.
7. **Honest system state.** Loading, partial evidence, uncertainty, failure, and approval state are always explicit.

Avoid default-looking Streamlit pages, sprawling or duplicated navigation, loose widget collections, emoji-heavy presentation, decorative gradients, generated Streamlit CSS class selectors, and unnecessary custom HTML.

## 3. Design Tokens

### Spacing

Use a 4-pixel base scale consistently.

| Token | Size | Typical use |
| --- | ---: | --- |
| `space-1` | 4 px | Tight inline separation |
| `space-2` | 8 px | Icon and label gaps |
| `space-3` | 12 px | Compact component padding |
| `space-4` | 16 px | Standard component padding |
| `space-6` | 24 px | Card sections and form groups |
| `space-8` | 32 px | Major content groups |
| `space-12` | 48 px | Page-section separation |

Do not create arbitrary spacing when an existing token is suitable.

### Radius

| Token | Size | Typical use |
| --- | ---: | --- |
| `radius-sm` | 8 px | Inputs, buttons, badges |
| `radius-md` | 12 px | Standard cards |
| `radius-lg` | 16 px | Prominent summary panels |

### Color

The base interface uses a warm off-white canvas (`#f7f7f5`), white content surfaces, a dark evidence rail (`#12161f`), near-black text, and a restrained blue accent. Semantic color communicates state, not decoration.

| State | Meaning |
| --- | --- |
| Success | Confirmed, approved, or completed |
| Warning | Limitation, uncertainty, or attention required |
| Critical | Blocking failure, invalid state, or destructive consequence |
| Neutral | Context without positive or negative judgment |
| Information | Guidance, current workflow stage, or supporting detail |

Every semantic treatment includes text or an icon with an accessible label. Color alone never carries meaning. Text and interactive controls must meet WCAG 2.2 AA contrast requirements.

## 4. Typography Hierarchy

Use Source Sans 3 with a system-sans fallback for readable product copy. IBM Plex Mono is reserved for compact evidence labels, stage metadata, and numeric display values.

| Style | Suggested size | Weight | Use |
| --- | ---: | ---: | --- |
| Display | 40 px | 700 | Landing-page statement only |
| Heading | 24 px | 600 | Page and major-section titles |
| Subheading | 18 px | 600 | Card and subsection titles |
| Body | 16 px | 400 | Primary content and explanations |
| Caption | 14 px | 400 | Metadata, dates, sources, limitations |

Use sentence case. Avoid long all-caps text. Keep body line length near 60–75 characters when layout permits.

## 5. Layout and Cards

Pages use a centered, readable content width and generous vertical spacing. Related content is grouped into cards; unrelated widgets are never left visually unstructured.

Card patterns:

- **Standard card:** One topic with a heading, body, and optional action.
- **Evidence card:** Claim, evidence type, source, retrieval date, confidence, and limitations.
- **Decision card:** Recommendation, rationale, alternatives, and explicit user action.
- **Summary card:** Compact final values used for review, never as a substitute for evidence.
- **Approval card:** Exact version under review, disclosed limitations, and approve/revise actions.

Cards use subtle borders and surfaces rather than heavy shadows. Nested cards should be rare.

## 6. Badges and Status Patterns

Badges are short labels for state or classification. They must not resemble buttons.

Use badges for confirmation state, evidence maturity, confidence, accessibility, workflow status, and limitations. Use canonical product terminology. A badge includes a visible label and, where needed, nearby explanatory text.

Examples include `Confirmed`, `Inference`, `Moderate confidence`, `Partial evidence`, and `Apply selectively`. Do not communicate nuanced conclusions through an unexplained color or percentage.

## 7. Metric Patterns

Metric cards contain:

1. Value
2. Precise label
3. Scope or qualifier when needed
4. Optional link to supporting evidence

Use “15 validated postings” rather than “15 jobs.” Market counts must state the searched source scope, geography, and retrieval date and must not imply complete market coverage. Exact-title and related-title counts remain separate.

Progress bars are allowed only when backed by a documented measure. Qualitative evidence labels are preferred when no defensible numeric scale exists.

Market and analysis pages use a visual-first reading order. Charts show only existing validated
counts, frequencies, and classifications; they must not derive an undisclosed readiness score.
Requirement-frequency bars, title-mix segments, employer concentration, comparison outcomes, and
gap distributions appear before detailed summary cards. Every chart includes a text label and its
scope so that color or shape is never the only carrier of meaning.

## 8. Button Hierarchy

- **Primary:** The single main forward action, such as `Confirm Profile` or `Approve and Save Plan`.
- **Secondary:** A safe alternative, such as `Revise Goal` or `Save as Draft`.
- **Tertiary:** Low-emphasis disclosure or navigation, such as `View evidence`.
- **Destructive:** Rejection, deletion, or cancellation with clear consequences; use sparingly.

Labels describe the outcome. Avoid vague labels such as `Submit`. Prevent duplicate execution during long-running work and preserve completed state safely.

## 9. Workflow Navigation

The primary workflow is:

```text
Profile → Goal → Market → Analysis → Plan
```

A compact evidence rail shows completed, current, and upcoming stages on desktop. It is the only primary workflow navigation and therefore does not duplicate a horizontal application stepper. The current stage uses a filled treatment; completed stages include a check and text cue in addition to color. Navigation follows application and LangGraph reached-state rules rather than unrestricted links. A small normal-flow context row identifies the current stage without duplicating navigation actions; sticky positioning is avoided because it is unreliable across Streamlit releases.

On narrow screens, the rail collapses to Streamlit's accessible menu control and the context bar remains compact. Users may return only to stages supported by workflow rules, with downstream invalidation explained before changes are applied.

## 10. System States

### Loading

Identify the operation in progress, such as searching exact titles or validating postings. For multi-stage work, show meaningful stage progress rather than a simulated percentage. Disable duplicate actions and preserve validated partial work.

### Error

State what failed, what was preserved, and what the user can do next. Never expose secrets, provider internals, stack traces, or sensitive content. Distinguish recoverable errors from safe terminal failures.

### Partial Evidence

Show available results with a `Partial evidence` status, affected sources or pages, confidence impact, limitations, and retry or continue choices. Partial evidence must never be presented as complete coverage.

### Empty

Explain why no content exists and provide the next useful action. Distinguish no search performed, no validated results, insufficient profile evidence, and filters that excluded results.

### Human Approval

Display the exact profile, goal, inference, or plan version being reviewed. Separate confirmed facts from inferred capabilities. Present limitations before approval and offer approve, revise, reject where applicable, save as draft where supported, and cancel. No inference or plan becomes authoritative merely because it was displayed.

## 11. Accessibility Requirements

- Meet WCAG 2.2 AA contrast and interaction expectations.
- Support keyboard-only navigation with visible focus indicators.
- Use semantic headings in order and meaningful control labels.
- Associate instructions and errors with their fields.
- Do not rely on color, position, or icons alone.
- Provide accessible names for icons and hide decorative elements from assistive technology.
- Keep touch targets at least 44 by 44 CSS pixels where practical.
- Respect browser zoom, text resizing, reduced motion, and high-contrast needs.
- Avoid time-limited interactions unless necessary and user-controllable.
- Announce consequential loading, error, and completion changes appropriately.
- Render user and external content through safe native components; never interpolate it into trusted raw HTML.

## 12. Responsive Layout

Design mobile-first, then enhance for wider screens. Use one column for forms and evidence details on narrow screens. Metric and summary cards may form two- or three-column grids only when content remains readable. Never encode essential order through columns alone.

Allow workflow navigation to compact or scroll without clipping. Tables must reflow, scroll, or become stacked records. Buttons should become full-width when that improves touch use. Test common phone, tablet, laptop, and wide-desktop widths without assuming a fixed viewport.

## 13. Streamlit Implementation Guardrails

- Keep `.streamlit/config.toml` limited to supported global settings and free of secrets.
- Prefer native Streamlit controls and layout primitives when suitable.
- Keep page modules thin and delegate workflow actions to the Application Controller.
- Keep model, MCP, persistence, and career logic out of UI components.
- Use reusable project-owned components for cards, badges, metrics, evidence, timelines, and navigation.
- Target only stable Streamlit selectors such as documented attributes when necessary; never target generated classes such as `.css-1x8cf1d`.
- Follow the final native-Streamlit handoff: do not inject a custom stylesheet into the portal.
- Use Plotly for quantitative graphics and native Streamlit primitives for structure and state.
- Compatibility markup helpers must never receive untrusted content without escaping it and are not
  used for active portal rendering.
- Do not implement functional pages or the complete UI during Activity 3A.

## 14. Planned UI Package

Activity 3C uses this package structure for the synthetic product shell:

```text
src/ai_career_navigator/ui/
├── pages/
│   ├── home.py
│   ├── profile.py
│   ├── goal.py
│   ├── market.py
│   ├── role_analysis.py
│   └── roadmap.py
├── components/
│   ├── cards.py
│   ├── badges.py
│   ├── metrics.py
│   ├── evidence.py
│   ├── timeline.py
│   └── navigation.py
├── theme.py
└── styles.css
```

The modules contain presentation behavior only. Live orchestration, persistence, integrations, and domain services remain outside the UI layer.

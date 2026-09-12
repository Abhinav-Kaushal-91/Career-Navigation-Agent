# UI Design System

## September 12 — corrected reference implementation (supersedes the first visual pass)

- Unconfirmed competencies contribute zero **demonstrated coverage** to the radar, per the
  user's explicit instruction. They remain Unconfirmed in the table and do not become skill
  gaps or change accessibility. Three or more supplied groups can render, including zero groups.
  Missing group membership and processing failure remain distinct from unconfirmed evidence.
- Center all dimension labels, split them at the slash and leave mobile-safe margins. No 0% tick
  or per-dimension numeric prose. Keep left radar and right 2×2 counts from identical public rows.
- The role-ordered competency list uses row numbers, horizontal rules and semantic status colours;
  no evidence paragraphs, employer charts or new numerical importance score.
- Replace the discarded category-box map with Starting point → Next milestone → Decision point
  (only when backed by an actual later application/reassessment step) → Target direction.
  View-step controls reveal actual saved conditions; they do not confirm completion.
- Below it, render a connected vertical 1–2–3 action storyline with topic headings from the
  milestone basis and full unmodified action/completion text. No fake three-step limit.
- A project-owned Streamlit v2 component isolates styles in a shadow root, with no portal-wide
  stylesheet or generated-class overrides. Dynamic content uses textContent, never innerHTML.
  Native controls, approval and theme remain unchanged. Minimum Streamlit is now 1.63 (already
  installed); no additional package was introduced. Phone layout stacks the journey vertically.

## September 12 — competency snapshot and adaptive path overview

Place Your competency snapshot below the verdict. Use native bordered columns: Coverage
by dimension on the left, Your competency matches on the right, with a wide separating gap.
The right side has two-by-two Demonstrated / Transferable / Partial / Unconfirmed metrics.
Show confirmed development needs separately when present. Native panels provide separation
without injecting a custom stylesheet. Preserve native narrow-screen stacking.

Radar labels are centered at their corresponding vertices; adapt to 3–6 meaningful role
groups, not six invented groups. Hide the 0% label. Do not add per-axis count lists or
evidence prose underneath. A short coverage—not readiness—caption is sufficient; the
existing comparison table carries the details. Missing grouping or failed processing shows
an unavailable chart message, not a reassuring filled shape. Counts still describe available rows.

Plan: Your path at a glance precedes numbered actions, one numbered node per real milestone.
Use short milestone-type labels and up to three nodes per row. The map is an ordered overview,
not a duration or completion scale; preserve existing justified timeline details separately.
Short plans stay short. Actual conditions, prerequisites, action wording and Done when checks
remain below. No clickable completion controls in V1. Synthetic visual QA lives in
scripts/visual_components_preview.py and uses demo_data, never live workflow state.

## September 12 — shared plain-language copy across all six directions

Extend the concise leadership presentation language to all assessment/plan routes, not its
leadership verdict or competency list. Use goal-specific direction captions, short complete
explanations, explained strengths, How you compare, What to develop/What needs attention, and
Questions before deciding. Consolidated views use Competency / Your position; preserve partial,
transferable and unconfirmed statuses. Omit unrelated context from the main table, but retain
prerequisites and assessed development needs. Full original comparisons stay in Run details.
Legacy canonical views keep optionality/eligibility in the competency label and their full context
table in details. Never cut an assessment sentence to conceal a condition. Clarification fallback
must remain visible when an older result has CLARIFY findings but no questions array.

Same style is not identical advice: current-market, transition, target-plan, leadership, exploration
and reassessment retain their goal type and existing routing. No hard-coded number of strengths,
gaps or actions. Do not turn exploration into a mandatory destination, or invent historical change
for reassessment. No leadership heading for a non-leadership result. Preserved/saved plans retain
their exact text/version; only new model runs receive new writing instructions.

## September 12 — plain-language leadership assessment and plan

For leadership, show "A credible leadership direction" only for a validated NEAR_TERM_TARGET
with UNCONFIRMED readiness; keep processing-failure and other accessibility states distinct.
This is a direction label, not a positive application decision or duration estimate.
Use a short core-role overview, strength names with one concise explanation, and a two-column
Competency / Your position table containing TARGET records only. UNKNOWN is "Unconfirmed";
confirmed shortfalls are "Needs development". Preserve original statuses and non-target records
in Run details, not in the primary comparison table. Do not repeat unknowns as gap paragraphs.
Show confirmed development needs separately, followed by up to three grouped direct questions
from new model runs. Never slice historical questions and silently discard important conditions.

Plan uses "Your leadership plan", the same direction/readiness heading, one ordered action list,
one observable completion per step, confidence and no-fixed-timeline semantics. Application gates
are attached before plan creation, not substituted during rendering; approved/historical plans
are never rewritten by UI refresh. Keep exact-version approval and session-only saving notice.

## September 11 — distinguish empty discovery from excluded results

When no postings are retained, distinguish a provider returning zero from returned records
excluded during normalization/validation. If historical retrieval details are absent, say so.
Run details contains the saved query, returned/retained counts and a single posting/outcome/reason
table. No extra API call is triggered by opening details. Empty role input never means the
candidate lacks skills or that the model failed; keep profile strengths and plan guards intact.

## September 11 — readable failure diagnostics

Live-analysis recovery shows a specific, concise reason and an allowlisted error code. One
optional Failure details expander contains sanitized stage/timing/ID information and whether
a local record was saved. Keep this available on the confirmed-goal page after rerender too.
Never show raw exception text, traces or provider responses. Preserve confirmed inputs and
existing explicit retry/back actions; diagnostics do not start another API request.

## September 11 — limited sample versus assessment processing status

For concise-v2-fit-scope results, COMMON is displayed as Core role work, not market frequency.
One reviewed description receives a short role-specific scope note without blocking a supported
fit verdict. When processing_issues exist (including historical results) or no verdict is present,
show Assessment needs review once, preserve comparisons, and keep exact failed checks in Run
details. Do not present a processing failure as Insufficient candidate evidence. Valid substantive
insufficient-evidence assessments retain that verdict. No automatic positive fit or plan approval.

## September 11 — public-copy contract across assessment and Plan

Future concise-v1 same-role/transition results use one or two complete sentences for readiness
and a combined two/three-sentence role overview, not an employer inventory. Keep material
conditions and uncertainty; never truncate a concise result to its first sentence. Plan keeps
one action and one observable completion check per step, plus confidence and timing. References
stay in structured fields/details. Older saved model output is preserved, not retroactively
regenerated. No semantic scoring, schema thresholds, reference validation or approval changes.

## September 11 — combined role review, not inline source commentary

For same-role and transition assessments, show a brief readiness conclusion and
"What this role involves": shared expectations, specialist skills and optional advantages
from the existing classified competencies. Keep one brief reviewed-description scope note.
Strengths are names, not repeated evidence paragraphs. Original model rationale, role
narrative, source IDs and individual-posting analysis belong in optional Run details.
Never change stored evidence or accessibility to achieve this presentation.

## September 10 — approved five-description Analysis composition

The latest Analysis composition supersedes the main/aside assessment layout below:
one verdict card, short role-picture block, full-width numbered competency/status table,
gaps and clarification blocks, then one next-step action. Duties belong in the role picture,
not the batch competency table. Specialist conditions remain in Run details. Show Core,
Supporting, Eligibility or Additional advantage with Yes / Transferable / Partial / No /
Unknown. For a satisfied OR expectation show the demonstrated alternative, not both skills.
Do not duplicate source paragraphs or add a model-generated percentage. Preserve the existing
compact native theme, maximum-1120px content width and exact-version Plan approval.

## September 10 — reference-aligned native UI overhaul

This is the latest presentation contract and supersedes conflicting older mock-screen
instructions below. Reference: Career Navigator redesign (1).zip, handoff spec and
Home/Analysis/Plan screenshots. Preserve its white/gray/blue native Streamlit language,
compact heading hierarchy, aligned cards and clear main/secondary content separation.

- Use a centered, maximum 1120px native container and 15px base type; headings use
  the shared theme rather than inline styles or generated CSS selectors.
- Home has a concise introduction, existing primary actions and four aligned benefit cards.
- Profile progress uses short labels with full-name tooltips; section actions have
  enough width to avoid clipping. Input ownership and AI confirmation are unchanged.
- Goal's six directions use equally sized content areas with the button inside each card.
- Career assessment stays merged: verdict/confidence, one static competency table,
  key gap names/severity, next step and bounded-sample context. Details are optional.
- Plan shows supported choices only when there is a real choice, one action sequence,
  route/strength context and one version-specific approval area. No repeated roadmap,
  priority list and summary presenting the same actions three times.
- Preserve Unknown, employer-specific context, insufficient-evidence stopping and
  no-fixed-timeline semantics. Do not resurrect mock fit scores, probabilities,
  unsupported paths, or decorative market charts.
- Technical/source details remain in Run details or Plan details. This is not a
  provider prompt or evidence-threshold change.

See UI_OVERHAUL_QA.md for verification scope and remaining limitations.

## September 10 — concise assessment surface

Show the verdict/confidence once, the competency table once, material gap names
with severity, and one short next-step sentence. Remove repeated strength/meaning
summaries and evidence narratives from the main page. Retain source notes, detailed
rationale, named clarifications, processing diagnostics and posting audit in one
optional Run details section, without nested Streamlit expanders. Keep insufficient
states, unknown labels, material gaps and plan-navigation safeguards visible/intact.
This is presentation-only; no relaxation of grounding or model validation.

## September 10 — compact competency comparison

The employer-expectation section is one static numbered table: competency,
short context label and one-word candidate status. No per-dimension dropdowns,
nested comparison/source expanders or supporting-evidence paragraphs in this block.
Use Yes / Transferable / Partial / No / Unknown; reserve No for a confirmed unmet
or contradicted condition. Failed, pending and low-confidence comparisons remain
Unknown. Related-role rows are context, not readiness judgments. Preserve canonical
records and source audit elsewhere; this presentation does not change assessments.

## Current assessment presentation — September 9, 2026

The approved combined Career assessment page supersedes the separate Market/Analysis
presentation and visual-first chart instructions below. The visible workflow is
Profile → Goal → Career assessment → Plan. Legacy Market and Analysis route keys
remain compatible aliases; business stages and evidence-scope safeguards stay separate.

Lead with the existing calibrated assessment, then employer expectations beside candidate
evidence, demonstrated strengths, direction/opportunity context, gaps and clarifications.
Use professional technical, business, interpersonal, leadership, people-management,
delivery and eligibility dimensions only when supported. Do not score EQ/personality.
Exact/variant/related counts, sources, query audit and coverage belong in expandable
details. No frequency, title-mix, concentration pie or readiness-percentage charts on
the combined page. Plan retains evidence-supported roadmap rendering and approval guards.

Unknown evidence is a question, not proof of inability. Missing market evidence must
not erase confirmed profile strengths or imply rejection. No generated plan means no
enabled Continue to Plan action. Existing sessions are never reset merely to preview UI.

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

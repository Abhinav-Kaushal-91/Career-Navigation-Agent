# Current State

## GitHub handoff checks — September 7, 2026

The user requested publication of the accumulated code, regression tests and documentation to
the existing GitHub repository. Pre-publication verification: 791 tests passed in 21.96 seconds;
Ruff passed across `src`, `tests` and `scripts`. Temporary test directories and artifact work
are now explicitly ignored alongside credentials, local databases, logs and generated outputs.
This is a source-code checkpoint, not a live release certification or a website deployment.
The full-description retrieval and live acceptance limitations below remain open.

## Retrieval improvement checkpoint — September 7, 2026

Targeted retrieval defects were corrected: strict ATS/open-employer query lanes, supported
Contents formats and MCP envelope parsing, vacancy section boundaries, explicit Adzuna excerpts,
non-destructive identity-checked completion and post-completion deduplication.
Final integrated suite: 791 tests passed; market and diagnostic lint checks passed.

Live retrieval still does **not** pass full-description acceptance. The repaired retrieval check
retained 9 postings from 7 employers, all short excerpts; no full body was recovered. A separate
quoted-city/wider-index probe improved Toronto-specific URL discovery, but its three fetched pages
were a loading shell, closed job and 404. No candidate data or model calls were involved.

See [retrieval improvement record](RETRIEVAL_IMPROVEMENT_20260907.md). The earlier V1 release
acceptance gate remains open; these checks do not replace it.

## V1 reliability checkpoint — September 7, 2026

The generic implementation is in validation; **live release acceptance remains open**. This
checkpoint supersedes historical success statements below for the current change set.

- Implemented primary-cohort title/seniority selection, vacancy identity, qualifier provenance,
  responsibility/qualification separation, AND/OR protection and employer-specific conditions.
- Comparison preserves unknown versus unmet evidence and rejects contribution-as-ownership and
  unrelated-evidence-as-prerequisite-failure. Synthesis and Plan retain validated lineage.
- Same-role apply-ready paths avoid invented bridges/training; no fixed timeline is valid.
- Canonical-role confidence caps downstream assessment/synthesis/plan confidence without
  changing candidate accessibility solely because the market sample is limited.
- Shared website/gateway settings, bounded opt-in local model inspection and safe diagnostics.
- Native Market/Analysis/Plan rendering reviewed in a real browser for full, provisional and
  insufficient-evidence states; explicit sample/confidence limitations and no fake readiness score.
- Twelve frozen production-graph cases: original rubric 11/12, revised policy-correct rubric 12/12;
  original failure and revision reason are retained. These are not live semantic-model tests.
- Final integrated verification: 713 tests passed; changed-file lint and diff checks passed.
- One real-provider synthetic same-role run: 10 retained vacancies, 5 selected descriptions of
  500 characters, 4 schema-valid responses, only 2 postings with accepted statements. It safely
  withheld synthesis/accessibility/Plan. This is a failed happy-path acceptance attempt.
- New content-completion/quality diagnostics are validated offline; they do not turn that
  saved live failure into a pass. A new bounded live acceptance check remains necessary.
- Excel includes current expected/actual results and all 100 original golden expectations marked
  not rerun; historic observations stay separate.

See [V1 validation record](V1_RELIABILITY_VALIDATION.md) and
[V1 model contracts](V1_MODEL_CONTRACTS.md). No public deployment or git push was performed
during that earlier validation activity.

## Generic Career Assessment Synthesis

- Status: Implemented and regression-tested on September 5, 2026
- Placement: After raw gap/accessibility analysis and before bridge, timeline, and plan logic
- Model responsibility: Semantic grouping and concise explanation only
- Deterministic responsibility: Severity, frequency, accessibility, confidence, counts, and ID validation
- Analysis page: Uses synthesized advantages, transfers, grouped gaps, summary, and rationale
- Plan generation: Uses synthesis ordering and accessibility while retaining raw `GapItem` IDs
- Plan wording model: Remains disabled in production orchestration
- Generic regression scenarios: AI Product Manager, Engineering Manager, Product Manager,
  Data Scientist, and Junior Business Analyst
- Accessibility calibration: Uses weighted primary-scope evidence, independent severe dimensions,
  structured gap grouping, prerequisite blocking, and confidence ceilings
- Explicit comparison scopes: Exact target, target variant, and related title
- Grouped-gap audit metadata: Raw count, severe count, requirement composition, and dimensions

## Activity 8 Market Source Architecture Update

- Adzuna-to-requirement handoff: Fixed; structured postings bypass web segmentation
- Requirement-quality refinement: Implemented and validated on September 4, 2026
- Capability, prerequisite, and rejected-metadata QA counts: Reported separately
- Bounded combined live QA: Stopped before candidate comparison as required
- Live extraction selection: 5 postings (3 exact, 1 target variant, 1 related)
- Latest live NVIDIA reliability run: 6 calls including one repair; 4 of 5 analyzed
- Candidate-comparison extraction gate: Passed
- Remaining live failure: 1 repeated strict schema failure; no timeout
- Latest You.com enrichment: 2 attempts, 0 accepted because conflict checks rejected both

- Adzuna primary structured adapter: Implemented offline
- You.com role: Concurrent bounded web discovery plus matching thin-record enrichment
- Parallel source provenance, confidence, conflict handling, and deduplication: Implemented
- Fake Adzuna and combined-service tests: Implemented
- Adzuna live request: Performed through the bounded combined QA script
- Combined Adzuna/You.com/NVIDIA live run: Performed; no candidate comparison
- Next: Candidate comparison may proceed with confirmed candidate evidence

- Activity 0: Complete
- Activity 1: Complete
- Activity 2: In Progress
- Activity 2A-1A — Complete
- Activity 2A-1B — Complete
- Activity 2A-2 — Complete
- Activity 2A — Complete
- Activity 2B — In Progress
- Activity 2B-1 — Complete
- Activity 2B-2 — Complete
- Activity 2B-3 — In Progress
- Activity 2B-3A — Complete
- Activity 2B-3B — Complete
- Activity 2B-3C — In Progress
- Activity 2B-3C-1 — Complete
- Activity 2B-3C-2 — Complete
- Activity 2B-3C — Complete
- Activity 2B-3 — Complete
- Activity 2B-4 — In Progress
- Activity 2B-4A — Complete
- Activity 2B-4B — Complete
- Activity 2B-4C — Complete
- Activity 2B-4 — Complete
- Activity 2B-5 — In Progress
- Activity 2B-5A — Complete
- Activity 2B-5B — Complete
- Activity 2B-5 — Complete
- Activity 2B — Complete
- Activity 2C — Complete
- Activity 2D — Complete
- Activity 2E — Complete
- Activity 2F — Complete
- Activity 2G — Complete
- Activity 2 — COMPLETE
- Architecture: Frozen
- Implementation Target: V1
- V1 implementation: In progress
- V1 implementation-scope checkpoint: Complete
- Activity 3: Complete
- Activity 3A: Complete
- Activity 3B: Complete
- Activity 3C: Complete
- Activity 4A: Complete
- Activity 4B: Complete
- Activity 4C: Complete
- Activity 4D: Complete
- Activity 5A: Complete
- Activity 5B: Complete
- Activity 5C: Complete
- Activity 6A: Complete
- Activity 6B: Complete
- Activity 6C: Complete
- Activity 7A: Complete
- Activity 7B: Complete
- Production UI foundation checkpoint: Complete
- Python environment: Established
- Configuration foundation: Implemented
- UI design foundation: Implemented
- Domain schemas: Implemented
- V1 UI shell: Implemented with synthetic data
- Workflow navigation refinement: Complete
- Model Gateway: Implemented
- Provider abstraction: Implemented
- External provider: Fireworks adapter foundation implemented
- Live provider call: Not performed
- Profile onboarding: Implemented
- Profile confirmation: Implemented
- Document import: Deferred
- AI capability inference: Implemented
- Human inference review: Implemented
- Career goal: Confirmed
- You.com MCP: Connected at adapter/service level
- Current market retrieval: Implemented
- Current market evidence processing: Implemented
- Posting segmentation and requirement extraction: Implemented
- LangGraph: Implemented through final plan review and checkpoint-scoped finalization
- Checkpointing: Implemented with an in-memory workflow checkpointer
- Candidate profile: Accepted as confirmed graph input
- Goal: Accepted as confirmed graph input
- Market retrieval: Orchestrated
- Requirement processing: Orchestrated
- Current market signals: Opportunity Availability, Employer Diversity, Market Concentration, and Evidence Confidence
- Historical market: Deferred
- Candidate requirement comparison: Implemented
- Direct, transferable, partial, and no-confirmed-match handling: Implemented
- Overall percentage score: Not used
- Gap analysis: Implemented
- Gap severity and hard-blocker policy: Implemented
- Candidate accessibility: Implemented
- RoleAssessment: Implemented
- Bridge role assessment: Implemented from observed related-title evidence
- Timeline assessment: Implemented with qualitative classifications
- Career path assessment: Implemented
- CareerPlan: Implemented as a versioned draft with exact-version human review
- Plan milestones: Implemented with gap and dependency traceability
- Path-aware roadmap: Implemented
- Plan approval: Implemented in workflow/checkpoint state only
- Plan revision routing: Implemented with dependency-aware invalidation
- Final plan review: Implemented
- Human approval: Implemented
- Revision routing: Implemented
- Final workflow statuses: Implemented
- Database persistence: Not implemented
- Persistence: Not implemented
- Historical market: Deferred
- Next: Continue Activity 8 live end-to-end validation beyond the bounded market slice

- Functional implementation: Model Gateway foundation implemented
- Foundational dependencies: Installed
- External integrations: You.com MCP and NVIDIA NIM adapters implemented and live-smoke validated
- Database: Not created
- LangGraph: Installed and implemented through the Activity 7B workflow slice
- LangChain: Not installed
- MCP: Official Python SDK installed; You.com Streamable HTTP adapter implemented

Activities 0 through 2, Activities 3A through 3C, Activities 4A through 4D,
Activities 5A through 5C, Activities 6A through 6C, and Activities 7A through 7B are complete.
Activity 7B adds a true final-plan interrupt, exact plan ID/version validation, typed human actions,
checkpoint-scoped action records, terminal result handling, and four dependency-aware revision
routes. Approval creates an approved copy rather than mutating the reviewed draft. Activity 8 live
QA exercises bounded You.com retrieval and conditionally gated NVIDIA extraction. Business
persistence, historical
intelligence, durable production checkpointing, and mem0 remain unimplemented.

## Final V1 Visual Pass

The Streamlit shell now uses the approved warm-neutral product language: a compact dark evidence
rail, reached-state workflow navigation, a normal-flow stage context row, Source Sans 3 typography,
IBM Plex Mono metadata, denser cards, restrained semantic labels, and responsive collapse through
the native Streamlit sidebar control. The redesign changes presentation only; live profile,
market, analysis, and plan orchestration remain on the existing provider-neutral workflow.

Market and candidate-analysis results now lead with accessible visual summaries for requirement
frequency, employer concentration, posting-title mix, evidence-match outcomes, and gap distribution.
Existing metric and detail cards follow as supporting summaries; no new scoring or business rule was
introduced.

The dark evidence rail now overrides Streamlit's secondary-button surface at the correct selector
specificity, so completed and available stages remain dark rather than rendering as white tiles.
A retained market snapshot can open the Analysis stage even when no role assessment was produced;
that page shows an explicit insufficient-requirement-evidence state instead of treating Sparse
availability as a navigation failure.

## Native Streamlit Design Handoff

The final handoff supersedes the custom dark-rail presentation. The portal now uses Streamlit's
native light sidebar, radio navigation, containers, metrics, badges, callouts, progress controls,
and theme configuration without injecting a custom stylesheet. Market and Analysis visuals use
Plotly while remaining bound to validated workflow values. The synthetic demo adds a clearly
labelled readiness radar and three selectable path previews; live mode does not synthesize scores
or alternative paths. Goal-direction cards use a consistent height, and sparse live market
evidence can still open the honest limited Analysis state.

## Six-direction Backend QA Matrix

A reusable deterministic backend runner now covers two sample profiles across all six goal
directions. Ten named-target cases reach `CAREER_PLAN_READY` and wait for exact-version human
review. Both targetless career-exploration cases stop at `ROLE_DISCOVERY_REQUIRED`, accurately
recording the current V1 limitation. The generated Excel workbook separates profiles, goal inputs,
backend outputs, and reserved website-traversal fields. Deterministic provider fixtures exercise
the real graph and domain services without claiming live-market coverage.

## Golden Evaluation Dataset

A versioned Excel golden dataset defines 100 question-and-expected-answer cases across profile
evidence, capability inference, all six goal directions, geography, title discovery, source
architecture, requirement extraction, candidate comparison, career plans, and UI/failure states.
Evaluation is meaning-based rather than verbatim and includes required evidence discipline plus
automatic failure conditions for invention, guarantees, secret exposure, and unvalidated output.

The evaluation loop loads the Excel workbook directly, accepts JSONL candidate answers, grades
normalized exact matches without a model call, and optionally uses the configured validation model
for strict structured meaning-match decisions. Each run writes a timestamped summary and per-case
results. Missing, duplicate, unknown, failed-judge, and schema-invalid cases cannot pass silently.
The initial 100-case reference self-check passes at 100%; this validates the harness only, not the
portal or model quality.

## Career-transition live reliability

The named career-transition path has been exercised end to end with live Adzuna and You.com
discovery plus NVIDIA Nemotron extraction and reasoning. Portal requirement extraction is bounded
to five postings even when retrieval retains a larger market snapshot. The extraction prompt now
distinguishes `item_type` from `category` explicitly; the live verification analyzed all five
selected postings and reached `CAREER_PLAN_READY`. Safe logs retain schema-field validation
categories without job descriptions or model reasoning, and market transport failures are
identified separately before any NVIDIA call.

## Live-analysis transition experience

Clicking `Run Live Analysis` now first reruns into a dedicated full-width progress view before any
provider work starts. Seven user-facing stages advance from actual LangGraph node completions;
internal node names and invented percentages are not displayed. The current stage uses a restrained
motion cue with reduced-motion support, completed and pending stages remain explicit, sidebar
navigation is disabled during the active run, and duplicate starts are blocked. Successful runs
continue automatically to Market. Failures replace the active state with safe Retry and Back to
goal actions while preserving the confirmed profile and goal.

## Evidence-first strengths onboarding

Profile onboarding now gathers Experience, Portfolio Projects, and Education/Certifications before
opening one automatic AI-assisted Strengths step. Grounded AI suggestions and literal evidence
matches are selected by default in a removable native chip control; users can add uncatalogued
strengths directly and confirm the list once. Removed inferences remain in profile provenance as
`REJECTED_INFERENCE`, retained inferences become `CONFIRMED_INFERENCE`, and manually added strengths
remain approved `EXPLICIT` evidence. The former manual-first Skills step and manual "Identify
additional capabilities" action are no longer part of the live profile path.

Capability cleaning is deliberately conservative and preserves technical punctuation including
`C#`, `C++`, `CI/CD`, `OAuth2/OIDC`, `AI/ML`, `.NET`, and parentheses. Experience, education, and
certification inputs use a rolling 60-year history window; future experience dates are rejected,
while future education completion requires an explicit expected-completion flag.

## Market, analysis, and plan decision-story redesign

The production Market, Analysis, and Plan pages now map validated graph objects through a dedicated
presentation layer. Market leads with four real metrics and five tabs, then shows semantic
requirement-frequency bars, a distinguishable concentration donut, a zero-safe stacked title-mix
bar, and concise takeaways. Analysis now reconciles direct, transferable, partial, and no-confirmed
match counts from one comparison dataset; presents evidence-backed strength and transfer cards;
uses qualitative readiness findings instead of a synthetic radar score; and groups material gaps
into readable career themes while retaining every underlying gap ID. Plan renders only
engine-supported routes, filters a multiple-bridge roadmap to the selected real option, and blocks
the roadmap and approval controls when required upstream evidence is missing.

Raw workflow limitations are no longer forwarded into plan copy. Compensation, benefit, stock,
and similar posting fragments are removed from user-facing limitations, while internal rejection
diagnostics are either omitted or translated into a single concise requirement-quality statement.
Product-ownership comparisons now require explicit ownership evidence before a transferable match
can be assigned; adjacent discovery evidence may transfer to product discovery but not automatically
to vision, strategy, roadmap, KPI, adoption, or lifecycle ownership. No Market or Plan policy was
changed as part of this Analysis-page correction.

The bounded live AI Product Manager regression for Canada completed through career-plan readiness:
20 validated postings, 5 analyzed postings, 8 requirement comparisons, 0 direct, 0 transferable,
7 partial, 1 no-confirmed match, moderate confidence, and `APPLY_SELECTIVELY`. All 13 NVIDIA calls
succeeded with no failed model calls.

## Plan decision page correction

The production Plan page now treats an approved `No fixed timeline` preference as a valid planning
choice rather than missing evidence. It renders an untimed `NOW`, `NEXT`, optional `BRIDGE` or
`BUILD EVIDENCE`, and `TARGET` sequence without inventing month ranges. A missing timeline on an
unapproved goal remains incomplete, and genuinely insufficient candidate or market evidence still
blocks approval.

Current-role resolution prefers the explicit About value and otherwise uses the most recent active
experience entry. The page displays only engine-produced paths and bridge roles, removes synthetic
likelihood percentages, and maps three to five available material gaps into action cards containing
the action, why it matters, and the evidence needed. Risks remain candidate- or market-grounded;
raw workflow errors are excluded. The shared live/demo renderer was visually checked at desktop
width after a clean Streamlit restart.

A post-change bounded live retry exposed a pre-existing Market ingestion defect before any model
call: one You.com result matched a reported-count pattern with an empty capture, which raised while
converting the capture to an integer. Market was intentionally not changed during this Plan-only
step. The earlier bounded AI Product Manager run reached plan readiness successfully, while the
final Plan behavior is covered by the full deterministic suite.

## Market decision-story refinement

The Market page now answers the target-market question through five evidence-backed dimensions:
opportunity availability, employer diversity, title consistency, geographic spread, and evidence
confidence. Existing market classifications remain authoritative. The presentation translates
them into plain language, retains exact/variant/related title counts, and clearly labels all posting
figures as a bounded searched-source sample rather than a complete market total.

Validated posting locations are now retained as counts on the market snapshot and summarized into
transparent Canadian region groupings for the ranked geography display. Requirement themes contain
only capabilities present in the extracted requirement summary, and every frequency shows its
`N of M` evidence plus the successfully analyzed denominator. The page ends with four compact
takeaways and a two-sentence bridge into Analysis; detailed employers, titles, sources, and sanitized
limitations remain expandable.

The live AI Product Manager/Canada/no-fixed-timeline regression reached `CAREER_PLAN_READY` twice
after the Market parser safeguard. The final run found 20 validated postings from 16 employers,
with 3 exact titles, 0 target variants, 17 related titles, Canada-wide geographic spread, broadly
distributed employers, strong opportunity availability, moderate evidence confidence, and five
successfully analyzed postings. All 11 NVIDIA calls succeeded. Desktop manual QA covered Market,
Analysis, and Plan after a clean Streamlit restart.

## Professional profile onboarding correction

Professional Summary is captured only on About You. The second production onboarding page is now
Professional Profile, with separate Core Competencies and Professional Experience sections on the
same page. The confirmed profile retains the core-competency text separately from Professional
Summary, and AI Strength Identification receives both fields together with approved experience,
project, education, and certification evidence. Legacy in-session `Experience`, `Skills`, and
`Strengths` step names are migrated to the current labels without duplicating inputs.

A production Streamlit regression traverses every onboarding page and proves that the Professional
Summary input appears exactly once. Focused profile and UI verification passes with 54 tests.

## Career synthesis calibration hardening

Career accessibility now uses exact-target and target-variant requirement comparisons as its
primary evidence, while retaining related-title evidence as explicitly secondary context. Direct,
transferable, partial, and no-confirmed-match comparisons contribute internal support weights of
`1.0`, `0.7`, `0.35`, and `0.0`; the weighted value is not displayed as a user score.

High and blocking gaps are assessed by independent career dimensions rather than raw gap count.
Grouped gaps retain their source gap IDs, total and severe counts, mandatory/preferred composition,
and affected dimensions for auditability. Confidence ceilings prevent low-confidence evidence from
producing `APPLY_NOW` or `APPLY_SELECTIVELY`, and related-title-only evidence fails closed as
insufficient. The five generic fixtures now resolve to near-term, aspirational, aspirational,
near-term, and near-term respectively. Full verification passes with 471 tests.

## Analysis rebuilt on Career Assessment Synthesis

The production Analysis page now uses `CareerAssessmentSynthesis` as its only career-level
interpretation. Accessibility, confidence, advantages, transfer mappings, grouped gaps, summaries,
rationales, dimensions, and canonical match counts come directly from synthesis. Raw comparison,
gap, and evidence objects are retained only for provenance and bounded supporting excerpts. If a
synthesis is unavailable, the page fails closed rather than rebuilding a competing story.

The page presents the target assessment, four compact metrics, a count-based five-part evidence-mix
bar, synthesis strength and transfer cards, grouped gap burden, qualitative structured dimensions,
a bounded conclusion, and user-relevant limitations. Internal identifiers, raw enum names, fit
percentages, requirements-covered percentages, provider diagnostics, and the old reconstructed
readiness interpretation are not displayed.

The bounded live AI Product Manager/Canada run completed at `CAREER_PLAN_READY` with no model-call
failures. Analysis reported a near-term target at moderate confidence, one strongest match, one
transfer mapping, five partial matches, and five grouped career gaps. The rationale states that the
transition is credible but still requires stronger direct evidence.

## Plan rebuilt on synthesized career assessment

Plan now uses synthesis for accessibility, strongest advantages, grouped career-gap burden,
rationale, and the career-level story. The recommended route retains deterministic bridge output.
Displayed actions are consolidated by grouped career gap, prioritized by blocker/severity,
independent severe dimensions, mandatory burden, and frequency, while retaining the represented raw
gap IDs and milestone evidence artifacts. Approval checks synthesis confidence, path credibility,
blocking prerequisites, and milestone provenance.

No-fixed-timeline plans render `NOW`, `NEXT`, `BUILD / BRIDGE`, and `TARGET` without dates or zero
month ranges and remain approval-eligible when the other evidence gates pass. Current role falls
back from the explicit profile role to active employment and then completed employment. Optional
plan model refinement remains disabled.

Final end-to-end QA identified and corrected a generic bridge-order defect: an observed senior
director title could previously be recommended as a bridge to a manager-level target. Bridge
candidates above the target's conservative seniority band are now excluded. Aspirational paths with
no valid bridge display as longer development routes rather than direct selective transitions.

## Market exact-versus-expanded evidence alignment

Market remains independent of candidate assessment. Exact target, target variants, related titles,
and expanded market evidence are now explicit separate counts. Availability text identifies when
its signal uses expanded scope, title consistency remains count-derived, and related roles are
clearly secondary context for Analysis. Employer, geography, and confidence conclusions remain
grounded in validated snapshot data.

Requirement themes now use extracted requirement categories instead of product-specific labels.
Every requirement row states its `N of M successfully analyzed postings` denominator. The final
market handoff explains title variation and downstream evidence scope without showing candidate fit,
gaps, or synthesis accessibility.

Final bounded QA on 2026-09-05 completed at `CAREER_PLAN_READY`. The expanded Canada sample contained
20 validated postings: 3 exact targets, 0 target variants, and 17 related titles across 16 employers.
Market reported strong expanded-scope availability, broadly distributed employers, low title
consistency, Canada-wide spread, and moderate confidence from 5 successfully analyzed postings.
Analysis reported an aspirational target at moderate confidence with 5 grouped gap themes. Plan
preserved that same accessibility, found no valid bridge role, rendered a longer development route
with the untimed four-stage roadmap, and remained approval-eligible because its actions retained
valid raw-gap provenance and no blocking prerequisite existed. All 16 NVIDIA calls succeeded.

The same QA exposed a validation edge case when a rejected synthesis response caused deterministic
fallback text to exceed the stricter presentation-schema limits. Fallback fields are now whitespace
normalized and safely bounded; a regression test covers verbose grounded source text. Full
verification passes with 487 tests.

## Demonstrated-strength preservation

Career synthesis now separates what the candidate has demonstrated from how completely that
evidence satisfies the target. Approved, sufficiently mature evidence supporting direct,
transferable, or partial comparisons can appear in `demonstrated_strengths`; no-confirmed-match
comparisons cannot. Employment records remain valid provenance, but a job title is not rendered as
a standalone capability. Exact-target and target-variant alignments are preferred over related-title
duplicates.

Analysis now renders three explicit layers: `What you've demonstrated`, `How it helps with this
target`, and `What you still need to demonstrate`. Partial alignments show both confirmed candidate
evidence and the remaining difference. Gap cards retain internal dimensions but use requirement-
derived display titles and list their underlying target requirements without exposing IDs. The
accessibility calculation is unchanged.

The final bounded AI Product Manager/Canada rerun produced four demonstrated strengths, six primary
target alignments, and five requirement-named gap themes. Accessibility remained policy-derived and
resolved to near-term at moderate confidence for that run. All 15 NVIDIA calls succeeded. Full
verification passes with 492 tests.

## Canonical target-role profile and requirement auditability

Market processing now keeps raw posting requirements for market interpretation and consolidates
exact/variant evidence into a canonical target-role profile for candidate comparison. Related-only
requirements remain contextual, low-support primary signals remain optional, and sparse samples are
explicitly provisional or insufficient. Independent support is employer-deduplicated and each
canonical requirement retains bounded posting, quote, and source-requirement provenance.

Candidate comparison runs once per canonical requirement. Raw gaps preserve the canonical ID and
every underlying source requirement ID, so synthesis and Plan actions stay traceable without
changing the calibrated synthesis or accessibility policy. Workflow checkpoints retain the bounded
profile and audit records; full posting bodies remain transient.

Final live QA on 2026-09-05 retrieved 20 validated AI Product Manager/Canada postings (3 exact,
0 variants, 17 related) and analyzed 3 exact plus 2 related postings. The posting audit caught one
exact listing whose body self-identified as an Insights Manager, preventing its analytics duties
from entering the target profile. Only Manulife supplied accepted primary requirements, so the
profile correctly resolved to insufficient and candidate comparison did not run. All 7 NVIDIA calls
succeeded. The bounded report is in `outputs/canonical-role-profile-live-qa-2026-09-05.md`.

## Controlled target-variant expansion and insufficient-evidence completion

An insufficient canonical profile now triggers at most one observed-title expansion cycle when the
approved goal allows related titles. Up to five related titles and five additional postings are
evaluated. Promotion requires aligned seniority, high overlap across function, ownership, scope,
and outcome, accepted grounded requirement evidence, and exact posting-ID provenance. Every
candidate retains an auditable accepted/rejected decision. No role-specific alias list exists.

The rebuilt profile separately reports exact and variant posting and employer support. A
variant-dependent result is confidence-capped and cannot qualify as stable without meaningful
exact evidence. If the profile remains insufficient, the graph stops at Market with a controlled
`INSUFFICIENT_EVIDENCE` status. Candidate accessibility, gaps, synthesis, and Plan remain absent.
The three live pages provide focused next actions without treating sparse evidence as a platform
failure.

The bounded AI Product Manager/Canada QA on 2026-09-05 found 20 validated postings across 16
employers. The initial profile contained 3 exact, 0 variant, and 17 related postings, but only one
exact employer supplied an accepted primary requirement. Five observed candidate titles were
checked in one validation cycle; none returned sufficient title-specific grounded provenance for
promotion. The final profile therefore remained `INSUFFICIENT`, no accessibility or plan was
created, and all 12 NVIDIA requests completed without provider failure. See
`outputs/target-variant-expansion-live-qa-2026-09-05.md`.

## Requirement-sample clarity and concise demonstrated strengths

Market requirement bars now use successfully analyzed exact-target and validated-variant postings
only. Related-title requirements remain secondary context and cannot change the target-role
frequency. The page states analyzed coverage against all validated postings, identifies the primary
sample denominator, and labels samples below eight primary postings as directional. The duplicate
open requirement table was removed; a collapsed explanation preserves denominator and failure-
handling transparency without repeating the chart.

Analysis `What you've demonstrated` cards now show only the confirmed capability names. Repeated
project descriptions, maturity/confidence captions, target-requirement lists, and nested supporting-
evidence blocks remain available in validated backend objects but are no longer repeated in this
summary section. Target translation and gaps continue in their dedicated sections below.

## Generic comparison and accessibility calibration

The global comparison contract is role-neutral and reports function, ownership, scope, maturity,
and production-context alignment. Candidate and target maturity are deterministic rather than
model-authored. Evidence selection now ranks semantic relevance and capability specificity ahead of
generic employment titles while retaining professional achievements and project evidence on equal,
relevance-based terms.

Partial matches distinguish demonstrated-function maturity gaps, adjacent capabilities, and
ownership/scope gaps. Accessibility applies documented subtype weights and a guarded small-sample
rule; transferable comparisons without a concrete residual no longer create a material gap. Career
gap consolidation uses the structured residual dimensions, and aspirational assessments without a
supported bridge now create a development/reassessment route rather than an immediate target-role
application milestone. The UI displays the backend path type without relabeling it.

Each completed live run writes a bounded JSON QA artifact under `outputs/run-audits`. It includes
posting identity and classification, source-quoted requirement provenance and canonical mapping,
selected evidence IDs/capabilities, deterministic maturities, structured comparison dimensions,
the accessibility result, and the plan route. It excludes full posting bodies and chain-of-thought.

The final AI Engineer/Canada calibration QA on 2026-09-06 completed through
`CAREER_PLAN_READY`: 20 postings were validated (17 exact, 3 related) and five were analyzed. The
provisional canonical profile produced six comparisons: one transferable, two ownership/scope
partials, one location/work-arrangement partial, one no-confirmed-match for ASP.NET MVC, and one
insufficient AI Solution Development comparison after NVIDIA twice exceeded the explanation-length
contract. The policy result remained `ASPIRATIONAL` at low confidence; the generated
`DEVELOPMENT` route contained no application-readiness milestone. The result was not forced toward
near-term. See `outputs/ai-engineer-calibration-live-qa-2026-09-06.json` and its referenced run-audit
artifact for the bounded trace.

## Primary Adzuna + You.com ATS market retrieval

Adzuna and You.com now run concurrently as first-class discovery lanes. You.com uses one dynamic
ATS-focused query and at most one fallback, processes up to ten individual results, and excludes
generic/index pages from canonical evidence. Normalized postings retain provider, source type,
retrieval quality, title class, seniority, selected content, and duplicate provenance. Cross-source
duplicates count once, and the richer direct page wins without losing either provider record.

Requirement analysis now supports up to ten seniority-aligned, employer-diverse primary postings.
Extraction retains role responsibilities, hiring capabilities, prerequisites, preferences, and
non-requirement metadata as distinct meanings. The canonical target-role profile exposes both role
work and candidate expectations, with separate responsibility/qualification support plus provider,
source, employer, posting, title-scope, and quote provenance. Only hiring capabilities and
prerequisites enter comparison; responsibilities and preferences cannot silently become gaps.
Retrieval decisions survive in workflow state and the bounded run-audit JSON. Generic guides,
marketing copy, and work-arrangement metadata cannot enter candidate comparison or planning.

Live AI Engineer/Canada QA produced both expected external-state outcomes. A successful preliminary
run retained 20 unique postings across 17 employers, including two You.com direct postings, and
analyzed ten; it reached a guarded `ASPIRATIONAL`/`DEVELOPMENT` result. Subsequent final-code runs
encountered sparse provider evidence: one retained eight Adzuna postings across eight employers but
no repeated canonical requirement survived, while another retained none. Both stopped safely at
Market with `INSUFFICIENT_EVIDENCE`, no fabricated comparison or Plan, and no NVIDIA transport
failure. The latest bounded report is `outputs/ai-engineer-calibration-live-qa-2026-09-06.json`.

## Career Navigator Baseline V1 evaluation

The reviewed ten-case workbook is now adapted to the live workflow with golden references kept out
of workflow inputs. The named Baseline V1 experiment completed on 2026-09-06 and all ten traces were
accepted by LangSmith. Verdict exact-match accuracy was 0/10. All ten terminal outcomes were
`insufficient_evidence`. Nine cases stopped after market processing without a candidate assessment
because the canonical target-role profile remained insufficient; CN-004 completed matching but
returned the same terminal verdict instead of `ready_now`.
A separate nine-case retry reproduced the market-stage failures.

Actual predictions, runtimes, token counts, trace IDs, and failure-first annotations are recorded in
`outputs/career-navigator-evaluation-baseline-v1/Career_Navigator_Evaluation.xlsx`. Unmeasured
diagnostics and unavailable costs remain blank. The dominant observed failure category is market
evidence validation attrition; no V2 behavior change is included in these results.

## Career Navigator V2 evidence-retention evaluation

V2 makes one focused correction to source-quote verification: Unicode normalization and
punctuation-insensitive token comparison now retain quotes whose wording is unchanged but whose
hyphen or punctuation typography differs from the fetched posting. The verifier still requires the
complete normalized quote token sequence. Unsupported paraphrases remain rejected, and the
two-independent-primary-posting threshold is unchanged.

The separate ten-case V2 experiment completed on 2026-09-06 and all ten trace references were
accepted by LangSmith. Two cases reached assessment versus one in V1. CN-007 changed from a
market-stage failure to the correct `adjacent_fit` verdict. CN-004 again reached assessment but
remained incorrectly classified as `insufficient_evidence`; the other eight cases stopped after
market processing. Verdict accuracy therefore improved from 0/10 to 1/10, with one failure-to-pass
fix and no pass-to-fail regressions.

The V1/V2 comparison is recorded in
`outputs/career-navigator-evaluation-v2/Career_Navigator_Evaluation.xlsx`. Live inputs were not
identical: CN-008 lost the Adzuna lane in V2, CN-009 included truncated content, and rejection mixes
changed in other cases. Operational changes are observations rather than controlled performance
claims.

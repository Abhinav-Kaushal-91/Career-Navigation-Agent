# GLM Plan phase — September 10, 2026

## Follow-up: wording correction implemented

The findings below describe the original diagnostic. The subsequent authorized
wording-only correction uses plan-wording-v4 and a controlled equivalence set.
It accepts resolve/remove uncertainty and narrow grammatical variants, but does
not freely equate proficiency levels, skills, versions, obligations or timelines.
Ordered meaningful-token checks replace unordered token sets; condition movement,
lost repeated anchors, changed numeric bounds and technical symbols are rejected.

After global identity/structure/risks/assumptions validation, each milestone's
action and outcome are checked as a pair. Both original fields are retained if
either fails; accepted wording in other milestones survives. The service reports
SUCCEEDED_WITH_FALLBACK and wording_rejections (milestone_key, field, safe reason)
when any local fallback occurred. Structural or schema/provider failure still
retains the entire original plan. Original IDs and provenance never come from
the edited model text.

Offline replay of the same recorded GLM output:

- Accepted rewritten microservices clarification and reassessment milestones.
- Retained original Java 8 milestone because "great working knowledge" became
  "strong working knowledge"; diagnostic: proficiency or strength qualifier changed.
- All immutable plan fields, draft status and no-fixed-timeline preference preserved.
- No new API call, market retrieval, website restart or current-run replacement.
- Audit and final plan: `outputs/glm-plan-replay/20260910T172634Z/`.

197 tests passed across career services, plan review and the diagnostic tests;
Ruff passed. The existing pytest cache warning remains non-fatal. Accessibility
and the uncertainty-to-development issue are **not corrected by this change**.

## Verdict

The live Plan response completed quickly, but its wording was rejected by the
production validator. The deterministic fallback was retained. More importantly,
the bounded input exposed contradictory synthesis and path-selection behavior.
This is a Plan-contract diagnostic, **not** a successful full five-JD workflow.
No production settings, prompts, policies, website state or approvals changed.

## Reproducible scope

Command: `.\.venv\Scripts\python.exe scripts/benchmark_glm_plan.py --live`

Artifacts: `outputs/glm-plan-check/20260910T171111Z/`

- `request.json`: actual system prompt, user JSON, schema and provider settings.
- `response.txt`: final GLM answer only; no private reasoning traces.
- `metrics.json`: provider duration and token counts.
- `inputs.json`: four saved comparisons, requirements, deterministic synthesis,
  bridge/timeline results, and explicit evidence-ID replay aliases.
- `baseline-plan.json`, `final-plan.json`, `audit.json`, `manifest.json`.

Sources were successful GLM comparison cases saved at 20260910T032403Z and
20260910T033132Z. The latter replaced the earlier failed Java-experience case.
The synthetic demo goal was replayed from 20260909T194458Z: Senior Java Developer,
Canada, no fixed timeline. Source vacancies were not refreshed. Neither that saved
demo run nor the later frozen-market run contained a completed role assessment.
The experimental five-JD consolidated response was not used as validated evidence.

The replay builds an explicitly limited assessment from four saved comparison
cases using production gap, deterministic synthesis, bridge and timeline services.
It caps plan confidence at LOW. It does not represent all extracted requirements,
a complete canonical profile, or a current-market accessibility recommendation.
Run-specific evidence IDs are reconciled only by unique exact capability,
description, maturity and evidence type; source reference is checked when supplied.
Every supporting quote is checked against its mapped description/context/outcome.
Aliases are saved, never applied to production records.

## Live result

| Measure | Observed |
|---|---|
| Provider/model | Fireworks / accounts/fireworks/models/glm-5p3-flash |
| Explicit reasoning effort | high |
| Output ceiling | 30,000 tokens |
| Timeout / retries / calls | 600 seconds / 0 / 1 |
| Response time | 4.34 seconds |
| Input / output tokens | 779 / 208 |
| Finish reason | stop |
| Output | Three compact milestone objects |
| Wording accepted | No |
| Retained result | Original deterministic plan |

Production requests 2,400 tokens in the Plan service, but ModelGateway's configured
30,000-token override determines the actual wire limit. This ceiling was not
approached in this test. No independent reasoning-token split was returned.

GLM asked to clarify Java 8 working knowledge, clarify microservices architecture
experience, and reassess readiness. It introduced no new milestone, certification,
bridge role, training obligation or timeline. The validated final plan retained
all immutable IDs, evidence links, dependencies, draft status and no-fixed-timeline
preference. This preservation includes safe fallback, not acceptance of model wording.

## Findings

### 1. Paraphrase permission conflicts with lexical validation

The prompt permits close paraphrases. `_validate_wording` instead requires nearly
identical normalized token sets, with a small synonym whitelist. GLM changed
"great" to "strong", "resolves" to "removes", "about" to "regarding", and
"refreshed assessment determines" to "updated assessment establishes".
The first rejected field triggers `PlanSynthesisValidationError` with
"model introduced or removed supported plan content". These are not new gaps or
credentials. Qualifier wording still deserves preservation; do not simply remove
validation to accept every paraphrase.

Recommendation: consider deterministic wording for these already-short actions,
or align the allowed paraphrase contract and validator while retaining immutable
links, material qualifiers, polarity and obligation checks.

### 2. Clarification questions become an Aspirational/Development route

Saved comparison tracks:

- Mentoring: direct match, PREFERENCE; correctly not a baseline hiring gate.
- Cloud deployment/containerization: direct match, ROLE_RESPONSIBILITY; correctly
  not automatically promoted to a qualification.
- Java 8 knowledge: partial hiring match with an unanswered clarification.
- Java development/microservices: partial hiring match with an unanswered clarification.

Both hiring gaps have severity INSUFFICIENT_EVIDENCE, not HIGH or BLOCKING.
Nevertheless, synthesis counts both primary comparisons as adjacent partials,
weighted 0.30 each. Their average remains 0.30, below the 0.40 near-term branch.
They are not counted as insufficient comparisons because match_type is non-null
and confidence is not INSUFFICIENT. The final branch selects ASPIRATIONAL.
The path policy then selects DEVELOPMENT; milestones are labeled capability/
maturity development, with a reassessment after "building" evidence.

Recommendation: reconcile uncertainty across comparison, gap and synthesis
statuses before deriving accessibility. An unanswered version/architecture question
must not silently become proof of a development need. Retain preference/duty
separation; do not inflate baseline fit by reclassifying those tracks. Establish
complete target coverage before making any overall recommendation from this slice.

### 3. Rationale contradicts its own classification

The generated deterministic rationale says:

> No material target-role gap remains in the usable comparison evidence.

and then:

> The remaining independent barriers or limited core support make this an Aspirational target.

Uncertainty gaps are absent from the material grouped-gap list, while partial-match
weights still lower accessibility. No severe independent barrier was established
in this slice. The rationale should explicitly state unresolved information and
the assessment limit, not present missing information as a distant transition.

### 4. Plan wording cannot repair the upstream role profile

The Plan call receives a deterministic skeleton, not raw JDs or the full candidate
profile. It can only refine action/outcome text. A different model cannot correct
an incorrectly selected route or invent missing market evidence within this contract.

## Verification

47 targeted tests passed across the diagnostic transport/audit checks, production
plan generation and compact-output contracts. Ruff passed. Pytest reported its
existing Windows cache-path warning; test execution passed. No full-suite or
browser/end-to-end acceptance is claimed.

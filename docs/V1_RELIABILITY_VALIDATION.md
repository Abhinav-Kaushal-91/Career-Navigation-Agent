# V1 reliability implementation and acceptance record

Date: September 7, 2026. This is an implementation/validation checkpoint, not a production
release certificate. Changes are generic across role families and the six goal types.

## Release decision

**Not live-release-ready.** Offline execution and browser presentation have improved, but the
single bounded real-provider happy-path attempt stopped for insufficient usable role evidence.
No result was replaced with demo data, no plan was fabricated, and no additional live scenario
was run to search for a passing result. Code, frozen replays and live-provider quality are
separate claims.

## Implemented scope

- Context-grounded decorated-title equivalence, seniority-aligned primary selection and explicit
  complementary Adzuna/You.com budgets; vacancy identity separate from employer/title equality.
- Responsibilities, hiring capabilities, prerequisites, preferences and metadata retain their
  source meaning. Primary-cohort qualifiers and representative quotes agree; outlier or related
  postings cannot silently redefine the target. AND/OR and optionality remain explicit.
- Grounded comparison retains function, ownership, scope, maturity, production context and
  uncertainty. A contributor quotation cannot become ownership because the model tags it that
  way. Unrelated credential evidence cannot establish an unmet prerequisite.
- Synthesis preserves strengths and generic accessibility calibration. Employer-specific
  conditions and low market confidence do not automatically create a universal career barrier.
  Canonical-role confidence caps assessment, synthesis and plan confidence independently of
  candidate accessibility; a supported direct fit can remain apply-ready with LOW confidence.
- Plans retain validated milestone/evidence/gap lineage. Direct candidates are not forced into
  bridges or training; no fixed timeline is valid and produces an ordered, untimed roadmap.
- Shared website/diagnostic model configuration, bounded schema repairs, and opt-in local
  sanitized model inspection. Unexpected field names are not echoed into ordinary error logs.
- Market/Analysis/Plan use the native design handoff with subsequent evidence-synthesis changes.
  Readable navigation, explicit provisional/empty states and chart denominators replace fake
  readiness percentages. Professional Summary remains on About You; confirmed profile years
  are carried through without claiming years of a particular skill.

Detailed model roles, prompts, schemas, settings and validators:
[V1 model contracts](V1_MODEL_CONTRACTS.md).

## Final automated verification

The integrated test suite passed **713 tests in 22.63 seconds** after the final retrieval,
comparison, confidence, privacy and UI changes. Changed-file Ruff checks and `git diff --check`
also passed. These automated results do not establish live provider or model acceptance.

## Frozen expected-versus-actual checks

`scripts/run_v1_replay.py` executes the production graph/controller with synthetic market and
model recordings. It covers two cases for each of the six goal types. It validates orchestration,
grounding, lineage and deterministic policy, **not** the semantic accuracy of a live model.

The initial reviewed rubric passed 11/12 cases. TARGET-A had three supported direct comparisons,
no material gaps and a provisional two-employer role profile. Its original expectation reduced
candidate accessibility solely for the small market sample. That contradicted the policy that
market confidence and candidate fit are different dimensions. The revised rubric requires the
provisional/limited-confidence warning, every supported comparison, and no invented gap, bridge
or duration. It does not simply accept any emitted verdict. The original failed expectation and
the rationale for revision remain in the JSON and workbook; the revised suite passes 12/12.

Artifacts under `outputs/v1-reliability-20260906/`:

- `replay-results.json`: case inputs, original/revised expectations, outputs, complete serialized
  graph state, source audits, queries and lineage checks.
- `workbook/career_navigator_v1_expected_actual.xlsx`: concise results and failure/success record.
  All 100 historical golden questions/expected answers are preserved and labelled **NOT RERUN**
  for this implementation. Historical observations remain dated, not represented as current passes.

## Bounded live acceptance attempt — failed happy path, successful safe stop

Synthetic CURRENT-A: Senior Java Developer seeking the same role, Toronto, no fixed deadline,
no bridge. The runner used the website runtime and required explicit `--allow-live`. Limits:
six logical searches, twelve content fetches, five selected postings, thirty model calls,
one retry, at most sixty seconds per model attempt and a ten-minute model-run budget.
External telemetry was disabled. The initial sandbox transport failure made no model calls;
the permitted network retry was the same scenario, not an additional test case.

Captured run `be44bc25…`, approximately 248 seconds:

| Observation | Actual result |
|---|---|
| Adzuna | 3 searches; 33 raw results; 26 pre-dedup validated observations |
| You.com | 3 searches; 23 raw results; 0 validated Toronto postings |
| Retained market sample | 10 vacancies, 8 employers |
| Selected for extraction | 5 postings; every supplied description was 500 characters |
| Model calls | 9 actual invocations, 5 schema-rejected attempts; no transport failures |
| Schema-valid posting responses | 4; this did **not** mean four usable full job descriptions |
| Postings with accepted requirement statements | 2 |
| Unsupported source quotes rejected | 22, never promoted to canonical requirements |
| Final state | `MARKET_READY` / `INSUFFICIENT_EVIDENCE` |
| Accessibility, synthesis, plan | Not produced |

The Adzuna adapter did not locally truncate these descriptions. The supplied provider excerpts
were short; two identity-matched enrichment attempts failed and the original snippets were
retained. The saved You.com rejection evidence predominantly shows guides/list pages, contextual
roles, and wrong or unclear geography. There is no retained proof that a valid Toronto ATS body
was wrongly rejected. Relaxing title or geography validation would not be a justified fix.

CGI yielded no accepted requirements (six invented quotes plus metadata); Localcoin yielded none
(sixteen invented quotes plus metadata). Cognizant remained schema-invalid after retry.
Targeted Talent supplied one accepted statement and the decorated Tangentia title supplied five.
This proves a real usable-content/extraction problem, not that the candidate lacks Java skills.

`live-current-a.json` retains the actual saved state and sanitized inspection events. That run
predates query-pass retention and detailed enrichment diagnostics: its discarded query strings
and returned-page identity conflicts cannot be reconstructed honestly. Later audit additions
and content-budget fixes are offline-tested improvements, not retroactive evidence of a passing
live run. Another explicitly bounded live validation is required before release acceptance.

Offline corrections made after this failure:

- The content-completion budget defaults to the analyzed-posting limit rather than two; an
  explicit override remains supported and every attempt still consumes the shared fetch budget.
  Primary relevance, seniority and employer diversity determine completion order.
- Per-post audits retain short-excerpt/unknown/verified-posting quality, input size, completion
  URL/status, identity/failure reason and budget deferral. Long text alone is not labelled complete.
- Schema-valid response counts, grounded-hiring posting counts and rejected-item counts are
  separate. A response whose proposed requirements all fail grounding is `GROUNDING_FAILED`,
  not a successfully analyzed posting, and is excluded from frequency denominators. Valid empty
  extraction remains distinct. None of this retrospectively changes the saved live artifact.

## Manual browser-level QA

An isolated local Streamlit harness (`scripts/v1_browser_qa.py`) loads saved typed graph states
and calls the **production** navigation and Market/Analysis/Plan renderers. It never calls a
provider. Its permanent on-page banner distinguishes frozen synthetic fixtures from captured
live results. It is not a substitute for testing fresh onboarding or persisted approvals.

The supplied ZIP specification and its Market/Analysis/Plan screenshots were read and viewed.
Browser checks at 1280 × 900 included:

| Path | Pages and observed behavior |
|---|---|
| CURRENT-A full | Market → Analysis → Plan; 5 primary postings, 3 direct matches, no artificial gap/bridge, one untimed application step; summary follows roadmap |
| TARGET-A provisional | Sparse two-posting market continues to Analysis and Plan; explicit limited-sample notice on every page, demonstrated strengths preserved |
| REASSESS-A safe stop | Zero-posting Market, withheld candidate comparison, confirmed strengths retained; Plan explains why no plan exists and offers no approval |
| Captured live CURRENT-A | Market retains the ten-posting sample; Analysis withholds a verdict and preserves Java/API/testing evidence, consistent with the backend failure |

Checks covered top content, charts, lower summaries, expanders, navigation and final controls.
They caught and corrected the arbitrary sidebar-completeness percentage, frequency-axis ticks
above 100%, clipped chart labels/legend, narrow summary cards, and a nullable-state reload error.
A zero-result warning no longer claims opportunities were found; a zero denominator has no
coverage percentage. A mobile 390 × 844 check confirmed native stacked content and a collapsible
sidebar without document-level horizontal overflow. This was not an exhaustive device/accessibility
audit. Streamlit sometimes retains scroll position between stages; navigation remains functional.

Actual browser evidence is saved in `outputs/v1-reliability-20260906/browser-qa/`, including
`current-analysis-top.png`, `current-plan-roadmap.png`, `provisional-market.png`,
`provisional-analysis-final.png`, `provisional-plan-final.png`, `insufficient-analysis.png`,
`insufficient-plan.png`, and `mobile-live-analysis.png`. The explicitly named before-fix chart
screenshot is a defect record, not a final-state screenshot.
`current-market-charts-final.png` and `current-market-bottom-final.png` show the corrected label
bounds and aligned summaries. `insufficient-market-final.png` shows the corrected zero-result copy.
The final provisional screenshots were recaptured after the confidence ceiling correction:
Analysis and Plan both retain LOW confidence, the direct verdict, and the untimed route.

## Remaining limitations

- Full-body retrieval and live structured extraction still require another bounded acceptance
  run. Tests cannot establish that an external provider/model will produce usable evidence.
- Exact quotations and semantic guards reduce known errors; they are not a proof of complete
  semantic entailment for every professional domain or ambiguous sentence.
- Historical 100-question evaluations were reviewed, not executed anew against the live model.
- Saved inspection artifacts can contain career-sensitive content even after redaction. They
  are local-only, not anonymous, and should be deleted after review if no longer needed.
- V1 plan approval remains session-scoped in the portal. No public deployment, git push, new
  authentication system or persistence migration was performed in this implementation pass.

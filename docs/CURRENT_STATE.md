# Current State

## September 12 — GitHub checkpoint before goal-choice consolidation

This checkpoint contains the leadership route and shared concise assessment/plan
wording for all six existing goal types. The proposed merge of career transition
and target-role planning has not been implemented; goal selection is unchanged.
Local credentials, generated run outputs and session data are excluded from the
checkpoint. Publishing this code does not deploy or restart the local application.

## September 12 — local application availability verified

The full production entry point is listening at http://127.0.0.1:8533/ and its
Streamlit health endpoint returns `ok`. The server was left running to preserve
existing sessions. Port 8534 is the separate saved-result preview, not the full
manual onboarding workflow. This check did not run another live analysis.

## September 12 — plain-language guidance extended to all six categories

Shared writing guidance now reaches same-role, transition/target planning, leadership, and legacy
synthesis/plan wording contracts. It directs plain second-person wording, concise strength
explanations, grouped questions, conditional application decisions, no fixed example result or
four-step quota, and preservation of ownership/depth boundaries. Role-specific conclusions,
reference checks, retrieval, eligibility and goal routing are unchanged. Consolidated input now
always includes the actual goal_type; legacy synthesis still consumes validated comparisons and
optional plan wording still operates on the immutable skeleton. This is not a new exploration engine.

Both production rendering paths use concise comparisons and explained strengths with original
details retained. Leadership keeps its typed TARGET filter; other consolidated findings retain
core work, prerequisites and actual development needs while unrelated/narrow context stays in
details. Legacy rows retain preferred/eligibility context without extra columns. Partial and
transferable contributions remain distinct from demonstrated and unconfirmed. Clarification text
is shown once, with an older-result fallback if no explicit questions exist. Goal orientation
captions cover all six directions. Plan exact-version approval and session-only saving remain.
Legacy direct-plan completion now records an evidence-supported apply-or-defer decision.

Validation: 912 career/UI/orchestration/market/config tests passed; changed code passed Ruff and
diff whitespace checks. Includes parameterized Streamlit rendering for all six goal categories,
actual action/approval preservation, partial/transferable/unknown status checks and shared prompt
attachment. Existing mocked-result serializer warning remains. No new paid/live six-case run or
manual browser traversal was performed in this activity; automated rendering is not semantic LLM
reliability proof. The known live cloud/microservices over-credit remains a semantic evaluation
case; the shared prompt now explicitly states that boundary, but it has not been live-revalidated.
Existing saved runs and sessions were not reset, rewritten or seeded; new model wording requires
a fresh run. No GitHub push. The prior obsolete case-matrix fixture issue is still separate.

## September 12 — concise leadership guidance implemented

Production leadership prompts and pages now use a short core-role overview, concise explained
strengths, TARGET-only Competency / Your position table and grouped questions. Unknowns remain
Unconfirmed and are no longer repeated in gap paragraphs; confirmed shortfalls remain visible.
Context/excluded records remain in Run details. NEAR_TERM_TARGET with UNCONFIRMED readiness is
presented as "A credible leadership direction" on both pages, not as an application recommendation.
Other verdicts and processing-review states retain their distinctions. No role-specific sample
facts are hard-coded into the production page.

Before creating a new plan, APPLY actions receive a favourable readiness/employer-requirements
condition and an explicit defer/reassess branch; completion is an apply-or-defer decision. Conditional
development retains its typed links with shorter public text. Prompts distinguish formal management
from workstream/coaching experience and preserve ownership verbs across strengths and actions.
Existing stored/approved plan text is not rewritten by rendering. Temperature remains 0.1/0.0
for author/reviewer; retrieval unchanged. New guidance text requires a fresh analysis run.

Validation: 432 career/UI/orchestration tests passed, Ruff passed. New tests cover compact leadership
rendering, audit retention, unknown/failure labels, and application/defer conditions surviving into
the generated plan and completion. Existing test serializer warning remains unrelated.

First saved-five/live-DeepSeek replay: outputs/leadership-review-check/concise-v3/results.json,
144.45s, three calls (author, repair, reviewer), no processing issues, five draft actions.
Manual review found "supported production incidents" overstated as "incident ownership"; preserved
the raw result and tightened author/reviewer ownership instructions before a final replay.

Final saved-five/live-DeepSeek replay: outputs/leadership-review-check/concise-v3-final/results.json,
144.70s, two calls (41.67s author, 102.93s reviewer), no repair, no processing issues, four actions,
three strengths, three questions and nine comparisons (seven TARGET rows visible). Readiness remains
UNCONFIRMED, direction NEAR_TERM_TARGET, confidence MODERATE. Incident-ownership overstatement is
absent; the final action explicitly compares employer requirements before apply/defer. Manual
browser traversal of the production Analysis and Plan renderers in a separately labelled read-only
preview on 8534 confirmed headings, table, questions, conditional plan and disabled approval.
Original app session on 8533 was preserved, not seeded or restarted. This preview uses the saved
backend run, not a new end-to-end browser/live-search run. No GitHub push.

Remaining semantic QA issue: the final model groups "Cloud and microservices delivery" as
DEMONSTRATED although the supplied facts establish AWS/container/REST delivery, not microservices
architecture. The reviewer also repeats a conditional lead-in in the development step. Preserve
these outputs as regressions; the wording change is not universal semantic reliability proof.

## September 12 — actual website leadership validation

Restarted localhost:8533 with current code and traversed the real browser flow: Explore demo,
Education -> live AI Strength Identification -> confirmed three grounded suggestions -> profile
review -> LEADERSHIP_PROGRESSION -> confirmed Software Engineering Manager, Toronto/Metro Area,
related titles allowed, no fixed timeline -> Run Live Analysis -> Career assessment -> Plan.
No saved backend result was injected. The website profile contains 28 confirmed evidence items
(including three new inferred strengths); it is not identical to the earlier nine-item backend
payload. Used live configured JSearch and Fireworks DeepSeek. Final author temperature is 0.1;
repair/review remain 0.0. This run verifies the latest leadership rule version in the UI.

Run audit: outputs/run-audits/226f0862-02fe-4af4-a0ae-c3b215f305c3.json (plus matching retrieval
audit). Five returned/retained/reviewed descriptions, 11 competency rows, five plan actions,
NEAR_TERM_TARGET/MODERATE, UNCONFIRMED current readiness, no processing issues. Mastercard and
Amazon are CORE; Stripe ML management and Fullscript director are CONTEXT; Kepler hardware is
EXCLUDE. The live search cohort differs from the saved replay. Browser-observed total was roughly
four minutes; retrieval audit completed 13:11:46 and assessment audit 13:14:49 local (183 seconds
between artifacts, not measured provider latency). Exact per-call timings are not in this audit.

Manually inspected both pages and screenshots. Technical strengths were retained; unreported
management remains clarification, not a confirmed shortfall. Development action AND completion
carry the condition that earlier clarification confirms missing experience. No invented duration
or forced bridge role in the overview. Plan approval/version and session-only saving notice show.
Left the draft Plan open in the browser; did not approve, save, or apply for any vacancy.

Remaining semantic/UI findings (not changed during this test): final APPLY action says to apply
once management questions are resolved, but resolution may confirm inadequate experience; it
needs an explicit favourable readiness/per-posting eligibility condition and a reassessment branch.
A supervised workstream/coaching assignment should not imply formal people-management experience.
Excluded hardware and contextual specialist/director rows still occupy the main competency table;
overview and repeated clarification text remain wordy. Schema success is not semantic perfection.

## September 12 — structured leadership refinement and temperature 0.1

Implemented in the production leadership route: shorter dedicated prompt; per-posting
CORE/CONTEXT/EXCLUDE benchmark; target/context applicability; explicit evidence state and current
readiness; typed action purposes and after-clarification conditions. Checks enforce source support,
scope, unknown versus shortfall, readiness consistency, action linkage and clarification order.
Code attaches the same condition to development actions and their completion checks, and derives
public readiness from its validated field rather than conflicting free prose. Exact candidate
shortfall excerpts still require semantic review; matching a quote does not prove interpretation.

Assessment/combined-plan authors now use temperature 0.1; integrity repair and independent review
stay 0.0. Legacy career synthesis and plan wording use 0.1. Extraction/retrieval are unchanged.
Existing non-leadership schemas remain compatible; leadership retains its goal and plan approval.

Saved-five-description/live-DeepSeek real-graph test: outputs/leadership-review-check/
temperature-01-refined/results.json, 131.86s, 2 calls (59.36s author, 72.40s reviewer), no search
calls, no repair, no processing issues, WAITING_FOR_HUMAN. Two core postings, two context,
one excluded; 9 comparisons, 4 actions; NEAR_TERM_TARGET/MODERATE with UNCONFIRMED readiness.
Management/delivery history stays UNKNOWN/CLARIFY; platform/budget stays context; development
is conditional in both action and completion. This is not universal model reliability proof.

Preserved failed first refinement at temperature-01/results.json: an old check demanded repeated
development-focus prose despite explicit UNKNOWN/CLARIFY fields (121.29s, 2 calls, no plan).
Removed that redundant requirement only for leadership; substantive validation remains.
The successful replay's overview still suggested a bridge sequence too strongly. Final prompt
reserves progression for conditional plan actions and role_picture for role work only; that final
wording adjustment has contract coverage, not another live replay.

Validation: 891 career/orchestration/UI/market/config tests passed before final wording/storage
refinements; focused leadership/transition tests and saved-assessment round-trip also passed.
New storage bounds accommodate code-added conditions without truncation. No browser run, app
restart or GitHub push. Historical case-matrix fixture failure remains a separate follow-up.

## September 12 — target-led leadership route implemented and live-tested

LEADERSHIP_PROGRESSION with a specified target now uses consolidated five-description
assessment and the validated assessment's plan actions; original goal enum and approval
semantics remain. Search follows the destination, not the current role. Leadership selection
prioritizes target domain/level before description length, preserving employer diversity and
related-role provenance. The model distinguishes mentoring, formal management, team delivery
and higher organizational scope instead of applying a generic management checklist.

Bounded real JSearch + configured Fireworks DeepSeek test: Senior Java Developer demo ->
Software Engineering Manager, Toronto/metro, expansion allowed, no fixed timeline.
outputs/live-failure-check/20260912T160559Z/results.json: 5 returned/retained/reviewed;
2 target variants, 3 related roles; 3 model calls (author, action-basis repair, reviewer).
Retrieval 41.30s, assessment/review 115.60s, total 157.00s. WAITING_FOR_HUMAN, no processing
issues; NEAR_TERM_TARGET/MODERATE, 12 comparisons, 5 plan actions. Hardware, platform and
director opportunities were differentiated from the selected application-team manager target.

Quality review found a remaining interpretation error: the draft prescribed building management
history that was merely unreported. Strengthened author/reviewer instructions to use CLARIFY,
verify first and make development conditional in actions and completion checks; readiness must
remain unconfirmed when decisive prior scope is unknown.

Saved-retrieval/live-DeepSeek real-graph replay: outputs/leadership-review-check/results.json,
70.35s, two model calls, no additional JSearch requests, WAITING_FOR_HUMAN, no processing issues.
13 comparisons, 5 actions, NEAR_TERM_TARGET/MODERATE. First action now verifies prior supervisory
work and formal management is CLARIFY. Interpretation is not fully corrected: rationale still
says "not yet ready" because experience is unconfirmed, some partial/unknown scope is prescribed
as unconditional development, and conditionality is not consistently retained in completion checks.
Do not confuse schema/reference validation success with semantic calibration success.

Verification: 879 tests passed across career/orchestration/UI/market/config (one existing enum
serialization fixture warning). Changed-file Ruff and git diff --check passed. Added real
production-context leadership routing tests, goal preservation/approval/invalidation checks,
generic API destination tests and discipline/level-before-length selection regression.

No UI/browser verification or Git push performed for this activity. Existing per-posting case
matrix fixture failure remains a separate documented follow-up; do not call it fixed here.

## September 12 — original leadership progression live test (historical failure)

User requested testing the leadership role. Ran the unchanged production backend with the
approved synthetic Senior Java Developer profile, LEADERSHIP_PROGRESSION, Engineering Manager,
Toronto/metro, related expansion allowed, no fixed timeline. Report:
outputs/live-failure-check/20260912T155449Z/results.json.
6 returned, 5 retained, all RELATED_TITLE, zero descriptions selected, zero model calls,
INSUFFICIENT_EVIDENCE, no assessment or plan; total 18.34s (retrieval 18.20s).
The four-call test cap was never reached and did not cause this outcome.

Verified cause: leadership progression does not enter uses_consolidated_target_assessment;
it still uses the legacy exact/variant-only batch selector. A second substantive issue is
target ambiguity: Engineering Manager returned manufacturing, steel-building design and hardware
management alongside platform engineering. Do not fix this by blindly accepting all related
postings. Software domain needs to be explicit/confirmed or derived transparently from the goal
and profile, and different disciplines must remain distinct. This turn tested only; no application
code, prompts, model settings, browser session, or published Git state was changed.

## September 12 — GitHub publication checks

Prepared the JSearch integration, timeout/diagnostic fixes, target-plan routing and regression
tests for publication. Fresh combined career/orchestration/UI/market/scripts/config suite:
895 passed, one failed (test_goal_case_matrix_covers_two_sets_for_all_six_goal_types).
The same matrix test also fails on the previously published fd332b5 in an isolated worktree:
its mock provider supplies obsolete schemas. Baseline reports 6 waiting cases versus expected 9;
current reports 4, because target planning now joins the consolidated assessment route and
the mock lacks that response contract too. Do not describe this check as all green or silently
change expected counts. Updating this historical matrix remains follow-up work.
Ruff passed for every pending Python file. Local environment credentials and runtime outputs
remain ignored; pending files were checked against configured secret values before staging.

## September 12 — actual website target-plan routing failure fixed

Inspected the user's existing 8533 browser session, not the earlier backend replay. Its goal
was TARGET_CAREER_PATH (Plan toward a target role), AI engineer, Toronto, Canada, Strict City,
related expansion allowed, no fixed timeline, 29 confirmed synthetic-profile evidence items.
Run details showed 10 returned / 8 retained, all RELATED_TITLE; the legacy batch selector
admitted only exact/variant and selected zero. The earlier successful backend test used
ROLE_TRANSITION, so it did not reproduce this route. This was a verified routing/selection
mismatch, not lack of retrieved descriptions or a model-output validation rejection.

TARGET_CAREER_PATH now shares the consolidated up-to-five assessment/review/plan flow with
ROLE_TRANSITION. The confirmed goal is never rewritten; goal_type is supplied to the model and
retained in the audit. Related scope labels remain unchanged, and related input is skipped if
expansion is disallowed. Other goal routes remain unchanged. The older target-plan extraction
path is available only via explicit legacy_target_plan_pipeline runtime injection for historical
replays (default false, no UI/env flag, no automatic failure fallback).

One live retry was executed by clicking Run Live Analysis in the user's actual existing tab,
without restarting the server or injecting backend results. Run 4d47528c-8699-4c65-b8f1-52b6a1070f50:
10 returned, 7 retained, 5 reviewed, 14 competencies, 6 actions, NEAR_TERM_TARGET / MODERATE,
processing_issues empty, plan DRAFT. Production Analysis displayed the result; Continue to Plan
opened the six actions and exact-version approval controls. Returned to Analysis without approval.
Files: outputs/run-audits/<run-id>.json and outputs/run-audits/retrieval/<run-id>.json.

Regression coverage includes both explicit transition and target-plan directions, all-related
inputs, eight-to-five selection, disallowed expansion, goal preservation, and plan-version
approval/invalidation. 867 broad tests passed plus the new eight-to-five regression separately;
Ruff passed. This proves this route executes, not that all model interpretations are perfect:
mixed seniority/co-op context and unknown-versus-learning wording still merit quality review.

## September 11 — empty transition input and live AI Engineer reproduction

The portal's failed run d32e364a-d38f-4c8d-bbcc-9911c94542cb preserved a zero-posting
snapshot and logged a transition ValueError. Its provider payload/routes were not persisted,
so whether that particular response was empty or entirely excluded remains unverified.
Do not infer the old run's cause from fresh responses.

Same-role/transition empty eligible input now stops without a model call or candidate verdict,
instead of reporting generic model failure. Existing retrieval limitations are preserved on
technical errors. A separate retrieval audit is written before assessment (including empty
runs), with provider counts, query and per-posting routes; no profile, full JDs or reasoning.
Missing transient content remains a technical failure, not an empty market result. Run details
shows retrieved versus retained counts and exclusions; an absent historical summary is explicit.

Actual live backend demo Java-to-AI Engineer run: outputs/live-failure-check/20260912T031746Z.
9 raw, 7 retained, 5 reviewed, 2 DeepSeek calls, assessment and unapproved plan generated,
no processing issues. Retrieval 72.13s; author 53.76s; reviewer 52.42s; total 178.48s.
Verdict NEAR_TERM_TARGET / MODERATE; 17 competencies and 6 actions. AI strength inference
was not rerun; this uses the approved synthetic demo profile, not an export of the user's
28-item browser profile. A separate earlier search returned 10 raw/7 retained in 5.38s.
These demonstrate variable search results/latency and successful execution, not provider SLA.

Remaining quality issue: reviewed cohort includes a co-op and lead role, and broad AI titles
remain classified as related. No relevance or seniority policy relaxation was made here.
Both production assessment/plan renderers accepted the actual saved result with zero UI
exceptions. 661 offline tests passed, Ruff and diff checks passed. No server restart, commit
or push. Current browser profile/goal remain session-only; no successful result was injected.

## September 11 — confirmed JSearch timeout mitigation

Two real failed-run records confirm MARKET_TIMEOUT at MARKET_RETRIEVAL, after 30.259s and
30.425s (failure IDs cd9a2be3-5002-4074-96c2-c73b9e064f39 and
217690bf-7bfc-42cf-a1d3-6bcdd59ba724). Neither preserved a market snapshot or reached the model.
Introduced JSEARCH_SEARCH_TIMEOUT_SECONDS=90 independently of the existing 30-second detail
timeout; connect/write/pool bounded to 10s, total search deadline 100s. No automatic retries,
pagination, extra model calls, or relevance-rule relaxation. Logs now identify timeout phase.

One fresh live search with the changed client returned 4 jobs, 0 malformed, in 8.84s including
process startup. This did not reproduce a >30s provider response: the mitigation is verified by
explicit transport/deadline tests, not a claim of guaranteed provider availability. No new model
run was needed for this HTTP-only change; the earlier 135.81s successful workflow remains separate.
Validation: 618 market/orchestration/UI/config tests passed; lint/diff checks passed. Restarted
the exact main-app processes on port 8533 after warning about session-only state reset. Active
configuration verified at 90s search/30s details and restarted health endpoint returned ok.

## September 11 — actual live reproduction completed successfully

Executed the production confirmed-demo-to-plan graph with live JSearch and the configured
Fireworks model (no AI-inference autoapproval, no model/provider substitution). Artifact:
outputs/live-failure-check/20260912T000433Z/results.json. This run discovered 3 postings,
retained Iris, and excluded 2 full-stack roles via existing relevance rules. Market retrieval
took 3.77s; author model 52.34s; reviewer 79.62s; total 135.81s. Assessment APPLY_SELECTIVELY,
MODERATE confidence, 5 competencies (4 demonstrated, CMS integration not established),
4 plan actions, no processing issues. Workflow WAITING_FOR_HUMAN is expected plan approval,
not a technical stop; no plan approval was performed. Market and Plan production routes
rendered the saved typed state with zero AppTest exceptions.

The previous generic-banner failure was NOT reproduced and its exact cause remains unknown;
do not claim a root-cause fix from this passing run. Earlier live probes returned 4 jobs for
Toronto/Canada and 5 for Toronto; those are different calls, not this run's denominator.
Added an explicit --live reproduction script with a 4-model-call/15-minute ceiling.
Fresh main app started on 127.0.0.1:8533 (health ok); old 8532 process/session left intact.
This is a fresh deployment of the successfully tested current code, not proof of why the old run failed.

## September 11 — safe failed-run diagnostics

Implemented specific timeout, rate/quota and malformed-response messages plus visible safe
error codes. New failed live attempts (initialization, handled workflow failure or unexpected
execution exception) save sanitized IDs/stage/elapsed-time records to outputs/failed-runs and
emit warning-level logs. Removed raw UI-boundary traceback logging. Code/details remain available
on return to the confirmed-goal page; retries and goal invalidation clear stale displayed records.
No live API/model call was made; this does not establish the cause of the earlier unrecorded run.
Current browser session was not restarted. Test attempts use isolated temporary record directories.
Validation: 613 market/orchestration/UI/config tests passed, including Streamlit AppTest failure
detail rendering; changed-file lint and diff checks passed. Local port 8532 health check returned ok.
No manual browser-level visual QA or live provider retry was performed in this pass.

## September 11 — JSearch response-contract routing

Added Search V2/list-envelope normalization, safe alternative apply-link selection, limited
Responsibilities/Qualifications highlights fallback, and bounded full-job-ID details enrichment.
Useful provider metadata stays separate from job-content text. Routing reasons, normalization
issues, raw counts, continuation flag and request ID survive into workflow/audit records; cursor
values are not stored or followed. Empty optional metadata does not invalidate job content.

Offline replay of the user's saved four-job JSON: 4 normalized, all descriptions present,
1 retained (Iris), 3 role-relevance exclusions (PeoplePilot, Resonaite, Kovasys). The two full-stack
exclusions still need semantic relevance review. No new live API/LLM request was made and no
end-to-end success is claimed. Location conflicts in prose are not automatically resolved.
Validation: 598 market/orchestration/UI/config tests passed; changed-file Ruff and git diff
checks passed. No app restart was performed in this pass, preserving the user's current session.

## September 11 — candidate fit and sample coverage separated

Removed the requirement for a demonstrated COMMON capability before accepting a positive
same-role/transition verdict. Demonstrated evidence and source/ID checks remain mandatory.
Prompts/schema describe COMMON as central role work rather than multiple-employer prevalence;
SPECIALIST describes narrow work, never sample size. Version suffix: concise-v2-fit-scope.
Single-posting assessments are visibly limited to that role. No verdict is forced positive.

Failed output validation now stores accessibility=null and no plan, with actual diagnostic
issues retained. UI shows Assessment needs review, avoids the duplicate warning, and does not
describe processing failures as missing candidate evidence. Old saved results remain unchanged.
This implementation has not been rerun through a live LLM; it requires a fresh manual analysis.
The separate retrieval relevance issue and JSearch timeout remain outside this change.
Validation: 383 career/UI/orchestration tests passed (one existing test-fixture serialization
warning); changed-file lint passed. Manual app restarted on 127.0.0.1:8532.

## September 11 — JSearch mixed-cohort snapshot failure corrected

JSearch had retained IRRELEVANT jobs in the validated total while snapshot title buckets
excluded them, raising the count-invariant ValidationError before any model call. Unrelated
results now remain in posting audits with explicit exclusion reasons, but do not enter target
postings, source content, employer counts or analysis inputs. JSearch passes its validated
classifications to the snapshot; result counters use that same snapshot. Legacy snapshot
callers retain their existing behavior. No relevance, geography or model rules were weakened.

587 market/orchestration/UI/config tests passed; changed-file lint passed. Saved user response
replay: four discovered, one eligible (Iris), three audited exclusions, no count exception.
The existing classifier still labels PeoplePilot and Resonaite irrelevant; that separate
relevance-policy issue is not fixed by this accounting change. The one fresh live test timed
out at JSearch search, before any LLM call. No live end-to-end success is claimed.
Manual app restarted on 127.0.0.1:8532; integration changes remain unpushed.

## September 11 — manual retest query alignment

Aligned JSearch search requests with the successful four-record backend probe: lowercase
location phrase, Canadian search country value `canada`, date_posted `all`, num_pages 1,
and no cursor. Internal country codes and Job Details remain unchanged. Posting age,
location validation, title classification, and LLM rules remain unchanged; this is not
a claim of end-to-end analysis success. Restarted the manual instance on port 8532.


## September 11 — JSearch live connection verified

Removed a trailing empty RAPIDAPI_KEY entry from the ignored local environment file
that was overriding the user's populated entry. One live search for Senior Java Developer
in Toronto, Canada (country ca, date_posted month) returned two normalized jobs, zero invalid
records: Iris Software (65 description words) and Resonaite (478 words). No Job Details or
LLM calls were made; this verifies search connectivity, not full workflow quality or sufficient
target-role coverage. 23 focused JSearch/config tests passed (one cache-write warning).
A fresh manual Streamlit instance was started on 127.0.0.1:8532, leaving the previous session
untouched. Credentials remain ignored and these integration changes are not yet pushed.

## September 11 — JSearch-only market setup

User selected RapidAPI JSearch to replace both active Adzuna and You.com retrieval.
Added fixed-host/header-key adapter, v1/v2 response normalization, one-search/five-detail
bounded service, ID-checked details, conservative dedup, currentness/geography checks,
and graph routing that never constructs legacy clients in JSearch mode. Existing model
settings, top-five analysis selection and assessment rules remain unchanged. Defaults and
the ignored local package environment select JSearch; RAPIDAPI_KEY is intentionally blank.
583 focused market/workflow/UI/config tests passed. No live provider call, subscription,
purchase, Git push or claim of live description completeness. User must add their own key
and verify subscription, then run the one-call probe. See JSEARCH_SETUP.md.

## September 11 — GitHub snapshot validation

Preparing the accumulated V1 code, tests, documentation and supplied job-description test inputs
for the user-requested GitHub push. Full offline suite: **1071 passed, 8 failed** (26.52 s).
Seven failures are in `tests/evaluation/test_v1_replay.py`; one is in
`tests/scripts/test_run_goal_case_matrix.py`. The case-matrix mock emits incompatible
assessment/comparison responses; replay expectations receive missing analysis/plan data.
These older evaluation paths require migration/investigation, not weakened assertions.
The focused 376-test UI/career/orchestration suite previously passed. This snapshot is not a
full-suite or live-model quality acceptance. Credentials, raw run outputs, local databases and
logs are excluded; `.streamlit/secrets.toml` is now explicitly ignored as well.

## September 11 — concise public-copy contracts and Plan alignment

Applied shared public wording guidance to same-role/transition initial and review prompts;
aligned legacy synthesis and constrained plan-refinement prompts. Version suffix `concise-v1`
distinguishes future runs. Reference fields, bounded calls, assessment policy and schemas stay
unchanged. New concise narratives render complete (no first-sentence clipping); saved older
runs retain the prior compact presentation. Plan actions/completion checks hide source notation
while retaining original wording in details; standalone aliases get readable referents.
376 UI/career/orchestration tests pass, changed-code lint passes, and both pages render the
actual saved AI Engineer result through AppTest. No fresh model benchmark, Git push or online
publication. Existing V3 semantic-quality issues remain unresolved.

## September 11 — combined review presentation, without inline evidence

Same-role/transition Analysis now shows a short readiness conclusion, a role overview
grouped from existing COMMON/SPECIALIST/OPTIONAL competencies, and strength names.
Original rationale, role narrative and individual-posting commentary remain in Run details.
Known source aliases are removed from main-page copy without changing stored results,
reference validation, accessibility, prompts or plans. This is presentation-only;
the recorded V3 semantic issues remain unresolved. 34 focused regressions and lint pass.
Restarted the read-only preview at 127.0.0.1:8530 and visually verified the updated
saved five-description result. No new provider requests or online publication.

## September 11 — V3 implemented; DeepSeek workflow passes, quality does not

Implemented the role-neutral transition prompt replacement and supervised-practice /
jurisdiction safeguards, retaining schemas, routing, same-role behavior and approval.
Same Java demo/five AI files through DeepSeek: 214.69 s, two calls, NEAR_TERM_TARGET /
MODERATE, seven strengths, 20 competencies, six draft actions, no reference issues.
372 regressions and actual saved Analysis/Plan AppTest passed; Ruff passed.
Material semantic failures remain (AI tenure overgeneralization, unconditional learning,
Docker context, bundled skills, incomplete prose). Degree field is omitted by the model
input builder. No claim of quality acceptance. See TRANSITION_V3_LIVE_VALIDATION.md.

## September 11 — cross-profession prompt desktop validation

Applied the unchanged proposed prompt to a fictional junior-plumber profile and five
explicitly fictional welding descriptions, with seven input-variation checks.
Assistant-authored assessment/self-review, not an API/model benchmark or app run.
The approach distinguishes trainee entry from qualified welding readiness; proposed
generic safety-supervision and jurisdiction/credential safeguards remain unapplied.
See PLUMBER_TO_WELDER_PROMPT_VALIDATION.md. Production behavior is unchanged.

## September 11 — independent assessment and prompt proposal

Authored an independent assessment of the same Java demo and five AI job descriptions,
separating credible AI-application direction from readiness for the advertised roles.
Drafted a role-neutral replacement-prompt proposal with boundary examples and evaluation
cases. No provider calls, production prompt/code changes or deployment in this activity.
See INDEPENDENT_JAVA_TO_AI_ASSESSMENT.md and CAREER_ASSESSMENT_PROMPT_PROPOSAL.md.
The proposal is not model-tested; existing semantic reliability issues remain open.

## September 11 — unchanged V2 repeat reveals verdict instability

Repeated the same five-file Java → AI Engineer test with identical first-call prompts
and payload. DeepSeek took 229.34 s/two calls; final verdict ASPIRATIONAL/MODERATE versus
NEAR_TERM_TARGET/MODERATE on the prior run. Backend/REST preserved; Docker production
overclaim persists. 18 competencies, six draft actions; no processing issues. Actual
Analysis/Plan AppTest passed. No rules/code/provider changes during this repeat.
See the repeat section in TRANSITION_INTERPRETATION_V2_VALIDATION.md. Semantic reliability
remains unresolved; successful execution does not establish stable career calibration.

## September 11 — transition interpretation V2 and controlled live rerun

Implemented four user-approved interpretation corrections in transition author/reviewer
prompts; same-role defaults and retrieval/approval boundaries unchanged. Same five files,
Java demo and DeepSeek: 189.65 s, two calls, NEAR_TERM_TARGET/MODERATE, 20 competencies,
six draft actions, no processing issues. Base REST/cloud preserved; mixed skills split;
unknowns clarified; plan narrowed to AI application engineering. Docker production attribution
still overclaimed, so semantic quality is improved but not fully corrected.
369 regression tests and changed-file Ruff passed. Actual saved output AppTest passed.
See TRANSITION_INTERPRETATION_V2_VALIDATION.md for detailed results and limitations.

## September 11 — live Java → AI Engineer transition test

Five user-supplied AI descriptions/four employers, synthetic Java demo profile, actual
Fireworks DeepSeek: 256.26 seconds, two calls, ASPIRATIONAL/HIGH, eight strengths,
20 competencies and six draft-plan milestones. Schema/reference checks passed; actual
Analysis/Plan AppTest rendering passed. Semantic issues remain (REST downgraded by an
Azure-specific condition, uneven unknown handling, broad scope/confidence, zero transfer labels).
See AI_ENGINEER_TRANSITION_LIVE_TEST.md. No browser, discovery calls or plan approval.
Fixed a diagnostic-only employer-count assumption exposed by two Definity roles.

## September 11 — separate generic career-transition rules

Implemented `career-transition-assessment-v1` for ROLE_TRANSITION in the production
graph, with a separate typed assessment, concise Analysis/Plan rendering and exact-version
approval. Preserves strengths and distinguishes transferable evidence, clarification,
learning and experience-building. Same-role prompts and other goal routes are unchanged.
See CAREER_TRANSITION_RULES.md for the contract and verification limits.
Live transition output quality has not yet been evaluated; this activity made no provider calls.
Validation: 783 relevant tests passed; changed-file Ruff checks passed. Analysis and
Plan were exercised with native Streamlit AppTest, not manual browser visual QA.

## September 10 — full local website started with DeepSeek

Saved local (git-ignored) environment role settings now all select
`accounts/fireworks/models/deepseek-v4p1-flash` through Fireworks. Started the full
production Streamlit application at http://127.0.0.1:8531/ for manual testing, not
the read-only saved-result preview. This is loopback-only, not a public deployment.
Latest implementation changes remain local/uncommitted and have not been pushed.


## September 10 — DeepSeek comparison on unchanged same-role rules

Actual Fireworks `deepseek-v4p1-flash` test completed in 124.79 seconds, two calls,
APPLY_SELECTIVELY / MODERATE, 20 competencies, six plan steps and zero reference
issues. Artifact: `outputs/local-descriptions/20260911T034636Z/results.json`.
Same demo profile and four relevant supplied descriptions; no fresh retrieval.
Docker project/production distinction and automated-testing/TDD separation are
correct in the final output, unlike GLM. Remaining errors: frontend/React asks
from Tactable are carried into the LTIMindtree action, and optional Kubernetes
is framed too strongly among barriers. The output is also longer than desired.
This is an improved single-case result, not general model acceptance.

Configuration was NOT edited: the user's `FIREWORKS_MODEL` setting names DeepSeek,
but Settings ignores that key and the role-specific model settings still name GLM.
The test used process-only EXTRACTION_MODEL/REASONING_MODEL/VALIDATION_MODEL overrides.
The normal website therefore still reads the saved GLM role settings.


## September 10 — production same-role assessment path

Implemented a separate same-role Current Market Analysis path using consolidated
GLM assessment + critical review, short evidence aliases, concise Analysis/Plan,
and existing exact-version approval. Legacy thresholds do not override this path;
career-transition processing is unchanged. Actual hosted GLM run with the four
relevant saved descriptions completed in 87.84 seconds / two calls, returned
APPLY_SELECTIVELY (MODERATE), 13 competencies and a four-step draft plan.
Zero reference-validation failures, but semantic QA is NOT passed: Docker production
overclaim, automated-testing/TDD conflation, erroneous within-sample salary comparison,
and inconsistent duty/qualification labels remain. See SAME_ROLE_LIVE_VALIDATION.md.


## September 10 — title relevance corrected; full-description live rerun

Added description-supported specialty relevance to the production discovery and
extraction boundaries. Original titles, seniority/authority guards, source scopes,
and same-vacancy identity rules are preserved. Four local descriptions (LTIMindtree,
Kaseya, BMO, Tactable) now enter the batch as TARGET_VARIANT; Impro.AI remains
outside the Java target. No employer-specific or Java-specific exception was added.

Live GLM run `outputs/local-descriptions/20260911T023008Z/results.json` completed
in 547.30 s with 15 model calls and no Adzuna/You discovery calls. Full bodies were
sent unchanged (1,212 / 1,030 / 844 / 836 words). Extraction plus one repair took
353.64 s; comparison 186.49 s; synthesis 6.83 s. The graph reached draft plan
generation but this is NOT a quality acceptance pass: 30 draft themes, 23 initial
rejections, eight repaired, 15 unresolved. Twelve comparisons: ten OPERATION_FAILED
(five schema-validation errors, five semantic/grounding-validation errors), one
UNKNOWN and one SUPPORTED (degree). Overall assessment and plan confidence remain
INSUFFICIENT. The plan is an evidence-clarification draft, not an application-ready
recommendation. No validation thresholds were relaxed to create a fit verdict.

756 market/career/orchestration/UI/diagnostic tests passed, plus final focused
checks. Streamlit AppTest rendered Analysis, Plan and Input files without errors.
Read-only production-renderer preview starts directly on Analysis at localhost:8529.
Browser navigation remained blocked by unavailable admin-policy verification; no
visual browser QA or successful automatic opening is claimed. The earlier 8528
preview still represents the pre-fix zero-call run. Production profile/session data
and the five original text files were not changed.

## September 10 — supplied-description diagnostic and read-only preview

Tested the five user-saved files in `job-descriptions` against the unchanged Senior
Java Developer demo goal. Bodies contain 451–1,212 words. The existing classifier
returned one RELATED_TITLE and four IRRELEVANT; none qualified for the exact/variant
batch. The graph reached market_ready then safely stopped, with zero model calls,
no candidate assessment and no plan. This is a title-selection failure, not an LLM
failure or proof of inadequate descriptions. No production policy was changed.

Added `scripts/check_local_descriptions.py` (local retrieval injection, production
downstream services, sanitized results) and `scripts/local_description_preview.py`
(read-only existing Analysis/Plan renderers). Result:
`outputs/local-descriptions/20260911T021429Z/results.json`.
BMO's exact role title was absent from its body and taken from its filename;
public posting URLs and current vacancy status were not verified. Original text
files are unchanged. One importer regression passed; Streamlit AppTest rendered
the assessment without exceptions. Preview starts on Analysis at localhost:8528.
Browser-level inspection was blocked because the browser tool could not verify
its admin-enforced policy. No bypass or alternate browser-control route was used.
Target-role broadening or a title-selection policy change still needs user direction.

## September 10 — fresh backend demo through analysis (no browser)

Ran the production runtime with the synthetic demo through Education/Certification,
live AI strength review and fresh Adzuna/You.com retrieval. Reached assessment synthesis
in 195.35 s with eight GLM calls, but final accessibility/confidence remain insufficient.
AI review succeeded (five suggestions, not auto-approved); 25 posting records retained;
five truncated descriptions analyzed. Core Java themes were rejected by a mixed-section
duty guard; two of four comparisons failed semantic output validation. This is not an
end-to-end acceptance pass. See DEMO_TO_ANALYSIS_BACKEND_CHECK.md and the sanitized run
under `outputs/demo-to-analysis/20260911T002304Z/`. Production rules and browser sessions
were not changed during the test.

## September 10 — recover individual batch theme validation failures

The 8526 run failed at `FivePostingRoleProfile: themes.6:value_error`: a cross-field
validation failure erased the whole batch. Exact rejected response content was not retained.
Production now validates the transport envelope, then each theme independently, including
grounding. Valid siblings survive; rejected themes receive one indexed repair request with
no gateway retries. Invalid repairs cannot change accepted themes or downgrade core importance.
Unresolved core/supporting qualifications or prerequisites withhold overall readiness.
Processing status is explicit and the UI no longer calls a validation failure only a limited
role sample. Existing saved runs are not recomputed automatically.

Tests cover seventh-theme failure, valid repair, rejected repair, source IDs, core safeguards
and native UI rendering. Live saved-public-description validation is tracked separately below.
Verification: 801 Market/career/UI/orchestration/model tests plus 107 profile/script tests
pass (908 total); scoped Ruff checks pass. Fresh production app on 8527 returns healthy
and its Home page was inspected in the in-app browser. The existing 8526 session is preserved.

First bounded live check (`outputs/five-posting-recovery/20260910T233725Z`) selected five
saved public excerpts, not fresh vacancies. Initial response: 187.90 s, 13 invalid themes
(invented headings, obligation conflicts). Repair: 303.91 s, 30,000 tokens, finish `length`;
no usable requirements. Safe stop preserved. This is not an end-to-end success.
The previously tested explicit GLM high-effort setting was absent from production; it is now
wired into the exact deployment, and the repair prompt no longer repeats the whole-profile task.

Follow-up high-effort checks: `20260910T234722Z` completed both calls in 104.53 s but
recovered no requirements. With source-label prompt v3 and corrected-name repair,
`20260910T235050Z` completed in 103.24 s (61.24 initial + 41.96 repair), recovered 3 themes
and retained 7 unresolved themes. Canonical output includes one primary hiring theme
(Database expertise), one optional Git theme and one experience prerequisite. Overall
readiness remains blocked. This proves partial recovery, not successful career-analysis
acceptance. Input was five saved short excerpts, including a company-only excerpt, not
the user's current browser session or fresh/full descriptions. Outputs and exact wire bodies
are saved under `outputs/five-posting-recovery/`; no candidate data or reasoning traces sent/stored.
Source-label normalization and model classification quality remain limitations.
Final verification after all changes: 913 tests pass across Market, career, UI,
orchestration, models, profile and diagnostic scripts; scoped Ruff passes. Fresh production
server restarted on 8527 with the updated GLM adapter and prompt v3. Full live workflow
acceptance remains open; do not describe the partial extraction replay as a complete fix.

## September 10 — live connection correction and word-ranked batch selection

Replaced the batch's 600-character/70-word cutoff with descending word count among
nonempty, in-scope exact/variant descriptions. Preserved source validation and uncertainty;
length is not completeness. Saved real 28-posting selection replay now chooses five instead
of zero (79, 73, 72, 69, 69 words), without a new model analysis.

Live checks found the You.com MCP `extraction` argument now expects a string, while our
adapter sent an object. The adapter now follows the advertised parameter type; full-page
search succeeds. Adzuna search, You.com handshake/basic search and a tiny GLM structured
response also succeeded. 397 scoped Market/UI tests pass. These checks do not establish
fresh end-to-end career-analysis quality or that a fetched page is a complete JD.

## September 10 — five-description production batch and approved Analysis layout

The website now explicitly uses `analyze_five_postings`: one logical extraction request
for up to five usable target descriptions, validated model grouping, role importance
separate from source obligation, and shared canonical objects for comparison/Plan.
The Analysis surface now has a role picture, full-width numbered competency table,
separate gaps/questions and a next step. Specialist conditions stay in audit; additional
advantages do not become baseline gaps. OR matches show the demonstrated alternative.
Offline service replay reaches an untimed Plan. Fresh live-provider acceptance remains
pending; prior saved runs are not recomputed. See FIVE_POSTING_PRODUCTION_BATCH.md.

## September 10 — reference-aligned UI overhaul

Revisited the user design ZIP and reconciled it with the later merged-assessment
requirements. Applied a bounded native layout, compact shared typography, aligned
Home/Goal cards, readable onboarding navigation, an assessment main/side layout,
and a single Plan action sequence with secondary route/strength context. Removed
duplicated Plan prose and session-persistence notices. Exact-version approval,
unknown statuses, confidence warnings and safe stops are preserved.

318 UI/career/plan-review tests pass; scoped Ruff checks pass. Browser inspection
covered production Home/Education and frozen full-path, provisional and insufficient
assessment replays, plus Plan top/footer controls. See UI_OVERHAUL_QA.md.

Fresh production app: http://127.0.0.1:8520/. QA harness: port 8521. Existing app
sessions were not stopped. No live model or retrieval request was made for this
presentation pass. Extraction accuracy and complete live-workflow acceptance are
still separate unresolved product checks, not fixed by layout work.

## September 10 — remove repetitive assessment narrative

The main assessment now contains verdict/confidence, competency table, gap names
with severity (when present), and one short next step. Repeated strengths, focus,
supporting-evidence prose and alert stacks were removed from the decision surface.
One Run details section retains full rationale, deduplicated notes, posting leads,
source audit JSON and search queries. Backend rules, model prompts, saved evidence
and plan gate are unchanged. Automated rendering checks cover compact headings and
diagnostic placement. No live model call or browser-session reset.

## September 10 — readable competency block

Replaced employer-expectation accordion/card nesting with one numbered native table
(Competency / Context / You). Removed per-item evidence prose and source-detail
dropdowns from that block; retained audit data and separate diagnostic details.
Compact statuses preserve transferable/partial/unknown distinctions and never label
processing failure as No. Backend policies and provider prompts are unchanged.
Automated Streamlit rendering and status-mapping tests cover the new presentation;
no live API call or current-session reset.

## September 10 — bounded readiness without all-item completion veto

Canonical readiness now needs two non-employer-specific baseline expectations and
at least two / strictly more than half resolved comparisons, not every hiring item.
Unverified mandatory baseline prerequisites and independent-source/content-quality
gates still withhold the verdict. Unknown/failed comparisons remain visible but do
not vote as deficits. Open questions cap confidence at Moderate and Apply now at
Apply selectively. Specific candidate, employer and processing notes appear on the
assessment page; existing comparisons and strengths remain intact. Fit thresholds,
retrieval/model contracts and approved records are unchanged. See
ASSESSMENT_RULES_QUICK_REFERENCE.md. 279 backend/UI/plan-review regressions and
targeted Ruff checks pass (existing non-fatal pytest cache warning); no new live API
run or browser-session replacement. Re-run analysis to update an old result.

## September 10 — date-derived experience and uncertainty preservation

Added an explicit-employment timeline calculator (union of intervals, current roles
through the analysis date, no project/education inflation). Comparison v8 receives
total/role tenure and missing-date questions; Profile Review shows calculated and
self-reported experience separately. Explicit UNKNOWN and pending partial-match
clarifications remain unknown. Synthesis no longer interprets clarification-linked
insufficient-evidence gaps as low-fit barriers. A fresh GLM-configured app runs on
127.0.0.1:8518; health check passed, older session untouched. No new live API run.
374 career/profile/UI tests and targeted Ruff checks passed (non-fatal pytest
cache-path warning). Automated Profile Review rendering passed; manual live-model
verification is left to the user.
See EXPERIENCE_DATE_CALCULATION.md for boundaries and manual checks.

## September 10 — Plan wording validation corrected

Plan-wording-v4 permits controlled paraphrases while protecting proficiency,
versions/numeric qualifiers, conditions, technical symbols and word order. Valid
milestones survive a wording failure elsewhere; each rejected action/outcome pair
reverts together, with structured field/reason diagnostics. Structural tampering
still rejects the full response. Saved GLM replay now accepts two of three rewritten
milestones, retaining the original proficiency wording in the third. All immutable
plan fields are unchanged. 197 targeted tests and Ruff pass; no new live call or
browser validation. Uncertainty-to-Aspirational policy remains unchanged and pending.
Replay: outputs/glm-plan-replay/20260910T172634Z. See GLM_PLAN_PHASE_FINDINGS.md.

## September 10 — bounded GLM Plan diagnostic

One live high-effort Plan call over four saved demo comparisons completed in
4.34 seconds (779 input / 208 output tokens). Production rejected paraphrasing;
deterministic fallback preserved IDs and no fixed timeline. The limited replay
also exposed uncertainty gaps classified as Aspirational/Development and a
contradictory no-material-gap rationale. Not a full five-JD workflow validation;
experimental batch excluded, production unchanged. 47 targeted tests and Ruff
pass. See GLM_PLAN_PHASE_FINDINGS.md and outputs/glm-plan-check/20260910T171111Z.

## September 10 — GLM explicit-high reasoning succeeds at generation

Verified GLM 5.3 rejects reasoning_effort=none as thinking-only. Changing only
reasoning_effort to high completed the same five-JD task in 86.43 seconds with
10,378 output tokens, versus a prior 246.26-second/30k truncation. Complete JSON,
25 themes, all five IDs, 90 quote/ID checks pass. Semantic review still fails:
duties labeled qualifications, missing eligibility/credentials, truncated theme
names and source-completeness confusion. Diagnostic only; website unchanged.
Seven targeted tests and Ruff pass. See GLM_REASONING_CONTROL_FINDINGS.md.


## September 10 — five-description GLM test

Selected five longer saved descriptions across five employers, no 500-character
snippets. Unchanged consolidated contract failed after 246.26 seconds: 3,546 input
tokens, 30,000 output tokens, finish=length, zero visible final JSON. Same safe
failure as the ten- and 34-record GLM tests. No automatic retry or production change.
See FULL_BATCH_ROLE_PROFILE_BENCHMARK.md for selection and all three measurements.


## September 10 — same ten-record task on Nemotron

NVIDIA Nemotron 3.5 Lightning returned schema-valid JSON in 276.52 seconds, 6,288
input / 5,841 output tokens, finish=stop. Ten themes and all ten posting reviews;
40/51 support rows pass narrow checks, 11 fail. Manual spot checks find additional
duty-to-qualification promotion, cross-posting leakage and irrelevant theme support
among quoted evidence. Completion succeeds where GLM capped out, but semantic
quality does not pass. No website/provider configuration change or candidate/Plan
output. See NEMOTRON_BATCH_COMPARISON.md and saved request/response/audit.


## September 10 — ten-record consolidated follow-up

Repeated the unchanged consolidated GLM contract on six longer descriptions plus
four evidence-bearing snippets. 5,328 input tokens; 273.62 seconds; `length` at
30,000 output tokens; zero visible final JSON. Safely rejected, no retry, no website
change. Record-count reduction alone did not resolve this failure. See the follow-up
table in FULL_BATCH_ROLE_PROFILE_BENCHMARK.md. Four targeted offline tests pass.


## September 10 — full inventory single-call consolidation test

Sent all 34 saved source records (28 snippets plus six retrieved JD documents,
30,336 text characters) in one GLM request. Returned after 248.98 seconds with
`finish_reason=length`, 10,023 input / 30,000 reported output tokens and no visible
final JSON. Gateway safely rejected the response; no retry or production change.
No complete role-profile quality assessment is possible from this failed attempt.
See FULL_BATCH_ROLE_PROFILE_BENCHMARK.md. Three offline audit tests and Ruff pass.


## September 10 — live two-worker extraction diagnostic

Four saved public postings completed through Fireworks GLM and production extraction
validation in 190.50 seconds with two workers, versus 369.99 seconds summed request
durations (not a measured serial baseline). All four schema-valid, no retries or
timeouts; 30/42 statements retained. One full body plus three short snippets is not
a representative full-JD throughput test. Production website remains sequential.
See PARALLEL_EXTRACTION_BENCHMARK.md for timings, quality caveats and raw artifacts.


## September 10 — compact model output contracts

Inference and comparison request one-sentence descriptions (320-character schema
bounds); comparisons allow at most two exact excerpts of up to 320 characters.
Extraction and synthesis request unique, concise limitations; conservative cleanup
removes case/whitespace duplicates, not distinct conditions. Plan replies contain
only milestone keys and editable action/outcome wording. Code restores immutable
plan metadata and comparison requirement IDs; returned conflicting metadata still
faces existing validation. Semantic dimensions and transferable capability labels
remain model outputs. Prompts: inference v5, extraction v7, comparison v7,
synthesis v6, plan wording v3. Output ceiling/timeouts unchanged. No live latency
claim: provider reasoning and sequential calls can still dominate elapsed time.
Validation: 920 tests passed (one pytest-cache filesystem warning), targeted Ruff
checks passed, and git diff --check passed. No live provider run or forced server
restart was performed for this change; existing session results are not regenerated.


## September 9 — live GLM instruction test and server reload

Used the actual Fireworks GLM gateway with saved public job text and the synthetic
demo. Valid extraction returned 25 statements in 130.62 seconds. Replaying that
same answer after generic role-label/verb-normalization fixes retained 21 rather
than 17. Live comparisons preserve optional mentoring, satisfy a cloud OR through
AWS, and do not convert generic Java into a complete Java 8 match.

The test exposed missing date/current-role context and a model-generated stitched
quote. Added source dates/current-employment context and an explicit contiguous-
quote rule; retained strict grounding validation. Synthesis now explicitly keeps
the evidence tracks distinct. Future audits stamp schema/pipeline/prompt versions.
See `docs/GLM_BACKEND_CONTRACT_CHECK.md` for raw artifact locations, failures and
acceptance limits. No full market/Plan completion is claimed by this small test.
Final comparison prompt v6 passed schema/exact-quote validation with a partial
match and microservices clarification, not Apply now. Semantic caveats remain
around tenure wording and partial subtype; latency was 171.17 seconds. Final
verification: 910 tests passed, targeted Ruff passed, and port 8517 restarted at
23:34 with a healthy endpoint (`ok`). Seven live requests total; no new searches.

## September 9 — broader grounded evidence comparison

Implemented source-preserving hiring, preference and work-alignment tracks.
Low recurrence no longer excludes employer-specific hiring conditions. Same
concepts with different statement kinds remain distinct; source mandatory flags,
years, qualifiers and provenance survive canonical projection and model prompts.
The saved 60-item quote replay yields 6 hiring groups, 10 work-alignment groups
and 1 preference; all remaining statements retain explicit audit dispositions.

Coverage checks prevent one Java match or incomplete hiring comparisons from
establishing overall Apply now. Duties/preferences do not create mandatory gaps;
confirmed no-fixed-timeline is preserved. The combined assessment page separates
tracks and moves long explanations into source details. Plan uses coverage-safe
exploration or concrete posting-specific application evidence checks.

Verification: 903 tests passed, targeted Ruff checks passed, and Streamlit AppTest
rendered the three evidence tracks and audit disclosure without exceptions.
Pytest reported only the existing local cache-directory warning. Offline replay
details and limits: see `docs/EVIDENCE_PIPELINE_REPLAY.md`.
No provider calls, provider-setting changes, session resets or edits to saved
live results were made. Fresh live GLM acceptance remains outstanding.

## September 9 — port 8517 connection failure investigation and restart

Confirmed Explore demo seeds inputs and then uses the production GLM gateway;
it does not select a separate NVIDIA provider. Demo-flow tests pass. The old
NVIDIA transport-error label was hard-coded UI copy and is now provider-neutral.
Fireworks worker errors now preserve timeout versus transport categories without
logging credentials, provider bodies, or reasoning. Validators remain unchanged.

Network probes failed with ConnectError under restricted execution and succeeded
with approved external execution: You.com handshake, native-schema GLM streaming,
production parser, and production subprocess gateway. This points to the launch
environment; the original worker's generic errors do not prove the exact OS-level
cause. Windows token restriction flags alone were not discriminating evidence.

Bounded production-adapter verification outside the restricted environment:
You.com returned 2 search results; Adzuna returned 2; GLM reviewed all 9 synthetic
demo evidence items and SUCCEEDED with 5 pending strengths (Enterprise Systems
Integration, Backend Service Design, Technical Design Review, API Documentation,
Authentication Implementation). No inferred strengths were approved and no browser
profile was used by the diagnostic. Diagnostic timeout was capped at 180 seconds;
website settings remain 600 seconds, 30000 output tokens, zero retries.

Restarted only the verified port-8517 server processes using approved external
execution; new launcher PID 34168. Same URL returns HTTP 200 health=ok. Restart
clears temporary session state; Explore demo refills inputs. Old failure logs
are preserved; new logs use .streamlit-8517-network-restart.*.log. Full browser
Market/Analysis/Plan acceptance remains unverified; connection recovery is not
proof of complete job-description extraction or assessment quality.

Reusable bounded check: scripts/check_live_connections.py (--search --demo opts
into two small searches and a synthetic demo review; default is handshake/ping).
Verification: 892 tests passed in 31.53s; targeted lint and git diff --check passed.
Pytest emitted one non-failing cache-write warning; no cache cleanup was performed.

## September 9 — live website switched to Fireworks GLM, 30k output ceiling

At user request, ignored local package .env now routes extraction/reasoning/
validation to accounts/fireworks/models/glm-5p3-flash via Fireworks. Global model
output override is 30000, timeout 600s, retries 0, Fireworks streaming enabled.
Gateway applies the override before inspection/dispatch. Defaults for unconfigured
environments remain unchanged. No candidate facts, approvals or validators changed.

Fireworks streaming now runs in an isolated, hidden transport worker. Parent
communicate(timeout) kills/reaps a stalled worker rather than relying only on
arriving chunks. Worker preserves final answer/token counts, discards reasoning,
and rejects interrupted streams. Provider still passes length finishes to the
gateway's truncation rejection. HTTP errors are typed without credential logs.

Live production-adapter ping returned GLM connection successful (stop, 29 input /
36 output tokens, 2.60s). Full regression suite: 890 passed; targeted lint passed.
Fresh loopback Streamlit instance at http://127.0.0.1:8517 has HTTP 200 health=ok.
User will manually exercise the workflow; no claim that a 30k full JD or end-to-end
GLM workflow has succeeded. Existing older browser sessions should not be reused.

## September 9 — Fireworks GLM saved-workflow partial test

Configured FIREWORKS_MODEL accounts/fireworks/models/glm-5p3-flash is reachable.
Initial thinking-disabled request failed 400; thinking-enabled repeat used same
saved sources/prompts with streaming/20k. Full Cognizant probe reached 20k tokens
and was rejected as truncated (227.56s). Five demo strength suggestions passed
validation without approval. Three of 28 excerpts returned schema-valid outputs;
only one hiring item and one responsibility survived. Fourth batch stream hit
the diagnostic deadline; 24 postings were not sent. Six calls plus initial 400.
Market gate INSUFFICIENT_EVIDENCE; no comparison/Plan. Website remains Nemotron.
Important harness limitation: call 6 recorded 4209.43s because deadline checks
run on arriving chunks, not an independent watchdog. Do not attribute that delay
solely to model generation; host/stream cause unverified. Fix hard cancellation
before another batch. Three offline tests/lint passed. Report:
`outputs/fireworks-saved-market/20260909T221337Z/README.md`.

## September 9 — streaming Qwen succeeds; 28-posting batch blocked by credits

User-authorized streaming test completed the full Cognizant extraction in 263.84s,
first chunk 0.65s, 2413 input/2792 output tokens, finish=stop under a 20k ceiling.
Valid JSON: 18 raw, 8 retained (5 hiring/1 responsibility/2 preferences); current
semantic/noncanonical rejections still remove Java experience and sponsorship.
Next capability call and first batch posting call returned HTTP 402 (depleted HF
included credits). Circuit breaker prevented remaining network requests: 3 actual
calls total; only 1/28 batch postings submitted, 27 not sent. All 28 saved records
contain 500-character excerpts, not complete JDs; no fresh retrieval. Market failed
on service availability; no comparison/accessibility/Plan. No production switch or
purchase. Report: `outputs/qwen-saved-market/20260909T215500Z/README.md`.
Two offline stream tests and lint passed. No background calls remain.

## September 9 — live Hugging Face Qwen extraction attempt

User-authorized saved Cognizant test used Qwen/Qwen3.8-27B, 20k output ceiling,
temperature 0, JSON-object output, thinking requested off, 600s client timeout.
Two 400 responses exposed rejection of two system messages. Diagnostic combined
their unchanged contents into one system message; third call ended HTTP 504 at
120.079s with no final answer or usage. No backend acceptance result is available.
No production model switch. Report: `outputs/qwen-live-extraction/20260909T214032Z/README.md`.
The provider error recommends streaming; not attempted in this activity.

## September 9 — supplied GLM Flash partial response review

Attachment 2c1e303f-82b5-4c26-bbe8-f6f5c2dedc05 includes surrounding prompt text
and an incomplete final answer. Final-answer JSON has invalid sponsorship-quote
escapes and ends mid-string in item 20. Cause of truncation/copy corruption and
provider settings are unknown. No complete production-valid GLM response supplied.
Diagnostic only: isolate final answer, remove two known quote backslashes, replay
the 19 complete objects with an empty diagnostic limitations array. All 19 quotes
ground; 12 retained (3 responsibilities, 5 hiring, 3 preferences, 1 prerequisite),
5 semantic rejections, 1 Java Development non-canonical rejection, 1 metadata
exclusion. The concise sponsorship label survives, unlike null-label fallback in
the Qwen/Nemotron cases. Visible GLM preserves years=6, cloud OR and frontend
EXPOSURE but bundles AND skills and assigns LEADERSHIP maturity to mentoring.
Partial subset is not full-response acceptance or a model ranking. No live calls,
production edits or provider switch; surrounding reasoning text not persisted.

## September 9 — full saved Qwen/Nemotron backend comparison

Offline production-validator replay completed for the same full Cognizant JD.
Nemotron retains 10/18 items; original Qwen fails JSON; diagnostic-only removal
of two malformed backslashes yields 24/38 retained Qwen items. All parsed source
quotes ground, but semantic validation rejects additional items. Both lose the
Java experience requirement and sponsorship prerequisite; Qwen retains clearer
duty boundaries and cloud ANY_OF. One employer cannot satisfy the canonical
evidence gate: all cases stop INSUFFICIENT_EVIDENCE; no candidate/Plan model run.
No live calls, provider switch or production fix. See
`outputs/qwen-nemotron-comparison/20260909-cognizant/README.md` and item-level JSON.
Qwen telemetry remains unavailable; no speed/cost or general winner claim.

## September 9 — user-supplied Qwen extraction response review

Read the user's Qwen response attachment b9709c52-713b-4dec-98b2-aec272528d4c.
The original response fails PostingRequirementResult JSON parsing at line 64:
invalid backslashes around the visa-sponsorship quote. Removing only those two
backslashes in memory yields schema-valid output with 38 items: 14 responsibilities,
13 hiring capabilities, six preferences, one prerequisite, four metadata items.
All 38 source quotes pass the existing normalized _contains_quote check against
the saved full Cognizant input. This is not a full downstream acceptance test.
Qwen preserves years=6, cloud ANY_OF and preferred Agile/mentoring more faithfully
than the saved Nemotron response. More items alone do not establish better accuracy.
Original attachment and production code unchanged; no model call or provider switch.
Manual transport/provider settings and response latency remain unverified.

## September 9 — Qwen manual comparison input

Exported `outputs/qwen-manual-test/cognizant-input.txt` from the successful saved
20k Nemotron v5 Cognizant request: all system/schema and user-message contents
preserved, combined with labelled sections for a single Hugging Face prompt box.
This is the saved full-description test, not the fresh run's 500-character snippet.
Single-message transport differs from the original API roles. No Qwen call made,
no model switch, no credentials in the artifact, no comparison winner claimed.

## September 9 — fresh full demo backend acceptance attempt

Ran the actual editable Senior Java Developer demo through the production backend
with fresh Adzuna/You.com and Nemotron, using diagnostic 20k output/600s timeout/no
retry overrides only. Finished after 387.24s and 18 model calls at MARKET_READY /
INSUFFICIENT_EVIDENCE. Four valid inferred strengths remain pending. Adzuna gave
33 raw / 28 retained records, 17 employers; You.com gave zero retained direct jobs
and zero successful enrichments. All 15 extraction inputs were 500-character
excerpts; 14 schema-valid responses, 11 analyzed postings, six with accepted hiring
requirements. Three model responses failed schema across extraction, variant
validation and overview. Canonical baseline empty; comparison and Plan not reached.
Safe stop passed, end-to-end acceptance failed. No production policy fixes made.

New defects evidenced include invented source quotes (correctly rejected), genuine
Cognizant duties misclassified as metadata, API paraphrase false rejection and an
accepted incomplete preference. Initial ten-extraction budget expands by five in
fallback. Auxiliary analysis-view export raised ValueError; graph/raw outputs
saved. See `outputs/demo-profile-live/20260909T194458Z/README.md`. Diagnostic state
is in-memory; saved sanitized artifacts persist. No browser QA claim.

## September 9 — successful single Nemotron call with 20k diagnostic ceiling

User-authorized Cognizant retry with current v5 prompt, 20,000 max output tokens,
600-second timeout and no retries completed in 38.56 seconds. Provider reported
2,598 input and 1,701 output tokens, finish_reason=stop. All 18 returned items passed
schema; posting processing retained 10 and rejected 8. No null lists occurred in
the returned answer (optional fields were mostly omitted); null repair remains
offline-regression verified. The diagnostic script now supports request-budget
override before gateway inspection; production budget/settings remain unchanged.
Lint and an offline dispatch assertion confirm the diagnostic override.

Live quality issues remain: duties mislabelled hiring capabilities, preferred
Agile/mentoring mislabelled, missing structured years/alternatives and source-backed
Java Development/Mentoring rejected by current guards. This test did not run the
overview/candidate/Plan stages and does not establish a token-limit timeout fix.
See `outputs/nemotron-live-overview/20260909T185859Z/README.md` for the full answer
and item-level audit. Prior failed tests below are historical and preserved.

## September 9 — narrow extraction list-format repair

Requirement prompt v5 explicitly requests arrays for `qualifier_quotes` and
`capability_options`, with `[]` rather than null when empty. A field-level before
validator converts only nulls in those two ExtractedRequirement fields to empty
lists before ordinary gateway/schema validation. The advertised schema remains
non-nullable arrays; no global coercion or fabricated alternatives were added.
ANY_OF cardinality, source/qualifier grounding, semantic alignment, category/enum,
extra-field and contradictory-flag checks remain enforced. Timeout/token/retry
settings are unchanged. The 42 added regressions include the real gateway plus
extraction path with a fake provider; all 882 tests and targeted lint pass.
No new live model call was made; provider latency remains unresolved. Previously
exported request files intentionally preserve the original v4 diagnostic inputs.

## September 9 — live Nemotron saved-JD diagnostic

The exact Cognizant retry payload was exported unchanged for manual Nemotron
testing as `outputs/nemotron-live-overview/cognizant-request.json`, with a separate
`cognizant-playground.txt` containing the system/schema and user message texts.
Export equality was verified against the saved request; no new provider call.

Seven bounded model attempts produced zero accepted extractions: five 90-second
timeouts and one list-field schema rejection across six saved descriptions, then
one additional Cognizant timeout at 180 seconds outside the sandbox. No overview,
candidate comparison or Plan model call could be validated. The empty canonical
profile stopped safely; it was not substituted with a demo answer. This corpus is
not the current portal's 27-posting run. No production settings were changed.
See `outputs/nemotron-live-overview/README.md` and its two sanitized run records.
Added a preflight-by-default bounded diagnostic script; lint and 15 overview tests
pass. Live acceptance remains unproven; provider latency and invalid list outputs
are concrete unresolved failures.

## September 9 — combined career assessment implementation

Market and Analysis now route to one production Career assessment screen, with one
sidebar entry and backward-compatible internal route keys. Employer expectations
appear alongside source-ID-linked candidate comparisons. Frequency charts, title
mix, employer pie and prominent exact/expanded counters are absent from this route;
source scope, counts and search queries remain under evidence details. Demonstrated
strengths survive incomplete assessments. UNKNOWN comparisons appear as questions,
OPERATION_FAILED as processing issues. No plan result means disabled Plan continuation.

A bounded cross-posting model call organizes canonical expectations and supporting
passages by professional capability dimension. This is structured-extract synthesis,
not concatenation of all raw JDs or an unconstrained market-strategy generator.
The model cannot create expectations, omit/duplicate IDs, blend duty/preference/
prerequisite/scope boundaries or assert people management from mentoring alone.
Invalid/unavailable organization falls back to labelled original-source grouping.
Original requirements, comparison and accessibility policies retain ownership.
Overview state is cleared on invalidation; existing sessions without it render a
source-grouped view without automatically making a model call.

Posting input preserves section line breaks; extraction instructions cover interpersonal
capabilities, eligibility and incomplete content, and heading-fragment names are rejected.
Comparison receives bounded professional-summary/core-competency context separately from
approved evidence. Self-reported labels cannot establish ownership/maturity/production.

Verification: 840 tests pass, including 15 new overview/contract regressions and updated
combined-route assertions. Targeted lint and diff whitespace checks pass. Separate
localhost:8516 browser harness exercised successful Senior Java → Plan, provisional
Senior Python, and insufficient Instructional Designer states using frozen synthetic
production-graph replays. Narrow layout inspected; no provider calls or plan approvals.
User localhost:8515 session was not reset. See docs/ASSESSMENT_QA.md.

Final fresh-session screenshots also verified the reduced heading and expanded
employer/candidate source card at 1280px width, without repeated explanation.

Not yet verified: fresh live Nemotron overview quality or a reconciled same-input A/B
against the user's latest 27-posting portal run. Offline
tests prove contracts/rendering, not better retrieval or model reasoning. Existing
saved six-JD inventory is a different diagnostic corpus. No Git push/deployment.

## September 9 — repeatable input-only demo shortcut

Home's existing Explore demo button now loads a fresh editable Senior Java Developer
test ProfileDraft through Education & Certifications. It opens Education with earlier
sections reachable, uses manual/live workflow routing, and does not seed approvals,
inferences, a goal, market evidence, assessment or plan. A synthetic-input badge remains
visible in the sidebar; homepage copy discloses resetting current session progress.
Each click clears prior derived state and creates fresh input entry IDs. Ordinary
Start new analysis still opens a blank profile. Frozen demo illustrations remain for
existing fixture tests, but are not selected by the homepage demo action.

Verification: 825 tests pass, including four new shortcut/edit/reset/no-automatic-call
regressions; targeted lint passes. Browser-level localhost:8515 verification clicked
Explore demo and observed Education, saved 2018 Computer Science education, saved
2023 synthetic Java certification, zero confirmed items and the enabled Continue to
AI Strength Identification button. Left that page open. No live provider calls made.

## September 9 — production retrieval update (offline verified)

Supersedes the diagnostic-only status immediately below. Production deduplication
now merges only supported vacancy identities (same posting ID/canonical URL or
same employer requisition, with conflicting requisitions kept apart). Same-employer
similar descriptions produce informational links, never automatic merges or JD
transfers; different employers do not receive content-only duplicate links.

The combined service retains validated related-title discoveries and attempts their
missing-content retrieval within the shared budgets. Existing independent You.com
discovery remains. Failed direct content completion can now search You.com using
the Adzuna employer, complete original title and location. Each result is independently
validated: a different relevant vacancy is added with seed lineage; a verified
same-vacancy result can merge provenance and supply its better body. Individual
LinkedIn/Indeed/Glassdoor/ZipRecruiter vacancy URLs are distinguished from guides
and listing pages, labelled job-board copies, not employer-verified active postings.

Full-page Markdown is requested when advertised by the MCP search schema; older
servers use the existing Contents fallback. Returned page bodies are cached only
against their exact result URL. No direct REST integration or dependency added.
Enrichment and seed searches share bounded content/search budgets (default limits:
three independent You searches, up to four seeded searches, five Adzuna searches;
unused/failed work remains visible, not a claim of globally unavailable JDs).
This is not automatic background continuation through every pending posting.

Comparison/accessibility/canonical-cohort policies are unchanged. Related-role
retention does not promote those roles into the baseline target. Possible duplicate
counts are explicitly not verified unique-vacancy totals. Audit exports include
possible-duplicate links. No credentials, live provider calls, push, or deployment
were involved. Regression verification: full suite 821 tests; market subset 306.

Latest user decision: keep same-employer/content-similar postings as separate jobs
for now. Test inventory updated to 28 Adzuna plus six separate You.com jobs = 34
operational records and six JD documents. Five possible duplicate flags are only
informational, including the previously merged Cognizant content match. This is
not 34 verified unique active vacancies. Production deduplication not modified.

Offline replay of saved broad and refined You.com batches now preserves six
distinct relevant JD documents in combined-job-and-jd-inventory.json/.md under
outputs/senior-java-basic-case. 28 Adzuna seed rows plus five separately retained
You discoveries yield 33 source records after one strong Cognizant content-based
merge; four possible duplicates remain unresolved, so 33 is NOT a unique vacancy
count. Additional Autodesk requisition retained independently. No new API/model
calls or production changes; JD currentness/identity and job-board quality review
remain required. Checked inventory counts, distinct URLs and substantive body lengths.

Refined 28-posting You.com diagnostic: employer-focused queries, full_page Markdown,
60s crawl timeout, three results; 26 employer-domain restrictions and two unrestricted
queries. Three unique relevant substantive JDs (one Cognizant, two Autodesk), across
four searches; 24 searches did not yield a relevant individual JD. One strong
same-vacancy linkage remains Cognizant. Additional Autodesk vacancy is discovery,
not a second enrichment of the original input. Coverage did not improve over prior
five JD-bearing pages; restricting domains removed job-board copies. 29 calls total:
one correction rerun restored Java accidentally removed from a reordered title.
Saved all queries and bounded Markdown in outputs/senior-java-basic-case/refined-enrichment-results.json.
No production or model changes.

Batch employer enrichment diagnostic: reused September 7 Adzuna audit, skipped
three aged-out entries, merged two identical URLs, searched remaining 28 including
related titles via You.com (employer/title/Toronto/careers, count 3, full_page,
concurrency 3; no employer domain restriction). Found five distinct relevant
individual pages with substantive JD sections: Cognizant employer, Autodesk ATS,
CGI Glassdoor, Astra North LinkedIn and Atyeti ZipRecruiter. Only Cognizant original
5860849291 has previously established distinctive excerpt linkage; others require
identity/currentness review. Multiple Cognizant searches hit the same employer URL.
Seven searches were repeated because terminal truncation lost their first records;
35 total API calls, no new Adzuna or model calls. Saved bounded page content in
outputs/senior-java-basic-case/all-employer-enrichment-results.json; not a raw
untruncated response archive. No production changes or safe-stop bypasses.

Saved September 7 Adzuna 33-to-9 audit: 33 provider audit entries comprise three
age-window exclusions, nine selected EXACT_TARGET/TARGET_VARIANT entries, and
21 RELATED_TITLE entries excluded with expansion disabled. Two URLs repeat in
the latter group. The intermediate adzuna_validated_count is 25, but complete
historical merge lineage is not saved (duplicate_of null); do not attribute all
24 nonselected entries to duplicates. Several related-title classifications merit
review (Senior Developer - Java, Sr. Java Developer (Hybrid), Core/Backend Java).

Employer enrichment probe succeeded for saved Adzuna Cognizant job 5860849291:
one You.com title/employer/Toronto full_page search returned five results, one
substantive JD and four page-not-found responses. Employer requisition 00069350121
matches title, location, employer and distinctive Adzuna opening text; Adzuna has
no requisition ID, so linkage is content-based, not ID-confirmed. No production
changes or model calls. Summary: outputs/senior-java-basic-case/cognizant-enrichment-probe.json.

Bounded Adzuna URL extraction probe (job 5870556705): You.com exact-ID snippet
search returned no results; URL search with full_page returned five nonmatching
Adzuna pages with security checks. One direct You.com Contents fetch of the exact
job URL also returned a human-verification challenge, not a JD. Outcome:
JD_UNAVAILABLE for this tested URL. No bypass, model calls, or production changes.

Bounded Arbeitnow probe: three API requests returned 250/250/100 records. Three
Java-title postings were found, all ARQ London (standard/senior/lead) with substantial,
near-identical HTML descriptions. Pages 2/3 contained no empty descriptions and no
Canada/Toronto location matches. The sample includes UK and France, not just Germany.
Saved selected response records under outputs/senior-java-basic-case/arbeitnow-probe.json.
No integration or model calls; not a complete-market or active-status validation.

September 8 Toronto time: ran the three production You.com Senior Java Developer
Toronto query-family searches only. Each returned 12 results (0.82/0.90/0.65 seconds).
Captured wire arguments show domain filters translated to site operators, count 12,
month/year/year freshness, and no country/language parameters supported by this
connection. Results include non-target titles and non-Canadian locations; these are
discovery hits, not validated postings. Saved title/URL comparison under
outputs/senior-java-basic-case/you-query-results-20260908.json. No content fetches,
Adzuna or Nemotron calls, and no retrieval code changes.

A synthetic Senior Java Developer strengths-review request is available under
`outputs/senior-java-basic-case/nemotron-request.json`, built offline using the
production prompt/schema/payload builders. It includes three source-linked records
(employment, personal project, education); goal preferences are intentionally not
part of capability inference. No provider request or app approval was performed.

Strength inference now resolves evidence IDs exact-first, with unique hexadecimal
prefix repair (at least eight hex characters) scoped to the explicit evidence supplied
in the current request. Gateway validation context stays local, outside the provider
payload; the field validator repairs before UUID validation. Unknown, ambiguous,
malformed, too-short and duplicate-after-repair references fail. Successful prefix
resolutions emit a count-only log; downstream evidence retains full UUIDs. Other model
flows retain their existing validation. 155 profile/model/orchestration tests passed;
no live call or semantic capability changes were made in this step.

Capability inference v4 removes reasoning_summary and source_context_summary from
the output contract. The UI uses description; inferred evidence retains that description
and source IDs without a duplicate generated context. Prompts, demo data, fixtures and
the local request package match. Profile/UI/orchestration tests: 182 passed with one
Market AppTest 3-second timeout; the design-handoff module passed on isolated rerun.
Targeted Ruff passed. No live call was made; the 10,000-token limit is unchanged.

Capability inference v3 now instructs reusable professional names, semantic duplicate
avoidance, preservation of business actor roles and evidence-relevant limitations.
Schema descriptions carry this guidance; deterministic filtering also reserves exact
Core Competency list entries. No role-specific name blacklist or semantic rewrite was
added. The review payload/package is updated. All 59 profile tests and targeted Ruff
checks pass. Prompt-contract tests do not establish live model compliance; no live
call was made. Output cap remains 10,000 tokens.

At user request, capability inference now permits 10,000 output tokens instead of
2,048. The local Nemotron review request and package were updated to match. All
19 profile inference tests pass, including the request-budget regression assertion.
No live call was made; timeout, retry settings and other model flows are unchanged.

The September 8 resume input now has a local, Git-ignored `nemotron-package` directory
containing normalized evidence, exact system/user prompts, output schema and assembled
NVIDIA request body. Export used production builders offline, retained the existing
2048-token limit, and made no new model call. No successful response is claimed.

## Resume-based strengths test — September 8, 2026

A user-authorized backend test used the current `infer_capabilities` service and unchanged
`capability-inference-v2` prompt on a two-page supplied resume. Four employment records, two
independent projects, two education records and six credentials/training entries were normalized
into 14 source-linked evidence items. Professional summary and core competencies were retained;
name, contact information and profile links were excluded. Employment maturity started at APPLIED,
independent projects at DEMONSTRATED, and education/training at EXPOSURE; inferred outputs were
to remain unconfirmed. Test-only approval flags enabled the source-input service gate without
creating any approval or profile record in the website, database or memory store.

With the saved-file-only NVIDIA configuration, the existing 2,048-token output limit, a 90-second
timeout and at most one retry, both provider calls timed out. Total elapsed time: 180.54 seconds.
Actual outcome: FAILED / ModelTimeoutError; zero validated capabilities. The local ignored
`outputs/resume-skills-test-20260908/` folder preserves the minimized input and actual result.
No Adzuna, You.com, goal selection, market analysis or candidate approval was performed.
Any separately presented assistant resume review is not Nemotron output or a successful product test.

A second user-requested run of the same input and production inference contract completed after
179.27 seconds with FAILED / ModelTimeoutError. Unlike the first run, provider tracking recorded
one returned response (3,680 input tokens, 2,048 output tokens) followed by one timed-out request.
The returned response did not pass gateway validation; the single repair/retry then timed out.
Zero capabilities were validated by the service. Reaching the configured output cap suggests
possible truncation, but this runner did not retain the rejected response's finish reason or
validation issue, so its exact rejection reason is not established. No rejected content was
substituted or published as model-generated skills. The separate actual result is retained in
the ignored `outputs/resume-skills-test-20260908/result-attempt-2.json` artifact.

## NVIDIA connectivity check — September 8, 2026

One user-authorized, profile-free structured request to the currently configured
`nvidia/nemotron-3.5-lightning-30b-a3b` model through the production gateway timed out after
30.11 seconds (`ModelTimeoutError`). The request asked only for a JSON status of `ready`,
with 32 output tokens, thinking disabled, a 30-second timeout and zero retries. Inspection
and external tracing were disabled for this check. No response passed schema validation.
This reproduces a timeout with a tiny input; it does not distinguish provider/model latency
from the network path. No production settings or application code were changed.

A second explicitly requested identical check also timed out after 30.10 seconds, with zero
automatic retries and no profile data. Both tiny-input checks failed; the underlying provider
versus network cause remains unconfirmed.

A third explicitly requested identical check timed out after 30.12 seconds, again without
automatic retries or profile data. Three consecutive tiny-input checks have now failed.

An offline comparison against commit `9df5bd5` found identical NVIDIA URLs, authentication
header construction, request bytes and timeout arguments for equivalent tiny text and structured
requests (dummy credentials and intercepted transport; no network calls). The HTTP transport itself
was unchanged. However, the UI gateway refactor replaced its hard-coded one retry with the Settings
value, currently two retries. This increases repeated-timeout waiting from approximately 180 to
270 seconds per posting, but cannot explain the three zero-retry connectivity failures. A direct
network/provider isolation check remains needed; this audit does not establish NVIDIA as the cause.

At the user's request, one live tiny-input comparison loaded the NVIDIA adapter and gateway
directly from commit `9df5bd5` into an isolated Python process, without replacing checkout files.
Their shared model schemas, errors, roles, protocols and provider base are unchanged between
that commit and HEAD. Using the current configured key/model and the same prompt, 32-token
output limit, 30-second timeout and zero retries, the old implementation also raised
`ModelTimeoutError` after 30.17 seconds. This reproduces the failure without the recent adapter
and gateway changes; it is not a recreation of the historical environment/model or a full old-app
acceptance test. No profile data was sent and no production settings were changed.

After the user saved the replacement key (package `.env` modified September 8 at 13:22 local),
the old adapter/gateway check was repeated using a diagnostic Settings subclass with only explicit
initialization and dotenv sources. OS environment and secret-directory overrides were bypassed;
no cached settings were used. The key came only from the newly saved package `.env` and was never
printed. The same tiny request timed out after 30.20 seconds with zero retries. VS Code's disabled
terminal environment injection did not affect this file-only test. Current app configuration
and checkout code remain unchanged.

The next user-requested repeat of the same old-commit, saved-file-only test succeeded in
18.16 seconds, returning the schema-validated status `ready` from
`nvidia/nemotron-3.5-lightning-30b-a3b`, with zero retries. This confirms that this saved-key/model
combination can complete a tiny request now; it does not prove full-workflow reliability or that
old code is superior, since the immediately preceding identical old-code test timed out.

The subsequent user-requested latest-code check (`f83947b` gateway and adapter), using the same
saved-file-only configuration, prompt, model, output limit, 30-second timeout and zero retries,
also succeeded: validated `ready` in 27.33 seconds. Both old and new connection paths have now
completed the tiny request. These sequential observations do not establish a code-caused latency
difference or resolve the earlier intermittent timeouts and full-workflow reliability limitations.

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

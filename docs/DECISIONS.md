# Decisions

## September 12 — fix visual parity and unknown-zero coverage

The user explicitly authorized treating unconfirmed competencies as zero for radar coverage.
This supersedes the earlier unknown-only-group suppression rule, not the evidence or accessibility
policy. Apply the change to read-only summaries of existing results, without another model call.

The first visual implementation did not reproduce the approved mockup. Replace generic category
boxes with a role-to-target journey and a connected numbered action list. Select detail views from
existing milestones; do not add a prerequisite, bridge, decision action or duration. Reuse full
conditional action text and completion criteria. Styles live only in an isolated native Streamlit
v2 component; this is not an architecture/provider change or a portal-wide CSS override.

Verification must include actual saved-result replay, desktop and phone screenshots, action-detail
clicks, regression tests and a restart that verifies modules in the serving process.

## September 12 — post-checkpoint goal consolidation and read-only visuals

New journeys offer five direction choices: transition and destination planning share
TARGET_CAREER_PATH. Preserve ROLE_TRANSITION and its field policy for historical goals;
do not migrate approved records or change their versions.

Analysis counts use the same final public comparison rows as the table. Remove exact
duplicate rows only; do not combine semantically different qualifications. The radar
is demonstrated coverage, not readiness: directly demonstrated rows / all grouped rows.
An all-unconfirmed group is undefined, not zero. At least three meaningful groups and
no undefined group are needed; unresolved processing suppresses the polygon. Prerequisites
remain visible in the comparison, outside the radar. Confirmed development needs are
separate from unconfirmed evidence. No weighted match, probability or accessibility policy changes.

Consolidated responses gain one optional display_dimension enum in their existing call.
Group from target expectations, never candidate strengths; no extra model call or forced
six-axis list. Old results remain valid without grouping. Legacy responses reuse validated
EmployerOverview groups. Prompt versions distinguish this additive presentation contract.

Plan overview nodes correspond one-for-one to the selected plan's milestones, in their
existing order. Milestone types provide short labels; actual conditions and completion
checks remain immediately below. Do not invent durations, bridge roles or guaranteed outcomes.
V2 completion tracking, durable progress storage and readiness reassessment remain deferred.
No new provider, dependency, scoring policy or persistence architecture is introduced.

## September 12 — common writing style, separate career judgments

All goal categories share public-copy guidance and compact rendering, not a common positive
verdict or leadership roadmap. Preserve current routing and target requirements (including the
existing V1 need for a specified target before live retrieval); do not invent a destination for
exploration or a historical comparison for reassessment. Shared instructions attach to both the
consolidated author/review contracts and the optional legacy synthesis/plan wording contracts.
Model-owned conclusions and deterministic policy fields retain their existing authorities.
Hide unrelated display context without deleting evidence, prerequisites, material conditions,
source references or original statuses. New instructions apply on rerun, never by regenerating
or silently rewriting an approved plan during presentation.

## September 12 — career guidance copy and a positive application condition

Leadership copy separates credible direction from current readiness. Keep non-target records in
the audit and show concise core comparisons, strengths and grouped questions. No universal example
verdict, management checklist or hard-coded role names. Model author remains at temperature 0.1.
Resolving unknown experience can reveal a shortfall, so code attaches a favourable readiness and
employer-requirements gate plus defer/reassess branch to APPLY actions before constructing the
versioned plan. Completion records a role-by-role apply-or-defer decision rather than forcing an
application. Structured after_clarifying links remain auditable; public conditional development
copy no longer repeats the full competency list. Mentoring/workstream leadership must not imply
formal management, and incident support must not become ownership in strengths or plan prose.

## September 12 — explicit leadership decisions instead of more prose caveats

Use a shorter dedicated leadership contract on the existing consolidated route. Establish posting
benchmark scope before target competencies. Encode evidence state separately from partial or
transferable match status, so an unknown remainder is not a confirmed shortfall. Check structured
contradictions and action dependencies; retain source aliases internally. Exact candidate excerpts
support claimed shortfalls but still require semantic review. No profession-specific verdicts.

Generate public readiness from its validated field. Attach explicit development conditions in
code to both plan fields, with storage bounds preserving full text. Optional repeated focus prose
must not block valid typed clarification. Legacy routes retain their contracts. Invalid substantive
output gets bounded repair and withholds a plan if unresolved. Assessment/plan authors use 0.1;
repairs/reviewers use 0.0. Temperature changes variability, not factuality. Retrieval is unchanged.

## September 12 — target-led leadership progression on the consolidated route

LEADERSHIP_PROGRESSION with a specified target now shares the consolidated five-description
assessment/review/plan mechanics, without changing the user's goal enum. The target defines
discipline, requested level and roadmap destination; the current role supplies candidate evidence,
not a replacement search title. No universal management checklist or forced bridge role.

JSearch remains the only discovery provider. Search uses target title (plus explicitly requested
seniority) and location, country=canada, language=en, date_posted=all, num_pages=1; no cursor,
fields projection or invented seniority/work-mode API filters. Existing location/currentness,
deduplication and bounded missing-description detail checks remain. Leadership batch selection
prioritizes target/variant relevance, target-domain support and level alignment before text length;
the independent-employer pass and five-description cap remain. Missing domain wording is a
lower selection priority, not automatic exclusion; actual duties may establish relevance.
Different disciplines and director-level scope must remain context, not target-baseline gaps.

Leadership interpretation preserves technical delivery/mentoring strengths without inventing
formal reports, hiring or performance authority. Unreported scope is CLARIFY, including partial
matches; development after an unknown must be conditional on absence. Roadmap actions and
completion checks should resolve uncertainty before building authorized leadership experience.
No fixed timeline remains a valid preference; approvals still reference the exact plan version.

## September 12 — target-role planning uses the consolidated assessment route

The actual portal target-plan case retained eight related postings but the legacy selector admitted
none. The successful transition test did not cover that goal route. Use the existing consolidated
assessment for TARGET_CAREER_PATH as well as ROLE_TRANSITION, retaining the user's goal enum and
preferences in model input and audit. Do not relabel related postings as exact to bypass selection.
Related inputs require the user's expansion permission. Goal-less exploration and other directions
retain their existing routes. Historical per-posting target-plan replays require an explicit
runtime-only legacy_target_plan_pipeline injection, default false; no silent live fallback.

## September 11 — separate JSearch response latency from detail latency

Observed real market-retrieval timeouts at 30.259s/30.425s. Give search a configurable 90s
read allowance while bounding connection setup and total time. Do not apply this increase to
every detail/model request or add billable automatic retries. This addresses premature search
timeout risk without weakening evidence checks; persistent provider failures still stop safely.

## September 11 — diagnostic visibility without relaxed analysis rules

User approved exposing the safe error code and recording failed attempts. Add a small
allowlisted local diagnostic artifact instead of logging exception payloads or full traces.
Keep failures distinguishable from candidate gaps; preserve profiles and available market
snapshots. Diagnostic writes are best-effort and must not replace the original failure.
This does not alter retrieval/assessment thresholds, credentials or retry quotas.

## September 11 — use the JSearch response contract at the retrieval boundary

Normalize the supplied structured fields directly instead of treating JSearch as a generic
web-page scraper. Use full descriptions when present; bounded exact-ID details for missing,
truncated or highlights-only content; labelled job highlights as limited fallback. Do not turn
salary/benefits/provider metadata into skills. Optional nulls are not rejection conditions.
Keep all application options as one job, preserve raw/failed/deferred counts, and record routes
without following cursor pagination. This is an adapter/routing change, not a relaxation of
source grounding or a new career-fit policy. Existing full-stack relevance remains a separate issue.

## September 11 — separate bounded candidate fit from market prevalence

User approved removal of the multiple-employer COMMON-label prerequisite for a positive
fit assessment. COMMON remains wire-compatible but now means central work in supplied roles;
SPECIALIST means narrow platform/domain/direction, not low employer count. Same-role and
transition prompts align on this definition. One substantive role can support limited fit,
not market-wide demand or universal requirements. Model interpretation still evaluates core
work, ownership, scope and unresolved barriers; demonstrated evidence is still required for
positive verdicts. No profession-specific rules or automatic verdict upgrades were added.

Processing failures now withhold accessibility (null) in saved assessments rather than assigning
INSUFFICIENT_CANDIDATE_EVIDENCE. Explicit model judgments about genuinely insufficient inputs
remain available. Plans remain blocked on validation issues or absent verdicts. The model reply
schema still requires a verdict; nullable storage represents validation failure only. Historical
records are not rewritten; UI presents any processing issue as Assessment needs review.

## September 11 — discovery audit versus eligible target-market cohort

Preserve every normalized JSearch discovery in retrieval audits, including exclusions.
Only EXACT_TARGET, TARGET_VARIANT and RELATED_TITLE classifications enter target-market
postings and model-bound content. Do not relabel unrelated jobs to satisfy snapshot counts or
weaken the count invariant. Build JSearch summary buckets from the same validated classification
used for selection, without a second title-only classification. This fixes accounting; it does
not settle whether particular Java/full-stack descriptions are semantically relevant.

## September 11 — user-directed JSearch replacement

Replace both active market providers with RapidAPI JSearch. Old adapters/schemas remain readable
for historical artifacts but are never fallback calls on the JSearch route. Use fixed RapidAPI
host with header authentication, one bounded search, details only for absent/visibly truncated
descriptions, at most five details, no automatic retries. Keep provider-returned descriptions
without pretending length establishes completeness. Preserve candidate/model rules and top-five
selection. Setup is not a paid-plan authorization or live success claim. Credentials stay local.

## September 11 — separate public review wording from internal evidence

User approved the cleaner combined Analysis presentation and requested code/prompt alignment
before a later Git push. Same-role/transition prompts and their final reviews now share concise
public-copy guidance; legacy synthesis and plan wording also forbid inline IDs. Version labels
use `concise-v1`. Keep reference fields and all eligibility/grounding/approval rules unchanged.
UI removes citation notation only at display time, with original records retained in details;
new concise results retain their complete material conditions. No new model calls or publishing
are part of this implementation. Passing contract tests is not a semantic model-quality claim.

## September 11 — four targeted transition interpretation corrections

User authorized base/specialty separation, mixed-evidence splitting, consistent unknown
handling and direction-specific planning. Implement as revised transition author/reviewer
instructions, not additional lexical gates or role-specific scoring. Keep same-role review
unchanged through a parameterized reviewer prompt. Retain existing schema, reference checks,
retrieval and approval boundaries. Validate with the same five-description live case; do not
force a more positive accessibility result or a minimum transfer count.

## September 11 — user-authorized career-transition rule replacement

Use a dedicated transition prompt/schema for ROLE_TRANSITION, sharing transport,
bounded selection and integrity checks with same-role assessment. Preserve current
strengths, make transfer boundaries explicit, and distinguish missing information from
learning/experience needs. Do not append role-specific exceptions to legacy scoring.
New transition state feeds both Analysis and Plan; approvals/invalidation stay intact.
Other goal modes and same-role prompt semantics are not changed by this decision.

## September 10 — separate same-role interpretation path

User authorized replacing the brittle scoring path for same-role job moves, not
accumulating lexical exceptions or tuning for a single role. For Current Market
Analysis with the same normalized current/target title, analyze at most five
relevant descriptions plus approved candidate evidence in one structured response,
then critically review it. Career transitions remain unchanged. The model interprets
common versus specialist expectations; code validates structure, references and
plan bases, attaches identity/provenance, and preserves approval/invalidation.
No old canonical-profile thresholds silently overwrite this assessment.
Concise source-linked interpretation is not a guarantee of semantic correctness;
the live validation report explicitly records remaining content failures.


## September 10 — description-supported role relevance before batch extraction

Do not reject a compatible occupational heading solely because the target specialty
is absent from its title. Permit bounded discovery of compatible headings; use
substantive work/qualification text to admit DESCRIPTION_SUPPORTED_SPECIALTY variants.
Preserve literal titles and exact/variant counts. Retain level/authority boundaries,
exclude preference-only/negated/marketing mentions, and let batch extraction retain
specialist expectations separately or reject materially different scopes. This is a
generic specialty rule, with a functional software-engineer/developer alias, not a
Java-, employer-, or candidate-specific exception. Re-evaluate stale title-only
rejections when full content becomes available. This relevance signal must never
prove vacancy identity or relax deduplication/enrichment identity checks.

## September 10 — isolate batch theme failures with one bounded repair

A malformed cross-field theme must not discard independently valid siblings. Keep strict
structural envelope validation in ModelGateway; apply cross-field, citation and semantic
checks atomically per theme before any canonical use. A structural envelope failure or
invalid posting-review identity still safe-stops. Make at most one initial request plus
one indexed repair request, both with gateway retries disabled. Repair cannot modify valid
themes, invent source IDs, alter ANY_OF choices, or downgrade core importance. Explicit
preferences can be corrected to ADDITIONAL without becoming required qualifications.
Retain rejection reasons as sanitized rule messages and original theme indexes. Unresolved
core/supporting qualification or prerequisite failures block a whole-role verdict; rejected
optional/duty/specialist evidence lowers confidence without inventing candidate gaps.
Persist processing status in the canonical contract for truthful UI messaging and replay.
No retrieval, comparison, source validation or plan-approval safeguards are relaxed.

Production Fireworks now supplies explicit `reasoning_effort=high` for the exact configured
`accounts/fireworks/models/glm-5p3-flash` deployment when no override is provided. This follows
the saved controlled experiment in GLM_REASONING_CONTROL_FINDINGS.md; it is not thinking-off
or a hard reasoning budget. Other model defaults remain unchanged. The optional Settings field
`FIREWORKS_REASONING_EFFORT` permits low/medium/high overrides without changing model routing.
The repair prompt is standalone and requests only indexed corrections, not another full profile.
Rejected names may be shortened to source-grounded labels while kind, category, importance
and alternatives remain protected. Repair supports must be a subset of original posting/quote
pairs, preventing a rejected theme from being replaced by an unrelated new expectation.
Prompt v3 requests compact source labels without unsupported descriptive wrappers. Do not
relax source validation or invent a positive fit when the saved truncated sample remains weak.

## September 10 — rank descriptions by words; honor the live MCP parameter schema

User requested the five longest relevant descriptions instead of a hard length cutoff.
Word count is the primary ordering after relevance/geography/nonempty filtering; previous
selection ordering is a tie-breaker only. Low retrieval quality remains visible to extraction
and confidence policy, rather than excluding every available excerpt up front. No word count
proves a complete description. Existing source grounding and safe-stop rules are unchanged.

Connection probes isolated a You.com full-page request mismatch: live MCP advertises a string
enum, not the nested REST-style extraction object. Send the string for that schema, retain
the object for an explicitly object-shaped schema, and use the existing contents fallback
when its shape is unknown. Never guess an argument merely because its name exists.

## September 10 — consolidate five descriptions before candidate comparison

The approved batch experiment is now a production website service. The model groups up to
five usable exact/variant descriptions into role-level themes; code validates source lineage
and attaches deterministic counts. Importance is separate from explicit employer obligation.
Core/supporting expectations drive baseline comparison; specialist conditions remain audit
context and optional advantages cannot create baseline gaps. Partial descriptions cap
confidence; rejected primary expectations preserve the safe-stop coverage guard.
The UI consumes the same canonical/comparison/synthesis objects, not a separate model narrative.
Legacy replay service defaults remain compatible; the website binding is explicitly tested.
See FIVE_POSTING_PRODUCTION_BATCH.md for boundaries and remaining live acceptance work.

## September 10 — reconcile design reference with current product decisions

Restore the reference's native Streamlit visual hierarchy without reverting later
product choices. Keep one Career assessment stage, one visible numbered competency
block, and concise statuses. Use a bounded canvas, consistent theme and card
composition rather than CSS overrides or further ad-hoc prose deletion.

Plan actions appear once in an ordered roadmap; supporting explanations remain
available in one details section. A sole supported route is not presented as a
choice. No model/provider configuration, evidence calculation, or approval policy
is changed. Visual acceptance and live-result correctness are tracked separately.

## September 10 — concise presentation is separate from evidence validation

User requested a cleaner, less repetitive assessment. Keep short structured results
in the main view, and collect original explanations and source/processing diagnostics
in one optional detail section. Do not reduce grounding standards or treat less
visible evidence as less validated evidence. No provider prompt or accessibility
policy change is part of this presentation pass.

## September 10 — one visible competency comparison block

User requested numbered competency information and short statuses instead of
dropdowns and evidence paragraphs. Use one native static table and retain a compact
context column to distinguish duties, preferences and employer-specific conditions.
Keep approved evidence and source lineage in backend/audit storage, without changing
comparison meaning. Unknowns and failures must not be converted to No.

## September 10 — assess resolved baseline evidence; retain unanswered conditions

User authorized removing the blanket insufficient-evidence outcome for isolated
unanswered or employer-specific conditions. Require at least two non-employer-specific
hiring expectations, two resolved comparisons and strictly greater than 50% baseline
completion. Unverified mandatory baseline prerequisites still prevent an overall
verdict. Source independence and content-quality gates are retained. A resolved
comparison needs Moderate/High confidence and no unknown/failure/pending question;
confirmed mismatches remain negative evidence. Preserve all comparisons, but omit
unresolved votes when the coverage gate permits a bounded assessment. Open questions
cap confidence at Moderate and Apply now at Apply selectively. Display separately
what needs candidate clarification, employer verification or processing retry.
No model prompt, retrieval, fit-threshold, plan-approval or session-reset change.

## September 10 — employment tenure is deterministic; relevance remains evidence-based

Calculate dated employment elapsed time in code, merge overlapping periods and use
the analysis date for explicitly current roles. Keep the user's self-reported years
separate and do not rewrite approved records. Send duration calculations into the
comparison contract instead of relying on model arithmetic. A role's tenure does
not automatically establish duration for every tool or technology mentioned there.
Incomplete dates and pending relevant-duration questions are unknowns, not confirmed
shortfalls. Explicit model UNKNOWN must not become supported merely because a match
enum was also returned. Clarification-linked uncertainty must participate in the
synthesis sufficiency gate. No role-specific retrieval or accessibility rule added.

## September 10 — bounded paraphrases and milestone-local fallback

Allow a small explicit vocabulary/grammar equivalence set, not unconstrained
semantic similarity or another LLM judge. Preserve ordered meaningful tokens,
numeric qualifiers, technical symbols, conditions and proficiency levels. Keep
unchanged original wording where equivalence is not established. A rejected
milestone retains both action and outcome, while other valid milestones survive.
All structural/identity/risk/assumption checks remain whole-response gates before
wording is accepted. Expose non-durable rejection metadata and sanitized logs;
do not store model reasoning or candidate text in rejection diagnostics.
No change to accessibility/synthesis policy is included in this wording correction.

## September 10 — separate Plan transport success from recommendation quality

The bounded GLM Plan test completed in 4.34 seconds but failed production wording
validation. Retain deterministic fallback; do not equate model completion with
accepted plan generation. The four-comparison diagnostic is not a full canonical
market assessment. Its clarification gaps exposed an Aspirational/Development
policy inconsistency that must be reviewed independently of model choice.
Do not feed the semantically flawed five-JD batch into production Plan. No
production configuration or policy change was made in this diagnostic activity.

## September 10 — explicit GLM reasoning setting, separate semantic gate

Fireworks returned a definitive thinking-only error for GLM 5.3 with none. Do not
equate shorter output instructions with disabling reasoning. A controlled request
changing only reasoning_effort to high completed successfully (86.43 seconds) under
the unchanged 30k ceiling. Keep default production behavior unchanged until the
semantic contract is corrected: valid JSON and quote IDs still concealed duties
promoted to qualifications, missing prerequisites and compound/truncated names.
No hidden reasoning traces stored; no unsupported inference about default Max or
an exact reasoning-token split. Generation and content quality are separate gates.


## September 10 — stop treating input count as the only GLM batch bottleneck

Five longer descriptions reproduce the consolidated GLM failure at the 30k output
ceiling with only 3,546 input tokens. Record-count reduction alone has not succeeded
at 34, ten or five records. Do not silently shrink further, raise limits or substitute
a result. Preserve the empty final response and typed rejection; generation/task
contract investigation is a separate next step requiring user direction.


## September 10 — distinguish Nemotron completion from assessment validity

The user-authorized Nemotron replay uses the exact saved task/user input and schema,
with provider-specific NVIDIA JSON-object/schema-prompt and thinking-off settings
explicitly disclosed. No durable configuration switch. A complete JSON response
with grounded-looking citations is not sufficient: duties were promoted to mandatory
qualifications, one employer's statement leaked into another, and unrelated quotes
supported broad themes. Keep this output diagnostic, not a trusted role baseline.


## September 10 — ten-record cap does not resolve consolidated-call failure

The user-requested ten-record subset cut input tokens from 10,023 to 5,328 but
again exhausted the 30k output ceiling without final JSON. Preserve the same
contract/settings to isolate the input selection change. Do not treat the failure
as network timeout, invent a consolidated profile, raise limits or retry silently.
Diagnostic selection is explicit and does not alter production role ranking.


## September 10 — full batch failure is not a usable consolidated assessment

Honor the full-scale test using all 34 available operational source records, while
disclosing 28 are snippets and only six are longer retrieved documents. Keep
source identities/possible-duplicate flags and role scopes. One GLM consolidated
request exhausted 30k output tokens without final JSON at 248.98 seconds. Reject
it rather than reconstructing an invented profile, silently dropping sources,
raising token limits, retrying, or changing the active website. Batch architecture
remains experimental; a failed single-model attempt is not proof the idea is invalid.


## September 10 — measure parallel extraction before production adoption

Use a separate opt-in diagnostic runner with independent gateways, two workers,
four calls and a shared deadline. Preserve production prompts and validation.
The measured 190.50-second batch shows overlapping requests work; the sum of
durations (369.99 seconds) is not a controlled serial baseline. Keep source-quality
and normalization failures visible. Do not automatically modify the active website
or conclude four mixed-length inputs predict ten full-description throughput.


## September 10 — reduce output repetition without dropping evidence conditions

Ask for concise sentences and at most two short exact comparison excerpts; reject
overlong structured answers rather than truncating evidence. Keep qualifiers,
AND/OR relations, match dimensions and evidence IDs. Only request plan wording
edits, restoring immutable skeleton fields in code through validation context.
Bind comparison requirement IDs in code, but retain model-derived transferable
capability labels because they are semantic content, not internal metadata.
Legacy full replies remain subject to identity/tamper checks. Deduplication is
case/whitespace based, not semantic merging of potentially distinct limitations.
Do not lower the configured 30k ceiling or claim a latency gain without measurement.


## September 9 — live contract findings, not model-only blame

A production GLM response exposed deterministic false rejections of an explicit
role-named qualification and ordinary action-word inflections. Recover these
with generic source-grounded rules, not profession-specific exceptions or relaxed
quote validation. The same raw response is replayed to distinguish code changes
from provider variability.

Comparison receives source dates, source reference and explicitly recorded
current-employment status. This is temporal context, not proof of equal years in
every technology. Unknown historical flags remain null; no old evidence is
silently upgraded. Non-contiguous assembled excerpts remain invalid even when
their individual sentences exist in the source. Future run audits record the
loaded pipeline/prompt versions to distinguish stale-runtime results from current
contracts. Synthesis must retain the separate hiring/preference/work tracks.

## September 9 — recurrence is not comparison eligibility

All extracted statements remain auditable. Grounded primary-role hiring asks
are eligible for comparison even when uncommon or employer-specific. Legacy
CORE/SECONDARY/OPTIONAL recurrence labels no longer determine that eligibility.
Required/preferred/unspecified conditions remain source-specific; no voting rule
turns an uncommon requirement into an optional preference or a universal demand.

Canonical grouping separates hiring, preference and responsibility statements
even for the same concept. Their comparisons share evidence/provenance contracts,
but only hiring expectations contribute candidate hiring gaps and accessibility.
Related-role context and ambiguous fragments remain outside that baseline.

Overall readiness requires usable role coverage and completed hiring comparisons;
one surviving skill is not enough. Coverage uncertainty is not a candidate
capability gap. Preserve individual strengths and approved timeline preferences;
use exploration/evidence verification when an overall verdict is unsupported.
No role-specific shortcuts, retrieval changes or model-provider changes are part
of this pass. See EVIDENCE_PIPELINE_REPLAY.md for frozen evidence and test limits.

## September 9 — Fireworks streaming and explicit live output ceiling

User requested the actual website use configured GLM 5.3 Flash and increase output
capacity to 30k. A nullable Settings.model_max_output_tokens override is applied
at the gateway before dispatch/inspection; it is unset by default. Local ignored
configuration selects 30000, Fireworks and streaming without changing provider
defaults for other deployments. GLM's required thinking is left enabled by its
provider default; no reasoning trace is exposed or persisted.

The earlier diagnostic demonstrated that per-chunk deadline checks are not a
sufficient cancellation mechanism. Production Fireworks streaming is isolated in
a child transport worker, with parent-side timed communication and kill/reap on
timeout. Credentials pass only through stdin, never command-line arguments or
logs; the network destination is fixed. Completed final answer text and usage are
normalized through the existing adapter/gateway. Partial streams and length-
terminated JSON cannot silently become validated workflow results. No changes
to requirements, comparison/accessibility policy, or human approvals are implied.

## Activity 8: Parallel Adzuna and You.com discovery

Adzuna structured discovery and You.com MCP web discovery run concurrently as independent bounded
lanes. Each lane applies posting, title, geography, freshness, and deduplication validation before
merge. Cross-source duplicates retain Adzuna's structured fields, while matching You.com content
may enrich a thin record. One failed lane preserves healthy evidence from the other but lowers the
separate source-coverage confidence. Provider selection remains internal to the Market Intelligence
Service, preserving provider-neutral graph and career-analysis boundaries.

## 0. Provider-independent hosted LLM architecture

**Status:** Accepted for initial planning

Because the available local RAM is limited to 16 GB, the project will use hosted LLM APIs behind a provider-independent adapter rather than hosting a large model locally. NVIDIA Nemotron through Fireworks or the NVIDIA API is one candidate; other hosted providers will be evaluated before final selection.

## 1. Product supports every career stage

**Status:** Accepted for Activity 1

The product is available to students, early-career professionals, mid-career transitioners, senior professionals, leaders, explorers, and returnees. Career stage changes the analysis performed, not product eligibility.

## 2. Market opportunity intelligence is core

**Status:** Accepted for Activity 1

The product must analyze current market opportunities and credible historical evidence, alongside candidate accessibility and career strategy.

## 3. Market evidence must remain qualified

**Status:** Accepted for Activity 1

Exact-title and related-title markets are analyzed separately. Current counts describe results found through searched sources, not complete market totals. Historical availability claims require credible historical evidence.

## 4. Candidate evidence and market conclusions remain separate

**Status:** Accepted for Activity 1

Market availability and candidate accessibility are separate assessments. Student evidence is represented without overstating professional experience. Gaps are divided into skill, experience, leadership/scope, evidence, and prerequisite categories.

## 5. Career outcomes are not guaranteed

**Status:** Accepted for Activity 1

The product will communicate uncertainty and will never guarantee jobs, promotions, salaries, offers, titles, timelines, or other career outcomes.

## 6. Synthetic personas validate the MVP

**Status:** Accepted for Activity 1

The MVP will be evaluated with three synthetic personas: a student, a mid-career transitioner, and a leadership-progression candidate.

## 7. Product remains a career intelligence system

**Status:** Accepted for Activity 1

The MVP is a career intelligence and strategy system rather than an automatic job-application bot.

## 8. SQLite is the authoritative MVP business store

**Status:** Accepted for Activity 2C

SQLite is the authoritative store for confirmed user records, retained market evidence, derived analysis records, approved plans, approval history, and related business metadata. Derived analysis remains distinguishable from candidate facts and objective market facts.

## 9. LangGraph checkpoints are workflow persistence, not business authority

**Status:** Accepted for Activity 2C

LangGraph checkpoints support pause/resume, retries, recovery, routing, and temporary workflow context. They are not the authoritative source for confirmed profiles, approved goals, approved plans, or validated market history.

## 10. mem0 is optional contextual memory only

**Status:** Accepted for Activity 2C

mem0 remains optional and unresolved for the MVP. If enabled later, it may retain approved contextual preferences and rejected directions, but it must not replace authoritative business records or store raw resumes.

## 11. Large source documents are referenced rather than repeated in graph state

**Status:** Accepted for Activity 2C

Large resumes, web pages, HTML, job descriptions, and provider-native responses are referenced by IDs, hashes, or content references rather than repeatedly copied into checkpoints.

## 12. Graph state is serializable and provider-agnostic

**Status:** Accepted for Activity 2C

Graph state contains serializable workflow context and references, not secrets, provider clients, database connections, or active MCP sessions. It remains independent of a specific model provider.

## 13. Confirmed profiles, approved goals, and approved plans are versioned and immutable

**Status:** Accepted for Activity 2D

Confirmed profile versions, approved career goals, and approved career plans are versioned. Confirmed profiles and approved plans are immutable; corrections or revisions create new versions linked to the superseded version.

## 14. Derived analysis records are run-scoped and provenance-linked

**Status:** Accepted for Activity 2D

Requirement comparisons, gaps, accessibility, bridge, timeline, and plan interpretations retain run, profile, goal, market, source, and workflow provenance. They record system conclusions for a run and are not promoted to candidate facts or objective market facts.

## 15. Original external evidence is preserved alongside normalized interpretations

**Status:** Accepted for Activity 2D

Original source records, job postings, and employer titles are preserved. Normalized titles, role families, and extracted requirements are interpretations that must not overwrite original evidence.

## 16. Data models separate evidence, analysis, and planning records

**Status:** Accepted for Activity 2D

The conceptual model keeps confirmed facts, retained market evidence, derived analysis, plan records, and workflow/audit records distinguishable with separate authority and approval rules.

## 17. Approval records reference the exact entity version presented

**Status:** Accepted for Activity 2D

Approval records retain the entity version and presented-data reference or hash so approved data cannot silently differ from what the user reviewed.

## 18. Use You.com MCP as the MVP external search/content boundary

**Status:** Accepted for Activity 2E

You.com MCP provides the approved external search and content capability through the MCP Client Layer. Application services retain planning, validation, interpretation, and career reasoning.

## 19. Do not build a custom Career Data MCP server for the MVP

**Status:** Accepted for Activity 2E

Internal career data remains behind Domain Services → Repository Interfaces → SQLite. A custom server may be reconsidered for independent deployment, multiple consumers, multiple agents, or justified organizational boundaries.

## 20. Internal persistence uses repository interfaces

**Status:** Accepted for Activity 2E

Repositories provide the internal boundary to authoritative SQLite storage without introducing MCP transport complexity inside the MVP application.

## 21. Hosted LLM access goes through the Model Gateway

**Status:** Accepted for Activity 2E

Domain services and LangGraph use a provider-independent Model Gateway and provider adapters. Provider SDKs do not leak beyond adapter boundaries.

## 22. Logical model roles remain separated

**Status:** Accepted for Activity 2E

Extraction, reasoning, and optional validation are distinct logical roles even if one hosted model fulfills more than one role initially.

## 23. Final model/provider choice is evaluation-driven

**Status:** Accepted for Activity 2E

The final model and provider will be selected through project-specific evaluation rather than public benchmarks alone.

## 24. MCP and provider objects never enter graph state

**Status:** Accepted for Activity 2E

Graph state contains serializable references and validated results, not MCP sessions, provider clients, SDK objects, secrets, or credentials.

## 25. Confidence is multidimensional, not a single opaque score

**Status:** Accepted for Activity 2F

Confidence is tracked separately for profile, evidence, market, analysis, bridge, timeline, and plan dimensions, with reasons and limitations.

## 26. Failure handling uses bounded retries and explicit degraded mode

**Status:** Accepted for Activity 2F

Retries are bounded, reason-specific, traceable, and used only for appropriate technical/transient failures. Degraded mode is explicit and does not override unsafe stop conditions.

## 27. External content is treated as untrusted data

**Status:** Accepted for Activity 2F

Retrieved postings, reports, pages, and tool results are evidence, never instructions. Embedded commands cannot alter system policy or workflow behavior.

## 28. PII minimization applies to remote model and tool calls

**Status:** Accepted for Activity 2F

Remote calls receive only the minimum information required for the task. Secrets, unnecessary contact data, and raw resumes are excluded from remote calls and logs.

## 29. Observability remains provider-independent

**Status:** Accepted for Activity 2F

Tracing records workflow, model, tool, human, provenance, and confidence metadata through an abstraction that does not require a specific platform.

## 30. Chain-of-thought is never persisted

**Status:** Accepted for Activity 2F

The system retains structured outputs, explanations intended for users or systems, metadata, and evidence references, never private model reasoning or chain-of-thought.

## 31. Step 2 architecture is frozen for MVP implementation

**Status:** Accepted for Activity 2G

The Step 2 architecture is frozen for MVP implementation. Minor implementation details may evolve; major boundary, authority, provider, MCP, security, or workflow changes require an ADR and explicit review.

## 32. V1 profile acquisition uses structured manual onboarding

**Status:** Accepted for Activity 4B

V1 captures candidate facts through a guided six-stage onboarding workflow and maps only
explicit user-entered skills and capabilities into confirmed evidence. DOCX import is deferred
as a possible convenience input to the same profile structure. Resume upload, PDF/DOCX parsing,
OCR, and document-extraction prompts are outside the current V1 scope. This changes the active
implementation scope without replacing the frozen long-term architecture boundaries.

## 33. Target requirements follow the selected goal interaction

**Status:** Accepted for Activity 4D

`TARGET_CAREER_PATH` requires a target in the durable `CareerGoal` model. The current
`ROLE_TRANSITION` interaction also requires a named role, but that rule remains in the V1 intent
policy so a future open-transition interaction is not blocked by the durable model. Current-market
analysis, career exploration, leadership progression, and reassessment may omit a target. This is
a validation correction and adds no durable fields or entities.

## 34. V1 current-market interpretation uses separate explainable signals

**Status:** Accepted for Activity 5A

The active V1 `CurrentMarketSnapshot` reports Opportunity Availability, Employer Diversity,
Market Concentration, and Evidence Confidence independently. It retains the validated posting,
normalized employer, top-employer, search, retrieval, and duplicate counts used by the transparent
heuristics. `MarketBreadth` remains only as a compatibility enum and is not silently repurposed as
availability. Role specificity, historical persistence, trend, seasonality, and the higher-order
Market Verdict remain deferred to V2.

## 35. V1 market requirements use posting candidates, not source pages

**Status:** Accepted for Activity 5B

A retrieved source page may contain one posting, multiple postings, or mixed non-job content.
Activity 5B therefore classifies each retained source and creates source-grounded posting
candidates before title, geography, or requirement analysis. Obvious structures are segmented
deterministically; irregular aggregator content may use the extraction model through
`ModelGateway`, but every model-created candidate must match exact source text. Requirement
extraction receives one bounded posting candidate per call. Frequencies use successfully analyzed
posting candidates as their denominator and retain exact-title and related-title counts separately.
Page-level claims such as "31 jobs" never become validated market counts.

## 36. Activity 5C uses in-memory workflow checkpoints and transient raw-content handoff

**Status:** Accepted for Activity 5C

The initial executable graph uses LangGraph's official `InMemorySaver` for workflow pause/resume
and test checkpointing. It is not authoritative business persistence. Runtime services are supplied
through LangGraph context and never enter state. Because market processing needs retrieved page
content while checkpoints must remain small, an injected process-local content buffer holds bounded
source content by run ID and the state retains only source IDs and validated summaries. Durable
checkpoint storage, raw-content retention, and SQLite business repositories remain future work.

## 37. Activity 6A comparisons retain posting and title-scope provenance

**Status:** Accepted for Activity 6A

The existing `RequirementComparison` is narrowed for executable use by adding the originating
posting ID and an `EXACT_TARGET` or `COMBINED_RELATED` scope. Its match type may be absent only for
an explicitly `INSUFFICIENT` comparison after semantic evaluation fails; the system does not
fabricate a match merely to fill a result table. Detailed 5B analysis is handed to the comparison
node through the injected process-local run store, while checkpoint state retains the resulting
typed comparisons and limitations. This does not create business persistence or an overall score.

## 38. Activity 6B uses deterministic, provenance-preserving gap policy

**Status:** Accepted for Activity 6B

V1 maps normalized requirement frequency into explicit bands using centralized thresholds:
`COMMON >= 0.60`, `FREQUENT >= 0.35`, `OCCASIONAL >= 0.15`, and `RARE` below that; unavailable
frequency is `INSUFFICIENT_EVIDENCE`. These bands affect gap priority but never change comparison
match type. Duplicate posting differences produce one gap that retains every contributing
requirement ID. Exact-target evidence is primary and related-only severity is capped below `HIGH`.
Accessibility uses explainable rule inputs and remains independent of Opportunity Availability.
No model call or percentage score is used for gap/accessibility classification.

## 39. Activity 6C bridge titles must be observed and gap-reducing

**Status:** Accepted for Activity 6C

V1 bridge candidates come only from related titles already present in the current-market snapshot
and retained posting analysis. A candidate is rejected unless its observed requirements reduce at
least one material target gap. Ranking uses ordered, explainable dimensions—gap reduction,
confirmed-strength overlap, observed posting support, and title—without a displayed score. The
policy requires no new provider call or market search. Timeline assessment uses broad qualitative
rules and permits a missing requested timeline only with
`UNSUPPORTED_INSUFFICIENT_EVIDENCE`. Detailed milestones and CareerPlan remain inactive.

## 40. Activity 7A uses a deterministic plan skeleton with optional validated wording

**Status:** Accepted for Activity 7A

Path selection, phase allocation, IDs, milestone traceability, timing, evidence artifacts, risks,
assumptions, confidence, and draft status are deterministic business rules. Optional
`ModelRole.REASONING` assistance receives only the bounded deterministic draft and may refine
wording without changing its target, bridge roles, milestone structure, gap IDs, dependencies,
credentials, risks, or assumptions. Invalid output or provider failure retains the deterministic
plan and records a limitation. The active graph does not require this optional call. Final approval,
persistence, revision history, and market reassessment remain outside Activity 7A.

## 41. Activity 7B approval is exact-version and checkpoint scoped

**Status:** Accepted for Activity 7B

Final review is a true LangGraph interrupt and resumes only through the controller with a bounded
action matching the checkpointed plan ID and version. Approval creates a new approved model copy;
the reviewed draft object is not edited in place. Human actions are recorded with safe metadata in
workflow state, and duplicate identical terminal submissions return the existing final result.
Revision actions use one dependency-aware invalidation policy and stop in explicit handoff states
without automatically calling market or model providers. These semantics do not constitute
business persistence, approval history, or versioned plan storage.

## 42. Activity 8 geographic discovery is explicit and permission bounded

**Status:** Accepted for Activity 8 live QA

V1 records `STRICT_CITY`, `METRO_AREA`, `PROVINCE`, `COUNTRY`, and `COUNTRY_REMOTE` as distinct
search scopes. A goal defaults to strict city; wider scopes must be selected explicitly, and
an explicit Canada location defaults naturally to `COUNTRY`. Country-wide remote additionally
requires Remote as an accepted work mode. Toronto search phrases
are deterministic and bounded. Retained postings preserve the requested query scope, the scope
matched from posting-level evidence, the grounded location, and its evidence text. A generic
`COUNTRY` accepts explicit Canadian cities, provinces, or Canada itself, while a generic "Remote"
label is not sufficient evidence of Canadian eligibility, and rejected or unclear
geography is never relaxed to meet the live-QA posting gate.

## 43. Activity 8 target-title variants are lexical and separately counted

**Status:** Accepted for Activity 8 live QA

The discovery sequence is exact title, deterministic target-title variants, then permission-gated
related roles. The V1 variant policy is deliberately small: Solution/Solutions, configured AI/ML,
and Generative AI/GenAI forms with punctuation normalization. Variants are never counted as exact
titles, and related roles remain separate. Variant discovery uses bounded You.com searches with
direct employer/ATS-oriented query terms; no ATS is scraped directly and no model invents titles.
Requirement aggregation retains exact-only and exact-plus-variant frequencies independently.

## 44. The final portal handoff uses native Streamlit plus Plotly

**Status:** Accepted for the final V1 visual implementation

The supplied Streamlit-ready handoff supersedes the earlier custom dark evidence rail. The active
portal uses a light native sidebar with `st.radio`, native containers and status components, and
Plotly for quantitative graphics. No global custom stylesheet is injected by the application;
the live-progress component may include its own scoped motion and state styling. Synthetic
demo scores and route alternatives remain explicitly labelled and isolated in demo presentation;
live pages render only workflow-produced facts and retain honest insufficient-evidence states.

## 45. Live portal requirement analysis is bounded to five postings

**Status:** Accepted for Activity 8 live reliability

Market retrieval may retain a wider validated snapshot, but one interactive workflow run sends at
most five postings through requirement extraction. This preserves the 3-posting gate while
bounding latency, retries, and provider calls. `PostingRequirementResult` remains strictly
validated; prompt wording explicitly assigns CAPABILITY, PREREQUISITE_CONDITION, and
METADATA_NON_REQUIREMENT to `item_type`, while `category` uses the separate requirement taxonomy.
Logs may record sanitized schema field/error types but never full posting descriptions, rejected
model output, secrets, or reasoning traces.

## 46. Live analysis uses a dedicated stage-mapped transition

**Status:** Accepted for the production portal

The live workflow is launched only after Streamlit reruns into a dedicated progress view. The UI
maps graph completions to seven stable product stages and derives bar advancement from completed
stages, so it does not display raw node names or fabricated percentages. Active-run session flags
disable sidebar navigation and prevent duplicate starts. Successful display-ready results navigate
automatically to Market; a run without a usable snapshot returns safe Retry and Back to goal
actions. The motion treatment is component-scoped, restrained, and disabled when the browser
requests reduced motion.

## 47. Profile strengths are inferred after evidence capture and confirmed once

**Status:** Accepted for the production portal

The live profile sequence collects experience, portfolio projects, education, and certifications
before automatically invoking grounded capability inference. One native multi-select chip control
combines conservatively deduplicated literal evidence, prior explicit strengths, AI inferences, and
user-entered exceptions. AI inferences are active by default. The single confirmation maps retained
inferences to `CONFIRMED_INFERENCE`, removed inferences to `REJECTED_INFERENCE`, and new manual items
to `EXPLICIT`; rejected records retain their original supporting provenance but are not eligible for
downstream analysis. Technical punctuation is presentation data and is not tokenized or rewritten.

Profile dates use a rolling current-year-minus-60 history boundary. Employment cannot start or end
in the future and must retain start/end ordering; a current role has no end date. Education may use
a future completion year only when explicitly marked expected, certification issue years cannot be
future years, and certification expiration cannot precede issue.

## 48. Market, analysis, and plan use presentation view models and strict approval gating

**Status:** Accepted for the production portal

Validated domain and LangGraph objects remain the source of truth, but production pages no longer
decode those objects into long prose inline. Presentation-only view models translate enum labels,
prepare chart/table datasets, state sample denominators, and synthesize safe limitations without
changing business classifications. Market answers what was observed, Analysis answers how confirmed
candidate evidence compares, and Plan shows only evidence-supported route choices and milestones.

Plan approval is rendered only for a draft plan with a target, current-role starting point,
supported timeline, candidate assessment, non-insufficient confidence, credible path type, and
evidence-linked milestones. Missing inputs produce corrective actions instead of an approval-ready
roadmap. Multiple-path selection filters an existing engine-generated bridge branch; the UI never
invents additional routes or success probabilities. Raw compensation/benefit fragments and
requirement-processing diagnostics are not eligible as plan risks or limitations.

## 49. Analysis uses reconciled comparisons and guarded product transfer

**Status:** Accepted for the production Analysis page

All Analysis summary counts derive from the same usable `RequirementComparison` collection:
direct, transferable, partial, and no-confirmed match remain mutually exclusive and reconcile to
the displayed total. Partial matches are not described as covered, and the page does not compute a
fit percentage. Material gaps include moderate, high, and blocking severities; presentation may
group them into career-level themes only when every underlying `GapItem` identifier is retained.

Readiness is qualitative and derived from the categorized comparison outcomes rather than a
synthetic radar score. A semantic transferable result for product vision, strategy, roadmap,
lifecycle, KPI, or adoption ownership is downgraded to partial unless supporting evidence explicitly
demonstrates that ownership. Process discovery may still transfer to product discovery because the
workflow and outcome are adjacent, but discovery alone never proves product-direction ownership.

## 50. An approved no-fixed-timeline goal produces an untimed, approval-eligible plan

**Status:** Accepted for the production Plan page

`NO_FIXED_TIMELINE` is a first-class timeline classification, distinct from
`UNSUPPORTED_INSUFFICIENT_EVIDENCE`. It is valid only when the goal itself is approved; the same
missing numeric duration on a draft goal remains incomplete. Untimed plans preserve real milestone
dependencies but present them as `NOW`, `NEXT`, optional `BRIDGE` or `BUILD EVIDENCE`, and `TARGET`.
They never display zero-month ranges or infer a duration.

Plan approval remains blocked when candidate evidence or market comparison is genuinely
insufficient, no credible path exists, or critical upstream artifacts are missing. Current role is
resolved from the explicit About field first, then from the most recent active employment entry.
The UI renders only paths and bridge roles produced by the engine, uses qualitative effort/risk,
and creates action cards only from material `GapItem` records with retained identifiers and stated
evidence needs. Missing gaps are not invented merely to fill the requested three-to-five range.

## 51. Market dimensions are presentation classifications over validated evidence

**Status:** Accepted for the production Market page

Opportunity availability continues to use the existing market policy. Employer diversity combines
the existing `EmployerDiversity` and `MarketConcentration` outcomes into broadly distributed,
moderately concentrated, concentrated, or limited-evidence language. Title consistency is derived
only from exact-target, target-variant, and related-title counts: at least 70% exact is high
consistency; at least 50% exact-plus-variant is moderate variation; otherwise it is low consistency.
This is a presentation metric, not a new market ontology.

`CurrentMarketSnapshot.location_posting_counts` retains normalized, posting-grounded location
strings and counts. The UI groups them into recognizable Canadian provinces/regions, remote, or
Canada-wide categories without hard-coding a preferred city. Requirement themes are deterministic
labels over the names actually present in `MarketRequirementSummary`; the UI cannot add a theme
capability that extraction did not support. Every frequency states `N of M` and the analyzed sample
denominator. Raw provider validation diagnostics and metadata debris are replaced with concise,
user-relevant limitations.

## 52. Career-level synthesis is semantic-only and preserves raw analysis provenance

**Status:** Accepted for the production Analysis and Plan workflow

The workflow inserts a generic `CareerAssessmentSynthesis` after deterministic requirement
comparison and raw gap construction, before bridge-role, timeline, and plan decisions. The model
may group related findings and write concise explanations, but it cannot set severity, market
frequency, accessibility, confidence, counts, timelines, bridge roles, certifications, or source
identifiers. Those values are computed or validated deterministically.

Every grouped gap must cover existing material `GapItem` identifiers exactly once. Every advantage
and transferable strength must cite eligible comparisons and approved evidence already present in
the bounded input. Unknown or contradictory model output fails closed to deterministic grouping.
Analysis renders the validated synthesis; downstream planning may use its grouped priority and
accessibility rationale, while milestones continue to reference raw gap identifiers. No target-role
special cases are permitted, and optional plan model refinement remains disabled.

## 53. Accessibility uses weighted primary evidence and independent severe dimensions

**Status:** Accepted for calibrated career synthesis

Target-role accessibility uses exact-target and target-variant comparisons as its primary evidence.
Related-title comparisons remain available for interpretation and bridge analysis but cannot inflate
target readiness. Internal evidence weights are `DIRECT_MATCH = 1.0`,
`TRANSFERABLE_MATCH = 0.70`, `PARTIAL_MATCH = 0.35`, and `NO_CONFIRMED_MATCH = 0.0`.
The weighted value is one policy input only and is never presented as a candidate fit score.

Material gaps are classified into structured, role-neutral dimensions from requirement category,
gap type, maturity difference, match type, and bounded requirement semantics. Generic gap prose is
not a primary classification input. Accessibility considers independent high/blocking dimensions,
not a raw high-gap threshold: two or more independent severe dimensions are aspirational; one severe
dimension is near-term when weighted primary support is at least 0.50 and aspirational otherwise.
A 75% unmatched primary share with a high gap is poor fit, and any hard/blocking prerequisite remains
poor fit. Moderate-only gaps can support selective application when weighted support is at least
0.65 and direct share at least 0.40. Apply-now requires no material gap, at least 0.60 direct share,
at least 0.75 weighted support, and no unmatched primary requirement.

At least half insufficient primary comparisons yield insufficient candidate evidence. Low role or
primary-comparison confidence caps a result at near-term; moderate confidence caps it at apply
selectively. Grouped gaps retain raw identifiers plus underlying count, high/blocking count,
mandatory/preferred composition, and affected dimensions. These controls are deterministic and
remain independent of model wording or grouping.

## 54. Analysis presents Career Assessment Synthesis as its sole career interpretation

**Status:** Accepted for the production Analysis page

The Analysis view model requires `CareerAssessmentSynthesis` and does not derive a parallel career
story from raw requirement comparisons or gaps. Synthesis supplies accessibility, confidence,
advantages, transfer mappings, grouped gaps, summaries, rationales, structured dimensions, and the
canonical match counts. Raw comparisons, gaps, and evidence remain available only for bounded
supporting excerpts, provenance, reconciliation, and administrative debugging.

The page shows a count-based match-mix visual rather than a fit score. Grouped gap cards disclose
their underlying and severe requirement burden, mandatory/preferred composition, and affected
dimensions without displaying identifiers. If synthesis is absent, Analysis fails closed with a
preserved-evidence message instead of reconstructing an interpretation from lower-level objects.

## 55. Plan actions consolidate synthesized career gaps while preserving raw provenance

**Status:** Accepted for the production Plan page

Plan uses synthesis for accessibility, strengths, grouped career gaps, rationale, and the transition
story. Each displayed action corresponds to one prioritized grouped gap and retains every valid raw
`GapItem` identifier represented by that group. Milestone artifacts remain the evidence proof when
available. Bridge titles and route structure continue to come only from deterministic bridge and
path assessments; plan model refinement remains disabled.

An untimed approved goal is a valid planning mode and renders ordinal `NOW`, `NEXT`,
`BUILD / BRIDGE`, and `TARGET` stages without month estimates. Plan approval requires a credible
path, sufficient synthesis confidence, no unresolved blocking prerequisite, and valid milestone gap
provenance. Current role resolution uses the explicit profile role, then the most recent active
employment entry, then the most recent completed employment entry.

Observed related titles above the target role's conservative seniority band are not eligible bridge
roles. This is a generic title-order safeguard: it prevents a director, vice-president, or other
higher-seniority role from being presented as an intermediate step toward a lower target. When an
aspirational assessment has no valid bridge, the UI presents the deterministic evidence-closure
plan as a longer development route rather than calling it a direct selective transition.

## 56. Market separates exact-target evidence from expanded market evidence

**Status:** Accepted for the production Market page

Market remains independent of candidate synthesis and readiness. It displays exact-target,
target-variant, related-title, and expanded totals separately. Availability wording explicitly says
when the signal uses the expanded target and related-title scope, and related-title evidence is
described as secondary context for downstream candidate analysis.

Requirement themes use extracted requirement categories rather than target-role-specific labels.
Every requirement observation retains the successfully analyzed posting denominator. Geographic
and employer conclusions use validated snapshot counts, and the market handoff contains no
candidate strengths, gaps, accessibility, or provider diagnostics.

## 57. Demonstrated strength is independent of complete target satisfaction

**Status:** Accepted for career synthesis and the production Analysis page

Approved candidate evidence may represent a meaningful demonstrated capability when its target
comparison is direct, transferable, or partial. A partial comparison therefore contributes both a
demonstrated-strength record and an explicit remaining difference; it does not increase the match
weight or accessibility classification. No-confirmed-match comparisons cannot create strengths.

Analysis presents demonstrated strengths, target alignments, and remaining gaps as separate layers.
Grouped gaps retain deterministic internal dimensions and raw gap IDs, while their primary display
titles and disclosed underlying requirement names come from validated requirement semantics. Broad
dimension labels are secondary metadata rather than the main career-gap name.

## 58. Candidate comparison uses a canonical target-role profile

**Status:** Accepted

Posting extraction remains source-specific and auditable, but candidate comparison no longer runs
once per extracted sentence. A deterministic consolidation layer groups supported equivalents,
counts each known employer once, and separates exact/variant evidence from related-title context.
Exact and target-variant evidence determine `CORE`, `SECONDARY`, and `PREREQUISITE` comparison
requirements; one-off signals and related-only context remain available for audit.

The profile is `STABLE` only with at least five analyzed primary postings, three independent primary
employer identities, and repeated-employer agreement on at least half of comparison requirements.
Two or more primary postings may form a `PROVISIONAL` profile at reduced confidence; fewer than two
or no usable comparison requirements is `INSUFFICIENT`. Core support requires two independent
primary identities and a 0.50 support ratio; secondary support requires 0.30 or a majority mandatory
signal. Known employer identities form the denominator, with posting identity as the fallback.

Every canonical requirement retains source requirement, posting, employer, quote, and title-scope
provenance. `RequirementComparison` and `GapItem` preserve the canonical ID plus all raw source
requirement IDs. Bounded audits are checkpointed while full posting bodies remain transient.
Semantic alignment rejects clearly unrelated quote-to-capability mappings. Synthesis and
accessibility policy are unchanged.

## 59. Target-title expansion is observed, bounded, validated, and fail-closed

**Status:** Accepted for the final V1 structural pass

Controlled title expansion runs only when the initial canonical target-role profile is
`INSUFFICIENT`, the goal permits related-title expansion, and observed related titles exist. One
cycle considers at most five distinct observed titles and at most five additional postings. It
never recursively creates title families. Deterministic normalization, duplicate removal,
exact-title exclusion, and seniority checks run before one bounded `ModelRole.VALIDATION` request.

A title is promoted only when the model returns that exact observed title, cites at least one of
its supplied posting IDs, classifies it as `VALID_TARGET_VARIANT`, aligns seniority, rates function,
ownership, scope, and outcome overlap at 0.70 or higher, and the posting has accepted grounded
requirements. Missing, invalid, or ungrounded output leaves the title `RELATED_TITLE`. The model
cannot create titles, postings, requirements, or evidence. Every decision retains its posting IDs,
overlap findings, seniority, confidence, and reason.

The canonical profile is rebuilt once using exact targets plus validated variants as primary
evidence; ordinary related titles remain secondary context. Exact and variant employer and posting
support are tracked separately. Variant-heavy profiles cannot become `STABLE` and generally remain
low-confidence `PROVISIONAL`. Existing accessibility policy is unchanged. If the rebuilt profile
is still insufficient, the graph ends successfully at `MARKET_READY` with
`INSUFFICIENT_EVIDENCE`; it creates no candidate accessibility, gaps, synthesis, or career plan.
Market, Analysis, and Plan then show concise evidence-limited guidance rather than an error.

The live runtime maps a blank optional validation-model setting to the configured reasoning model
on the same provider. This is model-role routing, not a provider fallback, and prevents a blank
`VALIDATION_MODEL` from silently disabling semantic validation.

## 60. Adzuna and You.com ATS discovery are first-class market sources

**Status:** Accepted

Live target-role retrieval runs Adzuna structured discovery and You.com discovery concurrently.
The You.com lane issues one dynamically constructed ATS query over Greenhouse, Lever, Ashby, and
Workday, processes at most ten results independently, and permits one fallback search only when
fewer than three usable postings survive. Generic guides, job indexes, aggregators, and other
non-posting pages remain bounded audit context and cannot create canonical requirements, candidate
gaps, accessibility, or Plan actions.

Both lanes normalize into `MarketPostingEvidence`. Cross-source duplicates count as one posting and
one employer while preserving all provider provenance. Direct employer content outranks direct ATS
content, which outranks structured descriptions and aggregator snippets; qualification and
responsibility sections, identity clarity, and freshness break ties. Primary analysis selects at
most ten postings by exact-title scope, seniority alignment, employer diversity, content quality,
freshness, and provider diversity. One employer cannot dominate the sample.

Canonical requirements separately count employer, posting, Adzuna, You.com, exact, variant, and
related support. Cross-source agreement requires independent employer evidence across both
providers; duplicate provider observations of one employer never increase employer support.
Work arrangement, compensation, contract metadata, and marketing copy are excluded before
canonicalization. Role responsibilities remain role-context evidence but cannot become hiring
qualifications, candidate gaps, accessibility inputs, or Plan actions unless the posting separately
states the capability as a candidate requirement. Bounded retrieval and requirement audits are
checkpointed and persisted without full posting bodies or reasoning traces.

## 61. Posting meaning and source lineage remain explicit through canonicalization

**Status:** Accepted

Posting extraction classifies each grounded statement as `ROLE_RESPONSIBILITY`,
`HIRING_CAPABILITY`, `PREREQUISITE`, `PREFERENCE`, or `METADATA_NON_REQUIREMENT`. The canonical
target-role profile presents both what the role does and what candidates are expected to possess,
but only supported hiring capabilities and prerequisites enter comparison. Preferences remain
visible without defining baseline gaps. Every canonical item retains separate responsibility and
qualification posting counts, employer and posting support, provider identities, source locators,
source quotes, and raw requirement IDs.

Target-role relevance and seniority precede employer diversity, content quality, freshness, and
provider diversity when selecting up to ten postings. When target seniority is unspecified,
standard-level roles define the baseline and materially junior, senior, or staff roles remain
scope context. Internship exclusions derive only from the requested role and seniority: explicitly
junior, entry-level, new-graduate, or internship targets may retain early-career evidence.

A cross-source duplicate remains one posting and one employer signal with multiple provenance
records. Occupational guides and career articles remain `BACKGROUND_CONTEXT`; they cannot enter
requirement extraction, comparison, gaps, accessibility, or planning. These retrieval and
canonicalization rules do not change the generic comparison or accessibility policies.

## 62. V1 reliability uses primary-cohort meaning and separate validation evidence

**Status:** Implemented; live release acceptance remains open (September 7, 2026).

Canonical hiring expectations draw their maturity, years, mandatory status, source quotes and
confidence from the aligned exact/variant cohort. Related or materially different-seniority
postings retain provenance but cannot silently raise the baseline. Employer-weighted observed
qualifier combinations select a matching representative quote; the model must not receive a
ten-year outlier quote alongside a three-year canonical expectation. Source responsibilities
remain distinct from qualifications. Optional credentials are not universal blockers; OR
alternatives remain one expectation and cannot weaken an AND requirement.

Comparison retains semantic function, ownership, scope, maturity and production differences,
including unknown versus explicitly unmet evidence. Label-only overlap is not general proof of
direct fit. Employer-specific conditions cannot block a whole target by default. Synthesis
preserves demonstrated strengths and derives accessibility generically, without profession-specific
verdicts. A small provisional market sample lowers confidence, not candidate fit by itself.

Plan actions retain requirement/evidence/gap lineage and actual milestone meaning. An apply-ready
same-role candidate is not forced into training or a bridge. An unspecified deadline is valid;
no unsupported month estimate is added. UI counts and actions consume these validated objects.

Frozen provider/model recordings test execution and lineage across all six goal types. They do
not establish Nemotron's semantic accuracy. The original expected rubric and failures are retained
when an expectation is revised for an independently stated policy reason. Live runs and browser
checks are separate acceptance evidence. A bounded live safe stop is not a happy-path success.

## 63. Retrieval distinguishes discovery hits, excerpts and usable vacancy bodies

**Status:** Implementation improved; live full-description acceptance remains open (September 7, 2026).

Search source preference is not source validation, and length is not completeness. Adzuna search
excerpts stay explicitly incomplete. Contents metadata and one-job extraction retain identity and
section boundaries; stronger bodies win over host preference. Completion must not replace useful
requirements with a shell, silently accept unknown redirected geography, or inflate counts after
multiple redirects resolve one requisition. Original evidence and bounded observations remain auditable.

Later query passes may search a wider index window while posting currentness is validated separately.
The public query probe improved Toronto URL relevance but its three fetches did not yield usable
full bodies. This does not authorize treating expired/inaccessible pages as hiring evidence,
altering comparison/accessibility policy, or claiming a release-ready product.

## 64. Adzuna-seeded discovery retains uncertain identities separately

**Status:** Implemented with offline tests, September 9, 2026; live acceptance pending.

The user's retained-jobs instruction supersedes content-fingerprint merging. Only
an exact posting/canonical URL or shared employer requisition supports automatic
merging; conflicting requisitions remain separate. Same employer and similar body
can flag possible duplicates but cannot change counts by merging or attach one JD
to another source record. A returned different URL also needs identity evidence
before it can complete an existing posting. Original snippets and provenance remain.

Use structured employer/title/location as bounded You.com search seeds when direct
completion fails. Preserve the complete title, including role-defining suffixes;
no Java-specific rules or hand-coded employer-domain map. Request full-page Markdown
through advertised MCP capabilities, with Contents fallback on older schemas. Keep
independently validated alternative vacancies, each linked to the search seed, and
deduplicate only after checking identity. Existing parallel discovery remains.

Retain related-title discoveries without promoting them into the canonical baseline.
Recognized individual job-board copies may supply grounded descriptions but are not
labelled employer-verified vacancies; guides and result-list pages stay excluded.
Shared search/content budgets still apply. Pending or budget-deferred work is not
unavailable-description evidence. No automatic background retry system is introduced.
The safe-stop, requirement extraction, synthesis and accessibility policies remain
unchanged; record counts with possible duplicates are not verified vacancy totals.

## 65. Homepage demo is a reusable profile-input shortcut

**Status:** Implemented and browser-verified, September 9, 2026.

The user wants to avoid repeatedly entering test data, not preview canned results.
Explore demo therefore creates a fresh synthetic ProfileDraft and stops at Education
& Certifications, using the normal manual/live route thereafter. No goal, strengths
review, approval, retrieval, assessment or plan is seeded. The user chooses when to
continue into AI review and live analysis. Repeated use replaces temporary session
progress with fresh input records; homepage copy discloses that behavior. Synthetic
input labels remain visible. Standard blank onboarding and backend policies are unchanged.

## 66. One user-facing assessment, separate evidence and decision stages

**Status:** Implemented offline, September 9, 2026; live model-quality benchmark pending.

The user approved merging Market and Analysis around employer expectations and candidate
evidence rather than retrieval statistics. Internal workflow stages and canonical scope
rules remain separate; both legacy view keys map to one assessment renderer. Plan remains
a separate evidence-linked action and version-approval experience.

Cross-posting organization uses canonical expectations with exact source passages and
employer/posting provenance; candidate data enters only the comparison stage. This bounded
call is allowed to organize IDs into professional dimensions, not invent role requirements,
people-management demands, personality scores, accessibility, gaps or career advice. It
must preserve complete coverage and semantic-type/scope boundaries; failure leaves all
original expectations visible with an explicit fallback label. Existing accessibility and
plan rules are unchanged. This first implementation does not claim unconstrained role-family
narratives or per-vacancy candidate-fit recommendations.

Professional summary/core competencies are labelled context, not new verified evidence.
No market growth/decline, hiring probability or universal-role requirements may be inferred
from the bounded posting sample. Numbers remain available for audit, not the primary story.

## 67. Repair only empty optional extraction lists, not evidence

**Status:** Implemented and regression-tested, September 9, 2026.

The observed Nemotron nulls for `qualifier_quotes` and `capability_options` may be
normalized to empty lists at the ExtractedRequirement boundary. This narrowly
repairs absent optional annotations without changing the required array wire
schema or relaxing other fields. Non-null wrong types remain errors. ANY_OF still
requires at least two alternatives and downstream validation still requires
distinct, non-empty alternatives explicitly supported by an OR source statement.
Quotes, qualifiers, normalized capability grounding and provenance are unchanged.
Prompt v5 explicitly specifies array values. This is not a timeout fix and does
not establish live provider quality; the completed diagnostic remains failed.
# September 11, 2026 — transition V3 prompt replacement

User authorized implementing the independent role-neutral assessment approach and
cross-profession safeguards, then repeating the Java-to-AI case with DeepSeek.
Replace the transition author/reviewer prompts; do not append a second policy stack.
Use existing rationale for readiness now and role_picture for the credible direction.
Keep the existing accessibility enum with explicit developmental versus apply-now meaning.
Add supervised-practice and verified jurisdiction/task-authorization boundaries without
profession-specific laws, forced verdicts or fabricated credentials. Preserve schemas,
same-role behavior, retrieval, reference validation and exact-version plan approval.
Original proposal/self-review artifacts remain historical; live semantic quality must
be reported from the actual rerun, not inferred from prompt-contract test success.

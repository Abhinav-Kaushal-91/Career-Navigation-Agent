# Graph State

## 1. Purpose

LangGraph state answers: “What does this workflow currently know and where is it in the process?” It is temporary workflow context, not the authoritative business database. This document defines the conceptual `CareerNavigatorState`; it does not define TypedDict, Pydantic, dataclass, or LangGraph implementation schemas.

## 2. CareerNavigatorState Groups

### A. Run Identity

Conceptual fields: `run_id`, `thread_id`, `workflow_version`, `run_type`, `run_status`, `current_stage`, `current_substage`, `started_at`, `updated_at`, `completed_at`, and `degraded_mode`.

Run types: `INITIAL_ANALYSIS`, `CAREER_EXPLORATION`, `CURRENT_MARKET_ANALYSIS`, `TARGET_CAREER_PATH`, `LEADERSHIP_PROGRESSION`, and `CAREER_REASSESSMENT`.

Run statuses: `IN_PROGRESS`, `WAITING_FOR_USER`, `COMPLETED`, `COMPLETED_WITH_LIMITATIONS`, `SAVED_AS_DRAFT`, `USER_CANCELLED`, `INSUFFICIENT_EVIDENCE`, and `FAILED`.

### B. User Input State

Conceptual fields: input type, original request, resume reference, manual profile input, career-stage input, target role and seniority, target timeline, location, industry, work mode, bridge-role willingness, search-expansion permission, and exploration mode. Full resume bytes do not belong in graph state.

### C. Profile State

Conceptual fields: profile draft reference, confirmed profile ID, validation status and issues, confirmed evidence IDs, inferred capability items, rejected and unconfirmed inference IDs, evidence-maturity assignments, missing information, and profile approval status. Draft profile data may be temporary; the confirmed profile becomes authoritative only after approval.

### D. Goal State

Conceptual fields: career-goal draft, confirmed goal ID, goal type, clarification questions, and goal approval status. Goal types include `CAREER_EXPLORATION`, `CURRENT_MARKET_ANALYSIS`, `ROLE_TRANSITION`, `TARGET_CAREER_PATH`, `LEADERSHIP_PROGRESSION`, and `CAREER_REASSESSMENT`.

### E. Market Intelligence State

Conceptual fields: search-plan reference, exact/related/role-family query references, raw search-result references, validated posting IDs, blocked-source IDs, duplicate-group IDs, retrieved posting IDs, normalized-role and role-family IDs, current snapshot ID, historical signal ID, stringency result, consistency result, market verdict, evidence status, confidence, and limitations. Complete HTML and large job descriptions should be referenced, not copied into checkpoints.

### F. Career Analysis State

Conceptual fields: requirement-comparison IDs, transferable-skill assessment IDs, gap IDs, blocker IDs, candidate-accessibility results, role-assessment IDs, bridge-candidate IDs, recommended bridge ID, bridge outcome and confidence, timeline assessment ID and confidence, and analysis validation issues.

### G. Career Plan State

Conceptual fields: plan-draft reference, path type, roadmap-phase references, milestone IDs, evidence-building action IDs, leadership/scope action IDs, market-action IDs, reassessment-trigger IDs, risks, assumptions, plan-validation status, approval status, approved-plan ID, and draft-plan ID.

### H. Control and Recovery State

Conceptual fields: pending human action, last user action, clarification context, retry counts, last error category, error IDs, warnings, completed stages, invalidated stages, recompute-from-stage, fallback-used, and degraded-mode reasons. Detailed interrupt payloads are deferred.

## 3. State Design Rules

- State values must be serializable and provider-agnostic.
- State must contain no secrets, API keys, provider clients, database connections, active MCP sessions, or other credentials.
- Large documents belong in controlled external storage and are referenced by IDs, hashes, or content references.
- Raw resumes and full job pages must not be repeatedly copied into checkpoints.
- Model responses are reduced to validated structured results before retention.
- Temporary drafts are not authoritative.
- Confirmed records are referenced by authoritative IDs after persistence.
- Evidence and source references remain available for traceability.
- Timestamps include timezone information.
- Bounded classifications should later become enums.
- State changes must be attributable to a workflow stage.

## 4. State Lifecycle

- **Start:** Create run identity, thread identity, and initial input state.
- **Profile and Goal:** Add draft references, approvals, confirmed profile reference, and confirmed goal reference.
- **Market Intelligence:** Add query, posting, snapshot, historical-signal, and market-verdict references.
- **Career Analysis:** Add comparisons, gaps, accessibility, bridge, and timeline references.
- **Career Plan:** Add plan draft, milestones, risks, and assumptions.
- **Final Approval:** Add approval outcome, approved or draft reference, and final status.
- **End:** Retain authoritative business records, checkpoint history according to policy, and optional approved contextual memory if enabled.

## 5. Recompute and Invalidation Concepts

- Confirmed profile change invalidates comparisons, gaps, accessibility, bridge, timeline, and plan. Market search reruns only if location, target, seniority, industry, work mode, or search scope changed.
- Location change invalidates the current snapshot, geography-dependent history, verdict, accessibility where requirements change, bridge, timeline, and plan.
- Timeline-only change invalidates timeline assessment and plan.
- Bridge willingness change invalidates bridge, timeline, and plan.
- Market refresh invalidates verdict, changed requirement context, accessibility, bridge, timeline, and plan.

Downstream analysis must not remain marked valid when an affected upstream input is invalidated.

## 6. State-Size Controls

Avoid repeatedly storing resume files, PDF binaries, full web pages, large HTML, hundreds of job descriptions, or provider-native objects. Prefer IDs, hashes, source references, database IDs, validated summaries, and small normalized objects. This improves checkpoint performance, recovery, debugging, privacy, and storage size.

## 7. Validation Requirements

Future validation must check required stage inputs, valid status transitions, valid bounded classifications, referential integrity, approval before authoritative IDs appear, no unconfirmed inference in confirmed profile, no approved-plan ID without approval, no downstream validity after invalidation, no secrets, and serializable values.

## 8. Traceability Requirements

State should support answering what evidence produced a conclusion, which source supports it, which approved profile and goal versions were analyzed, which provider produced a structured interpretation, what was retried, which fallback was used, and what was invalidated after user changes. Store structured explanations and evidence references, not complete chain-of-thought or private model reasoning.

## 9. Open Questions

- Exact retention periods
- Encryption-at-rest approach
- Raw resume retention duration
- Whether raw web content needs a dedicated local content store
- Multi-user data isolation, outside the current MVP scope

## 10. Activity 5C Concrete State

Activity 5C implements `CareerGraphState` as a project-owned typed dictionary. Its active fields
cover run/thread identity, workflow version/stage/status, temporarily supplied confirmed profile
and goal, capability-inference and review status, bounded inferred evidence, market status and
snapshot, market source IDs, requirement summary, limitations, warnings, retry counts, a safe
error category, pending human action, completed stages, and degraded mode.

The state intentionally excludes provider clients, `ModelGateway`, MCP sessions, `Settings`,
loggers, database connections, Streamlit widgets, raw resumes, full job-page content, provider
responses, and chain-of-thought. `serialize_graph_state()` produces JSON-compatible UUID,
datetime, enum, and Pydantic values for controller/UI boundaries.

The initial implementation uses LangGraph `InMemorySaver`. It provides checkpoint/resume behavior
for tests and the process lifetime but is not durable business storage. Retrieved source content is
placed in an injected run-scoped `TransientMarketContentStore`; only source IDs and validated
summaries enter checkpoints. A durable checkpoint backend and raw-content retention policy remain
future decisions.

## 11. Activity 6A Comparison State

Activity 6A adds `requirement_comparisons`, `candidate_comparison_status`, and
`comparison_limitations`, then advances the graph to `CANDIDATE_COMPARISON_READY`.
Comparisons retain requirement ID, posting ID, exact/related scope, supporting approved evidence
IDs, maturity, match type, remaining difference, explanation, and comparison confidence. A match
type may be absent only when confidence is `INSUFFICIENT` and semantic comparison failed safely.

The detailed `MarketRequirementAnalysis` is retained in the injected process-local run store so
the graph node can consume posting-level requirements and title assessments without checkpointing
raw market pages or runtime provider objects. This remains a V1 in-memory workflow boundary, not
business persistence.

## 12. Activity 6B Assessment State

Activity 6B adds `role_assessment`, `gap_analysis_status`, `candidate_accessibility`, and
`gap_limitations`, then advances the workflow to `CANDIDATE_ASSESSMENT_READY`. The role assessment
contains the posting-grounded comparisons plus deduplicated gaps. Each gap retains a representative
requirement ID, all contributing requirement IDs, exact/related scope, market frequency band,
candidate evidence references, severity, blocker status, and confidence.

The graph stores no policy services or model objects. Gap and accessibility rules execute in the
injected career service and produce JSON-compatible domain records. No bridge, timeline, or plan
state is active in this slice.

## 13. Activity 6C Career-Path State

Activity 6C adds bounded `bridge_assessments`, `bridge_outcome`,
`bridge_analysis_status`, `bridge_would_help`, `timeline_assessment`,
`timeline_analysis_status`, and `career_path_limitations`. The workflow ends at
`CAREER_PATH_ASSESSMENT_READY`.

Bridge records reference observed role titles and canonical gap UUID strings. Timeline records
contain only the requested month constraint, qualitative classification, concise prerequisite
outcomes, dependencies, confidence, and limitations. No model/provider objects, invented market
titles, detailed roadmap, or `CareerPlan` enters state.

## 14. Activity 7A Career-Plan State

Activity 7A adds `career_plan`, `career_plan_status`, and `plan_limitations`, then advances the
workflow to `CAREER_PLAN_READY`. The plan is a JSON-compatible Pydantic record containing the
selected path type, supported bridge assessments, timeline assessment, bounded milestones, risks,
assumptions, source IDs, and confidence. Each gap-derived milestone retains actual gap UUIDs;
dependencies reference milestone UUID strings from the same draft.

The plan remains version 1 with both plan and approval status set to `DRAFT`. State contains no
approval record, repository, database connection, provider client, raw market content, or plan
history. Optional wording-fallback details are retained only as limitations.

## 15. Activity 7B Final-Review State

Activity 7B adds `plan_review_request`, `workflow_action_records`, and `completed_at`. The review
request contains only the exact `plan_id`, `plan_version`, and bounded `PlanReviewAction` supplied
at resume. Each checkpoint-scoped action record adds an action ID, workflow run ID, and aware
timestamp; it is not a durable `ApprovalRecord` or business repository record.

`FINAL_PLAN_REVIEW` is a true interrupt. Terminal actions advance to `FINALIZED`; revision actions
advance to one of `PROFILE_REVISION_READY`, `GOAL_REVISION_READY`,
`MARKET_REASSESSMENT_REQUESTED`, or `CAREER_ANALYSIS_REASSESSMENT_REQUESTED`. Profile revision
invalidates candidate-dependent analysis while retaining applicable market evidence. Goal and
market revision invalidate market and downstream state. Career-analysis reassessment retains the
market snapshot and requirement summary while invalidating comparison and downstream outputs.

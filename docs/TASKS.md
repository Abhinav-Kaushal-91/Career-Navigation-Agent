# Tasks

## Analysis synthesis presentation

- [x] Separate demonstrated candidate strength from target-requirement completeness
- [x] Retain approved partial-match evidence as a demonstrated strength
- [x] Exclude no-confirmed-match evidence and standalone employment titles from strengths
- [x] Render direct, transferable, and partial target alignments in user-facing language
- [x] Derive gap display titles from underlying requirements and disclose requirement names
- [x] Preserve the calibrated accessibility policy during the interpretation change
- [x] Require Career Assessment Synthesis for the production Analysis interpretation
- [x] Translate every accessibility enum into the approved user-facing label
- [x] Render canonical direct, transferable, partial, unmatched, and insufficient counts
- [x] Add a count-based match-mix visual without a readiness or fit percentage
- [x] Render synthesis advantages, transfer mappings, and grouped career gaps directly
- [x] Show grouped underlying, severe, mandatory/preferred, and dimensional burden
- [x] Replace reconstructed radar/readiness scores with qualitative synthesis dimensions
- [x] Fail closed when synthesis is unavailable
- [x] Add UI regressions proving raw comparisons cannot override the synthesis story
- [x] Run the bounded live AI Product Manager validation

## Plan synthesis presentation

- [x] Use synthesis for plan accessibility, strengths, grouped gaps, rationale, and story
- [x] Consolidate prioritized actions by grouped career gap while retaining raw gap IDs
- [x] Keep bridge titles and supported route choices deterministic
- [x] Render a synthesis-grounded recommended-path visual and strengths section
- [x] Treat no fixed timeline as a valid ordinal roadmap
- [x] Add the completed-employment current-role fallback
- [x] Gate approval on synthesis confidence, blockers, credible path, and gap provenance
- [x] Keep optional plan model refinement disabled
- [x] Reject observed bridge titles whose seniority exceeds the target role

## Market evidence alignment

- [x] Keep Market independent of candidate synthesis and readiness
- [x] Display exact-target, target-variant, related-title, and expanded counts explicitly
- [x] Scope availability wording to expanded evidence when related titles contribute
- [x] Derive title consistency from validated title classes
- [x] Group requirements by extracted, role-neutral categories
- [x] Display per-requirement analyzed-posting denominators
- [x] Report validated employer and geographic distribution plainly
- [x] Mark related-title evidence as secondary downstream context
- [x] Complete bounded Market → Analysis → Plan QA with parallel Adzuna and You.com evidence
- [x] Bound verbose grounded text in deterministic synthesis fallback

## Generic Career Assessment Synthesis

- [x] Preserve requirement comparisons and raw `GapItem` objects as source-of-truth records
- [x] Add schema-constrained career-level semantic synthesis
- [x] Validate all comparison, evidence, requirement, and gap identifiers
- [x] Compute severity, frequency, accessibility, confidence, and counts deterministically
- [x] Insert synthesis before bridge, timeline, and plan orchestration
- [x] Render synthesized advantages, transfers, grouped gaps, summary, and rationale in Analysis
- [x] Let Plan consume grouped-gap priority while retaining raw gap provenance
- [x] Keep optional plan model refinement disabled
- [x] Add five role-neutral regression scenarios and fail-closed model-output tests
- [x] Replace raw high-gap thresholds with independent severe-dimension policy
- [x] Weight direct, transferable, partial, and unmatched evidence differently
- [x] Separate exact-target, target-variant, and related-title comparison provenance
- [x] Add confidence ceilings and structured grouped-gap burden metadata
- [x] Strengthen maturity, scope, related-title, weighting, and rationale regressions

## Activity 8 Market Source Architecture Update

- [x] Remove legacy web-segmentation dependency from structured Adzuna evidence
- [x] Prioritize exact, target-variant, then related evidence for bounded extraction
- [x] Pass the five-posting combined live QA through requirement aggregation
- [x] Separate capability requirements, prerequisites, and rejected posting metadata
- [x] Add canonical aliases, per-posting extraction QA, and small-sample count presentation

- [x] Add Adzuna settings and primary structured provider adapter
- [x] Normalize raw Adzuna payloads immediately into project-owned schemas
- [x] Reuse title, geography, market-signal, and cross-source deduplication rules
- [x] Add thin-record-only You.com enrichment without primary-field overwrite
- [x] Add conflict limitations and controlled degraded discovery fallback
- [x] Run Adzuna and You.com discovery concurrently with separate source-confidence reporting
- [x] Add fake client, offline tests, and manual-only smoke/combined scripts
- [x] Run bounded live Adzuna retrieval after explicit QA approval
- [x] Run the combined bounded live validation after explicit QA approval
- [ ] Improve supporting-source match yield for thin 500-character Adzuna descriptions
- [x] Add one controlled structured-output retry and bounded transient timeout retry
- [x] Pass the NVIDIA reliability gate with at least 4 of 5 analyzed postings

## Activity Sequence

- [x] Activity 0: Repository setup and scaffolding
- [x] Activity 1: Final product definition and MVP requirements
- [x] Activity 2: Architecture, LangGraph state, MCP boundaries, data models, and provider boundaries
- [x] Activity 2A-1A: Define major system components and responsibilities
- [x] Activity 2A-1B: Validate architecture boundaries
- [x] Activity 2A-2: Architecture diagram and boundary validation
- [x] Activity 2A: Architecture documentation
- [x] Activity 2B: LangGraph workflow design
- [x] Activity 2B-1: LangGraph Parent Workflow
- [x] Activity 2B-2: Define Profile and Goal subgraph stages and decisions
- [x] Activity 2B-3: Define the Market Intelligence workflow
- [x] Activity 2B-3A: Define the Current Market Search workflow
- [x] Activity 2B-3B: Historical Market Evidence Workflow
- [x] Activity 2B-3C: Requirement Stringency and Market Verdict Workflow
- [x] Activity 2B-3C-1: Requirement Stringency Workflow
- [x] Activity 2B-3C-2: Market Verdict Workflow
- [x] Activity 2B-3C: Requirement Stringency and Market Verdict Workflow
- [x] Activity 2B-3: Market Intelligence workflow
- [x] Activity 2B-4: Career Analysis Workflow
- [x] Activity 2B-4A: Candidate-to-Role Comparison and Transferable Skills Workflow
- [x] Activity 2B-4B: Gap Classification and Candidate Accessibility
- [x] Activity 2B-4C: Bridge Role and Timeline Analysis
- [x] Activity 2B-4: Career Analysis Workflow
- [x] Activity 2B-5: Career Plan and Final Approval Workflow
- [x] Activity 2B-5A: Career Plan Assembly and Roadmap Logic
- [x] Activity 2B-5B: Final Plan Approval and Workflow Completion
- [x] Activity 2B-5: Career Plan and Final Approval Workflow
- [x] Activity 2B: LangGraph workflow design
- [x] Activity 2C: Graph State and Data Ownership
- [x] Activity 2D: Complete Conceptual Domain Data Model
- [x] Activity 2E: MCP and Model Provider Boundaries
- [x] Activity 2F: Reliability, Security, Confidence, and Observability
- [x] Activity 2G: Full Architecture Consolidation Review
- [x] V1 implementation-scope checkpoint
- [x] Activity 3: Configuration, schemas, and synthetic product shell
  - [x] Activity 3A: Python Environment, Foundational Dependencies, Configuration, and Production UI Foundation
    - [x] Production UI configuration, package boundary, and design-system foundation
  - [x] Activity 3B: Domain Enums and Pydantic Schemas
  - [x] Activity 3C: Production Streamlit UI Shell with Synthetic Data
    - [x] Bidirectional workflow navigation and non-destructive Home action
- [x] Activity 4A: Provider-Independent Model Gateway Foundation
  - [x] Logical extraction, reasoning, and validation model roles
  - [x] Provider-neutral requests, responses, errors, and adapter protocol
  - [x] Bounded retry and strict Pydantic structured-output validation
  - [x] Deterministic fake provider and Fireworks HTTP adapter foundation
  - [x] Safe model-call metadata logging and manual-only smoke command
- [x] Activity 4B: Structured Candidate Profile Onboarding
  - [x] Six-stage guided manual onboarding
  - [x] Student and nontraditional-candidate support
  - [x] Deterministic explicit-evidence mapping
  - [x] Profile review, editing, and session-only confirmation
- [x] Activity 4C: AI Capability and Transferable Evidence Inference
  - [x] PII-minimized prompt context using approved explicit evidence only
  - [x] Structured inference output and two-layer evidence-ID validation
  - [x] Conservative duplicate filtering and pending evidence mapping
  - [x] Per-capability confirm, reject, and leave-unconfirmed review
  - [x] Graceful empty, low-evidence, malformed-output, and provider-failure behavior
  - [x] Manual-only configured-provider smoke command
- [x] Activity 4D: Career Goal Capture and Confirmation
  - [x] Six intent-specific goal paths
  - [x] Structured, JSON-compatible goal draft
  - [x] Conditional target, timeline, and path preferences
  - [x] Conservative work-mode, industry, and exclusion normalization
  - [x] Goal review, editing, and timezone-aware confirmation
  - [x] Manual and synthetic-demo state separation
- [x] Activity 5A: You.com MCP web discovery foundation (now secondary under Activity 8)
  - [x] Official MCP SDK and authenticated Streamable HTTP adapter
  - [x] `you-search` and `you-contents` allowlist enforcement
  - [x] Deterministic exact-title search planning and no-target discovery state
  - [x] Conservative current-job validation, content retrieval, and normalization
  - [x] URL and posting deduplication with bounded work
  - [x] Permission-gated related-title expansion
  - [x] Deterministic target-title variant discovery with separate counts
  - [x] Explainable Opportunity Availability, Employer Diversity, Market Concentration, and Evidence Confidence signals
  - [x] Partial-failure handling, safe metadata logging, deterministic fake client, and manual-only smoke command
- [x] Activity 5B: Current Market Evidence Processing and Requirement Extraction
  - [x] Direct, aggregator, mixed, and insufficient source-content classification
  - [x] Posting-specific segmentation with source references and bounded text
  - [x] Conservative in-scope, out-of-scope, and unclear geography validation
  - [x] Permission-bounded city, metro, province, country, and Canada-remote discovery scopes
  - [x] Exact-target, related-title, and irrelevant-title separation
  - [x] One-posting-at-a-time grounded requirement extraction through `ModelGateway`
  - [x] Exact-title and combined requirement frequencies using analyzed-posting denominators
  - [x] Aggregator-count, mixed-content, prompt-injection, and hallucination fixtures
- [x] Activity 5C: LangGraph Core Orchestration Foundation
  - [x] Typed JSON-compatible workflow state and runtime dependency context
  - [x] Profile, inference, goal, market retrieval, processing, and market-ready nodes
  - [x] Dynamic capability-inference review interrupt and checkpoint resume
  - [x] Profile-input, goal-input, role-discovery, degraded, and safe-failure routes
  - [x] In-memory workflow checkpointing and run-scoped raw-content references
  - [x] Thin start, resume, and inspect controller
  - [x] Fake end-to-end graph through `MARKET_READY`
- [x] Activity 6A: Candidate-to-Market Requirement Comparison
  - [x] Approved explicit and confirmed-inference evidence filtering
  - [x] Deterministic capability, maturity, years, and prerequisite comparison
  - [x] Bounded semantic transferability through `ModelRole.REASONING`
  - [x] Exact-target and related-title comparison provenance
  - [x] Safe partial and insufficient outcomes without an overall score
  - [x] LangGraph extension through `CANDIDATE_COMPARISON_READY`
- [x] Activity 6B: Gap Analysis and Candidate Accessibility
  - [x] Five-category deterministic gap classification
  - [x] Normalized multi-posting gap deduplication with provenance
  - [x] Explicit requirement-frequency and severity policy
  - [x] Rare, non-substitutable hard-blocker detection
  - [x] Six-outcome qualitative candidate-accessibility policy
  - [x] RoleAssessment assembly without a percentage score
  - [x] LangGraph extension through `CANDIDATE_ASSESSMENT_READY`
- [x] Activity 6C: Bridge Role and Timeline Assessment
  - [x] No-bridge, recommended, multiple, no-valid, and insufficient outcomes
  - [x] Observed-title-only candidate generation and bounded ranking
  - [x] Specific material-gap reduction and user-willingness handling
  - [x] Evidence-building, leadership/scope, and retained-market support
  - [x] Four-outcome qualitative timeline policy without fake precision
  - [x] Missing-timeline and hard-prerequisite safeguards
  - [x] LangGraph extension through `CAREER_PATH_ASSESSMENT_READY`
- [x] Activity 7A: Career Plan Generation
  - [x] Deterministic path-type mapping and path-aware phase structure
  - [x] Gap-linked measurable milestones and evidence artifacts
  - [x] Bounded direct, bridge, multiple-path, exploration, and no-credible-path plans
  - [x] Timeline-bounded month ranges and reassessment checkpoints
  - [x] Grounded risks, explicit assumptions, and conservative plan confidence
  - [x] Optional validated model wording with deterministic fallback
  - [x] LangGraph extension through `CAREER_PLAN_READY`
- [x] Activity 7B: Final Plan Review and Human Approval
  - [x] Exact plan ID/version final-review interrupt and typed actions
  - [x] Checkpoint-scoped action record and idempotent controller resume
  - [x] Approve, draft, reject, cancel, and limitation-aware final statuses
  - [x] Profile, goal, market, and career-analysis revision routes
  - [x] Central dependency-aware invalidation policy
  - [x] Hierarchical Plan review controls and non-persistent user copy
- [ ] Activity 4: SQLite storage foundation
- [ ] Activity 5: Career profile intake and confirmation flow
- [ ] Activity 6: Market evidence and source retrieval
- [ ] Activity 7: Career analysis and role classification
- [ ] Activity 8: Gap analysis and timeline feasibility
- [ ] Activity 9: Roadmap generation and explanation
- [x] Final V1 visual pass: evidence rail, compact context bar, warm-neutral design tokens, and responsive shell
- [x] Visual-first market and analysis summaries using validated workflow values
- [x] Dark-rail stage-state correction and limited-evidence Analysis navigation
- [x] Implement the supplied native Streamlit handoff with a light radio-navigation sidebar
- [x] Replace injected-CSS charts with Plotly requirement, concentration, title-mix, and coverage charts
- [x] Add the labelled demo readiness radar and selectable three-path roadmap preview
- [x] Equalize goal-direction cards using native fixed-height containers
- [x] Create and execute a 12-case deterministic backend QA matrix covering all six goal directions
- [x] Export sample profiles, goal inputs, backend answers, and browser-run placeholders to Excel
- [ ] Traverse all 12 cases through the Streamlit portal and record website outcomes in the workbook
- [x] Create a 100-question golden evaluation dataset with expected answers and grading constraints
- [x] Implement the deterministic-first golden evaluation loop and timestamped run artifacts
- [x] Run the 100-case reference self-check at a 100% harness threshold
- [x] Verify the live named career-transition path through `CAREER_PLAN_READY`
- [x] Bound portal requirement extraction to five postings and disambiguate extraction fields
- [x] Separate market transport failures from NVIDIA extraction failures in portal diagnostics
- [x] Replace the inline live-analysis loader with a real stage-mapped transition screen
- [x] Disable workflow navigation and duplicate starts while live analysis is active
- [x] Add safe retry/back recovery when the transition stops before a market result
- [x] Replace the manual-first Skills step with one evidence-first automatic Strengths review
- [x] Preserve confirmed/rejected inference provenance through the single strengths confirmation
- [x] Preserve technical punctuation and apply conservative cross-source strength deduplication
- [x] Replace the 2015-era date floor with a rolling 60-year range and explicit future-date rules
- [x] Redesign live Market around real metrics, tabs, semantic charts, and concise takeaways
- [x] Redesign live Analysis around reconciled match counts, evidence-backed strengths,
  qualitative readiness, transfer translation, and grouped career-level gap cards
- [x] Add a product-ownership transfer guard and live-regress AI Product Manager in Canada
- [x] Gate Plan approval and roadmap rendering on credible evidence and required inputs
- [x] Add presentation view models and sanitize user-facing market/plan limitations
- [x] Treat an approved no-fixed-timeline goal as a valid untimed Plan without invented months
- [x] Resolve the Plan starting role from About first and the most recent active experience second
- [x] Replace fabricated route alternatives with actual engine paths and grounded 3–5 action cards
- [x] Visually verify the refreshed Plan page against the supplied desktop design
- [x] Fix the Market reported-count parser when a You.com result produces an empty numeric capture
- [x] Add five evidence-backed Market dimensions and transparent title-consistency presentation
- [x] Retain validated location counts and render a real ranked Canadian geography distribution
- [x] Group only extracted requirements into employer-readable themes with visible denominators
- [x] Add compact Market takeaways, Analysis handoff copy, and sanitized expandable diagnostics
- [x] Live-regress AI Product Manager in Canada and manually QA Market, Analysis, and Plan
- [x] Keep Professional Summary exclusively on About You and combine Core Competencies with
  Professional Experience on the Professional Profile page
- [x] Pass Professional Summary and Core Competencies into AI Strength Identification and add a
  production one-occurrence onboarding regression
- [x] Build a canonical target-role profile between extraction and candidate comparison
- [x] Compare once per canonical requirement with end-to-end raw requirement provenance
- [x] Retain bounded posting requirement audits and sparse-profile confidence guardrails
- [x] Add one bounded, observed-title target-variant validation cycle with full decision provenance
- [x] Track exact and variant employer/posting support separately in the canonical role profile
- [x] Stop gracefully at Market without accessibility, gaps, or Plan when target evidence remains
  insufficient
- [x] Live-regress AI Product Manager in Canada through controlled title expansion
- [x] Scope Market requirement frequency to analyzed exact/validated-variant postings and show
  analyzed coverage with a directional small-sample warning
- [x] Remove the duplicate requirement-frequency table and retain a collapsed calculation note
- [x] Reduce Analysis demonstrated-strength cards to confirmed capability names only
- [x] Replace role-contaminated transferability guidance with generic structured comparison
  dimensions and deterministic candidate/target maturity
- [x] Calibrate partial-match weighting, small canonical samples, residual gap creation, and shared
  deficit consolidation across technical, management, product, and data transitions
- [x] Add an aspirational development/reassessment route with no immediate target application
  milestone and keep backend/UI path labels aligned
- [x] Persist bounded per-run posting, requirement, comparison, accessibility, and plan audit JSON
- [x] Promote Adzuna and You.com ATS discovery to parallel first-class market evidence sources
- [x] Add cross-source posting deduplication with richer-content selection and full provenance
- [x] Increase primary requirement analysis to ten employer- and provider-diverse postings
- [x] Track per-requirement Adzuna/You support and independent source-agreement signals
- [x] Separate role responsibilities, hiring capabilities, prerequisites, preferences, and
  non-requirement metadata while keeping only qualifications/prerequisites comparison-eligible
- [x] Make internship exclusion target-level-dependent and keep unspecified-seniority baselines
  standard-level
- [x] Retain separate responsibility/qualification counts and multi-source canonical provenance
- [x] Persist bounded retrieval rejection, seniority, duplicate, and selected-content audit facts
- [x] Live-QA AI Engineer/Canada for both successful multi-source and insufficient-evidence paths
- [x] Lock the 20-posting/17-employer/22%-top-three market classification to high diversity, low
  concentration, and the `Broadly distributed` presentation label
- [ ] Generate real portal or backend candidate answers and run the semantic evaluation gate
- [ ] Activity 10: LangGraph orchestration
- [ ] Activity 11: Streamlit user interface
- [ ] Activity 12: MCP transport and future Career Profile MCP evaluation
- [ ] Activity 13: Cross-session memory with mem0
- [ ] Activity 14: Testing, quality, and evaluation
- [ ] Activity 15: Documentation and usability review
- [ ] Activity 16: Final demo

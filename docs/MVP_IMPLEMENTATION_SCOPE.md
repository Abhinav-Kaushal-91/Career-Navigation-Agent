# MVP Implementation Scope

## Purpose and Authority

This document defines which capabilities from the frozen architecture are active during V1 implementation. V1 is a subset of that architecture. The architecture is not being replaced or simplified; inactive capabilities remain architecture-ready for later releases.

When architecture documents describe V2 or V3 capabilities, do not implement them unless this document explicitly includes them. Major scope additions require explicit approval.

## V1 Objective

V1 proves that the system can take a person's confirmed career evidence, compare it with the current live job market, identify transferable skills, classify gaps, determine candidate accessibility, identify useful bridge roles where needed, assess a requested timeline, and generate an explainable career strategy.

Only selected capabilities from the frozen architecture are activated in V1.

## V1 User Flow

```text
Structured manual onboarding
→ Profile review
→ Human confirmation
→ AI capability inference
→ Human inference review
→ Career goal
→ Goal review
→ Human goal confirmation
→ Current market search
→ Requirement extraction
→ Candidate-to-role comparison
→ Transferable capabilities
→ Gap analysis
→ Candidate accessibility
→ Bridge-role analysis
→ Timeline assessment
→ Career plan
→ Human approval
```

## V1 — Implement Now

1. Structured manual profile onboarding
2. Deterministic profile assembly from user-entered facts
3. Explicit evidence mapping from structured skills and capabilities
4. Profile confirmation
5. AI capability inference from approved explicit evidence
6. Per-capability human inference review
7. Deterministic career-goal capture and human confirmation
8. Current structured market search through Adzuna, with bounded You.com supporting evidence
9. Exact-title searches
10. Related-title searches
11. Basic posting validation
12. Deduplication
13. Job-page retrieval
14. Requirement extraction
15. Basic title normalization
16. Requirement comparison
17. Transferable-skill analysis
18. Five gap categories: `SKILL`, `EXPERIENCE`, `LEADERSHIP_SCOPE`, `EVIDENCE`, and `CREDENTIAL_PREREQUISITE`
19. Candidate Accessibility: `APPLY_NOW`, `APPLY_SELECTIVELY`, `NEAR_TERM_TARGET`, `ASPIRATIONAL`, `POOR_FIT`, and `INSUFFICIENT_CANDIDATE_EVIDENCE`
20. Bridge-role analysis
21. Timeline feasibility
22. Career-plan generation
23. Human approval
24. SQLite persistence
25. LangGraph checkpointing
26. Basic logging and traceability
27. Basic error recovery
28. mem0 integration after the core end-to-end workflow works

Frozen rules remain in force, including separation of confirmed facts from inferences, separate market and candidate conclusions, evidence provenance, human approval, provider-independent domain logic, and safe insufficient-evidence outcomes.

## V1 Market Intelligence

V1 current-market analysis provides only:

- Validated postings found
- Exact-title results
- Related-title results
- Distinct employers
- Geography
- Basic role-family interpretation
- Common role requirements
- Basic requirement observations
- Search limitations
- Evidence confidence

V1 reports four separate current-market signals: Opportunity Availability, Employer Diversity, Market Concentration, and Evidence Confidence. It does not use one `BROAD` / `MODERATE` / `NICHE` label to combine posting volume, employer participation, concentration, and evidence quality. Current searches do not classify an occupation as intrinsically common, specialized, niche, or emerging. Historical Market Verdict remains deferred to V2.

Counts describe unique validated postings found through the searched sources as of the recorded date. They are not complete market totals. Exact-title and related-title results remain separate.

## V1 Requirement Stringency

V1 may provide a lightweight, evidence-linked explanation, such as:

> Many analyzed postings require previous Product Owner experience.

> UiPath is frequently mandatory, while Python appears mainly as a preferred skill.

Do not implement the advanced V2 stringency engine yet. V1 must still distinguish mandatory from preferred requirements where sources support that distinction and must not present an unexplained score.

## V1.1 mem0

mem0 is included as V1.1 functionality and is implemented only after the primary end-to-end workflow works. It is optional contextual memory and never replaces SQLite or LangGraph checkpointing.

mem0 may remember approved contextual information such as:

- Preferred career directions
- Rejected career directions
- Bridge-role willingness
- Preferred location and work mode
- Long-term career goal
- Useful reassessment context

Do not store in mem0:

- Raw resumes
- Full employment history as the only authoritative copy
- Full job descriptions
- API keys or other secrets
- Unapproved inferred capabilities
- The only copy of an approved career plan

## Deferred to V2

Do not implement yet:

- Historical market provider
- Historical persistence analysis
- Trend analysis
- Seasonality
- Employer-concentration analytics
- Advanced requirement-stringency engine
- Full Market Verdict classifications
- Advanced title normalization
- Official role or occupation taxonomy
- Historical market UI
- Long-term role-market comparisons

These capabilities remain part of the frozen long-term architecture but are inactive in V1.

## Deferred to V3

Do not implement yet:

- n8n scheduled market monitoring
- Automatic recurring reassessment
- Long-term market snapshots
- Proactive career notifications
- Pinecone
- Large-document RAG
- Career evidence RAG
- ElevenLabs voice interface
- Automatic applications
- ATS browser automation
- Resume tailoring
- Cover-letter generation
- Recruiter outreach
- Interview preparation

## V1 Profile-Acquisition Decision

V1 uses structured manual onboarding:

```text
About You
→ Experience
→ Skills and Competencies
→ Projects and Achievements
→ Education and Certifications
→ Review
→ Human confirmation
```

Document import is not part of the current V1 implementation. DOCX import is a deferred
convenience input that may later pre-fill the same structured profile. PDF import, parsing,
OCR, and resume-extraction prompts are not part of the current V1 scope. Do not introduce
document libraries, Pinecone, or embeddings for profile acquisition.

## V1 Technology Stack

Use:

- Python
- Streamlit
- LangChain
- LangGraph
- You.com MCP
- Hosted LLM through the Model Gateway
- SQLite
- LangGraph checkpoint persistence
- mem0 after core workflow stability
- pytest
- Ruff

Do not use in V1:

- n8n
- Pinecone
- ElevenLabs
- Lyzr

Provider selection remains configuration-driven and evaluation-based. You.com remains behind the Market Intelligence Service and MCP Client Layer; LangGraph does not call it directly.

## V1 Success Criteria

The MVP is successful when a user can:

1. Build a career profile through structured manual onboarding.
2. Review and confirm the entered information.
3. Enter a target role or exploration goal.
4. Retrieve current market evidence.
5. See matched and transferable capabilities.
6. See categorized gaps.
7. Understand current accessibility to target roles.
8. See a bridge role when useful.
9. Receive a realistic timeline assessment.
10. Receive an explainable, actionable career plan.
11. Review and approve the plan.

Target end-to-end completion time: under five minutes, excluding external provider outages.

## Implementation Rule

### Activity 8 market source update

Adzuna structured discovery and You.com MCP web discovery run concurrently in V1. Both lanes are
bounded and independently validated, then merged with cross-source deduplication. Adzuna structured
fields are retained when both lanes identify the same posting. A provider outage lowers
source-coverage confidence but does not discard healthy evidence from the other lane. Both
providers remain behind the Market Intelligence Service; LangGraph and downstream career logic
remain provider-neutral.

The frozen architecture remains the long-term reference. This document controls which frozen-architecture capabilities are activated during V1. Deferred V2 and V3 capabilities require explicit approval before implementation.

## Activity 6A Activation

V1 requirement comparison and transferable-skill analysis are implemented through
`CANDIDATE_COMPARISON_READY`. The implementation produces posting-grounded direct, transferable,
partial, no-confirmed-match, and insufficient results without an overall fit percentage. Gap
classification and candidate accessibility remain the next implementation activity.

## Activity 6B Activation

The five V1 gap categories, transparent severity policy, hard-prerequisite detection, qualitative
candidate accessibility, and `RoleAssessment` assembly are implemented through
`CANDIDATE_ASSESSMENT_READY`. Gaps are deduplicated without discarding requirement provenance.
Opportunity availability remains independent from candidate accessibility. Bridge-role and timeline
assessment remain deferred to Activity 6C, and career planning remains deferred to Activity 7.

## Activity 6C Activation

Observed-market bridge-role evaluation and qualitative timeline assessment are implemented through
`CAREER_PATH_ASSESSMENT_READY`. Bridge candidates must be observed related titles and must reduce
specific material gap IDs; no additional market search is performed. Timeline conclusions use the
four approved classifications and preserve missing evidence and user constraints without numeric
probabilities or completion-date predictions. CareerPlan and milestone generation remain deferred
to Activity 7A.

## Activity 7A Activation

V1 career-plan generation is implemented through `CAREER_PLAN_READY`. Plans use the existing
`DIRECT`, `BRIDGE`, `MULTIPLE_PATHS`, `EXPLORATION`, and `NO_CREDIBLE_PATH` classifications and
remain unapproved drafts. Milestones are gap-driven, measurable, evidence-oriented, dependency-
validated, and bounded by the requested timeline when one exists. Optional model wording cannot
change target roles, bridge roles, gap IDs, phases, milestone types, dependencies, credentials,
risks, or assumptions; invalid output falls back safely. Approval and persistence remain deferred
to Activity 7B and later persistence work.

## Activity 7B Activation

V1 final human review is implemented as a LangGraph interrupt after `CAREER_PLAN_READY`. A typed
request must match the exact checkpointed plan ID and version. Terminal actions produce
`COMPLETED`, `COMPLETED_WITH_LIMITATIONS`, `SAVED_AS_DRAFT`, or `USER_CANCELLED`; an unavailable
responsible plan produces `INSUFFICIENT_EVIDENCE`. Revision actions stop in explicit profile, goal,
market, or career-analysis reassessment states after centralized dependency-aware invalidation.
Approval and action records are checkpoint/session scoped only. SQLite repositories, durable plan
history, user accounts, mem0, and historical market intelligence remain outside this activation.

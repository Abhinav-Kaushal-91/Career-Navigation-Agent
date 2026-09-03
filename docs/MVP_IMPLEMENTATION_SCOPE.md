# MVP Implementation Scope

## Purpose and Authority

This document defines which capabilities from the frozen architecture are active during V1 implementation. V1 is a subset of that architecture. The architecture is not being replaced or simplified; inactive capabilities remain architecture-ready for later releases.

When architecture documents describe V2 or V3 capabilities, do not implement them unless this document explicitly includes them. Major scope additions require explicit approval.

## V1 Objective

V1 proves that the system can take a person's confirmed career evidence, compare it with the current live job market, identify transferable skills, classify gaps, determine candidate accessibility, identify useful bridge roles where needed, assess a requested timeline, and generate an explainable career strategy.

Only selected capabilities from the frozen architecture are activated in V1.

## V1 User Flow

```text
Resume or manual profile
→ Structured profile extraction
→ Human confirmation
→ Career goal
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

1. Resume upload and manual profile input
2. Resume text extraction
3. Structured profile extraction
4. Profile confirmation
5. Goal confirmation
6. Current market search through You.com MCP
7. Exact-title searches
8. Related-title searches
9. Basic posting validation
10. Deduplication
11. Job-page retrieval
12. Requirement extraction
13. Basic title normalization
14. Requirement comparison
15. Transferable-skill analysis
16. Five gap categories: `SKILL`, `EXPERIENCE`, `LEADERSHIP_SCOPE`, `EVIDENCE`, and `CREDENTIAL_PREREQUISITE`
17. Candidate Accessibility: `APPLY_NOW`, `APPLY_SELECTIVELY`, `NEAR_TERM_TARGET`, `ASPIRATIONAL`, `POOR_FIT`, and `INSUFFICIENT_CANDIDATE_EVIDENCE`
18. Bridge-role analysis
19. Timeline feasibility
20. Career-plan generation
21. Human approval
22. SQLite persistence
23. LangGraph checkpointing
24. Basic logging and traceability
25. Basic error recovery
26. mem0 integration after the core end-to-end workflow works

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

V1 may use the simple current-market descriptions `BROAD`, `MODERATE`, `NICHE`, and `INSUFFICIENT_EVIDENCE`. These are lightweight V1 summaries, not replacements for the full historical Market Verdict classifications in the frozen architecture.

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

## Resume-Processing Decision

V1 does not use RAG for a single resume. Use:

```text
Resume
→ Text extraction
→ Structured LLM extraction
→ Validation
→ Human confirmation
```

Preserve evidence references where practical. Do not introduce Pinecone or embeddings for resume processing.

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

1. Upload or enter a career profile.
2. Confirm the extracted information.
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

The frozen architecture remains the long-term reference. This document controls which frozen-architecture capabilities are activated during V1. Deferred V2 and V3 capabilities require explicit approval before implementation.

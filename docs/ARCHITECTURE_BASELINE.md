# MVP Architecture Baseline

## 1. Product Objective

The AI Career Strategy & Market Navigator is a market-grounded career intelligence and strategy agent for users at any career stage. It compares confirmed candidate evidence with current market evidence and credible historical market evidence when available to produce explainable role analysis, gaps, timeline feasibility, and career strategy.

## 2. Component Architecture

The logical component direction is:

```text
Streamlit UI
→ Application Controller
→ LangGraph Orchestrator
→ Domain Services
→ Integration Interfaces
→ Adapters / Persistence
→ External Systems
```

The major components are Streamlit UI, Application Controller, LangGraph Orchestrator, Profile Domain Service, Market Intelligence Domain Service, Career Analysis Domain Service, Career Planning Domain Service, Model Gateway, MCP Client Layer, Persistence Layer, Observability Layer, and External Systems. Boundaries are logical and may run in one local Python process.

## 3. Workflow Architecture

The parent workflow is:

```text
Initialize Run
→ Profile and Goal
→ Market Intelligence
→ Career Analysis
→ Career Plan
→ Final Approval
→ Finalize Run
```

Subworkflows cover profile/goal confirmation, current and historical market evidence, requirement stringency, market verdicts, candidate-to-role comparison, gaps/accessibility, bridge/timeline analysis, plan assembly, and final approval. Detailed implementation nodes and graph state are separate concerns.

## 4. Data and State Architecture

- LangGraph state is serializable, provider-agnostic workflow context containing stage information, temporary drafts, approvals, retries, routing, and references.
- SQLite is the authoritative MVP business store for confirmed user records, retained market evidence, derived run conclusions, plans, approvals, and business metadata.
- Derived analysis records are authoritative records of what the system concluded during a run, not candidate facts or objective market facts.
- `USER_INTENT` remains distinct from `CONFIRMED_FACT`.
- Original evidence is preserved beside normalized interpretations.
- Large documents are referenced rather than repeatedly copied into checkpoints.
- Approved profiles, goals, and plans are versioned; confirmed profiles and approved plans are immutable.

## 5. MCP Architecture

You.com MCP is the only required MVP MCP boundary. The path is LangGraph → Market Intelligence Domain Service → MCP Client Layer → You.com MCP. The conceptual allowlist is `you-search` and `you-contents`.

A custom Career Data MCP server is excluded from the MVP. Internal persistence uses Domain Services → Repository Interfaces → SQLite. A custom server may be reconsidered if multiple consumers, independent deployment, multiple agents, or organizational boundaries justify it.

## 6. Model Architecture

Domain services use Domain Service → Model Gateway → Provider Adapter → Hosted LLM API. Logical roles remain separate: Extraction Model, Reasoning Model, and optional Validation Model. Fireworks, NVIDIA NIM, and Hugging Face Router remain candidates, not selected providers. Final selection is evaluation-driven.

Workflow-facing model outputs require structured validation. Provider clients and SDK objects never enter graph state.

## 7. Persistence Architecture

SQLite stores authoritative business records and retained evidence. LangGraph checkpoints store workflow continuity, pauses, retries, routing, and temporary references only. mem0 is optional contextual memory and is not authoritative; raw resumes and the only copies of confirmed facts or approved plans do not enter mem0.

## 8. Reliability and Security Architecture

Failures use a shared error taxonomy with bounded, reason-specific retries and explicit degraded mode. Insufficient evidence is distinct from technical failure. Secrets remain in environment/configuration and never enter state, storage, logs, prompts, or user-visible errors. External content is untrusted data. PII is minimized in remote calls. Protected attributes do not affect role suitability. Chain-of-thought is never persisted.

## 9. Observability Architecture

Observability is a provider-independent cross-cutting concern covering run, stage, model, tool, human approval, provenance, retry, fallback, error, and confidence metadata. LangSmith remains a later candidate; a simpler local structured tracing interface may be used initially.

## 10. Key ADRs

- ADR 8: SQLite is the authoritative MVP business store
- ADR 9: LangGraph checkpoints are workflow persistence, not business authority
- ADR 10: mem0 is optional contextual memory only
- ADR 11: Large source documents are referenced rather than repeated in graph state
- ADR 12: Graph state is serializable and provider-agnostic
- ADR 13: Confirmed profiles, approved goals, and approved plans are versioned and immutable
- ADR 14: Derived analysis records are run-scoped and provenance-linked
- ADR 15: Original external evidence is preserved alongside normalized interpretations
- ADR 16: Data models separate evidence, analysis, and planning records
- ADR 17: Approval records reference the exact entity version presented
- ADR 18: Use You.com MCP as the MVP external search/content boundary
- ADR 19: Do not build a custom Career Data MCP server for the MVP
- ADR 20: Internal persistence uses repository interfaces
- ADR 21: Hosted LLM access goes through the Model Gateway
- ADR 22: Logical model roles remain separated
- ADR 23: Final model/provider choice is evaluation-driven
- ADR 24: MCP and provider objects never enter graph state
- ADR 25: Confidence is multidimensional, not a single opaque score
- ADR 26: Failure handling uses bounded retries and explicit degraded mode
- ADR 27: External content is treated as untrusted data
- ADR 28: PII minimization applies to remote model and tool calls
- ADR 29: Observability remains provider-independent
- ADR 30: Chain-of-thought is never persisted
- ADR 31: Step 2 architecture is frozen for MVP implementation

## 11. Open Decisions

### Must Resolve Before Implementation

- Approved dependency set and configuration values
- Exact business schema and migration approach
- Exact Model Gateway and MCP client contracts
- Security controls required for the chosen deployment

### May Resolve During Implementation

- Exact LangGraph checkpointer
- Exact You.com client/session lifecycle
- Retry counts and timeout values
- Local tracing format
- SQL normalization versus JSON child records
- Role and occupation taxonomy providers
- Posting deduplication model
- Whether a canonical capability entity is needed
- Cost and latency targets
- Whether one model initially serves extraction and reasoning
- Provider fallback order

### Post-MVP or Optional

- Whether mem0 is included in the first MVP
- Optional validation model
- LangSmith adoption
- Dedicated raw-content store and long-term market snapshots
- Additional external MCP servers
- Multi-user isolation and full authentication

Retention periods, encryption at rest, raw-resume retention, and access/deletion policy require explicit security/privacy decisions before handling real user data.

## 12. Implementation Constraints

- Do not commit secrets or real user data.
- Keep domain logic independent of Streamlit, MCP transport, and provider SDKs.
- Preserve source evidence and retrieval dates.
- Keep graph state serializable and small.
- Require validation before model output enters workflow logic or authoritative records.
- Require user approval before inferred profile facts or plans become authoritative.
- Maintain separate market and candidate conclusions.
- Do not guarantee career outcomes.

## 13. Definition of Architecture Freeze

The Step 2 architecture is frozen for MVP implementation. Implementation may now begin within these boundaries. Minor implementation details may evolve. Major component-boundary, authority, provider, MCP, security, or workflow changes require an ADR and explicit review.

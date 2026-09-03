# Decisions

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

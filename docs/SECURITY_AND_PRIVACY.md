# Security and Privacy

## Adzuna credentials and source trust

`ADZUNA_APP_ID` and `ADZUNA_APP_KEY` are secret settings and never enter logs, graph state,
prompts, retained sources, smoke output, or user-visible errors. Adzuna descriptions and You.com
content are untrusted external text; embedded instructions are never followed.

## 1. Purpose

Protect candidate data, external credentials, retained evidence, and workflow integrity while preserving user control and provenance.

## 2. Data Handling

Resume data is PII. Candidate records, goals, gaps, feedback, and plans may be career-sensitive. Remote model and tool calls receive only the minimum necessary information. Contact information is removed when not required. Raw resumes are not stored in mem0.

## 3. Secrets and Credentials

API keys and authentication tokens remain in environment configuration. They must never enter LangGraph state, SQLite business records, mem0, logs, prompts, tool metadata, or user-visible errors. Database files are excluded from Git.

## 4. External Content

External pages, job descriptions, reports, and tool results are untrusted data. Embedded instructions are ignored; they cannot alter system policy or workflow behavior. URLs and commands found in retrieved content are not executed automatically. Source provenance is retained.

## 5. Fairness and User Control

Protected attributes such as age, gender, race, ethnicity, religion, disability, and nationality must not affect role suitability. Career breaks are not automatically penalized. Users can correct or reject inferred information, and approval events are auditable.

## 6. Storage Boundaries

SQLite is authoritative for confirmed business records and retained market evidence. LangGraph checkpoints are workflow persistence only. mem0 is optional contextual memory only. Large raw documents are referenced rather than repeatedly copied into checkpoints, and raw resumes do not enter mem0.

## 7. Auditability

Approval events, source references, retrieval dates, model/tool metadata, assumptions, limitations, and user feedback are traceable. Logs must not contain secrets or full resumes. Chain-of-thought and private model reasoning are never persisted.

## 8. Open Questions

- Encryption-at-rest approach
- Retention periods and raw-resume retention
- Dedicated raw-content store
- Access control and deletion workflows
- Multi-user isolation

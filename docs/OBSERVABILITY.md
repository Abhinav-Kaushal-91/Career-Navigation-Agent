# Observability

## 1. Purpose

Observability makes workflow execution, evidence provenance, model/tool behavior, approvals, failures, and confidence traceable without storing secrets or private model reasoning.

## 2. Run-Level Tracing

Record conceptually: run ID, thread ID, run type, duration, final status, degraded mode, and final confidence.

## 3. Stage-Level Tracing

Record stage, referenced inputs, referenced outputs, duration, retry count, and error category. References are preferred over copying large documents.

## 4. Tool-Level Tracing

Record MCP server, tool, sanitized parameters, result count, duration, status, retries, and error category. Never record authentication headers, API keys, or unnecessary PII.

## 5. Model-Level Tracing

Record provider, model, task type, prompt version, latency, token usage where available, structured-schema validation, retries, and fallback. Provider-specific objects and chain-of-thought are not persisted.

## 6. Human-Level Tracing

Record approval type, decision, timestamp, feedback, reviewed entity/version, limitations acknowledged, and resulting workflow transition.

## 7. Provenance and Confidence

Every derived conclusion should be traceable to profile and goal versions, source references, model/tool metadata, workflow version, validation status, assumptions, limitations, and confidence dimensions.

## 8. Implementation Direction

The observability implementation is provider-independent and unresolved. LangSmith is a strong later candidate for tracing and evaluation, but the MVP may begin with a simpler local structured tracing interface.

## 9. Privacy and Retention

Logs must not contain secrets, full resumes, unnecessary contact details, raw authentication material, or private model reasoning. Retention, access, deletion, and encryption require later policy decisions.

## 10. Open Questions

- Observability platform
- Local tracing format and storage
- LangSmith adoption
- Sampling and retention policies
- Metrics and alerting targets

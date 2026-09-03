# Provider Strategy

## 1. Purpose

Hosted model access remains provider-independent and configuration-driven. The final model/provider is not selected in Step 2.

## 2. Model Gateway

Conceptual flow:

```text
Domain Service → Model Gateway → Provider Adapter → Hosted LLM API
```

LangGraph and domain services depend on the gateway contract, not provider SDKs or provider-specific objects.

## 3. Logical Model Roles

- **Extraction Model:** Resume extraction, job-requirement extraction, title interpretation, and structured source extraction. Priorities are grounding, structured-output reliability, latency, cost, and low hallucination.
- **Reasoning Model:** Transferable-skill reasoning, gap reasoning, bridge reasoning, timeline feasibility, plan synthesis, and explanations. Priorities are reasoning quality, instruction following, tool context, and grounded explanations.
- **Validation Model:** Optional future independent grounding review, critique, and unsupported-claim detection. It is not required for the MVP.

One hosted model may fill multiple roles while the logical roles remain distinct.

## 4. Provider Adapters

Conceptual adapters may support Fireworks, NVIDIA NIM, and Hugging Face Router/hosted inference. All satisfy the same gateway interface. Provider SDK objects remain inside adapters.

## 5. Candidate Providers and Models

Candidates include the NVIDIA Nemotron family through a hosted provider and other suitable hosted open-weight/instruction models through Fireworks or Hugging Face routes. Possible paths include Nemotron through Fireworks or NVIDIA NIM, and other hosted models through Fireworks or Hugging Face Router. No winner is selected.

## 6. Configuration

Provider choice is configuration-driven. Potential future variables include `LLM_PROVIDER`, `EXTRACTION_MODEL`, `REASONING_MODEL`, `VALIDATION_MODEL`, `FIREWORKS_API_KEY`, `NVIDIA_API_KEY`, `HF_TOKEN`, and `YDC_API_KEY`. No real values or secrets are stored.

## 7. Request Context

Conceptual `ModelRequestContext` contains run ID, workflow stage, task type, model role, prompt version, required output schema, source references, output limit, temperature, timeout, retry policy, and whether candidate PII is included.

## 8. Response Metadata

Conceptual `ModelResponseMetadata` contains provider, model, request ID, task type, latency, token usage, finish reason, schema validity, retry count, fallback use, and creation time. Private chain-of-thought is not stored.

## 9. Structured Outputs

Any output used by workflow logic must be schema-validated later. Invalid output is rejected, retried once with schema correction when appropriate, sent to configured fallback if available, and safely failed if still invalid. Malformed output must not enter authoritative records.

## 10. Retry and Fallback

Structured-output retries, transient provider retries, and provider fallback are distinct. Retries are bounded, reason-specific, traceable, and idempotent where necessary. Fallback preserves the same downstream contract and records the original failure, fallback provider/model, and final validation status. Final ordering and counts remain open.

## 11. Evaluation Criteria

Final selection is evaluation-driven using factual grounding, extraction accuracy, structured reliability, transferable-skill and gap reasoning, bridge quality, timeline realism, unsupported-claim rate, latency, cost, reliability, and tool compatibility. Public benchmarks alone do not decide.

## 12. PII Minimization

Remote calls receive only minimum necessary information. Requirement extraction does not need contact details; career comparison may need career evidence but not contact information; market search should not send resume contents to You.com unless explicitly necessary, which is not expected for the MVP. Secrets and unnecessary contact information never leave configuration boundaries.

## 13. Prompt-Injection Boundary

External postings, reports, and pages are data, never instructions. Embedded commands are ignored; system policy is not altered; URLs or commands are not executed automatically; provenance is preserved; and system/tool instructions remain separate from retrieved content.

## 14. Traceability

Model-supported conclusions should retain run ID, stage, provider, model, task/prompt version, source references, validation result, retry/fallback events, and timestamp. Structured explanations and evidence references are stored instead of chain-of-thought.

## 15. Provider-Independence Tests

Replacing Fireworks with NVIDIA NIM must require only configuration/adapter changes. LangGraph, domain services, and career logic remain unchanged. Replacing You.com later must affect only the external search/MCP adapter boundary; Market Intelligence logic remains.

## 16. Open Questions

- Final primary and extraction models
- Whether one model handles extraction and reasoning
- Fallback provider order
- Exact retry/timeout values
- Hugging Face Router necessity
- Cost ceiling and latency target
- Value of a validation model

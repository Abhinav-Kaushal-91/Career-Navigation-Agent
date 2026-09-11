# Full-inventory consolidated role-profile test — September 10, 2026

## Follow-up: five longer descriptions from different employers

User requested the top five on GLM. Selected Cognizant (`JD:00069350121`),
CGI (`JD:jl=1010203361685`), Astra (`JD:4451905067`), Atyeti
(`JD:jid=1b742ca9626c0351`) and Autodesk (`JD:26WD97970`). This diagnostic selection
prioritizes Java-role relevance, available longer text and distinct employers;
it is not a verified production top-five ranking. Excluded all four short excerpts
from the ten-record test and the second Autodesk document. Atyeti remains generic
job-board wording; documents are saved evidence, not newly verified active vacancies.

Same GLM model, consolidated prompt, schema, temperature 0, streaming adapter,
30,000 output ceiling, 600-second timeout and zero retries. Source text: 11,697
characters. Result: **246.26 seconds, 3,546 input tokens, 30,000 reported output
tokens, finish_reason=length, zero-byte final response**. The gateway rejected
`BatchRoleProfile` as `ModelResponseValidationError: truncated_response`.
No schema-valid profile or grounding audit could be produced. No new code/model
settings, production workflow changes, candidate assessment or Plan were introduced.

| GLM consolidated sample | Input tokens | Seconds | Final JSON |
|---|---:|---:|---|
| 34 records | 10,023 | 248.98 | None; output ceiling reached |
| 10 records | 5,328 | 273.62 | None; output ceiling reached |
| 5 longer records | 3,546 | 246.26 | None; output ceiling reached |

The repeated failure persists despite lower input volume. This supports investigating
the task/output contract and provider/model generation behavior instead of further
count-only reductions; it does not establish an exact hidden-reasoning token split
or prove all GLM tasks fail. No extra request or automatic fallback was sent.
Artifacts: `outputs/batch-role-profile/20260910T164628Z/` contains the selected-input
manifest, exact request, metrics, empty response and safe failure record.

## Follow-up: ten selected records, unchanged model and contract

At the user's request, repeated the same single-call test with exactly ten records:
the six longer retrieved descriptions plus four evidence-bearing 500-character
snippets (Acestack, INFOYA, emergiTEL and Astra's microservices/API role). Eight named
employers; Autodesk and Astra each contribute two separate records. Related-role
metadata remains visible; this is not ten complete exact-target descriptions.
Selection prioritizes the available longer texts and avoids company-only snippets;
it is an explicit diagnostic subset, not a new production ranking policy.

| Measure | Full inventory | Ten-record follow-up |
|---|---:|---:|
| Records | 34 | 10 |
| Source characters | 30,336 | 18,336 |
| Input tokens | 10,023 | 5,328 |
| Reported output tokens | 30,000 | 30,000 |
| Request duration | 248.98 s | 273.62 s |
| Finish reason | length | length |
| Visible final response | 0 bytes | 0 bytes |
| Valid consolidated profile | No | No |

Fireworks GLM model, system prompt, schema, temperature, 30k ceiling, streaming
adapter and 600-second timeout were unchanged; one request, zero retries. Gateway
rejected the follow-up as `ModelResponseValidationError: truncated_response`.
The model returned no usable final output; the source-grounding audit could not run.
There was no network timeout. The lower input size did not prevent output-budget
exhaustion. These two variable-latency observations do not establish that smaller
batches are intrinsically slower or diagnose the provider's hidden reasoning.

Artifacts: `outputs/batch-role-profile/20260910T162833Z/` contains the exact request,
selected-record manifest, metrics, empty final-response file and failure category.
The diagnostic runner now accepts explicit `--record-ids`; it rejects unknown or
duplicate IDs, preserves original text/order, and defaults to the full inventory.
Four targeted offline audit/selection tests and Ruff pass. No production website
changes, model-setting changes or further live requests were made.

Conclusion: capping records at ten alone did not fix this consolidated GLM contract.
Further tests should isolate task/output complexity or model behavior rather than
assuming record count is the sole issue. No new strategy was implemented here.

## Outcome

**Failed safely: no final role profile returned.** One live request to configured
Fireworks `accounts/fireworks/models/glm-5p3-flash`, using a diagnostic consolidated
schema/prompt and the production ModelGateway/streaming adapter.

| Measure | Observed |
|---|---:|
| Source records sent together | 34 |
| Adzuna excerpts | 28 |
| Separately retrieved JD documents | 6 |
| Source-text characters | 30,336 |
| Provider-reported input tokens | 10,023 |
| Provider-reported output tokens | 30,000 |
| Elapsed request time | 248.98 seconds (4m 9s) |
| Finish reason | `length` |
| Final-answer file size | 0 bytes |
| Gateway result | `ModelResponseValidationError: truncated_response` |
| Requests / retries | 1 / 0 |

The provider exhausted the configured output ceiling without delivering visible
final JSON through the production adapter. Reported completion usage is not the
size of a usable final answer. No private reasoning traces were collected, so do
not assert an exact reasoning-token split or diagnose the provider's internal
execution. This is not a network timeout: the provider returned `length` within
the configured 600-second timeout.

## Scope and input quality

All saved records were supplied, with no sampling down to four postings and no
new retrieval. Sources: the frozen 28-record demo retrieval plus the complete
six-document JD inventory. The 28 excerpts are 500-character fragments, not full
descriptions. The six retrieved documents are longer (completeness not independently
verified). This is the full **available inventory**, not 34 complete, independently
verified active vacancies. Possible duplicate links remain flagged, not merged.
Related titles and seniority differences were retained as scope metadata. No
candidate profile or private credentials were included in the model messages.

## Requested task

Consolidate equivalent capabilities into themes with per-posting quotations,
separate required/unspecified hiring asks, preferences, duties and prerequisites;
preserve years, versions, negation, scope and alternatives. Review all posting IDs,
distinguish partial/non-hiring evidence and avoid a universal union of employer
requirements. No candidate assessment, career plan or market forecast requested.
The role title is case input, not a role-specific classification rule.

The offline audit checks IDs, source quote/section grounding, review completeness,
explicit obligation conflicts, distinct-posting counts and distinct-employer counts.
Three tests pass, plus Ruff. These do not establish semantic correctness of model
outputs. No live output reached this audit, so completeness, grouping quality and
required-versus-preferred accuracy **cannot be evaluated** from this attempt.

## Interpretation

One all-in-one GLM request under the current 30k ceiling did not produce a usable
result. This does not disprove batch consolidation or establish that all models
would fail. Increasing timeout alone would not address this observed token-limit
termination. No second call, token-limit increase or silent fallback was attempted.

The previous two-worker test completed four mixed-length records in 190.50 seconds;
that is a different workload, not a controlled serial/parallel/batch comparison.
Do not claim that 249 seconds establishes higher or lower full-corpus throughput.

Potential next experiment (not implemented): bounded multi-posting batches followed
by consolidation of validated findings, or a model-supported lower-reasoning setting
after verifying provider support. Any comparison should use the same inventory and
measure coverage/qualifier preservation as well as latency. Production website
and its active session remain unchanged.

Artifacts: `outputs/batch-role-profile/20260910T162042Z/` contains the manifest,
exact non-secret request, provider metrics, empty final-response file, and validation
failure record. Runner: `scripts/benchmark_batch_role_profile.py` (dry-run default;
`--live` explicitly sends one request).

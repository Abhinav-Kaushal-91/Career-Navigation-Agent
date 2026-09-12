# Error Handling

## September 11 — live failure codes and sanitized records

The live launch boundary now distinguishes MARKET_TIMEOUT, MARKET_RATE_LIMIT,
MARKET_RESPONSE_INVALID, transport/auth/configuration errors and internal validation failures.
Codes are allowlisted; unknown categories map to INTERNAL_ERROR. The safe code remains visible
on the recovery and confirmed-goal pages. Details include the last checkpoint stage when available;
an unexpected exception uses WORKFLOW_EXECUTION rather than asserting an unverified failed stage.

New failed attempts write a small JSON record to ignored outputs/failed-runs and emit a warning
even when normal INFO logs are disabled. Records contain IDs, UTC timestamp, safe code/stage,
total attempt elapsed seconds and whether a market snapshot was preserved. No raw exception text,
stack traces, API headers/keys, profile/goal content, job descriptions or model output are stored.
Persistence failure is reported without masking the original failure. Retrying clears the current
displayed diagnostic but does not delete earlier files. No automatic API retry was added.

## Structured model extraction

An invalid structured response may receive one controlled schema-repair attempt. Repeated invalid
responses fail that posting safely. A transient timeout may receive one retry in the Activity 8 QA
configuration; repeated timeouts also fail safely. Failed postings do not enter the requirement
frequency denominator. Logs and QA output contain only typed failure categories, never rejected
model content, job descriptions, secrets, or reasoning traces.

## Activity 8 market-source failures

Adzuna and You.com authentication, rate-limit, timeout, transport, and malformed-response failures
map into the existing market error hierarchy. Failure of one concurrent lane preserves validated
evidence from the other and lowers source-coverage confidence. A You.com enrichment failure does
not discard a healthy Adzuna posting, and a conflict rejects supporting evidence rather than
overwriting structured primary fields.

## 1. Purpose

Errors are classified consistently, handled safely, and exposed through user-safe messages without leaking secrets or unsupported conclusions.

## 2. Error Taxonomy

| Error | Recoverable | Retry/backoff/fallback | Partial result | Confidence impact | User behavior |
|---|---|---|---|---|---|
| `INPUT_ERROR` | Usually no | No; request correction | No | Insufficient for affected input | Explain required correction |
| `PROFILE_EXTRACTION_ERROR` | Sometimes | Bounded retry or manual entry | Yes if usable | Lower profile confidence | Offer manual continuation |
| `AUTHENTICATION_ERROR` | Configuration-dependent | No automatic credential retry | No affected operation | Lower affected evidence | Safe configuration message |
| `RATE_LIMIT_ERROR` | Yes | Bounded backoff | Yes if sufficient | Lower if degraded | Explain limitation |
| `NETWORK_ERROR` | Yes | Bounded retry/backoff | Yes | Lower if partial | Preserve completed work |
| `TOOL_TIMEOUT` | Yes | Bounded retry | Yes | Lower tool confidence | Continue if credible |
| `EMPTY_SEARCH_RESULT` | Yes | Adjust approved query | Yes | Lower coverage | Broaden permitted search |
| `BLOCKED_PAGE` | Yes | Alternate source | Yes | Lower posting validity | Disclose blocked source |
| `EXPIRED_POSTING` | Yes | Exclude or replace | Yes | Lower freshness | Do not use as active posting |
| `DUPLICATE_CONTENT` | Yes | Deduplicate | Yes | No direct change | Do not inflate counts |
| `SCHEMA_VALIDATION_ERROR` | Yes | Corrective retry once | No invalid output | Lower model confidence | Do not persist invalid data |
| `LLM_PROVIDER_ERROR` | Yes | Bounded retry/fallback | Yes if fallback succeeds | Lower model confidence | Disclose degraded mode when relevant |
| `INVALID_MODEL_OUTPUT` | Sometimes | Schema retry then fallback | No invalid output | Insufficient affected result | Safe failure if unresolved |
| `INSUFFICIENT_MARKET_EVIDENCE` | No | No speculative retry | Observed facts only | Insufficient market confidence | Return valid insufficient result |
| `INSUFFICIENT_CANDIDATE_EVIDENCE` | No | Ask targeted clarification | Yes with limitation | Insufficient candidate confidence | Invite clarification |
| `AMBIGUOUS_TARGET` | Yes | Request clarification | No target analysis | Insufficient target confidence | Ask focused question |
| `UNCONFIRMED_PREREQUISITE` | Yes | Request confirmation | Yes with limitation | Lower accessibility confidence | Ask user; do not assume |
| `NO_VALID_BRIDGE_ROLE` | No | No forced alternative | Yes without bridge | Lower path confidence | State no credible bridge |
| `PERSISTENCE_ERROR` | Sometimes | Bounded retry if safe | No approved save | Final status affected | Do not claim saved |
| `APPROVAL_REQUIRED` | Yes | Wait for user | Draft only | No approval confidence | Request approval |
| `APPROVAL_REJECTED` | Yes | Route to revision | Draft/alternative | No technical penalty | Record decision |
| `INTERNAL_INVARIANT_ERROR` | Sometimes | Log and safe stop | Only validated prior work | Insufficient affected result | Generic safe error |

Internal logs retain category, stage, recoverability, retry data, references, and resolution without secrets. User messages are concise and safe; technical details are not exposed by default.

## 3. Retry Principle

Retries are bounded, reason-specific, traceable, and idempotent where necessary. Do not retry user rejection, insufficient evidence, or invalid business assumptions. Technical/transient failures may retry; invalid structured output receives a schema-correction attempt and then configured fallback when appropriate.

## 4. Degraded Mode

Degraded mode may continue for unavailable historical evidence, blocked pages, one failed search query, a failed provider followed by successful fallback, or credible partial market evidence. It must not continue when the profile is unreliable, required approval is absent, structured output remains invalid, market evidence is too weak, or critical persistence of approved data fails.

Limitations and confidence changes remain visible.

## 5. Safe Failure

The workflow returns insufficient evidence for analytical insufficiency and `FAILED` only for unrecoverable technical/system failure. It does not use `FAILED` for missing history, user disagreement, one failed tool, or candidate gaps.

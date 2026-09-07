# V1 model-facing contracts

This is the implemented contract inventory, not a claim that a live Nemotron run
has passed. Prompt builders and Pydantic schemas linked below are authoritative;
this document deliberately does not duplicate their complete prompts. It covers
the five assessment flows, not every auxiliary model call (for example, controlled
target-variant review).

## Shared gateway and effective NVIDIA request

All five flows call `ModelGateway.generate_structured`. Routing and validation live
in [gateway.py](../src/ai_career_navigator/models/gateway.py); the actual NVIDIA
body is built by
[`build_nvidia_payload`](../src/ai_career_navigator/models/providers/nvidia.py).

| Flow | ModelRole | Prompt version | Output-token limit |
| --- | --- | --- | ---: |
| Capability inference | `EXTRACTION` | `capability-inference-v2` | 2,048 |
| Posting requirement extraction | `EXTRACTION` | `market-requirements-v3` | 4,096 |
| Candidate/requirement comparison | `REASONING` | `candidate-comparison-v2` | 2,400 |
| Career assessment synthesis | `REASONING` | `career-assessment-synthesis-v4` | 3,200 |
| Career-plan wording refinement | `REASONING` | `plan-wording-v2` | 2,400 |

Every listed caller requests temperature `0`. The NVIDIA adapter additionally
forces `0.0` for extraction/validation roles. For each structured call, the effective
body contains:

- `model`: the configured model for the requested role, not a hard-coded Nemotron
  version. `LLM_PROVIDER`, `EXTRACTION_MODEL`, and `REASONING_MODEL` select the
  provider/models. Defaults are mock configuration, not a live NVIDIA deployment.
- `messages`: the task system prompt; a second system message containing the full
  output JSON Schema; and the generated user prompt. On a schema-repair attempt,
  the task system message also contains bounded validation feedback.
- `temperature: 0.0`, the caller's `max_tokens`, `stream: false`,
  `chat_template_kwargs: {"enable_thinking": false}`, and
  `response_format: {"type": "json_object"}`.

There is **no explicit reasoning-budget parameter**. JSON-object mode is not
provider-native strict JSON-Schema constrained decoding: the schema is supplied
as an instruction, then enforced locally by Pydantic. API authorization is an HTTP
header, never part of this body. The adapter reads final `message.content`, not
provider `reasoning_content`.

[Settings](../src/ai_career_navigator/config.py) default to a 90-second timeout per
attempt and `MAX_RETRIES=2`: at most three attempts per gateway call. Deployment
configuration can override both. A structured-validation failure gets at most one
repair attempt, sharing the same total retry budget with retryable provider errors.
The repair does not resend the raw invalid answer. Authentication and nonretryable
errors stop immediately. Retry delays start at 0.25 seconds and double, capped at
2 seconds. This is a per-call bound, not a 90-second bound on an entire market run
containing multiple model calls. There is no retry-until-positive loop.

Gateway success means routing and output schema passed. It does not mean domain
grounding or semantic accuracy passed; the services below apply those checks next.

## 1. Capability inference

**Entry:** [`profile/inference.py::infer_capabilities`](../src/ai_career_navigator/profile/inference.py).
**Prompt:** [`inference_prompts.py`](../src/ai_career_navigator/profile/inference_prompts.py),
`SYSTEM_PROMPT` and `build_user_prompt`.
**Schema:** [`CapabilityInferenceResult`](../src/ai_career_navigator/profile/inference_schemas.py).

The model has one task: propose additional atomic professional capabilities from
confirmed evidence, leaving them unconfirmed. Empty suggestions are allowed. The
prompt prohibits invented facts, protected-trait inference, career recommendations,
duplicate capabilities, and unsupported maturity upgrades. Professional Summary
comes from About You; it is not collected again on Professional Profile.

The user prompt wraps compact JSON in `confirmed_evidence_data`. Its fields are
`current_role`, `career_stage`, `career_summary`, `core_competencies`, and `evidence`.
Each evidence object contains `evidence_id`, `evidence_type`, `source_reference`,
`capability`, `description`, `maturity`, `context`, `outcome`, and `metric`.
Only approved explicit evidence is selected. Summary and competencies provide
context, not fictitious additional independent supporting records. No contact-data
fields are requested, although free text can still contain personal information.

The schema returns `inferred_capabilities`, `limitations`, and `unresolved_areas`.
Each suggestion includes a capability, description, supporting IDs, proposed
maturity, confidence, brief user-facing `reasoning_summary`, and source-context
summary. Capability names are limited to 80 characters/six words with a generic
vagueness-prefix guard. This is not a guarantee of semantic atomicity.

Before calling, profile approval is required; empty eligible evidence returns an
empty result without a model request. Afterward, unknown/duplicate supporting IDs
are rejected, insufficient-confidence suggestions are filtered, and normalized
duplicates against existing confirmed, pending, or rejected capabilities are
removed. Deduplication is intentionally textual, not semantic similarity.

Validated suggestions become `INFERRED_PENDING` evidence with `approved_by_user`
false. Only the separate user decision can promote them for downstream analysis.
Failures return a typed failed result without replacing or losing the confirmed
profile. Input fields are minimized, but arbitrary profile text and the entire
eligible evidence list do not currently have one global input-token cap.

## 2. Posting requirement extraction

**Entry:** [`market/requirements.py::extract_posting_requirements`](../src/ai_career_navigator/market/requirements.py).
**Prompt:** [`requirement_prompts.py`](../src/ai_career_navigator/market/requirement_prompts.py),
`REQUIREMENT_SYSTEM_PROMPT` and `build_requirement_prompt`.
**Schema:** [`PostingRequirementResult`](../src/ai_career_navigator/market/requirement_schemas.py).

One posting per request is classified into `ROLE_RESPONSIBILITY`,
`HIRING_CAPABILITY`, `PREREQUISITE`, `PREFERENCE`, or
`METADATA_NON_REQUIREMENT`. Duties remain available as role context without
automatically becoming qualifications. Salary, benefits, contract terms, and work
arrangement are not capabilities. The prompt forbids strengthening contribution
into ownership or project experience into production experience.

The exact user-payload keys are `posting_candidate_id`, `source_id`,
`source_reference`, `provider_provenance`, `source_type`, `source_url`,
`source_provenance`, `title`, `title_classification`, `employer`, `location`, and
`untrusted_bounded_posting_text`. Posting text is bounded at 20,000 characters by
the candidate schema. No candidate profile is sent.

The output contains `requirements` and `limitations`. Each extracted item retains
`source_quote`, category, normalized capability, `source_section`,
`qualifier_quotes`, `mandatory`, `preferred`, `years_required`, expected maturity,
confidence, and item type. `relationship` and `capability_options` preserve an
explicit `ANY_OF` expectation as one requirement; independent AND expectations
must be split. A demonstrated allowed alternative can satisfy that expectation.

After schema validation, quote containment, concise names, item classification,
qualifier grounding, and supported OR structure are checked. Explicit exclusions
and unsupported semantic strengthening are guarded deterministically. A failed
posting is recorded with an extraction failure category rather than fabricated
requirements. Ambiguous source text cannot be made unambiguous by schema alone.

The [canonical target profile](../src/ai_career_navigator/market/role_profile.py)
retains posting/source lineage and separate responsibility, qualification, employer,
and posting support counts. Primary exact/accepted-variant hiring evidence defines
the comparison baseline; related titles, scope-context roles, and background
guides cannot silently define it. Representative qualifiers and the source quote
stay together. Employer-specific qualifications remain marked rather than becoming
universal blockers. These are deterministic aggregation rules, not a second
opportunity for the extraction model to invent a role profile.

## 3. Candidate/requirement comparison

**Entry:** [`career/comparison.py::compare_candidate_to_requirements`](../src/ai_career_navigator/career/comparison.py);
individual semantic calls use `_semantic`.
**Prompt:** [`comparison_prompts.py`](../src/ai_career_navigator/career/comparison_prompts.py),
`SYSTEM_PROMPT` and `build_transferability_prompt`.
**Schema:** [`TransferabilityAssessment`](../src/ai_career_navigator/career/comparison_schemas.py).

One requirement is compared with a bounded approved-evidence shortlist, assessing
function, ownership, scope, maturity, production context, and outcome. The choices
are direct, transferable, partial, no confirmed match, or `null` for unresolved
evidence. Transferability is not the default positive answer. Shared vocabulary
does not prove ownership, and unknown is not confirmed inability.

The `requirement` object contains `requirement_id`, `text`, `normalized_capability`,
`category`, `years_required`, `expected_maturity`, `mandatory`, `preferred`,
`employer_specific`, `source_section`, `qualifier_quotes`, `relationship`, and
`capability_options`. `candidate_evidence` contains `evidence_id`, `capability`,
`description`, `maturity`, `context`, `outcome`, `metric`, `evidence_type`, and
`source_type`. The selector uses the whole requirement, reserves professional/project
evidence representation, and caps the shortlist at 12 items; selected and omitted
IDs remain inspectable.

The output includes match/dimension fields, supporting evidence IDs, confidence,
brief explanation, remaining difference, partial subtype, `evidence_status`,
`clarification_needed`, `evidence_quotes`, and `matched_alternative`. Direct matches
require verbatim excerpts with evidence IDs; confirmed-unmet/contradicted claims
also require excerpts. Unknown requires a specific clarification. Excerpts must
come from supplied evidence content, not merely its capability label.

Postvalidation checks IDs, excerpts, alternatives, and contradictory dimensions.
Material unknown ownership/scope/production/outcome cannot be silently counted as
aligned. Relevant-year requirements cannot be satisfied from general tenure alone.
Semantic direct matches are allowed when actual evidence supports them. A small
deterministic fast path remains for simple, affirmative, explicitly used technical
skills; substantive name equality is not a direct-match shortcut.

The in-memory semantic cache includes prompt version, comparison scope, full
requirement content/qualifiers, and selected evidence content. Domain failures
produce unknown/operation-failed records, not automatic capability deficits.
[Gap derivation](../src/ai_career_navigator/career/gap_analysis.py) preserves unknown
versus confirmed-unmet status, mandatory/preferred status, and employer specificity.
Unknown prerequisites do not become hard blockers; preferred-only gaps are not
treated as universal mandatory skill gaps. These records feed synthesis and plan.

## 4. Career assessment synthesis

**Entry:** [`career/synthesis.py::synthesize_career_assessment`](../src/ai_career_navigator/career/synthesis.py).
**Prompt:** [`synthesis_prompts.py`](../src/ai_career_navigator/career/synthesis_prompts.py),
`SYSTEM_PROMPT` and `build_synthesis_prompt`.
**Schema:** [`CareerSynthesisDraft`](../src/ai_career_navigator/career/synthesis_schemas.py);
the final domain result is `CareerAssessmentSynthesis`.

The model groups and explains existing comparison evidence. It does not decide
accessibility, severity, confidence, counts, new requirements, or timelines.

`_payload` sends `target_role`, a `candidate_summary` containing current role and
career stage, validated `comparisons`, referenced approved `evidence`, and material
`gaps`. Comparison records retain IDs, requirement name/category/frequency, match,
maturity, all dimensions, uncertainty/clarification, alternative/partial subtype,
remaining difference, confidence, and supporting IDs. Evidence is limited to IDs,
capability, description, maturity, and context. Gap records retain raw IDs,
requirements, type/dimensions/severity, uncertainty, frequency, mandatory/preferred
flags, target expectation, residual difference, evidence IDs, and evidence needed.
Full postings and the complete profile are not resent.

The draft returns strongest advantages, transferable strengths, grouped gaps,
assessment summary, and limitations. There is no minimum strength/gap quota.
Each material raw gap must appear exactly once in grouping; comparison/evidence
references and strength/group semantics are validated. Demonstrated strengths and
target alignments remain deterministically recoverable rather than disappearing
when model grouping fails.

Accessibility uses primary comparison coverage, match mix, material residual
severity/dimensions, prerequisites, ownership/maturity/scope, employer specificity,
and evidence confidence, not the number of grouped cards. Unknown evidence is not
an invented deficit. Source confidence can qualify a credible verdict without
mechanically converting every low-confidence source sample into a distant target;
overall assessment confidence is capped by the canonical target-role profile's
confidence, even when the broad retrieval snapshot and individual comparisons are
high-confidence. The cap is independent of match mix and does not itself downgrade
candidate accessibility. Insufficient actual comparisons still stop assessment. Validated synthesis is the
shared source of truth for Analysis and Plan. Invalid/unavailable model wording
uses a disclosed deterministic synthesis fallback, not demonstration data.

## 5. Career-plan refinement

**Entry:** [`career/plan.py::generate_career_plan`](../src/ai_career_navigator/career/plan.py);
the optional model call is `_apply_model_wording`.
**Prompt:** [`plan_prompts.py`](../src/ai_career_navigator/career/plan_prompts.py),
`SYSTEM_PROMPT` and `build_plan_prompt`.
**Schema:** [`CareerPlanDraftOutput`](../src/ai_career_navigator/career/plan_schemas.py).

Deterministic logic first constructs the route and milestones from validated
synthesis, actual gaps, eligible bridge assessments, goal preferences, and timeline
assessment. The model's task is close grammatical refinement, not career planning
from scratch. Direct-fit application actions need not become upskilling. No fixed
timeline is valid and does not become a missing timeline or invented duration.

The payload contains `target_role`, supported `bridge_roles`, `milestones`, `risks`,
and `assumptions`. Each milestone contains `milestone_key`, `phase`,
`milestone_type`, `action`, `linked_gap_ids`, `measurable_outcome`,
`evidence_to_create`, and `dependencies`. Raw profile/posting content is omitted;
dates are not editable model inputs.

Only `action` and `measurable_outcome` wording may change. Validation preserves
target/bridges, milestone identity/count, phase/type, gap IDs, artifacts,
dependencies, risks, and assumptions. Conservative wording-token and polarity
checks reject added/removed factual content, obligations, negation, or unsupported
credentials/advice. Traceability validates gap/dependency references and timeline
bounds. Rejected wording falls back to the already valid deterministic skeleton.
The model has no authority to add gaps, bridge roles, certifications, or timelines.

## Inspecting what was actually sent

Set `MODEL_INSPECTOR_ENABLED=true` in local configuration and construct a new
gateway (restart the application when using cached settings). It defaults to
`false`. [`LocalModelInspector`](../src/ai_career_navigator/models/inspection.py)
is opt-in, in-memory, process-local inspection, **not external telemetry**.

Read `gateway.inspector.events` for the current gateway. There is no automatic
export or upload and no implied production UI download control. A developer may
explicitly export these events for an authorized review; delete that export after
review. The inspector itself does not automatically delete an exported file.

For NVIDIA, each request event uses the same `build_nvidia_payload` as the adapter,
with role, configured model, schema, metadata, attempt, timeout, and retry budget.
This is the effective credential-free body, subject to redaction/content limits,
not a reconstructed generic prompt. Events also include schema-validated final
structured output or rejection category. Invalid raw model answers are not
recorded. Comparison domain-validation events add selected/omitted evidence IDs,
final match/status, grounded-quote count, and transformation notes. A
`SCHEMA_VALIDATED` gateway event alone is not a domain-validation success.

The recorder excludes credential/private-reasoning keys, redacts configured
secrets, common token patterns and email addresses, and removes balanced private
thinking blocks. It never intentionally records provider reasoning traces. It
retains at most 100 events and truncates individual strings beyond 200,000
characters with an explicit incomplete-content marker; older events are evicted.
Exports can therefore be incomplete. Redaction is not full anonymization: prompts
and validated answers can still contain **career-sensitive information**, names,
organizations, and free-text facts. Review and minimize them before any sharing.

## Lineage and remaining limits

The accountable path is posting/source provenance → classified source quote →
canonical qualification → selected candidate evidence → dimensional comparison →
residual/unknown gap → synthesis/accessibility → traceable plan action. Duties and
background context remain distinguishable from hiring qualifications throughout.
UI summaries must consume the same validated domain objects, not reclassify prose.

Schema validity, real IDs, and exact quotes are necessary but not sufficient for
semantic truth. A quoted responsibility can still be misinterpreted, an alias guard
can miss a paraphrase, bounded ranking can omit the best evidence, and a grammatical
rewrite can subtly change emphasis. Inference deduplication is not comprehensive
semantic duplicate detection. Synthesis cannot repair a poorly sampled baseline.
None of these contracts establish posting freshness, representative market totals,
or live model accuracy on their own.

Regression coverage includes
[comparison reliability](../tests/career/test_comparison_reliability.py),
[gap analysis](../tests/career/test_gap_analysis.py),
[synthesis](../tests/career/test_synthesis.py),
[plan](../tests/career/test_plan_generation.py), and
[inspector contracts](../tests/models/test_inspection.py).
Frozen expected/actual evaluations and bounded authorized live checks remain
necessary; passing stub/schema tests must not be reported as live semantic success.

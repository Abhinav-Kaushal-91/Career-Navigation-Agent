# Transition interpretation V2 — implementation and live comparison

September 11, 2026. User authorized four interpretation fixes, not retrieval changes
or a forced positive career verdict.

## Code changes

- `career/transition.py`: version `career-transition-assessment-v2`; author instructions
  preserve general capabilities, split different evidence levels, consistently clarify
  unknown experience and select a coherent direction before planning.
- Transition-specific critical review checks the same four points, including whether
  the reviewer itself introduces a strength downgrade. It replaces the ambiguous shared
  reviewer instruction that allowed a bundled item to remain partial.
- `career/same_role.py`: accepts a review-instructions parameter; the default review
  text and same-role behavior are unchanged.
- No schema expansion, new hard gates, title-specific classification rules, forced
  transfer labels, model/configuration changes or approval changes.
- Regression tests cover review dispatch, unchanged same-role review, separated base and
  specialist findings, and preservation of conditional plan actions. These fixtures test
  contracts, not a guarantee of live model semantics.

## Controlled live rerun

Baseline: `outputs/local-descriptions/20260911T164139Z/results.json`.
New run: `outputs/local-descriptions/20260911T171131Z/results.json`.

All five job-description SHA-256 hashes match. Same synthetic Senior Java Developer
profile, ROLE_TRANSITION → AI Engineer, location Toronto, no fixed timeline, same
Fireworks DeepSeek model. All five descriptions were sent together. No discovery calls,
browser interaction, inferred-strength approval or plan approval.

| Measure | Previous | V2 |
|---|---|---|
| Model verdict | ASPIRATIONAL / HIGH | NEAR_TERM_TARGET / MODERATE |
| Runtime | 256.26 s | 189.65 s |
| Model calls | 2 | 2 |
| Competencies | 20 | 20 |
| Demonstrated / partial / unconfirmed | 3 / 5 / 12 | 8 / 0 / 12 |
| TRANSFERABLE labels | 0 | 0 |
| Main strengths | 8 | 5 (other strengths also appear in competency rows) |
| Plan actions | 6 | 6 |
| Processing/reference issues | 0 | 0 |

The verdict change was model-generated, not forced in code. It now assesses AI application
engineering as a development destination, while treating agentic, platform and lead roles
separately. NEAR_TERM_TARGET is not a duration promise or evidence that the candidate is
ready to apply to the five jobs immediately. Four jobs remain STRETCH; the Definity lead
role is DIFFERENT_DIRECTION.

## Four requested corrections: observed outcome

| Check | Observed V2 behavior | Assessment |
|---|---|---|
| Preserve the base skill | Backend/REST remains demonstrated; base AWS/cloud remains demonstrated while AI cloud services are unconfirmed | Improved; Azure API Management itself is omitted rather than explicitly retained separately |
| Split mixed evidence | Docker/Kubernetes, mentoring/leadership, operations/observability are separate rows | Improved structure; Docker production attribution remains wrong |
| Unknown is not absent | All 12 unconfirmed competencies use CLARIFY; Python and LLM learning actions are conditional | Improved; some development-focus sentences condition only on role choice, not confirmation of absence |
| One coherent direction | Plan focuses on AI application development rather than adding feature stores, fraud experience and platform leadership to every route | Improved; application action could state remaining employer-specific prerequisites more explicitly |

## Actual revised plan (condensed)

1. Confirm existing Python and AI/LLM exposure.
2. If Python is absent, build a tested Python backend/API service.
3. If LLM/GenAI experience is absent, learn prompts, retrieval and orchestration.
4. Build and deploy a tested GenAI application using Docker and CI/CD.
5. Document the project and accurate existing backend/cloud/operations examples.
6. Pursue matching application-engineering roles once the relevant capability is demonstrated.

No invented dates, required certification, automatic plan approval or claim that a
portfolio project satisfies a multi-year professional prerequisite.

## Residual semantic issues

The model says Docker packaging is shown in production and the project. The supplied
employment evidence says only **containerized services**; Docker is named in the personal
project. Docker may receive demonstrated project credit, but production Docker is not
established. The final review still failed this attribution check despite explicit rules.

The base-cloud row label lists AWS/Azure/GCP while only AWS is supported; its reason correctly
limits the evidence to AWS, but the label can mislead. Data modeling/SQL is still broad.
Some employer-specific conditions are omitted from the compact output. Passing source-ID
validation does not certify these semantic claims. Do not present the result as fully corrected.

## Verification

- 369 tests passed across career, orchestration, UI and local-description diagnostic tests.
- Ruff passed on changed Python files.
- Actual saved V2 output rendered via native Streamlit AppTest: 20 Analysis rows, six
  Plan milestones, zero exceptions, Plan DRAFT. No manual browser visual QA performed.
- Initial model: 77.65 s, 11,296 input / 9,972 provider-reported output tokens.
- Review model: 111.85 s, 15,445 input / 19,608 provider-reported output tokens.
- Both finished with `stop`, not token-limit truncation. No reference repair required.
- Speed improvement is one observed run, not a latency guarantee.

Sanitized requests and final responses are alongside results as `model-01.json` and
`model-02.json`. Existing saved website results are not rewritten; new analysis runs use V2.

## Unchanged-rules repeat — 20260911T171815Z

User requested a second V2 run to check whether the result holds. No code, prompt,
provider settings or source files were changed. The first-call system prompt and user
payload match the prior V2 call exactly (case-sensitive string comparison); the five
file hashes, model and goal mode also match. This is stronger evidence of repeatability
than simply reusing the same filenames.

| Measure | First V2 run | Repeat V2 run |
|---|---|---|
| Accessibility | NEAR_TERM_TARGET | ASPIRATIONAL |
| Confidence | MODERATE | MODERATE |
| Duration | 189.65 s | 229.34 s |
| Calls | 2 | 2 |
| Competencies | 20 | 18 |
| Demonstrated / transferable / unconfirmed | 8 / 0 / 12 | 7 / 1 / 10 |
| Strengths / plan actions | 5 / 6 | 6 / 6 |
| Processing/reference issues | 0 | 0 |

The review retained the changed ASPIRATIONAL verdict. The prior result interpreted the
missing AI layer as buildable on a credible backend foundation; the repeat interpreted
Python, AI/LLM and MLOps as multiple major functional barriers. Both selected applied
GenAI/LLM engineering as the nearest direction. The model's boundary between near-term
and aspirational is therefore not stable on this case. This is not a connection,
description-availability or schema failure, nor proof that either enum alone is correct.

What held: backend/REST and AWS remain demonstrated; mentoring is separate from leadership;
all 11 outstanding needs use CLARIFY; the plan first checks existing experience, then
conditionally develops Python/LLM work, builds a project, seeks real team/production AI
experience and prepares targeted applications. Insurance preference remains optional;
the fraud/lead role remains a distinct direction with a professional prerequisite.

What did not hold: Docker is still incorrectly attributed to production employment;
the model now bundles CI/CD with Docker and MLOps with Kubernetes. The technical
communication-to-business-translation transfer is tentative and explicitly requires
clarification. Row structure and evidence interpretation still vary despite identical inputs.

Repeat verification: actual saved Analysis rendered 18 rows, Plan six milestones,
zero AppTest exceptions. Plan is DRAFT; no browser interaction or approval. No code fixes
were applied during this rerun. Full regression suite was not repeated because no code changed.

Timing: initial call 106.14 s (11,296 input / 9,557 provider-reported output tokens);
review 123.04 s (15,680 / 16,104). Both finished with `stop`, not token truncation.
Artifacts: `outputs/local-descriptions/20260911T171815Z/results.json`, plus model-01.json
and model-02.json in that folder. No provider secrets or private reasoning traces retained.

Conclusion: the workflow runs and generates a usable draft, but the readiness verdict
and attribution are not yet repeatably reliable. Do not claim the interpretation errors
are fully fixed based on the first favorable rerun.

# Transition V3 — implementation and actual DeepSeek result

September 11, 2026. **Workflow execution passed; semantic acceptance did not.**

## Implementation

Replaced the transition V2 author/reviewer prompts with a role-neutral practical
assessment contract in `career/transition_prompts.py`, rule version
`career-transition-assessment-v3`. `TransitionReply` schema descriptions distinguish
current readiness (`rationale`) from credible direction (`role_picture`). No new
persisted fields or enum values were added. Existing Analysis and Plan consume the
same validated assessment; no website redesign or deployment was performed.

Added supervised-practice and jurisdiction/task-specific authorization safeguards.
Existing source/ID checks, bounded repair/review, 30k output ceiling, same-role rules,
retrieval and exact-version plan approval were preserved. This implements the
proposal's principles in the existing contract, not its optional Markdown format.
Prompt-design guidance informed explicit boundaries and contrasting examples;
model compliance is judged from the actual run below, not prompt presence alone.

## Fixed live case

- Same synthetic Senior Java Developer profile: eight years, production backend
  work, personal Docker project; no AI/Python work supplied.
- Goal: ROLE_TRANSITION, AI Engineer, Toronto metro, no fixed timeline.
- Same five saved AI Engineer descriptions; their SHA256 values match the prior
  V2 run `20260911T171815Z` exactly. Four independent employers.
- Model: `accounts/fireworks/models/deepseek-v4p1-flash`, through Fireworks.
- Source acquisition injected at the local-file retrieval boundary; the production
  transition graph then ran normally. No Adzuna/You.com calls or new AI-strength
  inference, no invented job descriptions, and no auto-approval of inferred strengths.
- Assessment and final-review requests used temperature 0 and max_tokens 30000.
- During the run, one prompt line was wrapped for lint; text/meaning did not change.
  The archived requests retain the exact in-process prompt sent to the provider.

Artifacts: `outputs/local-descriptions/20260911T180320Z/`.

| Stage | Seconds | Input tokens | Output tokens | Finish |
| --- | ---: | ---: | ---: | --- |
| Initial assessment | 97.49 | 11,463 | 10,290 | stop |
| Critical review | 117.06 | 16,633 | 12,057 | stop |
| Complete graph run | 214.69 | — | — | Draft plan produced |

Two model calls; no integrity repair needed. Reported output tokens are provider
usage, not a count of user-visible prose. Both calls finished below the output ceiling.

## Actual final assessment and plan

- Accessibility: **NEAR_TERM_TARGET**; confidence: **MODERATE**.
- Narrative explicitly says current readiness for the supplied AI roles is not
  established, while the adjacent direction is AI application/platform engineering.
- Seven named strengths: backend delivery; REST integration; SQL optimization;
  AWS/CI/CD; automated testing; incident support; mentoring/review.
- 20 competencies: 9 demonstrated, 3 partial, 8 not established; no transferable
  labels. No quota was imposed for transferable labels.
- Remaining needs: 9 NONE, 7 LEARN, 3 BUILD_EXPERIENCE, 1 CLARIFY.
- Six ordered draft actions: Python service; RAG application/evaluation; agent
  workflow; interview examples; selective applications; reassessment.
- Plan: DEVELOPMENT, DRAFT, no fixed timeline. It was not approved or saved as an
  approved plan. Session-only UI saving semantics remain unchanged.
- Zero processing/reference issues. This establishes contract execution, not the
  truth of every conclusion or the correctness of the plan.

## What improved or worked

1. Current readiness and developmental direction are stated separately, despite
   remaining narrative quality problems.
2. Existing backend, REST, cloud, testing and mentoring strengths remain visible.
3. Reviewer removed an Azure-specific citation from the AWS row.
4. Reviewer correctly moved some testing/mentoring duties out of qualifications.
5. Reviewer recognized broadly shared GenAI work rather than treating it all as
   isolated specialist context, and corrected the draft's Mississauga mismatch claim.
6. Actual saved state rendered through both production Analysis and Plan with
   Streamlit AppTest: 20 rows, six milestones, no exceptions. This was not manual
   browser-level visual QA.

## Material deviations still present

| Finding | Evidence from this run | Assessment |
| --- | --- | --- |
| General experience became AI tenure | Final rationale says the postings require roughly 5-8 years of AI delivery | Incorrect: Tangerine accepts broad Software/Data/ML/AI engineering tenure; Definity Lead has broad technology tenure plus a separate specialist condition. Orion's agent/autonomous-system ask must stay scoped. |
| Missing information became a learning deficit | Seven NOT_ESTABLISHED rows use LEARN, and three items use BUILD_EXPERIENCE without explicit absence/depth evidence | Violates the new unknown/absent distinction; Python/AI questions coexist with unconditional learning steps. |
| Docker context remains blurred | Rationale lists Docker with the production foundation; Docker row combines generic employment containers with explicit project Docker | Professional Docker is not established by those sources. |
| Base-capability bundles overreach | SQL optimization supports a fully demonstrated data-modelling/SQL row; incident support supports a broader monitoring/operations row | Direct support for one component cannot establish the whole bundle. |
| Scope and plan still too broad | Application/platform language mixes directions; six actions despite a prompt preference for up to five | Schema still permits six. The plan is not the single focused, conditional sequence requested. |
| Review claim contradicts final text | Reviewer says it completed role_picture; final field is exactly 1000 characters and ends mid-sentence | Both raw provider content and saved result contain incomplete text. Finish=stop and schema validity do not establish sentence completeness. |
| IDs leak into display copy | P1L18, P3, E1 and similar aliases appear in narrative/reasons | Prompt instruction did not prevent user-facing reference noise. |
| Education data lost before model | Profile has field_of_study=Computer Science, but payload E3 only says Bachelor of Science | Input-builder issue: approved evidence stores the field in `capability`, which the shared payload omits. The resulting degree-field question is not solely a model failure. |

These errors are retained in the raw artifacts. They were not rewritten into a
better answer or silently replaced by the assistant's independent assessment.
The input omission is diagnosed here but was not patched during this fixed-input run.

## Verification

- Focused tests: 35 passed (included in the broader total, not additive).
- Career, orchestration, UI and local-description tests: **372 passed**, 19.46 seconds.
- Ruff: changed Python files passed.
- Actual saved-result Analysis/Plan AppTest: passed.
- Existing same-role fixture emitted enum-serialization warnings. Initial run also
  encountered a pytest cache write warning; broader run disabled cacheprovider.
- The live graph emitted future checkpoint-type registration warnings, not failures.

## Decision

The requested implementation is in the local codebase and the live backend case
completed. **Do not describe this as a semantically validated release.**
The result supports the broad career direction but still fails important evidence
interpretation and plan conditions. A next correction should preserve omitted
approved evidence fields and measure targeted semantic errors, not keep appending
role-specific exceptions or force the desired accessibility enum. One successful
execution also does not resolve the repeatability issue observed in V2.

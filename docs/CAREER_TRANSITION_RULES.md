# Career-transition rules — September 11, 2026

Applies to the approved **Explore a career transition** goal (`ROLE_TRANSITION`).
No AI Engineer, Product Manager or other profession-specific verdict rules.

## V3 — practical assessment and cross-profession safeguards

`career-transition-assessment-v3` replaces the V2 author/reviewer prompts with the
role-neutral proposal in CAREER_ASSESSMENT_PROMPT_PROPOSAL.md, adapted to the existing
JSON contract. The original proposal remains an archived draft, not a runtime file.

- `rationale` explicitly describes current readiness for the supplied opportunities.
- `role_picture` describes a credible transition direction and differences among roles.
- The existing accessibility enum is interpreted for that direction: NEAR_TERM_TARGET
  is a development category, not a promised duration or permission to apply now.
  ASPIRATIONAL requires material changes in the selected direction, not an unknown-row count.
- Shared work, specialist conditions and independent-employer support remain distinct.
- Preserve demonstrated foundations and separate professional, supervised, project and
  specialist context. Contrast examples address project-tool attribution and ownership.
- A real trainee opportunity can be pursued on its entry conditions, not full occupational
  mastery. Hypothetical entry routes must not be presented as discovered vacancies.
- Hazardous/safety-critical practice requires appropriate supervision and assessment;
  a personal project does not authorize regulated work.
- Distinguish employer requirements, optional credentials and verified jurisdiction/task
  authorization. Missing authoritative information calls for a precise verification step,
  not an invented legal barrier or assumed eligibility.
- Prefer up to five focused actions, with conditional development after material unknowns.

`career/transition_prompts.py` owns these prompts; `career/transition.py` retains typed
schemas and validation. The schema descriptions reinforce the two existing narrative
fields without adding new fields or changing persisted data. Existing enum values,
same-role prompts, retrieval, alias validation, bounded repair/review, 30k output limit,
graph routing and exact-version plan approval remain unchanged.

Contract/regression tests confirm wiring and preservation, not semantic model compliance.
The controlled DeepSeek rerun and its actual findings are documented separately.

## Historical V2 interpretation correction

`career-transition-assessment-v2` replaces four ambiguous interpretation instructions:

- Preserve a demonstrated base capability; assess vendor/domain/depth specializations separately.
- Split independently demonstrable skills when evidence differs; retain project credit without
  claiming production experience. Do not use a combined partial row to conceal different support.
- Apply CLARIFY consistently to missing information. LEARN/BUILD_EXPERIENCE needs explicit
  evidence of absence/limited depth; otherwise any later development action stays conditional.
- Identify the nearest credible sampled work direction before writing a verdict and one focused
  plan. Other senior/lead or niche directions remain separately assessed, not universal barriers.

The transition critical-review prompt checks exactly these issues and checks its own edits for
new strength downgrades. It replaces, rather than appends to, the shared review's ambiguous
"split or mark partial" instruction. Same-role review instructions remain byte-for-byte unchanged.
No new evidence gates, forced TRANSFERABLE count, positive verdict or confidence reduction.
Retrieval, response schemas, bounded retries and exact-version plan approval are unchanged.

1. Read up to five relevant, substantive descriptions together with approved
   candidate evidence and goal preferences. Keep common, specialist and optional asks separate.
2. Preserve demonstrated prior-career strengths. Current career tenure is not
   automatically target-role tenure; projects are not professional production work.
3. Compare meaningful capabilities: demonstrated, transferable, partial,
   not established, or context only. A transfer needs evidence and an explicit boundary.
4. Separate remaining needs: clarify information, learn a new capability, or build
   experience/depth. Missing text alone is a question, not a proven deficiency.
5. Assess accessibility from relevant strengths and material barriers, not a keyword
   ratio or fixed grouped-gap count. A change of title does not imply aspirational.
6. Keep employer-specific conditions attached to their actual role direction.
   Duties are not automatically qualifications; an OR does not require both alternatives.
7. Produce ordered, competency-linked actions with observable completion checks.
   No invented credentials, bridge roles, deadlines or claims of prior work.
8. Critically review the full response. Validate schema, source/evidence references,
   transfer boundaries and action bases; unresolved integrity errors stop plan creation.

## Implementation boundary

`career/transition.py` owns the prompt and typed transition response. It shares
bounded selection, alias generation, one optional reference repair, a final model
review and plan construction with the same-role runner. Code attaches real IDs and
provenance; it does not re-score the model with the old canonical gap thresholds.
Requests use the configured REASONING model, temperature 0 and a 30,000-output-token
ceiling. Normal execution uses two calls; reference repair can add one call.

Production graph state has a separate `transition_assessment`. Analysis and Plan
use that same validated object; plan approval remains tied to the exact plan version.
Profile/goal/market revisions clear dependent assessment and plan state.
Same-role prompts remain unchanged. Other goal types retain their existing path.

## Verification and limits

Automated tests exercise schema/reference checks, generic routing, production graph
integration, safe stopping, approval/invalidation and native Streamlit rendering.
Model responses in these tests are controlled fixtures, **not live model results**.
Prompt requirements alone cannot guarantee semantic accuracy: project-to-production
overclaims, transfer boundaries and cross-employer leakage still require a live
career-transition evaluation on the chosen profile and relevant target descriptions.
Initial V1 implementation was verified without provider calls; the subsequent V1 live test
and its semantic issues are documented in AI_ENGINEER_TRANSITION_LIVE_TEST.md.

Verification: 783 tests passed across career, orchestration, UI, market and the local
description runner in 29.09 seconds. Ruff passed for changed Python files. One existing
same-role fixture emitted an enum-serialization warning. Native UI checks use AppTest;
manual browser-level visual QA was not performed. See the live-test report for model quality.

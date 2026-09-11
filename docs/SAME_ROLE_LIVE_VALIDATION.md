# Same-role assessment implementation and live GLM validation

## Scope

Production route: Current market analysis with the same current and target role
(case/whitespace insensitive). Generic across professions; no Java/employer-specific
scoring exceptions. Career-transition goals and different-role goals retain their
existing route. Aliased same-role goal titles are not automatically routed yet.

The new path replaces legacy batch extraction, per-requirement comparison and
accessibility thresholds for this scope. It uses one consolidated GLM assessment,
one critical GLM review, and small structure/reference checks. There is at most one
reference-repair request before review. A failed review stops plan generation; it
never substitutes the old result or demo output.

## Rules

1. Read up to five relevant descriptions together; judge actual work, not titles alone.
2. Separate common capabilities, specialist asks and optional advantages.
3. Compare professional capabilities rather than calculate keyword coverage.
4. Demonstrated / partially demonstrated / not established / not relevant.
5. Select accessibility through a justified assessment, not matched-item thresholds.
6. Derive ordered plan actions from assessed capabilities; preserve no-fixed-timeline.
7. Use code-attached short source aliases, check references and require grounded action bases.
8. Present one assessment, competency table, opportunity directions and action plan.

Additional prompt clarification distinguishes duties from prior qualifications,
projects from production, generic containers from Docker production, and automated
testing from TDD. No personality score, invented credential, bridge role or timeline.
Exact-version plan review and dependency invalidation are preserved.

## Actual live runs (Fireworks GLM-5p3-flash)

Inputs: the saved synthetic Senior Java Developer profile, Toronto target,
four relevant supplied descriptions (Kaseya, Tactable, BMO, LTIMindtree).
The fifth supplied description, Impro.AI, remains outside the Java target.
These are actual hosted model calls through the production graph, not mocked
responses. Retrieval alone was injected from local descriptions: no live Adzuna
or You.com calls and no claim to have verified active vacancies.

| Artifact directory under outputs/local-descriptions | Calls | Total | Finding |
| --- | ---: | ---: | --- |
| 20260911T032902Z | 1 | 41.86 s | Apply selectively; preference labels and completion checks wrong |
| 20260911T033212Z | 1 | 43.03 s | Improved obligations/checks; bundled production claims still overstated |
| 20260911T033358Z | 2 | 87.84 s | Assessment + critical review; usable output but not quality acceptance |

Last run: APPLY_SELECTIVELY, MODERATE confidence, 13 competency comparisons,
four opportunity assessments, four ordered plan actions, zero reference issues.
The plan is DRAFT, waiting for human review. It was not approved in the live run.
Initial response 51.04 s; review 36.69 s. Earlier legacy run was 547.30 s/15 calls.

## Remaining semantic failures — not candidate deficits

- GLM still labels a combined AWS/Docker/CI-CD production capability demonstrated;
  employment names generic containers, while Docker is explicit only in the project.
- It downgrades broadly demonstrated automated testing because BMO separately asks
  for TDD. This improperly lets an employer-specific practice weaken a common strength.
- It claims BMO's salary ceiling is below the other postings although LTIMindtree's
  ceiling is lower. This is wrong even within the supplied sample.
- Java/SQL prior qualifications are labeled WORK_ALIGNMENT in the reviewed result.
- The rationale says central duties at all employers are satisfied despite recognizing
  material specialist unknowns. Several plan actions still encourage applications
  before clearly resolving employer prerequisites. The Karat prerequisite is in prose,
  not a separately auditable competency row.

The second model pass is not an independent guarantee of correctness. No reference
errors does not mean no factual errors. Do not call this a full quality sign-off or
claim that changing prompts alone has solved model reliability. Compare additional
same-role fixtures and semantic expected outcomes before expanding to transitions.

## Verification

Regression tests cover generic routing, full text/short aliases, project deduplication,
mandatory wording, reference repair, safe stop, linked plans, timeline preservation,
invalidation, production graph bypass of old rules, exact-version approval and native
Analysis/Plan rendering. Saved-run rendering is read-only and makes no model calls.
Only cited source lines (not the entire JD corpus) are retained in assessment state.
Production run audit export was added after the final live call; covered by graph tests.

Verification: 770 tests passed across career, orchestration, UI, market and local-import
tests; changed Python files pass Ruff. The actual final saved state rendered through
both production page functions in Streamlit AppTest with zero exceptions (13 rows,
four plan steps). Saved-result server: http://127.0.0.1:8530/; health returned `ok`.
This is a read-only view of real GLM output, not a new retrieval run or approval.
No manual browser visual inspection was performed in this implementation pass.

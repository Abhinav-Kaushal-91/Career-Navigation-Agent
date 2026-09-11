# UI overhaul verification — September 10, 2026

## Reference and scope

Reviewed the user's Career Navigator redesign (1).zip and its native Streamlit
handoff spec, plus Home, Analysis and Plan reference screenshots. Later user
instructions take precedence: merged Market/Analysis, short competency statuses,
no repetitive per-item evidence, and no unsupported scores or invented routes.

This pass changes presentation, not extraction prompts, comparison policy or
accessibility thresholds. Existing dirty backend changes were preserved.

## Automated verification

- 318 passed: tests/ui, tests/career, tests/orchestration/test_plan_review.py.
- Scoped Ruff checks pass for changed production UI files, app entry point,
  browser QA harness and changed UI tests.
- Regression checks preserve unknown/partial/transferable distinctions, safe
  stopping, plan approval gating, no-fixed-timeline handling and source objects.
- Added a check for one Plan action sequence and one session-persistence notice.

## Manual browser inspection

Used the actual native browser, not only Streamlit AppTest. Screenshots were
inspected in the task. Production preview: port 8520. Isolated replay: port 8521.

| Surface / saved case | Observed result |
| --- | --- |
| Production Home, 1280px | Compact title, four aligned cards, all bottom content visible. |
| Production demo Education, 1280px | Prefill retained; long progress labels initially clipped. Short labels now fit; full names remain tooltips. No AI review triggered. |
| CURRENT-A assessment, 1280px | Apply now / High, three Yes rows, compact next-step/sample cards, no per-row evidence paragraphs. |
| TARGET-A assessment, 1280px | Low confidence / Limited role sample remains visible next to the verdict. |
| REASSESS-A safe stop | No usable employer requirements; confirmed Learning Design strength retained; Continue to Plan disabled. |
| CURRENT-A Plan, 1280px, top and footer | One untimed action, route and strengths sidebar, reachable version-specific Approve/Draft/Reject/Cancel controls. No approval submitted. |
| Goal selection, narrow browser panel (~319px) | Cards stack and buttons remain inside each card; all six intents exist in the accessibility tree. |
| Goal selection, 1280px | Three equal-width cards per row; matching heights and aligned buttons, including the longest first-card description. |

## Limitations / product status

- Saved cases are frozen synthetic replays, not proof of current provider quality.
- No new Adzuna, You.com, GLM or Nemotron request was sent.
- Existing live sessions were not stopped or overwritten. A new production server
  was started so the revised theme is loaded from startup.
- The UI is ready for manual review. Extraction completeness, responsibility vs
  qualification classification and a successful live end-to-end run still need
  independent acceptance; this pass does not claim those problems are solved.

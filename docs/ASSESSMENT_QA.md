# Combined assessment QA — September 9, 2026

## Scope and method

Production routing plus isolated `scripts/v1_browser_qa.py` on localhost:8516.
The user's localhost:8515 session was not navigated, reset or rerun. No external
requests, model calls, job applications or plan approvals. All cases below use
labelled frozen synthetic graph states, not live provider-quality evidence.

840 automated tests passed. New tests cover expectation IDs/complete coverage,
unknown IDs, duplicates, missing IDs, mixing preference/duty/eligibility/scope,
unsubstantiated people management, invalid-output fallback, source immutability,
candidate-free market inputs, self-reported context, and section preservation.
UI tests cover merged routing, absence of legacy charts/counters, source details,
preserved strengths and plan safe-stop behavior.

## Manual browser observations

| Replay | Observed behavior |
| --- | --- |
| CURRENT-A | Senior Java Developer; Apply now and confidence retained from existing synthesis; Java/API Integration/Automated Testing source expectations beside direct comparisons; source expanders; one Career assessment sidebar item. Continue to Plan opened the production Plan renderer, preserving the untimed roadmap and session-only approval warning. No approval clicked. |
| TARGET-A | Senior Python Developer; provisional notice and low confidence visible; Python/SQL/testing expectations retained; no title-mix/frequency/pie graphics; both scope caveat and candidate conclusion present. |
| REASSESS-A | Instructional Designer; no validated postings, no unsupported accessibility conclusion, Learning Design profile evidence retained, unknown gaps not shown as zero-gap success; Continue to Plan disabled. |

Accessibility trees and screenshots were inspected in the in-app browser at its
approximately 512px-wide pane. Native sidebar overlays content when open on narrow
screens; the collapse control remains available. Text reflows without a score chart.
Initial inspection found duplicate comparison explanation text; display now suppresses
an identical remaining-difference string. Assessment title reduced to native header.
Plan return label now names Career assessment. Screenshots were inspected inline;
no image archive was written.

## Limits / next acceptance check

After restarting only the isolated QA server, a fresh browser tab at 1280px width
confirmed the final smaller native header, side-by-side employer/candidate card,
expanded source passages and absence of the duplicate explanation. This is a
desktop spot check, not an exhaustive viewport/content-size matrix.

The frozen replays do not exercise a
fresh Nemotron response. New model organization needs an identical-corpus live A/B;
the older saved six-description inventory has not been reconciled to the user's
27-posting portal run. Do not claim improved live extraction/recall based on this QA.

# Five-description production assessment

Implemented September 10, 2026. This replaces per-posting extraction **in the website runtime**;
legacy replay callers retain their previous default service for compatibility.

## Rules now in use

1. Select **up to five**, not necessarily five, nonempty in-scope exact/validated-variant
   descriptions by **descending word count**. There is no minimum character/word threshold,
   keyword-heading gate or retrieval-quality exclusion at selection. Existing title, seniority
   and employer-diversity ordering breaks equal-word-count ties. Related leads remain in
   retrieval/audit. Short excerpts can be selected; length never establishes completeness.
2. Send those descriptions together in **one logical gateway request**, with at most one
   extra indexed repair request for rejected themes. Gateway retries are disabled for both.
   Valid themes are never resent for rewriting. There is no per-posting extraction fallback or
   second hidden variant-extraction loop. Configured lower selection limits are respected.
3. Return consolidated duties, hiring capabilities, prerequisites and preferences. No
   salary/benefits/work-arrangement metadata section. Source quotes/IDs remain internal
   validation inputs, not repeated paragraphs on the assessment page.
4. Judge role importance as Core, Supporting, Additional or Specialist using functional
   relevance and recurrence—not frequency alone. Explicit required/preferred status belongs
   to each source; role importance never manufactures a universal employer requirement.
5. Preserve OR alternatives. A demonstrated alternative satisfies that expectation; the
   table and deterministic strength summary display the matched alternative. A separate
   employer genuinely requiring the other language remains a separate expectation.
6. Compare canonical capabilities against confirmed candidate evidence, not matching labels
   alone. Preserve ownership, scope, maturity and production context. Duties do not become
   prior qualifications, and technical leadership does not imply direct people management.
7. Additional advantages and specialist conditions do not create baseline capability gaps.
   Baseline readiness needs at least two resolved expectations and a strict majority;
   a strict majority of designated Core expectations must also be resolved. Mandatory
   baseline eligibility stays guarded. Unknown information is a question, not inability.
8. Show one verdict, a short role picture, one numbered competency/status table, material
   gaps, separate questions and a next step to Plan. No frequency pies, keyword-count bars,
   per-item dropdowns or repeated supporting-evidence paragraphs in the main surface.

## Validation and confidence

Posting IDs, source quotes, source sections, alternatives and explicit obligations are
checked before canonical construction. Canonical counts/provenance remain code-owned.
Invalid source evidence cannot become a requirement. A lost core/supporting qualification
blocks an overall verdict; a partially supplied description lowers sample confidence without
automatically deleting the other usable evidence. Batch contract failure safely stops without
substituting demo outputs. Fewer than two independent sources with usable primary hiring
evidence remains insufficient; two sources are provisional, and three or more high-quality
sources with complete validated extraction can establish a stable **bounded** role profile.
These are coverage checks, not proof of model semantic correctness or market-wide demand.

Cross-field and grounding failures are isolated by theme. Valid siblings survive, and repairs
must pass the same checks; unknown/duplicate repair indexes are rejected. Structural envelope
or review-identity failures still stop the batch. An explicit extraction processing status
distinguishes failures from a genuinely limited source sample in the UI. All selected inputs
remain auditable; "selected" is not presented as successful analysis after a processing failure.

Candidate comparison still uses a separate narrow task per canonical expectation. This change
does not combine profile, job extraction, accessibility and Plan into one unconstrained call.
The existing synthesis, generic accessibility calibration and version-specific Plan approval
remain downstream owners. No fixed timeline remains untimed.

## Verification / limitations

- 723 Market/career/UI/orchestration tests pass; scoped Ruff checks pass.
- Offline production-service replay: five synthetic descriptions → validated canonical profile
  → candidate comparison → gap/accessibility → synthesis → bridge/timeline → deterministic Plan.
  Four assessed capabilities, Java satisfies Java-or-Python, no VOIP gap, no invented timeline.
- Automated checks cover one batch request, maximum-five word ranking, empty/related exclusions,
  invalid IDs/quotes/alternatives, source lineage, partial-source confidence, core coverage,
  actual website runtime binding and the production Analysis renderer.
- Browser inspected the synthetic Analysis table and Plan view using production renderers;
  Plan approval controls were inspected, not submitted. The desktop viewport screenshot was
  constrained by the app panel, so it is not a full-width pixel-perfect acceptance record.
- **No fresh live GLM/Nemotron run was made in this implementation pass.** Passing synthetic
  tests proves wiring and guards, not response completeness, latency or live semantic quality.
- Existing saved results are not silently recomputed. Start a new live analysis to use the
  batch path. The five-description cap limits extraction/comparison scope, not all retrieval
  or You.com enrichment calls, so it is not a guarantee of total end-to-end runtime.

QA harness: `uv run streamlit run scripts/five_batch_ui_qa.py` (synthetic, no providers).
Production: `uv run streamlit run src/ai_career_navigator/app.py`.

# Date-based professional experience — September 10, 2026

## Implemented behavior

`profile/experience.py` calculates elapsed days from explicit, user-confirmed
employment records. It unions date intervals, so overlapping jobs and duplicate
records do not inflate total tenure and career breaks do not add time. Roles
explicitly marked current use the analysis date, not the date the profile was
saved. Dates in the future cannot add future experience. Missing start/end dates,
or conflicting current/end-date information, produce focused clarification items.
No usable dated history is unknown, not zero years. Partial dated history is a
lower bound, not proof the candidate falls below a hiring threshold.

Education, certifications, portfolio projects and inferred employment do not add
professional years. Same-title role periods have their own overlap-adjusted
tenures. Different titles remain separately visible rather than being silently
declared equivalent. Relevant work still needs supporting responsibilities; a role
title alone does not establish functional fit, ownership or production maturity.

Years are approximate display values (elapsed days / 365.2425, rounded to two
decimals). Elapsed days are the arithmetic source. The calculation does not assign
every technology the entire length of an employment period. Specific technology
duration remains unknown unless supported separately.

## Model and UI integration

- Comparison prompt v8 receives calculated_experience for the approved profile,
  with the analysis date, total and role tenure, source IDs, and unresolved dates.
  It is told to use these calculations instead of guessing or adding overlaps.
- Profile Review displays the calculated duration and an expandable explanation
  with role dates. The existing About You estimate remains explicitly self-reported.
  Confirmed profile fields and historical approvals are not overwritten.
- Explicit model UNKNOWN is no longer promoted to SUPPORTED. A partial comparison
  with a pending clarification remains unknown and retains its grounded evidence.
  Older positive replies that omitted evidence_status and have no question retain
  backward compatibility; explicit UNKNOWN is never treated as an omitted field.
- Synthesis counts clarification-linked insufficient-evidence gaps as unresolved,
  instead of assigning low partial-match weights and calling the target distant.
  Confirmed shortfalls with no unresolved question still remain genuine gaps.

## Verification and limitations

- 374 career/profile/UI tests passed; targeted Ruff checks passed. Pytest's existing
  Windows cache-path warning did not prevent test execution. No fresh live-model
  quality or full end-to-end browser acceptance is claimed.

- Employment from 2018-09-01 through 2026-09-10 calculates approximately 8.02 years.
- Tests cover overlaps, duplicate records, career breaks, current roles recorded
  years earlier, incomplete dates, future dates, excluded non-employment records,
  model payloads, UNKNOWN preservation, confirmed shortfalls and the review screen.
- The saved four-comparison diagnostic now takes the EXPLORATION path rather than
  DEVELOPMENT. This is an incomplete-evidence contract check, not a new live market
  run or proof of full target-role coverage.
- A fresh Streamlit instance was started at http://127.0.0.1:8518/, using the
  configured Fireworks GLM model. Health endpoint returned ok. The older app
  process/session was not stopped. No new live LLM or retrieval call was made.
- Existing saved results are not automatically recomputed; start a new test run.

## Manual checks

1. Open the port-8518 app and choose Explore demo to load sample profile inputs.
2. Proceed to Profile Review and expand How professional experience is calculated.
3. Check the employment dates, approximate total, and separate self-reported value.
4. Add an overlapping role: total elapsed time should not double-count the overlap.
5. Leave a non-current role's end date blank: review should flag the missing date,
   not silently count through today.
6. Run a fresh assessment after confirming the profile and goal. Technology-specific
   uncertainty should appear as a question, not proof that the candidate lacks skill.

Do not infer broad fit or a full development plan from this arithmetic alone.

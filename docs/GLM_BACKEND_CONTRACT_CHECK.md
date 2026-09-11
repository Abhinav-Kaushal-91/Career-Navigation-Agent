# GLM backend contract check — September 9, 2026

## Scope

Production Fireworks streaming adapter and ModelGateway, configured
`accounts/fireworks/models/glm-5p3-flash`, 30,000 output tokens, 600-second request
timeout, no automatic retries. One saved public Cognizant job description plus a
saved Java 8 requirement; synthetic demo evidence only. No Adzuna/You.com calls,
no new vacancy validation, no real candidate data and no private reasoning saved.

This is a bounded instruction/validation test, not a full market assessment or
proof of an end-to-end career plan. The synthetic profile's inferred strengths
were not automatically approved. Existing live-run audits remain unchanged.

## Results and corrections

| Check | Observed result | Assessment |
| --- | --- | --- |
| Extract saved Cognizant JD | 25 statements; valid structured JSON in 130.62 seconds | Model distinguishes duties, qualifications and preferences, but some labels remain compound/broad |
| Process the same answer | Initially 17 retained; 21 after generic validator corrections | Our validation, not just GLM, was dropping useful evidence |
| Optional mentoring | DIRECT_MATCH, preference track; 22.43 seconds | Preserves the optional advantage and quotes the demo's mentoring work |
| Cloud deployment alternatives | DIRECT_MATCH through AWS, work-alignment track; 38.90 seconds | Does not require all cloud alternatives; this was a duty comparison, not a blanket hiring qualification match |
| Six-year Java/Spring Boot expectation | UNKNOWN with a targeted clarification; 47.25 seconds | No automatic match from a Java label; exposed omitted employment dates |
| Specific Java 8 qualifier | PARTIAL_MATCH; 90.58 seconds | General Java experience did not prove Java 8; no evidence was invented |
| Date-inclusive retest | Model recognized 2018-09-01, but joined non-contiguous sentences into one quote; 52.42 seconds | Schema-valid answer correctly rejected by exact-quote validation; not a passed comparison |
| Final date/current-role and quote retest | PARTIAL_MATCH, moderate confidence; 171.17 seconds | Exact quotations validated; current role recognized; asks specifically whether the Spring Boot services used microservices architecture |

After reprocessing, the 21 retained statements comprise 10 hiring expectations,
6 duties and 5 preferences. Two metadata items and two unresolved normalizations
(work authorization wording and Agile Methodologies) remain auditable, not
candidate capability gaps. Related source words are not silently treated as exact
equivalents. The visa/sponsorship restriction still requires careful source-level
interpretation; no candidate eligibility conclusion was made.

Changes implemented from observed failures:

- Do not reject a role-named capability when its source explicitly states a
  qualification: Java Development with six years is not just a job-title label.
- Normalize generic verb forms such as mentor/mentoring, deploy/deployment and
  integrate/integration, retaining exact source-quote grounding.
- Send evidence source references and dates to comparison. Preserve the source's
  explicit current-employment flag and record date instead of interpreting a
  null end date as automatically ongoing.
- Require each model quote to be a contiguous substring; separate non-adjacent
  excerpts into separate quote objects. The grounding validator was not relaxed.
- Explicitly preserve preference/work-alignment/hiring distinctions in synthesis.
- Stamp future audits with schema version 2, pipeline version and prompt versions.

Employment tenure is not automatically years of every technology. Missing
microservices detail remains a clarification, not a claim that the candidate
cannot do the work. A small set of matches must not produce overall Apply now.
The final answer's claim that tenure exceeds the six-year bar is stronger than
the per-capability duration evidence warrants; do not treat schema/quote acceptance
as proof of every semantic assertion. Its ADJACENT_CAPABILITY_PARTIAL subtype also
deserves calibration review: the text describes unconfirmed architecture evidence,
not necessarily an adjacent function. These are remaining evaluation findings,
not reasons to fabricate missing evidence or turn the result into Apply now.

## Saved request and response packages

All paths below are relative to the repository root. `.request.json` contains
messages and output schema without credentials; `.response.txt` contains the
provider's final answer, not private reasoning; `.metrics.json` contains usage
and timing; `results.json` contains post-validation results.

- `outputs/glm-contract-check/20260910T031922Z`: original live extraction,
  comparison prompt v4/extraction v6. A diagnostic-only missing required field
  stopped execution after extraction; its paid response was retained and reused.
- `outputs/glm-contract-check/20260910T032403Z`: replay of that extraction plus
  four live comparisons. No second paid extraction.
- `outputs/glm-contract-check/20260910T032813Z`: one date-inclusive comparison,
  prompt v5. Shows the exact-quote rejection rather than substituting a result.
- `outputs/glm-contract-check/20260910T033132Z`: final focused comparison with
  prompt v6, explicit current-role context and contiguous-quote instructions.

The separate 032346Z directory contains only a diagnostic setup failure; no
request was sent. This does not count as a model failure.

## Final verification

Seven live requests in total: one extraction, four initial comparisons and two
focused follow-ups. Extraction was replayed locally, not repurchased. No silent
model retries, alternative-provider calls or replacement demo answers were used.
Comparison prompt is now v6, extraction v6, synthesis v5 and plan wording v2.
The final code passed 910 tests and targeted Ruff checks. One full-suite attempt
had Windows temporary-directory permission errors; the approved rerun passed.
The only remaining pytest warning concerns its cache directory.

Port 8517 was restarted after the final changes at 23:34 local time (launcher
PID 14956); `/_stcore/health` returned `ok`. Temporary browser session data was
reset by the authorized restart. No manual browser visual QA is claimed.

## Remaining limits

One model answer is not evidence of repeatability. Short comparisons still use
substantial provider-reported output-token budgets; usage is not the token count
of the visible final JSON alone. Full-JD completeness, generic grouping quality,
compound qualifications, source-specific scope and realistic response latency
still need broader evaluation. No credential, timeline or bridge role was invented
to fill missing evidence. The Plan model was inspected and regression-tested,
not exercised through a new live full-workflow run in this check.

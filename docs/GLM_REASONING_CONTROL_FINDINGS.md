# GLM generation investigation — September 10, 2026

## Finding: explicit high effort completes the unchanged five-JD task

| Same five-description task | No reasoning setting (control) | reasoning_effort=high |
|---|---:|---:|
| Input tokens | 3,546 | 3,546 |
| Output ceiling | 30,000 | 30,000 |
| Reported output tokens | 30,000 | 10,378 |
| Elapsed seconds | 246.26 | 86.43 |
| Finish reason | length | stop |
| Final JSON | None | Complete, schema valid |
| Themes / posting reviews | Not available | 25 / 5 |
| Quote/ID checks | Not available | 90 pass, 0 fail |

This is a one-run controlled request comparison, not a repeatability or production
latency guarantee. The code asserts the entire outgoing wire body equals the saved
control before adding only `reasoning_effort`. Same model, prompt, schema, input,
temperature, streaming transport and output ceiling. The timeout remains 600 seconds,
with one call and zero retries. No private reasoning traces are captured.

The active production Fireworks adapter omitted reasoning_effort; compact prose
instructions do not set an API reasoning level. The successful explicit-high request
shows this setting matters for completion in the tested configuration. It does not
prove the omitted setting is internally Max, or establish the hidden reasoning-token
split. Do not claim that reasoning was turned off in the successful run.

## Compatibility investigation

Official documentation checked:

- https://docs.fireworks.ai/api-reference/post-chatcompletions
- https://docs.fireworks.ai/guides/reasoning
- https://fireworks.ai/models/fireworks/glm-5p3-flash

The API documents reasoning_effort but does not explicitly include GLM 5.3 Flash
in the model support table. An otherwise identical five-JD request with `none`
failed in 1.22 seconds. A subsequent tiny compatibility probe (32-token ceiling,
20-second timeout, no retry) returned HTTP 400 with the sanitized explanation:

> GLM-5.3 is a thinking-only model; disabling thinking (reasoning_effort='none') is not supported.

Then one five-JD request with `high` returned successfully. Three diagnostic network
calls total this activity: rejected none batch, tiny none probe, successful high batch.
No authentication failures, credential outputs, model change or website restart.

## Quality review: completion is not an assessment pass

All 90 supports cite real text in the indicated posting/section and all five posting
IDs are reviewed exactly once. This narrow audit checks provenance, not full meaning.

Semantic failures visible in the saved answer:

- All 90 supports are labeled HIRING_CAPABILITY, including duty-section material.
  There are 79 REQUIRED and 11 PREFERRED obligations. Duty statements should remain
  responsibilities; preferences should have their correct item type.
- Cognizant's microservice delivery and code-quality duties are marked mandatory
  hiring capabilities, despite being under its role-responsibility heading.
- Work-authorization and credential prerequisites were omitted, despite the source
  including Cognizant's sponsorship restriction and CGI/Astra/Autodesk education
  conditions. No eligibility theme is returned.
- At least two theme names visibly end mid-phrase at the 80-character constraint
  (frontend technologies ending in TypeS; production support ending in where).
  Use short atomic labels rather than truncating explanatory headings.
- All posting reviews say PARTIAL, while several notes describe a complete JD.
  Content completeness and independently verified vacancy status are being conflated.

Positives: source attribution passes; the cloud OR alternatives and six-year Java
qualification are preserved in quoted evidence; Cognizant mentoring is PREFERRED
in its obligation field, though the separate item-type field is wrong. Broader
atomic grouping/coverage precision was not exhaustively scored.

## Recommendation and scope

Explicit high effort is a promising generation-setting correction for this exact
GLM deployment. Do not use unsupported none. Do not assume high is a hard token
budget. The remaining quality work is a separate contract change: avoid contradictory
kind/obligation combinations, preserve responsibilities and prerequisites, use concise
atomic names, and distinguish source completeness from vacancy verification. Test
these changes independently rather than claiming this answer is production-ready.

Production model configuration, prompts and website remain unchanged. Implemented
only opt-in diagnostic scripts and tests; no candidate assessment or Plan generated.
Seven offline control/audit tests passed and Ruff passed. Tests assert only the
reasoning field changes, unknown control payloads are not sent, and calls cannot
automatically repeat. Pytest reported a benign cache filesystem warning.

## Artifacts

- Control: `outputs/batch-role-profile/20260910T164628Z/`
- None rejection: `outputs/glm-reasoning-control/20260910T165408Z/`
- Tiny probe: timestamped `capability-probe-*.json` in `outputs/glm-reasoning-control/`
- High success: `outputs/glm-reasoning-control/20260910T165614Z/`
- Runner: `scripts/benchmark_glm_reasoning_control.py --live --effort high`
- Compatibility probe: `scripts/probe_fireworks_reasoning.py` (one tiny live request)

Requests exclude credentials; responses retain final content only. The successful
folder contains exact request, manifest, metrics, structured response and source audit.

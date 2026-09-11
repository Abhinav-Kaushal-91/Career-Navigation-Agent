# Nemotron versus GLM — same ten-record consolidated task

September 10, 2026. One user-authorized NVIDIA call; no retries or website changes.

## Results

| Metric | Fireworks GLM 5.3 Flash | NVIDIA Nemotron 3.5 Lightning 30B A3B |
|---|---:|---:|
| Records | 10 | 10 |
| Source text characters | 18,336 | 18,336 |
| Elapsed seconds | 273.62 | 276.52 |
| Input tokens reported | 5,328 | 6,288 |
| Output tokens reported | 30,000 | 5,841 |
| Finish reason | length | stop |
| Final answer | None | 20,668 characters |
| Schema valid | No | Yes |
| All posting IDs reviewed once | Not evaluable | Yes |
| Themes | Not evaluable | 10 |
| Source/obligation checks | Not evaluable | 40 pass, 11 fail out of 51 supports |

This attempt shows improved **completion**, not faster latency or proven superior
model quality. The Nemotron result is diagnostic only, not an approved market
profile. No candidate comparison, accessibility verdict or Plan was generated.

## Comparison controls and differences

The primary system/task prompt and user input were copied byte-for-byte from the
saved GLM request. The output Pydantic schema was asserted equal to the saved schema.
Both calls requested temperature 0, max_tokens 30,000, timeout 600 seconds and zero
retries. Source inventory: six longer retrieved documents and four excerpts; not
ten independently verified complete active postings.

NVIDIA uses the existing production adapter: `json_object` response mode, schema
instructions in an additional system message, `enable_thinking=false`, non-streaming.
GLM uses Fireworks schema response mode and streaming without a thinking override.
Therefore this compares configured provider/model combinations, not isolated model
weights under identical inference settings. Different tokenization/schema delivery
also means input token counts are not directly comparable. Thinking-off is requested,
not independently confirmed from hidden traces. No private reasoning was retained.

Model: `nvidia/nemotron-3.5-lightning-30b-a3b`, taken from the last saved NVIDIA test.
The existing NVIDIA key was loaded through Settings and never printed or persisted.
Only an in-memory diagnostic Settings copy changed; website remains configured for GLM.

## Returned theme headings

- Java Development & Frameworks
- Cloud Platforms & Containerization
- CI/CD & DevOps Practices
- API Design & Integration
- Database & Data Management
- Testing & Quality Assurance
- Agile & Team Collaboration
- Leadership & Mentorship
- Security & Performance Standards
- Work Authorization & Eligibility

These are the model's headings, not validated canonical capability names. Several
combine distinct functions contrary to the requested atomic-theme policy.

## Grounding and semantic findings

All ten posting IDs reviewed, none missing/unknown/duplicated; six marked USABLE,
four PARTIAL. Audit finds nine non-grounded quotes, three explicit duty-obligation
conflicts and one non-grounded section across 11 support rows (error types overlap).
The remaining 40 pass the narrow quote/ID/enum checks; **that is not 40 semantically
correct requirements**. They comprise 37 hiring-capability labels, two preferences
and one prerequisite, with no duty supports remaining after those checks.

Spot-checked successes:

- Cognizant's six-plus-year Java/Spring Boot/microservices requirement preserved.
- Cognizant mentoring is explicitly preferred, not mandatory.
- Cognizant's no-sponsorship statement retained as a prerequisite.
- Partial snippets acknowledged rather than described as complete JDs.

Concrete failures in the saved output:

- Cognizant cloud deployment, API work, CI/CD work and code-quality duties under
  “In this role, you will” are labeled mandatory HIRING_CAPABILITY. Exact quotes
  do not justify turning responsibilities into prior qualifications.
- Autodesk and CGI responsibility statements likewise promoted to hiring requirements.
- A CGI offshore coaching quote is attached to the Atyeti record and its section
  is absent from Atyeti. The Atyeti review note also adds hybrid/years/DevOps details
  absent from that supplied text. This demonstrates cross-posting contamination.
- Atyeti's SDLC/Agile quote supports “Cloud Platforms & Containerization” even
  though it establishes neither cloud nor containers. It passes quote grounding
  but fails semantic relevance; generic topic grouping alone is unsafe.
- Several other quotes are stitched, expanded or wording-modified, violating the
  contiguous-source requirement.

No exhaustive gold-label recall/precision evaluation was performed. Posting-review
coverage does not prove complete extraction, and exact-source counts must not be
promoted to trustworthy market frequencies without semantic validation.

## Verdict and artifacts

**Completed, but needs substantial refinement; do not feed unchanged into candidate
accessibility or Plan.** Reducing timeout or changing only JSON formatting will not
fix these classification and cross-source failures. No repair call was sent.

Raw evidence: `outputs/nemotron-batch-profile/20260910T163815Z/` contains request,
manifest, final response, structured JSON, metrics and item-level audit. GLM reference:
`outputs/batch-role-profile/20260910T162833Z/`. Runner:
`scripts/benchmark_nemotron_batch.py` (dry-run default, `--live` sends exactly once).
Ruff passed; four existing diagnostic audit/selection tests passed (benign pytest
cache filesystem warning). Dry-run verified key presence without exposing the key.

# Evidence pipeline: saved 60-statement replay

September 9, 2026. Offline regression replay; no external API calls.

## What changed

Frequency no longer decides whether a grounded hiring expectation is compared.
Uncommon employer-specific asks remain eligible; they do not become universal
requirements. Required, preferred and unspecified wording is retained per source,
with employer/posting IDs, quotes, years, maturity, qualifiers and alternatives.

Equivalent labels are grouped conservatively. Duties, preferences and prior
qualifications for the same concept retain separate canonical IDs and comparison
tracks. Duties and preferences cannot create mandatory hiring gaps or determine
overall accessibility. Related-title context still cannot define the baseline.

## Replay outcome

| Disposition | Source statements | Canonical comparison groups |
| --- | ---: | ---: |
| Hiring expectations | 17 | 6 |
| Role responsibilities / work alignment | 10 | 10 |
| Preference | 1 | 1 |
| Retained role/title/domain context | 5 | Not hiring evidence |
| Ambiguous qualification fragments | 2 | Require source clarification |
| Metadata, conditions or non-requirements | 25 | Audit only |
| Total | 60 | 17 across the three comparison tracks |

The six hiring groups are Java, Audio Codec Integration, Software Development
Experience, Mentoring Junior Developers, Code Reviews and Architectural
Decision-Making. Their original source conditions are not interchangeable.
Four hiring statements retain the legacy SECONDARY frequency label and thirteen
retain OPTIONAL; those labels describe recurrence, not whether an employer
requires the capability. All seventeen hiring statements now contribute to the
six eligible groups. No role-specific policy was introduced.

Each of the 60 source statements has an audit ID and disposition. No statement
was silently discarded to make the output look stronger. Ambiguous fragments
remain questions rather than candidate weaknesses.

## Accessibility and Plan guardrails

An isolated Java match cannot establish whole-role readiness. Coverage checks
withhold that verdict for a one-expectation profile, insufficient independent
role evidence, predominantly low-quality primary content, or incomplete/low-
confidence hiring comparisons. Completed individual matches remain available.
Low market confidence alone does not automatically erase a complete credible
comparison. Two expectations are only an anti-degenerate minimum, not proof that
the full role has been covered.

Incomplete evidence routes to exploration/evidence verification rather than an
unsupported direct-application recommendation. Confirmed 'No fixed timeline'
remains a preference, not a missing-input error. Direct application actions now
request a posting-specific requirement/evidence table and explicit unresolved
employer conditions.

## Boundaries of this test

The fixture preserves the saved audit's quotes and metadata, not full original
job descriptions or complete raw model responses. Missing optional model fields
use fixture defaults; the replay verifies deterministic processing of those
quotes, not a fresh extraction model's semantic accuracy. Its reconstructed
posting bodies are explicitly LOW quality. No fresh candidate comparisons or
new career verdict were generated; the counts above describe eligible work,
not successful live model calls.

Existing saved session results are not rewritten. A fresh live analysis is needed
to exercise the updated prompts with GLM and assess actual response quality,
latency and completeness. The existing session was not reset, and provider,
token and timeout settings were not changed.

## Verification

- Full backend/UI/evaluation regression suite: 903 passed (one local pytest
  cache-directory warning); targeted Ruff checks passed.
- Streamlit AppTest renders all three evidence tracks and the
  60-statement audit disclosure without calling a provider.
- No manual browser visual QA or live end-to-end acceptance is claimed.

Reproduce the quote replay from the repository root:

```powershell
.\.venv\Scripts\python.exe -m tests.market.test_evidence_tracks
```

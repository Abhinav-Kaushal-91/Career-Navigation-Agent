# Bounded parallel extraction — September 10, 2026

Live backend diagnostic, not a production pipeline change or full-workflow test.
Model: Fireworks `accounts/fireworks/models/glm-5p3-flash`.
Prompt: `market-requirements-v7`; output ceiling 30,000; two workers;
four calls maximum, zero retries, shared 600-second deadline.
Each worker used an independent production gateway/provider; production extraction,
schema checks, normalization and source grounding ran unchanged.

Inputs: saved public job text from the September 9 batch, not current vacancies.
One 3,170-character body plus three 500-character snippets. No candidate profile
was sent. No website session was stopped or changed. Other website requests may
have shared the provider account; provider-side concurrency was not measured.

| Posting | Start offset | Response duration | Finish offset | Raw / retained |
|---|---:|---:|---:|---:|
| Cognizant | 0 s | 190.49 s | 190.49 s | 25 / 21 |
| Targeted Talent | 0 s | 85.31 s | 85.31 s | 3 / 1 |
| Localcoin | 85.31 s | 27.92 s | 113.24 s | 1 / 0 |
| Astra North Infoteck | 113.24 s | 66.27 s | 179.51 s | 13 / 8 |

Wall time: **190.50 seconds**. Sum of per-request durations: **369.99 seconds**.
Overlap removed 179.49 seconds relative to that sum (48.5%); this is not a separate
serial control run. Do not generalize the speedup to ten full job descriptions.
All four returned `stop`, passed schema validation, and had no provider failure.
Source policy retained 30 of 42 extracted statements: 15 hiring capabilities,
6 duties, 9 preferences. Metadata/normalization exclusions total 12; no retained
statement failed the exact-source grounding checks. Retained does not imply
canonical target-role coverage or a complete candidate assessment.

Quality caveats: Localcoin's snippet was company description, not useful hiring
evidence. Targeted Talent yielded only one duty. Source normalization rejected
Cognizant's work-authorization label and Astra's software-experience label even
though associated source conditions are present; these remain in the saved audit
for review, not silently treated as resolved. Concurrency does not fix coverage
or normalization quality.

Provider-reported output token counts: Cognizant 20,448; Targeted Talent 8,724;
Localcoin 3,016; Astra 6,739. These are provider usage counts, not counts of visible
JSON alone. No private reasoning traces were saved.

Artifacts: `outputs/parallel-extraction/20260910T160944Z/results.json` and per-posting
request bodies, final response text, metrics and validated evidence/audits.
Runner: `scripts/benchmark_parallel_extraction.py` (dry run by default; `--live`
explicitly enables the bounded calls). Ruff passed; dry-run input loading passed.

Conclusion: two-worker extraction is promising for elapsed time. The website
still uses sequential extraction. Production adoption needs safe concurrency,
per-posting progress, batch deadline/cancellation and regression coverage.

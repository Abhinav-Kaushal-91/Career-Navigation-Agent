# Demo-to-analysis live backend check

Run: `outputs/demo-to-analysis/20260911T002304Z/results.json`.
Local date: September 10, 2026 (UTC artifact date September 11).

## Verdict

The production backend reached career assessment synthesis in **195.35 seconds**,
using eight GLM calls. It did **not** produce a usable overall-fit assessment:
`INSUFFICIENT_CANDIDATE_EVIDENCE`, confidence `INSUFFICIENT`.
Reaching the node is not an acceptance pass. No positive fit or candidate inability is established.

## Scope

- Production demo inputs through Education/Certification: synthetic Senior Java Developer,
  dated professional experience, competencies, personal project, BSc Computer Science and
  explicitly synthetic certification. These are test facts, not real candidate claims.
- Goal: current market analysis, Senior Java Developer, Toronto metro, variants allowed,
  no fixed timeline.
- Fresh Adzuna and You.com retrieval; configured Fireworks GLM and production five-posting
  extraction/comparison/synthesis services. No browser, DOM scraping, saved-market replay,
  production session mutation or Plan generation/approval.
- Inferred capabilities were tested and recorded but not automatically approved. Downstream
  comparison used the explicitly confirmed synthetic base profile, as with manual confirmation.
- Diagnostic runner: `uv run python scripts/check_demo_to_analysis.py --live`.

## Measured stages

| Stage | Seconds | Result |
|---|---:|---|
| AI strength review | 13.46 | Succeeded; five inferred suggestions |
| Fresh retrieval | 12.47 | 25 retained posting records; limited source coverage |
| Five-description extraction and repair | 90.96 | Seven initial rejected themes; five repaired, two unresolved |
| Candidate comparison | 61.42 | Two partial matches and two processing failures |
| Deterministic gap/accessibility | 0.06 | Insufficient; no unsupported verdict |
| Assessment synthesis | 16.79 | Insufficient assessment returned |

Minor initialization and export overhead accounts for the remainder of total elapsed time.

## Actual results

AI suggestions: Backend Service Design; Cross-System API Integration; Technical Design
Review; API Documentation; Authentication Implementation. Last two are demonstrated-level
project suggestions, not production claims.

Adzuna returned 31 raw results; 25 posting records were retained (3 exact, 5 variants,
17 related). Possible duplicates are not verified independent vacancies. You.com returned
48 search results but added zero validated postings and recorded zero successful enrichments.
The selected five descriptions were truncated excerpts, including one company-only excerpt.

| Compared expectation | Result |
|---|---|
| AWS services | Partial match |
| Application development experience | Partial match |
| Database expertise | Processing failed |
| Node.js (additional advantage) | Processing failed |

## Concrete blockers

1. The duty-heading guard rejected Java/J2EE and Spring Boot/REST/microservices hiring
   evidence under the combined heading **Key Skills & Responsibilities**. The Java quote
   includes **Strong expertise in Java/J2EE**, a candidate-capability statement. This is a
   backend false-rejection issue, not simply an LLM connection failure. The entire theme
   remains unresolved rather than establishing general candidate readiness.
2. Database comparison failed `TransferabilityAssessment`: a supported match lacked
   evidence references. Node.js comparison failed because a no-confirmed-match response
   supplied supporting evidence IDs. Both were correctly marked processing failures rather
   than candidate gaps. Revalidation used the production requirement-ID validation context;
   omitted code-owned IDs were not misdiagnosed as model omissions.
3. Retrieval still did not supply full descriptions for the selected batch. The workflow
   has role-sample limitations even after addressing validator errors.

No production rules were changed during this test. Sanitized inputs, final model responses,
stage timings, graph state and retained job evidence are in the run directory. Private
model reasoning and credentials are excluded. Full workflow acceptance remains open.

# Retrieval improvement checkpoint — September 7, 2026

Scope: public job discovery and source-body retrieval only. No candidate profile was sent,
no Nemotron/model calls were made, and comparison/accessibility/Plan policy was not changed.
This is not a live V1 release pass.

Final integrated verification: **791 tests passed in 22.62 seconds**. Market-code/test and
diagnostic-script Ruff checks pass. Automated fixtures verify contracts and guards, not live recall.

## Corrected defects

- ATS discovery uses public job-host allowlists, not optional domain boosts. A separate
  employer-site pass remains open to custom career domains and excludes known aggregators.
  The service rechecks domain policy against each actual URL before spending a fetch.
- Internship exclusions use whole-word career-stage markers; Internal Auditor is not an intern.
  Safe title-wording variants do not silently add specialties or change requested seniority.
- Contents requests supported Markdown, HTML and metadata formats. It understands the observed
  MCP `output` envelope, isolates one structured JobPosting body, and rejects ambiguous multiple
  jobs, missing content and malformed page associations. Scripts/links are not executed.
- Qualifications and responsibilities below subheadings stay with their vacancy. Separate job
  cards and salary/FAQ/related-job footers do not leak into that vacancy.
- Adzuna search descriptions explicitly carry `content_complete=False`, even above 500 characters.
  A missing completion signal is not proof of completeness.
- Enrichment requires positive identity support and in-scope redirected geography. Conflicting
  job metadata cannot be rescued by an unrelated employer/location mention in the body.
- A repeated excerpt, shorter unknown body or JavaScript/access shell cannot replace better
  source content. One selected body is used; original snippets and provenance are retained.
  Body quality precedes host preference when choosing duplicate content.
- Resolved canonical URLs/requisitions trigger deduplication again after completion. Same vacancy
  means one posting/employer signal; different requisitions remain separate.
- Audits retain bounded returned-page identity metadata and body lengths, not rejected full bodies.
  Explicit closed-job and 404 pages cannot become the requested vacancy through suggested jobs.

Provider contracts checked: [Adzuna Search](https://developer.adzuna.com/docs/search) explicitly
supplies snippets; [You.com Contents](https://you.com/docs/api-reference/contents) makes metadata
opt-in; [You.com Search](https://you.com/docs/api-reference/search/v1-search) distinguishes strict
domain inclusion from boosts. MCP behavior was also checked against an actual public response.

## Actual live checks — preserved separately

Artifacts are local under `outputs/retrieval-improvement-20260907/` and are not overwritten.

| Check | Bounds and result |
|---|---|
| `live-retrieval.json` | Six-query/twelve-fetch ceiling; actually 5 searches and 12 fetch attempts. 9 retained Adzuna postings, 7 employers, all 500-character excerpts. New normalizer rejected all content responses because the MCP `output` container was missing from its envelope allowlist. |
| One content-contract diagnostic | One fetch, no search. Observed `{output: [page]}` with Markdown, HTML and metadata. No page body or credentials printed. Added this exact shape as a regression fixture. |
| `live-retrieval-verified.json` | Same bounded retrieval after the envelope correction; 5 searches and 12 fetch attempts, 7.74 seconds. 9 retained postings/7 employers, zero full-body completions. Adzuna details returned 336-character pages with URL-like titles and no job identity; rejected. You.com bodies were now parsed, but context-only or out-of-scope/unclear geography. |
| `query-probe.json` | Three searches and three fetches. Quoted city plus a year-long search-index lookback returned Toronto-specific TD, Behavox, Cognizant, RBC and other URLs. The three fetched examples were a Workday loading/cookie shell, a closed Greenhouse posting and a Cognizant 404. These are discovery candidates, not validated active vacancies. The employer-specific query did not establish a matching Targeted Talent vacancy. |

The probe changed quoting and index recency together; it does not isolate which change improved
geographic relevance. Production keeps a recent first ATS pass and widens index lookback only in
bounded later passes. The separate 90-day posting-age policy and explicit-closure checks remain
unchanged. Unknown posting dates do not become verified-open. The final mixed query strategy is
regression-tested but was not run as another full live pipeline.

## What remains

Usable full descriptions from multiple independent in-scope employers remain the acceptance gap.
The system still needs a bounded route from inaccessible aggregator details to an identity-matched
employer/ATS description, or a compatible accessible source for that vacancy. The public probe did
not establish that employer-specific recovery works. Do not relax identity, geography, expiry or
grounding checks to manufacture a passing sample. No new ATS API integration, scraping framework,
browser automation, monitoring or provider architecture was introduced.

No new candidate comparison or Plan was run. Search counts and automated passes do not establish
successful Market → Analysis → Plan behavior.

# JSearch / RapidAPI setup

The live app now defaults to JSearch only. Neither Adzuna nor You.com is contacted
on this path, even if their old keys remain in your environment. Historical adapters
and fixtures remain available for old recordings; they are not automatic fallbacks.

## Your account

1. Open the JSearch listing on RapidAPI:
   https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
2. Check your subscription and quota. An application API key alone does not prove
   that you are subscribed. Choose a plan yourself; this app does not subscribe or upgrade.
3. Copy the X-RapidAPI-Key from your account into the ignored local environment file.
   Never put it into a chat, screenshot, source file or GitHub. Rotate any publicly exposed key.

## Local settings

The existing installation uses `src/ai_career_navigator/.env`; a project-root `.env`,
if created, takes precedence. Keep your model settings and model keys unchanged.

```dotenv
MARKET_PRIMARY_PROVIDER=jsearch
MARKET_ENRICHMENT_PROVIDER=none
RAPIDAPI_KEY=your_key_here
JSEARCH_SEARCH_PATH=/search-v2
JSEARCH_COUNTRY=ca
JSEARCH_MAX_DETAILS=5
JSEARCH_SEARCH_TIMEOUT_SECONDS=90
```

Use the actual endpoint shown in your RapidAPI code snippet: `/search-v2` is the
provider's current documented search example. `/search` is also supported by the
adapter for accounts using that endpoint. No automatic endpoint retry spends quota.
Host is fixed to `jsearch.p.rapidapi.com`; keys are sent as headers, never in URLs.

Restart the app after saving. Do not change the country to broaden geography without
also choosing the appropriate location in your goal. Default country is Canada.

## One-call connection check

From the project directory:

```powershell
.venv\Scripts\python.exe scripts/check_jsearch.py --role "Senior Java Developer" --location "Toronto, Canada"
```

This spends one search request and prints titles/employers/locations/description word
counts. It makes no LLM calls and does not fetch details. Run only after checking quota.

## Application flow

One bounded search (all posting dates, one page, no cursor) → normalize individual postings → identity deduplication
→ up to five detail requests for missing or visibly truncated descriptions → geography,
currentness and posting validation → target-role cohort selection → existing top-five
description selection → assessment/plan. Unrelated discoveries remain in audits, but not
in target-market counts or model-bound content. Existing posting-age checks remain active.

Existing nonempty descriptions are used without imposing a 600-character threshold. Text
length does not prove description completeness. Missing details stay missing; different
job IDs cannot substitute for the requested job. Same employer plus similar descriptions
does not merge jobs. Credentials/quota errors stop safely without retry loops or fallback.
Default maximum is six HTTP requests per live retrieval, not a promise about billable credits:
RapidAPI's plan determines credit accounting. One page may return fewer than five suitable jobs.

Search now has its own 90-second read budget (configurable 30–180 seconds), a 10-second
connection/write/pool budget and an outer deadline of read-budget + 10 seconds. Job Details
keeps MARKET_TIMEOUT_SECONDS (30 by default). A slow response no longer hits the old 30-second
search cutoff. Timeout phase/elapsed diagnostics contain no URL parameters or credentials.
This is a bounded latency tolerance change, not a guarantee that JSearch will always respond.

Live search connectivity has been verified, but this is not proof of end-to-end analysis
quality. See CURRENT_STATE.md for the latest bounded live and saved-response checks.

Provider reference: https://www.openwebninja.com/api/jsearch

## Response contract and routes (September 11)

The user's saved Search V2 JSON is the integration reference: `status`, `request_id`,
`data.jobs`, and optional `data.cursor`. The adapter also accepts the Job Details list envelope.
The cursor value is neither stored nor sent; only a continuation-available flag is retained.

- Use `job_description` directly, including short descriptions; length does not prove completeness.
- Missing/truncated description or highlights-only content → bounded `/job-details` request using
  the full `job_id`. A returned different job cannot substitute. A complete-looking detail response
  can replace a longer incomplete snippet. Failed/deferred requests retain their distinct status.
- If a description is absent, supplied Responsibilities/Qualifications highlights can provide limited
  text. Benefits, salary and other administrative fields are never synthesized into capabilities.
  A highlights-only detail response remains explicitly limited, not promoted to a full description.
- `job_apply_link` or a valid `apply_options[].apply_link` supplies a URL. Multiple application
  options remain one posting. `job_uid` is recorded only; it is not used instead of `job_id` or as
  an independently verified duplicate key. Existing conservative identity deduplication stays in place.
- Null salary, dates, employment type and empty highlights do not invalidate a description.
  Unknown dates remain unknown, not proof of a current vacancy. Structured location and separately
  reported display location are preserved; no assumption that remote means globally eligible.
- Audit routes distinguish retained descriptions, limited/missing content, duplicates, invalid
  metadata, location/posting review, currentness exclusion and role-relevance review.
  Review routes are diagnostic labels, not a newly implemented manual-review workflow.
- Raw counts include malformed objects. Normalization failures and records deferred beyond the
  50-record normalization cap are reported separately. One search and at most five details remain
  the default; neither pagination nor a new LLM call is introduced by these changes.

The replay of the supplied four-job response normalizes all four with descriptions. Existing role
matching retains Iris; PeoplePilot/Resonaite full-stack roles and Kovasys Python are excluded from
the target cohort. The full-stack relevance limitation is not fixed by schema routing. Location
conflicts within free-form descriptions are not automatically resolved by this adapter.

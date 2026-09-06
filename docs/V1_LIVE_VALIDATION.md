# V1 Live Validation

## September 4, 2026 extraction-reliability gate

The reliability rerun selected five postings and made six NVIDIA calls, including one controlled
schema-repair attempt. Four postings were successfully analyzed. One posting failed with
`ModelResponseValidationError` after the retry; no timeout occurred. The run therefore passed the
minimum gate of four successfully analyzed postings. It remained a market-only QA slice and did
not invent candidate evidence for comparison.

The four-posting denominator produced seven accepted capability occurrences and two employment
conditions. `Solution Architecture` appeared in 2 of 4 analyzed postings; each other normalized
capability appeared in 1 of 4. Two metadata/non-requirement items and one unsupported source
reference were rejected. Reported NVIDIA usage was 6,802 input tokens and 2,441 output tokens.

## September 4, 2026 requirement-quality QA

The bounded combined run retained 11 postings and selected five for extraction in title-scope
order. Two thin-record You.com enrichments were attempted; both were rejected because the
supporting page conflicted with structured Adzuna fields. NVIDIA received five bounded extraction
requests. Three postings were successfully analyzed, one response failed strict schema validation,
and one request timed out. The accepted output contained three capability requirements, no
prerequisite conditions, and no accepted posting metadata. Three unsupported source references
were rejected deterministically.

Every observed capability occurred in 1 of 3 successfully analyzed postings. This sample is a QA
slice and is not presented as representative of the Canadian market. Candidate comparison was not
started.

## September 3, 2026 combined QA result

The structured Adzuna path produced 11 validated postings. Five evidence units were selected in
scope order: three exact, one target variant, and one related. NVIDIA performed five structured
extraction calls and requirement aggregation completed. The run stopped before candidate
comparison. Adzuna evidence bypassed the legacy web-page segmentation stage as intended.

Live provider checks are manual-only and never run in automated tests.

## Combined market slice

1. Adzuna retrieves bounded structured Canadian job records.
2. Existing title, geography, currentness, and duplicate policies validate 3–5 postings.
3. You.com may enrich at most two thin records and cannot overwrite Adzuna structured fields.
4. NVIDIA extracts requirements once per retained posting from primary plus validated supporting
   evidence.
5. The script stops before candidate comparison.

An Adzuna failure or empty usable result may trigger explicitly labelled degraded You.com
discovery. A healthy small Adzuna sample does not.

```powershell
uv run python scripts/smoke_test_adzuna_market.py --env-file src/ai_career_navigator/.env
uv run python scripts/live_validate_combined_market.py --env-file src/ai_career_navigator/.env --posting-limit 5
```

The commands print safe counts and metadata only. Credential values are never printed.

# Evaluation Loop

The evaluation loop measures candidate answers against the 100-case golden workbook. It is
separate from live-market QA: it evaluates product behavior, evidence discipline, and safe failure
handling without treating the reference answers as market observations.

## Run cycle

1. Generate candidate answers as JSON Lines. Each line must contain `case_id` and `answer`.
2. Run the evaluator against the versioned golden workbook.
3. Review `summary.json` and the failed or errored rows in `case_results.jsonl`.
4. Fix the product, prompt, or test adapter. Do not edit a golden answer merely to hide a genuine
   regression.
5. Rerun into a new timestamped directory and compare category pass rates.

```powershell
uv run python scripts/run_golden_evals.py `
  --dataset outputs/golden-dataset/career_navigator_golden_dataset_100.xlsx `
  --answers path/to/candidate_answers.jsonl `
  --semantic-judge `
  --env-file src/ai_career_navigator/.env `
  --threshold 0.90 `
  --output-dir eval-runs/product
```

Normalized exact answers pass without a model call. Non-verbatim `Meaning match` cases use the
configured validation model with temperature zero and a strict Pydantic output schema. Missing,
duplicate, and unknown case IDs fail deterministically. Judge errors are reported as `ERROR` and
cannot satisfy the threshold.

## Reference self-check

The self-check validates dataset loading, grading, aggregation, artifact writing, and threshold
behavior. It does not measure model or portal quality.

```powershell
uv run python scripts/run_golden_evals.py `
  --dataset outputs/golden-dataset/career_navigator_golden_dataset_100.xlsx `
  --reference-self-check `
  --threshold 1.0 `
  --output-dir eval-runs/reference-self-check
```

## Gate

- Overall pass rate must meet the configured threshold.
- No judge or schema errors are permitted.
- Review category rates even when the overall threshold passes.
- High-priority failures block release review.
- A golden-answer change requires an explicit product-rule change and review.

## Component eval suites

The golden-answer loop above grades end-to-end product answers (exact match and
an LLM-judge "meaning match"). It does not check the pipeline stages that
produce those answers: whether market search retrieves the right postings,
whether requirement extraction is complete and faithful to the source text,
whether career synthesis cites evidence that actually exists, or whether the
LangGraph orchestration routes correctly. Four component suites under
`src/ai_career_navigator/evaluation/` cover those stages, each deterministic-first
like the golden-answer loop, and each backed by a hand-labeled gold set under
`tests/fixtures/` so the numbers are reproducible without a live model call.

Every suite shares one set of primitives in `evaluation/metrics.py`
(`classification_metrics`, `set_metrics` / `pool_set_metrics`, `recall_at_k` /
`precision_at_k` / `ndcg_at_k`, `exact_match_rate`, `completeness`) so results
are comparable across suites and unit-tested once (`tests/evaluation/test_metrics.py`).

### Retrieval: market-search relevance

`is_promising_search_result` (the gate deciding whether a raw search hit is
worth fetching) is a binary relevance filter, not a ranked list, so the metric
that matches it is precision/recall/F1 over labeled (search result, target
title) pairs -- not Recall@k/NDCG, which need a ranked list this stage doesn't
produce. `metrics.py` still ships `recall_at_k`/`precision_at_k`/`ndcg_at_k` for
whichever stage does expose one.

```
uv run python scripts/run_retrieval_eval.py --threshold 0.6
```

Gold set: `tests/fixtures/retrieval_relevance_gold.json` (16 hand-labeled cases,
each with a `note` explaining the judgment, including three intentionally
documented gaps between the deterministic gate and human relevance judgment).
Current score: F1 ≈ 0.71.

### Extraction: requirement capability extraction

`extract_posting_requirements` already computes per-posting schema-validity and
unsupported-quote QA counters (`PostingExtractionQuality`) that were previously
unread internals; this suite surfaces them as rates and adds the piece that was
missing -- field accuracy against a hand-labeled capability list for four real
postings from `job-descriptions/`.

```
uv run python scripts/run_extraction_eval.py --candidates path/to/candidates.jsonl [--quality path/to/quality.jsonl] --threshold 0.6
```

`candidates.jsonl` is one `{"posting_id", "extracted_capabilities"}` line per
posting. Gold set: `tests/fixtures/extraction_capability_gold.json`.

### RAG grounding: quote faithfulness and citation accuracy

Two deterministic checks, no judge required:

- **Quote groundedness** (extraction layer): a requirement is grounded only if
  its `source_quote` is a real substring of the posting text *and*
  `quote_capability_alignment` confirms the capability label doesn't overstate
  what the quote says. Run against `tests/fixtures/quote_grounding_gold.json`
  (10 cases: verbatim quotes, hallucinated quotes, and quotes whose capability
  label invents claims like "certified" or "expert"):

  ```
  uv run python scripts/run_grounding_eval.py --threshold 0.9
  ```

- **Citation accuracy** (synthesis layer): `synthesis_citation_accuracy(draft,
  known_evidence_ids=..., known_comparison_ids=..., known_gap_ids=...)` checks
  whether every evidence/comparison/gap ID a `CareerSynthesisDraft` cites
  resolves to an object the candidate profile or analysis actually produced.
  This is a library call against one run's live objects, not a static gold set
  -- call it wherever a run's synthesis output and its source IDs are both in
  scope (see `tests/evaluation/test_grounding_eval.py` for usage).

### Agent: LangGraph routing and task completion

`ai_career_navigator.orchestration.routing` is a set of pure functions of
`CareerGraphState`, so routing accuracy is checked directly against hand-built
states rather than by running the graph. Task completion drives the real
`CareerWorkflowController` through scripted scenarios (reusing the fakes in
`tests/orchestration/conftest.py`) and checks the workflow reached the
`WorkflowStatus` a correct implementation should reach.

```
uv run pytest tests/evaluation/test_agent_eval.py -v -s
```

`-s` prints the `RoutingAccuracySummary` (overall accuracy plus a breakdown per
router function) and `TaskCompletionSummary` JSON.

## Gate: component suites

- Retrieval and grounding F1 must not regress below the score recorded above
  without an explicit note explaining why (a new gap, or a fixed limitation).
- Extraction schema-validity and groundedness rates from
  `summarize_extraction_quality` must stay at 1.0; a drop means the production
  extraction pipeline is emitting invalid or hallucinated output, not that the
  gold set needs editing.
- Synthesis citation accuracy must be 1.0 for any run under review; any
  citation that doesn't resolve is a hallucinated reference and blocks release,
  the same way a golden-answer high-priority failure does.
- Routing accuracy and task completion rate must be 1.0; a routing mismatch
  means the graph takes the wrong edge for a state it has already been told
  the correct answer for.

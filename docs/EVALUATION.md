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

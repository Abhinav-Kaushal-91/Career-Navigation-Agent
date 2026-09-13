"""Score a candidate requirement-extraction run against the hand-labeled capability gold set.

Candidates are supplied as JSON Lines, one `ExtractionCandidate` per posting:
    {"posting_id": "AI-ENGINEER-1", "extracted_capabilities": ["...", "..."]}

Optionally also score the schema-validity/groundedness rates already computed by
the production pipeline by passing `--quality` with one JSON `PostingExtractionQuality`
record per line (see `PostingExtractionQuality` in
`ai_career_navigator.market.requirement_schemas`).
"""

import argparse
from pathlib import Path

from ai_career_navigator.evaluation import (
    evaluate_extraction,
    load_extraction_candidates,
    load_extraction_gold,
    summarize_extraction_quality,
)
from ai_career_navigator.market.requirement_schemas import PostingExtractionQuality


def _load_quality(path: Path) -> list[PostingExtractionQuality]:
    return [
        PostingExtractionQuality.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold", type=Path, default=Path("tests/fixtures/extraction_capability_gold.json")
    )
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--quality", type=Path)
    parser.add_argument("--threshold", type=float, default=0.6)
    args = parser.parse_args()

    gold = load_extraction_gold(args.gold)
    candidates = load_extraction_candidates(args.candidates)
    field_accuracy = evaluate_extraction(gold, candidates)
    print(field_accuracy.model_dump_json(indent=2))

    passed = field_accuracy.f1 >= args.threshold
    if args.quality:
        quality_summary = summarize_extraction_quality(_load_quality(args.quality))
        print(quality_summary.model_dump_json(indent=2))
        passed = passed and quality_summary.schema_valid_rate == 1.0

    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()

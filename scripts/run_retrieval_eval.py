"""Score the deterministic market-search relevance gate against a hand-labeled gold set."""

import argparse
from pathlib import Path

from ai_career_navigator.evaluation import evaluate_retrieval_gold, load_retrieval_gold


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path("tests/fixtures/retrieval_relevance_gold.json"),
    )
    parser.add_argument("--threshold", type=float, default=0.6)
    args = parser.parse_args()

    cases = load_retrieval_gold(args.gold)
    result = evaluate_retrieval_gold(cases)
    print(result.model_dump_json(indent=2))
    raise SystemExit(0 if result.f1 >= args.threshold else 1)


if __name__ == "__main__":
    main()

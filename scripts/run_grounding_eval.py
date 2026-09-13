"""Score the deterministic quote-groundedness gate against a hand-labeled gold set.

This covers requirement-extraction faithfulness (is a `source_quote` real, and
does the capability label overstate it). Synthesis-level citation accuracy
(`synthesis_citation_accuracy`) runs against a live `CareerSynthesisDraft` plus
the run's known evidence/comparison/gap IDs, so it is a library call for
whoever is validating one run's output rather than a static-gold-set script.
"""

import argparse
import json
from pathlib import Path

from ai_career_navigator.evaluation.grounding_eval import (
    GroundingGoldCase,
    evaluate_quote_grounding,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold", type=Path, default=Path("tests/fixtures/quote_grounding_gold.json")
    )
    parser.add_argument("--threshold", type=float, default=0.9)
    args = parser.parse_args()

    payload = json.loads(args.gold.read_text(encoding="utf-8"))
    cases = [GroundingGoldCase.model_validate(item) for item in payload]
    result = evaluate_quote_grounding(cases)
    print(result.model_dump_json(indent=2))
    raise SystemExit(0 if result.f1 >= args.threshold else 1)


if __name__ == "__main__":
    main()

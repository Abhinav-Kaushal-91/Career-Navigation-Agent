"""Run the frozen V1 production-controller replay suite without live calls."""

import argparse
import json
from pathlib import Path

from ai_career_navigator.evaluation.v1_replay import run_replays_sync


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/v1-reliability-20260906/replay-results.json")
    )
    args = parser.parse_args()
    result = run_replays_sync(audit_directory=args.output.parent / "replay-run-audits")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Frozen production-graph replay: {result['passed']}/{result['case_count']} cases passed."
    )
    print(f"Results: {args.output.resolve()}")
    for item in result["results"]:
        print(
            f"{item['case_id']}: {item['actual_accessibility']} / "
            f"{item['evaluation']['failures'] or 'passed'}"
        )


if __name__ == "__main__":
    main()

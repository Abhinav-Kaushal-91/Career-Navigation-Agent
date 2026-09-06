"""Run Career Navigator golden-answer evaluations and write versionable artifacts."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from ai_career_navigator.config import Settings
from ai_career_navigator.evaluation import (
    CandidateAnswer,
    ModelGatewayJudge,
    evaluate_cases,
    load_golden_cases,
)
from ai_career_navigator.models import ModelGateway


def _load_answers(path: Path) -> list[CandidateAnswer]:
    return [
        CandidateAnswer.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_run(output_dir: Path, run) -> None:  # type: ignore[no-untyped-def]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(run.summary.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    with (output_dir / "case_results.jsonl").open("w", encoding="utf-8") as stream:
        for result in run.cases:
            stream.write(result.model_dump_json() + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    answer_group = parser.add_mutually_exclusive_group(required=True)
    answer_group.add_argument("--answers", type=Path)
    answer_group.add_argument("--reference-self-check", action="store_true")
    parser.add_argument("--semantic-judge", action="store_true")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--output-dir", type=Path, default=Path("eval-runs/latest"))
    args = parser.parse_args()

    cases = load_golden_cases(args.dataset)
    answers = (
        [CandidateAnswer(case_id=case.case_id, answer=case.expected_answer) for case in cases]
        if args.reference_self_check
        else _load_answers(args.answers)
    )
    judge = None
    if args.semantic_judge:
        settings = Settings(_env_file=args.env_file if args.env_file else None)
        judge = ModelGatewayJudge(ModelGateway.from_settings(settings))
    run = evaluate_cases(cases, answers, judge=judge, threshold=args.threshold)
    timestamped = args.output_dir / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    _write_run(timestamped, run)
    print(run.summary.model_dump_json(indent=2))
    raise SystemExit(0 if run.summary.threshold_met else 1)


if __name__ == "__main__":
    main()

import json
from pathlib import Path

import pytest

from ai_career_navigator.evaluation import (
    CandidateAnswer,
    EvaluationOutcome,
    GoldenCase,
    JudgeDecision,
    evaluate_cases,
    load_golden_cases,
)


def case(case_id: str = "GOLD-001") -> GoldenCase:
    return GoldenCase(
        case_id=case_id,
        category="Trust",
        question="Can inferred evidence be confirmed automatically?",
        expected_answer="No. The user must confirm it.",
        evaluation_mode="Meaning match",
        required_behavior="Require confirmation.",
        automatic_failure_conditions="Automatic confirmation.",
        priority="High",
    )


class PassingJudge:
    def judge(self, golden: GoldenCase, answer: str) -> JudgeDecision:
        assert golden.case_id == "GOLD-001"
        assert answer
        return JudgeDecision(passed=True, score=0.9, reason="Meaning is preserved.")


class FailingJudge:
    def judge(self, golden: GoldenCase, answer: str) -> JudgeDecision:
        return JudgeDecision(
            passed=False,
            score=0.1,
            reason="User confirmation is missing.",
            missing_concepts=["user confirmation"],
        )


def test_exact_answer_passes_without_a_judge() -> None:
    result = evaluate_cases(
        [case()], [CandidateAnswer(case_id="GOLD-001", answer="No. The user must confirm it.")]
    )

    assert result.summary.threshold_met
    assert result.cases[0].grading_method == "normalized_exact"


def test_semantic_judge_can_pass_non_verbatim_answer() -> None:
    result = evaluate_cases(
        [case()],
        [CandidateAnswer(case_id="GOLD-001", answer="Only a person can approve the inference.")],
        judge=PassingJudge(),
    )

    assert result.cases[0].outcome is EvaluationOutcome.PASS


def test_failure_and_missing_answer_are_reported() -> None:
    second = case("GOLD-002")
    result = evaluate_cases(
        [case(), second],
        [CandidateAnswer(case_id="GOLD-001", answer="It happens automatically.")],
        judge=FailingJudge(),
    )

    assert result.summary.failed_cases == 2
    assert result.summary.missing_answers == 1
    assert result.summary.high_priority_failures == 2
    assert not result.summary.threshold_met
    assert result.cases[0].missing_concepts == ["user confirmation"]


def test_duplicate_and_unknown_answers_fail_before_grading() -> None:
    duplicate = CandidateAnswer(case_id="GOLD-001", answer="No")
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_cases([case()], [duplicate, duplicate])
    with pytest.raises(ValueError, match="unknown"):
        evaluate_cases([case()], [CandidateAnswer(case_id="GOLD-002", answer="No")])


def test_project_golden_workbook_loads_exactly_100_unique_cases() -> None:
    workbook = (
        Path(__file__).parents[2]
        / "outputs"
        / "golden-dataset"
        / "career_navigator_golden_dataset_100.xlsx"
    )

    cases = load_golden_cases(workbook)

    assert len(cases) == 100
    assert len({item.case_id for item in cases}) == 100
    assert json.loads(cases[0].model_dump_json())["case_id"] == "GOLD-001"

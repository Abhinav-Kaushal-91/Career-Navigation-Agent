"""Deterministic-first evaluation loop with an optional strict semantic judge."""

import json
import re
from collections import defaultdict
from typing import Protocol

from ai_career_navigator.models import ModelGateway, ModelRole

from .schemas import (
    CandidateAnswer,
    CaseEvaluation,
    EvaluationOutcome,
    EvaluationRun,
    EvaluationSummary,
    GoldenCase,
    JudgeDecision,
)


class SemanticJudge(Protocol):
    def judge(self, case: GoldenCase, answer: str) -> JudgeDecision: ...


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


class ModelGatewayJudge:
    """Use the configured validation role for non-exact meaning comparisons."""

    def __init__(self, gateway: ModelGateway) -> None:
        self._gateway = gateway

    def judge(self, case: GoldenCase, answer: str) -> JudgeDecision:
        payload = {
            "question": case.question,
            "expected_answer": case.expected_answer,
            "candidate_answer": answer,
            "required_behavior": case.required_behavior,
            "automatic_failure_conditions": case.automatic_failure_conditions,
        }
        response = self._gateway.generate_structured(
            role=ModelRole.VALIDATION,
            output_schema=JudgeDecision,
            system_prompt=(
                "Grade semantic correctness conservatively. Do not require verbatim wording. "
                "Fail invented facts, guarantees, secret exposure, weakened validation, or a "
                "missing required limitation. Return only the supplied schema and no "
                "reasoning trace."
            ),
            user_prompt=json.dumps(payload, ensure_ascii=True),
            temperature=0.0,
            metadata={"task": "golden_eval", "case_id": case.case_id},
        )
        assert response.structured_output is not None
        return JudgeDecision.model_validate(response.structured_output)


def evaluate_cases(
    cases: list[GoldenCase],
    answers: list[CandidateAnswer],
    *,
    judge: SemanticJudge | None = None,
    threshold: float = 0.9,
) -> EvaluationRun:
    """Evaluate once; callers own answer generation and iteration policy."""

    answer_map = {item.case_id: item.answer for item in answers}
    if len(answer_map) != len(answers):
        raise ValueError("candidate answers contain duplicate case IDs")
    unknown = set(answer_map) - {case.case_id for case in cases}
    if unknown:
        raise ValueError(f"candidate answers contain unknown case IDs: {sorted(unknown)}")
    results: list[CaseEvaluation] = []
    missing_answers = 0
    for case in cases:
        answer = answer_map.get(case.case_id, "").strip()
        if not answer:
            missing_answers += 1
            results.append(
                CaseEvaluation(
                    case_id=case.case_id,
                    category=case.category,
                    priority=case.priority,
                    outcome=EvaluationOutcome.FAIL,
                    score=0.0,
                    grading_method="missing",
                    reason="No candidate answer was supplied.",
                )
            )
            continue
        if _normalize(answer) == _normalize(case.expected_answer):
            results.append(
                CaseEvaluation(
                    case_id=case.case_id,
                    category=case.category,
                    priority=case.priority,
                    outcome=EvaluationOutcome.PASS,
                    score=1.0,
                    grading_method="normalized_exact",
                    reason="Candidate answer matches the golden answer.",
                )
            )
            continue
        if case.evaluation_mode.casefold() == "exact match" or judge is None:
            results.append(
                CaseEvaluation(
                    case_id=case.case_id,
                    category=case.category,
                    priority=case.priority,
                    outcome=EvaluationOutcome.FAIL,
                    score=0.0,
                    grading_method="exact_only" if judge is None else "exact",
                    reason=(
                        "Answer differs from the golden answer and no semantic pass was available."
                    ),
                )
            )
            continue
        try:
            decision = judge.judge(case, answer)
            results.append(
                CaseEvaluation(
                    case_id=case.case_id,
                    category=case.category,
                    priority=case.priority,
                    outcome=(
                        EvaluationOutcome.PASS
                        if decision.passed and not decision.automatic_failure
                        else EvaluationOutcome.FAIL
                    ),
                    score=decision.score,
                    grading_method="semantic_judge",
                    reason=decision.reason,
                    missing_concepts=decision.missing_concepts,
                )
            )
        except Exception as error:
            results.append(
                CaseEvaluation(
                    case_id=case.case_id,
                    category=case.category,
                    priority=case.priority,
                    outcome=EvaluationOutcome.ERROR,
                    score=0.0,
                    grading_method="semantic_judge",
                    reason=f"Judge failed safely: {type(error).__name__}.",
                )
            )
    category_results: dict[str, list[CaseEvaluation]] = defaultdict(list)
    for result in results:
        category_results[result.category].append(result)
    passed = sum(item.outcome is EvaluationOutcome.PASS for item in results)
    failed = sum(item.outcome is EvaluationOutcome.FAIL for item in results)
    errors = sum(item.outcome is EvaluationOutcome.ERROR for item in results)
    high_priority_failures = sum(
        item.priority.casefold() == "high" and item.outcome is not EvaluationOutcome.PASS
        for item in results
    )
    pass_rate = passed / len(results) if results else 0.0
    return EvaluationRun(
        summary=EvaluationSummary(
            total_cases=len(results),
            passed_cases=passed,
            failed_cases=failed,
            error_cases=errors,
            missing_answers=missing_answers,
            high_priority_failures=high_priority_failures,
            pass_rate=pass_rate,
            threshold=threshold,
            threshold_met=(pass_rate >= threshold and errors == 0 and high_priority_failures == 0),
            category_pass_rates={
                category: sum(item.outcome is EvaluationOutcome.PASS for item in items) / len(items)
                for category, items in sorted(category_results.items())
            },
        ),
        cases=results,
    )

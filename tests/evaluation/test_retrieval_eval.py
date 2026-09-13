from pathlib import Path

from ai_career_navigator.evaluation.retrieval_eval import (
    evaluate_retrieval_gold,
    load_retrieval_gold,
)

GOLD_PATH = Path(__file__).parents[1] / "fixtures" / "retrieval_relevance_gold.json"


def test_gold_set_loads_with_unique_case_ids() -> None:
    cases = load_retrieval_gold(GOLD_PATH)

    assert len(cases) == 16
    assert len({case.case_id for case in cases}) == len(cases)


def test_deterministic_relevance_gate_scores_above_two_thirds_f1_with_known_gaps() -> None:
    cases = load_retrieval_gold(GOLD_PATH)

    result = evaluate_retrieval_gold(cases)

    # Three documented gaps (RET-002, RET-006, RET-013, RET-014) keep this below a
    # perfect score; a regression that drives it much lower means the gate broke
    # in a new way, not just the known limitations this gold set already covers.
    assert 0.7 <= result.f1 < 1.0
    assert result.true_positives + result.false_negatives == sum(
        1 for case in cases if case.expected_relevant
    )

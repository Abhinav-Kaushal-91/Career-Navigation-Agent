from ai_career_navigator.evaluation.metrics import (
    classification_metrics,
    completeness,
    dcg_at_k,
    exact_match_rate,
    ndcg_at_k,
    pool_set_metrics,
    precision_at_k,
    recall_at_k,
    set_metrics,
)


def test_classification_metrics_counts_confusion_matrix_cells() -> None:
    result = classification_metrics(
        predictions=[True, True, False, False],
        labels=[True, False, True, False],
    )

    assert result.true_positives == 1
    assert result.false_positives == 1
    assert result.false_negatives == 1
    assert result.precision == 0.5
    assert result.recall == 0.5
    assert result.f1 == 0.5


def test_classification_metrics_rejects_mismatched_lengths() -> None:
    try:
        classification_metrics([True], [True, False])
    except ValueError:
        return
    raise AssertionError("expected a ValueError for mismatched lengths")


def test_set_metrics_scores_predicted_against_gold_set() -> None:
    result = set_metrics(predicted={"python", "sql"}, actual={"python", "aws"})

    assert result.true_positives == 1
    assert result.false_positives == 1
    assert result.false_negatives == 1
    assert result.f1 == 0.5


def test_pool_set_metrics_micro_averages_across_cases() -> None:
    pairs = [
        ({"python", "sql"}, {"python", "aws"}),
        ({"java"}, {"java"}),
    ]

    result = pool_set_metrics(pairs)

    assert result.true_positives == 2
    assert result.false_positives == 1
    assert result.false_negatives == 1


def test_exact_match_rate_computes_fraction_equal() -> None:
    assert exact_match_rate(["a", "b", "c"], ["a", "x", "c"]) == 2 / 3
    assert exact_match_rate([], []) == 0.0


def test_recall_and_precision_at_k() -> None:
    ranked = ["d1", "d2", "d3", "d4"]
    relevant = {"d2", "d4"}

    assert recall_at_k(ranked, relevant, k=2) == 0.5
    assert recall_at_k(ranked, relevant, k=4) == 1.0
    assert precision_at_k(ranked, relevant, k=2) == 0.5
    assert precision_at_k(ranked, relevant, k=4) == 0.5


def test_ndcg_at_k_is_one_for_ideal_ordering_and_penalizes_reordering() -> None:
    ideal = ndcg_at_k([3.0, 2.0, 1.0], k=3)
    reordered = ndcg_at_k([1.0, 2.0, 3.0], k=3)

    assert ideal == 1.0
    assert 0.0 < reordered < 1.0


def test_dcg_at_k_matches_hand_computed_value() -> None:
    # DCG = (2^3-1)/log2(2) + (2^1-1)/log2(3) = 7/1 + 1/1.5849625... = 7.6309...
    value = dcg_at_k([3.0, 1.0], k=2)

    assert round(value, 4) == 7.6309


def test_completeness_is_fraction_of_required_fields_present() -> None:
    assert completeness({"a", "b"}, {"a", "b", "c"}) == 2 / 3
    assert completeness(set(), set()) == 1.0

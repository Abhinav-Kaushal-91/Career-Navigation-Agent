from ai_career_navigator.domain import (
    ConfidenceLevel,
    EmployerDiversity,
    MarketConcentration,
    OpportunityAvailability,
)
from ai_career_navigator.market.signals import (
    SignalInputs,
    classify_concentration,
    classify_employer_diversity,
    classify_evidence_confidence,
    classify_opportunity,
    concentration_counts,
)


def inputs(
    counts: dict[str, int],
    *,
    postings: int | None = None,
    content_attempts: int | None = None,
    content_successes: int | None = None,
) -> SignalInputs:
    total = sum(counts.values()) if postings is None else postings
    attempts = total if content_attempts is None else content_attempts
    successes = total if content_successes is None else content_successes
    return SignalInputs(
        validated_postings=total,
        employer_counts=counts,
        search_attempts=1,
        search_successes=1,
        content_attempts=attempts,
        content_successes=successes,
        duplicate_count=0,
    )


def test_twenty_postings_across_twelve_employers_are_separate_signals() -> None:
    counts = {f"Employer {index}": 2 if index < 8 else 1 for index in range(12)}
    sample = inputs(counts)

    assert classify_opportunity(sample) is OpportunityAvailability.STRONG
    assert classify_employer_diversity(sample) is EmployerDiversity.HIGH
    assert classify_concentration(sample) is MarketConcentration.LOW
    assert concentration_counts(sample) == (20, 2, 6)


def test_twenty_postings_seventeen_employers_and_twenty_two_percent_top_three_is_broad() -> None:
    # Eighteen postings name an employer: one employer has two and sixteen have one.
    # The remaining two postings have unknown employers, so the top-three known-employer
    # share is 4/18 = 22.2% while the validated sample remains 20 postings.
    counts = {"Employer 0": 2, **{f"Employer {index}": 1 for index in range(1, 17)}}
    sample = inputs(counts, postings=20)

    assert sample.distinct_employers == 17
    assert classify_employer_diversity(sample) is EmployerDiversity.HIGH
    assert classify_concentration(sample) is MarketConcentration.LOW
    assert concentration_counts(sample) == (18, 2, 4)


def test_twenty_postings_across_three_employers_can_be_strong_and_concentrated() -> None:
    sample = inputs({"A": 10, "B": 5, "C": 5})

    assert classify_opportunity(sample) is OpportunityAvailability.STRONG
    assert classify_employer_diversity(sample) is EmployerDiversity.LOW
    assert classify_concentration(sample) is MarketConcentration.HIGH


def test_twelve_postings_across_ten_employers_have_high_diversity() -> None:
    sample = inputs({**{f"E{index}": 1 for index in range(8)}, "E8": 2, "E9": 2})

    assert classify_opportunity(sample) is OpportunityAvailability.MODERATE
    assert classify_employer_diversity(sample) is EmployerDiversity.HIGH


def test_three_postings_do_not_overstate_diversity_or_concentration() -> None:
    sample = inputs({"A": 1, "B": 1, "C": 1})

    assert classify_opportunity(sample) is OpportunityAvailability.SPARSE
    assert classify_employer_diversity(sample) is EmployerDiversity.LOW
    assert classify_concentration(sample) is MarketConcentration.INSUFFICIENT_EVIDENCE


def test_four_validated_results_are_limited_regardless_of_raw_search_volume() -> None:
    sample = inputs({"A": 2, "B": 1, "C": 1})

    assert classify_opportunity(sample) is OpportunityAvailability.LIMITED


def test_large_sample_with_fetch_failures_separates_availability_and_confidence() -> None:
    sample = inputs(
        {f"E{index}": 2 for index in range(10)},
        content_attempts=30,
        content_successes=20,
    )

    assert classify_opportunity(sample) is OpportunityAvailability.STRONG
    assert classify_evidence_confidence(sample) is ConfidenceLevel.MODERATE


def test_sparse_evidence_can_be_high_confidence_when_retrieval_is_complete() -> None:
    sample = inputs({"A": 1, "B": 1})

    assert classify_opportunity(sample) is OpportunityAvailability.SPARSE
    assert classify_evidence_confidence(sample) is ConfidenceLevel.HIGH

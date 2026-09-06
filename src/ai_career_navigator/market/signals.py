"""Transparent, configurable V1 current-market signal heuristics."""

from dataclasses import dataclass

from ai_career_navigator.domain import (
    ConfidenceLevel,
    EmployerDiversity,
    MarketConcentration,
    OpportunityAvailability,
)

STRONG_POSTING_MIN = 15
STRONG_EMPLOYER_MIN = 3
MODERATE_POSTING_MIN = 8
LIMITED_POSTING_MIN = 4

DIVERSITY_HIGH_POSTING_MIN = 8
DIVERSITY_HIGH_EMPLOYER_MIN = 5
DIVERSITY_HIGH_RATIO_MIN = 0.60
DIVERSITY_MODERATE_POSTING_MIN = 5
DIVERSITY_MODERATE_EMPLOYER_MIN = 3
DIVERSITY_MODERATE_RATIO_MIN = 0.30

CONCENTRATION_POSTING_MIN = 5
CONCENTRATION_EMPLOYER_COVERAGE_MIN = 0.60
CONCENTRATION_HIGH_LARGEST_SHARE_MIN = 0.40
CONCENTRATION_HIGH_TOP_THREE_SHARE_MIN = 0.75
CONCENTRATION_LOW_LARGEST_SHARE_MAX = 0.20
CONCENTRATION_LOW_TOP_THREE_SHARE_MAX = 0.50

CONFIDENCE_HIGH_RETRIEVAL_SUCCESS_MIN = 0.90
CONFIDENCE_HIGH_EMPLOYER_COVERAGE_MIN = 0.75
CONFIDENCE_HIGH_DUPLICATE_NOISE_MAX = 0.25
CONFIDENCE_MODERATE_SEARCH_SUCCESS_MIN = 0.75
CONFIDENCE_MODERATE_RETRIEVAL_SUCCESS_MIN = 0.60
CONFIDENCE_MODERATE_EMPLOYER_COVERAGE_MIN = 0.50


@dataclass(frozen=True)
class SignalInputs:
    validated_postings: int
    employer_counts: dict[str, int]
    search_attempts: int
    search_successes: int
    content_attempts: int
    content_successes: int
    duplicate_count: int
    malformed_response_count: int = 0

    @property
    def known_employer_postings(self) -> int:
        return sum(self.employer_counts.values())

    @property
    def distinct_employers(self) -> int:
        return len(self.employer_counts)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def classify_opportunity(inputs: SignalInputs) -> OpportunityAvailability:
    postings = inputs.validated_postings
    if postings == 0:
        return OpportunityAvailability.INSUFFICIENT_EVIDENCE
    if postings >= STRONG_POSTING_MIN and inputs.distinct_employers >= STRONG_EMPLOYER_MIN:
        return OpportunityAvailability.STRONG
    if postings >= MODERATE_POSTING_MIN:
        return OpportunityAvailability.MODERATE
    if postings >= LIMITED_POSTING_MIN:
        return OpportunityAvailability.LIMITED
    return OpportunityAvailability.SPARSE


def classify_employer_diversity(inputs: SignalInputs) -> EmployerDiversity:
    postings = inputs.validated_postings
    employers = inputs.distinct_employers
    if postings == 0 or employers == 0:
        return EmployerDiversity.INSUFFICIENT_EVIDENCE
    ratio = employers / postings
    if (
        postings >= DIVERSITY_HIGH_POSTING_MIN
        and employers >= DIVERSITY_HIGH_EMPLOYER_MIN
        and ratio >= DIVERSITY_HIGH_RATIO_MIN
    ):
        return EmployerDiversity.HIGH
    if (
        postings >= DIVERSITY_MODERATE_POSTING_MIN
        and employers >= DIVERSITY_MODERATE_EMPLOYER_MIN
        and ratio >= DIVERSITY_MODERATE_RATIO_MIN
    ):
        return EmployerDiversity.MODERATE
    return EmployerDiversity.LOW


def classify_concentration(inputs: SignalInputs) -> MarketConcentration:
    known = inputs.known_employer_postings
    coverage = _ratio(known, inputs.validated_postings)
    if known < CONCENTRATION_POSTING_MIN or coverage < CONCENTRATION_EMPLOYER_COVERAGE_MIN:
        return MarketConcentration.INSUFFICIENT_EVIDENCE
    counts = sorted(inputs.employer_counts.values(), reverse=True)
    largest_share = counts[0] / known
    top_three_share = sum(counts[:3]) / known
    if (
        largest_share >= CONCENTRATION_HIGH_LARGEST_SHARE_MIN
        or top_three_share >= CONCENTRATION_HIGH_TOP_THREE_SHARE_MIN
    ):
        return MarketConcentration.HIGH
    if (
        largest_share <= CONCENTRATION_LOW_LARGEST_SHARE_MAX
        and top_three_share <= CONCENTRATION_LOW_TOP_THREE_SHARE_MAX
    ):
        return MarketConcentration.LOW
    return MarketConcentration.MODERATE


def classify_evidence_confidence(inputs: SignalInputs) -> ConfidenceLevel:
    if inputs.validated_postings == 0 or inputs.content_successes == 0:
        return ConfidenceLevel.INSUFFICIENT
    search_success = _ratio(inputs.search_successes, inputs.search_attempts)
    retrieval_success = _ratio(inputs.content_successes, inputs.content_attempts)
    employer_coverage = _ratio(inputs.known_employer_postings, inputs.validated_postings)
    pre_deduplication = inputs.validated_postings + inputs.duplicate_count
    duplicate_noise = _ratio(inputs.duplicate_count, pre_deduplication)
    if (
        search_success == 1.0
        and retrieval_success >= CONFIDENCE_HIGH_RETRIEVAL_SUCCESS_MIN
        and employer_coverage >= CONFIDENCE_HIGH_EMPLOYER_COVERAGE_MIN
        and duplicate_noise <= CONFIDENCE_HIGH_DUPLICATE_NOISE_MAX
        and inputs.malformed_response_count == 0
    ):
        return ConfidenceLevel.HIGH
    if (
        search_success >= CONFIDENCE_MODERATE_SEARCH_SUCCESS_MIN
        and retrieval_success >= CONFIDENCE_MODERATE_RETRIEVAL_SUCCESS_MIN
        and employer_coverage >= CONFIDENCE_MODERATE_EMPLOYER_COVERAGE_MIN
    ):
        return ConfidenceLevel.MODERATE
    return ConfidenceLevel.LOW


def concentration_counts(inputs: SignalInputs) -> tuple[int, int, int]:
    counts = sorted(inputs.employer_counts.values(), reverse=True)
    return inputs.known_employer_postings, counts[0] if counts else 0, sum(counts[:3])

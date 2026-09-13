from pathlib import Path
from uuid import uuid4

from ai_career_navigator.career.synthesis_schemas import (
    AdvantageStrengthType,
    CareerAdvantageDraft,
    CareerSynthesisDraft,
    GroupedCareerGapDraft,
    TransferableStrengthDraft,
)
from ai_career_navigator.evaluation.grounding_eval import (
    GroundingGoldCase,
    evaluate_quote_grounding,
    is_grounded,
    synthesis_citation_accuracy,
)

GOLD_PATH = Path(__file__).parents[1] / "fixtures" / "quote_grounding_gold.json"


def test_gold_set_loads_with_unique_case_ids() -> None:
    import json

    payload = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    cases = [GroundingGoldCase.model_validate(item) for item in payload]

    assert len(cases) == 10
    assert len({case.case_id for case in cases}) == len(cases)


def test_quote_grounding_gold_set_is_perfectly_classified() -> None:
    import json

    payload = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    cases = [GroundingGoldCase.model_validate(item) for item in payload]

    result = evaluate_quote_grounding(cases)

    assert result.f1 == 1.0


def test_hallucinated_quote_is_not_grounded() -> None:
    case = GroundingGoldCase(
        case_id="X-1",
        posting_text="We require 5 years of Python experience.",
        source_quote="We require a PhD in astrophysics.",
        normalized_capability="PhD in astrophysics",
        expected_grounded=False,
    )

    assert is_grounded(case) is False


def test_real_quote_with_overstated_capability_is_not_grounded() -> None:
    case = GroundingGoldCase(
        case_id="X-2",
        posting_text="Strong communication skills are required.",
        source_quote="Strong communication skills are required.",
        normalized_capability="certified expert leadership",
        expected_grounded=False,
    )

    assert is_grounded(case) is False


def _advantage(evidence_ids: list, comparison_ids: list) -> CareerAdvantageDraft:
    return CareerAdvantageDraft(
        title="Advantage",
        explanation="Explanation.",
        supporting_comparison_ids=comparison_ids,
        supporting_evidence_ids=evidence_ids,
        strength_type=AdvantageStrengthType.DIRECT,
    )


def test_synthesis_citation_accuracy_flags_ids_that_do_not_resolve() -> None:
    known_evidence = uuid4()
    known_comparison = uuid4()
    hallucinated_evidence = uuid4()
    draft = CareerSynthesisDraft(
        strongest_advantages=[
            _advantage([known_evidence, hallucinated_evidence], [known_comparison])
        ],
        assessment_summary="Summary.",
    )

    result = synthesis_citation_accuracy(
        draft,
        known_evidence_ids={known_evidence},
        known_comparison_ids={known_comparison},
        known_gap_ids=set(),
    )

    assert result.total_citations == 3
    assert result.valid_citations == 2
    assert round(result.accuracy, 4) == round(2 / 3, 4)


def test_synthesis_citation_accuracy_checks_transferable_strengths_and_gaps() -> None:
    known_evidence = uuid4()
    known_gap = uuid4()
    draft = CareerSynthesisDraft(
        transferable_strengths=[
            TransferableStrengthDraft(
                source_capability="Python",
                target_application="ML pipelines",
                explanation="Explanation.",
                supporting_comparison_ids=[uuid4()],
                supporting_evidence_ids=[known_evidence],
            )
        ],
        grouped_gaps=[
            GroupedCareerGapDraft(
                title="Gap",
                explanation="Explanation.",
                underlying_gap_ids=[known_gap],
                what_candidate_already_has="Has X.",
                what_is_missing="Missing Y.",
                evidence_to_build="Build Y.",
            )
        ],
        assessment_summary="Summary.",
    )

    result = synthesis_citation_accuracy(
        draft,
        known_evidence_ids={known_evidence},
        known_comparison_ids=set(),
        known_gap_ids={known_gap},
    )

    assert result.total_citations == 3
    assert result.valid_citations == 2


def test_synthesis_citation_accuracy_is_perfect_for_an_empty_draft() -> None:
    draft = CareerSynthesisDraft(assessment_summary="Summary.")

    result = synthesis_citation_accuracy(
        draft, known_evidence_ids=set(), known_comparison_ids=set(), known_gap_ids=set()
    )

    assert result.total_citations == 0
    assert result.accuracy == 1.0

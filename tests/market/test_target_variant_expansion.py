import json
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from ai_career_navigator.domain import ConfidenceLevel, JobPosting, SourceRecord
from ai_career_navigator.market import (
    MarketPostingEvidence,
    RoleProfileStatus,
    TargetVariantAssessmentResult,
    TargetVariantClassification,
    analyze_market_requirements,
)
from ai_career_navigator.market.schemas import MarketPageContent
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.providers import FakeModelProvider

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


def evidence(
    index: int, title: str, *, capability: str = "Product Strategy"
) -> MarketPostingEvidence:
    url = f"https://employer{index}.example/jobs/{index}"
    quote = f"{capability} experience required"
    source = SourceRecord(
        source_type="ADZUNA",
        title=title,
        url=url,
        employer=f"Employer {index}",
        geography="Toronto, Canada",
        retrieval_date=date(2026, 9, 5),
    )
    posting = JobPosting(
        source_id=source.source_id,
        original_title=title,
        normalized_title=title,
        employer=source.employer,
        location=source.geography,
        location_evidence_text=source.geography,
        retrieved_at=NOW,
        active_status="ACTIVE",
        extraction_confidence=ConfidenceLevel.HIGH,
    )
    return MarketPostingEvidence(
        posting=posting,
        primary_source=source,
        primary_content=MarketPageContent(
            url=url,
            title=title,
            employer=source.employer,
            location=source.geography,
            markdown=f"Qualifications: {quote}.",
        ),
    )


def extraction(capability: str = "Product Strategy") -> str:
    return json.dumps(
        {
            "requirements": [
                {
                    "source_quote": f"{capability} experience required",
                    "category": "LEADERSHIP",
                    "normalized_capability": capability,
                    "mandatory": True,
                    "preferred": False,
                    "years_required": None,
                    "maturity_expected": "PRODUCTION",
                    "confidence": "HIGH",
                    "item_type": "HIRING_CAPABILITY",
                }
            ],
            "limitations": [],
        }
    )


def variant_result(
    candidates: list[MarketPostingEvidence],
    *,
    classification: TargetVariantClassification = TargetVariantClassification.VALID_TARGET_VARIANT,
) -> str:
    return json.dumps(
        {
            "assessments": [
                {
                    "candidate_title": item.posting.original_title,
                    "classification": classification.value,
                    "functional_overlap": 0.9,
                    "ownership_overlap": 0.9,
                    "scope_overlap": 0.9,
                    "seniority_alignment": "ALIGNED",
                    "outcome_overlap": 0.9,
                    "core_requirement_overlap": 0.9,
                    "evidence_confidence": "HIGH",
                    "supporting_posting_ids": [str(item.posting.posting_id)],
                    "reasoning_summary": (
                        "Observed role evidence materially aligns."
                        if classification is TargetVariantClassification.VALID_TARGET_VARIANT
                        else "Shared wording does not establish equivalent function and ownership."
                    ),
                }
                for item in candidates
            ]
        }
    )


def gateway(*outcomes: str) -> tuple[ModelGateway, FakeModelProvider]:
    provider = FakeModelProvider(outcomes=outcomes)
    return (
        ModelGateway(
            provider=provider,
            models={
                ModelRole.EXTRACTION: "fake-extraction",
                ModelRole.VALIDATION: "fake-validation",
            },
            timeout_seconds=10,
            max_retries=0,
            sleeper=lambda _: None,
        ),
        provider,
    )


def test_variant_result_accepts_only_the_observed_redundant_nemotron_flag() -> None:
    candidate = evidence(1, "Product Manager, AI")
    payload = json.loads(variant_result([candidate]))
    payload["target_variant_assessment_result"] = True

    parsed = TargetVariantAssessmentResult.model_validate(payload)

    assert len(parsed.assessments) == 1
    assert "target_variant_assessment_result" not in parsed.model_dump()

    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        TargetVariantAssessmentResult.model_validate(payload)


def test_valid_observed_variants_recover_a_provisional_profile() -> None:
    exact = evidence(1, "Product Manager")
    variants = [evidence(2, "AI Product Manager"), evidence(3, "Product Manager, AI")]
    model_gateway, provider = gateway(
        extraction(), extraction(), extraction(), variant_result(variants)
    )

    result = analyze_market_requirements(
        [exact, *variants],
        target_role="Product Manager",
        geography="Toronto, Canada",
        model_gateway=model_gateway,
        enable_target_variant_expansion=True,
        posting_limit=1,
        now=NOW,
    )

    assert result.initial_canonical_profile.profile_status is RoleProfileStatus.INSUFFICIENT
    assert result.canonical_profile.profile_status is RoleProfileStatus.PROVISIONAL
    assert result.canonical_profile.confidence is ConfidenceLevel.LOW
    assert result.canonical_profile.exact_posting_count == 1
    assert result.canonical_profile.variant_posting_count == 2
    assert result.canonical_profile.distinct_exact_employer_count == 1
    assert result.canonical_profile.distinct_variant_employer_count == 2
    assert len(result.requirements) == 1
    assert all(item.promoted for item in result.target_variant_audits)
    assert [call.request.role for call in provider.calls].count(ModelRole.VALIDATION) == 1


def test_related_title_is_not_promoted_by_keyword_overlap_alone() -> None:
    exact = evidence(1, "Product Manager")
    related = evidence(2, "Data Product Manager")
    model_gateway, _ = gateway(
        extraction(),
        extraction(),
        variant_result([related], classification=TargetVariantClassification.RELATED_TITLE),
    )

    result = analyze_market_requirements(
        [exact, related],
        target_role="Product Manager",
        geography="Toronto, Canada",
        model_gateway=model_gateway,
        enable_target_variant_expansion=True,
        posting_limit=1,
        now=NOW,
    )

    assert result.canonical_profile.profile_status is RoleProfileStatus.INSUFFICIENT
    assert result.canonical_profile.variant_posting_count == 0
    assert result.canonical_profile.related_posting_count == 1
    audit = result.target_variant_audits[0]
    assert audit.promoted is False
    assert audit.source_posting_ids == [related.posting.posting_id]
    assert audit.reason == "Shared wording does not establish equivalent function and ownership."


def test_seniority_mismatch_is_rejected_without_semantic_promotion() -> None:
    exact = evidence(1, "Product Manager")
    senior = evidence(2, "Senior Director, Product Management")
    model_gateway, provider = gateway(extraction(), extraction())

    result = analyze_market_requirements(
        [exact, senior],
        target_role="Product Manager",
        geography="Toronto, Canada",
        model_gateway=model_gateway,
        enable_target_variant_expansion=True,
        posting_limit=1,
        now=NOW,
    )

    assert result.target_variant_audits[0].seniority_alignment.value == "MISALIGNED"
    assert result.target_variant_audits[0].promoted is False
    assert all(call.request.role is ModelRole.EXTRACTION for call in provider.calls)


def test_expansion_does_not_run_when_initial_profile_is_sufficient() -> None:
    exact = [evidence(1, "Product Manager"), evidence(2, "Product Manager")]
    related = evidence(3, "AI Product Manager")
    model_gateway, provider = gateway(extraction(), extraction())

    result = analyze_market_requirements(
        [*exact, related],
        target_role="Product Manager",
        geography="Toronto, Canada",
        model_gateway=model_gateway,
        enable_target_variant_expansion=True,
        posting_limit=2,
        now=NOW,
    )

    assert result.initial_canonical_profile.profile_status is not RoleProfileStatus.INSUFFICIENT
    assert result.target_variant_expansion_attempted is False
    assert result.target_variant_audits == []
    assert len(provider.calls) == 2


def test_expansion_remains_bounded_to_five_titles_and_one_validation_call() -> None:
    exact = evidence(1, "Product Manager")
    related = [
        evidence(index, f"Product Manager {letter}") for index, letter in enumerate("ABCDEF", 2)
    ]
    considered = related[:5]
    model_gateway, provider = gateway(
        extraction(),
        *(extraction() for _ in considered),
        variant_result(considered, classification=TargetVariantClassification.RELATED_TITLE),
    )

    result = analyze_market_requirements(
        [exact, *related],
        target_role="Product Manager",
        geography="Toronto, Canada",
        model_gateway=model_gateway,
        enable_target_variant_expansion=True,
        posting_limit=1,
        now=NOW,
    )

    validation_calls = [
        call
        for call in provider.calls
        if call.request.metadata.get("task_type") == "target_variant_validation"
    ]
    assert len(result.target_variant_audits) == 5
    assert len(validation_calls) == 1
    assert len(provider.calls) == 7


def test_variant_policy_is_role_neutral() -> None:
    exact = evidence(1, "Software Engineer", capability="Distributed Systems")
    variant = evidence(2, "Backend Software Engineer", capability="Distributed Systems")
    model_gateway, _ = gateway(
        extraction("Distributed Systems"),
        extraction("Distributed Systems"),
        variant_result([variant]),
    )

    result = analyze_market_requirements(
        [exact, variant],
        target_role="Software Engineer",
        geography="Toronto, Canada",
        model_gateway=model_gateway,
        enable_target_variant_expansion=True,
        posting_limit=1,
        now=NOW,
    )

    assert result.canonical_profile.profile_status is RoleProfileStatus.PROVISIONAL
    assert result.canonical_profile.variant_posting_count == 1
    assert result.target_variant_audits[0].promoted is True


def test_related_context_does_not_enter_primary_denominator() -> None:
    exact = evidence(1, "Product Manager")
    variants = [evidence(2, "AI Product Manager"), evidence(3, "Product Manager, AI")]
    related = evidence(4, "Data Product Manager")
    # The model can validate only specific candidates; use a complete result with two promotions.
    promoted_output = json.loads(variant_result(variants))
    related_output = json.loads(
        variant_result([related], classification=TargetVariantClassification.RELATED_TITLE)
    )
    model_gateway, _ = gateway(
        extraction(),
        extraction(),
        extraction(),
        extraction(),
        json.dumps({"assessments": promoted_output["assessments"] + related_output["assessments"]}),
    )
    result = analyze_market_requirements(
        [exact, *variants, related],
        target_role="Product Manager",
        geography="Toronto, Canada",
        model_gateway=model_gateway,
        enable_target_variant_expansion=True,
        posting_limit=1,
        now=NOW,
    )

    canonical = result.canonical_profile.requirements[0]
    assert canonical.primary_support_ratio == 1
    assert canonical.exact_support_count == 1
    assert canonical.variant_support_count == 2
    assert canonical.exact_employer_support_count == 1
    assert canonical.variant_employer_support_count == 2
    assert canonical.related_support_count == 1
    assert result.canonical_profile.profile_status is RoleProfileStatus.PROVISIONAL
    assert len(result.requirements) == 1

import json
from datetime import UTC, date, datetime
from uuid import uuid4

from ai_career_navigator.career import (
    assess_candidate_accessibility,
    compare_candidate_to_requirements,
)
from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateProfile,
    CareerGoal,
    CareerStage,
    ComparisonScope,
    ConfidenceLevel,
    CurrentMarketSnapshot,
    EmployerDiversity,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
    GoalType,
    MarketConcentration,
    OpportunityAvailability,
    RequirementCategory,
    RequirementStatementType,
    RoleRequirement,
)
from ai_career_navigator.market import (
    MarketRequirementAnalysis,
    MarketRequirementSummary,
    PostingCandidate,
    PostingCandidateAssessment,
    PostingGeographyStatus,
    PostingRequirementAudit,
    PostingRequirementAuditItem,
    PostingTitleMatch,
    RequirementAuditStatus,
    RequirementItemType,
    RequirementRunStatus,
    RoleProfileStatus,
    SourceAgreement,
)
from ai_career_navigator.market.role_profile import (
    build_canonical_target_role_profile,
    quote_capability_alignment,
)
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.providers import FakeModelProvider

NOW = datetime(2026, 9, 5, tzinfo=UTC)


def _posting(index: int, match: PostingTitleMatch, employer: str):
    posting_id = uuid4()
    candidate = PostingCandidate(
        posting_id=posting_id,
        source_id=uuid4(),
        source_reference=f"source-{index}",
        source_reference_text=f"Role {index} at {employer}",
        title="Product Manager" if match is PostingTitleMatch.EXACT_TARGET else "Related Role",
        employer=employer,
        location="Toronto",
        posting_text="Product roadmap ownership and stakeholder partnership required.",
        extraction_confidence=ConfidenceLevel.HIGH,
    )
    assessment = PostingCandidateAssessment(
        candidate=candidate,
        geography_status=PostingGeographyStatus.IN_SCOPE,
        title_match=match,
    )
    return posting_id, assessment


def _build(specs: list[tuple[str, str, PostingTitleMatch, str]]):
    assessments = []
    requirements = []
    audits = []
    for index, (quote, name, match, employer) in enumerate(specs):
        posting_id, assessment = _posting(index, match, employer)
        assessments.append(assessment)
        requirement = RoleRequirement(
            posting_id=posting_id,
            category=RequirementCategory.LEADERSHIP,
            requirement_text=quote,
            normalized_capability=name,
            mandatory=True,
            extraction_confidence=ConfidenceLevel.HIGH,
        )
        requirements.append(requirement)
        audits.append(
            PostingRequirementAudit(
                posting_id=posting_id,
                title=assessment.candidate.title,
                employer=employer,
                location="Toronto",
                title_classification=match,
                source_reference=assessment.candidate.source_reference,
                extraction_status=RequirementAuditStatus.SUCCEEDED,
                items=[
                    PostingRequirementAuditItem(
                        source_requirement_id=requirement.requirement_id,
                        source_quote=quote,
                        normalized_capability=name,
                        category=requirement.category,
                        item_type=RequirementItemType.HIRING_CAPABILITY,
                        accepted=True,
                        final_classification="ACCEPTED_PENDING_CANONICALIZATION",
                    )
                ],
            )
        )
    exact = sum(item.candidate.title == "Product Manager" for item in assessments)
    related = len(assessments) - exact
    summary = MarketRequirementSummary(
        target_role="Product Manager",
        geography="Toronto",
        source_page_count=len(assessments),
        identified_candidate_count=len(assessments),
        validated_in_scope_posting_count=len(assessments),
        analyzed_posting_count=len(assessments),
        exact_title_analyzed_count=exact,
        related_title_analyzed_count=related,
        out_of_scope_count=0,
        unclear_geography_count=0,
        irrelevant_title_count=0,
    )
    profile, audits = build_canonical_target_role_profile(
        target_role="Product Manager",
        geography="Toronto",
        requirements=requirements,
        assessments=assessments,
        summary=summary,
        posting_audits=audits,
        generated_at=NOW,
    )
    return profile, requirements, assessments, audits, summary


def test_independent_employers_create_one_canonical_signal() -> None:
    profile, *_ = _build(
        [
            (
                "Stakeholder partnership required",
                "Stakeholder Partnership",
                PostingTitleMatch.EXACT_TARGET,
                "A",
            ),
            (
                "Stakeholder communication required",
                "Stakeholder Communication",
                PostingTitleMatch.EXACT_TARGET,
                "B",
            ),
            (
                "Stakeholder management required",
                "Stakeholder Management",
                PostingTitleMatch.EXACT_TARGET,
                "A",
            ),
        ]
    )
    assert len(profile.requirements) == 1
    assert profile.requirements[0].employer_support_count == 2
    assert profile.requirements[0].posting_support_count == 3


def test_repetition_from_one_employer_is_one_independent_signal() -> None:
    profile, *_ = _build(
        [
            ("Own product roadmaps", "Roadmap Ownership", PostingTitleMatch.EXACT_TARGET, "A"),
            ("Roadmap prioritization", "Roadmap Management", PostingTitleMatch.EXACT_TARGET, "A"),
            ("Product roadmap ownership", "Roadmap Ownership", PostingTitleMatch.EXACT_TARGET, "A"),
        ]
    )
    item = profile.requirements[0]
    assert item.employer_support_count == 1
    assert item.posting_support_count == 3


def test_provider_support_is_separate_from_independent_employer_support() -> None:
    _, requirements, assessments, audits, summary = _build(
        [
            ("Python required", "Python", PostingTitleMatch.EXACT_TARGET, "A"),
            ("Python required", "Python", PostingTitleMatch.EXACT_TARGET, "B"),
        ]
    )
    assessments = [
        item.model_copy(
            update={
                "candidate": item.candidate.model_copy(
                    update={
                        "provider": provider,
                        "provider_sources": [provider],
                    }
                )
            }
        )
        for item, provider in zip(assessments, ("ADZUNA", "YOU"), strict=True)
    ]

    profile, _ = build_canonical_target_role_profile(
        target_role="Product Manager",
        geography="Toronto",
        requirements=requirements,
        assessments=assessments,
        summary=summary,
        posting_audits=audits,
        generated_at=NOW,
    )

    item = profile.requirements[0]
    assert item.employer_support_count == 2
    assert item.adzuna_support_count == 1
    assert item.you_support_count == 1
    assert item.qualification_support_count == 2
    assert item.responsibility_support_count == 0
    assert item.provider_sources == ["ADZUNA", "YOU"]
    assert len(item.source_provenance) == 2
    assert item.source_agreement is SourceAgreement.CROSS_SOURCE_CONFIRMED


def test_mixed_duty_and_qualification_keep_separate_lineage() -> None:
    _, requirements, assessments, audits, summary = _build(
        [
            (
                "Product discovery experience required",
                "Product Discovery",
                PostingTitleMatch.EXACT_TARGET,
                "A",
            ),
            (
                "Product discovery experience required",
                "Product Discovery",
                PostingTitleMatch.EXACT_TARGET,
                "B",
            ),
        ]
    )
    duties = [
        RoleRequirement(
            posting_id=assessment.candidate.posting_id,
            category=RequirementCategory.LEADERSHIP,
            statement_type=RequirementStatementType.ROLE_RESPONSIBILITY,
            requirement_text="Conduct product discovery",
            normalized_capability="Product Discovery",
            extraction_confidence=ConfidenceLevel.HIGH,
        )
        for assessment in assessments
    ]

    profile, _ = build_canonical_target_role_profile(
        target_role="Product Manager",
        geography="Toronto",
        requirements=[*duties, *requirements],
        assessments=assessments,
        summary=summary,
        posting_audits=audits,
        generated_at=NOW,
    )

    item = profile.comparison_requirements[0]
    assert item.responsibility_support_count == 2
    assert item.qualification_support_count == 2
    assert item.representative_source_quotes[0] == "Product discovery experience required"
    assert item.comparison_requirement_ids == [
        requirement.requirement_id for requirement in requirements
    ]


def test_two_provider_records_for_one_employer_do_not_create_false_agreement() -> None:
    _, requirements, assessments, audits, summary = _build(
        [
            ("Python required", "Python", PostingTitleMatch.EXACT_TARGET, "A"),
            ("Python required", "Python", PostingTitleMatch.EXACT_TARGET, "A"),
        ]
    )
    assessments = [
        item.model_copy(
            update={
                "candidate": item.candidate.model_copy(
                    update={"provider_sources": [provider]}
                )
            }
        )
        for item, provider in zip(assessments, ("ADZUNA", "YOU"), strict=True)
    ]

    profile, _ = build_canonical_target_role_profile(
        target_role="Product Manager",
        geography="Toronto",
        requirements=requirements,
        assessments=assessments,
        summary=summary,
        posting_audits=audits,
        generated_at=NOW,
    )

    item = profile.requirements[0]
    assert item.employer_support_count == 1
    assert item.source_agreement is SourceAgreement.LOW_SUPPORT


def test_shared_ownership_word_does_not_merge_distinct_semantics() -> None:
    profile, *_ = _build(
        [
            (
                "Product vision ownership",
                "Product Vision Ownership",
                PostingTitleMatch.EXACT_TARGET,
                "A",
            ),
            ("Budget ownership", "Budget Ownership", PostingTitleMatch.EXACT_TARGET, "B"),
        ]
    )
    names = {item.display_name for item in [*profile.requirements, *profile.optional_signals]}
    assert names == {"Product Vision Ownership", "Budget Ownership"}


def test_related_only_requirement_stays_context_only() -> None:
    profile, *_ = _build(
        [("People leadership required", "People Leadership", PostingTitleMatch.RELATED_TITLE, "A")]
    )
    assert not profile.comparison_requirements
    assert [item.display_name for item in profile.related_context] == ["People Leadership"]


def test_sparse_exact_profile_is_provisional() -> None:
    profile, *_ = _build(
        [
            (
                "Stakeholder partnership required",
                "Stakeholder Partnership",
                PostingTitleMatch.EXACT_TARGET,
                "A",
            ),
            (
                "Stakeholder communication required",
                "Stakeholder Communication",
                PostingTitleMatch.EXACT_TARGET,
                "B",
            ),
            (
                "Stakeholder management required",
                "Stakeholder Management",
                PostingTitleMatch.EXACT_TARGET,
                "C",
            ),
        ]
    )
    assert profile.profile_status is RoleProfileStatus.PROVISIONAL
    assert profile.confidence is not ConfidenceLevel.HIGH


def test_related_support_does_not_change_primary_frequency() -> None:
    profile, *_ = _build(
        [
            (
                "Stakeholder partnership required",
                "Stakeholder Partnership",
                PostingTitleMatch.EXACT_TARGET,
                "A",
            ),
            (
                "Product vision ownership",
                "Product Vision Ownership",
                PostingTitleMatch.EXACT_TARGET,
                "B",
            ),
            (
                "Stakeholder management required",
                "Stakeholder Management",
                PostingTitleMatch.RELATED_TITLE,
                "C",
            ),
        ]
    )
    item = next(
        item for item in profile.requirements if item.display_name == "Stakeholder Collaboration"
    )
    assert item.primary_support_ratio == 0.5
    assert item.exact_support_count == 1
    assert item.related_support_count == 1


def test_semantically_mismatched_quote_is_rejected() -> None:
    aligned, reason = quote_capability_alignment(
        "Work closely with senior stakeholders to define requirements.", "Cloud Architecture"
    )
    assert not aligned
    assert reason


def test_comparison_and_gap_preserve_canonical_provenance_once() -> None:
    canonical, raw, assessments, audits, summary = _build(
        [
            (
                "Stakeholder partnership required",
                "Stakeholder Partnership",
                PostingTitleMatch.EXACT_TARGET,
                "A",
            ),
            (
                "Stakeholder communication required",
                "Stakeholder Communication",
                PostingTitleMatch.EXACT_TARGET,
                "B",
            ),
        ]
    )
    analysis = MarketRequirementAnalysis(
        status=RequirementRunStatus.SUCCEEDED,
        assessments=assessments,
        requirements=[item.as_role_requirement() for item in canonical.comparison_requirements],
        raw_requirements=raw,
        canonical_profile=canonical,
        posting_audits=audits,
        summary=summary,
    )
    evidence = EvidenceItem(
        evidence_type="skill",
        source_type="manual",
        source_reference="profile",
        capability="Unrelated Evidence",
        description="Confirmed production work.",
        maturity_level=EvidenceMaturity.PRODUCTION,
        confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        approved_by_user=True,
        created_at=NOW,
    )
    candidate = CandidateProfile(
        career_stage=CareerStage.MID_CAREER,
        evidence_items=[evidence],
        approval_status=ApprovalStatus.APPROVED,
        confirmed_at=NOW,
        created_at=NOW,
    )
    canonical_item = canonical.comparison_requirements[0]
    provider = FakeModelProvider(
        outcomes=[
            json.dumps(
                {
                    "requirement_id": str(canonical_item.canonical_requirement_id),
                    "match_type": "NO_CONFIRMED_MATCH",
                    "supporting_evidence_ids": [],
                    "candidate_maturity": None,
                    "target_maturity": None,
                    "transferable_capability": None,
                    "remaining_difference": "No direct evidence.",
                    "confidence": "HIGH",
                    "explanation": "No evidence.",
                }
            )
        ]
    )
    gateway = ModelGateway(
        provider=provider,
        models={ModelRole.REASONING: "fake"},
        timeout_seconds=10,
        max_retries=0,
    )
    comparison = compare_candidate_to_requirements(candidate, analysis, gateway)
    assert len(comparison.comparisons) == 1
    assert (
        comparison.comparisons[0].source_requirement_ids
        == canonical_item.supporting_requirement_ids
    )
    snapshot = CurrentMarketSnapshot(
        target_role="Product Manager",
        geography="Toronto",
        search_date=date(2026, 9, 5),
        exact_title_count=2,
        related_title_count=0,
        validated_posting_count=2,
        distinct_employer_count=2,
        employer_posting_counts={"A": 1, "B": 1},
        known_employer_posting_count=2,
        largest_employer_posting_count=1,
        top_three_employer_posting_count=2,
        opportunity_availability=OpportunityAvailability.MODERATE,
        employer_diversity=EmployerDiversity.MODERATE,
        market_concentration=MarketConcentration.LOW,
        evidence_confidence=ConfidenceLevel.MODERATE,
    )
    goal = CareerGoal(
        goal_type=GoalType.TARGET_CAREER_PATH,
        target_role="Product Manager",
        approval_status=ApprovalStatus.APPROVED,
        approved_at=NOW,
    )
    gaps = assess_candidate_accessibility(
        candidate, goal, snapshot, analysis, comparison.comparisons
    )
    assert gaps.role_assessment.gaps[0].requirement_id == canonical_item.canonical_requirement_id
    assert (
        gaps.role_assessment.gaps[0].source_requirement_ids
        == canonical_item.supporting_requirement_ids
    )
    assert gaps.role_assessment.gaps[0].comparison_scope is ComparisonScope.EXACT_TARGET

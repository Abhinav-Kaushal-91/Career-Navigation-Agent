"""Offline audit replay and generic evidence-track safety regressions."""

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from ai_career_navigator.career.evidence_coverage import readiness_coverage_issue
from ai_career_navigator.domain import (
    ComparisonScope,
    ConfidenceLevel,
    MatchType,
    RequirementComparison,
    RequirementStatementType,
)
from ai_career_navigator.market.requirement_schemas import (
    MarketRequirementAnalysis,
    MarketRequirementSummary,
    PostingCandidate,
    PostingCandidateAssessment,
    PostingGeographyStatus,
    PostingTitleMatch,
    RequirementRunStatus,
)
from ai_career_navigator.market.requirements import _quality_and_audit, extract_posting_requirements
from ai_career_navigator.market.role_profile import (
    build_canonical_target_role_profile,
    quote_capability_alignment,
)
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.providers import FakeModelProvider


def replay_saved_audit():
    saved = json.loads(
        (Path(__file__).parents[1] / "fixtures/evidence_60_item_audit.json").read_text()
    )
    raw, assessments, audits = [], [], []
    for posting in saved["postings"]:
        # Only audit quotes survive: this does NOT pretend to replay a full original JD.
        candidate = PostingCandidate(
            posting_id=UUID(posting["posting_id"]),
            source_id=uuid4(),
            source_reference=posting["source"],
            source_reference_text=posting["title"],
            title=posting["title"],
            employer=posting["employer"],
            location=posting["location"],
            posting_text="\n".join(item["source_quote"] for item in posting["requirements"]),
            extraction_confidence=ConfidenceLevel.HIGH,
            retrieval_quality="LOW",
        )
        assessment = PostingCandidateAssessment(
            candidate=candidate,
            geography_status=PostingGeographyStatus.IN_SCOPE,
            title_match=PostingTitleMatch.EXACT_TARGET,
        )
        provider = FakeModelProvider(
            outcomes=[
                json.dumps(
                    {
                        "requirements": [
                            {
                                "source_quote": row["source_quote"],
                                "category": row["category"],
                                "normalized_capability": row["normalized_requirement"],
                                "item_type": row["item_type"],
                                "mandatory": row["mandatory"] or False,
                                "preferred": row["preferred"] or False,
                                "confidence": "HIGH",
                            }
                            for row in posting["requirements"]
                        ]
                    }
                )
            ]
        )
        gateway = ModelGateway(
            provider=provider,
            models={ModelRole.EXTRACTION: "offline"},
            timeout_seconds=1,
            max_retries=0,
        )
        outcome = extract_posting_requirements(assessment, gateway)
        _, audit = _quality_and_audit(assessment, outcome, enrichment_used=False)
        raw.extend(outcome.requirements)
        assessments.append(assessment)
        audits.append(audit)
    summary = MarketRequirementSummary(
        target_role="Senior Java Developer",
        geography="Canada",
        source_page_count=10,
        identified_candidate_count=10,
        validated_in_scope_posting_count=10,
        analyzed_posting_count=10,
        exact_title_analyzed_count=10,
        related_title_analyzed_count=0,
        out_of_scope_count=0,
        unclear_geography_count=0,
        irrelevant_title_count=0,
    )
    canonical, audits = build_canonical_target_role_profile(
        target_role=summary.target_role,
        geography=summary.geography,
        requirements=raw,
        assessments=assessments,
        summary=summary,
        posting_audits=audits,
        generated_at=datetime.now(UTC),
    )
    analysis = MarketRequirementAnalysis(
        status=RequirementRunStatus.SUCCEEDED,
        summary=summary,
        canonical_profile=canonical,
        requirements=[item.as_role_requirement() for item in canonical.assessment_requirements],
        raw_requirements=raw,
    )
    return analysis, audits


def test_all_sixty_items_remain_auditable_and_useful_expectations_survive():
    analysis, audits = replay_saved_audit()
    rows = [item for audit in audits for item in audit.items]
    assert len(rows) == len({item.audit_item_id for item in rows}) == 60
    counts = Counter(item.final_classification for item in rows)
    assert counts == {
        "RETAINED_ROLE_CONTEXT": 5,
        "PREFERENCE": 1,
        "REJECTED_NON_REQUIREMENT": 25,
        "ROLE_RESPONSIBILITY": 10,
        "SECONDARY": 4,
        "OPTIONAL": 13,
        "UNRESOLVED_QUALIFICATION_CONTEXT": 2,
    }
    names = {item.display_name for item in analysis.canonical_profile.comparison_requirements}
    assert {"Code Reviews", "Architectural Decision-Making", "Audio Codec Integration"} <= names
    assert any("Mentoring" in name for name in names)
    assert "Software Development Experience" in names
    assert len(names) > 1
    assert any(item.final_classification == "REJECTED_NON_REQUIREMENT" for item in rows)
    assert any(
        item.statement_type is RequirementStatementType.ROLE_RESPONSIBILITY
        for item in analysis.requirements
    )
    assert any(
        item.statement_type is RequirementStatementType.PREFERENCE for item in analysis.requirements
    )
    assert readiness_coverage_issue(analysis, []) is not None


def test_employer_specific_matches_cannot_substitute_for_baseline_breadth():
    analysis, _ = replay_saved_audit()
    canonical = analysis.canonical_profile.model_copy(
        update={
            "coverage_limitations": [],
            "profile_status": "PROVISIONAL",
        }
    )
    analysis = analysis.model_copy(update={"canonical_profile": canonical})
    comparisons = [
        RequirementComparison(
            requirement_id=item.canonical_requirement_id,
            posting_id=item.supporting_posting_ids[0],
            comparison_scope=ComparisonScope.EXACT_TARGET,
            match_type=MatchType.DIRECT_MATCH,
            evidence_status="SUPPORTED",
            confidence=ConfidenceLevel.HIGH,
        )
        for item in canonical.comparison_requirements
    ]
    # The saved cohort has only one shared baseline expectation. Matching every
    # employer-specific condition still cannot establish whole-role readiness.
    assert "fewer than two" in readiness_coverage_issue(analysis, comparisons)
    assert "fewer than two" in readiness_coverage_issue(analysis, comparisons[:1])
    assert comparisons[0].match_type is MatchType.DIRECT_MATCH


@pytest.mark.parametrize(
    ("quote", "name"),
    [
        ("Prior experience mentoring junior developers", "Developer Mentoring"),
        ("5 years' experience as a Software Developer", "Software Development Experience"),
        ("help them build and troubleshoot scalable systems", "Building Scalable Systems"),
        (
            "designing, developing, and modernizing enterprise applications",
            "Enterprise Application Development",
        ),
    ],
)
def test_faithful_normalization_is_not_rejected(quote, name):
    assert quote_capability_alignment(quote, name)[0]


def test_normalization_cannot_promote_participation_to_ownership():
    assert not quote_capability_alignment(
        "contributing to architectural decisions", "Architecture Ownership"
    )[0]


if __name__ == "__main__":
    analysis, audits = replay_saved_audit()
    print(
        json.dumps(
            {
                "mode": "offline audit-quote replay; no original full JD or new model inference",
                "raw_audit_items": sum(len(audit.items) for audit in audits),
                "dispositions": dict(
                    Counter(item.final_classification for audit in audits for item in audit.items)
                ),
                "hiring": [
                    item.display_name for item in analysis.canonical_profile.comparison_requirements
                ],
                "tracks": dict(
                    Counter(item.statement_type.value for item in analysis.requirements)
                ),
                "readiness_issue": readiness_coverage_issue(analysis, []),
            },
            indent=2,
        )
    )

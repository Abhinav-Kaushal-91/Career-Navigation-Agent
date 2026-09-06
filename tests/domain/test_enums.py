from pathlib import Path

import ai_career_navigator.domain as domain
from ai_career_navigator.domain import (
    ApprovalStatus,
    BridgeOutcome,
    CandidateAccessibility,
    CareerStage,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceMaturity,
    GapCategory,
    GapSeverity,
    GoalType,
    MarketBreadth,
    MatchType,
    MilestoneStatus,
    MilestoneType,
    PathType,
    PlanStatus,
    RequirementCategory,
    TimelineClassification,
)


def test_all_v1_enums_have_string_values() -> None:
    enum_types = (
        CareerStage,
        EvidenceMaturity,
        EvidenceConfirmationStatus,
        GoalType,
        MatchType,
        GapCategory,
        GapSeverity,
        CandidateAccessibility,
        BridgeOutcome,
        TimelineClassification,
        ConfidenceLevel,
        ApprovalStatus,
        PlanStatus,
        PathType,
        MilestoneType,
        RequirementCategory,
        MarketBreadth,
        MilestoneStatus,
    )

    assert all(isinstance(member.value, str) for enum_type in enum_types for member in enum_type)


def test_v1_domain_does_not_expose_deferred_models_or_technologies() -> None:
    assert not hasattr(domain, "HistoricalMarketSignal")
    assert not hasattr(domain, "MarketVerdict")

    domain_root = Path(domain.__file__).parent
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8") for path in domain_root.glob("*.py")
    ).lower()
    assert "pinecone" not in runtime_source
    assert "n8n" not in runtime_source

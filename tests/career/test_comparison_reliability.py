"""Regressions for semantic claims, uncertainty and comparison input fidelity."""

import json

import pytest

from ai_career_navigator.career import (
    assess_candidate_accessibility,
    compare_candidate_to_requirements,
)
from ai_career_navigator.career.comparison import _candidate_set
from ai_career_navigator.domain import (
    ConfidenceLevel,
    EvidenceMaturity,
    MatchType,
    ProductionContextDifference,
    RequirementCategory,
)
from ai_career_navigator.models.inspection import LocalModelInspector
from tests.career.test_comparison import (
    analysis,
    evidence,
    gateway,
    profile,
    requirement,
    semantic_json,
)
from tests.career.test_gap_analysis import inputs as gap_inputs


def direct_response(req, item, *, dimensions=None, **changes):
    payload = json.loads(semantic_json(req, item, match_type="DIRECT_MATCH"))
    payload.update(
        {
            "confidence": "HIGH",
            "evidence_status": "SUPPORTED",
            "remaining_difference": "The material expectation is directly demonstrated.",
            "evidence_quotes": [
                {
                    "evidence_id": str(item.evidence_id),
                    "quote": item.description,
                    "dimensions": dimensions or ["function"],
                }
            ],
        }
    )
    payload.update(changes)
    return json.dumps(payload)


def test_identical_ownership_label_cannot_override_explicit_contradiction():
    item = evidence(
        "Product Vision Ownership",
        description=(
            "Supported roadmap documentation. Did not own product vision or strategic decisions."
        ),
    )
    req = requirement("Product Vision Ownership")
    model, provider = gateway(direct_response(req, item, dimensions=["function", "ownership"]))
    result = compare_candidate_to_requirements(profile([item]), analysis([req]), model)
    assert len(provider.calls) == 1
    assert result.comparisons[0].match_type is MatchType.PARTIAL_MATCH
    assert result.comparisons[0].validation_notes


@pytest.mark.parametrize(
    ("capability", "description", "target"),
    [
        (
            "Process discovery",
            "Conducted stakeholder interviews and shadow sessions; "
            "translated requirements into a solution roadmap.",
            "Product Vision Ownership",
        ),
        (
            "Financial reporting",
            "Prepared reports and assisted the controller who owned final reporting decisions.",
            "Financial Reporting Ownership",
        ),
    ],
)
def test_model_ownership_dimension_tag_is_not_source_ownership_proof(
    capability, description, target
):
    item = evidence(capability, evidence_type="employment", description=description)
    req = requirement(target)
    model, _ = gateway(direct_response(req, item, dimensions=["function", "ownership"]))
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.match_type is MatchType.PARTIAL_MATCH
    assert comparison.ownership_alignment.value == "PARTIAL"
    assert comparison.validation_notes


@pytest.mark.parametrize(
    "description",
    [
        "Was accountable for financial reporting outcomes and held final decision authority.",
        "Signed off financial reporting submissions and was responsible for the results.",
        "Set the strategic direction for financial reporting and served as the final approver.",
    ],
)
def test_generic_accountability_signoff_and_direction_can_establish_ownership(description):
    item = evidence("Financial reporting", evidence_type="employment", description=description)
    req = requirement("Financial Reporting Ownership")
    model, _ = gateway(direct_response(req, item, dimensions=["function", "ownership"]))
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.match_type is MatchType.DIRECT_MATCH


@pytest.mark.parametrize(
    ("description", "expected_status"),
    [
        ("Completed a Bachelor of Science degree.", "UNKNOWN"),
        ("My professional registration is not expired.", "UNKNOWN"),
        ("I do not hold professional registration.", "CONFIRMED_UNMET"),
        ("My professional registration has expired.", "CONFIRMED_UNMET"),
    ],
)
def test_negative_prerequisite_needs_relevant_explicit_negative_source(
    description, expected_status
):
    item = evidence(
        "Education and registration", evidence_type="education", description=description
    )
    req = requirement("Professional registration", category=RequirementCategory.CREDENTIAL)
    payload = json.loads(semantic_json(req, item, match_type="NO_CONFIRMED_MATCH"))
    payload.update(
        supporting_evidence_ids=[],
        evidence_status="CONFIRMED_UNMET",
        evidence_quotes=[
            {"evidence_id": str(item.evidence_id), "quote": description, "dimensions": ["function"]}
        ],
    )
    model, _ = gateway(json.dumps(payload))
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.evidence_status == expected_status
    if expected_status == "UNKNOWN":
        assert comparison.match_type is None
        assert comparison.clarification_needed
    else:
        assert comparison.match_type is MatchType.NO_CONFIRMED_MATCH
    _, goal, snapshot, _, _ = gap_inputs(
        [RequirementCategory.CREDENTIAL],
        [MatchType.NO_CONFIRMED_MATCH],
        capability="Professional registration",
    )
    gaps = assess_candidate_accessibility(
        profile([item]), goal, snapshot, analysis([req]), [comparison]
    ).role_assessment.gaps
    assert gaps[0].hard_blocker is (expected_status == "CONFIRMED_UNMET")


def test_direct_classification_cannot_coexist_with_confirmed_unmet_premise():
    item = evidence(
        "Professional registration",
        evidence_type="education",
        description="I do not hold professional registration.",
    )
    req = requirement("Professional registration", category=RequirementCategory.CREDENTIAL)
    model, _ = gateway(direct_response(req, item, evidence_status="CONFIRMED_UNMET"))
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.match_type is None
    assert comparison.evidence_status == "UNKNOWN"


def test_qualified_java_expectation_can_be_direct_on_demonstrated_work():
    item = evidence(
        "Backend service delivery",
        evidence_type="employment",
        description=(
            "Built and deployed Java and Spring Boot services in production; "
            "owned releases and incident resolution."
        ),
    )
    req = requirement("Java", maturity=EvidenceMaturity.PRODUCTION).model_copy(
        update={
            "requirement_text": "Build Java services in production and own their release lifecycle."
        }
    )
    model, provider = gateway(
        direct_response(req, item, dimensions=["function", "ownership", "production"])
    )
    result = compare_candidate_to_requirements(profile([item]), analysis([req]), model)
    assert result.comparisons[0].match_type is MatchType.DIRECT_MATCH
    assert result.comparisons[0].confidence is ConfidenceLevel.HIGH
    assert result.comparisons[0].grounded_evidence_quotes[0]["quote"] == item.description
    assert len(provider.calls) == 1


def test_generic_ownership_rule_applies_outside_product_roles():
    item = evidence(
        "Financial review", description="Prepared reports for the accountable controller."
    )
    req = requirement("Financial Reporting Ownership", category=RequirementCategory.DOMAIN)
    model, _ = gateway(semantic_json(req, item))
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.match_type is MatchType.PARTIAL_MATCH
    assert "ownership" in comparison.remaining_difference


def test_same_name_with_different_scope_does_not_reuse_cached_answer():
    item = evidence("Architecture delivery", description="Contributed component designs to a team.")
    first = requirement("Architecture").model_copy(
        update={"requirement_text": "Contribute component designs."}
    )
    second = requirement("Architecture").model_copy(
        update={"requirement_text": "Own enterprise-scale architecture decisions."}
    )
    model, provider = gateway(
        direct_response(first, item),
        semantic_json(
            second,
            item,
            match_type="PARTIAL_MATCH",
            ownership_alignment="MISSING",
            partial_match_subtype="OWNERSHIP_OR_SCOPE_GAP",
        ),
    )
    comparisons = compare_candidate_to_requirements(
        profile([item]), analysis([first, second]), model
    ).comparisons
    assert len(provider.calls) == 2
    assert [item.match_type for item in comparisons] == [
        MatchType.DIRECT_MATCH,
        MatchType.PARTIAL_MATCH,
    ]


def test_production_context_difference_survives_equal_maturity():
    item = evidence("Workflow delivery", maturity=EvidenceMaturity.PRODUCTION)
    req = requirement("Backend engineering", maturity=EvidenceMaturity.PRODUCTION)
    model, _ = gateway(
        semantic_json(
            req,
            item,
            match_type="PARTIAL_MATCH",
            production_context_difference="OTHER",
            partial_match_subtype="ADJACENT_CAPABILITY_PARTIAL",
        )
    )
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.production_context_difference is ProductionContextDifference.OTHER


def test_unknown_semantic_result_is_not_a_provider_failure():
    item = evidence("Reporting")
    req = requirement("Decision Ownership")
    payload = json.loads(semantic_json(req, item))
    payload.update(
        {
            "match_type": None,
            "supporting_evidence_ids": [],
            "evidence_status": "UNKNOWN",
            "ownership_alignment": "UNKNOWN",
            "clarification_needed": "Which decisions were you personally accountable for?",
        }
    )
    model, _ = gateway(json.dumps(payload))
    result = compare_candidate_to_requirements(profile([item]), analysis([req]), model)
    assert result.failed_count == 0
    assert result.comparisons[0].evidence_status == "UNKNOWN"
    assert result.comparisons[0].confidence is ConfidenceLevel.INSUFFICIENT


def test_invented_source_quote_fails_even_with_valid_evidence_id():
    item = evidence("Service development", description="Built a personal project.")
    req = requirement("Distributed Engineering")
    payload = json.loads(direct_response(req, item))
    payload["evidence_quotes"][0]["quote"] = "Owned global production deployments."
    model, _ = gateway(json.dumps(payload))
    model.inspector = LocalModelInspector()
    result = compare_candidate_to_requirements(profile([item]), analysis([req]), model)
    assert result.comparisons[0].match_type is None
    assert result.comparisons[0].evidence_status == "OPERATION_FAILED"
    events = model.inspector.events
    assert any(item["event"] == "validated_response" for item in events)
    domain_event = next(item for item in events if item["event"] == "comparison_domain_validation")
    assert domain_event["validated_match"] is None
    assert domain_event["evidence_status"] == "OPERATION_FAILED"
    assert domain_event["selected_evidence_ids"] == [str(item.evidence_id)]


def test_professional_paraphrase_survives_many_overlapping_skill_labels():
    labels = [evidence(f"Discovery {index}") for index in range(16)]
    concrete = evidence(
        "Professional delivery",
        evidence_type="employment",
        source_reference="Bank delivery",
        description="Interviewed customers to identify pain points and validate unmet needs.",
    )
    selected = _candidate_set(requirement("Product Discovery"), [*labels, concrete])
    assert len(selected) == 12
    assert concrete in selected


def test_any_of_requires_only_the_demonstrated_alternative():
    item = evidence("Kotlin delivery", description="Built and operated Kotlin services.")
    req = requirement("Java or Kotlin").model_copy(
        update={
            "relationship": "ANY_OF",
            "capability_options": ["Java", "Kotlin"],
            "requirement_text": "Experience developing services using Java or Kotlin.",
        }
    )
    model, provider = gateway(direct_response(req, item, matched_alternative="Kotlin"))
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.match_type is MatchType.DIRECT_MATCH
    assert comparison.matched_alternative == "Kotlin"
    assert '"relationship": "ANY_OF"' in provider.calls[0].request.user_prompt


def test_unknown_material_production_context_is_not_assumed_aligned():
    item = evidence("Data processing", description="Built data-processing applications.")
    req = requirement("Production Data Processing")
    model, _ = gateway(semantic_json(req, item, production_context_difference="UNKNOWN"))
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.match_type is None
    assert "production context" in comparison.clarification_needed


def test_unverified_general_tenure_does_not_satisfy_specific_years():
    item = evidence(
        "Cloud delivery", description="Delivered cloud components and reviewed designs."
    )
    req = requirement("Cloud Architecture", years=5)
    model, _ = gateway(direct_response(req, item))
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.match_type is None
    assert "years of directly relevant experience" in comparison.clarification_needed


def test_atomic_skill_with_unknown_relevant_years_requests_clarification():
    item = evidence("Python", description="Used Python in production delivery.")
    req = requirement("Python", years=5)
    model, provider = gateway()
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.match_type is None
    assert comparison.evidence_status == "UNKNOWN"
    assert comparison.partial_match_subtype is None
    assert not provider.calls


def test_explicit_unmet_prerequisite_retains_its_negative_source_excerpt():
    item = evidence(
        "CPA", evidence_type="certification", description="I do not hold CPA certification."
    )
    req = requirement("CPA", category=RequirementCategory.CREDENTIAL)
    payload = json.loads(semantic_json(req, item))
    payload.update(
        {
            "match_type": "NO_CONFIRMED_MATCH",
            "supporting_evidence_ids": [],
            "functional_overlap": "NONE",
            "evidence_status": "CONFIRMED_UNMET",
            "evidence_quotes": [
                {
                    "evidence_id": str(item.evidence_id),
                    "quote": item.description,
                    "dimensions": ["function"],
                }
            ],
            "remaining_difference": "The mandatory CPA qualification is explicitly not held.",
        }
    )
    model, _ = gateway(json.dumps(payload))
    comparison = compare_candidate_to_requirements(
        profile([item]), analysis([req]), model
    ).comparisons[0]
    assert comparison.match_type is MatchType.NO_CONFIRMED_MATCH
    assert comparison.evidence_status == "CONFIRMED_UNMET"
    assert comparison.grounded_evidence_quotes[0]["quote"] == item.description

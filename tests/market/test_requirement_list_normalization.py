"""Narrow provider-format repair must not manufacture or weaken hiring evidence."""

import copy
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_career_navigator.market.processing import assess_candidate
from ai_career_navigator.market.requirement_prompts import PROMPT_VERSION, REQUIREMENT_SYSTEM_PROMPT
from ai_career_navigator.market.requirement_schemas import (
    ExtractedRequirement,
    PostingCandidate,
    PostingRequirementResult,
)
from ai_career_navigator.market.requirements import extract_posting_requirements
from ai_career_navigator.models import ModelGateway, ModelRole
from ai_career_navigator.models.providers import FakeModelProvider


def payload(**overrides):
    return {
        "source_quote": "Java experience is required.",
        "category": "TECHNICAL",
        "normalized_capability": "Java",
        "confidence": "HIGH",
        "mandatory": True,
        "qualifier_quotes": None,
        "capability_options": None,
        **overrides,
    }


def extract(item, text="Java experience is required."):
    provider = FakeModelProvider(outcomes=[json.dumps({"requirements": [item]})])
    gateway = ModelGateway(
        provider=provider,
        models={ModelRole.EXTRACTION: "fake-extraction"},
        timeout_seconds=10,
        max_retries=0,
    )
    candidate = PostingCandidate(
        source_id=uuid4(),
        source_reference="Test employer vacancy",
        source_reference_text="Senior Java Developer at Test employer",
        title="Senior Java Developer",
        employer="Test employer",
        location="Toronto, Canada",
        posting_text=text,
        extraction_confidence="HIGH",
    )
    assessment = assess_candidate(
        candidate, target_role="Senior Java Developer", target_geography="Toronto, Canada"
    )
    return extract_posting_requirements(assessment, gateway), provider


def test_explicit_role_named_qualification_is_not_discarded_as_a_job_title():
    quote = "6+ years of experience in Java development (Spring Boot, microservices architecture)"
    outcome, _ = extract(
        payload(
            source_quote=quote,
            normalized_capability="Java Development",
            item_type="HIRING_CAPABILITY",
            years_required=6,
            qualifier_quotes=["Spring Boot, microservices architecture"],
        ),
        quote,
    )
    assert len(outcome.requirements) == 1
    assert outcome.requirements[0].years_required == 6
    assert outcome.requirements[0].qualifier_quotes == ["Spring Boot, microservices architecture"]


def test_bare_job_title_does_not_become_a_capability():
    quote = "Job Title: Senior Java Developer"
    outcome, _ = extract(
        payload(
            source_quote=quote,
            normalized_capability="Java Development",
            mandatory=False,
        ),
        quote,
    )
    assert not outcome.requirements


@pytest.mark.parametrize(
    ("quote", "label"),
    [
        ("Ability to mentor junior engineers", "Mentoring"),
        ("Build and deploy cloud applications", "Cloud Deployment"),
        ("Integrate services into CI/CD pipelines", "CI/CD Pipeline Integration"),
    ],
)
def test_inflected_professional_capability_remains_source_grounded(quote, label):
    outcome, _ = extract(
        payload(
            source_quote=quote,
            normalized_capability=label,
            mandatory=False,
        ),
        quote,
    )
    assert len(outcome.requirements) == 1


@pytest.mark.parametrize("value", [None, [], ["Exact source words"]])
def test_nulls_become_empty_lists_and_valid_lists_are_preserved_without_mutation(value):
    source = payload(qualifier_quotes=value, capability_options=value)
    original = copy.deepcopy(source)
    result = ExtractedRequirement.model_validate(source)
    assert result.qualifier_quotes == ([] if value is None else value)
    assert result.capability_options == ([] if value is None else value)
    assert source == original


def test_missing_fields_keep_existing_empty_defaults_and_nullable_scalars_stay_null():
    source = payload(source_section=None, years_required=None, maturity_expected=None)
    del source["qualifier_quotes"]
    del source["capability_options"]
    result = ExtractedRequirement.model_validate(source)
    assert result.qualifier_quotes == result.capability_options == []
    assert result.source_section is result.years_required is result.maturity_expected is None


@pytest.mark.parametrize("field", ["qualifier_quotes", "capability_options"])
@pytest.mark.parametrize("value", ["Java", "[]", {}, 0, False, [None], [7], [[]]])
def test_wrong_types_are_not_repaired(field, value):
    with pytest.raises(ValidationError):
        ExtractedRequirement.model_validate(payload(**{field: value}))


@pytest.mark.parametrize("field", ["qualifier_quotes", "capability_options"])
def test_list_length_bounds_remain_enforced(field):
    with pytest.raises(ValidationError):
        ExtractedRequirement.model_validate(payload(**{field: ["item"] * 9}))


@pytest.mark.parametrize("options", [None, [], ["Java"]])
def test_any_of_still_requires_alternatives(options):
    with pytest.raises(ValidationError, match="ANY_OF needs at least two"):
        ExtractedRequirement.model_validate(
            payload(relationship="ANY_OF", capability_options=options)
        )


def test_omitted_any_of_alternatives_are_not_fabricated():
    source = payload(relationship="ANY_OF")
    del source["capability_options"]
    with pytest.raises(ValidationError, match="ANY_OF needs at least two"):
        ExtractedRequirement.model_validate(source)


@pytest.mark.parametrize("field", ["requirements", "limitations"])
def test_no_global_null_to_list_coercion(field):
    with pytest.raises(ValidationError):
        PostingRequirementResult.model_validate({field: None})


def test_wire_schema_still_requests_arrays_not_nulls():
    properties = ExtractedRequirement.model_json_schema()["properties"]
    for field in ("qualifier_quotes", "capability_options"):
        assert properties[field]["type"] == "array"
        assert properties[field]["items"]["type"] == "string"
        assert "anyOf" not in properties[field]


def test_null_list_response_passes_real_gateway_and_grounding_without_retry():
    result, provider = extract(payload())
    assert result.failure_category is None
    assert result.capability_count == 1
    assert result.unsupported_count == 0
    assert len(result.requirements) == len(provider.calls) == 1
    assert result.requirements[0].capability_options == []
    assert provider.calls[0].request.metadata["prompt_version"] == PROMPT_VERSION


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "source_quote": "Kubernetes experience is required.",
            "normalized_capability": "Kubernetes",
        },
        {"qualifier_quotes": ["Enterprise production leadership"]},
        {"normalized_capability": "Kubernetes"},
    ],
)
def test_null_repair_does_not_bypass_quote_qualifier_or_capability_grounding(overrides):
    result, _ = extract(payload(**overrides))
    assert result.requirements == []
    assert result.audit_items and not result.audit_items[0].accepted


@pytest.mark.parametrize("options", [["Java", "Java"], ["Java", "Kotlin"], ["Java", ""]])
def test_any_of_invalid_options_are_still_rejected_downstream(options):
    result, _ = extract(
        payload(
            source_quote="Java or Python experience is required.",
            normalized_capability="Java or Python",
            relationship="ANY_OF",
            capability_options=options,
        ),
        text="Java or Python experience is required.",
    )
    assert result.requirements == []
    assert result.audit_items[0].final_classification == "REJECTED_UNSUPPORTED_ALTERNATIVES"


def test_valid_any_of_keeps_alternatives_after_null_qualifier_repair():
    result, _ = extract(
        payload(
            source_quote="Java or Python experience is required.",
            normalized_capability="Java or Python",
            relationship="ANY_OF",
            capability_options=["Java", "Python"],
        ),
        text="Java or Python experience is required.",
    )
    assert len(result.requirements) == 1
    assert result.requirements[0].capability_options == ["Java", "Python"]
    assert result.requirements[0].relationship == "ANY_OF"


@pytest.mark.parametrize(
    "overrides",
    [
        {"category": "MADE_UP"},
        {"confidence": "CERTAIN"},
        {"invented_field": "anything"},
        {"mandatory": True, "preferred": True},
    ],
)
def test_other_contract_errors_remain_rejected(overrides):
    with pytest.raises(ValidationError):
        ExtractedRequirement.model_validate(payload(**overrides))


def test_prompt_explicitly_requires_arrays_and_grounded_alternatives():
    assert (
        "qualifier_quotes and capability_options must always be JSON arrays of strings"
        in REQUIREMENT_SYSTEM_PROMPT
    )
    assert "never null, a string, or an object" in REQUIREMENT_SYSTEM_PROMPT
    assert "An empty list cannot justify ANY_OF" in REQUIREMENT_SYSTEM_PROMPT

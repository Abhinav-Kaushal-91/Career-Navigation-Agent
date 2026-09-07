import pytest

from ai_career_navigator.market.requirement_schemas import ExtractedRequirement, RequirementItemType
from ai_career_navigator.market.requirements import _grounded_alternatives, _item_group
from ai_career_navigator.market.role_profile import quote_capability_alignment


def requirement(**overrides):
    return ExtractedRequirement(
        **{
            "source_quote": "A degree is required",
            "category": "EDUCATION",
            "normalized_capability": "Degree",
            "mandatory": True,
            "confidence": "HIGH",
            **overrides,
        }
    )


@pytest.mark.parametrize(
    "quote",
    [
        "No degree required",
        "A degree is not required",
        "Certification optional",
        "CPA preferred",
        "Certification is a nice-to-have",
    ],
)
def test_optional_or_negated_credential_cannot_be_mandatory_prerequisite(quote):
    item = requirement(source_quote=quote)
    assert _item_group(item) in {
        RequirementItemType.PREFERENCE,
        RequirementItemType.METADATA_NON_REQUIREMENT,
    }


def test_explicit_preference_precedes_prerequisite_category():
    assert (
        _item_group(requirement(mandatory=False, preferred=True)) is RequirementItemType.PREFERENCE
    )


@pytest.mark.parametrize(
    "quote,options,valid",
    [
        ("Python or SQL required", ["Python", "SQL"], True),
        ("Python and SQL required", ["Python", "SQL"], False),
        ("Python or SQL required", ["Python", "Python"], False),
        ("Python and SQL or Scala required", ["Python", "SQL", "Scala"], False),
        ("Python or SQL and collaboration required", ["Python", "SQL"], True),
        ("Python/SQL experience", ["Python", "SQL"], False),
    ],
)
def test_alternative_logic_preserves_source_operators(quote, options, valid):
    item = requirement(
        source_quote=quote,
        category="TECHNICAL",
        normalized_capability="Python or SQL",
        relationship="ANY_OF",
        capability_options=options,
    )
    assert _grounded_alternatives(item) is valid


@pytest.mark.parametrize("quote,capability,valid", [
    ("Cloud experience is required", "AWS", False),
    ("Production SQL experience required", "Production Python", False),
    ("Text generation experience", "RAG", False),
    ("Amazon Web Services experience", "AWS", True),
    ("Retrieval augmented generation experience", "RAG", True),
    ("Led design of automation frameworks", "Automation Framework Design", True),
])
def test_semantic_anchors_cannot_be_satisfied_by_one_generic_word(quote, capability, valid):
    assert quote_capability_alignment(quote, capability)[0] is valid


@pytest.mark.parametrize("capability", ["Nursing Registration", "Python", ".NET", "Node.js"])
def test_sentence_punctuation_does_not_change_literal_capability_support(capability):
    assert quote_capability_alignment(f"Candidates must demonstrate {capability}.", capability)[0]

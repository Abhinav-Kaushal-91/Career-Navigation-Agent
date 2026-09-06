from ai_career_navigator.profile import (
    capability_key,
    clean_capability_name,
    dedupe_capabilities,
)


def test_technical_punctuation_is_preserved_verbatim() -> None:
    values = ("C#", "C++", "CI/CD", "OAuth2/OIDC", "AI/ML", ".NET", "RAG (advanced)")

    assert tuple(clean_capability_name(value) for value in values) == values


def test_submitted_strength_remains_one_semantic_value() -> None:
    value = "OAuth2/OIDC (enterprise identity)"

    assert dedupe_capabilities([value]) == (value,)


def test_duplicate_policy_is_conservative_and_deterministic() -> None:
    assert dedupe_capabilities(
        ["REST API", "REST APIs", "Solution Architecture", "Enterprise Architecture"]
    ) == ("REST API", "Solution Architecture", "Enterprise Architecture")
    assert capability_key("AI / ML") == capability_key("AI/ML")

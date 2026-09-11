"""Production batch contract: source lineage, importance and safe bounded coverage."""

import json

import pytest

from ai_career_navigator.market.batch_profile import (
    analyze_five_postings,
    description_word_count,
    select_batch,
)
from ai_career_navigator.market.requirements import _assessment_from_evidence
from tests.market.test_requirement_processing import gateway, structured_evidence

TITLE = "Senior Java Developer"
BODY = """Responsibilities
Design REST APIs for production services and collaborate with delivery teams.
Requirements
Experience with Java or Python is required.
Experience with SQL databases is required.
Experience with automated testing is required.
Experience with VOIP protocols is required for this specialized communication product.
Preferred
AWS experience is preferred.
About the work
The team delivers services for internal business users and external customers. Engineers work
with product colleagues to understand needs, design maintainable systems, review changes,
investigate incidents and improve reliability. This posting describes a hands-on individual
contributor role with collaborative delivery responsibilities, technical planning and ongoing
support of production applications. Candidates should provide examples of their relevant work.
"""


def sources(count=5):
    result = []
    for i in range(count):
        source = structured_evidence(i, TITLE)
        result.append(
            type(source).model_validate(
                {
                    **source.model_dump(),
                    "title_classification": "EXACT_TARGET",
                    "retrieval_quality": "HIGH",
                    "primary_content": source.primary_content.model_copy(update={"markdown": BODY}),
                }
            )
        )
    return result


def response_for(selected):
    def theme(
        name, quote, *, importance="CORE", kind="HIRING_CAPABILITY", subset=None, alternatives=()
    ):
        return {
            "name": name,
            "category": "TECHNICAL",
            "kind": kind,
            "importance": importance,
            "importance_reason": "Supported by the supplied role work.",
            "relationship": "ANY_OF" if alternatives else "SINGLE",
            "alternatives": list(alternatives),
            "supports": [
                {
                    "posting_id": str(source.posting.posting_id),
                    "quote": quote,
                    "source_capability": name,
                    "section": "Responsibilities"
                    if kind == "ROLE_RESPONSIBILITY"
                    else "Preferred"
                    if kind == "PREFERENCE"
                    else "Requirements",
                    "obligation": "NOT_APPLICABLE"
                    if kind == "ROLE_RESPONSIBILITY"
                    else "PREFERRED"
                    if kind == "PREFERENCE"
                    else "REQUIRED",
                }
                for source in (selected if subset is None else subset)
            ],
        }

    return {
        "themes": [
            theme(
                "Java or Python",
                "Experience with Java or Python is required.",
                alternatives=("Java", "Python"),
            ),
            theme("SQL", "Experience with SQL databases is required."),
            theme(
                "Automated Testing",
                "Experience with automated testing is required.",
                importance="SUPPORTING",
            ),
            theme(
                "VOIP Protocols",
                "Experience with VOIP protocols is required for this "
                "specialized communication product.",
                importance="SPECIALIST",
                subset=selected[:1],
            ),
            theme(
                "AWS", "AWS experience is preferred.", kind="PREFERENCE", importance="ADDITIONAL"
            ),
            theme(
                "REST APIs",
                "Design REST APIs for production services and collaborate with delivery teams.",
                kind="ROLE_RESPONSIBILITY",
            ),
        ],
        "posting_reviews": [
            {"posting_id": str(item.posting.posting_id), "status": "USABLE"} for item in selected
        ],
        "limitations": [],
    }


def run_batch(selected=None, mutate=None):
    selected = sources() if selected is None else selected
    response = response_for(selected)
    if mutate:
        mutate(response)
    model, provider = gateway(json.dumps(response))
    analysis = analyze_five_postings(
        selected, target_role=TITLE, geography="Toronto, Canada", model_gateway=model
    )
    return analysis, provider


def test_one_request_creates_source_grounded_role_profile_and_keeps_or():
    analysis, provider = run_batch()
    assert len(provider.calls) == 1
    assert analysis.status == "SUCCEEDED", analysis.summary.limitations
    canonical = analysis.canonical_profile
    assert canonical.construction_method == "FIVE_POSTING_BATCH"
    assert canonical.profile_status == "STABLE"
    assert len(canonical.selected_posting_ids) == 5
    assert len(canonical.requirements) == 3
    assert len(canonical.responsibilities) == 1
    assert len(canonical.preferences) == 1
    assert [item.display_name for item in canonical.optional_signals] == ["VOIP Protocols"]
    assert len(canonical.comparison_requirements) == 3
    assert len(canonical.assessment_requirements) == 4
    either = next(item for item in canonical.requirements if item.relationship == "ANY_OF")
    assert either.capability_options == ["Java", "Python"]
    assert either.employer_support_count == either.posting_support_count == 5
    assert either.qualification_support_count == 5
    assert not either.mandatory_signal  # role importance is not a universal source mandate
    assert all(item.expectation_status == "REQUIRED" for item in either.source_expectations)
    assert {item.requirement_id for item in analysis.raw_requirements} == {
        row.source_requirement_id
        for audit in analysis.posting_audits
        for row in audit.items
        if row.accepted
    }
    # The model payload has descriptions, not the candidate or provider credentials.
    payload = json.loads(provider.calls[0].request.user_prompt)
    assert len(payload["postings"]) == 5
    assert set(payload) == {"target_role", "geography", "target_seniority", "postings"}


def test_selection_is_maximum_five_keeps_short_text_but_excludes_related():
    selected = sources(8)
    assessments = [_assessment_from_evidence(item, target_role=TITLE) for item in selected]
    assert len(select_batch(assessments, TITLE, limit=10)) == 5
    assessments[0] = assessments[0].model_copy(update={"title_match": "RELATED_TITLE"})
    assessments[1] = assessments[1].model_copy(
        update={
            "candidate": assessments[1].candidate.model_copy(
                update={"posting_text": "Java required."}
            )
        }
    )
    assert len(select_batch(assessments[:4], TITLE)) == 3


def test_longest_descriptions_win_without_a_minimum_length_or_quality_cutoff():
    assessments = [_assessment_from_evidence(item, target_role=TITLE) for item in sources(6)]
    sizes = [158, 150, 200, 300, 400, 450]
    assessments = [
        item.model_copy(
            update={
                "candidate": item.candidate.model_copy(
                    update={
                        "posting_text": " ".join(["word"] * size),
                        "retrieval_quality": "LOW",
                    }
                )
            }
        )
        for item, size in zip(assessments, sizes, strict=True)
    ]
    selected = select_batch(assessments, TITLE)
    assert [description_word_count(item.candidate.posting_text) for item in selected] == [
        450,
        400,
        300,
        200,
        158,
    ]
    assert description_word_count("# Skills\n- Java and Python") == 4


def test_word_ranking_still_excludes_empty_and_out_of_scope_descriptions():
    items = [_assessment_from_evidence(item, target_role=TITLE) for item in sources(3)]
    items[0] = items[0].model_copy(
        update={"candidate": items[0].candidate.model_copy(update={"posting_text": "  # --- "})}
    )
    items[1] = items[1].model_copy(update={"geography_status": "OUT_OF_SCOPE"})
    assert select_batch(items, TITLE) == [items[2]]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda draft: draft["posting_reviews"].pop(),
        lambda draft: draft["themes"][0]["supports"][0].update(posting_id="unknown-id"),
        lambda draft: draft["themes"][0]["supports"][0].update(
            quote="Invented experience required."
        ),
        lambda draft: draft["themes"][0].update(alternatives=["Java", "Ruby"]),
    ],
)
def test_invalid_batch_safely_stops_without_individual_retry_or_invented_gaps(mutation):
    analysis, provider = run_batch(mutate=mutation)
    assert 1 <= len(provider.calls) <= 2
    if len(provider.calls) == 2:
        assert provider.calls[1].request.metadata["task_type"] == "five_posting_theme_repair"
        assert analysis.canonical_profile.requirements  # Unaffected siblings survive.
    assert analysis.canonical_profile.profile_status in {"INSUFFICIENT", "PROVISIONAL"}
    assert analysis.canonical_profile.coverage_limitations
    assert not analysis.canonical_profile.comparison_requirements or analysis.status == "PARTIAL"


def test_empty_selection_does_not_call_model():
    model, provider = gateway()
    analysis = analyze_five_postings([], target_role=TITLE, geography="Canada", model_gateway=model)
    assert analysis.status == "EMPTY"
    assert not provider.calls


def test_cross_field_failure_is_repaired_without_losing_other_themes():
    selected = sources()
    draft = response_for(selected)
    repaired = dict(draft["themes"][4])
    draft["themes"][4] = {**repaired, "importance": "CORE"}
    model, provider = gateway(
        json.dumps(draft), json.dumps({"repairs": [{"index": 4, "theme": repaired}]})
    )
    analysis = analyze_five_postings(
        selected, target_role=TITLE, geography="Toronto, Canada", model_gateway=model
    )
    canonical = analysis.canonical_profile
    assert len(provider.calls) == 2
    assert len(canonical.requirements) == 3
    assert canonical.preferences[0].display_name == "AWS"
    assert canonical.extraction_processing_status == "COMPLETE"
    assert not canonical.coverage_limitations
    repair_payload = json.loads(provider.calls[1].request.user_prompt)
    assert [item["index"] for item in repair_payload["rejected_themes"]] == [4]
    assert any("1 repaired; 0 unresolved" in note for note in canonical.limitations)


def test_invalid_seventh_theme_does_not_erase_six_valid_siblings():
    import copy

    selected = sources()
    draft = response_for(selected)
    invalid = copy.deepcopy(draft["themes"][1])
    invalid["supports"][0]["obligation"] = "NOT_APPLICABLE"
    draft["themes"].append(invalid)
    model, provider = gateway(json.dumps(draft), '{"repairs": []}')
    analysis = analyze_five_postings(
        selected, target_role=TITLE, geography="Toronto, Canada", model_gateway=model
    )
    canonical = analysis.canonical_profile
    assert len(provider.calls) == 2
    assert len(canonical.requirements) == 3
    assert len(canonical.preferences) == len(canonical.responsibilities) == 1
    assert canonical.coverage_limitations
    assert canonical.extraction_processing_status == "PARTIAL"
    assert any("Theme 7 excluded" in note for note in canonical.limitations)
    from ai_career_navigator.career.evidence_coverage import readiness_coverage_issue

    assert "Batch coverage" in readiness_coverage_issue(analysis, [])


@pytest.mark.parametrize(
    "repair_kind", ["unknown_id", "change_core", "duplicate_index", "new_index"]
)
def test_repair_cannot_introduce_bad_sources_or_rewrite_valid_themes(repair_kind):
    import copy

    selected = sources()
    draft = response_for(selected)
    original = copy.deepcopy(draft["themes"][0])
    draft["themes"][0]["supports"][0]["obligation"] = "NOT_APPLICABLE"
    repairs = [{"index": 0, "theme": original}]
    if repair_kind == "unknown_id":
        original["supports"][0]["posting_id"] = "not-supplied"
    elif repair_kind == "change_core":
        original["importance"] = "SPECIALIST"
    elif repair_kind == "duplicate_index":
        repairs.append(copy.deepcopy(repairs[0]))
    else:
        repairs[0]["index"] = 1
    model, provider = gateway(json.dumps(draft), json.dumps({"repairs": repairs}))
    analysis = analyze_five_postings(
        selected, target_role=TITLE, geography="Toronto, Canada", model_gateway=model
    )
    assert len(provider.calls) == 2
    assert [item.display_name for item in analysis.canonical_profile.requirements] == [
        "SQL",
        "Automated Testing",
    ]
    assert analysis.canonical_profile.coverage_limitations


def test_unrepaired_preference_lowers_confidence_without_inventing_core_gap():
    def mutate(draft):
        draft["themes"][4]["importance"] = "CORE"

    analysis, provider = run_batch(mutate=mutate)
    assert len(provider.calls) == 2
    assert len(analysis.canonical_profile.requirements) == 3
    assert not analysis.canonical_profile.coverage_limitations
    assert analysis.canonical_profile.confidence == "LOW"
    assert analysis.canonical_profile.extraction_processing_status == "PARTIAL"


def test_repair_can_shorten_rejected_name_without_changing_source_or_core_importance():
    import copy

    selected = sources()
    draft = response_for(selected)
    repaired = copy.deepcopy(draft["themes"][1])
    draft["themes"][1]["name"] = "SQL Executive Leadership"
    model, provider = gateway(
        json.dumps(draft), json.dumps({"repairs": [{"index": 1, "theme": repaired}]})
    )
    analysis = analyze_five_postings(
        selected, target_role=TITLE, geography="Toronto, Canada", model_gateway=model
    )
    assert len(provider.calls) == 2
    assert len(analysis.canonical_profile.requirements) == 3
    assert not analysis.canonical_profile.coverage_limitations
    sql = next(
        item for item in analysis.canonical_profile.requirements if item.display_name == "SQL"
    )
    assert sql.role_importance == "CORE"
    assert sql.posting_support_count == 5


def test_repair_cannot_replace_rejected_theme_with_different_source_expectation():
    import copy

    selected = sources()
    draft = response_for(selected)
    draft["themes"][1]["name"] = "SQL Executive Leadership"
    replacement = copy.deepcopy(draft["themes"][2])
    replacement["importance"] = "CORE"
    model, provider = gateway(
        json.dumps(draft), json.dumps({"repairs": [{"index": 1, "theme": replacement}]})
    )
    analysis = analyze_five_postings(
        selected, target_role=TITLE, geography="Toronto, Canada", model_gateway=model
    )
    assert len(provider.calls) == 2
    assert analysis.canonical_profile.coverage_limitations
    assert len(analysis.canonical_profile.requirements) == 2


def test_production_runtime_uses_the_batch_service():
    from ai_career_navigator.config import Settings
    from ai_career_navigator.models.providers import FakeModelProvider
    from ai_career_navigator.ui.live_workflow import build_live_workflow_runtime

    runtime = build_live_workflow_runtime(
        Settings(_env_file=None), provider_override=FakeModelProvider()
    )
    assert runtime.controller._context.market_processing_service is analyze_five_postings


def completed_batch_state():
    """Synthetic end-to-end service replay; no live provider or user profile."""
    from ai_career_navigator.career import (
        assess_bridge_roles,
        assess_candidate_accessibility,
        assess_timeline,
        compare_candidate_to_requirements,
        generate_career_plan,
        synthesize_career_assessment,
    )
    from ai_career_navigator.ui.demo_data import MARKET_SNAPSHOT
    from tests.career.test_comparison import evidence, profile
    from tests.career.test_comparison import gateway as comparison_gateway
    from tests.career.test_comparison_reliability import direct_response
    from tests.career.test_path_assessment import goal

    market, _ = run_batch()
    evidence_by_name = {}
    for requirement in market.requirements:
        name = requirement.normalized_capability
        demonstrated = "Java" if requirement.relationship == "ANY_OF" else name
        evidence_by_name[name] = evidence(
            demonstrated,
            evidence_type="employment",
            description=f"Designed and maintained production services using {demonstrated}.",
        )
    candidate = profile(list(evidence_by_name.values())).model_copy(update={"current_role": TITLE})
    target = goal(months=None).model_copy(update={"target_role": TITLE})
    responses = [
        direct_response(
            req,
            evidence_by_name[req.normalized_capability],
            **({"matched_alternative": "Java"} if req.relationship == "ANY_OF" else {}),
        )
        for req in market.requirements
    ]
    model, _ = comparison_gateway(*responses)
    compared = compare_candidate_to_requirements(candidate, market, model)
    snapshot = MARKET_SNAPSHOT.model_copy(
        update={
            "target_role": TITLE,
            "geography": "Toronto",
            "validated_posting_count": 5,
            "exact_title_count": 5,
            "target_variant_count": 0,
            "related_title_count": 0,
        }
    )
    role = assess_candidate_accessibility(
        candidate, target, snapshot, market, compared.comparisons
    ).role_assessment
    synthesis = synthesize_career_assessment(candidate, role, market, None)
    bridges = assess_bridge_roles(candidate, target, role, market, [])
    timeline_result = assess_timeline(target, role, bridges, snapshot)
    plan = generate_career_plan(
        candidate,
        target,
        role,
        bridges.assessments,
        bridges.outcome,
        timeline_result.assessment,
        synthesis=synthesis,
    ).plan
    return {
        "confirmed_profile": candidate,
        "confirmed_goal": target,
        "market_snapshot": snapshot,
        "canonical_target_role_profile": market.canonical_profile,
        "requirement_summary": market.summary,
        "posting_requirement_audits": market.posting_audits,
        "role_assessment": role,
        "career_assessment_synthesis": synthesis,
        "career_plan": plan,
    }


def test_five_posting_batch_reaches_comparison_synthesis_and_untimed_plan():
    state = completed_batch_state()
    role, plan = state["role_assessment"], state["career_plan"]
    assert len(role.requirement_comparisons) == 4
    assert all(item.match_type == "DIRECT_MATCH" for item in role.requirement_comparisons)
    assert any(item.matched_alternative == "Java" for item in role.requirement_comparisons)
    assert not role.gaps
    assert role.candidate_accessibility == "APPLY_NOW"
    assert plan is not None
    assert "VOIP" not in plan.model_dump_json()
    assert "missing timeline" not in plan.model_dump_json().lower()
    canonical = state["canonical_target_role_profile"]
    assert (
        type(canonical).model_validate_json(canonical.model_dump_json()).construction_method
        == "FIVE_POSTING_BATCH"
    )


def test_supporting_matches_do_not_hide_unresolved_core():
    from ai_career_navigator.career.evidence_coverage import readiness_coverage_issue
    from tests.career.test_readiness_coverage_policy import scenario

    _, role, market = scenario(total=5, unresolved=(0, 1))
    canonical = market.canonical_profile
    canonical = canonical.model_copy(
        update={
            "requirements": [
                item.model_copy(update={"role_importance": "CORE" if i < 2 else "SUPPORTING"})
                for i, item in enumerate(canonical.requirements)
            ]
        }
    )
    issue = readiness_coverage_issue(
        market.model_copy(update={"canonical_profile": canonical}), role.requirement_comparisons
    )
    assert "Supporting matches do not replace core coverage" in issue


def test_partial_description_lowers_confidence_without_erasing_valid_core_matches():
    def partial(draft):
        draft["posting_reviews"][0]["status"] = "PARTIAL"
        draft["posting_reviews"][0]["note"] = "Some sections may be truncated."

    analysis, _ = run_batch(mutate=partial)
    assert analysis.status == "PARTIAL"
    assert analysis.canonical_profile.confidence == "LOW"
    assert analysis.canonical_profile.profile_status == "PROVISIONAL"
    assert len(analysis.canonical_profile.comparison_requirements) == 3
    assert not analysis.canonical_profile.coverage_limitations

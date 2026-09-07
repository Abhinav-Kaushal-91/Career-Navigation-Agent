from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from streamlit.testing.v1 import AppTest

from ai_career_navigator.domain import (
    CandidateAccessibility,
    ConfidenceLevel,
    EmployerDiversity,
    MarketConcentration,
    PathType,
    TimelineClassification,
)
from ai_career_navigator.market import CanonicalTargetRoleProfile, RoleProfileStatus
from ai_career_navigator.ui.components.charts import (
    build_requirement_frequency_figure,
    build_segmented_bar_figure,
)
from ai_career_navigator.ui.demo_data import (
    CANDIDATE_PROFILE,
    CAREER_PLAN,
    DEMO_CAREER_SYNTHESIS,
    DEMO_DATETIME,
    MARKET_SNAPSHOT,
    ROLE_ASSESSMENT,
    ROLE_REQUIREMENTS,
)
from ai_career_navigator.ui.pages import live_views
from ai_career_navigator.ui.view_models import (
    analysis_view_model,
    market_view_model,
    plan_eligibility,
    plan_limitations,
    plan_view_model,
    product_label,
    untimed_roadmap_stages,
    user_facing_limitations,
)


def _summary() -> SimpleNamespace:
    requirements = [
        SimpleNamespace(
            normalized_capability=item.normalized_capability,
            category=item.category,
            requirement_ids=[item.requirement_id],
            exact_title_occurrence_count=1,
            target_variant_occurrence_count=0,
            related_title_occurrence_count=0,
            exact_and_variant_frequency=item.frequency_within_sample,
            combined_frequency=item.frequency_within_sample,
        )
        for item in ROLE_REQUIREMENTS
    ]
    return SimpleNamespace(
        analyzed_posting_count=4,
        exact_title_analyzed_count=4,
        target_variant_analyzed_count=0,
        related_title_analyzed_count=0,
        capability_requirements=requirements,
        requirements=requirements,
        limitations=["Rejected 2 metadata, responsibility, or non-canonical items."],
    )


def test_market_view_uses_validated_counts_and_separates_title_mix() -> None:
    view = market_view_model(
        {"market_snapshot": MARKET_SNAPSHOT, "requirement_summary": _summary()}
    )

    assert view.validated_postings == MARKET_SNAPSHOT.validated_posting_count
    assert view.distinct_employers == MARKET_SNAPSHOT.distinct_employer_count
    assert view.title_mix == (
        ("Exact target", 6),
        ("Target variants", 0),
        ("Related titles", 9),
    )
    assert view.requirements[0].occurrences == 1
    assert view.requirements[0].sample_size == 4
    assert view.primary_analyzed_postings == 4
    assert view.requirement_sample_confidence == "Directional"
    assert view.exact_target_postings == 6
    assert view.target_variant_postings == 0
    assert view.related_title_postings == 9
    assert view.expanded_market_postings == 15
    assert "expanded target and related-title market" in view.dimensions[0].evidence
    assert "secondary context" in view.what_this_means


def test_market_dimensions_derive_from_existing_signals_and_title_counts() -> None:
    snapshot = MARKET_SNAPSHOT.model_copy(
        update={
            "exact_title_count": 3,
            "target_variant_count": 1,
            "related_title_count": 11,
            "employer_diversity": EmployerDiversity.HIGH,
            "market_concentration": MarketConcentration.LOW,
        }
    )
    view = market_view_model({"market_snapshot": snapshot, "requirement_summary": _summary()})
    dimensions = {item.name: item.value for item in view.dimensions}

    assert dimensions["Opportunity availability"] == "Strong"
    assert dimensions["Employer diversity"] == "Broadly distributed"
    assert dimensions["Title consistency"] == "Low consistency"
    assert "3 exact · 1 variants · 11 related" in view.dimensions[2].evidence

    cases = (
        (11, 2, 2, "High consistency"),
        (5, 4, 6, "Moderate variation"),
        (3, 1, 11, "Low consistency"),
    )
    for exact, variants, related, expected in cases:
        candidate = snapshot.model_copy(
            update={
                "exact_title_count": exact,
                "target_variant_count": variants,
                "related_title_count": related,
            }
        )
        assert (
            market_view_model(
                {"market_snapshot": candidate, "requirement_summary": _summary()}
            ).title_consistency
            == expected
        )


def test_high_diversity_low_concentration_maps_to_broadly_distributed() -> None:
    snapshot = MARKET_SNAPSHOT.model_copy(
        update={
            "validated_posting_count": 20,
            "distinct_employer_count": 17,
            "known_employer_posting_count": 18,
            "top_three_employer_posting_count": 4,
            "employer_diversity": EmployerDiversity.HIGH,
            "market_concentration": MarketConcentration.LOW,
        }
    )

    view = market_view_model({"market_snapshot": snapshot, "requirement_summary": _summary()})

    assert view.employer_diversity == "Broadly distributed"
    assert view.employer_conclusion == (
        "Observed hiring is not dominated by a small number of employers."
    )


def test_geography_summary_uses_only_validated_snapshot_locations() -> None:
    snapshot = MARKET_SNAPSHOT.model_copy(
        update={
            "location_posting_counts": {
                "Ottawa, Ontario": 5,
                "Vancouver, British Columbia": 3,
                "Remote - Canada": 2,
            }
        }
    )
    view = market_view_model({"market_snapshot": snapshot, "requirement_summary": _summary()})

    assert view.geography_counts == (("Ontario", 5), ("British Columbia", 3), ("Remote", 2))
    assert "Ontario" in view.geography_summary
    assert "Toronto" not in view.geography_summary


def test_requirement_themes_contain_only_extracted_requirement_names() -> None:
    view = market_view_model(
        {"market_snapshot": MARKET_SNAPSHOT, "requirement_summary": _summary()}
    )
    themed = {
        requirement for theme in view.requirement_themes for requirement in theme.requirements
    }

    assert themed == {item.name for item in view.requirements}
    assert {theme.name for theme in view.requirement_themes} == {
        "Technical / functional capability",
        "Ownership / leadership",
    }


def test_market_view_is_independent_of_candidate_synthesis() -> None:
    base_state = {"market_snapshot": MARKET_SNAPSHOT, "requirement_summary": _summary()}

    without_candidate = market_view_model(base_state)
    with_candidate = market_view_model(
        {
            **base_state,
            "career_assessment_synthesis": object(),
            "role_assessment": object(),
        }
    )

    assert with_candidate == without_candidate


def test_related_titles_do_not_change_target_role_requirement_frequency() -> None:
    summary = _summary()
    requirement = summary.capability_requirements[0]
    requirement.related_title_occurrence_count = 3
    requirement.exact_and_variant_frequency = 1.0
    requirement.combined_frequency = 1.0
    summary.exact_title_analyzed_count = 1
    summary.related_title_analyzed_count = 3

    view = market_view_model({"market_snapshot": MARKET_SNAPSHOT, "requirement_summary": summary})

    row = next(item for item in view.requirements if item.name == requirement.normalized_capability)
    assert row.occurrences == 1
    assert row.sample_size == 1
    assert row.frequency == 1.0


def test_chart_datasets_keep_real_counts_and_omit_zero_segments() -> None:
    frequency = build_requirement_frequency_figure((("Python", 0.75, 3, 4),))
    title_mix = build_segmented_bar_figure(
        (("Exact target", 3), ("Target variants", 0), ("Related titles", 7))
    )

    assert list(frequency.data[0].customdata[0]) == [3, 4]
    assert [trace.name for trace in title_mix.data] == ["Exact target", "Related titles"]
    assert [trace.x[0] for trace in title_mix.data] == [3, 7]


def test_analysis_counts_match_the_role_assessment() -> None:
    view = analysis_view_model(
        {
            "role_assessment": ROLE_ASSESSMENT,
            "requirement_summary": _summary(),
            "career_assessment_synthesis": DEMO_CAREER_SYNTHESIS,
        }
    )

    assert view.direct_count == DEMO_CAREER_SYNTHESIS.direct_match_count
    assert view.transferable_count == DEMO_CAREER_SYNTHESIS.transferable_match_count
    assert view.partial_count == DEMO_CAREER_SYNTHESIS.partial_match_count
    assert view.no_match_count == DEMO_CAREER_SYNTHESIS.no_confirmed_match_count
    assert (
        view.direct_count
        + view.transferable_count
        + view.partial_count
        + view.no_match_count
        + view.unassessed_count
        == view.total_requirements
    )
    assert view.material_gap_count == len(DEMO_CAREER_SYNTHESIS.grouped_gaps)
    assert view.total_requirements == len(DEMO_CAREER_SYNTHESIS.source_comparison_ids)


def test_grouped_gaps_preserve_every_underlying_material_gap_id() -> None:
    view = analysis_view_model(
        {
            "role_assessment": ROLE_ASSESSMENT,
            "requirement_summary": _summary(),
            "confirmed_profile": CANDIDATE_PROFILE,
            "career_assessment_synthesis": DEMO_CAREER_SYNTHESIS,
        }
    )
    represented = {gap_id for group in view.grouped_gaps for gap_id in group.gap_ids}
    expected = set(DEMO_CAREER_SYNTHESIS.source_gap_ids)

    assert represented == expected
    assert len(view.grouped_gaps) == len(DEMO_CAREER_SYNTHESIS.grouped_gaps)
    assert all(group.underlying_requirement_count >= 1 for group in view.grouped_gaps)


def test_raw_comparisons_cannot_override_the_synthesis_story() -> None:
    contradictory_role = ROLE_ASSESSMENT.model_copy(
        update={
            "candidate_accessibility": CandidateAccessibility.APPLY_NOW,
            "explanation": "Raw role story that must not be shown.",
            "requirement_comparisons": [],
            "gaps": [],
        }
    )

    view = analysis_view_model(
        {
            "role_assessment": contradictory_role,
            "requirement_summary": _summary(),
            "confirmed_profile": CANDIDATE_PROFILE,
            "career_assessment_synthesis": DEMO_CAREER_SYNTHESIS,
        }
    )

    assert view.accessibility == "Aspirational target"
    assert view.assessment_reason == DEMO_CAREER_SYNTHESIS.accessibility_rationale
    assert view.direct_count == DEMO_CAREER_SYNTHESIS.direct_match_count
    assert [item.capability for item in view.strongest_matches] == [
        item.title for item in DEMO_CAREER_SYNTHESIS.demonstrated_strengths
    ]
    assert [(item.experience, item.translation) for item in view.transferable_strengths] == [
        (item.source_capability, item.target_application)
        for item in DEMO_CAREER_SYNTHESIS.transferable_strengths
    ]
    assert "Raw role story" not in view.what_this_means
    assert view.what_this_means == DEMO_CAREER_SYNTHESIS.assessment_summary


@pytest.mark.parametrize(
    ("accessibility", "label"),
    (
        (CandidateAccessibility.APPLY_NOW, "Apply now"),
        (CandidateAccessibility.APPLY_SELECTIVELY, "Apply selectively"),
        (CandidateAccessibility.NEAR_TERM_TARGET, "Near-term target"),
        (CandidateAccessibility.ASPIRATIONAL, "Aspirational target"),
        (CandidateAccessibility.POOR_FIT, "Poor fit"),
        (CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE, "Insufficient evidence"),
    ),
)
def test_analysis_translates_every_accessibility_enum(
    accessibility: CandidateAccessibility, label: str
) -> None:
    synthesis = DEMO_CAREER_SYNTHESIS.model_copy(update={"accessibility": accessibility})

    view = analysis_view_model(
        {
            "role_assessment": ROLE_ASSESSMENT,
            "career_assessment_synthesis": synthesis,
        }
    )

    assert view.accessibility == label
    assert accessibility.value not in view.accessibility


def test_empty_market_comparison_does_not_imply_full_readiness() -> None:
    empty_role = ROLE_ASSESSMENT.model_copy(update={"requirement_comparisons": [], "gaps": []})

    view = analysis_view_model(
        {
            "role_assessment": empty_role,
            "requirement_summary": SimpleNamespace(analyzed_posting_count=0, requirements=[]),
            "career_assessment_synthesis": DEMO_CAREER_SYNTHESIS.model_copy(
                update={
                    "accessibility": "INSUFFICIENT_CANDIDATE_EVIDENCE",
                    "strongest_advantages": [],
                    "transferable_strengths": [],
                    "grouped_gaps": [],
                    "source_comparison_ids": [],
                    "source_gap_ids": [],
                    "direct_match_count": 0,
                    "transferable_match_count": 0,
                    "partial_match_count": 0,
                    "no_confirmed_match_count": 0,
                    "insufficient_comparison_count": 0,
                    "assessment_summary": "No primary target comparison is available.",
                    "accessibility_rationale": "Candidate accessibility could not be assessed.",
                }
            ),
        }
    )

    assert view.readiness_dimensions == ()
    assert view.accessibility == "Insufficient evidence"
    assert view.verdict == "No primary target comparison is available."


def test_raw_market_fragments_and_diagnostics_are_not_exposed() -> None:
    raw = (
        "Pay Range: 105,000 - 135,000",
        "Benefits include stock-purchase discounts.",
        "Rejected 2 metadata, responsibility, or non-canonical items.",
        "Provider validation error: missing field item_type.",
    )

    cleaned = user_facing_limitations(raw)
    plan_copy = plan_limitations({"requirement_summary": _summary(), "limitations": list(raw)})

    assert not any("salary" in item.casefold() or "benefit" in item.casefold() for item in cleaned)
    assert not any("rejected 2" in item.casefold() for item in cleaned)
    assert not any("missing field" in item.casefold() for item in cleaned)
    assert not any(
        fragment in " ".join(plan_copy).casefold() for fragment in ("pay range", "stock")
    )
    assert cleaned == (
        "Some posting content was excluded because it did not describe candidate requirements.",
        "Some source records could not be validated for this bounded sample.",
    )


def test_plan_approval_gate_rejects_insufficient_plan_and_accepts_valid_plan() -> None:
    valid = plan_eligibility(CAREER_PLAN, ROLE_ASSESSMENT, DEMO_CAREER_SYNTHESIS)
    insufficient = CAREER_PLAN.model_copy(
        update={
            "current_role": None,
            "path_type": PathType.EXPLORATION,
            "confidence": ConfidenceLevel.INSUFFICIENT,
        }
    )

    assert valid.can_approve
    assert not plan_eligibility(insufficient, ROLE_ASSESSMENT, DEMO_CAREER_SYNTHESIS).can_approve


def test_internal_enum_names_are_translated() -> None:
    assert product_label("INSUFFICIENT_CANDIDATE_EVIDENCE") == "Not enough candidate evidence"
    assert product_label("CONFIRMED_INFERENCE") == "Confirmed inference"
    assert "_" not in product_label("COMBINED_RELATED")


def test_live_pages_do_not_import_or_substitute_demo_data() -> None:
    source = Path(live_views.__file__).read_text(encoding="utf-8")

    assert "ui.demo_data" not in source
    assert "synthetic demonstration data" not in source.casefold()


def test_demo_profile_renders_all_evidence_without_card_count_assumptions() -> None:
    app_path = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"
    app = AppTest.from_file(app_path).run()
    app.session_state["profile_input_mode"] = "demo"
    app.session_state["current_step"] = "Profile"
    app.session_state["highest_reached_step"] = "Plan"

    rendered = app.run()

    assert not rendered.exception


def _render_live_plan(plan: object) -> AppTest:
    app_path = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"
    app = AppTest.from_file(app_path).run()
    app.session_state["current_step"] = "Plan"
    app.session_state["highest_reached_step"] = "Plan"
    app.session_state["profile_input_mode"] = "manual"
    app.session_state["live_graph_state"] = {
        "career_plan": plan,
        "role_assessment": ROLE_ASSESSMENT,
        "requirement_summary": _summary(),
        "career_assessment_synthesis": DEMO_CAREER_SYNTHESIS,
    }
    return app.run(timeout=10)


def _render_live_view(view: str) -> AppTest:
    app_path = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"
    app = AppTest.from_file(app_path).run()
    app.session_state["current_step"] = view
    app.session_state["highest_reached_step"] = "Plan"
    app.session_state["profile_input_mode"] = "manual"
    app.session_state["live_graph_state"] = {
        "market_snapshot": MARKET_SNAPSHOT,
        "requirement_summary": _summary(),
        "role_assessment": ROLE_ASSESSMENT,
        "confirmed_profile": CANDIDATE_PROFILE,
        "career_assessment_synthesis": DEMO_CAREER_SYNTHESIS,
    }
    return app.run(timeout=10)


def _target_profile(status: RoleProfileStatus) -> CanonicalTargetRoleProfile:
    sufficient = status is not RoleProfileStatus.INSUFFICIENT
    return CanonicalTargetRoleProfile(
        target_role="AI Solutions Architect",
        geography="Toronto, Canada",
        profile_status=status,
        confidence=ConfidenceLevel.LOW if sufficient else ConfidenceLevel.INSUFFICIENT,
        exact_posting_count=1,
        variant_posting_count=2 if sufficient else 0,
        related_posting_count=3,
        distinct_exact_employer_count=1,
        distinct_variant_employer_count=2 if sufficient else 0,
        analyzed_exact_posting_count=1,
        analyzed_variant_posting_count=2 if sufficient else 0,
        analyzed_related_posting_count=3,
        generated_at=DEMO_DATETIME,
    )


def _render_evidence_boundary_view(view: str, *, provisional: bool) -> AppTest:
    app_path = Path(__file__).parents[2] / "src" / "ai_career_navigator" / "app.py"
    app = AppTest.from_file(app_path).run()
    app.session_state["current_step"] = view
    app.session_state["highest_reached_step"] = "Plan"
    app.session_state["profile_input_mode"] = "manual"
    snapshot = MARKET_SNAPSHOT.model_copy(
        update={
            "validated_posting_count": 6,
            "exact_title_count": 1,
            "target_variant_count": 2 if provisional else 0,
            "related_title_count": 3 if provisional else 5,
            "target_variant_titles": (
                ["AI Solution Architect", "GenAI Solutions Architect"] if provisional else []
            ),
        }
    )
    state = {
        "market_snapshot": snapshot,
        "requirement_summary": _summary(),
        "canonical_target_role_profile": _target_profile(
            RoleProfileStatus.PROVISIONAL if provisional else RoleProfileStatus.INSUFFICIENT
        ),
    }
    if provisional:
        state.update(
            {
                "role_assessment": ROLE_ASSESSMENT,
                "confirmed_profile": CANDIDATE_PROFILE,
                "career_assessment_synthesis": DEMO_CAREER_SYNTHESIS,
                "career_plan": CAREER_PLAN,
            }
        )
    app.session_state["live_graph_state"] = state
    return app.run(timeout=10)


def _rendered_text(app: AppTest) -> str:
    return " ".join(
        item.value
        for collection in (
            app.title,
            app.header,
            app.subheader,
            app.markdown,
            app.caption,
            app.info,
            app.warning,
        )
        for item in collection
    )


def test_live_market_and_analysis_render_real_state_metrics() -> None:
    market = _render_live_view("Market")
    analysis = _render_live_view("Analysis")

    assert not market.exception
    assert not analysis.exception
    market_text = " ".join(
        item.value
        for collection in (market.markdown, market.caption, market.subheader, market.info)
        for item in collection
    )
    assert "Market dimensions" in market_text
    assert "4 of 15 validated postings were successfully analyzed (27% coverage)" in market_text
    assert "related titles do not affect target-role frequency" in market_text
    assert "Directional sample" in market_text
    assert "What this means for your search" in market_text
    assert "secondary context" in market_text
    assert "Synthetic demonstration data" not in market_text
    market_metrics = {metric.label: metric.value for metric in market.metric}
    assert market_metrics["Exact target postings"] == "6"
    assert market_metrics["Target variants"] == "0"
    assert market_metrics["Related-title evidence"] == "9"
    assert market_metrics["Expanded market evidence"] == "15"
    assert not any("Observed evidence" in frame.value.columns for frame in market.dataframe)
    assert "How this sample is calculated" in {item.label for item in market.expander}
    assert {metric.label: metric.value for metric in analysis.metric}["Directly aligned"] == "1"
    assert "Requirements covered" not in {metric.label for metric in analysis.metric}
    assert {metric.label: metric.value for metric in analysis.metric}["Partial matches"] == "2"
    assert not any("%" in metric.value for metric in analysis.metric)
    metric_values = {metric.label: metric.value for metric in analysis.metric}
    assert metric_values["Material career gaps"] == str(len(DEMO_CAREER_SYNTHESIS.grouped_gaps))


def test_provisional_variant_supported_state_renders_market_analysis_and_plan() -> None:
    market = _render_evidence_boundary_view("Market", provisional=True)
    analysis = _render_evidence_boundary_view("Analysis", provisional=True)
    plan = _render_evidence_boundary_view("Plan", provisional=True)

    assert not market.exception
    assert not analysis.exception
    assert not plan.exception
    metrics = {metric.label: metric.value for metric in market.metric}
    assert metrics["Exact target postings"] == "1"
    assert metrics["Target variants"] == "2"
    assert "Limited target-role evidence" not in _rendered_text(market)
    assert "Candidate accessibility" in _rendered_text(analysis)
    assert "Your career strategy" in _rendered_text(plan)
    for page in (market, analysis, plan):
        assert "Provisional target-role evidence" in _rendered_text(page)
        assert "not every employer" in _rendered_text(page)


def test_insufficient_state_is_controlled_across_market_analysis_and_plan() -> None:
    market = _render_evidence_boundary_view("Market", provisional=False)
    analysis = _render_evidence_boundary_view("Analysis", provisional=False)
    plan = _render_evidence_boundary_view("Plan", provisional=False)

    assert not market.exception
    assert not analysis.exception
    assert not plan.exception
    assert "Limited target-role evidence" in _rendered_text(market)
    assert "More evidence is needed" in _rendered_text(analysis)
    assert "A reliable career plan cannot be built yet" in _rendered_text(plan)
    assert "Approve Plan" not in {button.label for button in plan.button}


def test_empty_market_does_not_claim_opportunities_were_found_or_zero_percent_coverage() -> None:
    app = _render_evidence_boundary_view("Market", provisional=False)
    state = app.session_state["live_graph_state"]
    state["market_snapshot"] = MARKET_SNAPSHOT.model_copy(update={
        "validated_posting_count": 0, "exact_title_count": 0,
        "target_variant_count": 0, "related_title_count": 0,
    })
    state["requirement_summary"] = None
    app.session_state["live_graph_state"] = state
    app.run()
    text = _rendered_text(app)
    assert not app.exception
    assert "no postings passed validation" in text
    assert "opportunities were found" not in text
    assert "coverage unavailable: no validated postings" in text
    assert "(0% coverage)" not in text


def test_market_distinguishes_schema_valid_responses_from_grounded_hiring_evidence() -> None:
    summary = _summary()
    summary.schema_valid_extraction_count = 4
    summary.postings_with_accepted_hiring_requirements = 2
    summary.rejected_grounding_item_count = 22
    view = market_view_model({"market_snapshot": MARKET_SNAPSHOT, "requirement_summary": summary})
    assert "4 schema-valid posting responses" in view.extraction_quality_summary
    assert "2 postings supplied grounded hiring requirements" in view.extraction_quality_summary
    assert "22 unsupported items rejected" in view.extraction_quality_summary
    assert "only failed grounding are excluded" in view.extraction_quality_summary


def test_analysis_render_uses_synthesis_content_and_hides_internal_ids() -> None:
    analysis = _render_live_view("Analysis")
    text = _rendered_text(analysis)

    assert not analysis.exception
    assert DEMO_CAREER_SYNTHESIS.accessibility_rationale in text
    assert "100% requirements covered" not in text.casefold()
    assert "fit percentage" not in text.casefold()
    assert DEMO_CAREER_SYNTHESIS.accessibility.value not in text
    assert all(item.title in text for item in DEMO_CAREER_SYNTHESIS.demonstrated_strengths)
    assert "Relevant target requirements" not in text
    assert "Supporting evidence" not in {item.label for item in analysis.expander}
    assert all(item.target_requirement in text for item in DEMO_CAREER_SYNTHESIS.target_alignments)
    assert all(item.display_title in text for item in DEMO_CAREER_SYNTHESIS.grouped_gaps)
    assert all(
        requirement in text
        for item in DEMO_CAREER_SYNTHESIS.grouped_gaps
        for requirement in item.underlying_requirement_names
    )
    assert not any(str(gap_id) in text for gap_id in DEMO_CAREER_SYNTHESIS.source_gap_ids)


def test_valid_plan_displays_approval_action() -> None:
    app = _render_live_plan(CAREER_PLAN)

    assert not app.exception
    assert "Approve Plan" in {button.label for button in app.button}


def test_insufficient_plan_never_displays_approval_action() -> None:
    plan = CAREER_PLAN.model_copy(
        update={
            "current_role": None,
            "path_type": PathType.EXPLORATION,
            "confidence": ConfidenceLevel.INSUFFICIENT,
        }
    )
    app = _render_live_plan(plan)

    assert not app.exception
    assert "Approve Plan" not in {button.label for button in app.button}
    assert "Review profile" in {button.label for button in app.button}


def test_valid_untimed_plan_is_approval_ready_and_never_renders_zero_months() -> None:
    timeline = CAREER_PLAN.timeline_assessment.model_copy(
        update={
            "requested_months": None,
            "classification": TimelineClassification.NO_FIXED_TIMELINE,
            "confidence": ConfidenceLevel.MODERATE,
        }
    )
    plan = CAREER_PLAN.model_copy(update={"timeline_assessment": timeline})

    eligibility = plan_eligibility(plan, ROLE_ASSESSMENT, DEMO_CAREER_SYNTHESIS)
    app = _render_live_plan(plan)
    rendered_text = " ".join(
        item.value
        for collection in (app.markdown, app.caption, app.subheader)
        for item in collection
    )

    assert eligibility.can_approve
    assert not app.exception
    assert "Untimed roadmap" in rendered_text
    assert "Months 0–0" not in rendered_text
    assert "Approve Plan" in {button.label for button in app.button}


def test_plan_actions_retain_real_material_gap_ids() -> None:
    view = plan_view_model(CAREER_PLAN, ROLE_ASSESSMENT, DEMO_CAREER_SYNTHESIS)
    known_gap_ids = {gap.gap_id for gap in ROLE_ASSESSMENT.gaps}

    assert len(view.actions) == len(CAREER_PLAN.milestones)
    assert all(action.gap_ids for action in view.actions)
    assert {gap_id for action in view.actions for gap_id in action.gap_ids} <= known_gap_ids
    assert [action.action for action in view.actions] == [
        item.action for item in CAREER_PLAN.milestones
    ]


def test_plan_story_and_actions_come_from_synthesis() -> None:
    contradictory_role = ROLE_ASSESSMENT.model_copy(
        update={"candidate_accessibility": CandidateAccessibility.APPLY_NOW}
    )

    view = plan_view_model(CAREER_PLAN, contradictory_role, DEMO_CAREER_SYNTHESIS)

    assert view.accessibility == "Aspirational target"
    assert view.recommended_path == "Bridge route"
    assert view.route == (
        ("CURRENT ROLE", CAREER_PLAN.current_role),
        ("NEXT STEP / BRIDGE", view.bridge_role),
        ("TARGET ROLE", CAREER_PLAN.target_role),
    )
    assert [item.title for item in view.strengths] == [
        item.title for item in DEMO_CAREER_SYNTHESIS.strongest_advantages[:4]
    ]
    assert {item.action for item in view.actions} == {
        item.action for item in CAREER_PLAN.milestones
    }
    assert all(item.completion_condition for item in view.actions)


def test_untimed_roadmap_uses_ordinal_stages_without_months() -> None:
    timeline = CAREER_PLAN.timeline_assessment.model_copy(
        update={
            "requested_months": None,
            "classification": TimelineClassification.NO_FIXED_TIMELINE,
            "confidence": ConfidenceLevel.MODERATE,
        }
    )
    plan = CAREER_PLAN.model_copy(update={"timeline_assessment": timeline})
    view = plan_view_model(plan, ROLE_ASSESSMENT, DEMO_CAREER_SYNTHESIS)

    stages = untimed_roadmap_stages(view)

    assert len(stages) == len(plan.milestones)
    assert [detail for _, detail in stages] == [item.action for item in plan.milestones]
    assert all(stage.startswith("STEP ") for stage, _ in stages)
    assert not any("month" in detail.casefold() for _, detail in stages)
    assert plan_eligibility(plan, ROLE_ASSESSMENT, DEMO_CAREER_SYNTHESIS).can_approve


def test_plan_approval_requires_synthesis_and_valid_gap_provenance() -> None:
    invalid_milestone = CAREER_PLAN.milestones[0].model_copy(update={"linked_gap_ids": [uuid4()]})
    invalid_plan = CAREER_PLAN.model_copy(
        update={"milestones": [invalid_milestone, *CAREER_PLAN.milestones[1:]]}
    )

    assert not plan_eligibility(CAREER_PLAN, ROLE_ASSESSMENT).can_approve
    assert not plan_eligibility(invalid_plan, ROLE_ASSESSMENT, DEMO_CAREER_SYNTHESIS).can_approve
    insufficient_synthesis = DEMO_CAREER_SYNTHESIS.model_copy(
        update={"confidence": ConfidenceLevel.INSUFFICIENT}
    )
    assert not plan_eligibility(CAREER_PLAN, ROLE_ASSESSMENT, insufficient_synthesis).can_approve
    blocking_role = ROLE_ASSESSMENT.model_copy(
        update={
            "gaps": [
                ROLE_ASSESSMENT.gaps[0].model_copy(update={"hard_blocker": True}),
                *ROLE_ASSESSMENT.gaps[1:],
            ]
        }
    )
    assert not plan_eligibility(CAREER_PLAN, blocking_role, DEMO_CAREER_SYNTHESIS).can_approve


def test_ready_same_role_plan_has_only_its_actual_application_step() -> None:
    from ai_career_navigator.domain import BridgeOutcome
    from tests.career.test_plan_generation import generate, timeline

    result = generate(
        CandidateAccessibility.APPLY_NOW,
        [],
        BridgeOutcome.NO_BRIDGE_REQUIRED,
        timeline_assessment=timeline(None, TimelineClassification.NO_FIXED_TIMELINE),
    )
    ready_role = ROLE_ASSESSMENT.model_copy(update={"gaps": []})
    ready_synthesis = DEMO_CAREER_SYNTHESIS.model_copy(
        update={
            "accessibility": CandidateAccessibility.APPLY_NOW,
            "grouped_gaps": [],
            "source_gap_ids": [],
            "accessibility_rationale": (
                "Confirmed evidence supports the primary target requirements."
            ),
        }
    )
    view = plan_view_model(result.plan, ready_role, ready_synthesis)
    assert len(untimed_roadmap_stages(view)) == 1
    assert view.actions[0].action == result.plan.milestones[0].action
    assert not view.actions[0].gap_ids
    assert "BUILD / BRIDGE" not in str(untimed_roadmap_stages(view))
    assert "remaining priority dimensions" not in str(view)
    # A student or returner does not need to invent a current job to approve a plan.
    assert result.plan.current_role is None
    assert plan_eligibility(result.plan, ready_role, ready_synthesis).can_approve


def test_market_funnel_explains_17_validated_and_four_analyzed() -> None:
    snapshot = MARKET_SNAPSHOT.model_copy(update={"validated_posting_count": 17})
    summary = _summary()
    summary.capability_requirements[0].exact_title_occurrence_count = 2
    summary.capability_requirements[0].exact_and_variant_frequency = 0.99
    view = market_view_model({"market_snapshot": snapshot, "requirement_summary": summary})
    assert view.requirements[0].sample_size == 4
    assert view.requirements[0].frequency == 0.5
    assert dict(view.evidence_funnel)["Validated postings not successfully analyzed"] == 13
    assert dict(view.evidence_funnel)["Provider search hits (before deduplication)"] is None


def test_missing_market_denominator_has_no_directional_success_label() -> None:
    view = market_view_model({"market_snapshot": MARKET_SNAPSHOT})
    assert view.requirement_sample_confidence == "Unavailable"
    assert view.requirements == ()


def test_plan_render_hides_internal_enums_and_gap_ids() -> None:
    app = _render_live_plan(CAREER_PLAN)
    text = _rendered_text(app)

    assert not app.exception
    assert DEMO_CAREER_SYNTHESIS.accessibility.value not in text
    assert "PathType.BRIDGE" not in text
    assert "Timeline unsupported" not in text
    assert "Add a target timeline" not in text
    assert not any(str(gap_id) in text for gap_id in DEMO_CAREER_SYNTHESIS.source_gap_ids)


def test_no_fixed_timeline_label_is_user_facing() -> None:
    label = product_label(TimelineClassification.NO_FIXED_TIMELINE)

    assert label == "No fixed timeline"
    assert "_" not in label

"""The combined page renders the saved evidence tracks without live APIs."""

from streamlit.testing.v1 import AppTest


def test_empty_provider_result_is_distinct_from_validation_exclusions():
    for count, expected in [
        (0, "provider returned no postings"),
        (5, "excluded or could not be normalized"),
    ]:
        app = AppTest.from_string(f"""
from ai_career_navigator.ui.pages.assessment import render_assessment
from ai_career_navigator.ui.demo_data import MARKET_SNAPSHOT
from ai_career_navigator.market.schemas import MarketProviderSummary
render_assessment({{
    "market_snapshot": MARKET_SNAPSHOT.model_copy(update={{"validated_posting_count": 0}}),
    "market_provider_summary": MarketProviderSummary(
        raw_source_count={count}, search_queries=["AI engineer in toronto, canada"]),
}})
""").run()
        assert not app.exception
        assert any(expected in item.value for item in app.caption)
        assert any(f"Search returned {count} records" in item.value for item in app.caption)
        assert "AI engineer in toronto, canada" in [item.value for item in app.text]


def test_saved_evidence_tracks_and_audit_render_without_exceptions():
    app = AppTest.from_string("""
from tests.market.test_evidence_tracks import replay_saved_audit
from ai_career_navigator.ui.demo_data import MARKET_SNAPSHOT
from ai_career_navigator.ui.pages.assessment import render_assessment
analysis, audits = replay_saved_audit()
render_assessment({
    "market_snapshot": MARKET_SNAPSHOT,
    "canonical_target_role_profile": analysis.canonical_profile,
    "requirement_summary": analysis.summary,
    "posting_requirement_audits": audits,
})
""").run(timeout=15)
    assert not app.exception
    labels = [element.label for element in app.expander]
    assert not any(
        label.startswith(
            ("Work alignment", "Preferred advantages", "Employer-specific expectations")
        )
        for label in labels
    )
    assert "Source and comparison details" not in labels
    assert labels == ["Run details"]
    table = app.table[0].value
    assert list(table.columns) == ["Competency", "Your position"]
    table = app.expander[0].table[0].value
    assert list(table.columns) == ["No.", "Competency", "Context", "You"]
    assert {"Employer-specific", "Role duty", "Preferred"} <= set(table["Context"])
    assert list(table["No."]) == list(range(1, len(table) + 1))
    # A duty and a hiring expectation can share a name without sharing meaning.
    assert not table.duplicated(subset=["Competency", "Context"]).any()
    assert not any(item.value == "Your evidence" for item in app.caption)
    assert len(app.json) == 1
    assert any("60 extracted statements" in element.value for element in app.caption)
    assert any("not established" in element.value for element in app.warning)
    headings = [item.value for item in app.subheader]
    assert headings == [
        "Your competency snapshot", "What this role involves", "How you compare", "Next step",
    ]


def test_bounded_assessment_shows_processing_check_without_erasing_strengths():
    app = AppTest.from_string("""
from tests.career.test_readiness_coverage_policy import scenario
from ai_career_navigator.career import synthesize_career_assessment
from ai_career_navigator.ui.demo_data import MARKET_SNAPSHOT
from ai_career_navigator.ui.pages.assessment import render_assessment
profile, role, market = scenario(failed=True)
synthesis = synthesize_career_assessment(profile, role, market, None)
render_assessment({
    "market_snapshot": MARKET_SNAPSHOT,
    "confirmed_profile": profile,
    "role_assessment": role,
    "career_assessment_synthesis": synthesis,
    "canonical_target_role_profile": market.canonical_profile,
    "requirement_summary": market.summary,
})
""").run(timeout=15)
    assert not app.exception
    assert any(
        "Processing incomplete; retry comparison: Capability 2" in item.value for item in app.text
    )
    assert any("Apply selectively" in item.value for item in app.markdown)
    assert list(app.table[0].value["Your position"]) == [
        "Demonstrated", "Demonstrated", "Unconfirmed",
    ]
    assert [item.label for item in app.expander] == ["Run details"]
    assert not app.info
    assert any("Processing incomplete" in item.value for item in app.expander[0].text)
    assert [item.value for item in app.subheader] == [
        "Apply selectively",
        "Your competency snapshot",
        "Strengths you bring",
        "How you compare",
        "Questions before deciding",
        "Next step",
    ]


def test_next_step_remains_short_and_does_not_invent_readiness():
    from types import SimpleNamespace

    from ai_career_navigator.domain import CandidateAccessibility
    from ai_career_navigator.ui.pages.assessment import assessment_next_step

    assert "reassess" in assessment_next_step(None, [])
    for value in CandidateAccessibility:
        text = assessment_next_step(SimpleNamespace(accessibility=value), [])
        assert len(text) < 140
        assert text.count(".") == 1


def test_compact_status_preserves_unknown_partial_and_transferable_distinctions():
    from ai_career_navigator.domain import ConfidenceLevel, MatchType
    from ai_career_navigator.ui.pages.assessment import competency_status
    from tests.career.test_readiness_coverage_policy import scenario

    _, role, _ = scenario(unresolved=())
    match = role.requirement_comparisons[0]
    assert competency_status(match) == "Yes"
    assert competency_status(None) == "Unknown"
    assert (
        competency_status(match.model_copy(update={"match_type": MatchType.TRANSFERABLE_MATCH}))
        == "Transferable"
    )
    assert (
        competency_status(match.model_copy(update={"match_type": MatchType.PARTIAL_MATCH}))
        == "Partial"
    )
    for status, expected in [
        ("UNKNOWN", "Unknown"),
        ("OPERATION_FAILED", "Unknown"),
        ("CONFIRMED_UNMET", "No"),
        ("CONTRADICTED", "No"),
    ]:
        assert (
            competency_status(
                match.model_copy(
                    update={"match_type": MatchType.NO_CONFIRMED_MATCH, "evidence_status": status}
                )
            )
            == expected
        )
    assert (
        competency_status(match.model_copy(update={"confidence": ConfidenceLevel.LOW})) == "Unknown"
    )
    assert (
        competency_status(match.model_copy(update={"clarification_needed": "Verify version"}))
        == "Unknown"
    )


def test_production_batch_design_uses_one_table_and_matched_alternative():
    app = AppTest.from_string("""
from tests.market.test_five_posting_batch import completed_batch_state
from ai_career_navigator.ui.pages.assessment import render_assessment
render_assessment(completed_batch_state())
""").run(timeout=15)
    assert not app.exception
    assert app.title[0].value == "Your career assessment"
    assert app.table[0].value["Competency"].tolist() == [
        "Java", "SQL", "Automated Testing", "AWS (additional advantage)",
    ]
    assert list(app.table[0].value.columns) == ["Competency", "Your position"]
    assert [element.label for element in app.expander] == ["Run details"]
    assert not any(element.value == "Your evidence" for element in app.caption)
    assert any("Combined view of 5" in element.value for element in app.caption)
    assert not next(button for button in app.button if button.label == "Continue to Plan").disabled


def test_failed_batch_is_not_presented_as_a_candidate_or_market_shortfall():
    app = AppTest.from_string("""
from tests.market.test_five_posting_batch import completed_batch_state
from ai_career_navigator.ui.pages.assessment import render_assessment
state = completed_batch_state()
state['role_assessment'] = None
state['career_assessment_synthesis'] = None
state['career_plan'] = None
state['canonical_target_role_profile'] = state['canonical_target_role_profile'].model_copy(
    update={'extraction_processing_status': 'PARTIAL', 'profile_status': 'PROVISIONAL'}
)
render_assessment(state)
""").run(timeout=15)
    assert not app.exception
    assert any("model output could not be validated" in item.value for item in app.info)
    assert not any(item.value == "Limited role sample" for item in app.caption)
    assert len(app.table[0].value) == 4
    assert set(app.table[0].value["Your position"]) == {"Unconfirmed"}
    assert next(button for button in app.button if button.label == "Continue to Plan").disabled

"""Review copy summarizes expectations while preserving the original audit."""

import json
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

from ai_career_navigator.ui.pages.same_role import review_text


def story_steps(app):
    return next(
        json.loads(item.proto.json)["steps"] for item in app.get("bidi_component")
        if json.loads(item.proto.json)["mode"] == "actions"
    )


def assessment():
    return SimpleNamespace(
        accessibility="NEAR_TERM_TARGET",
        confidence="MODERATE",
        rationale="Direct AI experience is not established (P1L23, E1). P2 has a specialist ask.",
        role_picture="P1 and P2 describe different directions; this is the original model output.",
        posting_sources={"P1": {"employer": "Example", "title": "AI Engineer"}, "P2": {}},
        source_lines={"P1L23": "Python experience required."},
        competencies=[
            SimpleNamespace(
                name="Python",
                context="COMMON",
                status="NOT_ESTABLISHED",
                candidate_refs=["E1"],
                source_refs=["P1L23"],
                reason="No supplied Python evidence.",
                remaining_need="CLARIFY",
                development_focus="Confirm Python experience (E1).",
            ),
            SimpleNamespace(
                name="L2 support",
                context="SPECIALIST",
                status="DEMONSTRATED",
                candidate_refs=["E1"],
                source_refs=["P1L23"],
                reason="Professional support.",
            ),
        ],
        demonstrated_strengths=[
            SimpleNamespace(
                name="Backend delivery",
                candidate_refs=["E1"],
                why_it_helps="Detailed evidence (E1).",
            )
        ],
        opportunities=[
            SimpleNamespace(
                posting_ref="P1",
                direction="AI applications",
                fit="CONSIDER",
                reason="Posting-specific.",
            )
        ],
        questions=["Have you used Python (E1)?"],
        limitations=[],
        processing_issues=[],
        rule_version="test",
    )


def leadership_assessment():
    result = assessment()
    result.rule_version = "leadership-assessment-v1-concise-v3-fit-scope"
    result.current_readiness = "UNCONFIRMED"
    result.rationale = "Understand your management responsibilities before deciding where to apply."
    result.role_picture = "Lead engineers, own team delivery and coach people."
    for n, c in enumerate(result.competencies):
        c.applicability = "TARGET" if n == 0 else "CONTEXT"
        c.evidence_state = "UNKNOWN" if n == 0 else "CONTEXT"
    result.competencies[0].name = "Formal people management"
    result.competencies[1].name = "Hardware testing"
    result.competencies[1].status = "NOT_RELEVANT"
    result.demonstrated_strengths[0].why_it_helps = (
        "Production backend work supports technical decisions."
    )
    result.questions = ["Have you managed direct reports or conducted performance reviews?"]
    return result


def test_leadership_public_view_is_compact_without_erasing_audit_or_uncertainty():
    app = AppTest.from_string('''
from types import SimpleNamespace
from tests.ui.test_review_presentation import leadership_assessment
from ai_career_navigator.ui.pages.same_role import render_same_role_analysis
render_same_role_analysis({"transition_assessment": leadership_assessment(),
    "confirmed_goal": SimpleNamespace(target_role="Manager", target_location="Toronto")})
''').run()
    assert not app.exception
    headers = [s.value for s in app.subheader]
    assert "A credible leadership direction" in headers
    assert "Near term target" not in headers
    assert "What needs building or clarifying" not in headers
    assert "Questions before deciding" in headers
    assert list(app.table[0].value.columns) == ["Competency", "Your position"]
    assert list(app.table[0].value["Competency"]) == ["Formal people management"]
    assert list(app.table[0].value["Your position"]) == ["Unconfirmed"]
    assert any("Hardware testing" in e.value for e in app.expander[0].markdown)
    assert any("Production backend work supports" in e.value for e in app.markdown)


def test_leadership_review_failure_does_not_get_positive_heading():
    app = AppTest.from_string('''
from types import SimpleNamespace
from tests.ui.test_review_presentation import leadership_assessment
from ai_career_navigator.ui.pages.same_role import render_same_role_analysis
result = leadership_assessment()
result.processing_issues = ["Review needed"]
render_same_role_analysis({"transition_assessment": result,
    "confirmed_goal": SimpleNamespace(target_role="Manager", target_location="Toronto")})
''').run()
    assert not app.exception
    assert "Assessment needs review" in [s.value for s in app.subheader]
    assert "A credible leadership direction" not in [s.value for s in app.subheader]


def test_leadership_plan_preserves_saved_conditions_and_version_notice():
    app = AppTest.from_string('''
from types import SimpleNamespace
from tests.ui.test_review_presentation import leadership_assessment
from ai_career_navigator.domain import PlanStatus
from ai_career_navigator.ui.pages.same_role import render_same_role_plan
plan = SimpleNamespace(
    current_role="Developer", target_role="Manager", plan_status=PlanStatus.DRAFT,
    timing_basis="No fixed timeline; follow these steps in order.",
    milestones=[SimpleNamespace(phase="Step 1", basis="Formal people management",
        action="Only if readiness is supported, apply; otherwise defer and reassess.",
        measurable_outcome="An apply-or-defer decision is recorded.")],
)
render_same_role_plan({"transition_assessment": leadership_assessment(),
    "career_plan": plan}, read_only=True)
''').run()
    assert not app.exception
    assert app.title[0].value == "Your leadership plan"
    assert "A credible leadership direction" in [s.value for s in app.subheader]
    assert "otherwise defer and reassess" in story_steps(app)[0]["action"]
    assert "apply-or-defer decision" in story_steps(app)[0]["done"]
    assert any("Approval applies to this exact plan version" in e.value for e in app.caption)
    assert any("No fixed timeline" in e.value for e in app.caption)


def test_reference_cleanup_preserves_real_skill_names_and_original_data():
    original = assessment()
    assert review_text("Python (P1L23, E1). L2 support; Java 23.", original) == (
        "Python. L2 support; Java 23."
    )
    assert "P1L23" in original.rationale
    assert original.source_lines["P1L23"] == "Python experience required."


def test_analysis_is_a_combined_review_not_a_posting_audit():
    app = AppTest.from_string("""
from types import SimpleNamespace
from tests.ui.test_review_presentation import assessment
from ai_career_navigator.ui.pages.same_role import render_same_role_analysis
render_same_role_analysis({
    "transition_assessment": assessment(),
    "confirmed_goal": SimpleNamespace(target_role="AI Engineer", target_location="Toronto"),
})
""").run()
    assert not app.exception
    assert "What this role involves" in [s.value for s in app.subheader]
    assert "The role in this sample" not in [s.value for s in app.subheader]
    assert "Where to focus your search" not in [s.value for s in app.subheader]
    assert [e.label for e in app.expander] == ["Run details"]
    audit = app.expander[0]
    audit_text = [e.value for e in audit.markdown]
    assert assessment().rationale in audit_text
    assert assessment().role_picture in audit_text
    visible = [e.value for e in app.markdown if e.value not in audit_text]
    assert not any("P1" in t or "P2" in t or "E1" in t for t in visible)
    assert "Direct AI experience is not established." in visible
    assert any("Detailed evidence" in t for t in visible)  # one concise strength explanation
    assert list(app.table[0].value["Competency"]) == ["Python"]
    assert any("L2 support" in t for t in audit_text)


def test_standalone_references_do_not_leave_broken_sentences():
    assert review_text("P1 requires Python; E1 shows backend work.", assessment()) == (
        "the reviewed AI Engineer role requires Python; "
        "your recorded experience shows backend work."
    )


def test_failed_processing_is_review_status_not_candidate_insufficiency():
    app = AppTest.from_string("""
from types import SimpleNamespace
from tests.ui.test_review_presentation import assessment
from ai_career_navigator.ui.pages.same_role import render_same_role_analysis
result = assessment()
result.accessibility = "INSUFFICIENT_CANDIDATE_EVIDENCE"  # historical saved result
result.rationale = "Some output references could not be verified after repair."
result.processing_issues = ["accessibility: positive verdict has no demonstrated common capability"]
render_same_role_analysis({"same_role_assessment": result,
    "confirmed_goal": SimpleNamespace(target_role="Developer", target_location="Toronto")})
""").run()
    assert not app.exception
    assert "Assessment needs review" in [e.value for e in app.subheader]
    assert "Insufficient candidate evidence" not in [e.value for e in app.subheader]
    assert not app.warning
    assert any("positive verdict" in e.value for e in app.expander[0].markdown)


def test_single_role_fit_is_scoped_and_core_work_not_market_frequency():
    app = AppTest.from_string("""
from types import SimpleNamespace
from tests.ui.test_review_presentation import assessment
from ai_career_navigator.ui.pages.same_role import render_same_role_analysis
result = assessment()
result.posting_sources = {"P1": result.posting_sources["P1"]}
result.rule_version = "same-role-assessment-v2-concise-v2-fit-scope"
result.accessibility = "APPLY_SELECTIVELY"
render_same_role_analysis({"same_role_assessment": result,
    "confirmed_goal": SimpleNamespace(target_role="Developer", target_location="Toronto")})
""").run()
    assert not app.exception
    assert "Apply selectively" in [e.value for e in app.subheader]
    assert any("1 reviewed job description;" in e.value for e in app.caption)
    assert any("Limited role sample" in e.value for e in app.caption)
    assert list(app.table[0].value.columns) == ["Competency", "Your position"]
    assert app.table[0].value["Competency"].tolist() == ["Python"]


def test_new_concise_copy_keeps_its_material_second_sentence():
    app = AppTest.from_string("""
from types import SimpleNamespace
from tests.ui.test_review_presentation import assessment
from ai_career_navigator.ui.pages.same_role import render_same_role_analysis
result = assessment()
result.rule_version = "transition-concise-v1"
result.rationale = "An adjacent direction is credible. Confirm Python before applying."
result.role_picture = (
    "Integrate AI capabilities into reliable services. Cloud stacks vary by direction."
)
render_same_role_analysis({
    "transition_assessment": result,
    "confirmed_goal": SimpleNamespace(target_role="AI Engineer", target_location="Toronto"),
})
""").run()
    assert not app.exception
    assert any("credible. Confirm Python" in e.value for e in app.markdown)
    assert any("Cloud stacks vary by direction." in e.value for e in app.markdown)


def test_plan_public_actions_are_clean_and_original_actions_remain_auditable():
    app = AppTest.from_string("""
from types import SimpleNamespace
from tests.ui.test_review_presentation import assessment
from ai_career_navigator.domain import PlanStatus
from ai_career_navigator.ui.pages.same_role import render_same_role_plan
plan = SimpleNamespace(
    current_role="Java Developer", target_role="AI Engineer", plan_status=PlanStatus.DRAFT,
    timing_basis="No fixed timeline; ordered actions, not duration estimates.",
    milestones=[SimpleNamespace(phase="Step 1", basis="Python",
        action="Confirm Python experience before choosing training (P1L23, E1).",
        measurable_outcome="Existing experience or its absence is confirmed (E1).")],
)
render_same_role_plan({"transition_assessment": assessment(), "career_plan": plan}, read_only=True)
""").run()
    assert not app.exception
    assert [e.label for e in app.expander] == ["Plan details"]
    audit = [e.value for e in app.expander[0].markdown]
    assert story_steps(app)[0]["action"] == "Confirm Python experience before choosing training."
    assert any("P1L23" in e for e in audit)
    assert any("No fixed timeline" in e.value for e in app.caption)
    assert any("Approval applies to this exact plan version" in e.value for e in app.caption)
    assert any("review actions are disabled" in e.value for e in app.caption)

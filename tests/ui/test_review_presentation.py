"""Review copy summarizes expectations while preserving the original audit."""

from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

from ai_career_navigator.ui.pages.same_role import review_text


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
    assert not any("Detailed evidence" in t for t in visible)
    assert list(app.table[0].value["Competency"]) == ["Python", "L2 support"]


def test_standalone_references_do_not_leave_broken_sentences():
    assert review_text("P1 requires Python; E1 shows backend work.", assessment()) == (
        "the reviewed AI Engineer role requires Python; "
        "your recorded experience shows backend work."
    )


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
    public = [e.value for e in app.markdown if e.value not in audit]
    assert "Confirm Python experience before choosing training." in public
    assert any("P1L23" in e for e in audit)
    assert any("No fixed timeline" in e.value for e in app.caption)
    assert any("Approval applies to this exact plan version" in e.value for e in app.caption)
    assert any("review actions are disabled" in e.value for e in app.caption)

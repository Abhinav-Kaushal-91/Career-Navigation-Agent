"""Local-file diagnostics must not disguise title rejections or live discovery."""

import sys
from pathlib import Path

from ai_career_navigator.domain import CareerGoal

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from check_local_descriptions import load_descriptions, local_retrieval  # noqa: E402


def test_local_import_keeps_text_and_existing_title_gate(tmp_path):
    body = "Senior Full Stack Developer\nTypeScript and React experience required."
    (tmp_path / "Software Developer.txt").write_text(body, encoding="utf-8")
    evidence, manifest = load_descriptions(tmp_path, "Senior Java Developer")
    assert evidence[0].primary_content.markdown == body
    assert manifest[0]["classification"] == "IRRELEVANT"
    assert evidence[0].provider_sources == []
    assert evidence[0].primary_source.source_type == "USER_SUPPLIED_TEXT"
    assert evidence[0].posting.active_status is None
    assert evidence[0].primary_content.content_complete is None
    goal = CareerGoal(
        goal_type="CURRENT_MARKET_ANALYSIS",
        target_role="Senior Java Developer",
        target_location="Toronto, Canada",
    )
    result = local_retrieval(goal, evidence)
    assert result.snapshot.validated_posting_count == 0
    assert result.snapshot.opportunity_availability == "INSUFFICIENT_EVIDENCE"
    assert result.posting_evidence == evidence
    assert result.primary_search_count == result.you_search_count == 0


def test_reviewed_metadata_can_load_transition_without_title_overrides(tmp_path):
    body = "AI Engineer\nPython and AI application development experience required."
    (tmp_path / "AI Engineer 2.txt").write_text(body, encoding="utf-8")
    metadata = {"AI Engineer 2.txt": ["AI Engineer", "Example", "Location not specified"]}
    evidence, manifest = load_descriptions(tmp_path, "AI Engineer", metadata)
    assert len(evidence) == 1
    assert evidence[0].primary_content.markdown == body
    assert manifest[0]["classification"] == "EXACT_TARGET"
    assert any("City is not established" in note for note in manifest[0]["limitations"])


def test_local_import_counts_two_distinct_roles_at_same_employer(tmp_path):
    metadata = {}
    for n in range(2):
        name = f"AI Engineer {n}.txt"
        (tmp_path / name).write_text(
            "AI Engineer\nAI application experience required.", encoding="utf-8"
        )
        metadata[name] = ["AI Engineer", "Example", "Location not specified"]
    evidence, _ = load_descriptions(tmp_path, "AI Engineer", metadata)
    goal = CareerGoal(
        goal_type="ROLE_TRANSITION", target_role="AI Engineer", target_location="Toronto"
    )
    snapshot = local_retrieval(goal, evidence).snapshot
    assert snapshot.validated_posting_count == 2
    assert snapshot.distinct_employer_count == 1
    assert snapshot.largest_employer_posting_count == 2
    assert snapshot.top_three_employer_posting_count == 2

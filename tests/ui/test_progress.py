from ai_career_navigator.ui.components.progress import (
    LIVE_ANALYSIS_STAGES,
    completed_stage_count,
)


def test_live_progress_uses_seven_user_facing_stages() -> None:
    assert LIVE_ANALYSIS_STAGES == (
        "Reviewing your confirmed profile",
        "Identifying your strengths",
        "Searching the current market",
        "Extracting employer requirements",
        "Comparing your experience",
        "Building your career path",
        "Preparing your career plan",
    )


def test_graph_nodes_map_to_real_user_facing_progress() -> None:
    assert completed_stage_count(None) == 0
    assert completed_stage_count("profile_ready") == 1
    assert completed_stage_count("capability_inference") == 2
    assert completed_stage_count("market_retrieval") == 3
    assert completed_stage_count("market_processing") == 4
    assert completed_stage_count("candidate_requirement_comparison") == 5
    assert completed_stage_count("timeline_assessment") == 6
    assert completed_stage_count("career_plan_generation") == 7


def test_unknown_graph_node_never_invents_progress() -> None:
    assert completed_stage_count("unrecognized_internal_step") == 0

import asyncio

from scripts.run_goal_case_matrix import run_all


def test_goal_case_matrix_covers_two_sets_for_all_six_goal_types() -> None:
    results = asyncio.run(run_all())

    assert len(results) == 12
    assert len({item["case_id"] for item in results}) == 12
    assert sum(item["workflow_status"] == "Waiting For Human" for item in results) == 9
    assert sum(item["workflow_status"] == "Insufficient Evidence" for item in results) == 1
    assert sum(item["workflow_status"] == "Role Discovery Required" for item in results) == 2
    assert all(item["run_mode"] == "DETERMINISTIC_BACKEND" for item in results)

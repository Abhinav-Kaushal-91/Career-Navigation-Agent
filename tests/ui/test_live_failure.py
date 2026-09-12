from types import SimpleNamespace
from uuid import uuid4

import pytest

from ai_career_navigator.orchestration.failure_diagnostics import record_live_failure
from ai_career_navigator.ui.demo_data import CAREER_GOAL
from ai_career_navigator.ui.pages import goal
from tests.ui.test_goal_app import goal_app


class Session(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


@pytest.mark.parametrize(
    "category,word",
    [
        ("MARKETTIMEOUTERROR", "timed out"),
        ("MARKETRATELIMITERROR", "quota"),
        ("MARKETCONTENTERROR", "expected format"),
    ],
)
def test_actionable_messages(category, word):
    assert word in goal._safe_live_failure_message(category)


@pytest.mark.parametrize("failure_mode", ["returned", "initialization", "exception"])
def test_failed_attempt_records_without_exception_payload(
    monkeypatch, tmp_path, caplog, failure_mode
):
    state = {
        "run_id": uuid4(),
        "current_stage": "MARKET_RETRIEVAL",
        "workflow_status": "FAILED",
        "last_error": "MARKETTIMEOUTERROR",
    }
    session = Session(confirmed_profile={"private": "SECRET_PROFILE"})
    monkeypatch.setattr(goal.st, "session_state", session)
    monkeypatch.setattr(
        goal, "CandidateProfile", SimpleNamespace(model_validate=lambda _: object())
    )
    monkeypatch.setattr(goal, "load_live_settings", lambda: object())
    monkeypatch.setattr(goal, "surface_graph_workflow_state", lambda _: None)
    monkeypatch.setattr(
        goal,
        "record_live_failure",
        lambda *a, **kw: record_live_failure(
            *a,
            **kw,
            directory=tmp_path,
        ),
    )

    class Controller:
        async def stream_start(self, **kwargs):
            yield "goal_ready"
            if failure_mode == "exception":
                raise TypeError("SECRET_API_KEY and SECRET_PROFILE")

        def inspect(self, **kwargs):
            return SimpleNamespace(state=state, interrupts=[])

    def build(_):
        if failure_mode == "initialization":
            raise ValueError("SECRET_API_KEY")
        return SimpleNamespace(controller=Controller())

    monkeypatch.setattr(goal, "build_live_workflow_runtime", build)
    assert goal._start_live_workflow(CAREER_GOAL, on_progress=lambda _: None) is False
    record = session.live_failure_diagnostic
    expected = {
        "returned": "MARKET_TIMEOUT",
        "initialization": "INTERNAL_VALUE_ERROR",
        "exception": "INTERNAL_TYPE_ERROR",
    }
    assert record["error_code"] == expected[failure_mode]
    assert record["record_saved"]
    assert len(list(tmp_path.glob("*.json"))) == 1
    assert "SECRET" not in caplog.text
    assert "SECRET" not in next(tmp_path.glob("*.json")).read_text()
    assert session.confirmed_profile == {"private": "SECRET_PROFILE"}


def test_failure_code_and_details_survive_goal_page_rerender(tmp_path):
    app = goal_app()
    app.session_state["goal_confirmed"] = True
    app.session_state["confirmed_goal"] = CAREER_GOAL.model_dump(mode="json")
    app.session_state["live_workflow_error"] = "MARKETTIMEOUTERROR"
    app.session_state["live_failure_diagnostic"] = record_live_failure(
        "MARKETTIMEOUTERROR",
        stage="MARKET_RETRIEVAL",
        elapsed_seconds=30,
        directory=tmp_path,
    )
    app.run()
    assert not app.exception
    assert any("Error code: MARKET_TIMEOUT" in c.value for c in app.caption)
    assert any(e.label == "Failure details" for e in app.expander)
    assert any("timed out" in c.value for c in app.caption)

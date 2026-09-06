from ai_career_navigator.models import ModelRole, TrackingModelProvider
from ai_career_navigator.models.providers import FakeModelProvider
from ai_career_navigator.models.schemas import ModelRequest


def test_tracking_provider_records_safe_usage_without_content() -> None:
    private = "private candidate evidence"
    tracked = TrackingModelProvider(FakeModelProvider(outcomes=["result"]))

    response = tracked.generate_text(
        request=ModelRequest(role=ModelRole.REASONING, user_prompt=private),
        model="fake-reasoning",
        timeout_seconds=10,
    )

    assert response.content == "result"
    assert tracked.usage.calls == 1
    assert tracked.usage.successful_calls == 1
    assert tracked.usage.input_tokens == 1
    assert tracked.usage.output_tokens == 1
    assert private not in repr(tracked.usage)


def test_tracking_provider_records_only_failure_category() -> None:
    tracked = TrackingModelProvider(FakeModelProvider(outcomes=[TimeoutError("private detail")]))

    try:
        tracked.generate_text(
            request=ModelRequest(role=ModelRole.EXTRACTION, user_prompt="private prompt"),
            model="fake-extraction",
            timeout_seconds=10,
        )
    except TimeoutError:
        pass

    assert tracked.usage.failed_calls == 1
    assert tracked.usage.failure_categories == ["TimeoutError"]
    assert "private" not in repr(tracked.usage)

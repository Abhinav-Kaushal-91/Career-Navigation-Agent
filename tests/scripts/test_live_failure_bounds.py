import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_career_navigator.models import ModelGatewayError


def test_diagnostic_model_call_cap_stops_before_provider_access(tmp_path):
    path = Path(__file__).parents[2] / "scripts/check_demo_to_analysis.py"
    spec = importlib.util.spec_from_file_location("bounded_demo_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    recorder = module.BoundedRecorder(
        SimpleNamespace(provider_name="mock"),
        tmp_path,
        None,
        max_calls=0,
    )
    with pytest.raises(ModelGatewayError, match="budget exhausted"):
        recorder.generate_structured()
    assert recorder.calls == 0
    assert not list(tmp_path.iterdir())

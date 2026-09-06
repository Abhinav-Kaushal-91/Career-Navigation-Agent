def test_public_model_gateway_import_foundation() -> None:
    from ai_career_navigator.models import ModelGateway, ModelRole

    assert ModelGateway.__name__ == "ModelGateway"
    assert ModelRole.EXTRACTION.value == "EXTRACTION"

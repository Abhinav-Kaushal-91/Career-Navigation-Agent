"""Production-provider runtime construction for one Streamlit session."""

from dataclasses import dataclass
from pathlib import Path

from ai_career_navigator.config import Settings
from ai_career_navigator.market import (
    build_enrichment_market_client,
    build_primary_market_client,
)
from ai_career_navigator.market.batch_profile import analyze_five_postings
from ai_career_navigator.models import ModelGateway
from ai_career_navigator.models.protocols import ModelProvider
from ai_career_navigator.models.providers import configured_provider
from ai_career_navigator.models.tracking import ModelUsage, TrackingModelProvider
from ai_career_navigator.orchestration import (
    CareerWorkflowController,
    TransientMarketContentStore,
    WorkflowRuntimeContext,
    build_career_graph,
)


@dataclass(frozen=True)
class LiveWorkflowRuntime:
    controller: CareerWorkflowController
    model_gateway: ModelGateway
    model_usage: ModelUsage


def load_live_settings() -> Settings:
    """Load the local UI env file explicitly when the project-root file is absent."""

    root_env = Path(".env")
    package_env = Path("src/ai_career_navigator/.env")
    env_file = root_env if root_env.is_file() else package_env
    return Settings(_env_file=env_file if env_file.is_file() else None)


def build_live_workflow_runtime(
    settings: Settings, *, provider_override: ModelProvider | None = None
) -> LiveWorkflowRuntime:
    """Build an isolated in-memory graph runtime using configured production providers."""

    tracked = TrackingModelProvider(provider_override or configured_provider(settings))
    gateway = ModelGateway.from_settings(settings, providers={tracked.provider_name: tracked})
    context = WorkflowRuntimeContext(
        settings=settings,
        model_gateway=gateway,
        market_client_factory=lambda: build_enrichment_market_client(settings),
        structured_market_client_factory=lambda: build_primary_market_client(settings),
        content_store=TransientMarketContentStore(),
        market_processing_service=analyze_five_postings,
    )
    controller = CareerWorkflowController(build_career_graph(), context)
    return LiveWorkflowRuntime(
        controller=controller,
        model_gateway=gateway,
        model_usage=tracked.usage,
    )

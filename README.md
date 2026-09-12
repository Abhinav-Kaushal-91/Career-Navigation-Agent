# AI Career Strategy & Market Navigator

Current-market retrieval uses **JSearch through RapidAPI**, replacing the active Adzuna and
You.com routes. One bounded search supplies job descriptions; up to five detail requests fill
missing or visibly truncated descriptions. No legacy-provider fallback. See
[JSearch setup](docs/JSEARCH_SETUP.md) for subscription, local key configuration and a one-call
connection check. Live retrieval and the target-role assessment/plan path have been verified;
see [current validation status](docs/CURRENT_STATE.md) for scope and remaining limitations.
Historical adapters remain for old recordings.

**Status: Architecture frozen; V1 implementation is in progress. Activity 7B is complete.**

The AI Career Strategy & Market Navigator is a market-grounded career intelligence and career strategy agent for people at any career stage. Career stage changes the analysis, not eligibility.

It supports:

- Career exploration when the user does not yet know a target.
- Market opportunity intelligence using current market evidence and credible historical market evidence when available.
- Career transitions through direct, adjacent, and bridge roles.
- Career progression toward leadership roles with explicit scope analysis.
- Explainable recommendations, gap analysis, timeline realism, sources, uncertainty, and human approval.

The repository contains the approved V1 scope, frozen architecture, Python development foundation,
V1 domain schemas, a production-oriented Streamlit shell, structured manual profile onboarding,
provider-independent AI capability inference, deterministic career-goal confirmation,
current-market retrieval through the JSearch adapter, posting-level requirement
extraction, evidence-grounded candidate comparison, gap/accessibility analysis, observed-market
bridge/timeline assessment, draft career-plan generation, and checkpoint-scoped final human review.
The LangGraph workflow pauses on the exact draft plan ID/version, then supports approval, draft,
rejection, cancellation, or dependency-aware revision outcomes. The separate demo uses an explicitly
fictional persona. Business database persistence has not been implemented. Major architecture-
boundary changes require an ADR and explicit review.

## Local setup

Python 3.11 or later and [uv](https://docs.astral.sh/uv/) are required. From the repository root:

```powershell
uv sync --dev
.\.venv\Scripts\Activate.ps1
python --version
python -c "import ai_career_navigator"
pytest
ruff check .
```

Copy `.env.example` to `.env` when local configuration is needed. Keep credentials out of source control; provider credentials are optional until their integration activities begin.

## Model Gateway configuration

Application and domain code import `ModelGateway` and `ModelRole`; they never call a provider directly. Logical roles are configured independently:

```dotenv
LLM_PROVIDER=fireworks
FIREWORKS_API_KEY=
EXTRACTION_MODEL=accounts/fireworks/models/your-extraction-model
REASONING_MODEL=accounts/fireworks/models/your-reasoning-model
VALIDATION_MODEL=
MODEL_TIMEOUT_SECONDS=60
MAX_RETRIES=2
```

The deterministic fake provider is used by tests. NVIDIA NIM and Hugging Face remain future adapters. To make an explicitly approved live smoke call after configuring a valid Fireworks key and models, run:

```powershell
python scripts\smoke_test_model_gateway.py
```

The smoke command is never run automatically and never prints the API key.

To manually exercise the complete structured capability-inference path with the configured
Fireworks provider, run:

```powershell
python scripts\smoke_test_capability_inference.py
```

This command is also opt-in and is never invoked by the application test suite.

## Historical You.com MCP configuration (inactive on the JSearch route)

For the current app use [JSearch setup](docs/JSEARCH_SETUP.md). The section below describes
the retained legacy integration, not a required account or fallback.

Activity 5A uses the official Python MCP SDK with the hosted Streamable HTTP endpoint. The
adapter exposes only `you-search` and `you-contents` and reads its credential through `Settings`:

```dotenv
YDC_API_KEY=
YOU_MCP_URL=https://api.you.com/mcp
MARKET_TIMEOUT_SECONDS=30
MARKET_MAX_SEARCH_QUERIES=3
MARKET_MAX_EXPANSION_QUERIES=3
MARKET_MAX_CONTENT_FETCHES=30
MARKET_TARGET_POSTING_COUNT=20
MARKET_ANALYSIS_POSTING_LIMIT=5
MARKET_EXPANSION_THRESHOLD=8
```

Automated tests use `FakeMarketSearchClient` and never call You.com. After explicit approval,
one small live adapter check can be run manually with:

```powershell
python scripts\smoke_test_you_market.py
```

Add `--fetch-first` to retrieve one result page while still printing metadata only.

## LangGraph workflow foundation

Activity 5C provides `CareerWorkflowController` for starting, resuming, and inspecting the
workflow. Automated graph tests use `FakeModelProvider`, `FakeMarketSearchClient`, and LangGraph's
in-memory checkpointer:

```powershell
pytest tests\orchestration
```

The graph accepts confirmed profile and goal objects, pauses for unresolved capability inference
review, and continues through market processing, comparison, gap/accessibility analysis, bridge
evaluation, timeline assessment, and draft planning to `CAREER_PLAN_READY`. Checkpoints contain
workflow state only; raw market pages are held in an injected process-local buffer and business
persistence is not created.

## Run the UI

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run src\ai_career_navigator\app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`. Choose **Build my career profile** for structured manual onboarding or **Explore demo** for the clearly labelled fictional profile. After profile and optional capability review, the Goal step supports current-role discovery, named transitions, target paths, leadership progression, open exploration, and reassessment. The production Market page remains a synthetic shell in 5A; the live retrieval boundary is exercised through services and the optional smoke command. Profile, inference, and goal decisions remain temporary session state, and the application does not create a database.

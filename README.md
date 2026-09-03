# AI Career Strategy & Market Navigator

**Status: Architecture frozen; V1 implementation is in progress. Activity 3A is complete.**

The AI Career Strategy & Market Navigator is a market-grounded career intelligence and career strategy agent for people at any career stage. Career stage changes the analysis, not eligibility.

It supports:

- Career exploration when the user does not yet know a target.
- Market opportunity intelligence using current market evidence and credible historical market evidence when available.
- Career transitions through direct, adjacent, and bridge roles.
- Career progression toward leadership roles with explicit scope analysis.
- Explainable recommendations, gap analysis, timeline realism, sources, uncertainty, and human approval.

The repository contains the approved V1 scope, frozen architecture, Python development environment definition, environment-backed settings, standard logging foundation, and production UI design foundation. External integrations, databases, workflow logic, domain models, and functional UI pages have not been implemented. Major architecture-boundary changes require an ADR and explicit review.

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

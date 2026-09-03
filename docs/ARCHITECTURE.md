# Provisional Architecture Overview

**Status: Consolidated in `ARCHITECTURE_BASELINE.md`.** This document remains a concise overview; the baseline is the frozen MVP architecture.

- Python 3.11 or later with a Streamlit user interface.
- LangGraph for orchestration and LangChain integrations where useful.
- Pydantic models for structured data and validation.
- A provider-independent adapter for hosted LLM APIs, with candidate providers including Fireworks or NVIDIA for Nemotron.
- You.com search and content retrieval through MCP.
- A custom Career Data MCP server is excluded from the MVP; it may be reconsidered for independent deployment or multiple consumers.
- Business logic separated from MCP transport.
- SQLite as the authoritative store for structured records.
- mem0 for relevant cross-session user memory.
- pytest for tests and Ruff for formatting and linting.

Deterministic work should remain in Python. LLMs should be used only for interpretation or judgment. Credentials must come from configuration and never be hard-coded. Confirmed user facts, inferred skills, market evidence, and model interpretation must remain distinct.

The parent workflow is documented in [`LANGGRAPH_WORKFLOW.md`](LANGGRAPH_WORKFLOW.md). It defines major stages and workflow-level branches only; individual nodes and graph state are deferred.

Activity 2C data-ownership and graph-state design is documented in [`GRAPH_STATE.md`](GRAPH_STATE.md) and [`DATA_OWNERSHIP.md`](DATA_OWNERSHIP.md). These documents are conceptual; implementation schemas and persistence are deferred.

Activity 2D's conceptual domain model is documented in [`DATA_MODEL.md`](DATA_MODEL.md). It separates confirmed facts, retained evidence, derived analysis, plans, and workflow/audit records; implementation schemas remain deferred.

Activity 2E's MCP and provider boundaries are documented in [`MCP_BOUNDARIES.md`](MCP_BOUNDARIES.md) and [`PROVIDER_STRATEGY.md`](PROVIDER_STRATEGY.md). You.com MCP is the sole justified MVP MCP boundary; internal persistence uses repository interfaces and SQLite, and hosted models are accessed through the Model Gateway.

Activity 2F's reliability, security, confidence, and observability design is documented in [`ERROR_HANDLING.md`](ERROR_HANDLING.md), [`SECURITY_AND_PRIVACY.md`](SECURITY_AND_PRIVACY.md), [`CONFIDENCE_MODEL.md`](CONFIDENCE_MODEL.md), and [`OBSERVABILITY.md`](OBSERVABILITY.md).

The approved wording is used consistently: “current market evidence and credible historical market evidence when available.”

The frozen MVP baseline is documented in [`ARCHITECTURE_BASELINE.md`](ARCHITECTURE_BASELINE.md).

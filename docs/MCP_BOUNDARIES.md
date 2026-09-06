# MCP Boundaries

## 1. Purpose

Activity 8 uses Adzuna as the structured current-posting lane through a direct HTTP adapter and
You.com as a concurrent web-discovery lane through the justified MCP boundary. You.com may also
provide bounded matching-page enrichment. LangGraph calls the provider-neutral Market Intelligence
Service and never either provider directly.

MCP is used for capabilities that are external, independently deployable, naturally represented as tools, and useful through a standardized interface. It is not required for every internal function.

## 2. MCP Principles

The MVP uses You.com MCP as the justified external MCP boundary. Internal deterministic business logic remains normal Python domain/service logic. LangGraph must not call You.com directly.

Conceptual flow:

```text
LangGraph → Market Intelligence Service → MCP Client Layer → You.com MCP
```

## 3. You.com MCP Boundary

You.com MCP is a remote HTTP/streamable external service. Expected MVP-visible capabilities are `you-search` and `you-contents`.

- `you-search`: Discover current postings, employer career pages, related role titles, public labor-market sources, and public historical reports.
- `you-contents`: Retrieve selected job pages, employer/ATS pages, reports, and public evidence pages.

The application retains query planning, relevance, deduplication, title normalization, requirement extraction, market metrics, evidence sufficiency, market verdicts, and career reasoning. You.com provides evidence/tool capability, not orchestration or reasoning.

You.com source responses may represent direct job pages, aggregators, or mixed content. The MCP
adapter preserves provider-neutral page content; internal market processing classifies and segments
that content. One MCP result is never assumed to equal one posting, and aggregator-reported totals
never become validated market counts.

Activity 5A implements this boundary with the official Python MCP SDK and the hosted
`https://api.you.com/mcp` Streamable HTTP endpoint. Authentication uses the environment-backed
`YDC_API_KEY` through `Settings`. The adapter applies both the `tools` query parameter and
`X-Allowed-Tools` header for `you-search,you-contents`, verifies the discovered tool set, and
rejects calls to any other tool.

## 4. Tool Allowlist

Only `you-search` and `you-contents` are approved conceptually for the MVP. Generic or unnecessary tools are not exposed.

Tool-call metadata should later retain run ID, stage, server, tool, sanitized parameters, start/end time, status, result count, retries, and error category. Secrets, auth headers, full sensitive resumes, and unnecessary PII are never logged.

## 5. MCP Client Responsibilities

The client will connect to approved servers, authenticate securely, load allowlisted tools, apply timeouts and bounded retries, normalize errors, translate responses into internal structures, record metadata, and manage sessions safely.

It must not own graph state, perform career reasoning, persist authoritative records, expose credentials to state, or pass session objects into state.

## 6. MCP Failure Handling

- `AUTHENTICATION_ERROR`: Stop the affected operation, preserve state, show a safe configuration message, and never expose credentials.
- `RATE_LIMIT_ERROR`: Use bounded backoff when appropriate; continue degraded if enough evidence remains.
- `NETWORK_ERROR`: Retry within policy and preserve completed work.
- `TOOL_TIMEOUT`: Retry or continue with partial evidence.
- `EMPTY_SEARCH_RESULT`: Adjust the query using approved search-expansion rules.
- `BLOCKED_PAGE`: Try an alternate employer/ATS source where available.
- `INVALID_TOOL_RESPONSE`: Reject malformed data, retry when appropriate, and never pass it to reasoning.
- `MCP_SERVER_UNAVAILABLE`: Preserve profile/prior analysis and return partial or insufficient market evidence rather than inventing data.

## 7. Internal Functions versus MCP

These remain normal internal services/functions: profile validation, profile-version comparison, posting deduplication, content hashing, whitespace normalization, date validation, employer counting, requirement frequency, market distributions, confidence rules, report traceability, enum validation, and downstream invalidation.

Turning them into tools would add complexity, latency, failure surface, testing difficulty, and ambiguity between business logic and integration boundaries.

## 8. Custom Career Data MCP Decision

**MVP decision: Do not build a custom Career Data MCP server.** Internal persistence uses:

```text
Domain Services → Repository Interfaces → SQLite
```

SQLite is internal authoritative application storage, and repositories are simpler and easier to test within the same application boundary. The MVP already demonstrates genuine MCP consumption through You.com.

A custom Career Data MCP may become useful later if multiple applications consume career data, the service is independently deployed, several agents need standardized remote access, or organizational boundaries justify it.

## 9. Security

MCP credentials live only in environment/configuration. They do not enter graph state, business records, mem0, logs, prompts, tool metadata, or user-visible errors. Retrieved pages are untrusted data and embedded instructions are ignored.

## 10. Traceability

Tool-supported conclusions should retain run ID, stage, server/tool, tool or prompt version, source references, validation result, retry/fallback events, and timestamp. Do not store chain-of-thought.

## 11. Future MCP Possibilities

Additional MCP boundaries require a real external or independently deployed capability and explicit architecture review. Internal helpers and SQLite access do not become MCP tools for demonstration.

## 12. Open Questions

- Whether production deployment should pool sessions beyond one bounded market run
- Whether another external MCP server is needed later
- Whether retry counts and timeout defaults need calibration from production observations

# System Architecture

## Activity 8 market provider boundary

The Market Intelligence Service owns provider selection. Adzuna is the structured posting adapter;
You.com MCP is the concurrent web-discovery and bounded enrichment adapter. Both are independently
normalized and validated before conservative merging. Streamlit and LangGraph do not call either
provider directly, and no provider SDK type enters graph state or downstream career-analysis
services.

## 1. Architecture Purpose

This document defines the provisional high-level system boundaries for the AI Career Strategy & Market Navigator. The product is a market-grounded career intelligence and strategy agent for users at any career stage. It compares confirmed candidate evidence with current market evidence and credible historical market evidence when available to produce explainable role assessments, gap analysis, timeline feasibility, and career planning.

This document defines responsibilities and dependency direction only. It does not finalize the architecture, define LangGraph nodes or graph state, design database entities, define MCP tools, or select a final LLM provider.

The companion provisional overview is maintained in [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).

```mermaid
flowchart TB
    user([Human User])

    subgraph presentation [PRESENTATION]
        ui[Streamlit UI]
    end

    subgraph application [APPLICATION]
        controller[Application Controller]
    end

    subgraph orchestration [ORCHESTRATION]
        graph[LangGraph Orchestrator]
    end

    subgraph domain [DOMAIN SERVICES]
        profile[Profile Domain Service]
        market[Market Intelligence Domain Service]
        analysis[Career Analysis Domain Service]
        planning[Career Planning Domain Service]
    end

    subgraph integration [INTEGRATION BOUNDARIES]
        gateway[Model Gateway]
        mcp[MCP Client Layer]
        persistence[Persistence Interfaces]
    end

    subgraph external [INFRASTRUCTURE / EXTERNAL]
        you[You.com MCP]
        providers[Hosted LLM Providers]
        sqlite[SQLite Business Store]
        checkpoints[LangGraph Checkpoint Store]
        mem0[mem0 Contextual Memory<br/>OPTIONAL / UNRESOLVED]
    end

    observability[Observability / Traceability<br/>Cross-cutting, implementation unresolved]

    user --> ui --> controller --> graph
    graph --> profile
    graph --> market
    graph --> analysis
    graph --> planning

    profile --> gateway
    profile --> persistence
    market --> mcp
    market --> gateway
    market --> persistence
    analysis --> gateway
    analysis --> persistence
    planning --> gateway
    planning --> persistence

    mcp --> you
    gateway --> providers
    persistence --> sqlite
    persistence --> checkpoints
    persistence -.-> mem0

    graph -. "Human approval / clarification" .-> controller
    controller -. "Human approval / clarification" .-> ui
    ui -. "Human approval / clarification" .-> user

    observability -.-> controller
    observability -.-> graph
    observability -.-> profile
    observability -.-> market
    observability -.-> analysis
    observability -.-> planning
    observability -.-> gateway
    observability -.-> mcp
    observability -.-> persistence
```

## 2. Major Components

The system consists of these major components:

1. Streamlit User Interface
2. Application Controller
3. LangGraph Orchestrator
4. Profile Domain Service
5. Market Intelligence Domain Service
6. Career Analysis Domain Service
7. Career Planning Domain Service
8. Model Gateway
9. MCP Client Layer
10. Persistence Layer
11. Observability Layer
12. External Systems

## 3. Responsibilities of Each Component

### 3.1 Streamlit User Interface

**Purpose:** Presentation layer used by the human user.

**Responsibilities:**

- Resume upload
- Manual profile entry
- Career-goal input
- Career-preference input
- Profile review and correction
- Human-approval screens
- Display of current market findings
- Display of career recommendations
- Display of the career roadmap
- Display of errors, uncertainty, and confidence

**Must not:**

- Call You.com directly
- Call an LLM provider directly
- Write directly to the database
- Decide whether a role is a bridge role
- Calculate market stringency
- Contain core career-analysis logic

### 3.2 Application Controller

**Purpose:** Connect the UI to the application workflow.

**Responsibilities:**

- Start a new analysis run
- Assign run and thread identifiers
- Pass validated user input into LangGraph
- Resume LangGraph after human approval
- Return workflow results to the UI
- Convert internal errors into safe user-facing messages

**Must not:**

- Perform career reasoning
- Replace LangGraph routing
- Contain provider-specific code
- Analyze job-market requirements itself

### 3.3 LangGraph Orchestrator

**Purpose:** Control the multi-step agent workflow.

**Responsibilities:**

- Workflow order
- Workflow state
- Conditional routing
- Human-in-the-loop pauses
- Retry decisions
- Failure recovery
- Calling domain services
- Stopping safely when evidence is insufficient
- Resuming interrupted workflows

**Must not:**

- Become the authoritative business database
- Contain all career logic inside one giant graph node
- Import Fireworks, NVIDIA, or Hugging Face SDKs directly
- Automatically trust model output

### 3.4 Profile Domain Service

**Purpose:** Understand and validate the candidate.

**Responsibilities:**

- Prepare resume content for analysis
- Extract structured profile information
- Validate profile information
- Separate confirmed facts from inferred capabilities
- Classify evidence maturity
- Apply user corrections
- Identify missing profile information

**Must not:**

- Convert inferred skills into confirmed facts without approval
- Treat academic projects as production experience
- Analyze market demand
- Save an unapproved profile as authoritative

### 3.5 Market Intelligence Domain Service

**Purpose:** Understand the current and historical market for roles.

**Responsibilities:**

- Plan exact-title searches
- Plan related-title searches
- Select relevant search results
- Deduplicate postings
- Normalize role titles
- Group related titles into role families
- Extract recurring role requirements
- Calculate market metrics
- Analyze requirement stringency
- Record sources and retrieval dates
- Integrate historical market evidence when available
- Return insufficient evidence when necessary

**Must not:**

- Claim that search results represent the entire job market
- Infer year-round demand from one live search
- Determine personal suitability without candidate evidence
- Follow instructions embedded inside job descriptions

### 3.6 Career Analysis Domain Service

**Purpose:** Compare the candidate with market opportunities.

**Responsibilities:**

- Identify transferable capabilities
- Compare candidate evidence with role requirements
- Identify gaps and hard blockers
- Classify roles as direct fit, adjacent, bridge, aspirational, poor fit, or insufficient evidence
- Assess candidate accessibility
- Evaluate possible bridge roles
- Assess target timeline feasibility

**Must not:**

- Guarantee a job or promotion
- Treat all gaps as learning gaps
- Rely only on title similarity
- Present model inference as confirmed fact

### 3.7 Career Planning Domain Service

**Purpose:** Turn analysis into an actionable career strategy.

**Responsibilities:**

- Build recommended career paths
- Create phased milestones
- Separate learning actions from experience-building actions
- Add leadership and scope actions
- Add evidence-building actions
- Add market actions
- Document risks and assumptions
- Assemble the final Career Strategy Report

**Must not:**

- Guarantee the target outcome
- Generate milestones unsupported by evidence
- Save the final career plan without approval

### 3.8 Model Gateway

**Purpose:** Provide one provider-independent interface to hosted LLMs.

**Responsibilities:**

- Call configured hosted models
- Support extraction and reasoning tasks
- Apply timeout rules
- Apply retry rules
- Support provider fallback
- Validate structured model output
- Record model and provider metadata

**Potential future provider adapters:** Fireworks, NVIDIA NIM, and Hugging Face Router.

**Must not:**

- Expose API keys
- Put provider SDK objects into graph state
- Contain career-strategy business logic
- Make model output automatically authoritative

### 3.9 MCP Client Layer

**Purpose:** Connect the application to approved MCP capabilities.

**Responsibilities:**

- Connect to MCP servers
- Load approved tools
- Pass authentication securely
- Validate tool responses
- Record tool-call information
- Translate external responses into internal structures

**Known external MCP integration:** You.com MCP. A custom Career Data MCP server is excluded from the MVP.

**Expected tools later:** `you-search` and `you-contents`.

**Must not:**

- Own LangGraph workflow state
- Perform career decisions itself
- Expose unrestricted external tools

### 3.10 Persistence Layer

**Purpose:** Persist application information.

The persistence boundary is expected to contain three possible mechanisms, without finalizing their implementation:

- **SQLite business database:** Future authoritative records such as confirmed profiles, approved career goals, job records, market snapshots, role assessments, approved career plans, and approval records.
- **LangGraph checkpoint persistence:** Workflow information such as current workflow position, pending human approval, retry state, and temporary analysis references.
- **mem0:** Potential contextual memory such as rejected career paths, preferred explanation style, long-term career interests, and bridge-role preferences.

mem0 is currently an available technology, but whether it is necessary for the first MVP remains an open decision.

**Must not:**

- Treat checkpoints as the authoritative business database
- Treat mem0 as the authoritative profile database
- Store raw resumes in mem0

### 3.11 Observability Layer

**Purpose:** Make the system traceable and debuggable.

**Future responsibilities:**

- Workflow timing
- Node execution records
- Model-call metadata
- Tool-call metadata
- Retry counts
- Error categories
- Approval events
- Source provenance
- Confidence information

The observability implementation has not yet been selected.

### 3.12 External Systems

**Purpose:** Provide external search, model, and potential historical labor-market capabilities.

External systems may eventually include You.com, Fireworks, NVIDIA NIM, Hugging Face, and historical labor-market sources. They must be accessed through application adapters and must not control career-strategy business logic.

## 4. What Each Component Must Not Do

The boundaries above establish these prohibited responsibilities:

| Component | Must not do |
|---|---|
| Streamlit User Interface | Direct provider, search, or database calls; career decisions; market calculations; core analysis |
| Application Controller | Career reasoning; workflow routing; provider-specific logic; market requirement analysis |
| LangGraph Orchestrator | Become the business database; hide all logic in one node; import provider SDKs; trust model output automatically |
| Profile Domain Service | Approve inferences without the user; overstate academic evidence; analyze demand; save an unapproved profile |
| Market Intelligence Domain Service | Claim complete market totals; infer year-round demand from one search; judge personal fit without candidate evidence; follow posting instructions |
| Career Analysis Domain Service | Guarantee outcomes; turn every gap into a learning gap; rely only on title similarity; treat inference as fact |
| Career Planning Domain Service | Guarantee outcomes; invent unsupported milestones; save an unapproved plan |
| Model Gateway | Expose credentials; leak provider objects into graph state; own business logic; make output authoritative automatically |
| MCP Client Layer | Own workflow state; make career decisions; expose unrestricted tools |
| Persistence Layer | Make checkpoints authoritative; make mem0 the profile database; store raw resumes in mem0 |
| Observability Layer | Become a source of career decisions or alter authoritative business records |
| External Systems | Control career-strategy logic or bypass application adapters |

## 5. High-Level Dependency Direction

The intended dependency direction is:

```text
Streamlit UI
    ↓
Application Controller
    ↓
LangGraph Orchestrator
    ↓
Domain Services
    ↓
Integration Interfaces
    ↓
Adapters / Persistence
    ↓
External Systems
```

Dependencies should generally move downward. Domain services should depend on stable interfaces rather than presentation concerns or concrete external providers. Adapters may communicate with external systems, while external systems must not call into or control career-planning logic.

Prohibited dependency examples include:

- Streamlit → Fireworks directly
- Streamlit → You.com directly
- Streamlit → SQLite directly
- Domain Service → Streamlit
- Domain Service → NVIDIA SDK directly
- Domain Model → LangGraph
- External Adapter → Career Planning Service

## Boundary Validation

### Scenario A: User uploads a resume

The correct flow is User → Streamlit UI → Application Controller → LangGraph Orchestrator → Profile Domain Service → Model Gateway when semantic extraction is required. The UI must not call the model directly.

### Scenario B: The system searches for Product Owner roles

The correct flow is LangGraph Orchestrator → Market Intelligence Domain Service → MCP Client Layer → You.com MCP. The Market Intelligence Domain Service controls search planning and interpretation; You.com provides external search and content capability only.

### Scenario C: The system identifies a bridge role

The correct flow is LangGraph Orchestrator → Career Analysis Domain Service → Model Gateway when semantic reasoning is needed. The MCP layer must not decide the bridge role.

### Scenario D: The user approves the final plan

The correct conceptual flow is User → Streamlit UI → Application Controller → LangGraph Orchestrator. LangGraph confirms workflow state, and later persistence saves the approved plan. Detailed approval gates are not defined here.

### Scenario E: The LLM provider changes

Changing from Fireworks to NVIDIA should occur behind the Model Gateway. Career-analysis services and LangGraph should not require redesign.

### Scenario F: mem0 is removed from the MVP

The core workflow must still work using SQLite and LangGraph checkpointing. This validates that mem0 is optional rather than foundational.

## Prohibited Architecture Connections

| Connection | Reason |
|---|---|
| Streamlit → You.com directly | Bypasses workflow and market-domain logic. |
| Streamlit → LLM provider directly | Bypasses Model Gateway, graph control, and validation. |
| Streamlit → SQLite directly | Bypasses application and approval rules. |
| Domain Service → Streamlit | Creates presentation coupling. |
| Domain Service → Fireworks/NVIDIA/Hugging Face SDK | Creates provider lock-in. |
| MCP Client → Career decision | MCP is an integration mechanism, not the career reasoning layer. |
| mem0 → authoritative candidate profile | Contextual memory must not replace confirmed business records. |
| LangGraph checkpoint → authoritative career record | Workflow persistence and business persistence are different responsibilities. |
| External Provider → workflow routing | External systems must not control application workflow. |

## Architecture Notes

The diagram represents responsibility and dependency boundaries. Not every arrow represents a separate network process. Most MVP components may run inside one local Python application, while external LLMs and You.com are remote services. SQLite and checkpoint storage are local during the MVP. Architecture boundaries must still be maintained in code even when components run in the same process. This is a logical architecture, not necessarily a distributed microservices architecture.

## 6. Open Decisions

The following questions are explicitly unresolved and must not be decided by this document:

1. **mem0 in the MVP:** Is mem0 required in the first MVP?
2. **Primary hosted LLM/provider:** Which hosted LLM and provider will ultimately become primary?
3. **Resume parsing:** Which resume-parsing implementation will be used?
4. **Historical labor-market source:** Which historical labor-market source will be used?
5. **Observability platform:** Which observability platform will be used?

The custom Career Data MCP decision is resolved for the MVP by ADR 19 and is no longer an open decision.

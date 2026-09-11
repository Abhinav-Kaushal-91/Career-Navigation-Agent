"""Career Navigator graph construction without module-level providers."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .context import WorkflowRuntimeContext
from .nodes import (
    apply_revision_request,
    bridge_role_assessment,
    candidate_requirement_comparison,
    capability_inference,
    capability_inference_review,
    career_assessment_synthesis,
    career_plan_generation,
    final_plan_review,
    finalize_workflow,
    gap_and_accessibility_analysis,
    goal_ready,
    initialize_run,
    market_processing,
    market_ready,
    market_retrieval,
    profile_ready,
    timeline_assessment,
)
from .routing import (
    route_after_candidate_assessment,
    route_after_candidate_comparison,
    route_after_goal,
    route_after_inference,
    route_after_market_processing,
    route_after_market_ready,
    route_after_market_retrieval,
    route_after_plan_review,
    route_after_profile,
    route_after_review,
)
from .state import CareerGraphState


def build_career_graph(*, checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Compile the graph through final review with workflow-only checkpoint persistence."""

    builder = StateGraph(CareerGraphState, context_schema=WorkflowRuntimeContext)
    builder.add_node("initialize_run", initialize_run)
    builder.add_node("profile_ready", profile_ready)
    builder.add_node("capability_inference", capability_inference)
    builder.add_node("capability_inference_review", capability_inference_review)
    builder.add_node("goal_ready", goal_ready)
    builder.add_node("market_retrieval", market_retrieval)
    builder.add_node("market_processing", market_processing)
    builder.add_node("market_ready", market_ready)
    builder.add_node("candidate_requirement_comparison", candidate_requirement_comparison)
    builder.add_node("gap_and_accessibility_analysis", gap_and_accessibility_analysis)
    builder.add_node("career_assessment_synthesis", career_assessment_synthesis)
    builder.add_node("bridge_role_assessment", bridge_role_assessment)
    builder.add_node("timeline_assessment", timeline_assessment)
    builder.add_node("career_plan_generation", career_plan_generation)
    builder.add_node("final_plan_review", final_plan_review)
    builder.add_node("finalize_workflow", finalize_workflow)
    builder.add_node("apply_revision_request", apply_revision_request)

    builder.add_edge(START, "initialize_run")
    builder.add_edge("initialize_run", "profile_ready")
    builder.add_conditional_edges(
        "profile_ready",
        route_after_profile,
        {"inference": "capability_inference", "end": END},
    )
    builder.add_conditional_edges(
        "capability_inference",
        route_after_inference,
        {"review": "capability_inference_review", "goal": "goal_ready"},
    )
    builder.add_conditional_edges(
        "capability_inference_review",
        route_after_review,
        {"goal": "goal_ready", "end": END},
    )
    builder.add_conditional_edges(
        "goal_ready",
        route_after_goal,
        {"market": "market_retrieval", "end": END},
    )
    builder.add_conditional_edges(
        "market_retrieval",
        route_after_market_retrieval,
        {"processing": "market_processing", "end": END},
    )
    builder.add_conditional_edges(
        "market_processing",
        route_after_market_processing,
        {"ready": "market_ready", "review": "final_plan_review", "end": END},
    )
    builder.add_conditional_edges(
        "market_ready",
        route_after_market_ready,
        {"comparison": "candidate_requirement_comparison", "end": END},
    )
    builder.add_conditional_edges(
        "candidate_requirement_comparison",
        route_after_candidate_comparison,
        {"gaps": "gap_and_accessibility_analysis", "end": END},
    )
    builder.add_edge("gap_and_accessibility_analysis", "career_assessment_synthesis")
    builder.add_conditional_edges(
        "career_assessment_synthesis",
        route_after_candidate_assessment,
        {"bridge": "bridge_role_assessment", "timeline": "timeline_assessment"},
    )
    builder.add_edge("bridge_role_assessment", "timeline_assessment")
    builder.add_edge("timeline_assessment", "career_plan_generation")
    builder.add_edge("career_plan_generation", "final_plan_review")
    builder.add_conditional_edges(
        "final_plan_review",
        route_after_plan_review,
        {
            "finalize": "finalize_workflow",
            "revision": "apply_revision_request",
            "end": END,
        },
    )
    builder.add_edge("finalize_workflow", END)
    builder.add_edge("apply_revision_request", END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())

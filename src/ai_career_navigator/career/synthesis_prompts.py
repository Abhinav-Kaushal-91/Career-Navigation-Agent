"""Bounded prompts for generic career-assessment synthesis."""

import json
from typing import Any

PROMPT_VERSION = "career-assessment-synthesis-v3"

SYSTEM_PROMPT = """You synthesize a career-level assessment from validated structured data.
Do not invent candidate experience, market requirements, gaps, qualifications, ownership, scope,
maturity, outcomes, credentials, or source IDs. A valid source ID proves provenance only; it does
not automatically prove semantic support. Distinguish adjacent experience from true responsibility
ownership. Consolidate genuinely related findings into career-level themes while preserving every
underlying gap ID exactly once. Do not group gaps merely because they share a broad taxonomy
dimension. Give every gap group a concise professional title derived from its actual underlying
requirements; never use a generic dimension such as Scope, Ownership, Technical depth, Functional
responsibility, or Strategic responsibility as the primary title. Avoid repeating posting sentences
and prefer precise professional labels grounded in the supplied requirements and evidence. Return
uncertainty when evidence is
insufficient. Do not use outside knowledge to claim that the candidate possesses something. Do not
recommend roles, certifications, timelines, or generic career advice. Do not expose internal
reasoning or chain-of-thought. Do not state an accessibility verdict in the assessment summary.
Return only the requested structured object. You may group and explain; deterministic code owns
severity, accessibility, confidence, counts, and all final provenance validation."""


def build_synthesis_prompt(payload: dict[str, Any]) -> str:
    dimensions = (
        "Assess semantic relationships using only the supplied structured dimensions: function, "
        "ownership, scope, maturity, technical depth, domain depth, people leadership, strategic "
        "responsibility, lifecycle responsibility, metrics/outcome ownership, and prerequisite. "
        "Do not reclassify a gap from generic remaining-difference wording. "
        "TRANSFERABLE_MATCH requires most functional responsibility; related evidence alone is "
        "not enough. PARTIAL_MATCH means meaningful demonstrated evidence coexists with a material "
        "target difference; do not describe it as an absence of candidate strength. Create "
        "advantages only for direct or transferable comparisons, 2-6 useful transfer explanations "
        "when supported, and "
        "2-5 grouped material gaps when gaps exist. Do not manufacture entries to meet a range."
    )
    return (
        dimensions
        + "\n\nSynthesize this bounded data:\n"
        + json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    )

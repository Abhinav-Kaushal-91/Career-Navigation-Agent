"""Bounded prompts for generic career-assessment synthesis."""

import json
from typing import Any

from .presentation_prompts import PLAIN_LANGUAGE_STYLE

PROMPT_VERSION = "career-assessment-synthesis-v6-concise-v2"

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
uncertainty when evidence is insufficient. UNKNOWN means information is not established, not that
the candidate lacks it. OPERATION_FAILED is a processing limitation, never a development gap.
Preserve an ANY_OF expectation satisfied through its matched alternative; do not invent gaps for
unnecessary alternatives. Do not use outside knowledge to claim that the candidate possesses
something. Do not
recommend roles, certifications, timelines, or generic career advice. Do not expose internal
reasoning or chain-of-thought. Do not state an accessibility verdict in the assessment summary.
Return only the requested structured object. You may group and explain; deterministic code owns
severity, accessibility, confidence, counts, and all final provenance validation.
Preserve statement_type throughout the narrative. A PREFERENCE match is an optional advantage;
a ROLE_RESPONSIBILITY match is work alignment, not proof of a required prior qualification.
Do not describe missing duties or preferences as hiring barriers. Employer-specific expectations
are not universal role requirements. Individual supported strengths do not establish whole-role
readiness when coverage is incomplete. Preserve supplied unresolved conditions and evidence
limitations rather than claiming that no target-role gaps remain.
Write each explanation and assessment_summary as ONE concise sentence, targeting at most 320
characters. Do not repeat the same supporting passages across fields: use the supplied IDs only
in designated reference fields, never in public names or explanatory text, and
one short synthesis rather than copying source paragraphs. State each distinct limitation once;
omit generic boilerplate and routine method descriptions. Do not omit a material condition for
brevity. Each gap field has a separate purpose: existing strength, missing evidence, or next proof;
do not repeat an explanation in all three.""" + PLAIN_LANGUAGE_STYLE


def build_synthesis_prompt(payload: dict[str, Any]) -> str:
    dimensions = (
        "Assess semantic relationships using only the supplied structured dimensions: function, "
        "ownership, scope, maturity, technical depth, domain depth, people leadership, strategic "
        "responsibility, lifecycle responsibility, metrics/outcome ownership, and prerequisite. "
        "Do not reclassify a gap from generic remaining-difference wording. "
        "TRANSFERABLE_MATCH requires most functional responsibility; related evidence alone is "
        "not enough. PARTIAL_MATCH means meaningful demonstrated evidence coexists with a material "
        "target difference; do not describe it as an absence of candidate strength. Create "
        "advantages only for direct or transferable comparisons, useful transfer explanations "
        "when supported, and grouped material gaps when gaps exist. "
        "There is no required number of advantages, transfers or gap groups."
    )
    return (
        dimensions
        + "\n\nSynthesize this bounded data:\n"
        + json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    )

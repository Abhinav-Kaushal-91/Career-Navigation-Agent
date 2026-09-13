"""Deterministic groundedness/faithfulness/citation-accuracy checks.

Two layers of the pipeline make claims that must trace back to real source
material, and both can be checked without an LLM judge:

1. Requirement extraction (`ai_career_navigator.market.requirements`) quotes the
   posting text directly (`ExtractedRequirement.source_quote`). Faithfulness here
   is exactly "is this quote actually in the posting, and does the capability
   label overstate what the quote supports" -- a literal substring/token check.
2. Career synthesis (`ai_career_navigator.career.synthesis_schemas`) does not
   quote text; it cites evidence/comparison/gap IDs. Faithfulness there reduces
   to "do the cited IDs resolve to real objects the candidate/analysis actually
   produced" -- a citation-accuracy check per the field guide's definition
   ("checks whether cited sources support the exact claims").

Neither needs a semantic judge, which keeps this suite deterministic-first, the
same policy the golden-answer eval loop documents.
"""

import re
import unicodedata
from collections.abc import Iterable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ai_career_navigator.career.synthesis_schemas import CareerSynthesisDraft
from ai_career_navigator.market.role_profile import quote_capability_alignment

from .metrics import PrecisionRecallF1, classification_metrics


def _grounding_tokens(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9+#]+", normalized))


def _quote_in_text(quote: str, text: str) -> bool:
    normalized_quote = _grounding_tokens(quote)
    return bool(normalized_quote) and normalized_quote in _grounding_tokens(text)


class GroundingGoldCase(BaseModel):
    """One (source quote, capability label, posting text) faithfulness judgment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(min_length=1)
    posting_text: str = Field(min_length=1)
    source_quote: str = Field(min_length=1)
    normalized_capability: str = Field(min_length=1)
    expected_grounded: bool
    note: str = Field(default="", max_length=300)


def is_grounded(case: GroundingGoldCase) -> bool:
    """Grounded only if the quote is real and the label doesn't overstate what it says."""

    quote_present = _quote_in_text(case.source_quote, case.posting_text)
    capability_supported, _ = quote_capability_alignment(
        case.source_quote, case.normalized_capability
    )
    return quote_present and capability_supported


def evaluate_quote_grounding(cases: list[GroundingGoldCase]) -> PrecisionRecallF1:
    predictions = [is_grounded(case) for case in cases]
    labels = [case.expected_grounded for case in cases]
    return classification_metrics(predictions, labels)


class CitationAccuracy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_citations: int = Field(ge=0)
    valid_citations: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)


def _count_valid(cited: Iterable[UUID], known: set[UUID]) -> tuple[int, int]:
    cited_ids = list(cited)
    return sum(1 for item in cited_ids if item in known), len(cited_ids)


def synthesis_citation_accuracy(
    draft: CareerSynthesisDraft,
    *,
    known_evidence_ids: set[UUID],
    known_comparison_ids: set[UUID],
    known_gap_ids: set[UUID],
) -> CitationAccuracy:
    """Fraction of cited evidence/comparison/gap IDs in a draft that resolve to real objects.

    A citation to an ID nothing in the profile/analysis produced is a hallucinated
    reference; catching that here is cheaper and more reliable than asking a judge
    to spot it in prose.
    """

    valid = total = 0
    for advantage in draft.strongest_advantages:
        v, t = _count_valid(advantage.supporting_evidence_ids, known_evidence_ids)
        valid, total = valid + v, total + t
        v, t = _count_valid(advantage.supporting_comparison_ids, known_comparison_ids)
        valid, total = valid + v, total + t
    for strength in draft.transferable_strengths:
        v, t = _count_valid(strength.supporting_evidence_ids, known_evidence_ids)
        valid, total = valid + v, total + t
        v, t = _count_valid(strength.supporting_comparison_ids, known_comparison_ids)
        valid, total = valid + v, total + t
    for gap in draft.grouped_gaps:
        v, t = _count_valid(gap.underlying_gap_ids, known_gap_ids)
        valid, total = valid + v, total + t
    return CitationAccuracy(
        total_citations=total,
        valid_citations=valid,
        accuracy=(valid / total if total else 1.0),
    )

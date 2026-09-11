"""Date-derived employment tenure, separate from claimed capability proficiency."""

from collections.abc import Iterable
from datetime import UTC, date, datetime

from ai_career_navigator.domain import EvidenceConfirmationStatus, EvidenceItem


def _merged_days(intervals: list[tuple[date, date]]) -> int:
    """Elapsed days in the union of half-open intervals; never count overlaps twice."""
    merged: list[tuple[date, date]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return sum((end - start).days for start, end in merged)


def calculate_professional_experience(
    evidence: Iterable[EvidenceItem], *, as_of: date | None = None
) -> dict:
    """Count explicitly confirmed employment dates, not summary/skill claims.

    The union is a lower bound when dates are incomplete. Individual role tenures
    do not establish how long every technology was used. Inferred employment,
    portfolio projects, education and certifications cannot add career years.
    """
    today = as_of or datetime.now(UTC).date()
    intervals = []
    rows = []
    groups: dict[str, dict] = {}
    unresolved = []
    for item in evidence:
        if (
            item.evidence_type.casefold() != "employment"
            or not item.approved_by_user
            or item.confirmation_status is not EvidenceConfirmationStatus.EXPLICIT
        ):
            continue
        start, end = item.start_date, item.end_date
        reason = None
        if not start:
            reason = "Employment start date is missing."
        elif start > today:
            reason = "Employment starts after the analysis date."
        elif item.is_current is True and end is not None:
            reason = "Current employment also has an end date; clarify which is correct."
        elif end is None and item.is_current is not True:
            reason = "Confirm the end date or explicitly mark this role as current."
        elif end is not None and end < start:
            reason = "Employment end date precedes its start."
        if reason:
            unresolved.append({"evidence_id": str(item.evidence_id), "question": reason})
            continue
        effective_end = today if item.is_current else min(end, today)
        interval = (start, effective_end)
        intervals.append(interval)
        days = (effective_end - start).days
        rows.append(
            {
                "evidence_id": str(item.evidence_id),
                "role": item.capability,
                "start_date": start.isoformat(),
                "effective_end_date": effective_end.isoformat(),
                "elapsed_days": days,
                "approximate_years": round(days / 365.2425, 2),
                "technology_specific_years": None,
            }
        )
        key = " ".join(item.capability.casefold().split())
        group = groups.setdefault(key, {"role": item.capability, "intervals": [], "ids": []})
        group["intervals"].append(interval)
        group["ids"].append(str(item.evidence_id))
    total = _merged_days(intervals)
    return {
        "analysis_date": today.isoformat(),
        "dated_employment_days": total if intervals else None,
        "approximate_professional_years": round(total / 365.2425, 2) if intervals else None,
        "coverage": "PARTIAL" if unresolved else "DATED_RECORDS_ONLY" if rows else "UNAVAILABLE",
        "overlap_days_removed": sum((end - start).days for start, end in intervals) - total,
        "employment_periods": rows,
        "role_tenures": [
            {
                "role": group["role"],
                "evidence_ids": group["ids"],
                "elapsed_days": _merged_days(group["intervals"]),
                "approximate_years": round(_merged_days(group["intervals"]) / 365.2425, 2),
            }
            for group in groups.values()
        ],
        "unresolved_dates": unresolved,
        "interpretation": (
            "Elapsed employment time from supplied dates, overlapping periods counted once. "
            "Role tenure is relevant only when duties demonstrate the required work; "
            "it does not prove each technology was used throughout that period. "
            "Unlisted employment is not assumed absent; incomplete dates give a lower bound. "
            "Rounded years are display estimates; elapsed days are the arithmetic source."
        ),
    }

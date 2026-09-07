"""Transparent currentness policy independent of provider and system clock."""

import re
from datetime import date

from ai_career_navigator.market.schemas import MarketPageContent


def currentness_rejection(page: MarketPageContent, *, as_of: date, max_age_days: int) -> str | None:
    if re.search(r"^(?:404|page not found)\b", (page.title or "").strip(), re.I) or re.search(
        r"(?im)^#{1,3}\s+(?:404|page not found)\s*$", page.markdown
    ):
        return (
            "Requested posting page is unavailable; suggested jobs are not the requested vacancy."
        )
    if re.search(
        r"\b(?:the\s+)?(?:job|position)(?:\s+you are looking for)?\s+"
        r"(?:is\s+)?no longer (?:open|available)\b",
        page.markdown,
        re.I,
    ):
        return "Posting is explicitly closed or no longer accepting applications."
    try:
        if (
            page.posting_date
            and page.closing_date
            and date.fromisoformat(page.closing_date[:10])
            < date.fromisoformat(page.posting_date[:10])
        ):
            return "Invalid posting dates: closing date precedes posting date."
    except ValueError:
        return "Invalid posting dates: date cannot be parsed."
    status = (page.active_status or "").casefold()
    if status in {"closed", "expired", "filled", "inactive"} or re.search(
        r"\b(?:job|position|posting)(?:\s+posting)?\s+(?:is\s+|has been\s+)?"
        r"(?:closed|expired|filled)\b|\bno longer accepting applications\b",
        page.markdown,
        re.I,
    ):
        return "Posting is explicitly closed or no longer accepting applications."
    for value, label in ((page.closing_date, "closing"), (page.posting_date, "posting")):
        if not value:
            continue
        try:
            parsed = date.fromisoformat(value[:10])
        except ValueError:
            continue
        if label == "closing" and parsed < as_of:
            return "Posting closing date is before the search date."
        if label == "posting" and parsed > as_of:
            return "Posting date is in the future and requires verification."
        if label == "posting" and (as_of - parsed).days > max_age_days:
            if status != "verified_open":
                return "Posting exceeds the configured age window without verified-open evidence."
    return None

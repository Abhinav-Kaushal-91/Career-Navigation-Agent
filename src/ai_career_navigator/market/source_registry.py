"""Shared source recognition; a known host alone never proves an individual job."""

import re
from urllib.parse import parse_qs, urlsplit

ATS_DOMAINS = frozenset(
    {
        "greenhouse.io",
        "lever.co",
        "ashbyhq.com",
        "myworkdayjobs.com",
        "smartrecruiters.com",
        "workable.com",
    }
)
# Discovery is narrower than source recognition: prefer public job hosts, not ATS
# vendor marketing/blog pages. Each returned URL still needs posting validation.
ATS_JOB_SEARCH_DOMAINS = frozenset(
    {
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "jobs.lever.co",
        "jobs.ashbyhq.com",
        "myworkdayjobs.com",
        "jobs.smartrecruiters.com",
        "apply.workable.com",
    }
)
AGGREGATOR_SEARCH_DOMAINS = frozenset(
    {
        "ziprecruiter.com",
        "indeed.com",
        "glassdoor.com",
        "glassdoor.ca",
        "linkedin.com",
        "jobilize.com",
        "jooble.org",
    }
)
JOB_PATH_MARKERS = ("job", "jobs", "careers", "positions", "openings")


def is_ats_domain(domain: str | None) -> bool:
    host = (domain or "").casefold().removeprefix("www.")
    return any(host == item or host.endswith(f".{item}") for item in ATS_DOMAINS)


def looks_like_individual_job_url(url: str) -> bool:
    if is_individual_job_board_url(url):
        return True
    parts = urlsplit(url)
    segments = [part for part in parts.path.split("/") if part]
    if not segments:
        return False
    if is_ats_domain(parts.hostname):
        # ATS root/company index pages do not receive individual-vacancy status.
        return len(segments) >= 2 and segments[-1].casefold() not in {
            "jobs",
            "careers",
            "search",
            "openings",
            "positions",
        }
    return any(
        part.casefold() in JOB_PATH_MARKERS and index + 1 < len(segments)
        for index, part in enumerate(segments)
    )


def is_individual_job_board_url(url: str) -> bool:
    """Recognize vacancy identifiers, not search/category/salary-guide pages."""
    parts = urlsplit(url)
    host = (parts.hostname or "").casefold()
    query = parse_qs(parts.query)

    def on(domain: str) -> bool:
        return host == domain or host.endswith("." + domain)

    if on("linkedin.com"):
        return bool(re.search(r"/jobs/view/[^/]*\d+/?$", parts.path))
    if on("indeed.com"):
        return parts.path.rstrip("/") == "/viewjob" and bool(query.get("jk"))
    if on("glassdoor.com") or on("glassdoor.ca"):
        return "/job-listing/" in parts.path.casefold() and bool(query.get("jl"))
    if on("ziprecruiter.com"):
        return "/job/" in parts.path.casefold() and bool(query.get("jid"))
    return False

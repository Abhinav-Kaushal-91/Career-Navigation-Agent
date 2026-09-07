"""Shared source recognition; a known host alone never proves an individual job."""

from urllib.parse import urlsplit

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

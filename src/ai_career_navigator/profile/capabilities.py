"""Conservative capability cleaning and duplicate detection."""

import re
import unicodedata
from collections.abc import Iterable

_ALIASES = {
    "rest api": "rest api",
    "rest apis": "rest api",
    "rest-api": "rest api",
    "rest-apis": "rest api",
    "restful api": "rest api",
    "restful apis": "rest api",
}


def clean_capability_name(value: str) -> str:
    """Clean accidental wrappers without damaging technical punctuation."""

    cleaned = " ".join(unicodedata.normalize("NFKC", value).strip().split())
    return cleaned.strip(",;")


def capability_key(value: str) -> str:
    """Return a deliberately narrow key used only for duplicate detection."""

    cleaned = clean_capability_name(value).casefold()
    cleaned = re.sub(r"\s*/\s*", "/", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return _ALIASES.get(cleaned, cleaned)


def dedupe_capabilities(values: Iterable[str]) -> tuple[str, ...]:
    """Keep first-seen spelling and order while removing conservative aliases."""

    retained: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_capability_name(value)
        key = capability_key(cleaned)
        if not key or key in seen:
            continue
        seen.add(key)
        retained.append(cleaned)
    return tuple(retained)

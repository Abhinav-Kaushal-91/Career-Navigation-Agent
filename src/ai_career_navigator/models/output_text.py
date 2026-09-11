"""Conservative output cleanup; never summarize away distinct evidence conditions."""


def unique_statements(value):
    """Remove only case/whitespace duplicates, preserving first wording and order."""
    if not isinstance(value, list):
        return value
    result, seen = [], set()
    for item in value:
        if not isinstance(item, str):
            result.append(item)  # Let the owning schema reject invalid types.
            continue
        key = " ".join(item.split()).casefold()
        if key and key not in seen:
            result.append(item.strip())
            seen.add(key)
    return result

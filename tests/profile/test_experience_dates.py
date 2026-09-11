from datetime import UTC, date, datetime

import pytest

from ai_career_navigator.domain import EvidenceConfirmationStatus
from ai_career_navigator.profile.experience import calculate_professional_experience
from tests.career.test_comparison import evidence


def job(start, end=None, current=False, **extra):
    return evidence("Developer").model_copy(
        update={
            "evidence_type": "employment",
            "start_date": start,
            "end_date": end,
            "is_current": current,
            **extra,
        }
    )


def test_current_role_uses_analysis_date_not_saved_date():
    start, today = date(2018, 9, 1), date(2026, 9, 10)
    item = job(start, current=True, created_at=datetime(2020, 1, 1, tzinfo=UTC))
    result = calculate_professional_experience([item], as_of=today)
    assert result["dated_employment_days"] == (today - start).days
    assert result["approximate_professional_years"] == 8.02
    assert result["employment_periods"][0]["technology_specific_years"] is None
    assert result["employment_periods"][0]["effective_end_date"] == today.isoformat()


def test_overlap_duplicates_and_breaks_not_double_counted():
    first = job(date(2020, 1, 1), date(2022, 1, 1))
    overlap = job(date(2021, 1, 1), date(2023, 1, 1))
    after_break = job(date(2024, 1, 1), date(2025, 1, 1))
    result = calculate_professional_experience(
        [first, first, overlap, after_break], as_of=date(2026, 1, 1)
    )
    expected = (date(2023, 1, 1) - date(2020, 1, 1)).days + 366
    assert result["dated_employment_days"] == expected
    assert result["role_tenures"][0]["elapsed_days"] == expected
    assert result["overlap_days_removed"] > 0


@pytest.mark.parametrize(
    "extra",
    [
        {"evidence_type": "project"},
        {"evidence_type": "certification"},
        {"evidence_type": "education"},
        {"approved_by_user": False},
        {"confirmation_status": EvidenceConfirmationStatus.CONFIRMED_INFERENCE},
    ],
)
def test_non_explicit_employment_never_adds_professional_years(extra):
    result = calculate_professional_experience(
        [job(date(2020, 1, 1), current=True, **extra)], as_of=date(2026, 1, 1)
    )
    assert result["dated_employment_days"] is None


@pytest.mark.parametrize(
    ("start", "end", "current"),
    [
        (None, date(2025, 1, 1), False),
        (date(2020, 1, 1), None, False),
        (date(2020, 1, 1), None, None),
        (date(2027, 1, 1), None, True),
        (date(2020, 1, 1), date(2025, 1, 1), True),
    ],
)
def test_incomplete_dates_are_unknown_not_zero_or_assumed_current(start, end, current):
    result = calculate_professional_experience([job(start, end, current)], as_of=date(2026, 1, 1))
    assert result["dated_employment_days"] is None
    assert result["coverage"] == "PARTIAL"
    assert len(result["unresolved_dates"]) == 1


def test_partial_dates_give_lower_bound_and_future_end_is_capped():
    result = calculate_professional_experience(
        [job(date(2020, 1, 1), date(2030, 1, 1)), job(date(2010, 1, 1))], as_of=date(2021, 1, 1)
    )
    assert result["dated_employment_days"] == 366
    assert result["coverage"] == "PARTIAL"

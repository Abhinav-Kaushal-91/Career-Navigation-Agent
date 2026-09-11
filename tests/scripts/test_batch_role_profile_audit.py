import importlib
from pathlib import Path

import pytest


@pytest.fixture
def batch(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("benchmark_batch_role_profile")


def test_batch_audit_rejects_wrong_source_and_retains_distinct_counts(batch):
    records = [
        {"posting_id": "A", "employer": "Acme", "text": "Requirements: Java required."},
        {"posting_id": "B", "employer": "Acme", "text": "Requirements: Java required."},
    ]
    supports = [
        {
            "posting_id": pid,
            "quote": quote,
            "section": None,
            "kind": "HIRING_CAPABILITY",
            "obligation": "REQUIRED",
        }
        for pid, quote in [
            ("A", "Java required"),
            ("B", "Java required"),
            ("A", "Python required"),
            ("unknown", "Java required"),
        ]
    ]
    result = batch.BatchRoleProfile.model_validate(
        {
            "themes": [{"name": "Java", "dimension": "TECHNICAL", "supports": supports}],
            "posting_reviews": [{"posting_id": "A", "status": "USABLE", "note": ""}] * 2,
            "limitations": [],
        }
    )
    audit = batch.audit(result, records)
    assert audit["valid_support_count"] == 2
    assert audit["invalid_support_count"] == 2
    assert audit["missing_review_ids"] == ["B"]
    assert audit["duplicate_review_ids"] == ["A"]
    assert audit["themes"][0]["posting_support_count"] == 2
    assert audit["themes"][0]["employer_support_count"] == 1


def test_explicit_subset_keeps_original_text_and_order(batch):
    records = [{"posting_id": "A", "text": "Full A"}, {"posting_id": "B", "text": "Full B"}]
    assert batch.select_records(records, ["B", "A"]) == [records[1], records[0]]
    assert batch.select_records(records, None) == records
    with pytest.raises(ValueError):
        batch.select_records(records, ["A", "A"])
    with pytest.raises(ValueError):
        batch.select_records(records, ["missing"])


@pytest.mark.parametrize("kind", ["PREFERENCE", "ROLE_RESPONSIBILITY"])
def test_batch_audit_does_not_promote_optional_or_duty_evidence(batch, kind):
    result = batch.BatchRoleProfile.model_validate(
        {
            "themes": [
                {
                    "name": "Java",
                    "dimension": "TECHNICAL",
                    "supports": [
                        {
                            "posting_id": "A",
                            "quote": "Java",
                            "section": None,
                            "kind": kind,
                            "obligation": "REQUIRED",
                        }
                    ],
                }
            ],
            "posting_reviews": [],
            "limitations": [],
        }
    )
    checked = batch.audit(result, [{"posting_id": "A", "employer": "Acme", "text": "Java"}])
    assert checked["valid_support_count"] == 0
    assert checked["invalid_support_count"] == 1

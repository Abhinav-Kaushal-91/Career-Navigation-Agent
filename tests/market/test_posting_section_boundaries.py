"""Full vacancy bodies must survive Markdown section boundaries."""

import pytest

from ai_career_navigator.market.processing import classify_and_segment_source
from ai_career_navigator.market.requirement_schemas import SourceContentType

from .test_requirement_processing import source_content


@pytest.mark.parametrize("heading", ["#", "##", "**"])
def test_single_job_keeps_responsibilities_and_qualifications_subsections(heading):
    def title(value):
        return f"**{value}**" if heading == "**" else f"{heading} {value}"

    markdown = "\n".join(
        [
            title("Senior Java Developer"),
            "Company: Example",
            "Location: Toronto, Ontario",
            "Join our team.",
            title("Responsibilities"),
            "Build reliable services.",
            title("Qualifications"),
            "Java and database experience required.",
        ]
    )
    result = classify_and_segment_source(
        source_content(markdown, page_title="Senior Java Developer")
    )
    assert result.content_type is SourceContentType.DIRECT_JOB_PAGE
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert "Build reliable services." in candidate.posting_text
    assert "Java and database experience required." in candidate.posting_text
    assert candidate.employer == "Example"
    assert candidate.location == "Toronto, Ontario"


def test_hiring_signal_can_appear_only_in_a_job_subsection():
    result = classify_and_segment_source(
        source_content(
            "# Financial Analyst\nAcme is expanding.\n"
            "## Qualifications\nFinancial reporting experience is required.\n",
            page_title="Financial Analyst",
        )
    )
    assert len(result.candidates) == 1
    assert "Financial reporting experience is required." in result.candidates[0].posting_text


def test_two_job_cards_keep_their_own_nested_sections_without_cross_contamination():
    result = classify_and_segment_source(
        source_content(
            "2 open jobs\n"
            "## Data Analyst — Alpha\nLocation: Toronto, Canada\nJoin our team.\n"
            "### Responsibilities\nPrepare reports.\n"
            "### Qualifications\nSQL experience required.\n"
            "## Operations Manager — Beta\nLocation: Vancouver, Canada\nJoin our team.\n"
            "### Responsibilities\nManage staffing.\n"
            "### Qualifications\nScheduling experience required.\n"
        )
    )
    assert len(result.candidates) == 2
    first, second = result.candidates
    assert "SQL experience required." in first.posting_text
    assert "Scheduling experience" not in first.posting_text
    assert "Scheduling experience required." in second.posting_text
    assert "SQL experience" not in second.posting_text
    assert first.employer == "Alpha"
    assert second.employer == "Beta"


def test_role_word_in_section_heading_does_not_create_an_extra_vacancy():
    result = classify_and_segment_source(
        source_content(
            "# Software Engineer\nJoin our team.\n"
            "## What our engineers do\nBuild reusable tools.\n"
            "## Engineer qualifications\nTesting experience required.\n",
            page_title="Software Engineer",
        )
    )
    assert len(result.candidates) == 1
    assert "Testing experience required." in result.candidates[0].posting_text


def test_salary_section_is_excluded_but_later_qualifications_are_not_lost():
    result = classify_and_segment_source(
        source_content(
            "# Business Analyst\nJoin our team.\n"
            "## Salary information\nMarket guide: all analysts earn $100,000.\n"
            "## Qualifications\nRequirements elicitation experience required.\n",
            page_title="Business Analyst",
        )
    )
    assert len(result.candidates) == 1
    text = result.candidates[0].posting_text
    assert "Requirements elicitation experience required." in text
    assert "all analysts earn" not in text


@pytest.mark.parametrize("job_heading", ["# Business Analyst\n", ""])
def test_related_job_footer_never_becomes_a_candidate_or_contaminates_the_main_job(job_heading):
    result = classify_and_segment_source(
        source_content(
            job_heading + "Job description.\nLocation: Toronto, Canada\n"
            "## Qualifications\nInterview experience required.\n"
            "## Related jobs\n"
            "3 open jobs\n"
            "### Engineering Manager\nJoin our team.\n"
            "#### Qualifications\nTen years of management required.\n",
            page_title="Business Analyst",
        )
    )
    assert result.content_type is SourceContentType.DIRECT_JOB_PAGE
    assert result.aggregator_reported_count is None
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.title == "Business Analyst"
    assert "Interview experience required." in candidate.posting_text
    assert "Engineering Manager" not in candidate.posting_text
    assert "Ten years" not in candidate.posting_text


def test_matching_single_job_metadata_is_preserved_for_heading_based_content():
    result = classify_and_segment_source(
        source_content(
            "# Data Analyst\nJoin our team.\n## Qualifications\nSQL required.\n",
            page_title="Data Analyst",
            employer="Structured Employer",
            location="Vancouver, Canada",
        )
    )
    assert result.candidates[0].employer == "Structured Employer"
    assert result.candidates[0].location == "Vancouver, Canada"
    assert result.candidates[0].location_evidence_text == "Vancouver, Canada"


def test_listing_metadata_is_not_assigned_to_an_individual_job_card():
    result = classify_and_segment_source(
        source_content(
            "5 open jobs\n## Data Analyst\nJob description.\n### Qualifications\nSQL required.\n",
            page_title="Data Analyst",
            employer="Listing Operator",
            location="Toronto, Canada",
        )
    )
    assert result.candidates[0].employer is None
    assert result.candidates[0].location is None

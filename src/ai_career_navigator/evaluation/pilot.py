"""Input/reference separation for the reviewed ten-case evaluation workbook."""

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict, Field

from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateAccessibility,
    CandidateProfile,
    CareerGoal,
    CareerStage,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
    GeographyScope,
    GoalType,
)

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


class PilotExecutionInput(BaseModel):
    """Only fields permitted to enter the Career Navigator workflow."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(pattern=r"^CN-\d{3}$")
    scenario_type: str
    candidate_profile: str = Field(min_length=1)
    career_goal: str = Field(min_length=1)
    target_role: str = Field(min_length=1)
    target_timeframe: str = Field(min_length=1)


class PilotReference(BaseModel):
    """Reviewed evaluator-only fields that must never enter agent inputs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_strengths: str
    expected_gaps: str
    expected_match_types: str
    expected_gap_severity: str
    expected_career_verdict: str
    expected_confidence: str
    ground_truth_rationale: str
    special_expected_behavior: str
    golden_label_reviewed: str
    notes: str


@dataclass(frozen=True)
class PilotCase:
    execution: PilotExecutionInput
    reference: PilotReference


_VERDICT_MAP = {
    CandidateAccessibility.APPLY_NOW: "ready_now",
    CandidateAccessibility.APPLY_SELECTIVELY: "strong_fit_minor_gaps",
    CandidateAccessibility.NEAR_TERM_TARGET: "adjacent_fit",
    CandidateAccessibility.ASPIRATIONAL: "significant_upskilling",
    CandidateAccessibility.POOR_FIT: "significant_upskilling",
    CandidateAccessibility.INSUFFICIENT_CANDIDATE_EVIDENCE: "insufficient_evidence",
}


def map_accessibility_to_verdict(value: CandidateAccessibility) -> str:
    """Apply the reviewed evaluation-only mapping without changing product logic."""

    return _VERDICT_MAP[value]


def execution_payload(case: PilotCase) -> dict[str, str]:
    """Return the auditable allowlist used to construct workflow inputs."""

    return case.execution.model_dump()


def _maturity(text: str) -> EvidenceMaturity:
    lowered = text.casefold()
    if any(word in lowered for word in ("leads ", "led ", "manages ", "mentors ")):
        return EvidenceMaturity.LEADERSHIP
    if "production" in lowered or "enterprise" in lowered:
        return EvidenceMaturity.PRODUCTION
    if any(word in lowered for word in ("built ", "delivered ", "developed ", "designed ")):
        return EvidenceMaturity.APPLIED
    if any(word in lowered for word in ("exposure", "familiar", "limited")):
        return EvidenceMaturity.EXPOSURE
    return EvidenceMaturity.DEMONSTRATED


def build_workflow_inputs(
    case: PilotCase, *, target_location: str = "Canada"
) -> tuple[CandidateProfile, CareerGoal]:
    """Translate only stated case input into approved synthetic evaluation records."""

    text = case.execution.candidate_profile
    statements = [item.strip() for item in re.split(r"(?<=[.!?])\s+|;\s+", text) if item.strip()]
    evidence = [
        EvidenceItem(
            evidence_type="evaluation_case_statement",
            source_type="reviewed_synthetic_evaluation",
            source_reference=f"{case.execution.case_id}:Candidate_Profile",
            capability=statement[:160],
            description=statement,
            maturity_level=_maturity(statement),
            confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
            confidence=ConfidenceLevel.HIGH,
            approved_by_user=True,
        )
        for statement in statements
    ]
    current_role = re.split(r"\s+(?:with|who)\s+", statements[0], maxsplit=1)[0]
    lowered = text.casefold()
    if any(word in lowered for word in ("manager", "team lead", "leads ")):
        stage = CareerStage.LEADERSHIP_MANAGEMENT
    elif "senior" in lowered:
        stage = CareerStage.SENIOR_INDIVIDUAL_CONTRIBUTOR
    else:
        stage = CareerStage.MID_CAREER
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    profile = CandidateProfile(
        career_stage=stage,
        professional_summary=text,
        current_role=current_role,
        current_location=target_location,
        evidence_items=evidence,
        approval_status=ApprovalStatus.APPROVED,
        created_at=now,
        confirmed_at=now,
    )
    goal_type = (
        GoalType.LEADERSHIP_PROGRESSION
        if "leadership" in case.execution.career_goal.casefold()
        else GoalType.ROLE_TRANSITION
    )
    goal = CareerGoal(
        goal_type=goal_type,
        target_role=case.execution.target_role,
        target_timeline_months=1 if case.execution.target_timeframe.casefold() == "now" else None,
        target_location=target_location,
        geography_scopes=[GeographyScope.COUNTRY],
        bridge_role_willingness=False,
        search_expansion_permission=False,
        approval_status=ApprovalStatus.APPROVED,
        created_at=now,
        approved_at=now,
    )
    return profile, goal


def _column_index(reference: str) -> int:
    match = re.match(r"[A-Z]+", reference)
    if match is None:
        raise ValueError(f"invalid cell reference: {reference}")
    value = 0
    for letter in match.group(0):
        value = value * 26 + ord(letter) - 64
    return value - 1


def _cell_text(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find(f"{{{_MAIN}}}v")
    if value is None or value.text is None:
        return "".join(node.text or "" for node in cell.findall(f".//{{{_MAIN}}}t"))
    if cell_type == "s":
        return shared_strings[int(value.text)]
    return value.text


def _sheet_rows(path: Path, sheet_name: str) -> list[dict[int, str]]:
    with zipfile.ZipFile(path) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        sheet = next(
            (
                item
                for item in workbook.findall(f".//{{{_MAIN}}}sheet")
                if item.attrib.get("name") == sheet_name
            ),
            None,
        )
        if sheet is None:
            raise ValueError(f"worksheet not found: {sheet_name}")
        relationship_id = sheet.attrib[f"{{{_REL}}}id"]
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship = next(
            item
            for item in relationships.findall(f"{{{_PKG_REL}}}Relationship")
            if item.attrib["Id"] == relationship_id
        )
        target = relationship.attrib["Target"].lstrip("/")
        worksheet_path = target if target.startswith("xl/") else f"xl/{target}"
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(node.text or "" for node in item.findall(f".//{{{_MAIN}}}t"))
                for item in root.findall(f"{{{_MAIN}}}si")
            ]
        worksheet = ElementTree.fromstring(archive.read(worksheet_path))
    return [
        {
            _column_index(cell.attrib["r"]): _cell_text(cell, shared_strings)
            for cell in row.findall(f"{{{_MAIN}}}c")
        }
        for row in worksheet.findall(f".//{{{_MAIN}}}row")
    ]


def load_pilot_cases(path: Path) -> list[PilotCase]:
    """Load exactly ten reviewed cases while preserving a hard input boundary."""

    rows = _sheet_rows(path, "Golden_Dataset")
    header_row = next(
        (row for row in rows if row.get(0) == "Case_ID"),
        None,
    )
    if header_row is None:
        raise ValueError("Golden_Dataset headers not found")
    headers = {value: index for index, value in header_row.items()}
    required = {
        "Case_ID",
        "Scenario_Type",
        "Candidate_Profile",
        "Career_Goal",
        "Target_Role",
        "Target_Timeframe",
        "Expected_Strengths",
        "Expected_Gaps",
        "Expected_Match_Types",
        "Expected_Gap_Severity",
        "Expected_Career_Verdict",
        "Expected_Confidence",
        "Ground_Truth_Rationale",
        "Special_Expected_Behavior",
        "Golden_Label_Reviewed",
        "Notes",
    }
    missing = required - set(headers)
    if missing:
        raise ValueError(f"Golden_Dataset is missing headers: {sorted(missing)}")
    cases: list[PilotCase] = []
    for row in rows:
        case_id = row.get(headers["Case_ID"], "")
        if not re.fullmatch(r"CN-\d{3}", case_id):
            continue

        def get(name: str) -> str:
            return row.get(headers[name], "").strip()

        reference = PilotReference(
            expected_strengths=get("Expected_Strengths"),
            expected_gaps=get("Expected_Gaps"),
            expected_match_types=get("Expected_Match_Types"),
            expected_gap_severity=get("Expected_Gap_Severity"),
            expected_career_verdict=get("Expected_Career_Verdict"),
            expected_confidence=get("Expected_Confidence"),
            ground_truth_rationale=get("Ground_Truth_Rationale"),
            special_expected_behavior=get("Special_Expected_Behavior"),
            golden_label_reviewed=get("Golden_Label_Reviewed"),
            notes=get("Notes"),
        )
        if reference.golden_label_reviewed.casefold() != "yes":
            raise ValueError(f"case is not reviewed: {case_id}")
        cases.append(
            PilotCase(
                execution=PilotExecutionInput(
                    case_id=case_id,
                    scenario_type=get("Scenario_Type"),
                    candidate_profile=get("Candidate_Profile"),
                    career_goal=get("Career_Goal"),
                    target_role=get("Target_Role"),
                    target_timeframe=get("Target_Timeframe"),
                ),
                reference=reference,
            )
        )
    if len(cases) != 10 or len({case.execution.case_id for case in cases}) != 10:
        raise ValueError("pilot dataset must contain exactly 10 unique reviewed cases")
    return cases

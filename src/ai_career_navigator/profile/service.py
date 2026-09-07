"""Deterministic assembly of explicit onboarding facts into a candidate profile."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from ai_career_navigator.domain import (
    ApprovalStatus,
    CandidateProfile,
    ConfidenceLevel,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
)
from ai_career_navigator.profile.schemas import ProfileDraft

MATURITY_LABELS = {
    "Learning / Exposure": EvidenceMaturity.EXPOSURE,
    "Used in Projects": EvidenceMaturity.DEMONSTRATED,
    "Used Professionally": EvidenceMaturity.APPLIED,
    "Used in Production": EvidenceMaturity.PRODUCTION,
    "Led / Owned": EvidenceMaturity.LEADERSHIP,
}


def maturity_from_label(label: str) -> EvidenceMaturity:
    try:
        return MATURITY_LABELS[label]
    except KeyError as error:
        raise ValueError(f"unknown maturity label: {label}") from error


def maturity_label(maturity: EvidenceMaturity) -> str:
    return next(label for label, value in MATURITY_LABELS.items() if value is maturity)


def _evidence_id(source_type: str, entry_id: UUID, capability: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"career-profile/{source_type}/{entry_id}/{capability}")


def _explicit_evidence(
    *,
    evidence_type: str,
    source_type: str,
    source_reference: str,
    source_id: UUID,
    capability: str,
    description: str,
    maturity: EvidenceMaturity,
    context: str | None = None,
    start_date=None,
    end_date=None,
    outcome: str | None = None,
    metric: str | None = None,
    created_at: datetime,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=_evidence_id(source_type, source_id, capability),
        evidence_type=evidence_type,
        source_type=source_type,
        source_reference=source_reference,
        capability=capability,
        description=description,
        maturity_level=maturity,
        context=context,
        start_date=start_date,
        end_date=end_date,
        outcome=outcome,
        metric=metric,
        confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        approved_by_user=True,
        created_at=created_at,
    )


def evidence_from_draft(draft: ProfileDraft, *, created_at: datetime) -> list[EvidenceItem]:
    """Map only explicit, deterministic user entries into evidence records."""

    evidence: list[EvidenceItem] = []
    for experience in draft.experiences:
        details = (
            " ".join(
                item
                for item in (
                    experience.description,
                    "; ".join(experience.accomplishments),
                )
                if item
            )
            or "User-entered professional experience."
        )
        evidence.append(
            _explicit_evidence(
                evidence_type="employment",
                source_type="manual onboarding",
                source_reference=f"{experience.job_title} at {experience.organization}",
                source_id=experience.entry_id,
                capability=experience.job_title,
                description=details,
                maturity=EvidenceMaturity.APPLIED,
                context=experience.location,
                start_date=experience.start_date,
                end_date=experience.end_date,
                created_at=created_at,
            )
        )
    for skill in draft.skills:
        evidence.append(
            _explicit_evidence(
                evidence_type="skill",
                source_type="manual onboarding",
                source_reference=skill.category.value,
                source_id=skill.entry_id,
                capability=skill.name,
                description=f"User-confirmed {skill.category.value.lower()} capability.",
                maturity=skill.maturity,
                created_at=created_at,
            )
        )
    for project in draft.projects:
        for capability in project.capabilities_used:
            evidence.append(
                _explicit_evidence(
                    evidence_type="project",
                    source_type="manual onboarding",
                    source_reference=(
                        f"{project.project_type.value}: {project.name} "
                        f"({project.delivery_stage.value})"
                    ),
                    source_id=project.entry_id,
                    capability=capability,
                    description=project.contribution,
                    maturity=project.maturity,
                    context=project.context,
                    outcome=project.outcome,
                    metric=project.measurable_impact,
                    created_at=created_at,
                )
            )
    for education in draft.education:
        capability = education.field_of_study or education.qualification
        evidence.append(
            _explicit_evidence(
                evidence_type="education",
                source_type="manual onboarding",
                source_reference=f"{education.institution}, {education.completion_year}",
                source_id=education.entry_id,
                capability=capability,
                description=education.qualification,
                maturity=EvidenceMaturity.EXPOSURE,
                created_at=created_at,
            )
        )
    for certification in draft.certifications:
        evidence.append(
            _explicit_evidence(
                evidence_type="certification",
                source_type="manual onboarding",
                source_reference=f"{certification.issuer}, {certification.year}",
                source_id=certification.entry_id,
                capability=certification.name,
                description=f"User-entered certification issued by {certification.issuer}.",
                maturity=EvidenceMaturity.EXPOSURE,
                created_at=created_at,
            )
        )
    return evidence


def build_candidate_profile(
    draft: ProfileDraft,
    *,
    approved: bool = False,
    now: datetime | None = None,
) -> CandidateProfile:
    """Build a draft or confirmed profile without inference or external calls."""

    timestamp = now or datetime.now(UTC)
    active_role = max(
        (item for item in draft.experiences if item.current),
        key=lambda item: item.start_date,
        default=None,
    )
    return CandidateProfile(
        career_stage=draft.about.career_stage,
        years_professional_experience=draft.about.years_professional_experience,
        professional_summary=draft.about.career_summary,
        core_competencies=draft.core_competencies_text,
        current_role=(
            draft.about.current_role or (active_role.job_title if active_role is not None else None)
        ),
        current_location=draft.about.current_location,
        evidence_items=evidence_from_draft(draft, created_at=timestamp),
        approval_status=ApprovalStatus.APPROVED if approved else ApprovalStatus.DRAFT,
        created_at=timestamp,
        confirmed_at=timestamp if approved else None,
    )


def confirm_candidate_profile(
    draft: ProfileDraft, *, now: datetime | None = None
) -> CandidateProfile:
    return build_candidate_profile(draft, approved=True, now=now)

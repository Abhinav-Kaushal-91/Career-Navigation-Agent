"""Structured manual profile onboarding and clearly separated demo profile."""

from datetime import date
from typing import Any
from uuid import uuid4

import streamlit as st
from pydantic import ValidationError

from ai_career_navigator.domain import (
    CandidateProfile,
    CareerStage,
    EvidenceConfirmationStatus,
    EvidenceMaturity,
)
from ai_career_navigator.models import ModelGatewayError
from ai_career_navigator.profile import (
    MATURITY_LABELS,
    PROFILE_ONBOARDING_STEPS,
    AboutYou,
    CapabilityInferenceResult,
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    InferenceDecision,
    InferenceRunStatus,
    ProfileDraft,
    ProjectEntry,
    ProjectStage,
    ProjectType,
    SkillCategory,
    SkillEntry,
    add_inferred_evidence,
    apply_inference_decision,
    build_candidate_profile,
    capability_key,
    clean_capability_name,
    confirm_candidate_profile,
    dedupe_capabilities,
    finalize_strengths_profile,
    infer_capabilities,
    maturity_from_label,
    maturity_label,
    next_profile_highest,
    profile_step_states,
)
from ai_career_navigator.ui.components.badges import render_status_badge
from ai_career_navigator.ui.components.cards import render_card, render_card_pair
from ai_career_navigator.ui.components.evidence import render_evidence_item
from ai_career_navigator.ui.components.layout import render_page_header
from ai_career_navigator.ui.components.metrics import render_metric_card
from ai_career_navigator.ui.components.navigation import go_to
from ai_career_navigator.ui.components.states import render_state
from ai_career_navigator.ui.demo_data import (
    CANDIDATE_PROFILE,
    CONFIRMED_CAPABILITIES,
    DEMO_INFERENCE_RESULT,
    DEMO_LABEL,
    PROFILE_EVIDENCE,
)
from ai_career_navigator.ui.live_workflow import (
    build_live_workflow_runtime,
    load_live_settings,
)

PROFESSIONAL_SUMMARY_LABEL = "Professional Summary (optional)"

CAREER_STAGE_LABELS = {
    CareerStage.STUDENT: "Student",
    CareerStage.RECENT_GRADUATE: "Recent Graduate",
    CareerStage.EARLY_CAREER: "Early Career",
    CareerStage.MID_CAREER: "Mid Career",
    CareerStage.SENIOR_INDIVIDUAL_CONTRIBUTOR: "Senior Individual Contributor",
    CareerStage.LEADERSHIP_MANAGEMENT: "Leadership / Management",
    CareerStage.CAREER_RETURNER: "Career Returner",
    CareerStage.OPEN_OTHER: "Other / Exploring",
}

SKILL_LIBRARY: dict[str, tuple[SkillCategory, tuple[str, ...]]] = {
    "Python": (SkillCategory.TECHNICAL, ("python",)),
    "C#": (SkillCategory.TECHNICAL, ("c#", "c sharp")),
    "UiPath": (SkillCategory.TECHNICAL, ("uipath",)),
    "REST APIs": (SkillCategory.TECHNICAL, ("rest api", "restful api")),
    "SQL": (SkillCategory.TECHNICAL, ("sql",)),
    "Stakeholder Management": (
        SkillCategory.PROFESSIONAL,
        ("stakeholder management", "stakeholder engagement"),
    ),
    "Solution Design": (SkillCategory.PROFESSIONAL, ("solution design",)),
    "Production Support": (SkillCategory.PROFESSIONAL, ("production support",)),
    "Project Ownership": (SkillCategory.PROFESSIONAL, ("project ownership",)),
    "Team Leadership": (SkillCategory.LEADERSHIP, ("team leadership", "team lead")),
}


def _draft() -> ProfileDraft:
    raw_draft = st.session_state.profile_draft
    if raw_draft is None:
        draft = ProfileDraft()
        st.session_state.profile_draft = draft.model_dump(mode="json")
        return draft
    return ProfileDraft.model_validate(raw_draft)


def _save_draft(draft: ProfileDraft) -> None:
    st.session_state.profile_draft = draft.model_dump(mode="json")
    st.session_state.profile_confirmed = False
    st.session_state.confirmed_profile = None
    _reset_capability_inference()


def _reset_capability_inference() -> None:
    st.session_state.capability_review_active = False
    st.session_state.capability_inference_status = "NOT_STARTED"
    st.session_state.capability_inference_result = None
    st.session_state.capability_inference_error = None
    st.session_state.capability_inference_decisions = {}
    st.session_state.capability_inference_metadata = None
    st.session_state.pop("strengths_selection", None)


def _confirmed_profile() -> CandidateProfile:
    return CandidateProfile.model_validate(st.session_state.confirmed_profile)


def _go_profile_step(step: str) -> None:
    highest = st.session_state.highest_reached_profile_step
    st.session_state.highest_reached_profile_step = next_profile_highest(highest, step)
    st.session_state.current_profile_step = step
    st.rerun()


def _validation_message(error: ValidationError) -> str:
    first_error = error.errors()[0]
    location = " ".join(str(item).replace("_", " ") for item in first_error["loc"])
    message = str(first_error["msg"]).removeprefix("Value error, ")
    return f"{location.title()}: {message}" if location else message


def _split_lines(value: str) -> list[str]:
    return [line.strip().removeprefix("- ") for line in value.splitlines() if line.strip()]


def _split_commas(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _replace_entry(draft: ProfileDraft, field: str, entry: Any) -> ProfileDraft:
    entries = list(getattr(draft, field))
    entries = [entry if item.entry_id == entry.entry_id else item for item in entries]
    return draft.model_copy(update={field: entries})


def _remove_entry(draft: ProfileDraft, field: str, entry_id: Any) -> None:
    entries = [item for item in getattr(draft, field) if item.entry_id != entry_id]
    _save_draft(draft.model_copy(update={field: entries}))
    st.rerun()


def _new_form_version(kind: str) -> int:
    return int(st.session_state.profile_new_form_versions[kind])


def _advance_new_form(kind: str) -> None:
    versions = dict(st.session_state.profile_new_form_versions)
    versions[kind] = int(versions[kind]) + 1
    st.session_state.profile_new_form_versions = versions


def _detected_skill_suggestions(draft: ProfileDraft) -> tuple[str, ...]:
    """Find only literal skill mentions; broader interpretation belongs to AI review."""

    parts: list[str] = []
    for experience in draft.experiences:
        parts.extend((experience.description or "", *experience.accomplishments))
    for project in draft.projects:
        parts.extend((project.contribution, *project.capabilities_used))
    parts.append(draft.core_competencies_text or "")
    corpus = " ".join(parts).casefold()
    existing = {skill.name.casefold() for skill in draft.skills}
    detected = [
        name
        for name, (_, aliases) in SKILL_LIBRARY.items()
        if name.casefold() not in existing and any(alias in corpus for alias in aliases)
    ]
    for project in draft.projects:
        for capability in project.capabilities_used:
            if capability.casefold() not in existing and capability not in detected:
                detected.append(capability)
    if draft.core_competencies_text:
        entries = _split_competency_entries(draft.core_competencies_text)
        for capability in entries:
            if capability.casefold() not in existing and capability not in detected:
                detected.append(capability)
    return tuple(detected)


def _split_competency_entries(value: str) -> tuple[str, ...]:
    normalized = value.replace(";", "\n").replace(",", "\n")
    candidates = _split_lines(normalized)
    return tuple(
        dict.fromkeys(item for item in candidates if len(item) <= 80 and len(item.split()) <= 8)
    )


def _render_profile_progress() -> None:
    current = st.session_state.current_profile_step
    highest = st.session_state.highest_reached_profile_step
    st.caption(
        f"Profile setup · Step {PROFILE_ONBOARDING_STEPS.index(current) + 1} "
        f"of {len(PROFILE_ONBOARDING_STEPS)}"
    )
    with st.container(key="profile_onboarding_navigation"):
        columns = st.columns(len(PROFILE_ONBOARDING_STEPS))
        for column, step in zip(columns, profile_step_states(current, highest), strict=True):
            with column:
                if st.button(
                    f"{step.number} {step.label}",
                    key=f"onboarding_{step.number}",
                    type="primary" if step.status == "current" else "secondary",
                    disabled=not step.available,
                    use_container_width=True,
                ):
                    _go_profile_step(step.label)


def _render_section_actions(back_step: str | None, next_step: str, next_label: str) -> None:
    back, _, forward = st.columns([1.3, 2.5, 1.5])
    with back:
        if st.button(
            "Back to Home" if back_step is None else f"Back to {back_step}",
            key=f"profile_back_{back_step or 'home'}",
            use_container_width=True,
        ):
            go_to("Home") if back_step is None else _go_profile_step(back_step)
    with forward:
        if st.button(next_label, type="primary", use_container_width=True):
            _go_profile_step(next_step)


def _render_about(draft: ProfileDraft) -> None:
    render_page_header(
        "About You",
        "Start with your current career context",
        "Employment is optional. Students and career returners can continue without a "
        "current role.",
    )
    about = draft.about
    with st.form("about_you_form"):
        left, right = st.columns(2)
        with left:
            stage = st.selectbox(
                "Career stage",
                tuple(CareerStage),
                index=tuple(CareerStage).index(about.career_stage),
                format_func=lambda value: CAREER_STAGE_LABELS[value],
            )
            role = st.text_input("Current role (optional)", value=about.current_role or "")
        with right:
            years = st.number_input(
                "Years of professional experience",
                min_value=0,
                max_value=80,
                value=(
                    int(about.years_professional_experience)
                    if about.years_professional_experience
                    else None
                ),
                step=1,
                placeholder="0",
            )
            location = st.text_input(
                "Current location (optional)", value=about.current_location or ""
            )
        summary = st.text_area(
            PROFESSIONAL_SUMMARY_LABEL,
            value=about.career_summary or "",
            help=(
                "Briefly describe your current professional background or where you are in "
                "your career."
            ),
        )
        submitted = st.form_submit_button("Save and continue", type="primary")
    if submitted:
        try:
            _save_draft(
                draft.model_copy(
                    update={
                        "about": AboutYou(
                            current_role=role,
                            years_professional_experience=years or 0,
                            current_location=location,
                            career_stage=stage,
                            career_summary=summary,
                        )
                    }
                )
            )
            _go_profile_step("Professional Profile")
        except ValidationError as error:
            st.error(_validation_message(error))
    if st.button("Back to Home", key="about_back_home"):
        go_to("Home")


def _experience_form(
    entry: ExperienceEntry | None = None, *, form_version: int = 0
) -> ExperienceEntry | None:
    key = str(entry.entry_id) if entry else f"new_{form_version}"
    today = date.today()
    with st.form(f"experience_form_{key}"):
        left, right = st.columns(2)
        with left:
            title = st.text_input("Job title", value=entry.job_title if entry else "")
            organization = st.text_input("Organization", value=entry.organization if entry else "")
            location = st.text_input(
                "Location (optional)", value=entry.location or "" if entry else ""
            )
        with right:
            start = st.date_input(
                "Start date",
                value=entry.start_date if entry else date(today.year - 1, 1, 1),
                min_value=date(today.year - 60, 1, 1),
                max_value=today,
            )
            current = st.checkbox("I currently work here", value=entry.current if entry else False)
            end = st.date_input(
                "End date",
                value=entry.end_date or today if entry else today,
                min_value=date(today.year - 60, 1, 1),
                max_value=today,
                disabled=current,
            )
        existing_details = ""
        if entry:
            existing_details = "\n".join(
                item for item in (entry.description, *entry.accomplishments) if item
            )
        role_evidence = st.text_area(
            "What did you do and achieve?",
            value=existing_details,
            help=(
                "Describe responsibilities, important work, decisions, and outcomes. "
                "Add one item per line."
            ),
        )
        submitted = st.form_submit_button("Save role", type="primary")
    if not submitted:
        return None
    return ExperienceEntry(
        entry_id=entry.entry_id if entry else uuid4(),
        job_title=title,
        organization=organization,
        start_date=start,
        end_date=None if current else end,
        current=current,
        location=location,
        description=None,
        accomplishments=_split_lines(role_evidence),
    )


def _render_experience(draft: ProfileDraft) -> None:
    render_page_header(
        "Professional Profile",
        "Add your core competencies and professional experience",
        "Keep your competencies and role evidence separate. Your Professional Summary is "
        "already saved in About You.",
    )
    st.subheader("Core Competencies")
    competency_text = st.text_area(
        "Paste your core competencies",
        value=draft.core_competencies_text or "",
        placeholder="Process discovery, solution roadmaps, requirements translation",
        help=(
            "Use commas, semicolons, or separate lines. AI Strength Identification will use "
            "this text together with the rest of your saved profile."
        ),
    )
    if st.button("Save core competencies", type="primary"):
        _save_draft(draft.model_copy(update={"core_competencies_text": competency_text}))
        st.rerun()

    st.subheader("Professional Experience")
    st.caption(
        "Employment history is optional. Describe what you did and achieved together, "
        "one item per line."
    )
    for entry in draft.experiences:
        with st.expander(f"{entry.job_title} · {entry.organization}"):
            try:
                updated = _experience_form(entry)
                if updated:
                    _save_draft(_replace_entry(draft, "experiences", updated))
                    st.rerun()
            except ValidationError as error:
                st.error(_validation_message(error))
            if st.button("Remove role", key=f"remove_experience_{entry.entry_id}"):
                _remove_entry(draft, "experiences", entry.entry_id)
    with st.expander("Add another role", expanded=not draft.experiences):
        try:
            added = _experience_form(form_version=_new_form_version("experience"))
            if added:
                _save_draft(draft.model_copy(update={"experiences": [*draft.experiences, added]}))
                _advance_new_form("experience")
                st.rerun()
        except ValidationError as error:
            st.error(_validation_message(error))
    _render_section_actions("About You", "Portfolio Projects", "Continue to Portfolio Projects")


def _skill_form(entry: SkillEntry | None = None, *, form_version: int = 0) -> SkillEntry | None:
    key = str(entry.entry_id) if entry else f"new_{form_version}"
    known_skills = tuple(SKILL_LIBRARY)
    choices = (*known_skills, "Other")
    initial_choice = entry.name if entry and entry.name in known_skills else "Other"
    left, right = st.columns(2)
    with left:
        suggestion = st.selectbox(
            "Skill or competency",
            choices,
            index=choices.index(initial_choice),
            key=f"skill_choice_{key}",
        )
        custom = ""
        if suggestion == "Other":
            custom = st.text_input(
                "Enter another skill or competency",
                value=entry.name if entry and entry.name not in known_skills else "",
                key=f"skill_other_{key}",
            )
    with right:
        labels = tuple(MATURITY_LABELS)
        level = st.selectbox(
            "Practical level",
            labels,
            index=labels.index(maturity_label(entry.maturity)) if entry else 0,
            key=f"skill_level_{key}",
        )
    submitted = st.button("Save skill", type="primary", key=f"save_skill_{key}")
    if not submitted:
        return None
    name = custom.strip() if suggestion == "Other" else suggestion
    category = SKILL_LIBRARY.get(name, (SkillCategory.OTHER, ()))[0]
    return SkillEntry(
        entry_id=entry.entry_id if entry else uuid4(),
        name=name,
        category=category,
        maturity=maturity_from_label(level),
    )


def _render_skills(draft: ProfileDraft) -> None:
    render_page_header(
        "Skills",
        "Review detected skills and add anything missing",
        "Only literal skill mentions are suggested here. Confirm them or add another skill, "
        "then choose the practical level that reflects how you used it.",
    )
    st.subheader("Core competencies")
    competency_text = st.text_area(
        "Paste skills and competencies",
        value=draft.core_competencies_text or "",
        placeholder="UiPath, REST APIs, automation design, stakeholder management",
        help=(
            "Use commas or separate lines. These become suggestions and are not approved "
            "until you add them below."
        ),
    )
    if st.button("Update skill suggestions", use_container_width=False):
        _save_draft(draft.model_copy(update={"core_competencies_text": competency_text}))
        st.rerun()

    suggestions = _detected_skill_suggestions(draft)
    st.subheader("Suggested from your information")
    if suggestions:
        columns = st.columns(3)
        for index, name in enumerate(suggestions):
            with columns[index % len(columns)]:
                st.write(name)
                if st.button(
                    f"Add {name}",
                    key=f"add_detected_skill_{name}",
                    use_container_width=True,
                ):
                    category = SKILL_LIBRARY.get(name, (SkillCategory.OTHER, ()))[0]
                    added = SkillEntry(
                        name=name,
                        category=category,
                        maturity=EvidenceMaturity.APPLIED,
                    )
                    _save_draft(draft.model_copy(update={"skills": [*draft.skills, added]}))
                    st.rerun()
    else:
        st.caption("No additional literal skill mentions were detected from saved information.")

    st.subheader("Confirmed skills and competencies")
    for entry in draft.skills:
        with st.expander(f"{entry.name} · {maturity_label(entry.maturity)}"):
            try:
                updated = _skill_form(entry)
                if updated:
                    _save_draft(_replace_entry(draft, "skills", updated))
                    st.rerun()
            except ValidationError as error:
                st.error(_validation_message(error))
            if st.button("Remove skill", key=f"remove_skill_{entry.entry_id}"):
                _remove_entry(draft, "skills", entry.entry_id)
    with st.expander("Add a skill or competency", expanded=not draft.skills):
        try:
            added = _skill_form(form_version=_new_form_version("skill"))
            if added:
                _save_draft(draft.model_copy(update={"skills": [*draft.skills, added]}))
                _advance_new_form("skill")
                st.rerun()
        except ValidationError as error:
            st.error(_validation_message(error))
    _render_section_actions(
        "Professional Profile", "Portfolio Projects", "Continue to Portfolio Projects"
    )


def _project_form(
    entry: ProjectEntry | None = None, *, form_version: int = 0
) -> ProjectEntry | None:
    key = str(entry.entry_id) if entry else f"new_{form_version}"
    with st.form(f"project_form_{key}"):
        left, right = st.columns(2)
        with left:
            name = st.text_input("Project name", value=entry.name if entry else "")
            project_type = st.selectbox(
                "Type",
                tuple(ProjectType),
                index=tuple(ProjectType).index(entry.project_type) if entry else 0,
            )
            context = st.text_input(
                "Project context *",
                value=entry.context if entry else "",
                placeholder="Personal portfolio, client delivery, academic capstone",
                help="Describe where or why this project was created or used.",
            )
            context_error = st.empty()
        with right:
            delivery_stage = st.selectbox(
                "Delivery stage",
                tuple(ProjectStage),
                index=(
                    tuple(ProjectStage).index(entry.delivery_stage)
                    if entry
                    else tuple(ProjectStage).index(ProjectStage.PROTOTYPE)
                ),
            )
            labels = tuple(MATURITY_LABELS)
            level = st.selectbox(
                "How was this work used?",
                labels,
                index=labels.index(maturity_label(entry.maturity)) if entry else 1,
            )
            capabilities = st.text_input(
                "Skills / capabilities used",
                value=", ".join(entry.capabilities_used) if entry else "",
                help="Separate entries with commas.",
            )
            impact = st.text_input(
                "Measurable impact (optional)", value=entry.measurable_impact or "" if entry else ""
            )
        contribution = st.text_area("What did you do?", value=entry.contribution if entry else "")
        outcome = st.text_area(
            "Outcome", value=entry.outcome if entry else "", help="A qualitative outcome is valid."
        )
        submitted = st.form_submit_button("Save portfolio project", type="primary")
    if not submitted:
        return None
    if not context.strip():
        context_error.error("Project context is required.")
        return None
    return ProjectEntry(
        entry_id=entry.entry_id if entry else uuid4(),
        name=name,
        project_type=project_type,
        delivery_stage=delivery_stage,
        context=context,
        contribution=contribution,
        capabilities_used=_split_commas(capabilities),
        maturity=maturity_from_label(level),
        outcome=outcome,
        measurable_impact=impact,
    )


def _render_projects(draft: ProfileDraft) -> None:
    render_page_header(
        "Portfolio Projects",
        "Add work that provides evidence beyond your role history",
        "This optional section is for portfolio, personal, academic, hackathon, volunteer, "
        "or significant cross-role projects not already covered in Experience.",
    )
    for entry in draft.projects:
        with st.expander(
            f"{entry.name} · {entry.project_type.value} · {entry.delivery_stage.value}"
        ):
            try:
                updated = _project_form(entry)
                if updated:
                    _save_draft(_replace_entry(draft, "projects", updated))
                    st.rerun()
            except ValidationError as error:
                st.error(_validation_message(error))
            if st.button("Remove project", key=f"remove_project_{entry.entry_id}"):
                _remove_entry(draft, "projects", entry.entry_id)
    with st.expander("Add a portfolio project", expanded=not draft.projects):
        try:
            added = _project_form(form_version=_new_form_version("project"))
            if added:
                _save_draft(draft.model_copy(update={"projects": [*draft.projects, added]}))
                _advance_new_form("project")
                st.rerun()
        except ValidationError as error:
            st.error(_validation_message(error))
    _render_section_actions("Professional Profile", "Education", "Continue to Education")


def _render_education(draft: ProfileDraft) -> None:
    render_page_header(
        "Education",
        "Add education and certifications where relevant",
        "Both sections are optional and do not determine whether you can complete your profile.",
    )
    st.subheader("Education")
    for entry in draft.education:
        render_card(
            entry.qualification,
            entry.institution,
            items=(entry.field_of_study or "Field not specified", str(entry.completion_year)),
        )
        if st.button("Remove education", key=f"remove_education_{entry.entry_id}"):
            _remove_entry(draft, "education", entry.entry_id)
    with st.expander("Add education", expanded=not draft.education):
        education_version = _new_form_version("education")
        with st.form(f"add_education_form_{education_version}"):
            qualification = st.text_input("Degree / qualification")
            field = st.text_input("Field of study (optional)")
            institution = st.text_input("Institution")
            completion_year = st.number_input(
                "Completion or expected year",
                min_value=date.today().year - 60,
                max_value=date.today().year + 15,
                value=date.today().year,
            )
            expected = st.checkbox("This is an expected completion year")
            add_education = st.form_submit_button("Save education", type="primary")
        if add_education:
            try:
                entry = EducationEntry(
                    qualification=qualification,
                    field_of_study=field,
                    institution=institution,
                    completion_year=completion_year,
                    expected=expected,
                )
                _save_draft(draft.model_copy(update={"education": [*draft.education, entry]}))
                _advance_new_form("education")
                st.rerun()
            except ValidationError as error:
                st.error(_validation_message(error))

    st.subheader("Certifications")
    for entry in draft.certifications:
        render_card(
            entry.name,
            entry.issuer,
            items=(
                f"Issued {entry.year}",
                f"Expires {entry.expiration_year}"
                if entry.expiration_year
                else "No expiration added",
            ),
        )
        if st.button("Remove certification", key=f"remove_certification_{entry.entry_id}"):
            _remove_entry(draft, "certifications", entry.entry_id)
    with st.expander("Add certification", expanded=not draft.certifications):
        certification_version = _new_form_version("certification")
        with st.form(f"add_certification_form_{certification_version}"):
            name = st.text_input("Certification name")
            issuer = st.text_input("Issuer")
            year = st.number_input(
                "Year",
                min_value=date.today().year - 60,
                max_value=date.today().year,
                value=date.today().year,
            )
            has_expiration = st.checkbox("This certification expires")
            expiration = st.number_input(
                "Expiration year",
                min_value=date.today().year - 60,
                max_value=date.today().year + 30,
                value=date.today().year,
                disabled=not has_expiration,
            )
            add_certification = st.form_submit_button("Save certification", type="primary")
        if add_certification:
            try:
                entry = CertificationEntry(
                    name=name,
                    issuer=issuer,
                    year=year,
                    expiration_year=expiration if has_expiration else None,
                )
                _save_draft(
                    draft.model_copy(update={"certifications": [*draft.certifications, entry]})
                )
                _advance_new_form("certification")
                st.rerun()
            except ValidationError as error:
                st.error(_validation_message(error))
    _render_section_actions(
        "Portfolio Projects",
        "AI Strength Identification",
        "Continue to AI Strength Identification",
    )


def _strength_category(name: str) -> SkillCategory:
    return SKILL_LIBRARY.get(name, (SkillCategory.OTHER, ()))[0]


def _render_strengths(draft: ProfileDraft) -> None:
    render_page_header(
        "AI Strength Identification",
        "Confirm the strengths supported by your evidence",
        "We reviewed your Professional Summary, Core Competencies, Professional Experience, "
        "Projects & Achievements, and Education & Certifications. Keep the strengths that fit "
        "and add anything we missed.",
    )

    status = st.session_state.capability_inference_status
    if status == "NOT_STARTED":
        base_profile = confirm_candidate_profile(draft)
        st.session_state.confirmed_profile = base_profile.model_dump(mode="json")
        with st.status("Identifying strengths from your evidence…", expanded=True):
            st.write("Reviewing your Professional Summary and Core Competencies")
            st.write("Reviewing Professional Experience and Projects & Achievements")
            st.write("Reviewing Education & Certifications")
            st.write("Building a grounded strengths list")
            _run_capability_inference(base_profile)
        st.rerun()

    profile = _confirmed_profile()
    inferred_items = [
        item
        for item in profile.evidence_items
        if item.confirmation_status
        in {
            EvidenceConfirmationStatus.INFERRED_PENDING,
            EvidenceConfirmationStatus.CONFIRMED_INFERENCE,
            EvidenceConfirmationStatus.REJECTED_INFERENCE,
        }
    ]
    inferred_names = [item.capability for item in inferred_items]
    detected_names = list(_detected_skill_suggestions(draft))
    existing_names = [item.name for item in draft.skills]
    options = list(dedupe_capabilities((*existing_names, *detected_names, *inferred_names)))
    rejected = {
        capability_key(item.capability)
        for item in inferred_items
        if item.confirmation_status is EvidenceConfirmationStatus.REJECTED_INFERENCE
    }
    defaults = [item for item in options if capability_key(item) not in rejected]

    if status == InferenceRunStatus.FAILED.value:
        render_state(
            "AI review unavailable",
            "The AI review did not finish, but you can retry or confirm strengths you add "
            "yourself. Your saved evidence is unchanged.",
            tone="warning",
        )
        if st.button("Retry AI strengths review"):
            st.session_state.capability_inference_status = "NOT_STARTED"
            st.session_state.pop("strengths_selection", None)
            st.rerun()
    elif status == InferenceRunStatus.EMPTY.value:
        render_state(
            "No additional AI strengths found",
            "Add anything missing below, or continue with the evidence already saved.",
        )
    else:
        st.caption("AI-detected strengths are selected by default.")

    selected = st.multiselect(
        "Your strengths",
        options=options,
        default=defaults,
        key="strengths_selection",
        placeholder="No strengths identified yet",
        help=(
            "Remove a chip to reject an AI suggestion. Retained chips become approved "
            "strengths when you confirm."
        ),
    )
    missed = st.text_area(
        "Anything we missed?",
        placeholder="Add one strength per line",
        help=(
            "Each line is saved as one capability. Technical names such as C#, C++, CI/CD, "
            "OAuth2/OIDC, AI/ML, .NET, and parentheses are preserved."
        ),
    )

    if inferred_items:
        with st.expander("Why these strengths were suggested"):
            for item in inferred_items:
                st.markdown(f"**{item.capability}**")
                st.caption(item.description)
                st.caption(item.source_reference)

    back, _, confirm = st.columns([1.3, 2.5, 1.5])
    with back:
        if st.button("Back to Education", use_container_width=True):
            _go_profile_step("Education")
    with confirm:
        if st.button("Confirm my strengths", type="primary", use_container_width=True):
            selected_names = list(dedupe_capabilities((*selected, *_split_lines(missed))))
            inferred_keys = {capability_key(item) for item in inferred_names}
            existing_by_key = {capability_key(item.name): item for item in draft.skills}
            manual_entries: list[SkillEntry] = []
            for name in selected_names:
                key = capability_key(name)
                if key in inferred_keys:
                    continue
                manual_entries.append(
                    existing_by_key.get(key)
                    or SkillEntry(
                        name=clean_capability_name(name),
                        category=_strength_category(name),
                        maturity=EvidenceMaturity.APPLIED,
                    )
                )
            updated_draft = draft.model_copy(update={"skills": manual_entries})
            st.session_state.profile_draft = updated_draft.model_dump(mode="json")
            st.session_state.confirmed_profile = finalize_strengths_profile(
                updated_draft, profile, selected_names
            ).model_dump(mode="json")
            st.session_state.profile_confirmed = True
            _go_profile_step("Review")


def _review_cards(items: list[Any], title: str, empty_message: str) -> None:
    st.subheader(title)
    if not items:
        st.caption(empty_message)
        return
    columns = st.columns(2)
    for index, item in enumerate(items):
        with columns[index % 2]:
            if isinstance(item, ExperienceEntry):
                render_card(
                    item.job_title,
                    item.organization,
                    items=tuple(item.accomplishments) or (item.description or "No details added",),
                )
            elif isinstance(item, ProjectEntry):
                render_card(
                    item.name,
                    item.contribution,
                    items=(item.project_type.value, item.delivery_stage.value, item.outcome),
                )
            elif isinstance(item, EducationEntry):
                render_card(
                    item.qualification, item.institution, items=(str(item.completion_year),)
                )
            else:
                render_card(item.name, item.issuer, items=(str(item.year),))


def _render_review(draft: ProfileDraft) -> None:
    render_page_header(
        "Review",
        "Review your career profile",
        "Confirm only when these user-entered facts accurately reflect your experience.",
    )
    about = draft.about
    profile = build_candidate_profile(draft)
    render_card_pair(
        left_title="Current context",
        left_body=profile.current_role or CAREER_STAGE_LABELS[about.career_stage],
        left_items=(
            f"{about.years_professional_experience:g} years professional experience",
            about.current_location or "Location not provided",
            CAREER_STAGE_LABELS[about.career_stage],
        ),
        right_title="Professional Summary",
        right_body=about.career_summary or "No career summary provided.",
    )
    _review_cards(draft.experiences, "Professional Experience", "No professional experience added.")
    if draft.experiences and profile.current_role is None:
        st.warning(
            "Which role should the career plan use as your current starting point? "
            "Mark an experience as current or add a current role in About You."
        )

    reviewed_profile = (
        _confirmed_profile()
        if st.session_state.profile_confirmed
        else build_candidate_profile(draft)
    )
    strength_items = [
        item
        for item in reviewed_profile.approved_evidence_items
        if item.evidence_type in {"skill", "inferred capability"}
    ]
    st.subheader("Confirmed strengths")
    if strength_items:
        st.write(" · ".join(dedupe_capabilities(item.capability for item in strength_items)))
    else:
        st.caption("No strengths confirmed.")

    _review_cards(draft.projects, "Portfolio Projects", "No portfolio projects added.")
    _review_cards(draft.education, "Education", "No education added.")
    _review_cards(draft.certifications, "Certifications", "No certifications added.")

    st.subheader("What you've demonstrated")
    metric_columns = st.columns(3)
    for column, (value, label) in zip(
        metric_columns,
        (
            (len(profile.evidence_items), "User-entered evidence"),
            (
                len(reviewed_profile.approved_evidence_items),
                "Confirmed evidence",
            ),
            (len(draft.projects), "Portfolio projects"),
        ),
        strict=True,
    ):
        with column:
            render_metric_card(value, label)
    inferred_confirmed = sum(
        item.confirmation_status is EvidenceConfirmationStatus.CONFIRMED_INFERENCE
        for item in reviewed_profile.evidence_items
    )
    inferred_rejected = sum(
        item.confirmation_status is EvidenceConfirmationStatus.REJECTED_INFERENCE
        for item in reviewed_profile.evidence_items
    )
    render_state(
        "Strengths reviewed",
        f"{inferred_confirmed} AI-inferred strengths confirmed and "
        f"{inferred_rejected} rejected. Rejected suggestions remain excluded from analysis.",
    )

    st.subheader("Edit a section")
    edit_columns = st.columns(5)
    for column, (label, step) in zip(
        edit_columns,
        (
            ("About You", "About You"),
            ("Professional Profile", "Professional Profile"),
            ("Portfolio Projects", "Portfolio Projects"),
            ("Education", "Education"),
            ("AI Strength Identification", "AI Strength Identification"),
        ),
        strict=True,
    ):
        with column:
            if st.button(f"Edit {label}", key=f"edit_{step}", use_container_width=True):
                _go_profile_step(step)

    if st.session_state.profile_confirmed:
        render_status_badge("APPROVED", prefix="Profile")
        _, forward, _ = st.columns([1.7, 1.4, 2.5])
        with forward:
            if st.button("Continue to Goal", type="primary", use_container_width=True):
                go_to("Goal")
        return

    back, _, confirm = st.columns([1.3, 2.5, 1.5])
    with back:
        if st.button("Back to AI Strength Identification", use_container_width=True):
            _go_profile_step("AI Strength Identification")
    with confirm:
        if st.button("Confirm Profile", type="primary", use_container_width=True):
            st.session_state.confirmed_profile = confirm_candidate_profile(draft).model_dump(
                mode="json"
            )
            st.session_state.profile_confirmed = True
            _go_profile_step("Review")


def _store_inference_failure(category: str = "ModelConfigurationError") -> None:
    st.session_state.capability_inference_status = InferenceRunStatus.FAILED.value
    st.session_state.capability_inference_error = (
        "We couldn’t identify additional capabilities right now. Your confirmed profile is "
        "still available and you can continue."
    )
    st.session_state.capability_inference_metadata = {"error_category": category}


def _run_capability_inference(profile: CandidateProfile) -> None:
    try:
        # A retry must reload current provider settings and receive a fresh
        # gateway instead of reusing a session object created before an env or
        # transient provider failure was corrected.
        runtime = build_live_workflow_runtime(load_live_settings())
        st.session_state.live_workflow_runtime = runtime
        gateway = runtime.model_gateway
    except (ModelGatewayError, ValueError) as error:
        _store_inference_failure(type(error).__name__)
        return

    with st.spinner("Reviewing confirmed evidence for additional capabilities…"):
        outcome = infer_capabilities(profile, gateway)
    st.session_state.capability_inference_status = outcome.status.value
    st.session_state.capability_inference_result = outcome.result.model_dump(mode="json")
    st.session_state.capability_inference_error = outcome.error_message
    st.session_state.capability_inference_metadata = {
        "provider": outcome.provider,
        "model": outcome.model,
        "latency_ms": outcome.latency_ms,
        "error_category": outcome.error_category,
    }
    if outcome.inferred_evidence:
        st.session_state.confirmed_profile = add_inferred_evidence(
            profile, outcome.inferred_evidence
        ).model_dump(mode="json")


def _apply_ui_inference_decision(evidence_id: Any, decision: InferenceDecision) -> None:
    profile = apply_inference_decision(_confirmed_profile(), evidence_id, decision)
    st.session_state.confirmed_profile = profile.model_dump(mode="json")
    decisions = dict(st.session_state.capability_inference_decisions)
    decisions[str(evidence_id)] = decision.value
    st.session_state.capability_inference_decisions = decisions
    st.rerun()


def _render_inference_proposal(
    profile: CandidateProfile,
    proposal: Any,
    *,
    demo: bool,
) -> None:
    inferred = next(
        (
            item
            for item in profile.evidence_items
            if item.source_type in {"AI capability inference", "synthetic profile inference"}
            and item.capability == proposal.capability
        ),
        None,
    )
    if inferred is None:
        return

    render_card(
        proposal.capability,
        proposal.reasoning_summary,
        items=(
            f"Proposed maturity: {proposal.proposed_maturity.value}",
            f"Confidence: {proposal.confidence.value}",
            f"Context: {proposal.source_context_summary}",
        ),
        accent=True,
    )
    render_status_badge(inferred.confirmation_status.value, prefix="Decision")
    st.markdown("**Supporting evidence**")
    evidence_by_id = {item.evidence_id: item for item in profile.evidence_items}
    for evidence_id in proposal.supporting_evidence_ids:
        source = evidence_by_id[evidence_id]
        render_evidence_item(source.capability, source.description, source.source_reference)

    if demo:
        st.caption("Demo action only — no real profile data is being changed.")
    status = inferred.confirmation_status
    if status is EvidenceConfirmationStatus.CONFIRMED_INFERENCE:
        render_state(
            "Capability confirmed",
            "This capability is now approved and will be used in your career analysis.",
            tone="success",
        )
        change, reject, _ = st.columns(3)
        with change:
            if st.button(
                "Move back to review",
                key=f"leave_inference_{inferred.evidence_id}",
                use_container_width=True,
            ):
                _apply_ui_inference_decision(
                    inferred.evidence_id, InferenceDecision.LEAVE_UNCONFIRMED
                )
        with reject:
            if st.button(
                "Reject instead",
                key=f"reject_inference_{inferred.evidence_id}",
                use_container_width=True,
            ):
                _apply_ui_inference_decision(inferred.evidence_id, InferenceDecision.REJECT)
    elif status is EvidenceConfirmationStatus.REJECTED_INFERENCE:
        render_state(
            "Capability rejected",
            "This suggestion will not be used in your career analysis.",
            tone="neutral",
        )
        if st.button(
            "Move back to review",
            key=f"leave_inference_{inferred.evidence_id}",
        ):
            _apply_ui_inference_decision(inferred.evidence_id, InferenceDecision.LEAVE_UNCONFIRMED)
    else:
        actions = st.columns(3)
        with actions[0]:
            if st.button(
                "Confirm capability",
                key=f"confirm_inference_{inferred.evidence_id}",
                type="primary",
                use_container_width=True,
            ):
                _apply_ui_inference_decision(inferred.evidence_id, InferenceDecision.CONFIRM)
        with actions[1]:
            if st.button(
                "Reject",
                key=f"reject_inference_{inferred.evidence_id}",
                use_container_width=True,
            ):
                _apply_ui_inference_decision(inferred.evidence_id, InferenceDecision.REJECT)
        with actions[2]:
            st.caption("No decision yet")
    st.write("")


def _render_capability_review(*, demo: bool = False) -> None:
    profile = _confirmed_profile()
    render_page_header(
        "AI Capability Review" if not demo else "Demo AI Capability Review",
        "Review AI-detected capabilities",
        (
            "Career Navigator found additional capabilities that may be supported by your "
            "experience. Review each one before continuing."
        ),
    )
    render_status_badge("APPROVED", prefix="Base profile")
    confirmed_capabilities = list(
        dict.fromkeys(item.capability for item in profile.approved_evidence_items)
    )
    if confirmed_capabilities:
        render_card(
            "Already confirmed in your profile",
            "AI suggestions matching these capabilities are excluded.",
            items=tuple(confirmed_capabilities),
        )
    if demo:
        render_status_badge(DEMO_LABEL)
        render_state(
            "Synthetic inference",
            "These suggestions and evidence references are fictional demonstration data.",
        )

    status = st.session_state.capability_inference_status
    if status == "NOT_STARTED":
        render_state(
            "Identifying strengths",
            "AI review uses only your confirmed evidence and starts automatically.",
        )
        _run_capability_inference(profile)
        st.rerun()
    elif status == InferenceRunStatus.FAILED.value:
        metadata = st.session_state.capability_inference_metadata or {}
        category = metadata.get("error_category")
        guidance = {
            "ModelUnavailableError": (
                "NVIDIA was temporarily unavailable after the bounded retry. You can retry "
                "without re-entering your profile, or continue using explicit evidence only."
            ),
            "ModelTimeoutError": (
                "NVIDIA did not respond within the bounded timeout. Retry when ready, or "
                "continue using explicit evidence only."
            ),
            "ModelRateLimitError": (
                "NVIDIA temporarily limited the request. Retry later, or continue using "
                "explicit evidence only."
            ),
            "ModelAuthenticationError": (
                "NVIDIA authentication was rejected. Provider configuration must be corrected "
                "before AI capability review can run."
            ),
            "ModelConfigurationError": (
                "The configured AI provider or extraction model is unavailable to the app."
            ),
        }.get(category, st.session_state.capability_inference_error)
        render_state(
            "Capability review unavailable",
            guidance,
            tone="warning",
        )
        if st.button("Retry capability review", type="primary"):
            _run_capability_inference(profile)
            st.rerun()
    elif status == InferenceRunStatus.EMPTY.value:
        render_state(
            "No additional capabilities found",
            "We didn’t identify any additional capabilities beyond the ones you already confirmed.",
        )
    else:
        result = CapabilityInferenceResult.model_validate(
            st.session_state.capability_inference_result
        )
        for proposal in result.inferred_capabilities:
            _render_inference_proposal(profile, proposal, demo=demo)
        if result.limitations:
            render_state("Limitations", " ".join(result.limitations), tone="warning")
        if result.unresolved_areas:
            render_state("Unresolved areas", " ".join(result.unresolved_areas))

    back, _, forward = st.columns([1.5, 2.5, 1.6])
    with back:
        if st.button("Back to Profile Review", use_container_width=True):
            st.session_state.capability_review_active = False
            st.rerun()
    with forward:
        if st.button("Continue to Career Goal", type="primary", use_container_width=True):
            go_to("Goal")


def _render_manual_onboarding() -> None:
    legacy_steps = {
        "Skills": "AI Strength Identification",
        "Strengths": "AI Strength Identification",
        "Experience": "Professional Profile",
    }
    st.session_state.current_profile_step = legacy_steps.get(
        st.session_state.current_profile_step, st.session_state.current_profile_step
    )
    st.session_state.highest_reached_profile_step = legacy_steps.get(
        st.session_state.highest_reached_profile_step,
        st.session_state.highest_reached_profile_step,
    )
    st.session_state.capability_review_active = False
    _render_profile_progress()
    draft = _draft()
    renderers = {
        "About You": _render_about,
        "Professional Profile": _render_experience,
        "Portfolio Projects": _render_projects,
        "Education": _render_education,
        "AI Strength Identification": _render_strengths,
        "Review": _render_review,
    }
    renderers[st.session_state.current_profile_step](draft)


def _render_demo_profile() -> None:
    render_page_header(
        "Demo Profile",
        "Explore a synthetic career profile",
        "This Senior UiPath Developer is fictional demonstration data—not your profile.",
    )
    render_status_badge(DEMO_LABEL)
    st.write("")
    render_card_pair(
        left_title="Current role",
        left_body=CANDIDATE_PROFILE.current_role or "Not provided",
        left_items=("8+ years experience", CANDIDATE_PROFILE.current_location or "Not provided"),
        right_title="Professional summary",
        right_body=CANDIDATE_PROFILE.professional_summary or "No summary provided",
    )
    st.subheader("Confirmed capabilities")
    st.write(" · ".join(CONFIRMED_CAPABILITIES))
    st.subheader("Experience evidence")
    evidence_columns = st.columns(3)
    for index, evidence in enumerate(PROFILE_EVIDENCE):
        with evidence_columns[index % len(evidence_columns)]:
            render_evidence_item(
                evidence.capability, evidence.description, evidence.source_reference
            )
    render_state(
        "Demo mode",
        "These synthetic facts are provided only to demonstrate later workflow screens.",
    )
    back, _, forward = st.columns([1.2, 2.5, 1.5])
    with back:
        if st.button("Back to Home", use_container_width=True):
            go_to("Home")
    with forward:
        if st.button("Continue Demo", type="primary", use_container_width=True):
            st.session_state.profile_confirmed = True
            st.session_state.confirmed_profile = CANDIDATE_PROFILE.model_dump(mode="json")
            st.session_state.capability_review_active = True
            st.session_state.capability_inference_status = InferenceRunStatus.SUCCEEDED.value
            st.session_state.capability_inference_result = DEMO_INFERENCE_RESULT.model_dump(
                mode="json"
            )
            st.rerun()


def render() -> None:
    if st.session_state.profile_input_mode == "demo":
        if st.session_state.capability_review_active:
            _render_capability_review(demo=True)
        else:
            _render_demo_profile()
    else:
        st.session_state.profile_input_mode = "manual"
        _render_manual_onboarding()

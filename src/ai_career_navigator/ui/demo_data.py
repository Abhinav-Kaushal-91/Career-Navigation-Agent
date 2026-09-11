"""Central synthetic scenario for the Activity 3C product shell."""

from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from ai_career_navigator.career import generate_career_plan, synthesize_career_assessment
from ai_career_navigator.domain import (
    ApprovalStatus,
    BridgeOutcome,
    BridgeRoleAssessment,
    CandidateAccessibility,
    CandidateProfile,
    CareerGoal,
    CareerStage,
    ComparisonScope,
    ConfidenceLevel,
    CurrentMarketSnapshot,
    EmployerDiversity,
    EvidenceConfirmationStatus,
    EvidenceItem,
    EvidenceMaturity,
    GapCategory,
    GapItem,
    GapSeverity,
    GoalType,
    MarketConcentration,
    MatchType,
    OpportunityAvailability,
    RequirementCategory,
    RequirementComparison,
    RequirementFrequency,
    RoleAssessment,
    RoleRequirement,
    SourceRecord,
    TimelineAssessment,
    TimelineClassification,
)
from ai_career_navigator.market import (
    AggregatedRequirement,
    MarketRequirementAnalysis,
    MarketRequirementSummary,
    RequirementRunStatus,
)
from ai_career_navigator.profile.inference_schemas import (
    CapabilityInferenceResult,
    InferredCapability,
)
from ai_career_navigator.profile.schemas import (
    AboutYou,
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    ProfileDraft,
    ProjectEntry,
    ProjectStage,
    ProjectType,
)

DEMO_LABEL = "Synthetic demonstration data"
DEMO_DATE = date(2026, 9, 2)
DEMO_DATETIME = datetime(2026, 9, 2, 16, 0, tzinfo=UTC)


def sample_profile_draft() -> ProfileDraft:
    """Fresh editable input only: no approved strengths, goal or canned analysis."""
    return ProfileDraft(
        about=AboutYou(
            current_role="Senior Java Developer",
            years_professional_experience=8,
            current_location="Toronto, Canada",
            career_stage=CareerStage.MID_CAREER,
            career_summary=(
                "SYNTHETIC TEST PROFILE — not real employment history. Senior Java developer "
                "with eight years of experience building and supporting enterprise backend "
                "applications using Java, Spring Boot, REST APIs, PostgreSQL and AWS. "
                "Responsible for production services, automated testing, incident support "
                "and mentoring developers."
            ),
        ),
        core_competencies_text=(
            "Java; Spring Boot; REST API Development; PostgreSQL; SQL Optimization; AWS; "
            "Git; Docker; CI/CD; JUnit; Automated Testing; Production Incident Support; "
            "Code Review; Technical Mentoring"
        ),
        experiences=[
            ExperienceEntry(
                job_title="Senior Java Developer",
                organization="Demo Software Company (fictional)",
                start_date=date(2018, 9, 1),
                current=True,
                location="Toronto, Canada",
                accomplishments=[
                    "Designed and maintained Java and Spring Boot backend services "
                    "used in production.",
                    "Built REST APIs integrating billing and customer-management systems.",
                    "Optimized PostgreSQL queries, reducing average response times by 30%.",
                    "Deployed containerized services to AWS using automated CI/CD pipelines.",
                    "Wrote JUnit integration and unit tests and supported production incidents.",
                    "Mentored two developers and reviewed code and technical designs.",
                ],
            )
        ],
        projects=[
            ProjectEntry(
                name="Order Management API — synthetic test project",
                project_type=ProjectType.PERSONAL,
                delivery_stage=ProjectStage.PROTOTYPE,
                context="Personal portfolio application; not a production employer system.",
                contribution=(
                    "Built an order-management application using Java, Spring Boot and PostgreSQL. "
                    "Added authentication, validation, automated unit and integration tests, "
                    "Docker packaging and API documentation."
                ),
                capabilities_used=[
                    "Java",
                    "Spring Boot",
                    "PostgreSQL",
                    "Docker",
                    "REST APIs",
                    "JUnit",
                ],
                maturity=EvidenceMaturity.DEMONSTRATED,
                outcome=(
                    "Working personal prototype; no production users or commercial impact claimed."
                ),
                measurable_impact="Documented and tested 12 REST endpoints in a local environment.",
            )
        ],
        education=[
            EducationEntry(
                qualification="Bachelor of Science",
                field_of_study="Computer Science",
                institution="Demo University (fictional)",
                completion_year=2018,
            )
        ],
        certifications=[
            CertificationEntry(
                name="Oracle Certified Professional: Java SE 17 Developer — synthetic test entry",
                issuer="Oracle (test data; no real credential claimed)",
                year=2023,
            )
        ],
    )


def demo_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"career-navigator-demo/{name}")


def _evidence(name: str, capability: str, description: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=demo_id(f"evidence/{name}"),
        evidence_type="employment",
        source_type="synthetic profile",
        source_reference="Senior RPA Developer, 2022–Present",
        capability=capability,
        description=description,
        maturity_level=EvidenceMaturity.PRODUCTION,
        confirmation_status=EvidenceConfirmationStatus.EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        approved_by_user=True,
        created_at=DEMO_DATETIME,
    )


PROFILE_EVIDENCE = (
    _evidence("uipath", "UiPath", "Delivered enterprise automation solutions."),
    _evidence(
        "api", "REST APIs", "Built REST integrations between UiPath and enterprise applications."
    ),
    _evidence(
        "support", "Production Support", "Supported live automations and operational recovery."
    ),
    _evidence(
        "solution-design",
        "Solution Design",
        "Designed technical solutions from discovery through production delivery.",
    ),
    _evidence(
        "stakeholder",
        "Stakeholder Collaboration",
        "Led cross-functional discovery and delivery discussions.",
    ),
)

INFERRED_API_EVIDENCE = EvidenceItem(
    evidence_id=demo_id("evidence/inferred-api"),
    evidence_type="inferred capability",
    source_type="synthetic profile inference",
    source_reference="Senior RPA Developer, 2022–Present",
    capability="Enterprise API Integration",
    description="Built REST integrations between UiPath and enterprise applications.",
    maturity_level=EvidenceMaturity.PRODUCTION,
    confirmation_status=EvidenceConfirmationStatus.INFERRED_PENDING,
    confidence=ConfidenceLevel.MODERATE,
    created_at=DEMO_DATETIME,
)

DEMO_INFERENCE_RESULT = CapabilityInferenceResult(
    inferred_capabilities=[
        InferredCapability(
            capability="Enterprise API Integration",
            description="Integration capability across enterprise automation systems.",
            supporting_evidence_ids=[
                PROFILE_EVIDENCE[0].evidence_id,
                PROFILE_EVIDENCE[1].evidence_id,
            ],
            proposed_maturity=EvidenceMaturity.PRODUCTION,
            confidence=ConfidenceLevel.MODERATE,
        )
    ],
    limitations=["This is synthetic inference for product demonstration only."],
    unresolved_areas=[],
)

CANDIDATE_PROFILE = CandidateProfile(
    profile_id=demo_id("profile"),
    career_stage=CareerStage.SENIOR_INDIVIDUAL_CONTRIBUTOR,
    professional_summary=(
        "Enterprise automation specialist with 8+ years of delivery, integration, "
        "and production-support experience."
    ),
    current_role="Senior UiPath Developer",
    current_seniority="Senior",
    current_location="Toronto, Canada",
    evidence_items=[*PROFILE_EVIDENCE, INFERRED_API_EVIDENCE],
    approval_status=ApprovalStatus.APPROVED,
    created_at=DEMO_DATETIME,
    confirmed_at=DEMO_DATETIME,
)

CONFIRMED_CAPABILITIES = (
    "UiPath",
    "REST APIs",
    "C#",
    "Automation Design",
    "Production Support",
    "Stakeholder Collaboration",
)

CAREER_GOAL = CareerGoal(
    goal_id=demo_id("goal"),
    goal_type=GoalType.TARGET_CAREER_PATH,
    target_role="AI Solutions Architect",
    target_timeline_months=24,
    target_location="Toronto, Canada",
    preferred_work_modes=["Hybrid", "Remote"],
    bridge_role_willingness=True,
    approval_status=ApprovalStatus.PENDING,
    created_at=DEMO_DATETIME,
)

SOURCES = tuple(
    SourceRecord(
        source_id=demo_id(f"source/{index}"),
        source_type="synthetic job source",
        title=f"Demo source {index}",
        url=f"https://example.invalid/demo-source-{index}",
        geography="Toronto, Canada",
        retrieval_date=DEMO_DATE,
        limitations=["Placeholder source for UI demonstration only."],
    )
    for index in range(1, 4)
)

REQUIREMENT_FREQUENCIES = (
    ("Python", "COMMON"),
    ("Cloud AI", "COMMON"),
    ("Solution Architecture", "COMMON"),
    ("RAG", "FREQUENT"),
    ("LLM Deployment", "FREQUENT"),
    ("Stakeholder Leadership", "OCCASIONAL"),
)

_DEMO_FREQUENCY_VALUES = {
    "COMMON": 0.75,
    "FREQUENT": 0.45,
    "OCCASIONAL": 0.20,
}

ROLE_REQUIREMENTS = tuple(
    RoleRequirement(
        requirement_id=demo_id(f"requirement/{name}"),
        posting_id=demo_id(f"posting/{index}"),
        category=RequirementCategory.TECHNICAL if index < 5 else RequirementCategory.LEADERSHIP,
        requirement_text=name,
        normalized_capability=name,
        frequency_within_sample=_DEMO_FREQUENCY_VALUES[frequency],
        extraction_confidence=ConfidenceLevel.MODERATE,
    )
    for index, (name, frequency) in enumerate(REQUIREMENT_FREQUENCIES)
)

DEMO_REQUIREMENT_SUMMARY = MarketRequirementSummary(
    target_role="AI Solutions Architect",
    geography="Toronto / Canada",
    source_page_count=15,
    identified_candidate_count=15,
    validated_in_scope_posting_count=15,
    analyzed_posting_count=15,
    exact_title_analyzed_count=6,
    related_title_analyzed_count=9,
    out_of_scope_count=0,
    unclear_geography_count=0,
    irrelevant_title_count=0,
    requirements=[
        AggregatedRequirement(
            category=requirement.category,
            normalized_capability=requirement.normalized_capability or requirement.requirement_text,
            requirement_ids=[requirement.requirement_id],
            exact_title_occurrence_count=round((requirement.frequency_within_sample or 0) * 6),
            related_title_occurrence_count=round((requirement.frequency_within_sample or 0) * 9),
            exact_title_frequency=requirement.frequency_within_sample,
            combined_frequency=requirement.frequency_within_sample or 0,
        )
        for requirement in ROLE_REQUIREMENTS
    ],
    capability_requirements=[
        AggregatedRequirement(
            category=requirement.category,
            normalized_capability=requirement.normalized_capability or requirement.requirement_text,
            requirement_ids=[requirement.requirement_id],
            exact_title_occurrence_count=round((requirement.frequency_within_sample or 0) * 6),
            related_title_occurrence_count=round((requirement.frequency_within_sample or 0) * 9),
            exact_title_frequency=requirement.frequency_within_sample,
            combined_frequency=requirement.frequency_within_sample or 0,
        )
        for requirement in ROLE_REQUIREMENTS
    ],
)

DEMO_REQUIREMENT_ANALYSIS = MarketRequirementAnalysis(
    status=RequirementRunStatus.SUCCEEDED,
    requirements=list(ROLE_REQUIREMENTS),
    summary=DEMO_REQUIREMENT_SUMMARY,
)

RELATED_TITLES = (
    "GenAI Solutions Architect",
    "AI Platform Architect",
    "AI Automation Architect",
    "Cloud AI Architect",
)

MARKET_SNAPSHOT = CurrentMarketSnapshot(
    snapshot_id=demo_id("market-snapshot"),
    target_role="AI Solutions Architect",
    geography="Toronto / Canada",
    search_date=DEMO_DATE,
    exact_title_count=6,
    related_title_count=9,
    validated_posting_count=15,
    distinct_employer_count=11,
    related_titles=list(RELATED_TITLES),
    common_requirements=[item.requirement_id for item in ROLE_REQUIREMENTS],
    opportunity_availability=OpportunityAvailability.STRONG,
    employer_diversity=EmployerDiversity.HIGH,
    market_concentration=MarketConcentration.LOW,
    evidence_confidence=ConfidenceLevel.MODERATE,
    source_ids=[source.source_id for source in SOURCES],
    employer_posting_counts={
        "Demo Employer A": 2,
        "Demo Employer B": 2,
        "Demo Employer C": 2,
        "Demo Employer D": 1,
        "Demo Employer E": 1,
        "Demo Employer F": 1,
        "Demo Employer G": 1,
        "Demo Employer H": 1,
        "Demo Employer I": 1,
        "Demo Employer J": 1,
        "Demo Employer K": 2,
    },
    location_posting_counts={
        "Toronto, Ontario": 7,
        "Vancouver, British Columbia": 3,
        "Remote - Canada": 3,
        "Calgary, Alberta": 2,
    },
    known_employer_posting_count=15,
    largest_employer_posting_count=2,
    top_three_employer_posting_count=6,
    search_query_count=2,
    successful_search_query_count=2,
    content_fetch_count=15,
    successful_content_fetch_count=12,
    duplicate_posting_count=1,
    limitations=["Synthetic UI data; no live search was performed."],
)

STRONG_MATCHES = (
    "REST APIs",
    "Enterprise integration",
    "Solution design",
    "Stakeholder collaboration",
)
TRANSFERABLE_CAPABILITIES = (
    "Automation orchestration",
    "Production support",
    "Technical delivery ownership",
)

_GAP_DETAILS = (
    (
        0,
        GapCategory.SKILL,
        "Python",
        "Python delivery is adjacent but direct applied evidence is still limited.",
        GapSeverity.MODERATE,
        (1,),
    ),
    (
        1,
        GapCategory.SKILL,
        "Cloud AI",
        "No confirmed cloud AI implementation evidence is available.",
        GapSeverity.HIGH,
        (),
    ),
    (
        2,
        GapCategory.LEADERSHIP_SCOPE,
        "Solution Architecture",
        "Solution design transfers, but architecture decision ownership is not confirmed.",
        GapSeverity.MODERATE,
        (1, 3),
    ),
    (
        3,
        GapCategory.EVIDENCE,
        "RAG",
        "No confirmed RAG implementation evidence is available.",
        GapSeverity.HIGH,
        (),
    ),
    (
        4,
        GapCategory.EXPERIENCE,
        "Production LLM delivery",
        "Create credible production-style delivery evidence.",
        GapSeverity.HIGH,
        (2,),
    ),
)

GAPS = tuple(
    GapItem(
        gap_id=demo_id(f"gap/{requirement_index}/{category.value}"),
        requirement_id=ROLE_REQUIREMENTS[requirement_index].requirement_id,
        requirement_ids=[ROLE_REQUIREMENTS[requirement_index].requirement_id],
        comparison_scope=ComparisonScope.EXACT_TARGET,
        requirement_frequency=RequirementFrequency(REQUIREMENT_FREQUENCIES[requirement_index][1]),
        category=category,
        current_evidence_ids=[PROFILE_EVIDENCE[item].evidence_id for item in evidence_indexes],
        target_expectation=title,
        remaining_difference=description,
        severity=severity,
        evidence_needed=description,
        possible_action=f"Build and document evidence for {title}.",
        confidence=ConfidenceLevel.MODERATE,
    )
    for requirement_index, category, title, description, severity, evidence_indexes in _GAP_DETAILS
)

_COMPARISON_SPECS = (
    (MatchType.PARTIAL_MATCH, (1,), "REST API delivery supports adjacent technical fluency."),
    (MatchType.NO_CONFIRMED_MATCH, (), "No confirmed cloud AI evidence."),
    (
        MatchType.TRANSFERABLE_MATCH,
        (1, 3),
        "Solution design and integration delivery transfer to solution architecture.",
    ),
    (MatchType.NO_CONFIRMED_MATCH, (), "No confirmed RAG evidence."),
    (
        MatchType.PARTIAL_MATCH,
        (2,),
        "Production support is relevant, but production LLM delivery is not confirmed.",
    ),
    (
        MatchType.DIRECT_MATCH,
        (4,),
        "Confirmed stakeholder leadership directly matches the requirement.",
    ),
)

COMPARISONS = tuple(
    RequirementComparison(
        comparison_id=demo_id(f"comparison/{index}"),
        requirement_id=ROLE_REQUIREMENTS[index].requirement_id,
        posting_id=ROLE_REQUIREMENTS[index].posting_id,
        comparison_scope=ComparisonScope.EXACT_TARGET,
        evidence_ids=[PROFILE_EVIDENCE[item].evidence_id for item in evidence_indexes],
        candidate_maturity=EvidenceMaturity.PRODUCTION,
        target_maturity=EvidenceMaturity.PRODUCTION,
        match_type=match_type,
        transferable_capability=(
            ", ".join(PROFILE_EVIDENCE[item].capability for item in evidence_indexes)
            if match_type is MatchType.TRANSFERABLE_MATCH
            else None
        ),
        remaining_difference=(
            explanation
            if match_type in {MatchType.PARTIAL_MATCH, MatchType.NO_CONFIRMED_MATCH}
            else None
        ),
        explanation=explanation,
        confidence=ConfidenceLevel.MODERATE,
    )
    for index, (match_type, evidence_indexes, explanation) in enumerate(_COMPARISON_SPECS)
)

ROLE_ASSESSMENT = RoleAssessment(
    role_assessment_id=demo_id("role-assessment"),
    target_role="AI Solutions Architect",
    requirement_comparisons=list(COMPARISONS),
    gaps=list(GAPS),
    candidate_accessibility=CandidateAccessibility.ASPIRATIONAL,
    explanation=(
        "Confirmed evidence directly or transferably supports 2 of 6 requirements; "
        "production AI delivery and architecture ownership evidence are still needed."
    ),
    confidence=ConfidenceLevel.MODERATE,
    source_ids=[source.source_id for source in SOURCES],
)

DEMO_CAREER_SYNTHESIS = synthesize_career_assessment(
    CANDIDATE_PROFILE,
    ROLE_ASSESSMENT,
    DEMO_REQUIREMENT_ANALYSIS,
    None,
)

BRIDGE_ASSESSMENT = BridgeRoleAssessment(
    bridge_assessment_id=demo_id("bridge-assessment"),
    bridge_role="AI Automation Engineer",
    current_strength_overlap=["Automation delivery", "REST APIs", "Enterprise integration"],
    gaps_reduced=[str(gap.gap_id) for gap in GAPS[:2]],
    target_capabilities_gained=["AI delivery", "LLM applications", "Architecture evidence"],
    market_availability_summary="Moderate evidence in this synthetic current-market sample.",
    candidate_accessibility=CandidateAccessibility.NEAR_TERM_TARGET,
    evidence_building_value="HIGH",
    leadership_scope_gain="MODERATE",
    user_constraint_fit="HIGH",
    outcome=BridgeOutcome.RECOMMENDED_BRIDGE,
    explanation=(
        "Strong overlap with automation and integration experience while building "
        "production AI evidence."
    ),
    confidence=ConfidenceLevel.MODERATE,
)

TIMELINE_ASSESSMENT = TimelineAssessment(
    timeline_assessment_id=demo_id("timeline-assessment"),
    requested_months=24,
    classification=TimelineClassification.AGGRESSIVE_BUT_PLAUSIBLE,
    assumptions=[
        "The user can build AI implementation evidence.",
        "A bridge role remains acceptable.",
        "Relevant AI roles remain available.",
    ],
    blocking_gap_ids=[gap.gap_id for gap in GAPS[:3]],
    required_milestones=["Production-style AI system", "Architecture ownership evidence"],
    bridge_role_required=True,
    market_dependencies=["Continued availability of relevant AI and automation roles"],
    confidence=ConfidenceLevel.MODERATE,
    evidence_limitations=["Assessment uses synthetic market evidence."],
)

CAREER_PLAN = generate_career_plan(
    CANDIDATE_PROFILE,
    CAREER_GOAL,
    ROLE_ASSESSMENT,
    [BRIDGE_ASSESSMENT],
    BridgeOutcome.RECOMMENDED_BRIDGE,
    TIMELINE_ASSESSMENT,
    market_confidence=MARKET_SNAPSHOT.evidence_confidence,
    source_ids=[source.source_id for source in SOURCES],
    synthesis=DEMO_CAREER_SYNTHESIS,
).plan.model_copy(update={"plan_id": demo_id("career-plan"), "created_at": DEMO_DATETIME})
PLAN_MILESTONES = tuple(CAREER_PLAN.milestones)

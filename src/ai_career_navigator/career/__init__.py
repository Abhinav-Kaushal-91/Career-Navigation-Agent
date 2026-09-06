"""Career analysis services for active V1 activities."""

from .bridge import assess_bridge_roles
from .comparison import compare_candidate_to_requirements, eligible_candidate_evidence
from .comparison_schemas import (
    CandidateComparisonResult,
    CandidateComparisonStatus,
    TransferabilityAssessment,
)
from .errors import (
    CandidateAnalysisError,
    InsufficientCandidateEvidenceError,
    RequirementComparisonError,
    TransferabilityAssessmentError,
)
from .gap_analysis import assess_candidate_accessibility
from .gap_policy import frequency_band
from .gap_schemas import GapAnalysisResult, GapAnalysisStatus
from .path_schemas import (
    BridgeAnalysisResult,
    BridgeAnalysisStatus,
    TimelineAnalysisResult,
    TimelineAnalysisStatus,
)
from .plan import PlanSynthesisValidationError, generate_career_plan
from .plan_schemas import CareerPlanGenerationResult, PlanGenerationStatus
from .synthesis import CareerSynthesisValidationError, synthesize_career_assessment
from .synthesis_schemas import (
    AdvantageStrengthType,
    CareerAdvantage,
    CareerAssessmentSynthesis,
    CareerGapDimension,
    CareerSynthesisDraft,
    CareerSynthesisStatus,
    DemonstratedStrength,
    GroupedCareerGap,
    TargetAlignment,
    TargetAlignmentType,
    TransferableStrength,
)
from .timeline import assess_timeline

__all__ = [
    "CandidateAnalysisError",
    "BridgeAnalysisResult",
    "BridgeAnalysisStatus",
    "CandidateComparisonResult",
    "CandidateComparisonStatus",
    "GapAnalysisResult",
    "GapAnalysisStatus",
    "CareerPlanGenerationResult",
    "PlanGenerationStatus",
    "PlanSynthesisValidationError",
    "TimelineAnalysisResult",
    "TimelineAnalysisStatus",
    "AdvantageStrengthType",
    "CareerAdvantage",
    "CareerAssessmentSynthesis",
    "CareerGapDimension",
    "CareerSynthesisDraft",
    "CareerSynthesisStatus",
    "CareerSynthesisValidationError",
    "DemonstratedStrength",
    "GroupedCareerGap",
    "TargetAlignment",
    "TargetAlignmentType",
    "TransferableStrength",
    "InsufficientCandidateEvidenceError",
    "RequirementComparisonError",
    "TransferabilityAssessment",
    "TransferabilityAssessmentError",
    "compare_candidate_to_requirements",
    "assess_candidate_accessibility",
    "assess_bridge_roles",
    "assess_timeline",
    "eligible_candidate_evidence",
    "frequency_band",
    "generate_career_plan",
    "synthesize_career_assessment",
]

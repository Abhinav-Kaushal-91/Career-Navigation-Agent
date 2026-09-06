"""Safe errors for candidate-to-market comparison."""


class CandidateAnalysisError(Exception):
    """Base error hidden behind the career-analysis boundary."""


class RequirementComparisonError(CandidateAnalysisError):
    """A requirement could not be compared safely."""


class TransferabilityAssessmentError(RequirementComparisonError):
    """Semantic transferability output was invalid or unsupported."""


class InsufficientCandidateEvidenceError(CandidateAnalysisError):
    """No approved candidate evidence is available for comparison."""

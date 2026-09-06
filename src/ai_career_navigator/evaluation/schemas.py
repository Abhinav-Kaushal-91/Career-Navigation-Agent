"""Typed inputs and outputs for repeatable product evaluations."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EvaluationOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


class GoldenCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(pattern=r"^GOLD-\d{3}$")
    category: str = Field(min_length=1)
    question: str = Field(min_length=1)
    expected_answer: str = Field(min_length=1)
    evaluation_mode: str = Field(min_length=1)
    required_behavior: str = Field(min_length=1)
    automatic_failure_conditions: str = Field(min_length=1)
    priority: str = Field(min_length=1)


class CandidateAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(pattern=r"^GOLD-\d{3}$")
    answer: str


class JudgeDecision(BaseModel):
    """Strict semantic-judge output without hidden reasoning."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=500)
    missing_concepts: list[str] = Field(default_factory=list, max_length=10)
    automatic_failure: bool = False


class CaseEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    category: str
    priority: str
    outcome: EvaluationOutcome
    score: float = Field(ge=0.0, le=1.0)
    grading_method: str
    reason: str
    missing_concepts: list[str] = Field(default_factory=list)


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    error_cases: int = Field(ge=0)
    missing_answers: int = Field(ge=0)
    high_priority_failures: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    threshold_met: bool
    category_pass_rates: dict[str, float]


class EvaluationRun(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: EvaluationSummary
    cases: list[CaseEvaluation]

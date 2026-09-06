"""Safe errors owned by the orchestration boundary."""


class WorkflowError(RuntimeError):
    """Base workflow error safe to classify without leaking provider details."""


class WorkflowInputError(WorkflowError):
    """Confirmed workflow input is missing or invalid."""


class WorkflowReviewError(WorkflowError):
    """Human-review data does not match the interrupted workflow state."""


class WorkflowDependencyError(WorkflowError):
    """A required run-scoped dependency or transient reference is unavailable."""

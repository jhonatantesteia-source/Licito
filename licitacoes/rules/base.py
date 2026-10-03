from abc import ABC, abstractmethod
from typing import List, Optional, Any
from pydantic import BaseModel

class Finding(BaseModel):
    """A detected irregularity or observation."""
    document: str
    finding_text: str
    severity: str  # "low", "medium", "high", "critical"
    rule_violated: str  # Clause or Law Article
    evidence: str    # Literal snippet
    file_path: str
    page: Optional[int] = None
    confidence: float = 1.0  # 1.0 for deterministic, <1.0 for LLM
    suggested_action: str
    status: str = "open" # "open", "confirmed", "discarded"

class RuleResult(BaseModel):
    """Result of a single rule execution."""
    passed: bool
    findings: List[Finding] = []

class BaseRule(ABC):
    """Base class for all validation rules."""

    @abstractmethod
    def evaluate(self, context: Any) -> RuleResult:
        """
        Evaluate a rule against a provided context.
        Context depends on the rule type (e.g., LicitanteContext, ProposalContext).
        """
        pass

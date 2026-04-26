from typing import Literal

from pydantic import BaseModel, Field

from domain.document import DocumentAnchor


class EvidenceSpan(BaseModel):
    text: str
    anchor: DocumentAnchor
    score: float | None = None
    evidence_type: Literal["quote", "summary", "table", "figure_caption"] = "quote"


class GroundedClaim(BaseModel):
    claim: str
    evidences: list[EvidenceSpan] = Field(default_factory=list)
    support_level: Literal["direct", "partial", "weak"] = "direct"


class InferredClaim(BaseModel):
    claim: str
    based_on_evidences: list[EvidenceSpan] = Field(default_factory=list)
    confidence: float | None = None

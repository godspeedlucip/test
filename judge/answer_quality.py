from __future__ import annotations

from pydantic import BaseModel, Field

from domain.evidence import EvidenceSpan
from domain.judge import DimensionScore, JudgeRubric


class AnswerQualityJudgeResult(BaseModel):
    passed: bool
    overall_score: float
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    hallucinated_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


class AnswerQualityJudge:
    def evaluate(
        self,
        *,
        question: str,
        answer: str,
        evidences: list[EvidenceSpan],
        rubric: JudgeRubric,
    ) -> AnswerQualityJudgeResult:
        dims: list[DimensionScore] = []
        base = 0.8 if evidences else 0.4
        for dim in rubric.dimensions or ["correctness", "grounding", "clarity"]:
            score = base
            if dim == "grounding" and not evidences:
                score = 0.2
            if dim == "clarity" and len(answer.split()) > 120:
                score = 0.7
            dims.append(DimensionScore(name=dim, score=score, reason="mock-judge"))
        overall = round(sum(x.score for x in dims) / max(1, len(dims)), 3)
        return AnswerQualityJudgeResult(
            passed=overall >= 0.6,
            overall_score=overall,
            dimension_scores=dims,
            hallucinated_claims=[] if evidences else ["No evidence grounding found"],
            unsupported_claims=[] if evidences else ["Answer lacks explicit support"],
            improvement_suggestions=["Provide direct evidence spans for key claims"],
        )

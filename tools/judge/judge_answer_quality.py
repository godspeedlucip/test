from pydantic import BaseModel, Field

from domain.context import RequestContext
from domain.evidence import EvidenceSpan
from domain.judge import DimensionScore, JudgeRubric
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from judge.answer_quality import AnswerQualityJudge
from tools.base import BaseToolHandler, success_result


class JudgeAnswerQualityInput(BaseModel):
    context: RequestContext
    model: ModelConfig
    prompt: PromptConfig
    runtime: RuntimeConfig | None = None
    question: str
    answer: str
    evidences: list[EvidenceSpan] = Field(default_factory=list)
    rubric: JudgeRubric


class JudgeAnswerQualityOutputData(BaseModel):
    passed: bool
    overall_score: float
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    hallucinated_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


class JudgeAnswerQualityHandler(BaseToolHandler):
    tool_name = "judge_answer_quality"
    input_model = JudgeAnswerQualityInput
    output_model = JudgeAnswerQualityOutputData

    def __init__(self) -> None:
        super().__init__()
        self.judge = AnswerQualityJudge()

    def run(self, payload: JudgeAnswerQualityInput):
        result = self.judge.evaluate(
            question=payload.question,
            answer=payload.answer,
            evidences=payload.evidences,
            rubric=payload.rubric,
        )
        return success_result(
            tool_name=self.tool_name,
            data=JudgeAnswerQualityOutputData.model_validate(result.model_dump()),
        )


judge_answer_quality_tool = JudgeAnswerQualityHandler()

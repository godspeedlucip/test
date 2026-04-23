from pydantic import BaseModel, Field

from domain.context import RequestContext
from domain.judge import JudgeRubric
from domain.runtime import ModelConfig, PromptConfig, RuntimeConfig
from tools.base import BaseToolHandler, success_result


class JudgeAgentTrajectoryInput(BaseModel):
    context: RequestContext
    model: ModelConfig
    prompt: PromptConfig
    runtime: RuntimeConfig | None = None
    user_query: str
    plan: list[str] = Field(default_factory=list)
    execution_steps: list[dict] = Field(default_factory=list)
    final_answer: str | None = None
    rubric: JudgeRubric


class JudgeAgentTrajectoryOutputData(BaseModel):
    passed: bool
    overall_score: float
    tool_selection_score: float
    efficiency_score: float
    grounding_score: float
    failure_points: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


class JudgeAgentTrajectoryHandler(BaseToolHandler):
    tool_name = "judge_agent_trajectory"
    input_model = JudgeAgentTrajectoryInput
    output_model = JudgeAgentTrajectoryOutputData

    def run(self, payload: JudgeAgentTrajectoryInput):
        return success_result(
            tool_name=self.tool_name,
            data=JudgeAgentTrajectoryOutputData(
                passed=True,
                overall_score=0.8,
                tool_selection_score=0.8,
                efficiency_score=0.8,
                grounding_score=0.8,
            ),
        )


judge_agent_trajectory_tool = JudgeAgentTrajectoryHandler()

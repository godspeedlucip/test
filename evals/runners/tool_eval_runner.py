from evals.schemas import EvalRunOutputData


def run_tool_eval() -> EvalRunOutputData:
    return EvalRunOutputData(run_id="mock-tool-eval", total_samples=1, completed_samples=1, metrics={"pass_rate": 1.0})

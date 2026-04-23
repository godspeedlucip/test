from evals.schemas import EvalRunOutputData


def run_workflow_eval() -> EvalRunOutputData:
    return EvalRunOutputData(run_id="mock-workflow-eval", total_samples=1, completed_samples=1, metrics={"pass_rate": 1.0})

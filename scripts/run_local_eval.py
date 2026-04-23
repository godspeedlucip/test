from evals.runners.tool_eval_runner import run_tool_eval
from evals.runners.workflow_eval_runner import run_workflow_eval

print(run_tool_eval().model_dump())
print(run_workflow_eval().model_dump())

from __future__ import annotations

import json

from domain.context import RequestContext
from integrations import get_java_client
from integrations.java_client import RecordFileArtifactRequest
from tools.compute.analyze_table import AnalyzeTableInput, analyze_table_tool
from tools.compute.execute_notebook_template import (
    ExecuteNotebookTemplateInput,
    execute_notebook_template_tool,
)
from tools.compute.execute_python_code import ExecutePythonCodeInput, execute_python_code_tool
from tools.compute.generate_plot import GeneratePlotInput, generate_plot_tool

from graph.nodes.common import run_node


def _record_artifact(ctx: RequestContext, trace_id: str, artifact: dict, artifact_type: str) -> None:
    uri = artifact.get("uri") or artifact.get("path") or str(artifact)
    get_java_client().record_file_artifact(
        RecordFileArtifactRequest(
            task_id=trace_id,
            artifact_uri=str(uri),
            artifact_type=artifact_type,
            metadata={"source": "compute_node"},
            idempotency_key=f"{trace_id}:artifact:{artifact_type}:{uri}",
        )
    )


def _record_artifact_list(ctx: RequestContext, trace_id: str, artifacts: list[dict], artifact_type: str) -> None:
    for item in artifacts:
        _record_artifact(ctx, trace_id, item, artifact_type)


def compute_node(state: dict):
    def _impl(s: dict):
        ctx = RequestContext.model_validate(s.get("context", {"user_id": "anonymous"}))
        trace_id = s.get("trace_id") or ctx.request_id or "unknown"
        artifacts = list(s.get("artifacts", []))
        answer_parts: list[str] = []

        notebook_overrides = s.get("prompt_overrides") or {}
        compute_task = s.get("compute_task") or ""
        notebook_template_path = notebook_overrides.get("notebook_template_path")
        notebook_json = notebook_overrides.get("notebook_json")
        notebook_parameters = notebook_overrides.get("notebook_parameters") or s.get("parameters") or {}
        if isinstance(compute_task, str) and compute_task.startswith("notebook_json:"):
            try:
                notebook_json = json.loads(compute_task.split(":", 1)[1].strip())
            except Exception:
                notebook_json = None
        elif isinstance(compute_task, str) and compute_task.startswith("notebook_template:"):
            notebook_template_path = compute_task.split(":", 1)[1].strip()

        if notebook_template_path or notebook_json:
            notebook_result = execute_notebook_template_tool.execute(
                ExecuteNotebookTemplateInput(
                    context=ctx,
                    template_path=notebook_template_path,
                    notebook_json=notebook_json,
                    parameters=notebook_parameters,
                    timeout_seconds=int(s.get("notebook_timeout_seconds", 20)),
                )
            )
            if not notebook_result.success:
                raise RuntimeError(
                    notebook_result.error.message if notebook_result.error else "execute_notebook_template failed"
                )
            notebook_data = notebook_result.data or {}
            notebook_artifact = notebook_data.get("notebook_artifact")
            artifacts.append({"type": "notebook_execution", "payload": notebook_data})
            _record_artifact_list(
                ctx,
                trace_id,
                notebook_data.get("artifacts", []) or ([notebook_artifact] if notebook_artifact else []),
                "notebook",
            )
            answer_parts.append(f"Notebook executed: cells={notebook_data.get('executed_cells', 0)}")

        if s.get("analysis_code"):
            code_result = execute_python_code_tool.execute(
                ExecutePythonCodeInput(
                    context=ctx,
                    code=s["analysis_code"],
                    timeout_seconds=int(s.get("timeout_seconds", 10)),
                    input_file_uris=[s["table_uri"]] if s.get("table_uri") else [],
                )
            )
            if not code_result.success:
                raise RuntimeError(code_result.error.message if code_result.error else "execute_python_code failed")
            code_data = code_result.data or {}
            artifacts.append({"type": "compute_code", "payload": code_data})
            _record_artifact_list(ctx, trace_id, code_data.get("artifacts", []), "compute-output")
            answer_parts.append(f"Code execution exit_code={code_data.get('exit_code', 0)}")
            if code_data.get("stdout"):
                answer_parts.append(f"stdout:\n{code_data['stdout']}")

        table_uri = s.get("table_uri")
        if table_uri:
            analysis_result = analyze_table_tool.execute(AnalyzeTableInput(context=ctx, table_uri=table_uri))
            if not analysis_result.success:
                raise RuntimeError(analysis_result.error.message if analysis_result.error else "analyze_table failed")
            artifacts.append({"type": "table_analysis", "payload": analysis_result.data})
            _record_artifact_list(ctx, trace_id, analysis_result.data.get("artifacts", []), "table-analysis")
            answer_parts.append(
                f"Table stats: rows={analysis_result.data.get('rows')} columns={analysis_result.data.get('columns')}"
            )

            if s.get("plot_kind") or "plot" in (s.get("user_query") or "").lower():
                plot_result = generate_plot_tool.execute(
                    GeneratePlotInput(
                        context=ctx,
                        table_uri=table_uri,
                        kind=s.get("plot_kind") or "line",
                        x=s.get("plot_x"),
                        y=s.get("plot_y"),
                        title=s.get("plot_title") or "Generated Plot",
                    )
                )
                if plot_result.success:
                    image = plot_result.data.get("image_artifact")
                    artifacts.append({"type": "plot", "payload": image})
                    _record_artifact_list(
                        ctx, trace_id, plot_result.data.get("artifacts", []) or ([image] if image else []), "plot"
                    )
                    answer_parts.append(f"Plot generated: {image.get('path')}")

        if not answer_parts:
            answer_parts.append("Compute node ran but no executable compute input was provided.")

        return {
            "answer": "\n".join(answer_parts),
            "artifacts": artifacts,
        }

    return run_node("compute_node", state, _impl)

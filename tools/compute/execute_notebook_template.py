from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from domain.context import RequestContext
from integrations import get_artifact_store
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result, wrap_exception


class ExecuteNotebookTemplateInput(BaseModel):
    context: RequestContext
    template_path: str | None = None
    notebook_json: dict[str, Any] | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 20

    @model_validator(mode="after")
    def validate_source(self) -> "ExecuteNotebookTemplateInput":
        if (self.template_path is None) == (self.notebook_json is None):
            raise ValueError("Exactly one of template_path or notebook_json must be provided")
        return self


class ExecuteNotebookTemplateOutputData(BaseModel):
    executed: bool
    notebook_artifact: dict[str, str]
    executed_cells: int


class ExecuteNotebookTemplateHandler(BaseToolHandler):
    tool_name = "execute_notebook_template"
    input_model = ExecuteNotebookTemplateInput
    output_model = ExecuteNotebookTemplateOutputData

    def run(self, payload: ExecuteNotebookTemplateInput):
        try:
            if payload.timeout_seconds <= 0:
                raise ValueError("timeout_seconds must be positive")

            artifact_store = get_artifact_store()
            run_id = payload.context.request_id or str(uuid.uuid4())
            artifact_store.ensure_run_dir(run_id)

            if payload.template_path:
                template_path = artifact_store.resolve_input_uri(payload.template_path)
                if not template_path.exists():
                    return failed_result(
                        tool_name=self.tool_name,
                        error=make_tool_error(
                            code="template_not_found",
                            message=f"Template file not found: {payload.template_path}",
                        ),
                    )
                notebook = json.loads(template_path.read_text(encoding="utf-8"))
            else:
                notebook = payload.notebook_json or {}

            cells = notebook.get("cells", [])
            exec_globals: dict[str, Any] = {"params": payload.parameters, "__name__": "__main__"}
            for k, v in payload.parameters.items():
                exec_globals[k] = v

            deadline = time.monotonic() + payload.timeout_seconds

            def _trace(frame, event, arg):  # noqa: ANN001
                if event == "line" and time.monotonic() > deadline:
                    raise TimeoutError(f"Notebook execution timed out after {payload.timeout_seconds} seconds")
                return _trace

            execution_count = 0
            try:
                sys.settrace(_trace)
                for cell in cells:
                    if cell.get("cell_type") != "code":
                        continue
                    source = cell.get("source", [])
                    code = "".join(source) if isinstance(source, list) else str(source)
                    try:
                        exec(code, exec_globals, exec_globals)
                        execution_count += 1
                        cell["execution_count"] = execution_count
                        cell["outputs"] = []
                    except Exception as exc:
                        cell["execution_count"] = execution_count + 1
                        cell["outputs"] = [
                            {"output_type": "error", "ename": exc.__class__.__name__, "evalue": str(exc)}
                        ]
                        artifact = artifact_store.write_text(
                            run_id=run_id,
                            file_name="executed_notebook.ipynb",
                            content=json.dumps(notebook, ensure_ascii=False, indent=2),
                        )
                        return failed_result(
                            tool_name=self.tool_name,
                            error=make_tool_error(
                                code="notebook_cell_failed",
                                message=f"{exc.__class__.__name__}: {exc}",
                                detail={"notebook_artifact": artifact, "executed_cells": execution_count},
                            ),
                        )
            finally:
                sys.settrace(None)

            artifact = artifact_store.write_text(
                run_id=run_id,
                file_name="executed_notebook.ipynb",
                content=json.dumps(notebook, ensure_ascii=False, indent=2),
            )
            return success_result(
                tool_name=self.tool_name,
                data=ExecuteNotebookTemplateOutputData(
                    executed=True,
                    notebook_artifact=artifact,
                    executed_cells=execution_count,
                ),
            )
        except TimeoutError as exc:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(
                    code="notebook_execution_timeout",
                    message=str(exc),
                    detail={"timeout_seconds": payload.timeout_seconds},
                ),
            )
        except ValueError as exc:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="invalid_notebook_input", message=str(exc)),
            )
        except Exception as exc:  # pragma: no cover
            return failed_result(tool_name=self.tool_name, error=wrap_exception(self.tool_name, exc))


execute_notebook_template_tool = ExecuteNotebookTemplateHandler()

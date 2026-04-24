from pathlib import Path
import uuid

from domain.context import RequestContext
from graph.workflows.compute_workflow import build_compute_workflow
from graph.workflows.qa_workflow import build_qa_workflow
from integrations import get_java_client


def _new_tmp_dir() -> Path:
    base = Path.cwd() / ".test_tmp"
    base.mkdir(parents=True, exist_ok=True)
    path = base / str(uuid.uuid4())
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_compute_branch_enters_workflow_and_generates_artifacts():
    tmp_path = _new_tmp_dir()
    table = tmp_path / "sample.csv"
    table.write_text("x,y\n1,2\n2,3\n3,5\n", encoding="utf-8")

    app = build_qa_workflow()
    out = app.invoke(
        {
            "workflow": "qa",
            "user_query": "please analyze table and plot trend",
            "context": RequestContext(user_id="u1", request_id="wf-compute-qa").model_dump(),
            "table_uri": str(table),
            "plot_kind": "line",
            "plot_x": "x",
            "plot_y": "y",
            "enable_judge": False,
        }
    )

    assert out.get("final_answer")
    assert any(s.get("node_name") == "compute_node" and s.get("status") == "succeeded" for s in out.get("execution_steps", []))
    assert any(a.get("type") in {"table_analysis", "plot"} for a in out.get("artifacts", []))
    assert len(get_java_client().artifacts) >= 1


def test_compute_workflow_runs_python_plot_and_notebook():
    tmp_path = _new_tmp_dir()
    table = tmp_path / "sample.csv"
    table.write_text("x,y\n1,2\n2,3\n3,5\n", encoding="utf-8")
    notebook = {
        "cells": [{"cell_type": "code", "source": ["z = params['k'] + 1"]}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    app = build_compute_workflow()
    out = app.invoke(
        {
            "workflow": "compute",
            "user_query": "run compute notebook and chart",
            "context": RequestContext(user_id="u1", request_id="wf-compute-standalone").model_dump(),
            "table_uri": str(table),
            "analysis_code": "print('sum', 1+2)",
            "plot_kind": "line",
            "plot_x": "x",
            "plot_y": "y",
            "prompt_overrides": {
                "notebook_json": notebook,
                "notebook_parameters": {"k": 2},
            },
            "enable_judge": False,
        }
    )
    assert out.get("final_answer")
    assert any(a.get("type") == "compute_code" for a in out.get("artifacts", []))
    assert any(a.get("type") == "notebook_execution" for a in out.get("artifacts", []))
    assert any(a.get("type") == "plot" for a in out.get("artifacts", []))
    assert len(get_java_client().artifacts) >= 1

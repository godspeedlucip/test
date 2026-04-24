from __future__ import annotations

import json
from pathlib import Path
import uuid

import pandas as pd

from domain.context import RequestContext
from tools.compute.analyze_table import AnalyzeTableInput, analyze_table_tool
from tools.compute.execute_notebook_template import ExecuteNotebookTemplateInput, execute_notebook_template_tool
from tools.compute.execute_python_code import ExecutePythonCodeInput, execute_python_code_tool
from tools.compute.generate_plot import GeneratePlotInput, generate_plot_tool


def _ctx() -> RequestContext:
    return RequestContext(user_id="u1", request_id="compute-test")


def _new_tmp_dir() -> Path:
    base = Path.cwd() / ".test_tmp"
    base.mkdir(parents=True, exist_ok=True)
    path = base / str(uuid.uuid4())
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_execute_python_code_runs_with_params():
    result = execute_python_code_tool.execute(
        ExecutePythonCodeInput(
            context=_ctx(),
            code="print('hello', params['name'])",
            parameters={"name": "sandbox"},
            timeout_seconds=5,
        )
    )
    assert result.success
    assert result.data["exit_code"] == 0
    assert "hello sandbox" in result.data["stdout"]


def test_execute_python_code_blocks_unsafe_call():
    result = execute_python_code_tool.execute(
        ExecutePythonCodeInput(context=_ctx(), code="import os\nos.system('echo x')", timeout_seconds=5)
    )
    assert not result.success
    assert result.error is not None
    assert result.error.code == "unsafe_or_invalid_code"


def test_execute_python_code_timeout():
    result = execute_python_code_tool.execute(
        ExecutePythonCodeInput(context=_ctx(), code="while True:\n    pass", timeout_seconds=1)
    )
    assert not result.success
    assert result.error is not None
    assert result.error.code == "execution_timeout"


def test_execute_notebook_template_from_json():
    nb = {
        "cells": [{"cell_type": "code", "source": ["x = value + 1"]}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    result = execute_notebook_template_tool.execute(
        ExecuteNotebookTemplateInput(context=_ctx(), notebook_json=nb, parameters={"value": 2}, timeout_seconds=5)
    )
    assert result.success
    artifact_path = Path(result.data["notebook_artifact"]["path"])
    assert artifact_path.exists()
    assert result.data["artifacts"]
    loaded = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert loaded["cells"][0]["execution_count"] == 1


def test_analyze_table_csv():
    path = _new_tmp_dir() / "sample.csv"
    path.write_text("a,b,c\n1,2,x\n2,,y\n", encoding="utf-8")
    result = analyze_table_tool.execute(AnalyzeTableInput(context=_ctx(), table_uri=str(path)))
    assert result.success
    assert result.data["rows"] == 2
    assert result.data["columns"] == 3
    assert result.data["missing_values"]["b"] == 1
    assert "a" in result.data["numeric_describe"]
    assert "c" in result.data["categorical_top_values"]
    assert result.data["artifacts"]


def test_analyze_table_tsv():
    path = _new_tmp_dir() / "sample.tsv"
    path.write_text("x\ty\n1\t3\n2\t4\n", encoding="utf-8")
    result = analyze_table_tool.execute(AnalyzeTableInput(context=_ctx(), table_uri=str(path)))
    assert result.success
    assert result.data["rows"] == 2


def test_analyze_table_xlsx():
    path = _new_tmp_dir() / "sample.xlsx"
    df = pd.DataFrame({"a": [1, 2], "b": ["u", "v"]})
    df.to_excel(path, index=False)
    result = analyze_table_tool.execute(AnalyzeTableInput(context=_ctx(), table_uri=str(path)))
    assert result.success
    assert result.data["rows"] == 2


def test_generate_plot_success():
    path = _new_tmp_dir() / "plot.csv"
    path.write_text("x,y\n1,2\n2,5\n3,9\n", encoding="utf-8")
    result = generate_plot_tool.execute(
        GeneratePlotInput(context=_ctx(), table_uri=str(path), kind="line", x="x", y="y", title="demo")
    )
    assert result.success
    image_path = Path(result.data["image_artifact"]["path"])
    assert image_path.exists()
    assert result.data["artifacts"]


def test_generate_plot_invalid_column():
    path = _new_tmp_dir() / "plot.csv"
    path.write_text("x,y\n1,2\n", encoding="utf-8")
    result = generate_plot_tool.execute(
        GeneratePlotInput(context=_ctx(), table_uri=str(path), kind="bar", x="x", y="missing")
    )
    assert not result.success
    assert result.error is not None
    assert result.error.code == "invalid_column"

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from domain.context import RequestContext
from integrations import get_artifact_store
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result, wrap_exception


class AnalyzeTableInput(BaseModel):
    context: RequestContext
    table_uri: str


class AnalyzeTableOutputData(BaseModel):
    rows: int
    columns: int
    column_types: dict[str, str]
    missing_values: dict[str, int]
    numeric_describe: dict[str, dict[str, float | None]]
    categorical_top_values: dict[str, dict[str, int]]
    artifacts: list[dict[str, str]] = Field(default_factory=list)


def _load_table(path: Path):
    import pandas as pd  # type: ignore

    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    if ext == ".tsv":
        return pd.read_csv(path, sep="\t")
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported table format: {ext}")


class AnalyzeTableHandler(BaseToolHandler):
    tool_name = "analyze_table"
    input_model = AnalyzeTableInput
    output_model = AnalyzeTableOutputData

    def run(self, payload: AnalyzeTableInput):
        try:
            store = get_artifact_store()
            path = store.resolve_input_uri(payload.table_uri)
            if not path.exists():
                return failed_result(
                    tool_name=self.tool_name,
                    error=make_tool_error(code="table_not_found", message=f"Table not found: {payload.table_uri}"),
                )

            df = _load_table(path)
            column_types = {str(col): str(dtype) for col, dtype in df.dtypes.items()}
            missing_values = {str(col): int(count) for col, count in df.isna().sum().items()}

            numeric_describe: dict[str, dict[str, float | None]] = {}
            numeric_df = df.select_dtypes(include=["number"])
            if not numeric_df.empty:
                describe = numeric_df.describe().to_dict()
                for col, stats in describe.items():
                    numeric_describe[str(col)] = {str(k): (None if v != v else float(v)) for k, v in stats.items()}

            categorical_top_values: dict[str, dict[str, int]] = {}
            categorical_df = df.select_dtypes(exclude=["number"])
            for col in categorical_df.columns:
                top_values = categorical_df[col].astype(str).value_counts(dropna=False).head(5)
                categorical_top_values[str(col)] = {str(k): int(v) for k, v in top_values.items()}

            output = AnalyzeTableOutputData(
                rows=int(df.shape[0]),
                columns=int(df.shape[1]),
                column_types=column_types,
                missing_values=missing_values,
                numeric_describe=numeric_describe,
                categorical_top_values=categorical_top_values,
            )
            run_id = payload.context.request_id or str(uuid.uuid4())
            report_artifact = store.write_text(
                run_id=run_id,
                file_name="table_analysis.json",
                content=json.dumps(output.model_dump(), ensure_ascii=False, indent=2),
            )
            output.artifacts = [report_artifact]
            return success_result(tool_name=self.tool_name, data=output)
        except ValueError as exc:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="invalid_table_input", message=str(exc)),
            )
        except Exception as exc:  # pragma: no cover
            return failed_result(tool_name=self.tool_name, error=wrap_exception(self.tool_name, exc))


analyze_table_tool = AnalyzeTableHandler()

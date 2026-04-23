from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from domain.context import RequestContext
from integrations import get_artifact_store
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result, wrap_exception


class GeneratePlotInput(BaseModel):
    context: RequestContext
    table_uri: str
    kind: Literal["line", "bar", "scatter", "histogram"]
    x: str | None = None
    y: str | None = None
    title: str | None = None


class GeneratePlotOutputData(BaseModel):
    image_artifact: dict[str, str]


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


class GeneratePlotHandler(BaseToolHandler):
    tool_name = "generate_plot"
    input_model = GeneratePlotInput
    output_model = GeneratePlotOutputData

    def run(self, payload: GeneratePlotInput):
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            store = get_artifact_store()
            path = store.resolve_input_uri(payload.table_uri)
            if not path.exists():
                return failed_result(
                    tool_name=self.tool_name,
                    error=make_tool_error(code="table_not_found", message=f"Table not found: {payload.table_uri}"),
                )

            df = _load_table(path)
            if df.empty:
                return failed_result(
                    tool_name=self.tool_name,
                    error=make_tool_error(code="empty_table", message="Cannot plot an empty table"),
                )

            def _require_column(name: str | None, field: str) -> str:
                if not name:
                    raise ValueError(f"{field} is required for {payload.kind}")
                if name not in df.columns:
                    raise KeyError(f"Column not found: {name}")
                return name

            fig, ax = plt.subplots(figsize=(6, 4))
            if payload.kind in {"line", "bar", "scatter"}:
                x_col = _require_column(payload.x, "x")
                y_col = _require_column(payload.y, "y")
                if payload.kind == "line":
                    ax.plot(df[x_col], df[y_col])
                elif payload.kind == "bar":
                    ax.bar(df[x_col], df[y_col])
                else:
                    ax.scatter(df[x_col], df[y_col])
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
            else:
                source_col = payload.y or payload.x
                hist_col = _require_column(source_col, "x or y")
                ax.hist(df[hist_col].dropna())
                ax.set_xlabel(hist_col)
                ax.set_ylabel("count")

            if payload.title:
                ax.set_title(payload.title)
            fig.tight_layout()

            run_id = payload.context.request_id or str(uuid.uuid4())
            run_dir = store.ensure_run_dir(run_id)
            output_path = run_dir / "plot.png"
            fig.savefig(output_path)
            plt.close(fig)

            return success_result(
                tool_name=self.tool_name,
                data=GeneratePlotOutputData(
                    image_artifact={"uri": output_path.resolve().as_uri(), "path": str(output_path.resolve())}
                ),
            )
        except KeyError as exc:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="invalid_column", message=str(exc)),
            )
        except ValueError as exc:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="invalid_plot_input", message=str(exc)),
            )
        except Exception as exc:  # pragma: no cover
            return failed_result(tool_name=self.tool_name, error=wrap_exception(self.tool_name, exc))


generate_plot_tool = GeneratePlotHandler()

from __future__ import annotations

import ast
import builtins
import io
import sys
import time
import traceback
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from domain.context import RequestContext
from integrations import get_artifact_store
from tools.base import BaseToolHandler, failed_result, make_tool_error, success_result, wrap_exception


class ExecutePythonCodeInput(BaseModel):
    context: RequestContext
    code: str
    timeout_seconds: int = 10
    input_file_uris: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExecutePythonCodeOutputData(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    artifacts: list[dict[str, str]] = Field(default_factory=list)
    dataframe_summary: dict[str, Any] | None = None


_BLOCKED_IMPORTS = {"socket", "subprocess", "shutil", "requests", "urllib", "http", "ftplib", "telnetlib"}
_BLOCKED_CALLS = {
    "os.system",
    "os.popen",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.run",
    "socket.socket",
    "socket.create_connection",
    "shutil.rmtree",
}


def _qualname(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualname(node.value)
        if parent is None:
            return None
        return f"{parent}.{node.attr}"
    return None


def _validate_safe_code(code: str) -> None:
    lowered = code.lower()
    raw_denied = ("socket.", "subprocess.", "os.system", "shutil.rmtree")
    for token in raw_denied:
        if token in lowered:
            raise ValueError(f"Unsafe token detected: {token}")

    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BLOCKED_IMPORTS:
                    raise ValueError(f"Unsafe import blocked: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in _BLOCKED_IMPORTS:
                    raise ValueError(f"Unsafe import blocked: {node.module}")
        elif isinstance(node, ast.Call):
            name = _qualname(node.func)
            if name in _BLOCKED_CALLS:
                raise ValueError(f"Unsafe call blocked: {name}")


def _safe_builtins() -> dict[str, Any]:
    allow = [
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "enumerate",
        "Exception",
        "float",
        "int",
        "isinstance",
        "len",
        "list",
        "max",
        "min",
        "print",
        "range",
        "reversed",
        "round",
        "set",
        "sorted",
        "str",
        "sum",
        "tuple",
        "zip",
    ]
    safe = {name: getattr(builtins, name) for name in allow}

    def _safe_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):
        root = name.split(".")[0]
        if root in _BLOCKED_IMPORTS:
            raise ImportError(f"Import blocked in sandbox: {name}")
        return builtins.__import__(name, globals, locals, fromlist, level)

    safe["__import__"] = _safe_import
    return safe


def _install_network_block() -> tuple[Any, Any]:
    try:
        import socket

        original_socket = socket.socket
        original_connect = socket.create_connection

        def _deny_network(*_: Any, **__: Any) -> None:
            raise PermissionError("Network access is disabled in execution sandbox")

        socket.socket = _deny_network  # type: ignore[assignment]
        socket.create_connection = _deny_network  # type: ignore[assignment]
        return original_socket, original_connect
    except Exception:
        return None, None


def _restore_network(original_socket: Any, original_connect: Any) -> None:
    if original_socket is None and original_connect is None:
        return
    import socket

    if original_socket is not None:
        socket.socket = original_socket  # type: ignore[assignment]
    if original_connect is not None:
        socket.create_connection = original_connect  # type: ignore[assignment]


def _df_summary(result_globals: dict[str, Any]) -> dict[str, Any] | None:
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return None

    for key, value in result_globals.items():
        if isinstance(value, pd.DataFrame):
            return {
                "name": key,
                "rows": int(value.shape[0]),
                "columns": int(value.shape[1]),
                "column_names": [str(col) for col in value.columns.tolist()],
            }
    return None


class ExecutePythonCodeHandler(BaseToolHandler):
    tool_name = "execute_python_code"
    input_model = ExecutePythonCodeInput
    output_model = ExecutePythonCodeOutputData

    def run(self, payload: ExecutePythonCodeInput):
        try:
            _validate_safe_code(payload.code)
            if payload.timeout_seconds <= 0:
                raise ValueError("timeout_seconds must be positive")

            artifact_store = get_artifact_store()
            run_id = payload.context.request_id or str(uuid.uuid4())
            run_dir = artifact_store.ensure_run_dir(run_id)

            staged_files: list[str] = []
            for uri in payload.input_file_uris:
                staged = artifact_store.stage_input_file(run_id=run_id, uri_or_path=uri)
                staged_files.append(str(staged))

            globals_dict: dict[str, Any] = {
                "__builtins__": _safe_builtins(),
                "__name__": "__main__",
                "params": payload.parameters,
                "input_files": staged_files,
                "run_dir": str(run_dir),
            }

            before = {str(p.resolve()) for p in Path(run_dir).rglob("*") if p.is_file()}
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            deadline = time.monotonic() + payload.timeout_seconds

            def _trace(frame, event, arg):  # noqa: ANN001
                if event == "line" and time.monotonic() > deadline:
                    raise TimeoutError(f"Execution timed out after {payload.timeout_seconds} seconds")
                return _trace

            original_socket, original_connect = _install_network_block()
            exit_code = 0
            try:
                with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                    sys.settrace(_trace)
                    try:
                        compiled = compile(payload.code, "<sandbox>", "exec")
                        exec(compiled, globals_dict, globals_dict)
                    except TimeoutError:
                        raise
                    except Exception:
                        exit_code = 1
                        traceback.print_exc(file=stderr_buffer)
            finally:
                sys.settrace(None)
                _restore_network(original_socket, original_connect)

            after = {str(p.resolve()) for p in Path(run_dir).rglob("*") if p.is_file()}
            new_files = sorted(path for path in after if path not in before)
            artifacts = [{"uri": Path(path).resolve().as_uri(), "path": path} for path in new_files]

            return success_result(
                tool_name=self.tool_name,
                data=ExecutePythonCodeOutputData(
                    stdout=stdout_buffer.getvalue(),
                    stderr=stderr_buffer.getvalue(),
                    exit_code=exit_code,
                    artifacts=artifacts,
                    dataframe_summary=_df_summary(globals_dict),
                ),
            )
        except TimeoutError as exc:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(
                    code="execution_timeout",
                    message=str(exc),
                    detail={"timeout_seconds": payload.timeout_seconds},
                ),
            )
        except ValueError as exc:
            return failed_result(
                tool_name=self.tool_name,
                error=make_tool_error(code="unsafe_or_invalid_code", message=str(exc)),
            )
        except Exception as exc:  # pragma: no cover
            return failed_result(tool_name=self.tool_name, error=wrap_exception(self.tool_name, exc))


execute_python_code_tool = ExecutePythonCodeHandler()

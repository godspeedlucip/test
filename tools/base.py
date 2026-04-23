from __future__ import annotations

import time
import traceback
import uuid
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from domain.base import ToolError, ToolMeta, ToolResult
from observability.recorder import get_recorder


def make_tool_error(
    *,
    code: str,
    message: str,
    detail: dict[str, Any] | None = None,
    retryable: bool = False,
    error_layer: str = "tool",
) -> ToolError:
    return ToolError(
        code=code,
        message=message,
        detail=detail,
        retryable=retryable,
        error_layer=error_layer,
    )


def wrap_exception(tool_name: str, exc: Exception, error_layer: str = "tool") -> ToolError:
    return make_tool_error(
        code=f"{tool_name}_failed",
        message=str(exc),
        detail={"type": exc.__class__.__name__, "traceback": traceback.format_exc()},
        error_layer=error_layer,
    )


class BaseToolHandler(ABC):
    tool_name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    def __init__(self) -> None:
        self.recorder = get_recorder()

    @abstractmethod
    def run(self, payload: BaseModel) -> ToolResult:
        raise NotImplementedError

    def execute(self, payload: BaseModel | dict[str, Any]) -> ToolResult:
        started_ms = int(time.time() * 1000)
        trace_id = None
        parsed_payload: BaseModel
        if isinstance(payload, dict):
            parsed_payload = self.input_model.model_validate(payload)
        else:
            parsed_payload = payload
        context = getattr(parsed_payload, "context", None)
        if context is not None:
            trace_id = context.request_id or str(uuid.uuid4())
        else:
            trace_id = str(uuid.uuid4())

        started_event = self.recorder.emit(
            event_type="tool_called",
            trace_id=trace_id,
            payload={"tool_name": self.tool_name},
        )
        try:
            result = self.run(parsed_payload)
            duration_ms = int(time.time() * 1000) - started_ms
            if result.meta is None:
                result.meta = ToolMeta(tool_name=self.tool_name)
            result.meta.tool_name = self.tool_name
            result.meta.duration_ms = duration_ms
            result.meta.trace_id = trace_id
            result.meta.parent_span_id = started_event.span_id
            self.recorder.emit(
                event_type="tool_finished",
                trace_id=trace_id,
                parent_span_id=started_event.span_id,
                payload={
                    "tool_name": self.tool_name,
                    "success": result.success,
                    "error_code": result.error.code if result.error else None,
                },
            )
            return result
        except Exception as exc:  # pragma: no cover
            err = wrap_exception(self.tool_name, exc)
            duration_ms = int(time.time() * 1000) - started_ms
            self.recorder.emit(
                event_type="error_raised",
                trace_id=trace_id,
                parent_span_id=started_event.span_id,
                payload={"tool_name": self.tool_name, "error_code": err.code},
            )
            return ToolResult(
                success=False,
                error=err,
                data=None,
                meta=ToolMeta(
                    tool_name=self.tool_name,
                    duration_ms=duration_ms,
                    trace_id=trace_id,
                    parent_span_id=started_event.span_id,
                ),
            )


def success_result(*, tool_name: str, data: BaseModel | dict[str, Any], meta: ToolMeta | None = None) -> ToolResult:
    payload = data.model_dump() if isinstance(data, BaseModel) else data
    return ToolResult(success=True, data=payload, meta=meta or ToolMeta(tool_name=tool_name))


def failed_result(*, tool_name: str, error: ToolError, meta: ToolMeta | None = None) -> ToolResult:
    return ToolResult(success=False, error=error, data=None, meta=meta or ToolMeta(tool_name=tool_name))

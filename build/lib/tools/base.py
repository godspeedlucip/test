from __future__ import annotations

import time
import traceback
import uuid
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from domain.base import ToolError, ToolMeta, ToolResult
from integrations.provider_errors import ProviderFailureError
from observability.emitter import get_emitter
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


def _extract_model_prompt(parsed_payload: BaseModel) -> tuple[str | None, str | None, str | None]:
    model_name: str | None = None
    prompt_name: str | None = None
    prompt_version: str | None = None

    model = getattr(parsed_payload, "model", None)
    if model is not None:
        model_name = getattr(model, "model_name", None) if not isinstance(model, dict) else model.get("model_name")

    prompt = getattr(parsed_payload, "prompt", None)
    if prompt is not None:
        if isinstance(prompt, dict):
            prompt_name = prompt.get("prompt_name")
            prompt_version = prompt.get("prompt_version")
        else:
            prompt_name = getattr(prompt, "prompt_name", None)
            prompt_version = getattr(prompt, "prompt_version", None)
    return model_name, prompt_name, prompt_version


class BaseToolHandler(ABC):
    tool_name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    def __init__(self) -> None:
        self.recorder = get_recorder()
        self.emitter = get_emitter()

    @abstractmethod
    def run(self, payload: BaseModel) -> ToolResult:
        raise NotImplementedError

    def execute(self, payload: BaseModel | dict[str, Any]) -> ToolResult:
        started_ms = int(time.time() * 1000)
        parsed_payload: BaseModel
        if isinstance(payload, dict):
            parsed_payload = self.input_model.model_validate(payload)
        else:
            parsed_payload = payload

        context = getattr(parsed_payload, "context", None)
        trace_id = context.request_id if context is not None and context.request_id else str(uuid.uuid4())
        model_name, prompt_name, prompt_version = _extract_model_prompt(parsed_payload)

        started_event = self.emitter.emit(
            event_type="tool_called",
            trace_id=trace_id,
            payload={
                "tool_name": self.tool_name,
                "model_name": model_name,
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
            },
        )
        try:
            result = self.run(parsed_payload)
            latency_ms = int(time.time() * 1000) - started_ms
            if result.meta is None:
                result.meta = ToolMeta(tool_name=self.tool_name)
            result.meta.tool_name = self.tool_name
            result.meta.duration_ms = latency_ms
            result.meta.latency_ms = latency_ms
            result.meta.trace_id = trace_id
            result.meta.parent_span_id = started_event.span_id
            result.meta.model_name = result.meta.model_name or model_name
            result.meta.prompt_name = result.meta.prompt_name or prompt_name
            result.meta.prompt_version = result.meta.prompt_version or prompt_version
            self.emitter.emit(
                event_type="tool_finished",
                trace_id=trace_id,
                parent_span_id=started_event.span_id,
                payload={
                    "tool_name": self.tool_name,
                    "success": result.success,
                    "error_code": result.error.code if result.error else None,
                    "model_name": result.meta.model_name,
                    "prompt_name": result.meta.prompt_name,
                    "prompt_version": result.meta.prompt_version,
                    "token_usage": result.meta.token_usage,
                    "duration_ms": result.meta.duration_ms,
                    "latency_ms": result.meta.latency_ms,
                },
            )
            return result
        except ProviderFailureError as exc:
            latency_ms = int(time.time() * 1000) - started_ms
            err = exc.tool_error
            self.emitter.emit(
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
                    duration_ms=latency_ms,
                    latency_ms=latency_ms,
                    trace_id=trace_id,
                    parent_span_id=started_event.span_id,
                    model_name=model_name,
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                ),
            )
        except Exception as exc:  # pragma: no cover
            err = wrap_exception(self.tool_name, exc)
            latency_ms = int(time.time() * 1000) - started_ms
            self.emitter.emit(
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
                    duration_ms=latency_ms,
                    latency_ms=latency_ms,
                    trace_id=trace_id,
                    parent_span_id=started_event.span_id,
                    model_name=model_name,
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                ),
            )


def success_result(*, tool_name: str, data: BaseModel | dict[str, Any], meta: ToolMeta | None = None) -> ToolResult:
    payload = data.model_dump() if isinstance(data, BaseModel) else data
    return ToolResult(success=True, data=payload, meta=meta or ToolMeta(tool_name=tool_name))


def failed_result(*, tool_name: str, error: ToolError, meta: ToolMeta | None = None) -> ToolResult:
    return ToolResult(success=False, error=error, data=None, meta=meta or ToolMeta(tool_name=tool_name))

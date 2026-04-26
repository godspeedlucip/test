from __future__ import annotations

import json
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from domain.observability import ExecutionTrace, ObservabilityEvent


class TraceStore(ABC):
    @abstractmethod
    def append(self, event: ObservabilityEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_trace_events(self, trace_id: str) -> list[ObservabilityEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_trace(self, trace_id: str) -> ExecutionTrace | None:
        raise NotImplementedError

    @abstractmethod
    def list_all_events(self) -> list[ObservabilityEvent]:
        raise NotImplementedError

    @abstractmethod
    def aggregate_metrics(
        self,
        *,
        trace_id: str | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError


def _within_window(event: ObservabilityEvent, start_ms: int | None, end_ms: int | None) -> bool:
    if start_ms is not None and event.timestamp_ms < start_ms:
        return False
    if end_ms is not None and event.timestamp_ms > end_ms:
        return False
    return True


def _sum_token_usage(events: list[ObservabilityEvent]) -> dict[str, int]:
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for event in events:
        token_usage = event.payload.get("token_usage")
        if not isinstance(token_usage, dict):
            continue
        usage["prompt_tokens"] += int(token_usage.get("prompt_tokens", 0) or 0)
        usage["completion_tokens"] += int(token_usage.get("completion_tokens", 0) or 0)
        usage["total_tokens"] += int(token_usage.get("total_tokens", 0) or 0)
    if usage["total_tokens"] == 0:
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
    return usage


class InMemoryTraceStore(TraceStore):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[ObservabilityEvent] = []
        self._events_by_trace: dict[str, list[ObservabilityEvent]] = {}
        self._trace_summary: dict[str, ExecutionTrace] = {}
        self._dedupe_keys: set[tuple[str, str, str]] = set()

    def append(self, event: ObservabilityEvent) -> None:
        dedupe_key = (event.trace_id, event.event_type, event.span_id)
        with self._lock:
            if dedupe_key in self._dedupe_keys:
                return
            self._dedupe_keys.add(dedupe_key)
            self._events.append(event)
            self._events_by_trace.setdefault(event.trace_id, []).append(event)
            summary = self._trace_summary.get(event.trace_id)
            if summary is None:
                summary = ExecutionTrace(
                    trace_id=event.trace_id,
                    request_id=event.trace_id,
                    user_query="",
                    started_at_ms=event.timestamp_ms,
                )
                self._trace_summary[event.trace_id] = summary
            summary.ended_at_ms = event.timestamp_ms
            if event.event_type == "request_started":
                summary.started_at_ms = event.timestamp_ms
                if event.payload.get("request_id"):
                    summary.request_id = str(event.payload["request_id"])
                if event.payload.get("user_query"):
                    summary.user_query = str(event.payload["user_query"])
            elif event.event_type == "step_finished":
                summary.total_steps += 1
            elif event.event_type == "tool_called":
                summary.total_tool_calls += 1
            elif event.event_type == "request_finished":
                success = bool(event.payload.get("success", False))
                has_errors = bool(event.payload.get("errors"))
                summary.final_status = "succeeded" if success else ("partial" if not has_errors else "failed")

    def list_trace_events(self, trace_id: str) -> list[ObservabilityEvent]:
        with self._lock:
            return list(self._events_by_trace.get(trace_id, []))

    def get_trace(self, trace_id: str) -> ExecutionTrace | None:
        with self._lock:
            trace = self._trace_summary.get(trace_id)
            return ExecutionTrace.model_validate(trace.model_dump()) if trace is not None else None

    def list_all_events(self) -> list[ObservabilityEvent]:
        with self._lock:
            return list(self._events)

    def aggregate_metrics(
        self,
        *,
        trace_id: str | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> dict[str, Any]:
        events = [e for e in self.list_all_events() if _within_window(e, start_ms, end_ms)]
        if trace_id:
            events = [e for e in events if e.trace_id == trace_id]
        started = [e for e in events if e.event_type == "request_started"]
        finished = [e for e in events if e.event_type == "request_finished"]
        step_finished = [e for e in events if e.event_type == "step_finished"]
        judge_finished = [e for e in events if e.event_type == "judge_finished"]
        tool_finished = [e for e in events if e.event_type == "tool_finished"]
        error_events = [e for e in events if e.event_type == "error_raised"]
        success_finished = [e for e in finished if bool(e.payload.get("success", False))]
        durations = [int(e.payload.get("duration_ms", 0) or 0) for e in step_finished]
        token_usage = _sum_token_usage(tool_finished)

        judge_scores = [
            float(e.payload.get("overall_score"))
            for e in judge_finished
            if isinstance(e.payload.get("overall_score"), (int, float))
        ]
        quality_layer = {
            "judge_events": len(judge_finished),
            "judge_score_avg": round(sum(judge_scores) / len(judge_scores), 4) if judge_scores else None,
            "error_events": len(error_events),
        }
        request_layer = {
            "request_count": len(started),
            "finished_request_count": len(finished),
            "success_rate": round(len(success_finished) / max(1, len(finished)), 4),
        }
        step_layer = {
            "step_count": len(step_finished),
            "avg_step_duration_ms": round(sum(durations) / len(durations), 3) if durations else 0.0,
            "p95_step_duration_ms": sorted(durations)[int(max(0, len(durations) - 1) * 0.95)] if durations else 0,
        }
        cost_layer = {
            "token_usage": token_usage,
            "estimated_cost_usd": round(token_usage["total_tokens"] * 0.000002, 6),
        }
        tool_layer = {
            "tool_call_count": len([e for e in events if e.event_type == "tool_called"]),
            "tool_finished_count": len(tool_finished),
        }
        return {
            "request_layer": request_layer,
            "step_layer": step_layer,
            "quality_layer": quality_layer,
            "cost_layer": cost_layer,
            "tool_layer": tool_layer,
            "trace_id": trace_id,
            "time_window": {"start_ms": start_ms, "end_ms": end_ms},
            # backward compatible flat fields
            "request_count": request_layer["request_count"],
            "finished_request_count": request_layer["finished_request_count"],
            "success_rate": request_layer["success_rate"],
            "avg_step_duration_ms": step_layer["avg_step_duration_ms"],
            "tool_call_count": tool_layer["tool_call_count"],
            "token_usage": cost_layer["token_usage"],
            "estimated_cost": cost_layer["estimated_cost_usd"],
            "judge_score_avg": quality_layer["judge_score_avg"],
            "total_tokens": token_usage["total_tokens"],
            "judge_score": quality_layer["judge_score_avg"],
            "error_count": len(error_events),
        }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._events_by_trace.clear()
            self._trace_summary.clear()
            self._dedupe_keys.clear()


class FileTraceStore(TraceStore):
    def __init__(self, root_dir: str | Path | None = None) -> None:
        self._mem = InMemoryTraceStore()
        base = Path(root_dir or (Path.cwd() / ".artifacts" / "traces"))
        self.root = base.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _trace_path(self, trace_id: str) -> Path:
        return self.root / f"{trace_id}.jsonl"

    def _load_file(self, path: Path) -> list[ObservabilityEvent]:
        parsed: list[ObservabilityEvent] = []
        if not path.exists():
            return parsed
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            parsed.append(ObservabilityEvent.model_validate_json(line))
        return parsed

    def append(self, event: ObservabilityEvent) -> None:
        self._mem.append(event)
        path = self._trace_path(event.trace_id)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump(), ensure_ascii=False) + "\n")

    def list_trace_events(self, trace_id: str) -> list[ObservabilityEvent]:
        events = self._mem.list_trace_events(trace_id)
        if events:
            return events
        loaded = self._load_file(self._trace_path(trace_id))
        for ev in loaded:
            self._mem.append(ev)
        return self._mem.list_trace_events(trace_id)

    def get_trace(self, trace_id: str) -> ExecutionTrace | None:
        self.list_trace_events(trace_id)
        return self._mem.get_trace(trace_id)

    def list_all_events(self) -> list[ObservabilityEvent]:
        current = self._mem.list_all_events()
        if current:
            return current
        for path in self.root.glob("*.jsonl"):
            for event in self._load_file(path):
                self._mem.append(event)
        return self._mem.list_all_events()

    def aggregate_metrics(
        self,
        *,
        trace_id: str | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> dict[str, Any]:
        self.list_all_events()
        return self._mem.aggregate_metrics(trace_id=trace_id, start_ms=start_ms, end_ms=end_ms)

    def clear(self) -> None:
        self._mem.clear()
        for path in self.root.glob("*.jsonl"):
            path.unlink(missing_ok=True)


class HybridTraceStore(TraceStore):
    def __init__(self, stores: list[TraceStore]) -> None:
        self._stores = stores

    def append(self, event: ObservabilityEvent) -> None:
        for store in self._stores:
            store.append(event)

    def list_trace_events(self, trace_id: str) -> list[ObservabilityEvent]:
        return self._stores[0].list_trace_events(trace_id)

    def get_trace(self, trace_id: str) -> ExecutionTrace | None:
        return self._stores[0].get_trace(trace_id)

    def list_all_events(self) -> list[ObservabilityEvent]:
        return self._stores[0].list_all_events()

    def aggregate_metrics(
        self,
        *,
        trace_id: str | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> dict[str, Any]:
        return self._stores[0].aggregate_metrics(trace_id=trace_id, start_ms=start_ms, end_ms=end_ms)

    def clear(self) -> None:
        for store in self._stores:
            store.clear()


trace_store: TraceStore | None = None


def build_trace_store() -> TraceStore:
    mode = os.getenv("TRACE_STORE_PROVIDER", os.getenv("TRACE_STORE_MODE", "memory")).lower()
    if mode in {"real", "local", "file"}:
        return FileTraceStore(root_dir=os.getenv("TRACE_STORE_ROOT"))
    if mode == "hybrid":
        mem = InMemoryTraceStore()
        file_store = FileTraceStore(root_dir=os.getenv("TRACE_STORE_ROOT"))
        return HybridTraceStore([mem, file_store])
    return InMemoryTraceStore()


def get_trace_store() -> TraceStore:
    global trace_store
    if trace_store is None:
        trace_store = build_trace_store()
    return trace_store

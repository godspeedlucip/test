from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error as urlerror
from urllib import request as urlrequest

from integrations.provider_errors import ProviderFailureError


@dataclass
class LLMResponse:
    text: str
    model_name: str
    token_usage: dict[str, int] | None = None
    cost: float | None = None


class BaseLLMClient:
    def answer(self, prompt: str, *, model_name: str | None = None, response_format: str = "text") -> LLMResponse:
        raise NotImplementedError

    def answer_with_fallback(
        self,
        *,
        prompt: str,
        primary_model: str,
        fallback_models: list[str],
        response_format: str = "text",
    ) -> LLMResponse:
        _ = fallback_models
        try:
            return self.answer(prompt, model_name=primary_model, response_format=response_format)
        except ProviderFailureError:
            raise
        except Exception as exc:
            raise ProviderFailureError(
                message="Real provider failed",
                retryable=True,
                error_layer="network",
                detail={"provider": "llm", "model_name": primary_model, "cause": str(exc)},
            ) from exc


class MockLLMClient(BaseLLMClient):
    def __init__(self, model_name: str = "mock-llm-v1") -> None:
        self.model_name = model_name

    @staticmethod
    def _should_fail(model_name: str) -> bool:
        lowered = model_name.lower()
        return lowered.startswith("fail-") or "unavailable" in lowered

    @staticmethod
    def _mock_judge_json(prompt: str) -> str:
        lowered = prompt.lower()
        if "execution_steps" in lowered or "trajectory" in lowered:
            payload = {
                "passed": True,
                "overall_score": 0.82,
                "tool_selection_score": 0.8,
                "efficiency_score": 0.83,
                "grounding_score": 0.84,
                "failure_points": [],
                "improvement_suggestions": ["Keep grounding signals explicit in final answer."],
                "judge_mode": "llm-json",
            }
        else:
            payload = {
                "passed": True,
                "overall_score": 0.8,
                "dimension_scores": [
                    {"name": "correctness", "score": 0.8, "reason": "LLM rubric assessment"},
                    {"name": "grounding", "score": 0.8, "reason": "Evidence mentions present"},
                    {"name": "clarity", "score": 0.8, "reason": "Answer is coherent"},
                ],
                "hallucinated_claims": [],
                "unsupported_claims": [],
                "improvement_suggestions": ["Add explicit evidence spans for critical claims."],
                "judge_mode": "llm-json",
            }
        return json.dumps(payload, ensure_ascii=False)

    def answer(self, prompt: str, *, model_name: str | None = None, response_format: str = "text") -> LLMResponse:
        selected_model = model_name or self.model_name
        if self._should_fail(selected_model):
            raise RuntimeError(f"model unavailable: {selected_model}")
        words = prompt.split()
        if response_format == "json":
            if "force_invalid_json" in prompt.lower():
                text = "{invalid-json"
            else:
                text = self._mock_judge_json(prompt)
        else:
            text = f"[MOCK ANSWER] {' '.join(words[:80])}"
        token_usage = {"prompt_tokens": len(words), "completion_tokens": min(120, len(text.split()))}
        return LLMResponse(text=text, model_name=selected_model, token_usage=token_usage)


class RealLLMClient(BaseLLMClient):
    def __init__(self) -> None:
        self.api_key = os.getenv("LLM_API_KEY")
        self.model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "512"))
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is required for real LLM provider mode")

    def answer(self, prompt: str, *, model_name: str | None = None, response_format: str = "text") -> LLMResponse:
        selected_model = model_name or self.model_name
        payload = {
            "model": selected_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}
        body = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        req = urlrequest.Request(
            url=url,
            method="POST",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlrequest.urlopen(req, timeout=self.timeout_seconds) as resp:
                status = int(resp.getcode() or 200)
                raw = resp.read().decode("utf-8")
        except urlerror.HTTPError as exc:
            status = int(exc.code or 500)
            body = exc.read().decode("utf-8", errors="ignore")
            raise ProviderFailureError(
                message="Real provider failed",
                retryable=status >= 500 or status in {408, 425, 429},
                error_layer="network",
                detail={"provider": "llm", "status_code": status, "body": body[:300]},
            ) from exc
        except (urlerror.URLError, TimeoutError) as exc:
            raise ProviderFailureError(
                message="Real provider failed",
                retryable=True,
                error_layer="network",
                detail={"provider": "llm", "cause": str(exc)},
            ) from exc
        if status < 200 or status >= 300:
            raise ProviderFailureError(
                message="Real provider failed",
                retryable=status >= 500 or status in {408, 425, 429},
                error_layer="network",
                detail={"provider": "llm", "status_code": status},
            )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderFailureError(
                message="Real provider failed",
                retryable=False,
                error_layer="parser",
                detail={"provider": "llm", "cause": "invalid_json"},
            ) from exc
        choices = parsed.get("choices") or []
        if not choices:
            raise ProviderFailureError(
                message="Real provider failed",
                retryable=False,
                error_layer="parser",
                detail={"provider": "llm", "cause": "missing_choices"},
            )
        text = ((choices[0].get("message") or {}).get("content") or "").strip()
        usage_raw = parsed.get("usage") or {}
        token_usage = {
            "prompt_tokens": int(usage_raw.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage_raw.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage_raw.get("total_tokens", 0) or 0),
        }
        return LLMResponse(text=text, model_name=str(parsed.get("model") or selected_model), token_usage=token_usage)


llm_client: BaseLLMClient | None = None


def _runtime_env() -> str:
    return os.getenv("RUNTIME_ENV", os.getenv("APP_ENV", "dev")).lower()


def build_llm_client() -> BaseLLMClient:
    mode = os.getenv("LLM_PROVIDER_MODE", "").lower()
    env = _runtime_env()
    if not mode:
        raise RuntimeError("LLM_PROVIDER_MODE must be explicitly set to 'real' or 'mock'")
    if env == "prod" and mode != "real":
        raise RuntimeError("LLM_PROVIDER_MODE must be 'real' when RUNTIME_ENV=prod")
    if mode not in {"real", "mock"}:
        raise RuntimeError("LLM_PROVIDER_MODE must be 'real' or 'mock'; fallback/hybrid are forbidden")
    if mode == "real":
        return RealLLMClient()
    return MockLLMClient()


def get_llm_client() -> BaseLLMClient:
    global llm_client
    if llm_client is None:
        llm_client = build_llm_client()
    return llm_client

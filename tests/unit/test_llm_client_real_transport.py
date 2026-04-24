import json

import pytest

from integrations import llm_client as llm_client_module
from integrations.llm_client import RealLLMClient


class _FakeResp:
    def __init__(self, body: dict):
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def getcode(self):
        return 200

    def read(self):
        return self._body


def test_real_llm_client_calls_chat_completions(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")

    def _fake_urlopen(req, timeout=30):
        assert req.full_url.endswith("/chat/completions")
        return _FakeResp(
            {
                "model": "gpt-test",
                "choices": [{"message": {"content": "{\"ok\": true}"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    client = RealLLMClient()
    out = client.answer("hello", response_format="json")
    assert out.model_name == "gpt-test"
    assert out.text
    assert out.token_usage["total_tokens"] == 20


def test_prod_mode_requires_real_llm_provider(monkeypatch):
    monkeypatch.setenv("RUNTIME_ENV", "prod")
    monkeypatch.setenv("LLM_PROVIDER_MODE", "mock")
    llm_client_module.llm_client = None
    with pytest.raises(RuntimeError):
        llm_client_module.build_llm_client()

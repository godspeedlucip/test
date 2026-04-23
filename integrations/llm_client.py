from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    model_name: str
    token_usage: dict[str, int]


class MockLLMClient:
    def __init__(self, model_name: str = "mock-llm-v1") -> None:
        self.model_name = model_name

    def answer(self, prompt: str) -> LLMResponse:
        words = prompt.split()
        text = " ".join(words[:80])
        return LLMResponse(
            text=f"[MOCK ANSWER] {text}",
            model_name=self.model_name,
            token_usage={"prompt_tokens": len(words), "completion_tokens": min(80, len(words))},
        )


llm_client = MockLLMClient()


def get_llm_client() -> MockLLMClient:
    return llm_client

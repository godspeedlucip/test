from __future__ import annotations

import hashlib
import math
import os
import re


class BaseEmbeddingClient:
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class DeterministicLocalEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, dimension: int = 64) -> None:
        self.dimension = max(16, dimension)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        tokens = self._tokens(text)
        if not tokens:
            return vec
        for idx, token in enumerate(tokens, start=1):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            pos = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 / math.sqrt(idx)
            vec[pos] += sign * weight
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]


class RealEmbeddingClient(BaseEmbeddingClient):
    def __init__(self) -> None:
        self.api_key = os.getenv("EMBED_API_KEY")
        self.model_name = os.getenv("EMBED_MODEL_NAME", "text-embedding-3-large")

    def embed(self, text: str) -> list[float]:
        if not self.api_key:
            raise RuntimeError("EMBED_API_KEY is required for real embedding provider mode")
        raise RuntimeError("Real embedding transport is not wired in this repository yet")


class HybridEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, primary: BaseEmbeddingClient, fallback: BaseEmbeddingClient) -> None:
        self.primary = primary
        self.fallback = fallback

    def embed(self, text: str) -> list[float]:
        try:
            return self.primary.embed(text)
        except Exception:
            return self.fallback.embed(text)


embed_client: BaseEmbeddingClient | None = None


def build_embed_client() -> BaseEmbeddingClient:
    mode = os.getenv("EMBED_PROVIDER_MODE", os.getenv("EMBED_MODE", "local")).lower()
    if mode == "real":
        return RealEmbeddingClient()
    if mode == "hybrid":
        return HybridEmbeddingClient(primary=RealEmbeddingClient(), fallback=DeterministicLocalEmbeddingClient())
    return DeterministicLocalEmbeddingClient()


def get_embed_client() -> BaseEmbeddingClient:
    global embed_client
    if embed_client is None:
        embed_client = build_embed_client()
    return embed_client

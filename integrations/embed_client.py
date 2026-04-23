class MockEmbeddingClient:
    def embed(self, text: str) -> list[float]:
        size = min(8, max(1, len(text.split())))
        return [float(size)] * 8


embed_client = MockEmbeddingClient()


def get_embed_client() -> MockEmbeddingClient:
    return embed_client

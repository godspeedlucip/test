from __future__ import annotations

from integrations.repository import get_repo


class MockJavaClient:
    def save_paper(self, user_id: str, paper_id: str) -> None:
        repo = get_repo()
        repo.library.setdefault(user_id, [])
        if paper_id not in repo.library[user_id]:
            repo.library[user_id].append(paper_id)


java_client = MockJavaClient()


def get_java_client() -> MockJavaClient:
    return java_client

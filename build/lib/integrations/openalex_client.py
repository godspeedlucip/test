from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from domain.paper import Author, PaperMetadata


SortBy = Literal["relevance", "date", "citations"]


@dataclass
class OpenAlexClientError(Exception):
    message: str
    error_layer: Literal["network", "parser", "tool"] = "tool"
    status_code: int | None = None

    def __str__(self) -> str:
        return self.message


class MockOpenAlexClient:
    def search(
        self,
        query: str,
        *,
        authors: list[str] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        venue: str | None = None,
        top_k: int = 10,
        sort_by: SortBy = "relevance",
        sources: list[str] | None = None,
    ) -> list[PaperMetadata]:
        _ = (authors, year_from, year_to, venue, sort_by, sources)
        return [
            PaperMetadata(
                paper_id=f"oa-{i}",
                title=f"{query} Study {i}",
                authors=[Author(name="Mock Author")],
                abstract=f"Abstract for {query} {i}",
                year=2024,
                venue="MockConf",
                source="openalex",
                pdf_url=f"https://example.org/{i}.pdf",
                citation_count=10 - (i % 10),
            )
            for i in range(1, top_k + 1)
        ]


class RealOpenAlexClient:
    base_url = "https://api.openalex.org/works"

    @staticmethod
    def _build_filter(
        *,
        authors: list[str] | None,
        year_from: int | None,
        year_to: int | None,
        venue: str | None,
    ) -> str | None:
        filters: list[str] = []
        if year_from is not None:
            filters.append(f"from_publication_date:{int(year_from)}-01-01")
        if year_to is not None:
            filters.append(f"to_publication_date:{int(year_to)}-12-31")
        if venue:
            filters.append(f"primary_location.source.display_name.search:{venue}")
        if authors:
            for author in authors:
                if author and author.strip():
                    filters.append(f"authorships.author.display_name.search:{author.strip()}")
        if not filters:
            return None
        return ",".join(filters)

    @staticmethod
    def _sort(sort_by: SortBy) -> str:
        if sort_by == "date":
            return "publication_date:desc"
        if sort_by == "citations":
            return "cited_by_count:desc"
        return "relevance_score:desc"

    @staticmethod
    def _map_work(work: dict) -> PaperMetadata:
        work_id = str(work.get("id") or "")
        paper_id = work_id.rsplit("/", 1)[-1] if work_id else str(work.get("ids", {}).get("openalex", ""))
        if not paper_id:
            raise OpenAlexClientError("missing paper id in OpenAlex work", error_layer="parser")
        title = work.get("title")
        if not title:
            raise OpenAlexClientError(f"missing title for paper {paper_id}", error_layer="parser")
        authors = []
        for auth in work.get("authorships") or []:
            name = ((auth.get("author") or {}).get("display_name") or "").strip()
            if name:
                authors.append(Author(name=name))
        doi = None
        ids = work.get("ids") or {}
        if ids.get("doi"):
            doi = str(ids["doi"]).replace("https://doi.org/", "")
        primary_location = work.get("primary_location") or {}
        pdf_url = (primary_location.get("pdf_url") or "").strip() or None
        venue = ((primary_location.get("source") or {}).get("display_name") or "").strip() or None
        return PaperMetadata(
            paper_id=paper_id,
            title=title,
            authors=authors,
            abstract=work.get("abstract") or None,
            year=work.get("publication_year"),
            venue=venue,
            doi=doi,
            pdf_url=pdf_url,
            source="openalex",
            citation_count=work.get("cited_by_count"),
        )

    def search(
        self,
        query: str,
        *,
        authors: list[str] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        venue: str | None = None,
        top_k: int = 10,
        sort_by: SortBy = "relevance",
        sources: list[str] | None = None,
    ) -> list[PaperMetadata]:
        requested_sources = [s.lower() for s in (sources or ["openalex"])]
        if "openalex" not in requested_sources:
            return []

        params = {
            "search": query,
            "per-page": max(1, min(int(top_k), 50)),
            "sort": self._sort(sort_by),
            "mailto": os.getenv("OPENALEX_MAILTO", "research-agent@example.com"),
        }
        filter_text = self._build_filter(authors=authors, year_from=year_from, year_to=year_to, venue=venue)
        if filter_text:
            params["filter"] = filter_text
        url = f"{self.base_url}?{urlparse.urlencode(params)}"
        timeout_s = float(os.getenv("OPENALEX_TIMEOUT_SECONDS", "10"))
        try:
            req = urlrequest.Request(url=url, method="GET", headers={"Accept": "application/json"})
            with urlrequest.urlopen(req, timeout=timeout_s) as resp:
                status = int(resp.getcode() or 200)
                raw = resp.read().decode("utf-8")
            if status < 200 or status >= 300:
                raise OpenAlexClientError(f"OpenAlex HTTP {status}", error_layer="network", status_code=status)
        except urlerror.HTTPError as exc:
            raise OpenAlexClientError(
                f"OpenAlex HTTP {int(exc.code or 500)}",
                error_layer="network",
                status_code=int(exc.code or 500),
            ) from exc
        except (urlerror.URLError, TimeoutError) as exc:
            raise OpenAlexClientError(f"OpenAlex request failed: {exc}", error_layer="network") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenAlexClientError("OpenAlex response is not valid JSON", error_layer="parser") from exc
        if not isinstance(payload, dict):
            raise OpenAlexClientError("OpenAlex response root must be an object", error_layer="parser")
        results = payload.get("results")
        if not isinstance(results, list):
            raise OpenAlexClientError("OpenAlex response missing results", error_layer="parser")
        papers: list[PaperMetadata] = []
        for work in results:
            if not isinstance(work, dict):
                continue
            papers.append(self._map_work(work))
            if len(papers) >= int(top_k):
                break
        return papers


openalex_client = None


def _runtime_env() -> str:
    return os.getenv("RUNTIME_ENV", os.getenv("APP_ENV", "dev")).lower()


def build_openalex_client():
    mode = os.getenv("ACADEMIC_PROVIDER_MODE", "").lower()
    env = _runtime_env()
    if not mode:
        raise RuntimeError("ACADEMIC_PROVIDER_MODE must be explicitly set to 'real' or 'mock'")
    if env == "prod" and mode != "real":
        raise RuntimeError("ACADEMIC_PROVIDER_MODE must be 'real' when RUNTIME_ENV=prod")
    if mode not in {"real", "mock"}:
        raise RuntimeError("ACADEMIC_PROVIDER_MODE must be 'real' or 'mock'; fallback/hybrid are forbidden")
    if mode == "real":
        return RealOpenAlexClient()
    return MockOpenAlexClient()


def get_openalex_client():
    global openalex_client
    if openalex_client is None:
        openalex_client = build_openalex_client()
    return openalex_client

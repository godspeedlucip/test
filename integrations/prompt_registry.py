from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from domain.runtime import PromptVersionSpec


@dataclass
class LoadedPrompt:
    prompt_name: str
    prompt_version: str
    text: str
    path: str
    is_default: bool
    status: str
    owner: str | None = None
    change_log: str | None = None


class PromptRegistryConfigError(ValueError):
    pass


class FilePromptRegistry:
    def __init__(self, prompts_root: Path | None = None) -> None:
        self.prompts_root = prompts_root or (Path(__file__).resolve().parents[1] / "prompts")
        self.registry_path = self.prompts_root / "registry.json"
        self._index = self._load_registry_index()

    def _load_registry_index(self) -> dict[str, dict[str, PromptVersionSpec]]:
        if not self.registry_path.exists():
            raise PromptRegistryConfigError(f"prompt registry file not found: {self.registry_path}")
        raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        rows = raw.get("prompts")
        if not isinstance(rows, list) or not rows:
            raise PromptRegistryConfigError("prompt registry must contain non-empty 'prompts' list")

        index: dict[str, dict[str, PromptVersionSpec]] = {}
        for row in rows:
            spec = PromptVersionSpec.model_validate(row)
            by_name = index.setdefault(spec.prompt_name, {})
            if spec.version in by_name:
                raise PromptRegistryConfigError(f"duplicate prompt version: {spec.prompt_name}/{spec.version}")
            by_name[spec.version] = spec

        for prompt_name, versions in index.items():
            active_count = len([v for v in versions.values() if v.status == "active"])
            if active_count != 1:
                raise PromptRegistryConfigError(
                    f"{prompt_name} must have exactly one active version, found {active_count}"
                )
            for version in versions.keys():
                prompt_path = self.prompts_root / prompt_name / f"{version}.txt"
                if not prompt_path.exists():
                    raise PromptRegistryConfigError(f"prompt file missing for registry entry: {prompt_name}/{version}")
        return index

    def list_versions(self, prompt_name: str) -> list[str]:
        versions = self._index.get(prompt_name, {})
        return sorted(versions.keys())

    def list_prompts(self) -> list[str]:
        return sorted(self._index.keys())

    def list_active_prompts(self) -> dict[str, str]:
        return {name: self._resolve_default_version(name) for name in self.list_prompts()}

    def _resolve_default_version(self, prompt_name: str) -> str:
        by_name = self._index.get(prompt_name)
        if not by_name:
            raise FileNotFoundError(f"prompt not found: {prompt_name}")
        active = [v.version for v in by_name.values() if v.status == "active"]
        if len(active) != 1:
            raise PromptRegistryConfigError(f"{prompt_name} active version configuration is invalid")
        return active[0]

    def load(self, prompt_name: str, prompt_version: str | None = None) -> LoadedPrompt:
        selected_version = prompt_version or self._resolve_default_version(prompt_name)
        by_name = self._index.get(prompt_name)
        if not by_name:
            raise FileNotFoundError(f"prompt not found: {prompt_name}")
        spec = by_name.get(selected_version)
        if spec is None:
            raise FileNotFoundError(f"prompt version not found in registry: {prompt_name}/{selected_version}")
        if prompt_version is None and spec.status == "deprecated":
            raise PromptRegistryConfigError(f"deprecated prompt cannot be selected as default: {prompt_name}/{selected_version}")

        prompt_path = self.prompts_root / prompt_name / f"{selected_version}.txt"
        text = prompt_path.read_text(encoding="utf-8")
        return LoadedPrompt(
            prompt_name=prompt_name,
            prompt_version=selected_version,
            text=text,
            path=str(prompt_path),
            is_default=prompt_version is None,
            status=spec.status,
            owner=spec.owner,
            change_log=spec.change_log,
        )


prompt_registry = FilePromptRegistry()


def get_prompt_registry() -> FilePromptRegistry:
    return prompt_registry

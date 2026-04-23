from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from integrations.prompt_registry import FilePromptRegistry, PromptRegistryConfigError


def _new_tmp_dir() -> Path:
    base = Path.cwd() / ".test_tmp"
    base.mkdir(parents=True, exist_ok=True)
    path = base / str(uuid.uuid4())
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_prompt(root: Path, name: str, version: str, text: str) -> None:
    p = root / name
    p.mkdir(parents=True, exist_ok=True)
    (p / f"{version}.txt").write_text(text, encoding="utf-8")


def _write_registry(root: Path, rows: list[dict]) -> None:
    (root / "registry.json").write_text(json.dumps({"prompts": rows}, ensure_ascii=False, indent=2), encoding="utf-8")


def test_prompt_registry_selects_active_by_default_and_allows_explicit_deprecated():
    root = _new_tmp_dir()
    _write_prompt(root, "ask_paper", "v1", "old prompt")
    _write_prompt(root, "ask_paper", "v2", "new prompt")
    _write_registry(
        root,
        [
            {"prompt_name": "ask_paper", "version": "v1", "status": "deprecated", "owner": "a", "change_log": "old"},
            {"prompt_name": "ask_paper", "version": "v2", "status": "active", "owner": "b", "change_log": "new"},
        ],
    )
    registry = FilePromptRegistry(prompts_root=root)

    default_loaded = registry.load("ask_paper")
    assert default_loaded.prompt_version == "v2"
    assert default_loaded.status == "active"

    deprecated_loaded = registry.load("ask_paper", "v1")
    assert deprecated_loaded.prompt_version == "v1"
    assert deprecated_loaded.status == "deprecated"


def test_prompt_registry_rejects_illegal_config_without_active():
    root = _new_tmp_dir()
    _write_prompt(root, "related_work", "v1", "content")
    _write_registry(
        root,
        [
            {"prompt_name": "related_work", "version": "v1", "status": "draft", "owner": "x", "change_log": "only draft"}
        ],
    )
    with pytest.raises(PromptRegistryConfigError):
        FilePromptRegistry(prompts_root=root)


def test_prompt_registry_explicit_missing_version_fails():
    root = _new_tmp_dir()
    _write_prompt(root, "compare_papers", "v1", "content")
    _write_registry(
        root,
        [
            {"prompt_name": "compare_papers", "version": "v1", "status": "active", "owner": "x", "change_log": "init"}
        ],
    )
    registry = FilePromptRegistry(prompts_root=root)
    with pytest.raises(FileNotFoundError):
        registry.load("compare_papers", "v9")

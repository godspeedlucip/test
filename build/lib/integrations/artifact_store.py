from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse


class ArtifactStore:
    def __init__(self, root: str | Path | None = None) -> None:
        base = Path(root) if root is not None else Path.cwd() / ".artifacts"
        self.root = base.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def ensure_run_dir(self, run_id: str | None = None) -> Path:
        resolved_run_id = run_id or str(uuid.uuid4())
        run_dir = self.root / resolved_run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_bytes(self, *, run_id: str, file_name: str, content: bytes) -> dict[str, str]:
        run_dir = self.ensure_run_dir(run_id)
        safe_name = Path(file_name).name
        artifact_path = run_dir / safe_name
        artifact_path.write_bytes(content)
        return self._as_ref(artifact_path)

    def write_text(self, *, run_id: str, file_name: str, content: str) -> dict[str, str]:
        return self.write_bytes(run_id=run_id, file_name=file_name, content=content.encode("utf-8"))

    def resolve_input_uri(self, uri_or_path: str) -> Path:
        parsed = urlparse(uri_or_path)
        if parsed.scheme == "file":
            path = Path(parsed.path)
            if not path.is_absolute():
                path = Path("/") / parsed.path.lstrip("/")
            return path.resolve()
        return Path(uri_or_path).expanduser().resolve()

    def stage_input_file(self, *, run_id: str, uri_or_path: str) -> Path:
        source = self.resolve_input_uri(uri_or_path)
        if not source.exists():
            raise FileNotFoundError(f"Input file does not exist: {uri_or_path}")
        run_dir = self.ensure_run_dir(run_id)
        target = run_dir / source.name
        shutil.copy2(source, target)
        return target

    def to_uri(self, path: str | Path) -> str:
        return Path(path).resolve().as_uri()

    def _as_ref(self, path: Path) -> dict[str, str]:
        resolved = path.resolve()
        return {"uri": resolved.as_uri(), "path": str(resolved)}


_store: ArtifactStore | None = None


def get_artifact_store() -> ArtifactStore:
    global _store
    if _store is None:
        _store = ArtifactStore()
    return _store

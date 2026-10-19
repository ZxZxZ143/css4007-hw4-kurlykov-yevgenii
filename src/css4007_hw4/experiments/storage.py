from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def append_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        handle.flush()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def source_digest(root: Path) -> str:
    files = sorted((root / "src/css4007_hw4").rglob("*.py")) + sorted((root / "src/css4007_hw4").rglob("*.json"))
    return json_digest({str(p.relative_to(root)).replace("\\", "/"): digest(p) for p in files})


def git_value(root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True,
                                encoding="utf-8", check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def protocol_commit(root: Path) -> str:
    committed = git_value(root, "show", "HEAD:docs/evaluation_protocol.md")
    actual = (root / "docs/evaluation_protocol.md").read_text(encoding="utf-8").strip()
    if committed != actual:
        raise ValueError("Commit the unchanged evaluation protocol before running experiments.")
    return git_value(root, "log", "-1", "--format=%H", "--", "docs/evaluation_protocol.md") or "unknown"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

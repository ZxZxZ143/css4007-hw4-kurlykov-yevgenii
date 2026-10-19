import json
from pathlib import Path

from css4007_hw4.domain.errors import ToolError
from css4007_hw4.domain.models import Document


def load_corpus(path: Path) -> list[Document]:
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not rows:
            raise ValueError("empty")
        docs = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip()
                                                for k in ("id", "title", "text")):
                raise ValueError("invalid fields")
            if row["id"] in seen:
                raise ValueError("duplicate ID")
            seen.add(row["id"])
            docs.append(Document(row["id"], row["title"], row["text"]))
        return docs
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise ToolError("CORPUS_ERROR", "Corpus is missing, unreadable, empty or malformed.") from exc


def full_corpus(docs: list[Document]) -> str:
    return "\n\n".join(f"[{d.doc_id}] {d.title}\n{d.text}" for d in docs)

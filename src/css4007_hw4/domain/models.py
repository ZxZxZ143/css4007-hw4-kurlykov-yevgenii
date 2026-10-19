from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    text: str


@dataclass(frozen=True)
class Excerpt:
    doc_id: str
    title: str
    chunk_id: str
    text: str
    kind: str
    correction_of: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Question:
    """Only these two fields cross the inference boundary; id is for storage."""
    id: str
    text: str

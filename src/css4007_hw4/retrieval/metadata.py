import re
from dataclasses import dataclass

from css4007_hw4.domain.errors import ToolError
from css4007_hw4.domain.models import Document


@dataclass(frozen=True)
class Metadata:
    kind: str
    district: str | None = None
    targets: tuple[str, ...] = ()


def classify(docs: list[Document]) -> dict[str, Metadata]:
    """Infer profiles and correction links from titles/text, never question data."""
    metadata = {}
    for doc in docs:
        profile = re.match(r"(.+?) district profile\b", doc.title, re.I)
        if "ARCHIVED" in doc.title.upper() or doc.text.upper().startswith("ARCHIVED"):
            metadata[doc.doc_id] = Metadata("archived")
        elif re.search(r"\bcorrection\b", doc.title, re.I) or doc.text.lower().startswith("correction:"):
            metadata[doc.doc_id] = Metadata("correction")
        else:
            metadata[doc.doc_id] = Metadata("profile" if profile else "reference",
                                             profile.group(1) if profile else None)
    for doc in docs:
        if metadata[doc.doc_id].kind != "correction":
            continue
        text = f"{doc.title} {doc.text}"
        profiles = [(d.doc_id, metadata[d.doc_id]) for d in docs if metadata[d.doc_id].kind == "profile"]
        explicit = [did for did, _ in profiles if re.search(rf"\b{re.escape(did)}\b", text)]
        inferred = [did for did, meta in profiles
                    if re.search(rf"\b{re.escape(meta.district or '')}\b", text, re.I)]
        targets = explicit or inferred
        if not targets:
            raise ToolError("CORPUS_ERROR", "A correction cannot be linked to a current profile.")
        metadata[doc.doc_id] = Metadata("correction", targets=tuple(sorted(targets)))
    return metadata

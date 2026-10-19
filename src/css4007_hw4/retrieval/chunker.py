import re

from css4007_hw4.domain.models import Document, Excerpt


def sentences(text: str) -> list[str]:
    """Decimal points are not boundaries; preserve original sentence contents."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text.strip()) if s.strip()]


def chunks(doc: Document, kind: str, correction_of: str | None = None,
           *, sliding: bool = True) -> list[Excerpt]:
    parts = sentences(doc.text)
    result = []
    index = 0
    while index < len(parts):
        end = index + 1
        if end < len(parts) and len(parts[index] + " " + parts[end]) <= 500:
            end += 1
        text = " ".join(parts[index:end])
        # Oversize sentences remain intact internally; lookup rejects them if needed.
        result.append(Excerpt(doc.doc_id, doc.title, f"{doc.doc_id}:s{index + 1}-{end}",
                              text, kind, correction_of))
        index = index + 1 if sliding else end
    return result

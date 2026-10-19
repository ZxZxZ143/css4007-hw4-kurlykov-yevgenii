import re
from difflib import SequenceMatcher

from css4007_hw4.domain.errors import ToolError
from css4007_hw4.domain.models import Document, Excerpt
from css4007_hw4.retrieval.bm25 import BM25, tokens
from css4007_hw4.retrieval.chunker import chunks
from css4007_hw4.retrieval.metadata import classify


class SearchIndex:
    def __init__(self, docs: list[Document]):
        self.metadata = classify(docs)
        self.names = sorted({m.district for m in self.metadata.values() if m.district})
        self.vocabulary = set(re.findall(r"[a-z]+", " ".join(d.text for d in docs).lower()))
        self.normalized_vocabulary = set(tokens(" ".join(d.text for d in docs)))
        self.passages: list[Excerpt] = []
        self.corrections: dict[str, list[Excerpt]] = {}
        for doc in docs:
            meta = self.metadata[doc.doc_id]
            if meta.kind == "archived":
                continue
            if meta.kind == "correction":
                for target in meta.targets:
                    excerpts = chunks(doc, meta.kind, target, sliding=False)
                    self.corrections.setdefault(target, []).extend(excerpts)
                    self.passages.extend(excerpts)
            else:
                self.passages.extend(chunks(doc, meta.kind))
        self.bm25 = BM25([p.text for p in self.passages])

    def entities(self, query: str) -> list[str]:
        words = re.findall(r"[a-z]+", query.lower())
        exact = [n for n in self.names if re.search(rf"\b{re.escape(n)}\b", query, re.I)]
        for word in words:
            if (word in self.vocabulary or set(tokens(word)) & self.normalized_vocabulary
                    or any(word == n.lower() for n in exact)):
                continue
            similar = sorted(((SequenceMatcher(None, word, n.lower()).ratio(), n) for n in self.names),
                             key=lambda x: (-x[0], x[1]))
            if similar and similar[0][0] >= 0.70:
                candidates = [n for score, n in similar if score >= max(0.70, similar[0][0] - 0.10)]
                code = "AMBIGUOUS_ENTITY" if len(candidates) > 1 else "UNKNOWN_ENTITY"
                raise ToolError(code, f"Unrecognized district name '{word}'; use an exact suggested name.", candidates)
        return exact

    def search(self, query: str, top_k: int) -> dict:
        entities = self.entities(query)
        stripped = query
        for entity in entities:
            stripped = re.sub(rf"\b{re.escape(entity)}\b", "", stripped, flags=re.I)
        ranked = []
        for index, passage in enumerate(self.passages):
            meta = self.metadata[passage.doc_id]
            if entities and meta.kind == "profile" and meta.district not in entities:
                continue
            if entities and meta.kind == "correction" and not any(
                self.metadata[target].district in entities for target in meta.targets
            ):
                continue
            score = self.bm25.score(stripped, index)
            if meta.kind == "profile" and meta.district in entities:
                score += 1.0
            if not tokens(stripped) and meta.kind != "profile":
                continue
            if score > 0:
                ranked.append((score, passage))
        ranked.sort(key=lambda x: (-x[0], x[1].doc_id, x[1].chunk_id))
        # Give each explicitly requested district a chance before extra excerpts.
        selected: list[Excerpt] = []
        if len(entities) > 1:
            for entity in entities:
                first = next((p for _, p in ranked if self.metadata[p.doc_id].district == entity), None)
                if first and len(selected) < top_k:
                    selected.append(first)
        for _, passage in ranked:
            if len(selected) >= top_k:
                break
            if passage not in selected:
                selected.append(passage)
        corrections = []
        for passage in selected:
            target = passage.correction_of or passage.doc_id
            for correction in self.corrections.get(target, []):
                if correction not in selected and correction not in corrections:
                    corrections.append(correction)
        all_passages = selected + corrections
        if (len(all_passages) > 10 or sum(len(p.text) for p in all_passages) > 3000
                or any(len(p.text) > 500 for p in all_passages)):
            raise ToolError("CONTEXT_LIMIT_EXCEEDED", "Required evidence cannot fit; narrow the query or reduce top_k.")
        return {"ok": True, "matches": [p.to_dict() for p in selected],
                "corrections": [p.to_dict() for p in corrections],
                "has_more": any(p not in all_passages for _, p in ranked)}

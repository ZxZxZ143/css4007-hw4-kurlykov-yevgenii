from pathlib import Path
from typing import Any

from css4007_hw4.domain.errors import ToolError, error
from css4007_hw4.retrieval.loader import load_corpus
from css4007_hw4.retrieval.search import SearchIndex


class Lookup:
    def __init__(self, corpus_path: Path):
        self.index: SearchIndex | None = None
        self.failure: dict[str, Any] | None = None
        try:
            self.index = SearchIndex(load_corpus(corpus_path))
        except ToolError as exc:
            self.failure = exc.result()
        except Exception:
            self.failure = error("INTERNAL_ERROR", "Corpus index initialization failed.")

    def __call__(self, **arguments: Any) -> dict[str, Any]:
        try:
            query, top_k = arguments.get("query"), arguments.get("top_k", 3)
            if (set(arguments) - {"query", "top_k"} or not isinstance(query, str)
                    or not query.strip() or len(query) > 300 or type(top_k) is not int or not 1 <= top_k <= 5):
                return error("INVALID_ARGUMENTS", "Use nonblank query (1–300 characters) and integer top_k (1–5) only.")
            if self.failure is not None:
                return self.failure
            assert self.index is not None
            return self.index.search(query, top_k)
        except ToolError as exc:
            return exc.result()
        except Exception:
            return error("INTERNAL_ERROR", "Lookup could not complete.")

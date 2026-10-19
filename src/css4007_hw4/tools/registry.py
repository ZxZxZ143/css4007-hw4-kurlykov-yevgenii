from collections.abc import Callable
from pathlib import Path
from typing import Any

from css4007_hw4.tools.calculate import calculate
from css4007_hw4.tools.lookup import Lookup

Tool = Callable[..., dict[str, Any]]


def registry(corpus_path: Path) -> dict[str, Tool]:
    return {"lookup": Lookup(corpus_path), "calculate": calculate}

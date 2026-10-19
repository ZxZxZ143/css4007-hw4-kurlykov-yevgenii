from pathlib import Path

import pytest

from css4007_hw4.tools.lookup import Lookup

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def lookup():
    return Lookup(ROOT / "data/corpus.jsonl")

import subprocess
from pathlib import Path

import pytest

from mog.graph.store import Store
from mog.index.indexer import Indexer

SAMPLE = {
    "src/auth.py": '''
"""Auth helpers."""
import os


def load_key():
    return os.environ["KEY"]


class TokenStore:
    def refresh(self, token):
        return token + "!"


def verify_token(token):
    store = TokenStore()
    key = load_key()
    return store.refresh(token) and key
''',
    "src/util.py": '''
def helper(x):
    return x * 2
''',
    "tests/test_auth.py": '''
from src.auth import verify_token


def test_verify_token():
    assert verify_token("a")
''',
    "README.md": "# sample\n\nnot code, but indexable as a file node.\n",
}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for rel, body in SAMPLE.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=False)
    return tmp_path


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "db" / "graph.db")


@pytest.fixture
def indexed(repo: Path):
    store = Store(repo / ".mog" / "graph.db")
    stats = Indexer(repo, store).run()
    yield repo, store, stats
    store.close()

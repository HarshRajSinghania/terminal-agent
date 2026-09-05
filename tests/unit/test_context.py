"""Unit tests for deterministic repository context engine and ranker."""

from pathlib import Path
from terminal_agent.context.engine import RepositoryContextEngine
from terminal_agent.context.ranker import DeterministicRanker, tokenize


def test_tokenizer():
    tokens = tokenize("validateJwtToken_v2")
    assert "validate" in tokens
    assert "jwt" in tokens
    assert "token" in tokens
    assert "v2" in tokens


def test_deterministic_ranker(tmp_path: Path):
    auth_file = tmp_path / "auth.py"
    auth_file.write_text("def validate_token(jwt_str):\n    return True\n", encoding="utf-8")

    utils_file = tmp_path / "utils.py"
    utils_file.write_text("def format_date():\n    return 'today'\n", encoding="utf-8")

    query_tokens = ["jwt", "token"]
    score_auth, reason_auth = DeterministicRanker.score_file(auth_file, auth_file.read_text(), query_tokens, tmp_path)
    score_utils, reason_utils = DeterministicRanker.score_file(utils_file, utils_file.read_text(), query_tokens, tmp_path)

    assert score_auth > score_utils
    assert "symbols" in reason_auth or "path" in reason_auth or "term" in reason_auth


def test_repository_context_engine(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_ok(): pass", encoding="utf-8")

    engine = RepositoryContextEngine(tmp_path)
    tree = engine.build_tree_summary()
    assert "src/" in tree
    assert "main.py" in tree

    context = engine.build_initial_context("Fix main function")
    assert "DIRECTORY STRUCTURE" in context


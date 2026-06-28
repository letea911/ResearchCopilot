"""Test CLI commands via click's test runner."""
import pytest
from click.testing import CliRunner
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_context():
    """Mock the entire application context."""
    return {
        "meta_store": AsyncMock(),
        "vector_store": AsyncMock(),
        "file_store": MagicMock(),
        "pipeline": AsyncMock(),
        "chat": AsyncMock(),
        "search": AsyncMock(),
        "summarize": AsyncMock(),
    }


def test_cli_help(runner):
    """CLI should show help."""
    from cli.main import cli
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "ResearchCopilot" in result.output
    assert "ingest" in result.output
    assert "ask" in result.output
    assert "search" in result.output
    assert "summarize" in result.output


def test_ingest_requires_path(runner):
    """ingest command requires a path argument."""
    from cli.main import cli
    result = runner.invoke(cli, ["ingest"])
    assert result.exit_code != 0  # missing argument


def test_ask_requires_question(runner):
    """ask command requires a question."""
    from cli.main import cli
    result = runner.invoke(cli, ["ask"])
    assert result.exit_code != 0


def test_search_requires_query(runner):
    """search command requires a query."""
    from cli.main import cli
    result = runner.invoke(cli, ["search"])
    assert result.exit_code != 0


def test_summarize_requires_document_id(runner):
    """summarize command requires a document_id."""
    from cli.main import cli
    result = runner.invoke(cli, ["summarize"])
    assert result.exit_code != 0


def test_list_command_help(runner):
    """list-docs command help should work."""
    from cli.main import cli
    with patch("cli.main._init_stores", lambda x: None):
        with patch("cli.main._build_context", return_value={
            "meta_store": AsyncMock(),
            "vector_store": AsyncMock(),
            "file_store": MagicMock(),
            "pipeline": AsyncMock(),
            "chat": AsyncMock(),
            "search": AsyncMock(),
            "summarize": AsyncMock(),
        }):
            result = runner.invoke(cli, ["list-docs", "--help"])
            assert result.exit_code == 0


def test_status_command_help(runner):
    """status command help should work."""
    from cli.main import cli
    with patch("cli.main._init_stores", lambda x: None):
        with patch("cli.main._build_context", return_value={
            "meta_store": AsyncMock(),
            "vector_store": AsyncMock(),
            "file_store": MagicMock(),
            "pipeline": AsyncMock(),
            "chat": AsyncMock(),
            "search": AsyncMock(),
            "summarize": AsyncMock(),
        }):
            result = runner.invoke(cli, ["status", "--help"])
            assert result.exit_code == 0

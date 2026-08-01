"""
Shared pytest fixtures for the myAgent test suite.

Provides:
- Execution mode isolation (defaults to dry_run, tests opt into real)
- Isolated temporary SQLite database
- LLM mocking via unittest.mock.AsyncMock
"""
import os
from unittest import mock
import pytest


# ──────────────────────────────────────────────────────────────────────
# Execution mode safety
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _safe_execution_mode(monkeypatch):
    """
    Every test runs in DRY_RUN by default.
    Tests that need REAL mode must explicitly set EXECUTION_MODE=real
    via monkeypatch or by using the `real_mode` fixture.
    """
    monkeypatch.setenv("EXECUTION_MODE", "dry_run")


@pytest.fixture
def real_mode(monkeypatch):
    """Opt-in fixture: switch to REAL execution mode for this test."""
    monkeypatch.setenv("EXECUTION_MODE", "real")


# ──────────────────────────────────────────────────────────────────────
# Isolated SQLite database
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def test_db(monkeypatch, tmp_path):
    """
    Create a fresh, isolated SQLite database per test.
    Automatically patches DB_PATH so all get_db_connection() calls
    use this temporary file.
    """
    db_path = str(tmp_path / "test_home_agent.db")
    monkeypatch.setattr("backend.app.storage.db.DB_PATH", db_path)

    from backend.app.storage.db import init_db
    init_db()

    yield db_path

    # Cleanup: remove the temp database
    try:
        os.remove(db_path)
    except OSError:
        pass


# ──────────────────────────────────────────────────────────────────────
# LLM mocking — uses unittest.mock.AsyncMock
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_llm():
    """
    Patch chat_with_ollama at all modules that import it.
    All patches share a single AsyncMock so setting return_value on it
    affects all call sites uniformly.

    Usage:
        def test_something(mock_llm):
            mock_llm.return_value = {"message": {"content": '{"fact_ids": [1]}'}}
            # ... test code ...
            assert mock_llm.called
    """
    import contextlib

    shared_mock = mock.AsyncMock()
    shared_mock.return_value = {"message": {"content": "{}"}}

    patches = [
        # Source module
        "backend.app.agent.llm.chat",
        # Modules that import chat_with_ollama at module level
        "backend.app.agent.orchestrator.chat",
        "backend.app.agent.scheduled_tasks.chat_with_ollama",
        "backend.app.memory.fact_extractor.chat_with_ollama",
        "backend.app.memory.relation_builder.chat_with_ollama",
        # memory_service imports inline, so source patch handles it
    ]
    with contextlib.ExitStack() as stack:
        for target in patches:
            stack.enter_context(mock.patch(target, shared_mock))
        yield shared_mock


# ──────────────────────────────────────────────────────────────────────
# API test client
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def api_client(monkeypatch):
    """
    FastAPI TestClient pre-configured with a test API key.
    Use for testing API endpoints with authentication.
    """
    monkeypatch.setenv("HOME_AGENT_API_KEY", "test-api-key-for-pytest")
    from fastapi.testclient import TestClient
    from backend.app.main import app
    return TestClient(app)


@pytest.fixture
def api_headers():
    """Default headers with valid API key for test requests."""
    return {"X-API-Key": "test-api-key-for-pytest"}


@pytest.fixture
def api_headers_invalid():
    """Headers with invalid API key for testing auth rejection."""
    return {"X-API-Key": "wrong-key"}

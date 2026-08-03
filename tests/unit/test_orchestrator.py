"""Regression tests for issue #44: orchestrator silently swallowed tool exceptions.

The plan-execute loop in agent/orchestrator.py used to wrap each tool call in
a broad except Exception that logged the failure and stuffed an
{"error": ..., "success": False} dict into the same results mapping a
successful tool would populate, with nothing at the top level of run()'s
return value to distinguish "everything succeeded" from "a tool silently
blew up".

The fix adds a top-level "success" flag and "failed_tools" list to run()'s
return value, populated from a `failed_tools` list tracked alongside
`results` in the plan-execute loop (see orchestrator.py:53-77). These tests
cover: a single failing tool, a full success, partial failure, total
failure, an empty plan, cache hits, and session persistence.
"""

from typing import TYPE_CHECKING, cast

import pytest

from agent.memory.context_manager import ContextManager
from agent.orchestrator import Orchestrator
from agent.tools.base import BaseTool, ToolResult

if TYPE_CHECKING:
    from agent.memory.session_store import SessionStore


class AlwaysFailsTool(BaseTool):
    """A tool that always raises, simulating a broken external dependency."""

    def __init__(self, name: str = "tech_detector") -> None:
        self.name = name
        self.description = "stub"

    def execute(self, input_data: dict) -> ToolResult:
        raise RuntimeError("simulated tool failure")


class AlwaysSucceedsTool(BaseTool):
    """A tool that always returns a fixed successful result."""

    def __init__(self, name: str = "tech_detector") -> None:
        self.name = name
        self.description = "stub"

    def execute(self, input_data: dict) -> ToolResult:
        return ToolResult(success=True, data={"detected": ["python"]})


@pytest.mark.unit
def test_orchestrator_surfaces_tool_failure() -> None:
    """A failing tool call must be surfaced, not silently absorbed.

    Reproduces issue #44: `run()` used to catch the exception in the
    plan-execute loop and return a result dict that looked the same shape
    as a success, so callers had no reliable signal that anything went
    wrong.
    """
    orchestrator = Orchestrator(tools={"tech_detector": AlwaysFailsTool()})

    result = orchestrator.run(
        profile_id="test-profile",
        profile_data={"files": ["main.py"]},
    )

    assert result["success"] is False
    assert "tech_detector" in result["failed_tools"]


@pytest.mark.unit
def test_orchestrator_reports_success_when_all_tools_pass() -> None:
    """A fully-successful run reports success=True and an empty failed_tools list."""
    orchestrator = Orchestrator(
        tools={
            "tech_detector": AlwaysSucceedsTool(name="tech_detector"),
            "market_analyzer": AlwaysSucceedsTool(name="market_analyzer"),
        }
    )

    result = orchestrator.run(
        profile_id="test-profile",
        profile_data={"files": ["main.py"]},
    )

    assert result["success"] is True
    assert result["failed_tools"] == []
    assert result["tool_results"]["tech_detector"] == {"detected": ["python"]}


@pytest.mark.unit
def test_orchestrator_partial_failure_reports_failed_tools() -> None:
    """One tool failing must not corrupt or hide another tool's successful result."""
    orchestrator = Orchestrator(
        tools={
            "tech_detector": AlwaysSucceedsTool(name="tech_detector"),
            "readme_scorer": AlwaysFailsTool(name="readme_scorer"),
            "market_analyzer": AlwaysSucceedsTool(name="market_analyzer"),
        }
    )

    result = orchestrator.run(
        profile_id="test-profile",
        profile_data={"files": ["main.py"], "readme_content": "# Hello"},
    )

    assert result["success"] is False
    assert result["failed_tools"] == ["readme_scorer"]
    assert result["tool_results"]["tech_detector"] == {"detected": ["python"]}
    assert result["tool_results"]["readme_scorer"]["success"] is False


@pytest.mark.unit
def test_orchestrator_all_tools_fail() -> None:
    """When every tool in the plan fails, all of them are named in failed_tools."""
    orchestrator = Orchestrator(
        tools={
            "tech_detector": AlwaysFailsTool(name="tech_detector"),
            "readme_scorer": AlwaysFailsTool(name="readme_scorer"),
            "market_analyzer": AlwaysFailsTool(name="market_analyzer"),
        }
    )

    result = orchestrator.run(
        profile_id="test-profile",
        profile_data={"files": ["main.py"], "readme_content": "# Hello"},
    )

    assert result["success"] is False
    assert set(result["failed_tools"]) == {"tech_detector", "readme_scorer", "market_analyzer"}


@pytest.mark.unit
def test_orchestrator_empty_plan_reports_success() -> None:
    """An empty plan (no tool-triggering data) must not be reported as a failure."""
    orchestrator = Orchestrator(tools={})

    result = orchestrator.run(profile_id="test-profile", profile_data={})

    assert result["success"] is True
    assert result["failed_tools"] == []
    assert result["tool_results"] == {}


@pytest.mark.unit
def test_orchestrator_cache_hit_not_misreported_as_failure() -> None:
    """A cached tool result must not be flagged as a failure just because it
    skipped the try/except in _execute_tool."""
    tool = AlwaysSucceedsTool(name="tech_detector")
    orchestrator = Orchestrator(
        tools={
            "tech_detector": tool,
            "market_analyzer": AlwaysSucceedsTool(name="market_analyzer"),
        }
    )

    profile_data = {"files": ["main.py"]}
    input_hash = ContextManager.hash_input({"files": ["main.py"]})
    orchestrator.context_manager.store_tool_result(
        "tech_detector", input_hash, ToolResult(success=True, data={"detected": ["python"]})
    )

    result = orchestrator.run(profile_id="test-profile", profile_data=profile_data)

    assert result["success"] is True
    assert result["failed_tools"] == []


@pytest.mark.unit
def test_orchestrator_persists_failed_tools_to_session_store() -> None:
    """Failure state must survive a session_store round trip like success state does."""

    class FakeSessionStore:
        def __init__(self) -> None:
            self.saved: dict | None = None

        def get(self, profile_id: str) -> dict | None:
            return None

        def set(self, profile_id: str, state: dict) -> None:
            self.saved = state

    session_store = FakeSessionStore()
    orchestrator = Orchestrator(
        tools={"tech_detector": AlwaysFailsTool()},
        session_store=cast("SessionStore", session_store),
    )

    orchestrator.run(profile_id="test-profile", profile_data={"files": ["main.py"]})

    assert session_store.saved is not None
    assert session_store.saved["tech_detector"]["success"] is False

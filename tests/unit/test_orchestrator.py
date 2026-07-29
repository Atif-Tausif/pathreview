"""Reproduction test for issue #44: orchestrator silently swallows tool exceptions.

The plan-execute loop in agent/orchestrator.py wraps each tool call in a
broad except Exception (orchestrator.py:60-62) that logs the failure and
stuffs an {"error": ..., "success": False} dict into the same results
mapping a successful tool would populate. Nothing forces the caller of
Orchestrator.run() to notice the failure - the top-level return value
looks identical in shape whether every tool succeeded or one silently
blew up.

This test reproduces that: a tool that always raises should make the
overall run distinguishable from a fully-successful run, without the
caller having to manually inspect every entry in tool_results for a
success key. Today it isn't - run() returns a normally-shaped result
dict with no top-level indication anything failed, so this test
currently fails.
"""

import pytest

from agent.orchestrator import Orchestrator
from agent.tools.base import BaseTool, ToolResult


class AlwaysFailsTool(BaseTool):
    """A tool that always raises, simulating a broken external dependency."""

    name = "tech_detector"
    description = "stub"

    def execute(self, input_data: dict) -> ToolResult:
        raise RuntimeError("simulated tool failure")


@pytest.mark.unit
def test_orchestrator_surfaces_tool_failure() -> None:
    """A failing tool call must be surfaced, not silently absorbed.

    Reproduces issue #44: currently `run()` catches the exception in the
    plan-execute loop (orchestrator.py:60) and returns a result dict that
    looks the same shape as a success, so callers have no reliable signal
    that anything went wrong.
    """
    orchestrator = Orchestrator(tools={"tech_detector": AlwaysFailsTool()})

    result = orchestrator.run(
        profile_id="test-profile",
        profile_data={"files": ["main.py"]},
    )

    # There should be some unambiguous, top-level indication that the run
    # had a failure - e.g. a `success` flag, or the raised exception
    # propagating out of `run()` entirely. Today, neither happens: `run()`
    # returns normally with `success` absent and the failure buried inside
    # `tool_results["tech_detector"]`.
    assert result.get("success") is False, (
        "orchestrator.run() should indicate overall failure when a tool "
        f"raises, but returned: {result}"
    )

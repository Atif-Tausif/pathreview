## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/44

**Issue title:** Orchestrator catches all exceptions from tool calls and continues without logging the failure

**Tier:** [ ] Tier 1  [x] Tier 2  [ ] Tier 3

**Problem summary:**
The plan-execute loop in the agent orchestrator wraps tool calls in a broad `except Exception` handler that swallows any failure without logging it. When a tool call fails partway through a run, the orchestrator just moves on as if nothing happened, so the resulting review comes out with missing sections and the user gets no indication that anything went wrong. This affects `agent/orchestrator.py` and `agent/error_handling.py`. A successful fix would make tool failures visible — logged with enough detail to debug, and surfaced to the user or calling code — instead of failing silently and producing incomplete output.

**Branch name:** fix/44-orchestrator-silent-tool-exceptions

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [ ] Issue added to cohort ledger

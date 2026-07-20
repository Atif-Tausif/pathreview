## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/44

**Issue title:** Orchestrator catches all exceptions from tool calls and continues without logging the failure

**Tier:** [ ] Tier 1  [x] Tier 2  [ ] Tier 3

**Why I chose this issue:**
Tier 2 fits where I am right now: I haven't contributed to an open-source project before, but I have worked in large, unfamiliar codebases before, so tracing a bug across two cooperating modules (`orchestrator.py`'s plan-execute loop and `error_handling.py`'s retry decorator) is a reasonable stretch without being a leap into full-system territory. I also specifically wanted an issue touching the agent system rather than ingestion or the frontend, and this is squarely that. Before claiming it, I checked scope: the issue names exactly two files, has zero existing comments/claims, and — I confirmed by tracing call sites — `Orchestrator` isn't wired into the live review pipeline yet (the API currently calls a hardcoded stub instead), which means my fix stays contained to the module itself and its first unit tests, rather than ballooning into also wiring it into `review_service.py`.

**Problem summary:**
The plan-execute loop in the agent orchestrator wraps each tool call in a broad `except Exception` handler that catches the failure, logs it, and then just moves on — the loop continues as if nothing happened. Currently, a failed tool call produces no distinct failure signal: its result is stuffed into the same results dict as successful tools (as an `{"error": ..., "success": False}` entry), so nothing downstream is forced to notice or react to it, and a review can come back with missing sections and zero indication to the user that something broke. This affects `agent/orchestrator.py` (the loop itself) and `agent/error_handling.py` (the retry/backoff logic tool calls go through before they reach that handler). A successful fix makes tool failures impossible to silently absorb — raising or clearly flagging them so calling code must handle the failure explicitly — backed by unit tests (there currently are none for this module) that prove a failing tool is no longer indistinguishable from a successful one.

**Branch name:** fix/44-orchestrator-silent-tool-exceptions

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [ ] Issue added to cohort ledger

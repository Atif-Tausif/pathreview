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

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** [ba2cf7f](https://github.com/ascherj/pathreview/commit/ba2cf7f) (branch `fix/44-orchestrator-silent-tool-exceptions`)

**Reproduction summary:**
Added `tests/unit/test_orchestrator.py`, which runs `Orchestrator.run()` with a tool that always raises `RuntimeError`. The test fails against current code: `run()` returns normally with no top-level failure indicator — the exception is caught in the plan-execute loop (`orchestrator.py:60-62`) and buried inside `tool_results["tech_detector"]` as an `{"error": ..., "success": False}` entry, indistinguishable in shape from a successful tool's output.

**PLAN.md link:** [PLAN.md](./PLAN.md)

**Walkthrough video (recommended):**

**Blockers or open questions:**
Still deciding whether a fully-failed run should raise from `run()` entirely vs. always return normally with a `success: False` flag (see Risks & unknowns in PLAN.md). Also need to confirm via grep whether `RetryContext` in `error_handling.py` is dead code before Week 9, since it looks unused outside the module.

## Week 9 — Solution building & PR submission

### Check-in 1 (mid-week)

**Current progress:**
Resolved the open question from Week 8: went with always returning normally with `success: False` + `failed_tools` rather than raising, since `run()` aggregates several independent tool calls and one bad tool shouldn't blow up the whole profile analysis. Implemented the fix in `agent/orchestrator.py` — `run()`'s plan-execute loop now tracks a `failed_tools` list alongside `results`, and the returned dict gains top-level `success: bool` and `failed_tools: list[str]` keys. Confirmed `RetryContext` in `error_handling.py` is genuinely dead code (grepped the whole repo — referenced nowhere outside its own module); left it alone since removing it is unrelated to this issue, but flagged it as a separate follow-up task rather than silently ignoring it.

Before touching anything, ran `make check` / `make test-unit` and recorded the pre-existing baseline: 54 pre-existing unit test failures (unrelated modules — bias detector, resume parser, review service, etc.), 175 pre-existing ruff errors, 49 files failing black formatting, and mypy stopping early on a pre-existing numpy/Python-version stub incompatibility. None of these touch `agent/orchestrator.py` or `agent/error_handling.py`.

Tests added: extended `tests/unit/test_orchestrator.py` from the single Week 8 reproduction test to 7 tests (full success, partial failure, total failure, empty plan, cache-hit-not-misreported, session-store persistence). Added `tests/unit/test_error_handling.py` (didn't exist before) with 3 tests confirming `retry_with_backoff` actually re-raises after exhausting retries rather than swallowing — the behavior the orchestrator fix depends on. All 10 new/updated tests pass; re-ran the full suite and confirmed no new failures beyond the documented baseline (54 → 53, since the reproduction test itself flipped from failing to passing).

**Next steps:**
Open a draft PR for early feedback, finish self-review against `docs/CONTRIBUTING.md` (branch name and commit messages already follow convention), fill out the PR template with the pre-existing-failures note, and get peer/mentor feedback in Slack before marking it ready for review.

**Blockers:**
None currently.

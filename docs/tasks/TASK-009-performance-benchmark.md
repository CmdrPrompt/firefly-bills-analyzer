# TASK-009 Automated performance benchmark for pattern analysis (NFR-05)

## Status

todo

## Description

Add a repeatable, opt-in benchmark for `analyzer.identify_recurring` so the
60-second bound in NFR-05 is enforced automatically over time instead of
being measured once and written into a task's Completion notes.

Open Item #6 in the spec ("reference transaction volume for the 60-second
bound") is still unresolved because no one has measured throughput against
real data yet. This task doesn't guess a single reference volume — it
measures elapsed time across a range of synthetic dataset sizes and reports
the results, so a defensible volume can be picked (or the bound revisited)
once the numbers exist. Guessing one number now would just relocate the TBD
into code instead of resolving it.

**Depends on:** TASK-003 (`analyzer.py` must exist to benchmark).
Independent of the other pipeline tasks — can run any time after TASK-003.

Covers NFR-05.

## Branch

**Branch name:** `task/009-performance-benchmark`
**Switch/create:** `git checkout -b task/009-performance-benchmark`
**Make target:** `make branch-task f=TASK-009`

## Acceptance criteria

- [ ] `tests/benchmark_analyzer.py` generates synthetic withdrawal transaction
      datasets at several sizes (e.g. 500, 2 000, 5 000, 10 000, 20 000
      transactions) spread across a 24-month window, with a realistic mix of
      recurring payees (monthly/quarterly/yearly patterns) and non-recurring
      noise payees
- [ ] For each size, `identify_recurring()` is run and wall-clock elapsed
      time is measured with `time.perf_counter()`
- [ ] Results are printed as a small table (transaction count → elapsed
      seconds) and written to `benchmark_results.json` (git-ignored) for
      later comparison across runs
- [ ] The benchmark is **not** part of `make test` (it's slow); it runs via a
      new `make benchmark` target
- [ ] At the largest dataset size, the benchmark asserts elapsed time is
      under 60 seconds (NFR-05) — a failure here is a real regression signal,
      even before Open Item #6 is closed
- [ ] `docs/REQUIREMENTS_new.md` NFR-05's `[VALUE TBD]` placeholder is
      resolved based on the measured results: replace it with the largest
      dataset size that stayed under 60 seconds, framed as a provisional
      reference volume pending confirmation against real user data; remove
      Open Item #6 from the Open Items table and add a changelog entry
      documenting the measured numbers
- [ ] `make lint && make test` pass with coverage >= baseline (the benchmark
      file itself is excluded from coverage accounting, same as other
      non-unit-test scripts)

## Completion

**Date:**
**Summary:**
**Files changed:**

- `tests/benchmark_analyzer.py` — created
- `Makefile` — modified (`benchmark` target)
- `.gitignore` — modified (`benchmark_results.json`)
- `docs/REQUIREMENTS_new.md` — modified (NFR-05 value, Open Item #6 removed, changelog)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-009-performance-benchmark.md` — modified
- `docs/tasks/README.md` — modified (status)

**Branch:** `git checkout task/009-performance-benchmark`
**Stage:** `git add tests/benchmark_analyzer.py Makefile .gitignore docs/REQUIREMENTS_new.md CHANGELOG.md docs/tasks/TASK-009-performance-benchmark.md`
**Commit:** `git commit -m "Add automated performance benchmark for analyzer.py and resolve NFR-05 reference volume (TASK-009)"`

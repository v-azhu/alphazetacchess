# AlphaZetaChess Progress Snapshot — V0.4.3-beta-3 benchmarked, mobility redesign recommended

Snapshot date: 2026-08-31

## Repository state verified

Latest GitHub commit checked: `23bbb77` — "v0.4.3beta3 submitted". Reviewed
everything since `1404dab` (V0.4.2 + web UI): V0.4.3 beta-1 (mobility
evaluation, disabled by default), beta-2 (SearchEngine wiring), beta-3
(A/B benchmark tooling).

## What's confirmed done

1. **V0.4.2 (King Safety): COMPLETE.** Confirmed by your local full
   `pytest -q` run (all green) in an earlier checkpoint.
2. **Web UI: core functional, confirmed by you in a real browser.** Two
   real bugs found and fixed (click-through CSS bug, move-render-timing
   bug). Further UI polish intentionally deferred, per your own call to
   pause here and return later.
3. **V0.4.3 beta-1/beta-2 (mobility, disabled by default): wired in and
   tested.** `pytest tests/test_mobility_v043.py tests/test_evaluation_v043.py
   tests/test_search_v043_beta2.py -q` → 9 passed in 0.36s (fast, confirmed
   this session).

## This checkpoint's work: V0.4.3-beta-3 benchmark

Ran the A/B comparison your own `docs/PROGRESS_v043_beta3.md` asked for
(mobility OFF vs ON), but **deliberately limited to depth 1-2 on the
initial position only** — full reasoning in the new
`docs/v0.4.3_beta3-results.md`, short version: extrapolating from the
depth-2 cost multiplier, depth-3 could plausibly take anywhere from ~20s
to several minutes per position, and running the full 3-position sweep
at both depths risked a long-running command that isn't a good idea to
attempt in a single response given your usage-limit concern.

**Result:** mobility costs ~2.6x (depth 1) to ~3.2x (depth 2) wall-clock
time, for a much smaller 1.14x-1.35x node-count increase — i.e. the cost
is mostly per-leaf evaluation overhead (`mobility_balance()` calls the
expensive, fully-legal `Rule.generate_legal_moves()` for both colors at
every leaf), not the search tree getting bigger. Full table in
`docs/v0.4.3_beta3-results.md`.

## Recommendation (not yet implemented)

Rather than tuning `mobility_weight` on top of the current expensive
implementation, or running deeper benchmarks to characterize it further,
the more valuable next step is likely: **rewrite `mobility_balance()` to
use pseudo-legal move counts** (via `MoveGenerator` directly, no
check-simulation) instead of `Rule.generate_legal_moves()`. Mobility only
needs to be a cheap, approximate positional signal — it doesn't need
exact legal-move counts — so this should eliminate most of the measured
cost. If an A/B benchmark confirms that (similar score signal, much
lower cost), it should replace the current implementation rather than
get tuned on top of it. `use_mobility` stays `False` by default either
way until this is resolved.

## What this checkpoint changed

- `docs/v0.4.3_beta3-results.md` (new): full benchmark table, cost
  analysis, and the pseudo-legal-mobility recommendation above.
- `docs/roadmap.md`: added a proper `### V0.4.3 — Mobility` sub-section
  (previously only existed as standalone docs, not reflected in the
  structured roadmap), updated the Web UI section to reflect your
  confirmation that it works, and updated the hand-off diagram.

No source code was changed this checkpoint — this was benchmarking +
documentation only, consistent with not wanting to make design changes
(like switching to pseudo-legal mobility) without first confirming via a
quick benchmark that they're actually worth it.

## Exact next step

**Option A (recommended, small & fast):** implement a pseudo-legal
version of `mobility_balance()` and A/B-benchmark it against the current
one, same methodology as beta-3. This is a small, self-contained change
(one function in `mobility.py`) with a clear, cheap way to validate it
(same benchmark script, or a quick inline timing check like this
checkpoint did) before deciding whether to adopt it.

**Option B, if you'd rather not touch mobility right now:** leave
`use_mobility=False` as-is (already the default, zero risk to current
play) and move to a different V0.4 item instead — pawn structure or
piece coordination are the remaining items from `docs/roadmap.md`'s V0.4
list.

**If you want the deeper benchmark data instead:** run locally —
```powershell
python tools/benchmark_v043_beta3.py --depths 2
python tools/benchmark_v043_beta3.py --depths 3
```
and paste back the output; no need to interpret it yourself.

## Handoff rule (unchanged, repeated for visibility)

At the next interruption, update this file with:
1. latest commit;
2. pytest count/result;
3. benchmark result (or honest non-result, or "deliberately not attempted
   and why", as this checkpoint's depth-3 decision shows is sometimes the
   right call);
4. remaining checklist;
5. one exact next command.

This keeps the project resumable without relying on conversation memory,
and — given the free-tier usage-limit concern — keeps each individual
checkpoint's own work small enough to finish within a single response.

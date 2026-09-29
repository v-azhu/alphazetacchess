# AlphaZetaChess Current Progress

Snapshot date: 2026-09-28

Starting revision: `f945c40`; this checkpoint's changes are in the current worktree.

## Current engine status

- The primary playing engine is the alpha-beta `SearchEngine`; the CLI defaults to
  depth 4. The Web UI uses its SEE-enhanced search variant, also at depth 4.
- MCTS, neural evaluation, and policy networks remain runnable experiments. Existing
  match results do not show them outperforming the traditional search baseline.
- Null Move pruning remains opt-in. The latest correctness and search-boundary work is
  recorded in [`v0.10.0.md`](v0.10.0.md); older experiments remain in
  [`roadmap.md`](roadmap.md) and their version-specific documents.

## Latest completed work

V0.10.0 fixed three search correctness issues:

1. Repetition draws are recognized in alpha-beta, quiescence, and MCTS. Search returns
   draw score 0 without caching a path-dependent repetition result as an ordinary
   transposition-table score.
2. Search-only null moves are excluded from actual repetition counts.
3. Quiescence search still resolves check evasions when its nominal ply cap is reached.
   Quiescence TT entries are now keyed by both position and quiescence ply, so entries
   searched with different remaining extension budgets cannot collide.

The same checkpoint removes a redundant legal-move generation at the depth-zero
quiescence boundary. On the three checked reference positions at depth 3, iterative
deepening took 2.735s vs. 4.798s, 3.666s vs. 6.063s, and 1.953s vs. 3.193s before the
change. Node counts, scores, and best moves were unchanged. Timings are single-run
measurements and should be treated as local performance evidence, not portable targets.

The tactical regression suite now asserts independently checkable properties:
find an immediate mate, take an objectively safe capture, and avoid a capture that
allows an immediate recapture. A depth 2–4 diagnostic run passed all three cases and
confirmed that the input board state was restored after each search.

## Depth-4 vs. depth-3 match

Completed 20 games with colors balanced: depth 4 played Red in 10 and Black in 10.
Opening randomization was disabled, so every game began from the standard initial
position. Result from depth 4's perspective: **10 wins, 10 losses, 0 draws**, score
rate 50%, estimated Elo difference 0.

This is inconclusive, not evidence that the depths are equal. Even treating the 20
games as independent gives a rough 95% score-rate interval of 30–70% (about -148 to
+148 Elo). In addition, repeating the same deterministic opening gives little opening
diversity, so a follow-up should use a balanced set of randomized or curated openings
and report game-level uncertainty. The full records are in
`data/v0.10_depth4_vs_depth3.jsonl`.

## Validation

The complete test suite passed for the final current worktree: **343 passed**.

Useful commands:

```powershell
python -m pytest -q
python tools/benchmark_tactics.py --depths 2 3 4
python tools/benchmark_search.py --depths 2 3
```

## Current caveats and next steps

- The 20-game depth-4 vs. depth-3 match is inconclusive and uses only the initial
  position. Search speed and tactical gates are not substitutes for playing-strength
  measurement.
- Historical design documents such as `docs/architecture.md` describe the initial
  project intent. Use this snapshot and the V0.10.0 report for current implementation
  status.
- A more informative depth-4 vs. depth-3 match remains the next strength-validation
  step. It should alternate colors over multiple openings, record all games, and report
  uncertainty rather than treating a point Elo estimate as decisive.
- Continue with targeted profiling and tactical tests before adding forward pruning or
  changing evaluation weights. Keep experimental pruning disabled until it is shown
  not to regress objective tactical tests and improves match results.

The completed single-opening comparison can be reproduced with:

```powershell
python tools/compare_engines.py --a-depth 4 --b-depth 3 --games 20 --random-opening-plies 0 --random-opening-prob 0 --output data/v0.10_depth4_vs_depth3.jsonl
```

For broader coverage, retain the default randomized opening plies and increase the
game count; runtime will be substantial at depth 4.

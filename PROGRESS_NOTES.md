# AlphaZetaChess Progress Snapshot — V0.4.1 COMPLETE, V0.4.2 starting

Snapshot date: 2026-08-31

## Repository state verified

Latest main commit at start of this checkpoint: `f492bd6` — "v035 beta submitted"
(V0.4.1 work in this checkpoint is uncommitted local changes on top of that commit;
see the delivered zip for exact files to apply.)

## pytest result

```
51 passed in ~130-150s
```

Includes 6 new tests in `tests/test_evaluation_v041.py` on top of the 45 that were
green at the previous checkpoint.

## What this checkpoint changed

- `src/alphazetacchess/engine/evaluation.py`: added Piece-Square Tables (PST) for
  Horse, Cannon, Rook, and Pawn, each built from a short, documented rationale
  (see `docs/v0.4.1.md`) rather than an opaque grid of numbers. `evaluate()` gained
  `use_piece_square_tables=True` (default), with `False` reproducing the exact
  V0.2/V0.3 formula for A/B comparison.
- `src/alphazetacchess/engine/search.py`: `SearchEngine` gained a matching
  `use_piece_square_tables` constructor flag, threaded through all four internal
  `evaluate()` call sites.
- `tests/test_evaluation_v041.py` (new, 6 tests): symmetry, "PST prefers good
  squares at equal material" (Horse and Pawn cases), exact reproduction of the old
  formula when disabled, and a direct wiring check through `SearchEngine._quiescence`.
- `docs/v0.4.1.md` (new): full design rationale per piece type, benchmark attempt
  log, and an honestly-recorded known limitation (see below).
- `docs/roadmap.md`: V0.4.1 → COMPLETE, V0.4.2 (King Safety) → CURRENT, hand-off
  diagram updated.

## Benchmark result — and an honest miss worth reading

Attempted a self-play win-rate benchmark (PST on vs off) at depth 1 and depth 2,
from the opening and from two midgame reference positions, with move caps up to
150. **Every attempt reached its move limit without a decisive result.** This is
not a bug: PST's bonuses are small relative to material, both engines are fully
deterministic (so repeated games from the same position don't sample real
variety), and depth 2 self-play is currently too slow (~140-200s+ per game) to
run enough games for a meaningful sample in one session. As a sanity check,
`SearchEngine(depth=1, use_piece_square_tables=True)` vs `RandomEngine` scored a
clean 6-0 in 36s — confirming the engine can produce decisive results when there
actually is a skill gap, so the draws above are specific to two closely-matched
shallow searches, not a general problem.

**The real acceptance evidence for V0.4.1 is the 6 unit-level correctness
tests**, which measure the actual mechanism directly ("does the evaluator now
prefer good squares to bad ones at equal material") far more precisely than a
noisy win-rate number would have. Full reasoning in `docs/v0.4.1.md`.

## Recurring lesson, still worth repeating

Same "kings on file 4 with nothing between them" pitfall did NOT recur this
checkpoint (no new hand-built test positions with kings involved were needed for
PST tests, which mostly use single-piece-plus-two-kings-on-different-files
fixtures already following the established convention). Keeping this note here
anyway since it's now a 3-for-3 recurring bug class across V0.3.3/3.4/3.5 and is
worth a permanent mental checklist item for any future hand-built board.

## Not yet started

V0.4.2 — King Safety. No code exists yet. Per `docs/v0.4.1.md`'s own "next step"
note, this is Xiangqi-specific (palace structure, advisor/elephant screen
integrity) rather than a generic technique, so it needs its own design rather
than reusing V0.4.1's column/development-rank table approach.

## Exact next step

1. Design a King Safety scoring term: candidates include counting intact
   advisor/elephant "screen" pieces still in their defensive positions,
   penalizing open lines (files/ranks) leading directly to the king, and/or a
   penalty for the king having very few legal squares (mobility-as-danger,
   inverted from how mobility is normally scored for other pieces).
2. Add it behind its own toggle (`use_king_safety` or similar), keeping
   material+mobility (V0.2) and PST (V0.4.1) both independently toggleable so
   each layer stays A/B-comparable on its own.
3. Write correctness tests FIRST that assert the intended direction (e.g., "a
   king with both advisors intact scores higher than the same king with both
   advisors captured, all else equal") before worrying about exact magnitudes.
4. Given V0.4.1's finding that self-play win-rate benchmarking isn't reliably
   practical at current search depths/speeds, don't block completion on it --
   attempt it, but if it's inconclusive again, record that honestly (as
   `docs/v0.4.1.md` did) rather than spending excessive session time chasing a
   decisive result that the search depth may simply not support yet.

## Handoff rule (unchanged, repeated for visibility)

At the next interruption, update this file with:
1. latest commit;
2. pytest count/result;
3. benchmark result (or honest non-result, as this checkpoint showed is
   sometimes the correct outcome to report);
4. remaining checklist;
5. one exact next command.

This keeps the project resumable without relying on conversation memory.

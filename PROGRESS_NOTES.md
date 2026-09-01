# AlphaZetaChess Progress Snapshot — V0.4.4 (Pawn Structure) COMPLETE

Snapshot date: 2026-09-01

## What this checkpoint did

Implemented V0.4.4 (Option B from the previous checkpoint): Pawn
Structure evaluation, specifically Connected Pawns (联兵) — pawns on
adjacent files at the same rank mutually support each other after
crossing the river.

## What was verified this checkpoint

```
python -m py_compile src/alphazetacchess/engine/pawn_structure.py \
                      src/alphazetacchess/engine/evaluation.py \
                      src/alphazetacchess/engine/search.py
→ OK

pytest tests/test_pawn_structure_v044.py -q
10 passed in 0.05s

pytest tests/test_mobility_v043.py tests/test_evaluation_v043.py \
       tests/test_search_v043_beta2.py tests/test_evaluation_v041.py \
       tests/test_evaluation_v042.py tests/test_pawn_structure_v044.py -q
35 passed in 0.39s   (all V0.4.x targeted tests together, confirms no
                       regressions from wiring the new term in)
```

Quick depth-2 cost check on the initial position (same methodology as
V0.4.3's checkpoints): **essentially free** — 5.57s (OFF) vs 5.43s (ON),
identical node count (1916) and chosen move. Unlike mobility, pawn
structure didn't need a performance pass — it's a simple
O(pieces-on-board) board scan, no move generation involved.

**Not run this checkpoint (kept small deliberately):** the full pytest
suite, any multi-position/multi-depth benchmark sweep, or
playing-strength self-play/UI testing.

## What changed

- `src/alphazetacchess/engine/pawn_structure.py` (new): Connected Pawns
  scoring, `pawn_structure_score()` / `pawn_structure_balance()`.
- `src/alphazetacchess/engine/evaluation.py`: added `use_pawn_structure=False`
  parameter to `evaluate()`, wired in additively (independent of the
  other three V0.4.x terms — all four can be combined freely).
- `src/alphazetacchess/engine/search.py`: `SearchEngine` gained a
  matching `use_pawn_structure` constructor flag, threaded through all
  four internal `evaluate()` call sites (same mechanical pattern used
  for `use_mobility`).
- `tests/test_pawn_structure_v044.py` (new, 10 tests): isolated pawn
  scores zero, connected pawns each score the base bonus, crossed-river
  bonus stacks correctly, same-file/non-adjacent/enemy pawns correctly
  do NOT count as connections, symmetry, exact-delta toggle checks, and
  a `SearchEngine`-level wiring check (direct `_quiescence` call,
  avoiding the "search picks a different move and hides the difference"
  trap documented in V0.4.1/V0.4.2's wiring tests).
- `docs/v0.4.4.md` (new): full design, scope boundaries, and benchmark.
- `docs/roadmap.md`: added the V0.4.3 beta-4 section header fix (was
  still saying "BETA-3" despite beta-4 being done), added the V0.4.4
  section, updated the hand-off diagram.

## No repeat of the recurring test-fixture bug

Every constructed position in `test_pawn_structure_v044.py` either
doesn't involve king adjacency logic at all (pure pawn-only fixtures) or
places the two kings on different files from the start — avoiding the
"kings on file 4 with nothing between them" pitfall documented across
V0.3.3/V0.3.4/V0.4.2's checkpoints. First V0.4.x test file written
without hitting it during development this time.

## `use_pawn_structure` is STILL `False` by default

Same reasoning as `use_mobility`: this checkpoint implemented and
cost-verified the term, not established a playing-strength case for it.

## Exact next step

Two independent options (same shape as after V0.4.3-beta-4):

**(a)** Try `use_mobility=True` and/or `use_pawn_structure=True`
together via the web UI for a qualitative playing-strength read — both
terms are now implemented, tested, and cheap enough to combine freely
with `use_piece_square_tables`/`use_king_safety` (already on by
default).

**(b)** Move to the last remaining item from `docs/roadmap.md`'s
original V0.4 list — **piece coordination** — and leave mobility and
pawn structure both available-but-off for later. This would complete
V0.4's full original scope (mobility, piece-square tables, coordination,
king safety, pawn structure, endgame/opening knowledge — endgame/opening
knowledge not yet started either, worth deciding whether that's V0.4 or
pushed to V0.5's self-play scope).

## Handoff rule (unchanged, repeated for visibility)

At the next interruption, update this file with:
1. latest commit;
2. pytest count/result;
3. benchmark result (or honest non-result, or "deliberately not
   attempted and why");
4. remaining checklist;
5. one exact next command.

This keeps the project resumable without relying on conversation memory,
and keeps each checkpoint's own work small enough to finish within a
single response, given the free-tier usage-limit concern.

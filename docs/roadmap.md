# AlphaZetaChess Roadmap v0.2

## Development Philosophy

Chess Rules → Traditional Engine → Search Optimization → Evaluation → Self Play → Neural Network → Hybrid Engine

Every version must remain runnable, and every claimed improvement should be measurable.

## Version Status

| Version | Status | Goal |
|---|---|---|
| V0.1 | COMPLETE | Chess foundation |
| V0.2 | COMPLETE | Minimax + Alpha-Beta |
| V0.3.1 | COMPLETE | Iterative deepening + move ordering |
| V0.3.2 | COMPLETE | Transposition table |
| V0.3.3 | COMPLETE | Negamax / PVS |
| V0.3.4 | CURRENT | Quiescence search |
| V0.3.5 | PLANNED | Benchmark / regression consolidation |
| V0.4 | PLANNED | Advanced evaluation |
| V0.5 | PLANNED | Self-play / training data |
| V0.6+ | PLANNED | Neural evaluation / MCTS |
| V0.7 | PLANNED | Hybrid engine |
| V1.0 | PLANNED | Complete Xiangqi AI platform |

## V0.1 — COMPLETE

Board/piece representation, all seven piece rules, legal move generation, check/flying-general validation, checkmate/stalemate handling, CLI play and tests.

## V0.2 — COMPLETE

Minimax, Alpha-Beta, basic material + positional evaluation, fixed depth, SearchResult, Human vs SearchEngine, AI benchmark.

Acceptance evidence from the repository:

- depth=1 vs RandomEngine: 10 games, 6 wins, 0 losses, 4 draws
- depth=2 vs RandomEngine: 6 games, 5 wins, 0 losses, 1 draw
- Minimax and Alpha-Beta agree on tested positions
- Alpha-Beta does not visit more nodes than corresponding Minimax

Current baseline: depth=2. Depth=3 is stronger but currently too slow.

## V0.3 — Strong Traditional Engine

### V0.3.1 — Iterative Deepening + Move Ordering — COMPLETE

Goal: make deeper Alpha-Beta practical while preserving V0.2 correctness.

Tasks:

- [x] Iterative deepening
- [x] Preserve last completed iteration as safe result
- [x] Root move ordering
- [x] Previous iteration best move first
- [x] Tactical moves before quiet moves (TT best-move ordering at non-root nodes, added in V0.3.2)
- [x] Search depth/node reporting
- [x] Regression tests
- [x] Benchmark against V0.2 fixed-depth search

Acceptance criteria: all met, see measured results below.

Design boundary: V0.3.1 does not introduce transposition tables, PVS or quiescence search
(the transposition table landed in V0.3.2 immediately after, per the original plan).

#### Measured results (2026-08-29, `tools/benchmark_search.py`, TT enabled in both arms)

| Position | Depth | Fixed (V0.2-style) | Iterative + ordering (V0.3.1) | Same score/move |
|---|---|---|---|---|
| initial | 2 | 3.21s / 1001 nodes | 3.03s / 973 nodes | yes |
| early_development | 2 | 2.33s / 671 nodes | 2.37s / 671 nodes | yes |
| central_development | 2 | 1.03s / 289 nodes | 0.59s / 171 nodes | yes |
| initial | 3 | did not finish in 50s | 6.65s / 2769 nodes | yes |
| early_development | 3 | not measured (>50s expected) | 16.32s / 5317 nodes | yes |
| central_development | 3 | not measured (>50s expected) | 13.83s / 5223 nodes | yes |

At depth 3, "fixed" (no root move ordering) still exhibits the same 50s+ / 100s+ slowness
recorded for V0.2 — confirming this is a clean before/after comparison, not an
accidentally-optimized baseline. Iterative deepening + move ordering + TT together bring
depth 3 down to single-digit-to-teens seconds, roughly a 7-15x speedup, with search
score and best move identical to the unordered baseline on every tested position.
`depth=4` from the initial position still exceeds 55s and is not yet practical; the next
speed lever is expected to be quiescence search / better pruning (V0.3.3-3.4) rather than
raw depth.

### V0.3.2 — Transposition Table — COMPLETE

Zobrist incremental hashing (round-trip tested), depth-aware TT entries with EXACT/LOWER/UPPER
bounds, deterministic eviction, TT-based move ordering at non-root nodes, TT statistics
(probes/hits/cutoffs). All V0.3.2 acceptance criteria from `docs/v0.3.2.md` are met:

1. Existing tests remain green (27/27).
2. Zobrist hash round-trips correctly through arbitrary move/undo (`test_zobrist_hash_round_trip`).
3. Search with TT returns the same score and best move as without TT
   (`test_tt_preserves_search_result`).
4. TT does not increase node count on the reference position (`test_tt_does_not_increase_nodes_on_reference_position`).
5. TT statistics (probes/hits/cutoffs) are exposed and non-zero in practice
   (e.g. initial position depth 3: 2769 probes, 705 hits, 533 cutoffs).
6. Benchmark results recorded above (V0.3.1 section) already include TT, since the
   benchmark tool enables it by default in both arms.
7. No change to Xiangqi rules or evaluation semantics.

**Known limitation carried forward:** the mate-distance ("ply from root") scoring inside
`_minimax`/`_alphabeta` originally derived its ply offset from `self.depth` (the engine's
final requested depth) instead of the current iterative-deepening iteration's own max
depth. This produced correctly-signed but slightly mis-scaled mate scores during
intermediate (non-final) iterations, which could pollute the TT with imprecise entries
for genuinely terminal positions. Fixed by threading the current iteration's depth
explicitly through the recursion as `root_depth`; covered by a new regression test
(`test_mate_score_ply_offset_uses_current_iteration_depth`). This did not change any
previously-passing test's result, since the final iteration was always self-consistent.

### V0.3.3 — Negamax / PVS — COMPLETE

Refactored search to Negamax (single recursion, mover's-own-perspective scoring), added
Principal Variation Search on top, and simplified the TT key to drop `root_color` (a
natural consequence of Negamax scoring — see `docs/v0.3.3.md`). Full design, scope,
acceptance criteria and measured PVS-vs-non-PVS benchmark (depth 2 and 3, three reference
positions) are recorded in `docs/v0.3.3.md`. Summary: PVS is correctness-neutral
everywhere tested (identical score/move to non-PVS Negamax and to V0.3.2's Alpha-Beta),
with a small net overhead at depth 2 and a modest win (up to ~9.5% fewer nodes) starting
to appear at depth 3 on two of three positions — consistent with PVS needing enough
remaining tree depth to pay back its own probing cost.

**Two test-fixture bugs found and fixed while validating this refactor:** two mate-in-1
test positions placed the Red and Black kings on the same file with the Black elephant as
the sole blocker. Since Black's king/advisors were already fully boxed in by their own
pieces, moving that elephant away exposed "flying general," which the legality filter
correctly rejects — pinning the elephant and leaving Black with **zero legal moves before
Red even moved**, independent of the intended tactic. Both tests happened to still return
a passing assertion (a large "near-mate" score), but for the wrong reason: any Red move
looked equally winning, not specifically the intended horse mate. Fixed by moving the Red
king off Black's file and adding a Black piece (a Rook) with mobility independent of the
pin, in both `tests/test_search_v031.py` and `tests/test_search_v033.py`, plus an
explicit "Black has legal moves before Red's move" sanity assertion so this class of
fixture bug fails loudly instead of passing vacuously in the future.

### V0.3.4 — Quiescence Search — CURRENT

Tactical move set, capture search, check extensions, horizon-effect tests and performance/strength benchmark.

### V0.3.5 — Benchmark & Regression — PLANNED

Fixed benchmark positions, reproducible seeds, NPS, strength regression and V0.3 acceptance report.

## V0.4 — Advanced Evaluation — PLANNED

Mobility, piece-square tables, coordination, king safety, pawn structure, endgame knowledge and opening knowledge.

## V0.5 — Self Play — PLANNED

AI vs AI games, data collection, automatic evaluation and training dataset generation.

## V0.6+ — Neural Evaluation / MCTS — PLANNED

Policy/value network, neural evaluation and MCTS integration.

## V0.7 — Hybrid Engine — PLANNED

Neural Network + MCTS/Alpha-Beta + Traditional Evaluation = AlphaZetaChess Engine.

## V1.0 — Complete AI Platform — PLANNED

Human play, analysis, self improvement, UCCI, model management and strength evaluation.

## Progress Tracking / Handoff

The repository is the source of truth. At the end of every step:

1. Update this roadmap.
2. Record the completed sub-version.
3. Record benchmark evidence.
4. Record known limitations.
5. State the exact next step.

Current hand-off:

    V0.3.2 COMPLETE (Zobrist + depth-aware TT, benchmarked)
        ↓
    V0.3.3 COMPLETE (Negamax + PVS refactor, benchmarked, TT key simplified,
    two mate-in-1 test fixtures fixed after they were found passing vacuously)
        ↓
    V0.3.4 CURRENT
        ↓
    Quiescence search: tactical move set, capture search, check extensions
        ↓
    Horizon-effect regression tests
        ↓
    Benchmark against V0.3.3 (search strength + node/time cost)

Last updated: 2026-08-29

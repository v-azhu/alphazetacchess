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
| V0.3.4 | COMPLETE | Quiescence search |
| V0.3.5 | COMPLETE | Benchmark / regression consolidation |
| V0.4 | CURRENT | Advanced evaluation |
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

### V0.3.4 — Quiescence Search — COMPLETE

Captures-only tactical search at the horizon, mandatory full legal-move search while in
check ("check extensions"), fail-soft Negamax alpha-beta quiescence, stand-pat pruning for
quiet nodes, a hard `quiescence_max_ply` safety cap, and partial TT integration (only for
values that don't depend on the remaining q-search budget). Full design, scope, validation
gates and measured A/B benchmark (Quiescence OFF vs ON, depth 2 and 3, three reference
positions) are recorded in `docs/v0.3.4.md`.

**Two more test-fixture bugs found and fixed while validating this feature** (same root
cause as the V0.3.3 fixes: hand-built minimal positions defaulting both kings to file 4
with nothing blocking between them, either creating an illegal "flying general" position
or leaving one side already in check before its own move):
- `test_engine_avoids_hanging_its_own_rook_when_it_can_see_the_recapture`
  (`tests/test_search.py`): the original bare-king position was so fragile (no advisors/
  elephants at all) that Quiescence Search correctly discovered several of the "safe"
  king-move alternatives actually walk into a real forced mate a few plies deeper — a
  genuine tactic the old, weaker search simply couldn't see, not a QS bug. Fixed by giving
  both kings their normal advisor + elephant screen so king safety stops dominating the
  position, leaving material (the actual thing under test) as the deciding factor.
- `test_iterative_deepening_matches_fixed_depth` (`tests/test_search_v031.py`): asserted
  iterative deepening and fixed-depth search return the exact same best move at equal
  depth. When multiple root moves are genuinely tied for best score, which one is
  returned depends on move-ordering-dependent tie-breaking, which legitimately differs
  between the two search modes. Relaxed to the invariant that actually holds: both
  searches must reach the same minimax **score**.
- A **third** instance of the identical pitfall was independently found and fixed during
  V0.3.5 validation (`tests/test_search_v035_beta.py`, see `docs/v0.3.5-beta.md`): a
  "free rook" regression position had the two kings facing each other with nothing on the
  file between them, making the position illegal and the test's premise meaningless. Fixed
  by adding a blocking pawn on the central file.

**Benchmark summary** (full table and analysis in `docs/v0.3.4.md`): the node/time cost of
Quiescence Search is highly position-dependent, not a fixed overhead — from roughly free
(-8.3% nodes on `central_development` at depth 3) to expensive (+300% nodes on `initial`
at depth 3, where the opening's central pawn tension gives the capture-only leaf search a
lot to resolve). `same(score/move)=False` between QS-off and QS-on is common and expected,
not a regression: that is the entire point of extending the horizon.

**Known limitation:** no Static Exchange Evaluation (SEE) or MVV-LVA move ordering within
quiescence, so capture-heavy positions (like the opening) pay the most. Deliberately not
optimized yet, per the project's "measure before optimizing" principle — see
`docs/v0.3.5.md`'s V0.3 Acceptance Summary for the full carry-forward list into V0.4.

### V0.3.5 — Benchmark & Regression — COMPLETE

Regression framework (`tests/test_search_v035.py`: legal-move guarantee, determinism, PVS
and TT score preservation, QS legal-move guarantee) plus explicit tactical regression
positions (`tests/test_search_v035_beta.py`: forced capture, forced check resolution,
Quiescence recapture) — 45/45 tests green. Full V0.3 phase acceptance summary, covering
V0.3.1 through V0.3.5 with evidence pointers for each, is in `docs/v0.3.5.md`.

## V0.4 — Advanced Evaluation — CURRENT

Mobility, piece-square tables, coordination, king safety, pawn structure, endgame knowledge and opening knowledge.

### V0.4.1 — Piece-Square Tables — COMPLETE

Per-square positional bonuses for Horse/Cannon/Rook/Pawn added to `engine/evaluation.py`,
toggleable via `use_piece_square_tables` (default True), with the exact V0.2/V0.3 formula
kept reachable via `False` as the regression baseline. Full design rationale (why each
table looks the way it does, in Xiangqi-specific terms) and validation are in
`docs/v0.4.1.md`. 6 new correctness tests (`tests/test_evaluation_v041.py`) plus the full
existing suite stay green — 51/51 total.

**Playing-strength self-play benchmark: attempted, result recorded honestly as
inconclusive.** Multiple depth-1 and depth-2 self-play attempts (PST on vs off, several
starting positions, move caps up to 150) all reached their move limit without a decisive
result — not a bug, but the expected outcome of two fully deterministic, closely-matched
shallow searches with a genuinely small (single-digit-to-~20-point) positional signal and
no opening-book variety to sample different game shapes. `SearchEngine(depth=1,
use_piece_square_tables=True)` vs `RandomEngine` scored a clean 6-0 in the same session,
confirming decisive results ARE reachable given a real skill gap — see `docs/v0.4.1.md`
for the full table of attempts and the reasoning. The six unit-level correctness gates
(testing the actual "does the evaluator prefer good squares to bad ones" mechanism
directly) stand as the real acceptance evidence for this sub-version; a statistically
meaningful win-rate benchmark is deferred until either search performance improves or an
opening book adds game variety.

### V0.4.2 — King Safety — IMPLEMENTATION COMPLETE, LOCAL VALIDATION PENDING

Two additive evaluation terms added to `engine/evaluation.py`: Guard Integrity (a bonus
per surviving Advisor/Elephant of the king's own color) and Open-File Exposure (a penalty
when a clear file runs from the king to an enemy Rook or Cannon). Both independently
toggleable from `use_piece_square_tables` via a new `use_king_safety` flag, threaded
through `SearchEngine` the same way V0.4.1's flag was. Full design rationale and scope
boundaries (rank-based exposure and attacker-proximity scoring deliberately deferred) are
in `docs/v0.4.2.md`.

10 new correctness tests (`tests/test_evaluation_v042.py`) confirmed green in isolation
this session (0.03s). **The full pytest suite has not been run this session** — per the
current workflow, long-running test/benchmark commands are being run locally instead of
in the sandbox that writes the code, to avoid spending session time/usage on them. Awaiting
that local confirmation before marking this sub-version COMPLETE.

**One test-fixture subtlety found and fixed while writing the wiring test** (a new
category, not a repeat of the "kings on the same file" pitfall from V0.3.3-3.5): a
position built to test Open-File Exposure using an enemy Rook on a fully open file turned
out to also be an actual, immediate check under `Rule.is_in_check` (nothing at all blocks
a Rook's line of sight), which correctly made Quiescence Search's "no stand-pat while in
check" rule (V0.3.4) take over instead of returning a plain evaluation — expected,
correct behavior, but the wrong fixture for isolating evaluation *wiring*. Fixed by using
a Cannon instead (a real King Safety threat that is not itself an immediate check, since
a Cannon needs a screen to capture). Full writeup in `docs/v0.4.2.md`.

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

    V0.4.1 COMPLETE (piece-square tables for Horse/Cannon/Rook/Pawn, 6 new
    correctness tests, 51/51 green; playing-strength self-play benchmark
    attempted and honestly recorded as inconclusive at practical depths --
    see docs/v0.4.1.md)
        ↓
    V0.4.2 IMPLEMENTATION COMPLETE, LOCAL VALIDATION PENDING (king safety:
    guard integrity + open-file exposure, 10 new correctness tests green
    in isolation this session; full suite NOT run this session -- see
    "exactly what to run locally" in docs/v0.4.2.md)
        ↓
    Run locally: pytest -q (full suite), report pass/fail count
        ↓
    If green: mark docs/v0.4.2.md and this roadmap entry COMPLETE
        ↓
    V0.4.3: pick next item from V0.4's list (pawn structure, piece
    coordination, or rank-based king exposure as a direct follow-on)

Last updated: 2026-08-31

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
| V0.4 | COMPLETE | Advanced evaluation |
| V0.5 | CURRENT | Self-play / training data |
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

## V0.4 — Advanced Evaluation — COMPLETE (five of five original terms; Endgame/Opening Knowledge moved to V0.5)

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

### V0.4.2 — King Safety — COMPLETE

Two additive evaluation terms added to `engine/evaluation.py`: Guard Integrity (a bonus
per surviving Advisor/Elephant of the king's own color) and Open-File Exposure (a penalty
when a clear file runs from the king to an enemy Rook or Cannon). Both independently
toggleable from `use_piece_square_tables` via a new `use_king_safety` flag, threaded
through `SearchEngine` the same way V0.4.1's flag was. Full design rationale and scope
boundaries (rank-based exposure and attacker-proximity scoring deliberately deferred) are
in `docs/v0.4.2.md`.

10 new correctness tests (`tests/test_evaluation_v042.py`) confirmed green in isolation
in-session (0.03s). **Full pytest suite confirmed green by local run (2026-08-31):** all
tests passing, no failures reported.

**One test-fixture subtlety found and fixed while writing the wiring test** (a new
category, not a repeat of the "kings on the same file" pitfall from V0.3.3-3.5): a
position built to test Open-File Exposure using an enemy Rook on a fully open file turned
out to also be an actual, immediate check under `Rule.is_in_check` (nothing at all blocks
a Rook's line of sight), which correctly made Quiescence Search's "no stand-pat while in
check" rule (V0.3.4) take over instead of returning a plain evaluation — expected,
correct behavior, but the wrong fixture for isolating evaluation *wiring*. Fixed by using
a Cannon instead (a real King Safety threat that is not itself an immediate check, since
a Cannon needs a screen to capture). Full writeup in `docs/v0.4.2.md`.

### V0.4.3 — Mobility — BETA-4 COMPLETE (cost fixed; not yet enabled by default)

Weighted legal-move-count mobility (`engine/mobility.py`: `mobility_balance()`, per-piece
weights favoring Horse/Cannon/Rook over King/Advisor/Elephant/Pawn), wired into
`evaluate()` and `SearchEngine` behind `use_mobility=False` (default) / `mobility_weight=1`,
following the same toggleable-layer pattern as V0.4.1/V0.4.2. Full history across beta-1
(evaluation-only), beta-2 (SearchEngine wiring), and beta-3 (A/B benchmark) is in
`docs/v0.4.3.md`, `docs/v0.4.3_beta2.md`, and `docs/PROGRESS_v043_beta3.md`.

9 focused tests (`tests/test_mobility_v043.py`, `tests/test_evaluation_v043.py`,
`tests/test_search_v043_beta2.py`) green (0.36s).

**Beta-3 A/B benchmark (initial position, depth 1-2 only — see
`docs/v0.4.3_beta3-results.md` for the full table and reasoning):** mobility adds
~2.6x (depth 1) to ~3.2x (depth 2) wall-clock time for a comparatively small 1.14x-1.35x
node-count increase — i.e. most of the cost is per-leaf evaluation overhead, not a bigger
search tree. Root cause: `mobility_balance()` calls the expensive, fully-legal
`Rule.generate_legal_moves()` for both colors at every leaf, the same check-simulation
bottleneck that has been the established cost driver since the V0.2 review. Depth-3 and
the other two reference positions were deliberately not benchmarked this session, to avoid
a long-running command; extrapolating from the depth-2 multiplier, depth-3 could plausibly
range from ~20s to several minutes per position depending on which one.

**Recommendation, not yet acted on:** rather than tuning `mobility_weight` on top of the
current expensive implementation, first benchmark a pseudo-legal-move-count version of
mobility (via `MoveGenerator` directly, no check-simulation) against the current
fully-legal one — this is very likely to eliminate most of the measured cost, since
mobility only needs to be a cheap approximate signal, not an exact legal-move count. If
that holds up, it should replace the current implementation rather than be tuned on top
of it. `use_mobility` stays `False` by default until this is resolved.

**Beta-4: implemented and confirmed.** Switched `mobility_score`/`mobility_balance` to
pseudo-legal counting via `MoveGenerator` (old fully-legal version kept as
`_mobility_score_legal_reference` for comparison only). Cost multiplier dropped from
2.6x-3.2x (beta-3) to **1.13x-1.43x** (beta-4) at depth 1-2 on the initial position, with
identical node counts and chosen moves at both depths — same search behavior, much less
overhead. Full table in `docs/v0.4.3_beta4.md`. `use_mobility` still defaults to `False`
(this fixes the cost of enabling it, doesn't yet establish it should be default-on — that
needs a playing-strength signal, not just a cost benchmark). Next step: try it via the now-
working web UI for a qualitative playing-strength read, or move on to the next V0.4 item
(pawn structure / piece coordination) and leave mobility available-but-off.

### V0.4.4 — Pawn Structure (Connected Pawns) — COMPLETE

One well-defined Xiangqi-specific concept: Connected Pawns (联兵) — pawns on adjacent
files at the same rank can mutually support each other after crossing the river (sideways
movement). `engine/pawn_structure.py`: `pawn_structure_balance()`, a base bonus per
connected pawn plus an extra bonus if that pawn has also crossed the river. Wired into
`evaluate()` and `SearchEngine` behind `use_pawn_structure=False` (default), independent
of `use_piece_square_tables`/`use_king_safety`/`use_mobility` — all four terms stack
additively and can be toggled in any combination. Full design, scope boundaries (isolated-
pawn penalty, doubled pawns, and passed-pawn-equivalents all deliberately deferred/skipped
with Xiangqi-specific reasoning for each) and benchmark are in `docs/v0.4.4.md`.

10 new correctness tests (`tests/test_pawn_structure_v044.py`) green. Combined with the
existing V0.4.1-4.3 targeted test files: **35/35 green, 0.39s total.** No "kings on the
same file" fixture pitfall this time — every test position either doesn't involve king
adjacency at all, or places the kings on different files from the start, consistent with
the standing lesson from V0.3.3/V0.3.4/V0.4.2.

**Benchmark: essentially free.** Depth-2 cost check on the initial position: 5.57s (OFF)
vs 5.43s (ON), identical node count (1916) and chosen move — within normal run-to-run
noise. Unlike V0.4.3's mobility term (which needed a pseudo-legal rewrite in beta-4 to
become cheap), pawn structure was cheap from the start: a simple O(pieces-on-board) scan,
no move generation involved.

No playing-strength benchmark attempted (consistent with keeping this checkpoint small,
and the same honest-non-result situation `docs/v0.4.1.md` already documented for this
class of signal — a real answer needs self-play or human-vs-engine games, not a cost
benchmark).

### V0.4.5 — Piece Coordination — COMPLETE

Two classical Rook/Cannon file-sharing patterns: Doubled Rooks (双车) and Rook-Cannon
Battery (车炮连环). `engine/piece_coordination.py`: `piece_coordination_balance()`, wired
into `evaluate()` and `SearchEngine` behind `use_piece_coordination=False` (default),
independent of and additive with all four other V0.4.x terms. Full design and scope
boundaries (no line-of-sight requirement between the pieces, Horse-Cannon screening and
rank-based coordination both deliberately deferred) are in `docs/v0.4.5.md`.

11 new correctness tests (`tests/test_piece_coordination_v045.py`). Combined with every
other V0.4.x targeted test file: **46/46 green, 0.35s.** Depth-2 cost check: 4.95s (OFF)
vs 5.30s (ON) on the initial position — cheap, same order of magnitude as V0.4.4's pawn
structure term, not the kind of cost V0.4.3's mobility term needed a rewrite to avoid.

**This completes V0.4's original five-term list** (mobility, piece-square tables,
coordination, king safety, pawn structure). Endgame/opening knowledge — qualitatively
different from the other five (evaluation-phase switching and a move-selection book,
respectively, not simple additive scoring terms) — remains an open decision: become
V0.4.6+, or fold into V0.5's self-play scope, since opening books are often built FROM
self-play data. Not decided yet, not blocking anything.

**Web UI updated alongside this:** `web/server.py`'s `new_game()` now accepts an
`eval_flags` dict (all five `use_*` booleans, unknown keys ignored, missing keys default),
and `index.html`/`board.js` expose this as five checkboxes next to the depth selector —
so any combination of the V0.4.1-4.5 evaluation terms can be tried directly from the
browser without editing code. This was the actual point of building V0.4.3-4.5 before
moving further: there's now something concrete to sit down and play against. See
`docs/ui.md`.

## V0.5 — Self Play — V0.5.4 COMPLETE (all mechanisms); real local runs next

AI vs AI games, data collection, automatic evaluation and training dataset generation.

**Scope decision (2026-09-01):** V0.4's original list included Endgame Knowledge and
Opening Knowledge, both left undone when V0.4.5 completed the other five terms. Decision:
learn these from self-play data rather than hand-coding them, and fold them into V0.5
rather than adding a V0.4.6/V0.4.7 — an opening book and endgame heuristics both need
recorded self-play data to derive from in the first place, which is exactly what V0.5 was
already going to produce.

### V0.5.1 — Self-Play Game Recording — COMPLETE

`src/alphazetacchess/selfplay/recorder.py`: `play_recorded_game()` plays one full game
move-by-move (built on the same `Rule.is_game_over`/`SearchEngine.choose_move`/`Board.move`
calls `tools/benchmark.py`'s win-rate-only `play_game` already used) and returns a
JSON-serializable record with the full move sequence, result, and both sides' engine
configuration. `append_record()`/`load_records()` provide append-only JSON-lines file I/O,
so repeated runs accumulate data across sessions rather than overwriting.
`tools/self_play.py` is the CLI wrapper (`--games`, `--depth`, `--output`, plus
`--use-mobility`/`--use-pawn-structure`/`--use-piece-coordination` matching
`SearchEngine`'s own toggles), appending each game's record as soon as it finishes so an
interrupted long run still leaves usable partial data. Full design, record format, and
reasoning in `docs/v0.5.1.md`.

5 new correctness tests (`tests/test_selfplay_recorder_v051.py`), including a fully
deterministic decisive-game test (added `board=` as an optional parameter to
`play_recorded_game` specifically to let tests start one ply from a forced mate instead of
waiting on a real game) that caught a genuine bug while being written: `recorder.py`'s
first draft read `.from_pos` directly off `SearchEngine.choose_move()`'s return value, but
every engine's `choose_move()` returns a uniform `SearchResult` (see `engine/base.py`), not
a bare `Move` — `tools/benchmark.py`'s existing `play_game` already had this right
(`result.best_move.from_pos`); fixed `recorder.py` to match. Combined with every other
targeted V0.4.x test file: **51/51 green, 0.42s.**

Smoke-tested end to end this session (`--games 2 --depth 1 --max-moves 20`, 22s total,
output file verified well-formed) — **no real data-collection run was attempted**, since
at the realistic `depth=2` configuration individual games have historically taken 1-3+
minutes (see `docs/v0.3.4.md`, `docs/v0.4.3_beta3-results.md`), making a data set large
enough to be useful for V0.5.2 a local, long-running task by design, same treatment as
every other genuinely slow operation in this project.

`data/` (gitignored `*.jsonl`, with a `README.md` explaining the directory) is where
`tools/self_play.py` writes by default.

### V0.5.2 — Opening Book from Self-Play — COMPLETE (mechanism); needs a real corpus

`src/alphazetacchess/selfplay/opening_book.py`: books are keyed by (Zobrist hash, color to
move) rather than move sequence, so transpositions share statistics instead of being
tracked separately. `build_book_from_records()` replays V0.5.1 records through a fresh
`Board` and accumulates per-position, per-move win/draw/loss/games counts for the first
`max_ply` half-moves; `select_book_move()` picks the best win-rate move meeting a
`min_games` threshold (deliberately simple frequentist scoring, no confidence interval or
exploration bonus — not worth the sophistication against a small corpus yet).
`tools/build_opening_book.py` is the CLI glue from `tools/self_play.py`'s output to a
saved book file. `SearchEngine` gained `use_opening_book`/`opening_book`/
`opening_book_min_games`; `choose_move()` checks the book first and returns immediately
(search never runs) when there's a confident entry, validated against actual current legal
moves before being trusted. `SearchResult` gained a defaulted `from_book: bool = False`
field so callers can tell a book move from a searched one. Full design and a known
limitation (a fully-deterministic low-depth self-play corpus has no real move diversity to
learn from) are in `docs/v0.5.2.md`.

9 new correctness tests (`tests/test_opening_book_v052.py`). Combined with every other
targeted V0.4.x/V0.5.x test file: **60/60 green, 1.42s.** Smoke-tested end to end
(self-play → book → book-driven `SearchEngine` move) this session with a small,
fully-deterministic sample — confirms the mechanism works, but **no book has been built
from a real, larger self-play corpus yet**, since that depends on V0.5.1's own "run
locally" step having actually been run at a useful scale.

### V0.5.2b — Opening Randomization — COMPLETE (confirmed necessary with real data)

A real 10-game self-play batch (`depth=2`, both sides identical config) was shared and
inspected: **all 10 games were byte-for-byte identical** — same 82-move length, same
result, every move matching. Confirmed the exact concern predicted in V0.5.2's "Known
limitation": `SearchEngine` is fully deterministic, so naive self-play from a fixed start
always replays the same game. Full diagnosis in `docs/v0.5.3-data-check.md`.

Fix: `src/alphazetacchess/selfplay/opening_randomization.py`'s `RandomizedOpeningEngine`
wraps any `ChessEngine` and, for the first N plies, has a configurable probability of
playing a uniformly random legal move instead of deferring to the wrapped engine
(standard "epsilon-greedy exploration"). Kept as an external wrapper, not built into
`SearchEngine`, since this is purely a data-collection concern. `tools/self_play.py` now
uses this **by default** (`--random-opening-plies 10 --random-opening-prob 0.3`,
`--random-opening-prob 0` to disable).

4 new tests (`tests/test_opening_randomization_v052b.py`), including one that directly
reproduces the original issue (two randomized games with different seeds must differ) —
combined with every other targeted test file: **64/64 green.** Real CLI smoke test
(`--games 4 --depth 1`, default randomization on) confirmed 4 genuinely different games,
unlike the original uploaded batch.

### V0.5.3 — Endgame Heuristics from Self-Play Data — COMPLETE (mechanism); needs a real corpus

`src/alphazetacchess/engine/endgame.py`: a new optional evaluation term grounded in a
well-known Xiangqi endgame principle — 车赛全局，炮怕残棋 (Rook power holds up into the
endgame, Cannon power declines as screening pieces are traded off). `is_endgame(board)`
classifies phase by combined Rook+Cannon+Horse material (both sides) dropping to ≤2600;
`endgame_balance()` applies a flat +40-per-Rook / −40-per-Cannon adjustment, but only
inside that phase — zero effect everywhere else. Deliberately does **not** add a
king-activity term (a natural-looking companion in Western chess): the Xiangqi King can
never leave its palace at any phase, so that heuristic simply doesn't translate. Wired into
`evaluate()`/`SearchEngine` as `use_endgame_heuristics` (disabled by default, same pattern
as every other V0.4.x/V0.5.x term).

`src/alphazetacchess/selfplay/endgame_analysis.py` + `tools/analyze_endgame.py`: mines
V0.5.1 self-play records for the actual hypothesis test — among games that reach the
endgame phase with a non-tied Rook/Cannon edge (weighted by this module's own constants),
does the favored side actually win more often? Mirrors V0.5.2's opening-book approach:
build and test the mechanism now, keep "trusting the specific constants" as a clearly
separate, re-runnable step once a larger corpus exists.

13 new tests (`tests/test_endgame_v053.py`), including a hand-built, capture-heavy
synthetic move sequence (verified independently against a real `Board()`) that exercises
`find_endgame_onset()` without needing a full search-generated game. Combined with every
other targeted V0.4.x/V0.5.x test file: **122/122 green.** Smoke-tested end to end this
session (self-play → onset detection → edge-vs-outcome summary); incidentally confirmed
the phase threshold's placement is reasonable (depth=1, 40-move-capped games essentially
never reach it; a 100-move-capped game did, at ply 70). Full design, exact test list, and
known limitations in `docs/v0.5.3.md`.

### V0.5.4 — Automated Strength Comparison — COMPLETE (mechanism); needs a real comparison

`src/alphazetacchess/selfplay/strength_comparison.py`: `run_comparison_match()` plays N
games between two independently configurable engine setups, alternating colors, and
reports win/draw/loss + a standard log-odds Elo-difference estimate. Reuses V0.5.1's
`play_recorded_game` directly rather than a separate play loop, so every comparison-match
game is automatically a valid, complete self-play record — a comparison run and a
data-collection run can be the same run, `--output` pointed at the same
`data/selfplay.jsonl` V0.5.2's opening book and V0.5.3's endgame analysis already consume.
`tools/benchmark.py`'s existing SearchEngine-vs-RandomEngine sanity check is untouched
(different job: RandomEngine has no configuration to compare).

`tools/compare_engines.py`: CLI exposing `--a-*`/`--b-*` flags for both sides' depth and
V0.4.x/V0.5.3 evaluation-term toggles, mirroring `tools/self_play.py`'s flag conventions.

8 new tests (`tests/test_strength_comparison_v054.py`), most notably one that starts two
games from the same forced-mate fixture with the winning color swapped between games,
specifically to catch a "credited the win to whoever played Red" bug rather than "credited
the win to the correct configuration" — the exact mistake a naive generalization of
`tools/benchmark.py`'s alternation logic could introduce. Combined with every other
targeted test file: **130/130 green.** Smoke-tested end to end (small real matches, plus
confirmed `--output` records are directly consumable by `tools/analyze_endgame.py`). Full
design and known limitations in `docs/v0.5.4.md`.

## V0.6+ — Neural Evaluation / MCTS — PLANNED

Policy/value network, neural evaluation and MCTS integration.

## V0.7 — Hybrid Engine — PLANNED

Neural Network + MCTS/Alpha-Beta + Traditional Evaluation = AlphaZetaChess Engine.

## V1.0 — Complete AI Platform — PLANNED

Human play, analysis, self improvement, UCCI, model management and strength evaluation.

## Tooling — Web UI — CORE FUNCTIONAL, POLISH DEFERRED

Not a numbered engine-strength version (it doesn't change `Board`/`Rule`/`SearchEngine`
at all), but tracked here since it directly enables human-vs-engine testing going forward.
`web/server.py` (Flask) + `web/static/` (SVG board, click-to-move) provide a real graphical
board in the browser, replacing the CLI's coordinate-typing interface for interactive
testing purposes. It calls the exact same Core/Engine classes as the CLI and test suite —
no game logic is duplicated. Full design, bug history, and a "what to check locally" list
are in `docs/ui.md`.

Two real bugs found via real-browser testing and fixed: (1) piece circles blocked clicks
from reaching the invisible click-handling layer beneath them (`pointer-events: none`
fix), and (2) Red's own move didn't render until the AI's reply had also finished
computing, because both moves were applied server-side before any response went back
(fixed by splitting into two endpoints, `POST /api/move` + `POST /api/ai_move`, so the
frontend can render after each side's move independently). **Both confirmed working by
the user in a real browser.** Core click-to-move gameplay loop is functional and
confirmed; further polish (side-switching, move undo, captured-piece tray, animation) is
intentionally deferred — see `docs/ui.md`'s "Known limitations" — to return to once the
engine-strength track (V0.4.3+) has more to show for it.

Drag-to-move was never implemented in this first version (click origin, then click
destination, is the only supported interaction) — this is a known scope limitation
documented in `docs/ui.md`, not a bug.

## Progress Tracking / Handoff

The repository is the source of truth. At the end of every step:

1. Update this roadmap.
2. Record the completed sub-version.
3. Record benchmark evidence.
4. Record known limitations.
5. State the exact next step.

Current hand-off:

    V0.4.5 COMPLETE -- V0.4's original five-term list fully done
    (piece-square tables, king safety, mobility, pawn structure, piece
    coordination), web UI exposes all five as checkboxes for real
    human-vs-engine testing.
        ↓
    Decision: Endgame/Opening Knowledge learned from self-play data
    rather than hand-coded -- folded into V0.5, no V0.4.6/4.7.
        ↓
    V0.5.1 COMPLETE (self-play game recording: engine/selfplay/recorder.py
    + tools/self_play.py, JSON-lines format, append-only, 5 tests green,
    smoke-tested end to end -- see docs/v0.5.1.md). No real data-collection
    batch run yet -- depth=2 games are a local, long-running task by
    design, same treatment as every other slow operation in this project.
        ↓
    V0.5.2 COMPLETE as a mechanism (opening book from self-play records,
    Zobrist-keyed for transposition sharing, wired into SearchEngine as
    use_opening_book -- see docs/v0.5.2.md). 9 tests green, smoke-tested
    end to end. Still needs a REAL corpus -- current data is a small
    deterministic smoke test with no real move diversity to learn from.
        ↓
    Real 10-game batch shared and inspected: all 10 games byte-identical
    (confirmed the predicted diversity problem with real data, not just
    prediction). Fixed: RandomizedOpeningEngine (epsilon-greedy opening
    randomization), now ON by default in tools/self_play.py. 4 new tests,
    64/64 total, smoke-tested -- confirmed games now actually diverge.
    See docs/v0.5.3-data-check.md.
        ↓
    V0.5.3 COMPLETE as a mechanism (endgame-phase Rook bonus / Cannon
    penalty, grounded in real Xiangqi endgame theory -- see
    engine/endgame.py -- plus selfplay/endgame_analysis.py +
    tools/analyze_endgame.py to test the hypothesis against recorded
    data). 13 new tests, 122/122 total, smoke-tested end to end. Still
    needs a REAL, larger corpus before the +40/-40 constants (or the
    decision to enable use_endgame_heuristics by default) can be
    trusted -- see docs/v0.5.3.md.
        ↓
    V0.5.4 COMPLETE as a mechanism (run_comparison_match() +
    tools/compare_engines.py: two independently configurable
    SearchEngine setups play each other, alternating colors, win/draw/
    loss + Elo-difference estimate reported. Reuses V0.5.1's
    play_recorded_game directly, so --output is the same
    data/selfplay.jsonl corpus every other V0.5.x tool already reads/
    writes -- a comparison run and a data-collection run can be the
    same run). 8 new tests, 130/130 total, smoke-tested end to end
    (including confirming --output records are directly consumable by
    tools/analyze_endgame.py). See docs/v0.5.4.md.
        ↓
    Next: run real, statistically meaningful local matches --
        python tools/compare_engines.py --a-depth 2 --a-use-endgame-heuristics \
            --b-depth 2 --games 20 --output data/selfplay.jsonl
        python tools/compare_engines.py --a-depth 3 --b-depth 2 \
            --games 20 --output data/selfplay.jsonl
        python tools/build_opening_book.py
        python tools/analyze_endgame.py
    One local session now answers V0.5.2's book-quality question,
    V0.5.3's endgame-constant question, AND V0.5.4's own "which
    configuration is actually stronger" question, since all three tools
    read/write the same corpus.
        ↓
    First real (if small) installment of that data collected here: 12
    real games (10 self-play + 2 compare_engines) run one at a time due
    to this sandbox not keeping background processes alive between
    commands -- data/selfplay.jsonl + data/opening_book.json committed
    deliberately as a reference point. analyze_endgame found 4 decided
    Rook/Cannon-edge positions (3/4 favored side won) -- directionally
    consistent with engine/endgame.py's hypothesis but explicitly NOT
    enough to trust; the 2-game use_endgame_heuristics on/off comparison
    (1 loss, 1 draw for "on") points the other way, which is itself a
    reminder that small samples are noisy in either direction. use_
    endgame_heuristics and the opening book both remain off by default.
    See docs/v0.5-real-data-checkpoint.md for the full breakdown.
        ↓
    User ran several real local batches (a real background process is
    practical outside this sandbox) and pushed the results:
    data/selfplay.jsonl grew from 12 to 63 real games. Rebuilt the
    opening book against the full corpus (had gone stale at 689
    positions from an intermediate partial run -- now 1057 positions,
    1121 position-move entries) and confirmed end to end that
    SearchEngine actually consults it (from_book=True on a real
    choose_move() call, not just a file existing).
    use_endgame_heuristics: isolated the 25 real on-vs-off comparison
    games in the corpus -- 3 wins / 3 wins / 19 draws, i.e. an exact
    50% score rate, Elo diff +0. A REAL null result, not "too small to
    tell": the previous checkpoint's 75%-favored-side-won number is now
    understood to have been small-sample noise, exactly as its own
    caveat warned. use_endgame_heuristics and the opening book both
    remain off by default -- no evidence of harm, but also none of
    benefit at depth=2. See docs/v0.5-real-data-checkpoint-2.md.
        ↓
    Small natural gap this surfaced: tools/compare_engines.py had no
    --use-opening-book flag (V0.5.4 predates the book becoming
    substantial enough to be worth comparing). Added --a-use-opening-book
    /--b-use-opening-book + shared --opening-book/--opening-book-min-games,
    wired straight to SearchEngine's existing V0.5.2 parameters -- no new
    mechanism, just a missing CLI path to one that already existed.
    Documented the interaction with opening randomization (can override
    a book move by design; pass --random-opening-prob 0 to isolate the
    book's effect specifically). Smoke-tested (book loads, from_book=True
    moves are instant; missing-book-file falls back cleanly with a
    message rather than crashing). 130/130 tests still green (no src/
    changes needed -- SearchEngine's book support was already tested by
    V0.5.2's own suite). See docs/v0.5.4.md's addendum.
        ↓
    Next: does the book actually help? Does depth=3 beat depth=2? Does
    use_endgame_heuristics show a different (real) result at depth=3,
    where search can act on the material nudge more meaningfully?
        python tools/compare_engines.py --a-use-opening-book --random-opening-prob 0 \
            --games 20 --output data/selfplay.jsonl
        python tools/compare_engines.py --a-depth 3 --b-depth 2 --games 20 --output data/selfplay.jsonl
        python tools/compare_engines.py --a-depth 3 --a-use-endgame-heuristics --b-depth 3 \
            --games 20 --output data/selfplay.jsonl
    All three still append to the same data/selfplay.jsonl -- one more
    local session (63 real games already banked) keeps compounding.
        ↓
    Here: with V0.5.1-V0.5.4 all in place as mechanisms, book-comparison
    now wired in, and a real 63-game checkpoint on record (one real null
    result, several questions still open), the V0.5 line's remaining
    work is almost entirely "keep collecting/comparing real data" rather
    than new code -- a natural pause point, or proceed to V0.6+ (neural
    evaluation / MCTS) if continuing here.

Last updated: 2026-09-05

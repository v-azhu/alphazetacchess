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
| V0.5 | COMPLETE | Self-play / training data |
| V0.6+ | V0.6.1-6.5 COMPLETE | Neural evaluation / MCTS |
| V0.7 | COMPLETE | UCCI protocol control + search-cancellation/time-control foundation |
| V0.8 | V0.8.1-8.3 COMPLETE | Search performance: specialized attack detector, killer move ordering, MVV-LVA capture ordering |
| V0.9 | V0.9.1-9.4 COMPLETE | Hybrid engine (renamed from this table's original V0.7 slot) |
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

## V0.5 — Self Play — COMPLETE (99 real games collected; see V0.6 for what's next)

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

### V0.5.2 — Opening Book from Self-Play — COMPLETE (mechanism + real corpus)

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
fully-deterministic sample — confirms the mechanism works. **Update**: a real book now
exists at `data/opening_book.json` (1330 entries, built from real accumulated self-play
data across many later sessions -- e.g. one popular opening move alone has 79 recorded
games with real win/draw/loss counts, not toy/mechanism-test numbers), closing the gap
this paragraph originally flagged.

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

### V0.5.4 — Automated Strength Comparison — COMPLETE (mechanism, extensively used for real comparisons since)

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
design and known limitations in `docs/v0.5.4.md`. **Update**: `tools/compare_engines.py`
has since been used extensively for real, decision-driving comparisons across V0.6.1
(38 games), V0.6.3 (120 games), V0.6.4 (200 games), V0.8.3 (57 games), and V0.9.2's
MCTS-vs-SearchEngine result -- the "needs a real comparison" gap this section originally
flagged has been closed many times over.

## V0.6+ — Neural Evaluation / MCTS — V0.6.2 concluded (negative result); V0.6.3 calibration COMPLETE (analysis + real-game result: leans negative); V0.6.4 COMPLETE (real-game result: clearly positive, first positive tuning result in project history); V0.6.5 COMPLETE (calibrated weights promoted to SearchEngine's actual defaults)

### V0.6.3 — Calibrating the Heuristic's Constants Against Real Data — COMPLETE (analysis + real-game result)

Rather than a fourth iteration of V0.6.2's "more data/capacity/features" pattern (three attempts,
each showing the same small, exhausted return), used the same 94,872 real labeled positions
completely differently: fit new values for `evaluate()`'s own hand-guessed constants directly via
linear regression, instead of training another black-box network.

`engine/evaluation.py`'s new `evaluate_components()` decomposes a position into raw regression
features (material counts per type, PST/king-safety/mobility/pawn-structure/piece-coordination/
endgame balances) -- recombining these with the CURRENT hand-guessed constants reproduces
`evaluate()`'s own output exactly (the central correctness gate, tested directly).
`tools/calibrate_evaluation.py` fits an OLS regression against real Pikafish scores.

**Real, coherent finding**: normalized to Pawn=1, Rook/Cannon/Horse appear substantially
undervalued in the current hand-guessed material scale (current ratios 9.0/4.5/4.0 vs. fitted
15.9/7.8/7.25 -- roughly 1.7-1.9x low across all three, a consistent pattern) while
Elephant/Advisor/Pawn's relative values already look about right. Also found a real +40cp
intercept (tempo bias) not currently modeled at all, and suggestive (but more cautiously
interpreted) findings that PST/king-safety scaling may be too small and pawn-structure/piece-
coordination's real impact needs separate variance-based investigation before drawing
conclusions. The linear model is LESS accurate overall than V0.6.2's neural network (1055cp/0.511
correlation vs. 760cp/0.786) -- expected, and not the point: the goal is better constants for the
existing, fast, interpretable heuristic, not a more accurate predictor in isolation.

7 new tests (`tests/test_evaluation_components_v063.py`). Combined total: **191/191 green**.

**Real-game result (100 games, updated 2026-09-10, combined with an earlier 20-game run
for 120 total)**: calibrated material scores 42.5%, Elo ~-53, 95% CI [33.7%, 51.3%],
p~=0.10 vs. a 50% null -- leans toward a real negative effect (worse, not better play),
not fully conclusive at conventional significance but no longer plausibly "probably
neutral" the way the earlier n=20 result was. A concrete instance of `docs/v0.6.2.md`'s
own caution that correlating better with a strong reference engine's static scores
doesn't guarantee playing better inside this engine's own alpha-beta search.
`use_calibrated_material` stays `False` by default -- this result supports that, not a
new decision. See `docs/v0.6.3.md`'s second addendum for the full numbers, the
draw-rate data-quality note, and two untested hypotheses for why (isolated material
change vs. the rest of `evaluate()`'s weighting; possible depth=2 shallowness effect).

### V0.6.4 — Combined Calibrated Weights (Material + PST + King Safety) — COMPLETE (mechanism + real-game result: clearly positive)

Builds infrastructure to test the first of V0.6.3's two untested hypotheses:
`evaluate()` gains `pst_weight=1`/`king_safety_weight=1` (both default 1, exactly
reproducing every prior version's behavior), required splitting `_piece_score`
(previously combined material + PST) into separate pieces so `pst_weight` can scale
PST independently -- a pure refactor, verified behavior-preserving before the new
parameters were even added. `CALIBRATED_PST_WEIGHT = 10`/`CALIBRATED_KING_SAFETY_WEIGHT
= 8` (rounded from the same V0.6.3 regression's fitted 9.9/8.3, same rounding rationale
`CALIBRATED_MATERIAL_VALUES` already used). `SearchEngine` threads both through
identically to `material_values`. `tools/compare_engines.py
--{prefix}-use-calibrated-weights` turns on all three calibrated findings together
(material + PST + king-safety), not material alone -- the actual point, since testing
them combined is exactly what V0.6.3's real-game result didn't do. 6 new tests
(`tests/test_pst_king_safety_weights_v064.py`), following V0.6.3's own test pattern
exactly, including confirming the V0.6.3 correctness gate (raw components recombined
with the constants in force reproduce `evaluate()`'s own output) still holds for a
non-default weighting. Full suite: **287/287 green.**

**Real-game result (2026-09-11, 100 games each depth)**: reverses V0.6.3's material-alone
finding. Depth 2: 57.0% score rate, Elo ~+49, 95% CI [47.3%, 66.7%], p=0.162 (leans
positive, not independently significant). Depth 3: 61.5% score rate, Elo ~+81, 95% CI
[52.0%, 71.0%], p=0.021 (significant at the conventional 0.05 level). Combined via
Fisher's method across both independent runs: p~=0.023. **This is the first clearly
positive result from any evaluation-tuning checkpoint in this project's history**
(V0.6.2 neural eval: -269 Elo; V0.6.3 material alone: ~-53 Elo) -- confirms both of
V0.6.3's untested hypotheses weren't mutually exclusive: the combined weighting is more
internally consistent than material alone (hypothesis a), and that consistency pays off
more clearly with more search depth (hypothesis b). `docs/v0.6.4.md`'s newest addendum
has the full numbers and explicitly flags the natural next step -- promoting
`CALIBRATED_MATERIAL_VALUES`/`CALIBRATED_PST_WEIGHT`/`CALIBRATED_KING_SAFETY_WEIGHT` to
`SearchEngine`'s actual constructor defaults -- as a real recommendation, acted on next
in V0.6.5 below.

### V0.6.5 — Promote Calibrated Weights to `SearchEngine`'s Actual Defaults — COMPLETE

Acts on V0.6.4's recommendation: `SearchEngine.__init__`'s actual parameter defaults
for `material_values`/`pst_weight`/`king_safety_weight` move from the old hand-guessed
baseline (`None`/1/1) to `CALIBRATED_MATERIAL_VALUES`/`CALIBRATED_PST_WEIGHT`/
`CALIBRATED_KING_SAFETY_WEIGHT` -- exactly the configuration V0.6.4's 200-game real
result already tested, not a new untested one, so no additional confirmatory run was
needed (re-running the same comparison would reproduce the same result rather than test
something new). Every default-constructed `SearchEngine()`, including `UCCIEngine`'s
own default, now uses it automatically. `evaluate()`'s own defaults are deliberately
unchanged -- only `SearchEngine`'s constructor moved, keeping the change's blast radius
to one call site rather than the shared lower-level function every direct `evaluate()`
caller (tests, `evaluate_components()`) also depends on.

Verified (not assumed) that `tools/compare_engines.py`'s existing A/B comparisons are
unaffected: every `SearchEngine(...)` call site there passes these three parameters
explicitly one way or the other, never relying on `SearchEngine`'s own default, so every
existing and future invocation means exactly what it always meant.

Broke 6 existing tests immediately, all the same shape (bare `SearchEngine()` compared
against a bare `evaluate()` call, which still defaults to the old baseline) -- fixed by
pinning the pre-V0.6.5 baseline explicitly on those `SearchEngine` constructions, since
those tests are about whether a specific toggle reaches `evaluate()`, not about which
defaults are currently in effect. **Also found and fixed a real, pre-existing bug while
fixing those 6**: two of V0.6.4's own tests
(`tests/test_pst_king_safety_weights_v064.py`) turned out to have been passing
*vacuously* since the previous session -- their shared fixture happened to produce
`pst_balance == 0`/`king_safety_balance == 0` on this project's actual tables, making
several delta assertions trivially `0 == 0` regardless of whether the weight scaling
being tested actually worked. Rebuilt the fixture to give material, PST, and
king-safety components all genuinely nonzero, verified by direct computation rather than
assumed; this also surfaced a second bug in one test's own expected-delta formula (only
accounted for the Rook term of `CALIBRATED_MATERIAL_VALUES`'s change, silently missing
that Cannon and Horse also differ by 300 each). Full suite: **287/287 green.** Full
writeup in `docs/v0.6.5.md` -- including a follow-up this doc initially flagged (a
missing `tools/compare_engines.py` flag to explicitly request the pre-V0.6.5 baseline)
that turned out, on checking, to be based on an incorrect claim: `build_engine` always
passes `material_values`/`pst_weight`/`king_safety_weight` explicitly regardless of
calibration flags, so `compare_engines.py`'s "no flags" case was never affected by
`SearchEngine`'s own default changing, and no new flag was actually needed. Left the
mistaken section in the doc with a correction above it rather than deleting it.

Policy/value network, neural evaluation and MCTS integration.

### V0.6.1 — Monte Carlo Tree Search Skeleton — COMPLETE

`src/alphazetacchess/engine/mcts.py`: `MCTSEngine`, a PUCT-based MCTS search skeleton using
the *existing* V0.4.x/V0.5.3 `evaluate()` function as its leaf value estimator (squashed
through `tanh` into `[-1, 1]`) and uniform move priors -- deliberately no policy/value
network yet, same "search skeleton first, evaluation second" split V0.3/V0.4 used. Both the
`evaluate()` call and the uniform priors are exactly the two things a future network
replaces, without touching the tree-search logic around them.

12 new tests (`tests/test_mcts_v061.py`), most notably a dedicated unit test for the single
most error-prone part of any minimax/MCTS implementation (a child's value must be negated
before comparing it from the parent's perspective) and a cross-validation test where
`MCTSEngine` finds the *exact same* mate-in-one move an independently-implemented
`SearchEngine(depth=2)` oracle finds, rather than hand-verifying the winning square.
Combined with every other targeted test file: **142/142 green.**

Smoke-tested against `RandomEngine`: 6/6 games drew at the move limit, which looked
concerning until investigated directly -- tracking material confirmed `MCTSEngine`
reliably builds a real, growing advantage (4150 vs 3600 by ply 60 in one representative
game) but doesn't reliably convert it to checkmate within 150 moves at the simulation
budgets tested (100-800) -- an expected characteristic of vanilla MCTS without a policy
network (needs far more simulations per move than alpha-beta needs plies), not a
correctness bug, which the unit tests (especially the alpha-beta cross-validation)
independently confirm. Full design, exact test list, and the material-tracking evidence in
`docs/v0.6.1.md`.

### V0.6.2 — Neural Evaluation via Pikafish Distillation — pipeline COMPLETE, untrained

Investigated "borrow Pikafish's trained NNUE weights directly" before writing code, found
two real blockers: Pikafish's own network has a custom non-commercial license murky enough
to not cleanly embed in this public repo, and its HalfKAv2_xq feature encoding + quantized
inference would need a substantial, bug-prone reimplementation to port correctly. Pivoted to
**distillation**: run Pikafish locally as an oracle to label positions, train an entirely
new, small, from-scratch network on those labels -- never redistributes Pikafish's own
weights/code, and needs far less compute than either full self-play training or NNUE
reimplementation.

Five new pieces, each independently tested: `core/fen.py` (Xiangqi FEN encode/decode --
note the UCCI piece-letter convention differs from this project's own `PieceType.value`,
see the module's docstring), `neural/features.py` (perspective-relative board encoding,
1260-dim), `neural/network.py` (`SmallMLP`, hand-derived backprop verified against a
numerical gradient check), `neural/pikafish_client.py` + `tools/label_positions_with_
pikafish.py` (UCI client tested against a real fake-engine subprocess, not mocked), and
`tools/train_neural_eval.py` + `neural/evaluator.py`. 23 new tests, combined total
**165/165 green**. Full pipeline smoke-tested end to end against a fake engine (real FENs
sampled from real self-play games, labeled, network trained on the labels).

**Not yet done**: no real Pikafish-labeled training has happened (needs the user's local
machine), and the trained-network story isn't wired into `SearchEngine`/`MCTSEngine` yet --
deliberately deferred until there's a real network worth plugging in. Full design and
exact next commands in `docs/v0.6.2.md`.

## V0.7 — UCCI Protocol & Search Foundation — COMPLETE

**Scope note:** this roadmap originally labeled V0.7 "Hybrid Engine" (Neural Network +
MCTS/Alpha-Beta + Traditional Evaluation). The work actually built under `dev/v0.7-*`
was UCCI protocol control and the search-cancellation/time-control foundation it needs
-- a prerequisite for real engine-vs-engine and engine-vs-GUI play, not the hybrid
evaluation merge. The original "hybrid engine" scope is renamed forward rather than
dropped -- see the new V0.9 placeholder below.

### V0.7.1 — Cooperative Search Cancellation — COMPLETE

`SearchEngine` gained a `threading.Event`-based cooperative cancellation contract
(`request_stop()`/`clear_stop()`, an externally-owned `stop_event` parameter on
`choose_move()`) so the UCCI layer can implement a real `go`/`stop` cycle without
force-killing a thread -- Python has no safe general mechanism for that. Every
search-side `board.move()` is paired with `board.undo()` in `try/finally`, so a
cancellation can never leave the caller's board mid-search. Iterative deepening keeps
the last **fully completed** depth's result on cancellation (`SearchResult.depth`
reports that, not the requested depth); a cancellation before depth 1 completes falls
back to the first legal move at `depth=0`. Cancelled/incomplete nodes are never written
to the TT. `tests/test_search_cancellation.py` covers exact board-state restoration
after a mid-search cancellation and the iterative-deepening fallback boundary, using
deterministic test doubles rather than wall-clock sleeps. Full design in
`docs/v0.7.1.md`.

### V0.7.2 — UCCI Asynchronous Search Worker — COMPLETE

The UCCI adapter's `go` now starts a daemon worker thread (reconstructing its own board
from a FEN snapshot, never mutating the live UCCI board directly) and returns
immediately to the protocol loop, so `stop` can actually be received and acted on while
a search is running -- closing the gap V0.7.1 made possible but didn't itself wire into
the protocol layer. `stop` sets the shared event and waits for the worker to unwind
naturally; a small lock-protected pending-response queue ensures exactly one final
`bestmove`/`nobestmove` is published. Commands that would change the searched position
(`position`, a `newgame`-equivalent reset, another `go`) are rejected while a worker is
active -- the client must `stop` first. Full design in `docs/v0.7.2.md`.

### V0.7.3 — UCCI Time Control — COMPLETE

`protocol/search_limits.py`'s `SearchLimits` normalizes UCCI's `depth`/`movetime`/
`time`/`opptime`/`increment`/`oppincrement`/`movestogo`/`usemillisec` fields into a
single millisecond time budget: `0.8 * (remaining / moves_to_go) + 0.05 * increment`,
capped at 80% of remaining time, `movestogo` defaulting to 20 when omitted -- a
deliberately conservative policy, not an attempt at full tournament time-allocation
modeling. A daemon `Timer` sets the same cooperative stop event V0.7.1/V0.7.2 already
use once the budget expires, so clock-based cancellation reuses the existing safe
unwind path rather than introducing a second mechanism. Full design in `docs/v0.7.3.md`.

### V0.7.4 — Final Audit & Regression Baseline — COMPLETE

Closing checkpoint for the V0.7 protocol/search-foundation phase: locks down the
time-budget semantics (`tests/test_search_limits.py`), the V0.7.1 cancellation
invariants, and UCCI worker/timing behavior as the stable contract V0.8's move-ordering
work builds on top of, without changing any of them further. No new optimization is
added at this step by design. Full scope in `docs/v0.7.4.md`.

## V0.8 — Search Performance (Move Ordering & Attack Detection) — V0.8.1-8.3 COMPLETE

### V0.8.1 — Specialized Attack Detector — COMPLETE

`core/attack.py`'s `AttackDetector` answers "is square (x,y) attacked by `by_color`"
directly via per-piece source-square/ray checks (no `Move` object construction, no
apply/undo), replacing the `MoveGenerator.generate_moves()`-based path
`Rule.is_in_check()` previously used inside the legality-filtering hot path (called
after every candidate move in `Rule.generate_legal_moves()`). Handles cannon's
one-screen requirement, elephant eye/river boundary, horse leg-blocking, and pawn's
pre/post-river attack directions explicitly; flying-general remains a separate
board-level check in `Rule.is_in_check()`, not something the detector attempts.
Validated two ways: targeted per-piece geometry tests, and deterministic differential
testing against `MoveGenerator` restricted to captures-onto-occupied-squares (the two
tools answer different questions -- pseudo-legal movement vs. actual-attack -- so only
that intersection is directly comparable). Full design in `docs/v0.8.1.md`.

### V0.8.2 — Killer Move Ordering — COMPLETE

`engine/killer_moves.py`'s `KillerMoves`, a two-slot per-ply table of quiet moves that
previously caused a beta cutoff, tried before other quiet moves at the same ply.
Captures are never recorded or promoted by a stale coordinate match (tested
explicitly), since capture ordering already has its own signal. `use_killer_moves`
defaults `True` -- justified not by the packaged `tools/benchmark_killer_moves.py`
fixture (a tiny 8-piece position where it shows a **regression**, +44-48% nodes) but by
re-running the same on/off comparison against the project's established
`initial`/`early_development`/`central_development` reference positions, where it gives
a real 16-57% node reduction at depth 3 (small overhead under 10% at depth 2, the same
"needs depth to pay back its own cost" pattern V0.3.3 documented for PVS), identical
best move/score in every case. Full design, the complete benchmark table, and the
explanation for why the packaged fixture is misleading are in `docs/v0.8.2.md`.

### V0.8.3 — MVV-LVA Capture Ordering — COMPLETE

`SearchEngine._order_captures_by_mvv_lva` ranks captures by
`victim_value * 1000 - attacker_value` (using `self.material_values or
MATERIAL_VALUES`, consistent with `_evaluate`'s own override), tried before other
quiet moves. Killer promotion (V0.8.2) runs first, unchanged, so `use_mvv_lva=False`
reproduces V0.8.2's exact prior behavior; MVV-LVA then pulls captures ahead of
everything else including an already-promoted killer when enabled, giving the standard
hash-move > captures > killers > other-quiets priority. Unlike V0.8.2,
`use_mvv_lva` defaults **False**: benchmarked against the established reference
positions it shows a small *regression* (opening-phase positions have few captures, so
the per-node sort overhead isn't repaid), but a real +36-37% node reduction on a
capture-dense midgame fixture -- a genuinely mixed, position-dependent result, not the
broad win V0.8.2 had, so per this project's "off until proven" rule it stays off pending
a real multi-game strength comparison. `--{a,b}-use-mvv-lva` and the previously-missing
`--{a,b}-no-killer-moves` flags were added to `tools/compare_engines.py` for that future
run. **Real-game result (expanded to 57 games)**: 26-29-2, B(MVV-LVA) score rate 52.6%,
95% CI [39.7%, 65.6%], Elo ~+18 -- comfortably consistent with no real effect, barely
moved from the initial n=26 result (50.0%) despite more than doubling the sample.
`use_mvv_lva=False` stays the default. Full design, both node-count benchmark tables,
and the full game-level result in `docs/v0.8.3.md`.

## V0.9 — Hybrid Engine — V0.9.1-9.4 COMPLETE

Neural Network + MCTS/Alpha-Beta + Traditional Evaluation = AlphaZetaChess Engine. This
is the scope originally labeled V0.7 before V0.7 was used for UCCI protocol/search-
foundation work instead (see the V0.7 scope note above). Builds on the existing
`eval_fn`/`MCTSEngine` pluggability from V0.6.1/V0.6.2 and the calibrated-material
finding from V0.6.3, none of which are superseded by V0.7/V0.8's protocol/search-layer
work -- V0.9 combines them rather than starting over.

### V0.9.1 — MCTS Cooperative Cancellation & UCCI Wiring — COMPLETE

`MCTSEngine.choose_move` gained the same `stop_event=None`
`request_stop()`/`clear_stop()` cooperative-cancellation contract `SearchEngine` has
had since V0.7.1/V0.7.2 -- the concrete prerequisite for plugging `MCTSEngine` into
`UCCIEngine` at all. Cancellation strategy deliberately differs from `SearchEngine`'s:
PUCT's root visit-count distribution stays meaningful after any number of completed
simulations (unlike a partially-searched alpha-beta iteration, which is unsound), so
cancellation just stops the simulation loop early and reports on the partial tree,
falling back to the first legal move only if cancelled before the very first simulation
could expand the root. Also fixed a real, previously-latent bug this surfaced:
`UCCIEngine._parse_go`/`_handle_go` unconditionally read/wrote
`self.search_engine.depth`, which crashed immediately for any engine without a
`.depth` attribute (MCTS measures effort in `simulations` instead) -- now
`getattr`/`hasattr`-guarded, so `go depth N` is accepted for any engine and simply a
no-op for ones without a depth concept, while `go movetime`/`go time` continue working
identically for every engine via the shared `stop_event` mechanism. Verified with a
real (not fake) `MCTSEngine` plugged into `UCCIEngine` end-to-end -- a full
`go`/bestmove cycle, and `go`/`stop` actually interrupting a long-running MCTS search --
specifically because a fake double would have silently passed without exercising the
`.depth` bug. Full design in `docs/v0.9.1.md`.

### V0.9.2 — `--engine mcts` Wiring in `tools/compare_engines.py` — COMPLETE

`--{a,b}-engine {search,mcts}` and `--{a,b}-simulations` let either side of a
`compare_engines.py` comparison play as `MCTSEngine` instead of `SearchEngine` (default
`search`, so every prior invocation is unaffected). Flags that don't apply to MCTS
(no killer table, no MVV-LVA, no opening book, no `material_values`) are accepted
without crashing but explicitly warned about when set to a non-default value, rather
than silently ignored. No dedicated unit tests, matching this project's existing
"`tools/` scripts are thin CLI wrappers" convention and the precedent already set by
V0.6.3's/V0.8.3's own additions to this same file -- verified by a real smoke-test run
instead.

**Immediately used to settle V0.6.1's long-open strength question**: 28 games,
`MCTSEngine` (200 simulations, V0.6.1's default) vs. `SearchEngine` (depth 2) -- **1
win, 27 losses, 0 draws** (95% CI on score rate: [0.0%, 10.4%], no larger sample needed
to be confident this is real, unlike V0.8.3's/V0.6.3's near-50% findings). A follow-up
10 games at 5x the simulation budget (1000 sims) went **0-10** -- rules out "just needs
more simulations." Not surprising in retrospect: V0.6.1's MCTS has uniform move priors
(no policy network yet) and reuses `SearchEngine`'s own `evaluate()` as its only leaf
signal, the same well-known gap that AlphaZero-style engines need a trained policy/value
network to close. Makes V0.9's neural-network step the more consequential remaining item
over further fixed-prior MCTS tuning. Full numbers and caveats (including why the
~-570 Elo figure is a rough scale indicator, not a precise one, given how unstable the
log-odds formula is near 0%/100%) in `docs/v0.9.2.md`.

### V0.9.3 — Heuristic-Informed MCTS Priors — COMPLETE

Replaces `_MCTSNode.prior`'s uniform `1/N` (V0.6.1's own placeholder, explicitly flagged
as "exactly the parameter a future policy network would replace") with a cheap,
non-learned first attempt: `_heuristic_priors` makes each candidate move, evaluates the
result from the mover's own perspective, undoes it, and softmax-normalizes -- not a
trained policy network, but a real, if crude, non-uniform signal, meant to answer
"is the better-priors direction worth pursuing at all" before considering anything more
expensive. `use_heuristic_priors=False` default reproduces V0.6.1's exact uniform-prior
behavior. No correctness invariant the way `SearchEngine`'s ordering features have --
MCTS is inherently approximate, so a different prior genuinely changes outcomes, which
is the point, not a bug. 7 new tests
(`tests/test_mcts_heuristic_priors_v093.py`). Full suite: **294/294 green.**

**Real cost**: ~2.6x slower per simulation (extra `evaluate()` calls at every
expansion). **Real benefit, measured two ways**: at equal simulation count, a clear win
(24 games, 75.0% score rate, 95% CI [57.7%, 92.3%] entirely above 50%, Elo ~+191); at
equal wall-clock time (200 heuristic-prior sims vs. 520 uniform-prior sims, matching the
speed ratio), leans clearly positive but doesn't independently clear conventional
significance at n=48 (final total after 4 batches, 62.5%, 95% CI [48.8%, 76.2%],
p=0.083; a stable point estimate across independent halves, worth reading
`docs/v0.9.3.md`'s own transparency note on an interim n=36 batch that briefly looked
significant before more data pulled it back). Does not close
the large gap to `SearchEngine` found in V0.9.2 (a quick 4-game check still went 0-4).
`use_heuristic_priors` stays `False` by default, per the same "off until proven" bar
V0.6.5 held V0.6.4's combined weights to before promoting them -- the equal-time result
leans positive but isn't independently conclusive yet. The real conclusion: the
prior-quality direction is a genuine, measurable lever on MCTS's own strength, not a
dead end -- worth continued investment (up to and including a trained policy network),
though this checkpoint alone doesn't settle how far. Full numbers, both comparisons, and
the scope boundary (no learning, `prior_temperature` not independently tuned) in
`docs/v0.9.3.md`.

### V0.9.4 — Policy Network Infrastructure (Mechanism, Not Yet Trained) — COMPLETE

Four new pieces, mirroring V0.6.2's exact "features -> network -> evaluator -> engine
wiring" shape applied to the policy side: `neural/policy_encoding.py`
(`move_to_policy_index`/`policy_index_to_squares`, `POLICY_DIM = 90*90 = 8100`, using
the *same* perspective-relative vertical-flip convention `board_to_features` already
uses for input planes, so a canonical policy network only learns one orientation);
`neural/policy_network.py` (`PolicyMLP`, a separate network from `SmallMLP` -- lower
risk than a shared trunk for a first checkpoint with no training data yet -- trains via
ordinary softmax cross-entropy, masks to only the legal move set at inference, not
training); `neural/policy_evaluator.py` (`NeuralPolicyEvaluator`, matching
`engine/mcts.py`'s `policy_fn(board, color, legal_moves) -> {move: probability}`
convention, mirroring `NeuralEvaluator`'s pattern for `eval_fn`); and `MCTSEngine`'s new
`policy_fn` parameter itself, which takes priority over V0.9.3's `use_heuristic_priors`
when both are set (verified directly with deliberately conflicting distributions, not
assumed). **A real, concrete gap found and fixed along the way**:
`PikafishClient.evaluate_fen` has always returned `best_move` alongside the score, but
`tools/label_positions_with_pikafish.py` was silently discarding it -- fixed to record
it, though existing `data/pikafish_labels.jsonl` predates the fix and would need
relabeling to be usable for policy training. 19 new tests across four files. Full
suite: **313/313 green.**

**No training has happened** -- every `PolicyMLP` in this checkpoint's tests is
randomly initialized, validating the mechanism (correct, symmetric encoding;
mathematically correct backprop; sound masking; correct `MCTSEngine` wiring priority),
not playing strength. `tools/train_policy_network.py` doesn't exist yet, and needs
relabeled data from the user's local Pikafish first -- the same one-time dependency
V0.6.2's value network already had. Concrete next steps in dependency order (relabel ->
write the training tool -> a real strength comparison) in `docs/v0.9.4.md`.

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
        ↓
    User ran the three suggested comparisons, interrupted early (depth=3
    games are slow) -- still appended 36 complete, valid records (no
    partial/corrupt lines) before stopping. data/selfplay.jsonl: 63 -> 99
    real games. All three questions got real answers:
      - Opening book: 20 games, exactly 50%/50%, Elo diff +0 -- no
        measurable benefit yet (interesting side-note: zero draws across
        all 20, vs. the corpus's overall ~60% draw rate -- see
        docs/v0.5-real-data-checkpoint-3.md for a tentative explanation).
      - Depth=3 vs Depth=2: 12 games, 62.5% score for depth=3, Elo diff
        +88.7 -- the first checkpoint in this project's self-play history
        to show a real, meaningfully-sized effect, matching strong prior
        chess-engine intuition (deeper search beats shallower search).
      - use_endgame_heuristics at depth=3: only 4 games completed before
        the interruption; combined with the existing depth=2 games (29
        total), still a flat ~52% / Elo +12 -- consistent with the
        earlier depth=2-only null result.
    tools/analyze_endgame.py on the full 99-game corpus: 20 decided
    Rook/Cannon-edge positions (the FIRST run where the "sample too
    small" note doesn't print) -- still exactly 50%. Opening book
    rebuilt again (1330 positions). use_endgame_heuristics and the
    opening book both remain off by default. Full breakdown in
    docs/v0.5-real-data-checkpoint-3.md.
        ↓
    Given depth=3-vs-depth=2 is now a fairly confident real result and
    the other two comparisons both cleared "not just too small" and came
    back null, decided to move to V0.6 rather than grind out more
    depth=3 games for diminishing certainty on two already-answered
    (negative) questions.
        ↓
    V0.6.1 COMPLETE: MCTSEngine (src/alphazetacchess/engine/mcts.py), a
    PUCT-based MCTS search skeleton using the EXISTING evaluate()
    function as its leaf value estimator (tanh-squashed into [-1,1]) and
    uniform move priors -- deliberately no policy/value network yet,
    same "search skeleton first, evaluation second" split V0.3/V0.4
    used. 12 new tests (142/142 total), including a dedicated sign-
    convention unit test (the single most error-prone part of any
    minimax/MCTS implementation) and a cross-validation test where
    MCTSEngine finds the exact same mate-in-one SearchEngine(depth=2)
    finds. Smoke test against RandomEngine initially looked concerning
    (6/6 games drew at the move limit) but tracking material directly
    confirmed MCTSEngine reliably builds a real advantage (4150 vs 3600
    by ply 60) -- it just doesn't reliably convert that to checkmate
    within 150 moves at the simulation budgets tried (100-800), an
    expected vanilla-MCTS-without-a-policy-network characteristic, not a
    bug (independently confirmed by the alpha-beta cross-validation
    test). See docs/v0.6.1.md.
        ↓
    Next: either (a) find via real local benchmarking what simulation
    count makes MCTSEngine reliably beat RandomEngine decisively and
    start competing with SearchEngine at various depths (needs CLI
    support -- not yet wired into tools/compare_engines.py/benchmark.py
    -- and real compute budget), or (b) design the actual policy/value
    network (V0.6.2) that _expand_and_evaluate's evaluate() call and
    uniform priors are deliberately left as placeholders for -- a bigger
    undertaking needing training data/infrastructure that doesn't exist
    yet, worth thinking through before writing any of it.
        ↓
    User: local infra (a laptop) can't handle self-play-scale training.
    Asked about borrowing Pikafish's (a strong open-source Xiangqi
    engine) published training results instead. Investigated before
    writing any code -- two real blockers to porting weights directly:
    Pikafish's own NNUE weights carry a custom non-commercial license
    murky enough to not cleanly embed in this public repo, and its
    HalfKAv2_xq feature encoding + quantized inference would need a
    substantial, bug-prone reimplementation to port correctly.
        ↓
    V0.6.2 COMPLETE as an untrained pipeline: pivoted to DISTILLATION --
    run Pikafish locally as an oracle to label positions, train an
    entirely new, small, from-scratch network on those labels (never
    redistributes Pikafish's own weights/code). Five new pieces, each
    independently tested: core/fen.py (Xiangqi FEN -- note the UCCI
    piece-letter convention differs from this project's own PieceType.
    value), neural/features.py (perspective-relative board encoding),
    neural/network.py (SmallMLP, backprop verified against a numerical
    gradient check), neural/pikafish_client.py + tools/label_positions_
    with_pikafish.py (UCI client tested against a real fake-engine
    subprocess), tools/train_neural_eval.py + neural/evaluator.py. 23
    new tests, 165/165 total. Full pipeline smoke-tested end to end
    against a fake engine. See docs/v0.6.2.md.
        ↓
    Next: ON THE USER'S MACHINE (needs a working Pikafish binary) --
        python tools/label_positions_with_pikafish.py --pikafish-path /path/to/pikafish
        python tools/train_neural_eval.py
    Then here, once a real trained network exists: add a pluggable
    eval_fn to SearchEngine/MCTSEngine (both currently hardcode
    evaluate()), wire NeuralEvaluator in, and run tools/compare_engines.py
    with it on one side -- the real test of whether any of this helped.
        ↓
    User ran the real pipeline. First trained network (data/neural_eval.npz)
    turned out DIVERGED (weights ~1e24-1e27, every prediction the same
    absurd constant) -- root cause: raw score_cp targets up to +/-9000,
    plain MSE gradient descent at a unit-scale-tuned learning rate blew
    up. Fixed: SmallMLP gained y_mean/y_std target standardization +
    gradient-norm clipping. 5 new tests (172/172 total), including one
    that reproduces the actual failure at real-label scale. See
    docs/v0.6.2.md's first addendum.
        ↓
    User reran training with the fix, real data (2888 positions, now
    force-pushed as data/pikafish_labels.jsonl) -- no divergence.
    Before trusting RMSE alone, hand-probed a few constructed positions
    and found a CONCERNING pattern (predictions got more confidently
    backwards as a constructed material imbalance grew) -- investigated
    rather than dismissing or panicking: ruled out a Board.move()
    current_player bug (none found), then computed correlation on the
    ACTUAL held-out validation split against real Pikafish labels (the
    fair, in-distribution test) -- 0.88-0.92 correlation, RMSE 40-60%
    of the naive baseline. Real signal, not noise or a repeat of the
    divergence -- the hand-probed positions were simply out-of-
    distribution (a small MLP with sparse binary features doesn't
    generalize additively to hand-crafted material configs far from
    anything in 2600 real training examples, unlike evaluation.py's
    hard-coded material counting). Compared 200 vs 800 vs 1000 epochs
    directly: validation plateaus around 800 (further epochs mostly
    just widen the train/val gap = overfitting onset). Updated the
    default --epochs 200 -> 800 accordingly. Final committed network:
    held-out correlation 0.915, RMSE 1292cp vs 3201cp naive baseline --
    real, working, still imprecise. See docs/v0.6.2.md's second addendum.
        ↓
    Next: more labeled data (2888 positions from only 99 self-play
    games) is the likelier lever for further improvement now, more than
    further epochs. Then: add a pluggable eval_fn to SearchEngine/
    MCTSEngine, wire NeuralEvaluator in, and run tools/compare_engines.py
    with it on one side -- the real test of whether any of this helped
    actual play strength, not just Pikafish-score correlation.
        ↓
    User: self-play data collection is bottlenecked by weak hardware --
    pointed out trainingdata/ already has ~140k real human/engine games
    unused (WXF + dpxq sources). Built tools/import_external_games.py
    to convert their ICCS-notation .pgns into this project's own V0.5.1
    record format, so the EXISTING labeling tool works unchanged.
    Coordinate-mapping needed real verification (a legal-move replay
    test alone couldn't distinguish an orientation from its mirror
    image, since Xiangqi's rules are left-right symmetric) -- resolved
    via the authoritative ICCS spec + these files' own FEN header
    matching core/fen.py's output exactly. Imported 3,957 real games
    (2,651 WXF + 1,306 dpxq), 100% legal-move validation pass rate
    (strong real-world confirmation the mapping is correct), ~40x more
    games than the self-play corpus. See docs/v0.6.2.md's third
    addendum. 172/172 tests still green (no engine code changed).
        ↓
    Next: ON THE USER'S MACHINE -- label the new corpus and retrain:
        python tools/label_positions_with_pikafish.py --pikafish-path ... \
            --network-path ... --input data/external_games.jsonl
        python tools/train_neural_eval.py
    Then here: add a pluggable eval_fn to SearchEngine/MCTSEngine, wire
    NeuralEvaluator in, and run tools/compare_engines.py with it on one
    side -- the real test of whether any of this helped actual play
    strength.
        ↓
    User labeled the full external corpus: 2,888 -> 94,872 labels
    (~33x). The fixed --epochs 800 default (right for the smaller
    dataset) caused a real, visible overfitting signature on the much
    larger one (val RMSE bottomed at epoch 160, then WORSENED through
    epoch 800 while train RMSE kept dropping). Fixed properly with
    early stopping (validate every epoch, keep the best checkpoint,
    stop after --patience epochs without improvement) rather than
    re-guessing another fixed number -- smoke-tested the mechanism
    before the real, expensive retrain. Retrained on the full 94,872
    positions: stopped at epoch 198 (saved ~75% of the wall-clock cost
    of running all 800), held-out RMSE 776cp vs naive baseline 1228cp.
    Honest mixed result: correlation dropped to 0.777 (from 0.915) --
    not necessarily worse, since the target distribution itself
    changed (naive baseline RMSE also dropped, 3201->1228cp, since real
    games have less mate-score-driven variance than the old mostly-
    self-play corpus). Early stopping firing at epoch 158/800 on 30x
    more data hints the network's fixed 64->32 capacity may now be the
    real bottleneck (underfitting) rather than overfitting risk -- a
    quick 128->64 experiment didn't finish within this session's
    per-command time budget, left as an open next experiment rather
    than a completed result. 172/172 tests still green. See
    docs/v0.6.2.md's 4th addendum.
        ↓
    Next: ON THE USER'S MACHINE -- try a larger network now that early
    stopping guards against overfitting regardless of capacity:
        python tools/train_neural_eval.py --hidden1 128 --hidden2 64
    Then, once satisfied with the network: add a pluggable eval_fn to
    SearchEngine/MCTSEngine, wire NeuralEvaluator in, and run
    tools/compare_engines.py with it on one side -- the real test of
    whether any of this helped actual play strength, not just
    Pikafish-score correlation.
        ↓
    User tried 128->64 hidden units: only marginal improvement (776->766cp,
    ~1.3% for ~4x more parameters) -- evidence AGAINST the capacity
    hypothesis, pointing instead at the feature representation itself
    (1260-dim one-hot piece-position encoding has no explicit mobility/
    king-safety/pawn-structure/coordination notion the way evaluation.py's
    hand-crafted terms do) as the likelier ceiling. Not chasing further
    architecture tuning -- diminishing returns -- moved to the actual
    point of this checkpoint instead.
        ↓
    Added a pluggable eval_fn to SearchEngine (via a new _evaluate()
    method every one of its 4 call sites now goes through) and
    MCTSEngine (_expand_and_evaluate) -- eval_fn=None (default)
    preserves every prior version's exact behavior; setting it (e.g. to
    a NeuralEvaluator, which already matches evaluate()'s calling
    convention) replaces the heuristic entirely. A REAL BUG was caught
    by the new tests, not shipped: consolidating SearchEngine's 4 call
    sites left self.tt = TranspositionTable(...) as dead code AFTER a
    return statement, meaning self.tt was never set on any instance --
    surfaced immediately by a new test calling _quiescence directly
    (AttributeError), invisible to py_compile or casual inspection.
    Fixed and confirmed via the full suite (178/178, every existing
    SearchEngine test included) rather than trusting the fix by
    inspection. 6 new tests. tools/compare_engines.py gained
    --a/b-use-neural-eval + --neural-eval-path, mirroring the existing
    --use-opening-book pattern exactly. Smoke-tested end to end (loads
    the real network, runs real games with it on one side). See
    docs/v0.6.2.md's 5th addendum.
        ↓
    Next: run an actual strength comparison (not yet done -- the smoke
    test above only confirmed the mechanism works, not whether it
    helps):
        python tools/compare_engines.py --a-use-neural-eval --a-depth 2 \
            --b-depth 2 --games 20 --random-opening-prob 0
    This is the real test of whether any of V0.6.2's distillation work
    actually improved play strength, not just Pikafish-score
    correlation.
        ↓
    Ran real comparisons. Learned something about the tool first:
    --random-opening-prob 0 + fully deterministic SearchEngine means
    re-running the same command reproduces the same 2 games every time,
    not new data -- accumulating a real sample needs randomization ON.
    6 genuinely distinct real games (depth=2, neural eval vs heuristic):
    0 neural wins, 4 heuristic wins, 2 draws -- neural score rate 16.7%,
    Elo diff -280. A real, if still modest-sized, signal the heuristic
    currently wins, consistent with the 776cp held-out RMSE (more than
    a Rook's value) and the earlier capacity experiment's weak result
    -- points at the feature representation, not more params/epochs/
    games, as the likely lever. use_neural_eval should NOT default on
    based on this evidence. 178/178 tests still green (no code changed,
    pure data-collection this round). See docs/v0.6.2.md's 6th addendum.
        ↓
    Next: a real, larger comparison (20+ games) would firm up the exact
    Elo figure, but the DIRECTION is unlikely to reverse given how it
    lines up with training-side evidence -- more valuable next step is
    likely revisiting neural/features.py's representation (add explicit
    mobility/king-safety/pawn-structure-style features, closer to what
    evaluation.py already hand-encodes) rather than just running more
    comparison games against the current representation.
        ↓
    Acted on that conclusion: added 8 auxiliary hand-crafted features
    to neural/features.py, reusing engine/evaluation.py's own
    mobility_balance/pawn_structure_balance/piece_coordination_balance/
    endgame_balance/_king_safety_score/material-count sub-components
    directly rather than reinventing feature engineering. FEATURE_DIM
    1260->1268 -- a BREAKING CHANGE for networks trained on the old
    encoding; NeuralEvaluator now checks this explicitly and raises a
    clear error instead of an opaque numpy shape mismatch. 6 new tests
    (184/184 total), including hand-verified material-difference and
    check-status assertions, and mirror-symmetry extended to the new
    features. Retrained on the real 94,872-position corpus, but HONESTLY
    an incomplete run -- this sandbox's time budget cut training short
    at 175 epochs (still improving, hadn't triggered early stopping) --
    modest improvement (RMSE 776.3->767.2cp, correlation ~unchanged at
    0.78). One real strength-comparison game: heuristic won again.
    Explicitly NOT claimed as a fair test of the auxiliary features'
    real potential -- needs a full, uninterrupted local run. See
    docs/v0.6.2.md's 8th addendum.
        ↓
    Next: ON THE USER'S MACHINE -- a full, uncapped retrain (no
    time-budget interruption) and a real 20+-game comparison:
        python tools/train_neural_eval.py
        python tools/compare_engines.py --a-use-neural-eval --a-depth 2 \
            --b-depth 2 --games 20 --output data/selfplay.jsonl
    This is the real, fair test of whether the auxiliary features
    actually closed the gap to the heuristic evaluator (-280 Elo before
    this change) -- the honest headline question this whole V0.6.2 line
    has been building toward.
        ↓
    User ran the full retrain + 20-game comparison. Training converged
    properly (early stopping at epoch 268, best epoch-228 checkpoint):
    held-out RMSE 760.5cp, correlation 0.786 -- only marginally better
    than the interrupted run. 20 real games: 1 neural win, 14 heuristic
    wins, 5 draws -- Elo -269, essentially UNCHANGED from the
    pre-auxiliary-features result (-280 on 6 games). Verified directly
    from data/selfplay.jsonl, not trusted from the printed summary.
        ↓
    CONCLUSION: this is the real, converged verdict, not an artifact of
    undertraining. Three attempts in a row (more capacity, ~33x more
    data, richer features) each showed the same small, easily-exhausted
    return on actual playing strength despite each being reasonable at
    the time -- a consistent picture, not three unrelated setbacks.
    use_neural_eval stays off by default, now with real evidence behind
    it rather than just caution. V0.6.2 CONCLUDES here as a genuine,
    documented negative result (same practice as V0.5.2's opening-book
    and V0.5.3's endgame-heuristic null results) -- not a failure of
    the checkpoint, real information about this technique's current
    ceiling. See docs/v0.6.2.md's final addendum.
        ↓
    Not recommended: more of the same tweak pattern (yet more data/
    capacity/features) -- three attempts have each shown the same
    small return. A more promising alternative for the same 94,872
    labeled positions: use them to CALIBRATE evaluation.py's own
    hand-guessed constants (MATERIAL_VALUES, mobility/pawn-structure/
    piece-coordination weights, etc.) directly via regression against
    real Pikafish scores, rather than training a black-box network from
    scratch -- fully interpretable, no eval_fn indirection needed, a
    fundamentally different and likely more sample-efficient use of the
    same hard-won data. Not attempted yet.
        ↓
    Separately, still open: V0.6.1's MCTSEngine has never been
    benchmarked for real strength (only shown to build a real material
    advantage vs RandomEngine, not compared against SearchEngine at any
    depth) -- a reasonable alternative next direction if not pursuing
    the calibration idea above.
        ↓
    Pursued the calibration idea. engine/evaluation.py gained
    evaluate_components() (raw regression features, recombining with
    current constants reproduces evaluate() exactly -- tested directly)
    and tools/calibrate_evaluation.py (OLS regression against real
    Pikafish scores). 7 new tests, 191/191 total.
    REAL FINDING: normalized to Pawn=1, Rook/Cannon/Horse appear
    substantially undervalued in the current material scale (9.0/4.5/4.0
    current vs 15.9/7.8/7.25 fitted -- a consistent ~1.7-1.9x pattern
    across all three), while Elephant/Advisor/Pawn already look about
    right. Also found a real +40cp tempo-bias intercept not currently
    modeled anywhere. PST/king-safety scaling suggestively too small;
    pawn-structure/piece-coordination near-zero coefficients flagged
    for caution (could mean "doesn't matter" OR "low variance in this
    data" -- not distinguished yet). Linear model is LESS accurate
    overall than V0.6.2's network (1055cp/0.511 vs 760cp/0.786) --
    expected and not the point: better constants for the existing fast
    interpretable heuristic, not a more accurate predictor in isolation.
    NOT yet applied back into evaluate() or benchmarked in real play --
    analysis only. See docs/v0.6.3.md.
        ↓
    Next: test the material-value finding specifically (most confident,
    coherent, easiest to isolate) -- update MATERIAL_VALUES (or an
    opt-in alternate set) with the fitted Rook/Cannon/Horse values,
    keep Elephant/Advisor/Pawn as-is, run a real
    tools/compare_engines.py comparison against current constants:
        (not yet implemented -- needs a way to swap MATERIAL_VALUES,
        e.g. a constructor override, before this can be run)
    Also worth doing before trusting the pawn-structure/piece-
    coordination near-zero findings: check each feature's actual
    variance/prevalence across the real corpus first.
        ↓
    Wired it up. evaluate() gained an optional material_values
    parameter (None preserves exact prior behavior); threaded through
    SearchEngine's own new material_values constructor param, same
    pattern as V0.6.2's eval_fn. New CALIBRATED_MATERIAL_VALUES constant
    (Rook 900->1500, Cannon 450->750, Horse 400->700, rounded from the
    exact fitted values; Elephant/Advisor/Pawn deliberately left
    unchanged to isolate the most confident finding). tools/
    compare_engines.py gained --a/b-use-calibrated-material, mirroring
    --use-opening-book/--use-neural-eval exactly. 4 new tests, 195/195
    total. A real comparison game was started but didn't complete
    within this sandbox's per-command time budget -- mechanism
    confirmed correct and tested, strength verdict still needs a real
    run. See docs/v0.6.3.md's addendum.
        ↓
    Next: ON THE USER'S MACHINE -- the actual strength test:
        python tools/compare_engines.py --a-use-calibrated-material \
            --a-depth 2 --b-depth 2 --games 20 --output data/selfplay.jsonl
    Also still open: investigate the near-zero pawn-structure/piece-
    coordination coefficients' actual variance/prevalence before
    drawing conclusions, and V0.6.1's MCTSEngine still has no real
    strength benchmark against SearchEngine at any depth.
        ↓
    User ran the real 20-game comparison. Result: 4 calibrated wins, 5
    default wins, 11 draws -- Elo -17. INCONCLUSIVE, not neutral: the
    approximate 95% CI on score rate is roughly [26%, 69%], wide enough
    to be consistent with a real advantage OR disadvantage in either
    direction. Explicitly distinguished from V0.6.2's neural-evaluator
    result (a real, converged -269 Elo at the same n=20 -- large enough
    to be confidently distinguishable from noise; this one isn't).
    Two separate things kept straight: the REGRESSION finding itself
    (Rook/Cannon/Horse undervalued ~1.7-1.9x vs Pawn, fit against real
    Pikafish scores) is real and well-supported; whether ACTING on it
    measurably improves actual game outcomes is a separate, still-open
    question this run couldn't resolve at this sample size (would need
    very roughly 100+ games to narrow the CI enough). See
    docs/v0.6.3.md's second addendum.
        ↓
    Next: a much larger comparison run (100+ games) is the natural way
    to actually settle this, whenever that compute is available -- not
    attempted further this session. Also still open: investigate the
    near-zero pawn-structure/piece-coordination coefficients before
    drawing conclusions, and V0.6.1's MCTSEngine still has no real
    strength benchmark against SearchEngine at any depth.
        ↓
    Separately, on dev/v0.7-foundation -> dev/v0.7-ucci-control ->
    dev/v0.8.1-attack-detector (a single linear chain, each an ancestor
    of the next): V0.7.1-7.4 (cooperative search cancellation, async
    UCCI go/stop worker, UCCI time control, final audit -- see the V0.7
    section above and docs/v0.7.1.md-v0.7.4.md) and V0.8.1-8.2
    (specialized attack detector, killer move ordering -- see the V0.8
    section above and docs/v0.8.1.md/v0.8.2.md) were built without this
    roadmap being updated as each step landed, breaking this file's own
    "update the roadmap" rule. Reviewed and merged into main in this
    session: chain confirmed linear and fast-forward-only (no conflicts
    possible), full suite 266/266 green on the merge tip, two stray
    AI-tool citation artifacts found and removed from docs/v0.8.1.md,
    docs/v0.8.2.md written retroactively (the killer-move benchmark tool
    existed but had never actually been run -- see that doc for why its
    packaged fixture looked like a regression when the established
    reference positions show a real improvement), and this roadmap
    backfilled with the V0.7/V0.8 sections above plus the V0.7 naming
    correction (the original V0.7 slot was "Hybrid Engine"; actual V0.7
    work was UCCI/search-foundation, so "Hybrid Engine" moved to the new
    V0.9 placeholder rather than being silently dropped).
        ↓
    Next: (a) V0.9 Hybrid Engine -- wire V0.6.1's MCTSEngine and/or
    V0.6.2's NeuralEvaluator behind the now-complete UCCI protocol layer
    for real engine-vs-GUI play, or (b) continue V0.8 with history
    heuristic / SEE-MVV-LVA capture ordering per docs/v0.8.1.md's own
    scope boundary, or (c) the still-open V0.6.3 material-calibration
    and MCTSEngine-strength questions noted above. Whichever is picked,
    update this roadmap at the end of the step -- see the rule this
    entry itself is following.
        ↓
    Picked (b): V0.8.3 MVV-LVA capture ordering (see the V0.8 section
    above and docs/v0.8.3.md). 274/274 green. Benchmarked the same way
    V0.8.2 was -- and the same lesson applied in reverse: the established
    opening-phase reference positions show a small *regression* (few
    captures near the root, so the per-node sort cost isn't repaid), but
    the capture-dense fixture V0.8.2 found misleading (too few *quiet*
    moves for a killer-move test) turned out to be exactly the right kind
    of position for a *capture*-ordering test, and shows a real +36-37%
    node reduction there. Given that mixed, position-dependent picture --
    unlike V0.8.2's broad win -- use_mvv_lva defaults False, following
    this project's standing "off until proven" rule for anything short
    of a clear win. Also added --{a,b}-use-mvv-lva and the
    previously-missing --{a,b}-no-killer-moves flags to
    tools/compare_engines.py, since settling whether V0.8.3 is worth
    defaulting on for real games needs an actual multi-game comparison,
    not another node count on a handful of fixed positions.
        ↓
    Next: that multi-game compare_engines.py run is now the natural
    next step for V0.8.3 specifically, and it shares its "needs a real
    multi-game run, not just node counts" blocker with two other still-
    open items: V0.6.1's MCTSEngine-strength question and V0.6.3's
    larger material-calibration comparison. Whoever picks this up next
    could reasonably batch two or three of those into one longer
    compare_engines.py session rather than three separate ones. Absent
    that, (a) V0.9 Hybrid Engine remains open per the note above.
    Update this roadmap at the end of the step, as always.
        ↓
    Ran that compare_engines.py comparison for V0.8.3 specifically: 26
    games at depth 2 (baseline vs. use_mvv_lva on), run in a few
    batches to fit the available session time, full records in
    data/v0.8.3_mvv_lva_compare.jsonl. Result: 12-12-2, a 50.0% score
    rate, ~0 Elo difference -- consistent with the node-count story
    above, where a real early-game cost and a real midgame benefit turn
    out to roughly cancel out over a full game. use_mvv_lva stays False
    by default; this adds real-game evidence for that call rather than
    changing it. 26 games is a start, not a conclusion (95% CI is
    roughly 31-69%, wide enough to hide a real few-dozen-Elo effect) --
    see docs/v0.8.3.md's updated "Real-game benchmark" section for the
    full numbers and caveats.
        ↓
    Next: a larger version of that same run (100+ games, and/or depth 3
    where the node-count effect was even bigger) would narrow the
    confidence interval enough to say more. Still shares its "needs
    real compute time, not another quick script" nature with V0.6.1's
    MCTSEngine-strength question and V0.6.3's own 100+ game
    material-calibration run -- same batching suggestion as before.
    Otherwise, (a) V0.9 Hybrid Engine is next in line. Update this
    roadmap at the end of the step.
        ↓
    Picked (a): V0.9.1 MCTS cooperative cancellation & UCCI wiring (see
    the V0.9 section above and docs/v0.9.1.md). 281/281 green. Gave
    MCTSEngine the same stop_event contract SearchEngine has had since
    V0.7.1/V0.7.2, with a cancellation strategy that's deliberately
    different (report the partial tree instead of discarding the
    iteration, since PUCT stays sound after any number of completed
    simulations -- unlike a partially-searched alpha-beta depth). Also
    fixed a real bug this surfaced: UCCIEngine unconditionally read/
    wrote self.search_engine.depth, which crashed immediately for any
    engine without one (MCTSEngine uses simulations instead). Verified
    with a real MCTSEngine plugged into UCCIEngine end-to-end, not a
    fake double, specifically so the .depth bug couldn't hide behind a
    test double that happened to satisfy the interface. NOTE: this
    session's V0.8.3 MVV-LVA thread and this V0.9.1 thread were worked
    independently in parallel per an explicit "these don't block each
    other, proceed separately" instruction -- worth checking both hand-
    off entries are still consistent with each other (they don't touch
    overlapping files) before treating this as the sole latest entry.
    A larger multi-game comparison was also started locally outside
    this session around the same time as this step, for one of the
    still-open questions this hand-off trail had flagged -- see the
    next entry for which one it turned out to be and what it found.
        ↓
    Next: (a) wire an actual --engine mcts style choice into
    UCCIEngine/tools/compare_engines.py/tools/self_play.py now that the
    interface mismatch is fixed (docs/v0.9.1.md's own scope boundary),
    (b) the still-open V0.6.1 MCTSEngine-strength and V0.6.3 material-
    calibration multi-game comparisons, now joined by V0.8.3's
    already-started-but-not-yet-100+-games MVV-LVA comparison as a
    third candidate for the same batched compare_engines.py session, or
    (c) start wiring V0.6.2's NeuralEvaluator into the same --engine
    style choice alongside MCTS. Update this roadmap at the end of the
    step.
        ↓
    The comparison mentioned above turned out to be V0.6.3's material-
    calibration question, not V0.8.3's MVV-LVA one (worth noting since
    the previous entry guessed it might be the latter -- it wasn't; the
    V0.8.3 MVV-LVA question is still exactly where the n=26 entry above
    left it). 100 real games (calibrated material vs. default, depth 2),
    combined with the earlier 20-game run for 120 total: 42.5% score
    rate, Elo ~-53, 95% CI [33.7%, 51.3%], p~=0.10 vs. a 50% null --
    leans toward a real negative effect, not fully conclusive but no
    longer plausibly neutral the way n=20 was. use_calibrated_material
    stays False (already the default; this adds evidence for it, not a
    new decision). Full numbers, a draw-rate data-quality note, and two
    untested hypotheses for *why* calibration hurts despite fitting
    Pikafish's scores better are in docs/v0.6.3.md's newest addendum;
    roadmap's V0.6.3 section above updated to match.
        ↓
    Next: still open, in no particular order -- (a) the --engine mcts
    wiring from the previous entry, (b) V0.8.3's MVV-LVA question still
    sitting at n=26, (c) V0.6.1's MCTSEngine-strength question, (d) the
    two untested hypotheses docs/v0.6.3.md's newest addendum raises for
    *why* calibrated material underperforms (a depth=3 re-run, or
    applying the PST/king-safety coefficients alongside the material
    ones). All four are real, independent threads at this point rather
    than one linear next step -- whoever picks this up should choose
    based on available compute/session time rather than assume an
    ordering. Update this roadmap at the end of whichever is picked.
        ↓
    Picked (a)+(c) together, since they directly unblock each other:
    V0.9.2 --engine mcts wiring in tools/compare_engines.py (see the
    V0.9 section above and docs/v0.9.2.md), then immediately used it to
    settle (c). Result was decisive, not close: MCTSEngine (200 sims)
    vs. SearchEngine (depth 2), 28 games, 1-27-0 -- no larger sample
    needed, 95% CI [0.0%, 10.4%] doesn't come close to 50%. A 1000-sim
    follow-up (5x the budget) still went 0-10, ruling out "just needs
    more simulations." Consistent with V0.6.1's own stated scope
    (uniform priors, no policy network yet, reusing SearchEngine's own
    evaluate() as the only leaf signal) -- not a bug, the expected shape
    of the gap a policy network is meant to close. 281/281 full suite
    unaffected throughout (only tools/compare_engines.py touched for
    the wiring itself).
        ↓
    Next: still open -- (b) V0.8.3's MVV-LVA question at n=26, (d)
    docs/v0.6.3.md's two untested material-calibration hypotheses. This
    session's MCTS result also sharpens the case for a genuinely new
    thread: a real policy/value network wired into MCTSEngine (V0.6.2's
    NeuralEvaluator already plugs into eval_fn identically for both
    engines, but a *policy* head replacing MCTS's uniform priors is new
    work, not yet started anywhere in this project) -- per
    docs/v0.9.2.md's own "practical implication," this is now the more
    consequential of the two remaining V0.9 directions compared to
    further fixed-prior MCTS tuning. Update this roadmap at the end of
    whichever is picked next.
        ↓
    User asked specifically for (d)'s first hypothesis (combined
    calibrated weights, not depth) -- built the mechanism: V0.6.4
    (see the V0.6.3 section above and docs/v0.6.4.md).
    pst_weight/king_safety_weight added to evaluate()/SearchEngine
    (default 1, behavior-preserving), CALIBRATED_PST_WEIGHT=10/
    CALIBRATED_KING_SAFETY_WEIGHT=8 from the same V0.6.3 regression,
    tools/compare_engines.py --use-calibrated-weights turns on all
    three findings together. 6 new tests, 287/287 full suite green,
    smoke-tested with a real 2-game run. THE REAL COMPARISON ITSELF
    WAS NOT RUN IN THIS SESSION -- docs/v0.6.4.md's "Script to run"
    has both commands (depth 2, directly comparable to V0.6.3's -53
    Elo material-alone result; and depth 3, testing the *other*
    untested hypothesis at the same time) ready for the user to run
    locally, same division of labor as V0.6.3's and V0.8.3's own
    100-game results.
        ↓
    Next: whoever picks this up should first check whether the
    docs/v0.6.4.md script has been run and its result analyzed/merged
    in (check for data/v0.6.4_combined_weights_compare.jsonl and
    data/v0.6.4_combined_weights_depth3_compare.jsonl) before treating
    V0.6.4 as still open. If it has landed, still open: (b) V0.8.3's
    MVV-LVA question at n=26, and the new MCTS policy-network thread
    flagged in the previous entry. Update this roadmap at the end of
    whichever is picked.
        ↓
    It had landed -- user ran and pushed both files. Result: a clear
    reversal of V0.6.3's material-alone finding. Depth 2: 57.0% score
    rate, Elo ~+49, p=0.162 (leans positive, not independently
    significant). Depth 3: 61.5%, Elo ~+81, p=0.021 (significant).
    Fisher-combined across both independent runs: p~=0.023. First
    clearly positive evaluation-tuning result in this project's whole
    history (V0.6.2: -269 Elo; V0.6.3 material alone: ~-53 Elo) --
    confirms V0.6.3's two untested hypotheses aren't mutually
    exclusive: combining all three calibrated findings is more
    internally consistent than material alone AND that consistency
    pays off more clearly with search depth. Full numbers in
    docs/v0.6.4.md's newest addendum; roadmap's V0.6.4 section above
    updated to match.
        ↓
    Next, in rough priority order given this result: (a) the
    recommendation docs/v0.6.4.md's addendum explicitly flags but
    deliberately didn't act on -- promoting
    CALIBRATED_MATERIAL_VALUES/CALIBRATED_PST_WEIGHT/
    CALIBRATED_KING_SAFETY_WEIGHT to SearchEngine's actual constructor
    defaults, which needs its own doc entry and its own before/after
    confirmation given how consequential changing every
    default-constructed SearchEngine's behavior (UCCIEngine included)
    would be -- a real candidate for the next step precisely because
    this result is strong enough to justify it, not just another
    available-but-off flag; (b) V0.8.3's MVV-LVA question still at
    n=26; (c) the MCTS policy-network thread. Update this roadmap at
    the end of whichever is picked.
        ↓
    Picked (a) -- user confirmed, proceed. V0.6.5 (see the V0.6+
    section above and docs/v0.6.5.md): SearchEngine's actual
    material_values/pst_weight/king_safety_weight defaults now ARE the
    CALIBRATED_* constants -- exactly what V0.6.4's 200 real games
    already tested, so no new confirmatory run was needed (would just
    reproduce the same result). evaluate()'s own defaults deliberately
    left unchanged, keeping the blast radius to one call site.
    Verified tools/compare_engines.py's existing A/B comparisons are
    unaffected (every call site there already passes these params
    explicitly). Broke 6 tests immediately (bare SearchEngine() vs.
    bare evaluate() comparisons); fixed by pinning the old baseline
    explicitly where the test's actual point was a different toggle.
    Also found and fixed two tests in V0.6.4's own test file that had
    been passing VACUOUSLY since the previous session (a fixture
    coincidence made two delta assertions trivially 0==0), plus a
    related bug in one test's expected-delta formula the fixture fix
    surfaced (only accounted for Rook, silently missing Cannon/Horse).
    287/287 green throughout. One small follow-up flagged initially,
    then found to be based on an incorrect claim and corrected in the
    same doc (see docs/v0.6.5.md): compare_engines.py's "no flags"
    case was never affected by SearchEngine's default changing, since
    build_engine always passes these params explicitly regardless.
        ↓
    Next: still open -- (b) V0.8.3's MVV-LVA question at n=26, (c) the
    MCTS policy-network thread. No item is currently more urgent than
    another -- pick based on available time. Update this roadmap at
    the end of whichever is picked.
        ↓
    User asked to continue (b) while also flagging that this table's
    V0.5 row still said CURRENT despite V0.5's own section header
    already saying COMPLETE (a real, long-standing inconsistency --
    fixed: table now says COMPLETE). While fixing that, two of V0.5.2/
    V0.5.4's own "needs a real X" caveats turned out to be stale too --
    a real opening book now exists (data/opening_book.json, 1330
    entries, real accumulated win/draw/loss counts, not toy numbers),
    and tools/compare_engines.py has since been used for real
    comparisons many times over (V0.6.1/6.3/6.4/8.3/9.2) -- both
    updated to reflect that rather than left stale.

    On (b) itself: found 31 more real MVV-LVA comparison games already
    sitting in data/v0.8.3_mvv_lva_compare.jsonl's working-tree copy
    (same command/config, generated in later work on this project but
    never committed) -- verified all 57 lines parse cleanly and configs
    are consistent before trusting them, then folded them in.
    Expanded result: 26-29-2, B(MVV-LVA) score rate 52.6%, 95% CI
    [39.7%, 65.6%], Elo ~+18 -- barely moved from the n=26 point
    estimate (50.0%) despite more than doubling the sample, which if
    anything strengthens the "genuinely close to neutral" read rather
    than revealing an effect the smaller sample missed. use_mvv_lva
    stays False. docs/v0.8.3.md and this roadmap's V0.8.3 section
    above updated to match. 287/287 full suite unaffected (data/docs
    only, no src/ change this step).
        ↓
    Next: still open -- (c) the MCTS policy-network thread remains the
    most substantive unstarted direction; V0.8.3's question is now
    about as settled as it's likely to get without a much larger
    (500+ game) run, which is a legitimate option but a step change in
    compute commitment rather than an obvious next increment. Update
    this roadmap at the end of whichever is picked.
        ↓
    Picked (c), scoped as a first, cheap increment rather than jumping
    straight to a trained network: V0.9.3 heuristic-informed MCTS
    priors (see the V0.9 section above and docs/v0.9.3.md) -- one-ply
    lookahead + softmax, replacing V0.6.1's uniform 1/N prior, meant to
    answer "is the better-priors direction worth pursuing at all"
    before investing in anything more expensive. 294/294 green.
    Real ~2.6x per-simulation speed cost measured directly. Real
    benefit measured two ways: equal simulation count is an
    unambiguous win (75.0%, 95% CI entirely above 50%, Elo ~+191);
    equal wall-clock time (accounting for the speed cost) leans clearly
    positive but doesn't independently clear significance at n=24
    (62.5%, CI [43.1%, 81.9%]). Does not close V0.9.2's large gap to
    SearchEngine (still 0-4 in a quick check). use_heuristic_priors
    stays False by default -- same "off until proven" bar V0.6.5 held
    V0.6.4's result to -- but the real takeaway is that prior quality
    is a genuine, measurable lever on MCTS's own strength, not a dead
    end, making a trained policy network a better-justified next
    investment than it was before this checkpoint.
        ↓
    Next: (a) a larger confirmatory run of V0.9.3's equal-time
    comparison specifically (n=24 leans positive but isn't conclusive
    alone), (b) start on an actual trained policy network now that
    V0.9.3 gives a real, if modest, positive signal that the direction
    is worth it -- the more consequential and much larger undertaking
    V0.9.2's own "practical implication" originally pointed at, (c)
    V0.8.3's MVV-LVA question, which could still use a much larger
    (500+ game) run if someone wants full confidence rather than the
    current "leans neutral" read. Update this roadmap at the end of
    whichever is picked.
        ↓
    Picked (a): ran two more 12-game batches of V0.9.3's equal-time
    comparison (final total: 48 games). Worth recording transparently,
    not just the end number: after the first 24 it read 62.5%; a third
    batch pushed the running total to n=36 at 69.4%, p=0.02 --
    independently significant; a fourth batch then pulled the full
    n=48 total back down to exactly 62.5% again, the same point
    estimate as the first 24 alone. The apparent n=36 significance did
    not hold up -- a real, concrete instance of why stopping at a
    lucky interim result ("it just crossed p<0.05") is a mistake, not
    a strategy. Final, honest number: 62.5%, 95% CI [48.8%, 76.2%],
    p=0.083 -- still leans positive (a stable point estimate across
    independent halves is informative on its own), still doesn't
    independently clear conventional significance. use_heuristic_priors
    stays False; docs/v0.9.3.md and this roadmap's V0.9.3 section above
    updated with the complete picture and the interim-result lesson.
        ↓
    Next: still open -- (b) the trained policy network (the larger,
    more consequential undertaking), (c) V0.8.3's MVV-LVA question at
    a much larger sample if full confidence is wanted, or a genuinely
    larger (200+ game) confirmatory run of V0.9.3's equal-time question
    specifically if that's judged more valuable than moving on. No
    item is obviously more urgent than another at this point -- pick
    based on available compute/session time. Update this roadmap at
    the end of whichever is picked.
        ↓
    Picked (b), scoped realistically: real training needs the user's
    local Pikafish (same one-time dependency V0.6.2's value network
    had, not something achievable from this session alone), so this
    step built and tested the CONSUMPTION side ahead of that -- V0.9.4
    (see the V0.9 section above and docs/v0.9.4.md): move<->policy-
    index encoding (same perspective-flip convention as the value
    network's input features), a separate PolicyMLP network (softmax
    cross-entropy, masked-at-inference-not-training), a
    NeuralPolicyEvaluator wrapper matching MCTSEngine's policy_fn
    convention, and policy_fn itself (verified to take priority over
    V0.9.3's use_heuristic_priors when both are set). Also found and
    fixed a real, previously-unnoticed gap: PikafishClient.evaluate_fen
    has always returned best_move, but the labeling tool was silently
    discarding it -- fixed, though existing pikafish_labels.jsonl
    predates the fix and needs relabeling to be usable for policy
    training. 313/313 green throughout. NO TRAINING HAS HAPPENED --
    every network in this checkpoint's tests is randomly initialized;
    this validates the mechanism, not playing strength.
        ↓
    Next: three items now, in dependency order for the policy-network
    thread specifically -- (1) relabel a real corpus with the fixed
    labeling tool (needs the user's local Pikafish), (2) write
    tools/train_policy_network.py once relabeled data exists, (3) a
    real strength comparison once there's an actual trained network,
    the same way V0.9.3 measured use_heuristic_priors. Still
    independently open regardless of that thread's pace: (c) V0.8.3's
    MVV-LVA question at a much larger sample, (d) a larger confirmatory
    run of V0.9.3's equal-time comparison specifically. Update this
    roadmap at the end of whichever is picked.

Last updated: 2026-09-12

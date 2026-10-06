# AlphaZetaChess Current Progress

Snapshot date: 2026-10-05

Starting revision: `dbb9ff9`; this checkpoint's changes are in the current worktree.

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

The original 20-game single-opening result remains in
`data/v0.10_depth4_vs_depth3.jsonl`: colors balanced, 10 wins and 10 losses for depth
4, no draws. It is inconclusive and every game used the same deterministic opening.

A follow-up played 100 games with default opening randomization (up to 10 opening
plies, 30% random legal-move probability per ply), alternating colors. Depth 4 played
Red in 50 and Black in 50. From depth 4's perspective the result was **60 wins, 37
losses, and 3 draws**: 61.5% score and an Elo-style point estimate of **+81**. A
20,000-resample, game-level percentile bootstrap gives a 95% score interval of
**52.0–71.0%**, corresponding to approximately **+14 to +156 Elo**. There were 97
distinct first-10-ply move sequences among the 100 games. All records were replayed
from the standard initial board; all 100 passed side-to-move, move-legality, and
recorded move-count checks. The three draws all reached the 150-ply move cap.
By color, depth 4 scored 26 wins, 22 losses, and 2 draws as Red, and 34 wins, 15
losses, and 1 draw as Black; the randomized openings were not paired across colors.

This single randomized match is suggestive, not a definitive strength claim. The
interval is conditional on this sample and does not capture all uncertainty in opening
selection or engine behavior. A separate run using the same openings with colors
mirrored was run as the paired follow-up below. The complete records are in
`data/v0.10_depth4_vs_depth3_multiopening_100.jsonl`; the first 20-game result is kept
separately and was not included in these statistics. The 100-game run used independent
worker JSONL files and merged them only after all workers had finished and the records
had been validated. The recorded match span was about 5 hours 18 minutes.

### Paired fixed-opening follow-up

To control color and opening variation, sampled 10 distinct positions after the first
10 plies of the randomized 100-game match, then played every position twice: once with
depth 4 as Red and once as Black. Depth 4 scored **11 wins, 5 losses, and 4 draws**
(65.0%, Elo-style estimate **+108**). The 95% percentile bootstrap, resampling the
10 opening pairs, was **52.5–77.5%** (approximately **+17 to +215 Elo**). By color,
depth 4 scored 7 wins, 1 loss, 2 draws as Red, and 4 wins, 4 losses, 2 draws as Black.
The outcome difference between colors is descriptive only; with 10 openings it is
highly uncertain.

All 20 game records were replayed and validated for legal moves, turn order, terminal
result, move limit, and exact color-swapped starting positions. The per-game JSONL is
`data/v0.10_depth4_vs_depth3_paired_10openings.jsonl`; its manifest records the source
positions, their 10-ply prefixes, and seed. The sample reuses positions selected from
the prior match, and 10 opening pairs remain a small sample. The result is encouraging
but not conclusive, nor independent confirmation of the randomized 100-game result.
The paired run took about 122 minutes.

### External-game opening follow-up

The repository contains 3,957 legally imported human/engine games in
`data/external_games.jsonl`, with 2,269 distinct legal first-10-ply prefixes. An
additional 10-opening, 20-game paired comparison used this independent corpus (depth 4
played each resulting position once as Red and once as Black). With baseline
SearchEngine settings, depth 4 scored **14 wins, 6 losses, and 0 draws** (70% score,
Elo-style estimate **+147**). The paired bootstrap 95% score interval was **50–90%**,
equivalent to approximately **0 to +382 Elo**. Depth 4 scored 7 wins and 3 losses as
Red, and 7 wins and 3 losses as Black.

All 20 records passed replay validation, and all 10 openings were played from the same
starting position with colors swapped. The per-game data and source-opening manifest
are `data/v0.10_depth4_vs_depth3_external_paired_10openings.jsonl` and
`data/v0.10_depth4_vs_depth3_external_paired_10openings.jsonl.manifest.json`. The
sample is small and its 95% interval is wide; this is suggestive, not a confirmed Elo
gain. Together with the earlier paired sample, it motivates expanding the paired
opening count, not claiming a definitive improvement. This run took about 164 minutes.

### Expanded external-game opening match

To increase the independent paired sample, another 20 distinct 10-ply positions were
sampled from the 3,957-game imported human/engine corpus. None overlap the prior
10-opening sample. Each position was played once with depth 4 as Red and once as Black
(40 games total), using baseline SearchEngine settings. Depth 4 scored **24 wins, 10
losses, and 6 draws** (67.5%, Elo-style estimate **+127**). Resampling the 20 opening
pairs gives a 95% score interval of **51.25–82.5%** (approximately **+9 to +269 Elo**).
Depth 4 had identical color splits: **12 wins, 5 losses, 3 draws** both as Red and as
Black. All six draws reached the 150-ply move cap.

All 40 games passed replay validation for legal moves, side-to-move, terminal results,
move limit, and identical start positions within each color-swapped pair. The records
and manifest are `data/v0.10_depth4_vs_depth3_external_paired_20openings.jsonl` and
`data/v0.10_depth4_vs_depth3_external_paired_20openings.jsonl.manifest.json`. The run
took about 240 minutes.

Across both non-overlapping external samples (30 opening pairs, 60 games), the
descriptive combined result is **38 wins, 16 losses, and 6 draws** (68.3%, Elo-style
estimate **+134**). A paired bootstrap over the 30 openings gives a 95% score interval
of **55.8–80.0%** (about **+41 to +241 Elo**). This combined interval is still
conditional on the imported-game corpus and these baseline settings; it is suggestive
evidence, not a universal strength estimate or proof that depth alone caused the
difference.

### Pikafish equal-time opponent match

Added a UCI-backed `PikafishEngine` adapter and a paired-opening match runner. A
depth-4 pilot showed that matching nominal depth was not computationally comparable:
Pikafish completed the initial-position search almost immediately while AlphaZeta's
depth-4 search took about 2.4 seconds. The completed match therefore used a 500 ms
per-move budget for both engines, with AlphaZeta's iterative search stopped by a timer
and Pikafish given UCI `go movetime 500`. Each of 10 distinct 10-ply positions from
`data/external_games.jsonl` was played twice, with colors swapped (20 games).

Pikafish scored **19 wins, 1 loss, and 0 draws** (95%, Elo-style point estimate
**+512**). It scored 10-0 as Red and 9-1 as Black. A 20,000-resample paired bootstrap
over the 10 openings gives an **85–100%** score interval; its transformed Elo upper
endpoint is unbounded. This is a strong result under this setup, but only 10 pairs
were tested and the interval is correspondingly wide.

All 20 records passed replay, legality, turn-order, outcome, time-control, and color
pairing checks. They contain 605 plies and no move-cap draws. Both engines received
the same nominal per-move budget, but these are not hard real-time limits: observed
mean move times were 505.8 ms for AlphaZeta and 446.7 ms for Pikafish. The recorded
mean reported search depths were 1.36 (AlphaZeta, including interrupted depth-0
fallbacks) and 47.59 (Pikafish). This measures the engines' overall playing strength
under equal approximate wall-clock budgets, not a search-algorithm-only comparison.
The run took about 0.8 minutes. Results and source-opening manifest are
`data/v0.10_pikafish_vs_search_500ms_10openings.jsonl` and
`data/v0.10_pikafish_vs_search_500ms_10openings.jsonl.manifest.json`.

The second sample used 10 different 10-ply positions (seed `20261006`, no overlap with
the 500 ms sample) and a longer 2,500 ms budget for both engines. Pikafish won **all
20 games**, 10-0 as Red and 10-0 as Black, with no draws. The paired percentile
bootstrap is degenerate at 100–100% because every sampled opening pair was a
two-game sweep; this is not evidence of certainty, and the Elo point estimate is
undefined at a 100% score. AlphaZeta averaged 2.13 reported search depth versus
Pikafish's 59.13, while the mean observed times were 2,507 ms and 2,134 ms,
respectively. All 20 games and color-swapped openings passed validation. Runtime was
about 3.7 minutes. Data and manifest:
`data/v0.10_pikafish_vs_search_2500ms_10openings.jsonl` and
`data/v0.10_pikafish_vs_search_2500ms_10openings.jsonl.manifest.json`.

### Quiescence legal-move filtering

Follow-up profiling showed quiescence was generating every legal move in a
non-check position and then discarding every quiet move. It now probes all possible
captures but checks only enough quiet moves to establish whether at least one legal
move exists (preserving stalemate detection); checked positions still enumerate every
legal evasion. On the three reference positions, iterative depth-3 search retained
the same node counts and scores while mean time fell from 0.635 to 0.273 seconds
(initial), 0.885 to 0.390 seconds (early development), and 0.519 to 0.228 seconds
(central development), a repeatable 2.27–2.32x speedup in paired local runs.
Depth-4 iterative search from the initial position took 1.16 seconds in the
post-change benchmark.

Focused rule/quiescence tests and the full **355-test** suite pass. A new independent
10-opening 500 ms paired match after the optimization scored **19–1–0** for Pikafish
(95%; paired bootstrap interval 85–100%), exactly the same game score as the prior
10-pair sample, but on openings disjoint from both earlier Pikafish batches. AlphaZeta
mean reported depth increased from 1.36 to **1.77**; the result shows modest depth
progress but no measured outcome improvement yet. All 20 games were replay-validated,
with 10 games per color. Data and manifest:
`data/v0.10_pikafish_vs_search_500ms_10openings_post_qsearch.jsonl` and
`data/v0.10_pikafish_vs_search_500ms_10openings_post_qsearch.jsonl.manifest.json`.

### Capture-only move generation and dispatch

The follow-up profile also found that quiescence still constructed quiet `Move`
objects before filtering them, and `MoveGenerator.generate_piece_moves` rebuilt a
piece-handler dictionary for every piece on every node. Added a capture-only generator
path that avoids constructing quiet moves, and replaced the repeatedly allocated
handler map with direct piece-type dispatch. Capture-only results were cross-checked
against full legal move generation for both colors on the initial, early-development,
and central-development positions. Rule, search, and tactical regression tests pass.

Compared with the immediately preceding implementation, depth-3 iterative benchmarks
improved a further 15–17% on the three reference positions (0.254 to 0.215s initial,
0.367 to 0.310s early development, 0.230 to 0.192s central development; three-run
averages). Depth-4 iterative initial search is about 1.06s in the repeated benchmark.

A third disjoint set of 10 external openings was then played at 500 ms/move (seed
`20261008`, 20 games, balanced colors). Pikafish scored **20–0–0**; the paired
bootstrap is 100–100% because all 10 opening pairs were sweeps, so it does not
quantify unseen-loss risk and the Elo estimate is undefined. AlphaZeta averaged
reported depth **1.93** at 507.7 ms per move; Pikafish averaged depth 49.52 at
444.7 ms. All games passed replay, legality, and pairing validation. Data and manifest:
`data/v0.10_pikafish_vs_search_500ms_10openings_post_qsearch_dispatch.jsonl` and
`data/v0.10_pikafish_vs_search_500ms_10openings_post_qsearch_dispatch.jsonl.manifest.json`.

## Validation

The complete test suite passes: **357 passed**. The focused Pikafish,
paired-opening, and recorder tests passed **24/24**.

Useful commands:

```powershell
python -m pytest -q
python tools/benchmark_tactics.py --depths 2 3 4
python tools/benchmark_search.py --depths 2 3
```

## Current caveats and next steps

- The 20-game depth-4 vs. depth-3 result is inconclusive and uses only the deterministic
  initial opening. The 100-game randomized follow-up is more informative, but is still a
  single sample rather than a definitive playing-strength measurement.
- Historical design documents such as `docs/architecture.md` describe the initial
  project intent. Use this snapshot and the V0.10.0 report for current implementation
  status.
- Each Pikafish sample currently covers only 10 opening pairs. The 2,500 ms sample is a
  complete sweep, so its percentile bootstrap cannot quantify unseen-loss risk. Expand
  the paired set and profile AlphaZeta's limited achieved depth further before treating
  the observed advantage as stable.
- Continue with targeted profiling and tactical tests before adding forward pruning or
  changing evaluation weights. Keep experimental pruning disabled until it is shown
  not to regress objective tactical tests and improves match results.

The completed single-opening comparison can be reproduced with:

```powershell
python tools/compare_engines.py --a-depth 4 --b-depth 3 --games 20 --random-opening-plies 0 --random-opening-prob 0 --output data/v0.10_depth4_vs_depth3.jsonl
```

## SEE activation and search-time trade-off

The Web UI configures `SeeSearchEngine(use_see=True)`, but the base search had not
passed its current board into the move-ordering hook. SEE therefore had silently
received no position and had not been used. The board is now passed through, with a
regression test proving the evaluator runs on multiple capture candidates. This
restores the configured behavior; it does not establish a playing-strength gain.

At depth 4 from the initial position, the SEE benchmark selected the same move and
score as baseline but took 1.549s and 22,652 nodes versus 1.106s and 17,079 nodes.
On the capture-rich reference position it took 0.036s and 1,262 nodes versus 0.041s
and 1,406 nodes; SEE was not called there because only one capture was available to
order. A 4-opening / 8-game, 500 ms paired pilot scored 43.8% for SEE. This is too
small to infer a strength difference, so SEE remains an experimental ordering option
rather than a demonstrated improvement.

A depth-5 iterative-deepening benchmark took 4.350s from the initial position
(137,851 cumulative nodes), versus about 1.06s for the prior depth-4 initial
benchmark. It took 5.592s in early development and 5.712s in central development.
Raising the default depth would therefore impose a substantial response-time cost;
the benchmark alone does not justify that trade-off.

Null-move pruning also remains disabled by default: its 4-opening / 8-game pilot
scored 43.8%, which is inconclusive. An unbounded depth-4 SEE comparison did not
complete within more than 10 minutes and was stopped; it produced no match result.
After the latest SEE wiring and recapture-path changes, the full suite passes
**361 tests**, and `git diff --check` passes.

## Principal-reply investigation

Added `tools/trace_principal_variation.py`, a diagnostic that independently searches
each selected root move, follows legal moves stored in that search's transposition
table, and reports captures, static and searched scores, TT bound metadata, and a
recomputed quiescence-boundary score. It checks that the input board is restored.
The TT-derived line may include bound moves, so it is evidence for investigation, not
a guaranteed exact PV.

The opening-position trace shows that the apparently attractive cannon moves
`(1,2)->(1,9)` and `(7,2)->(7,9)` capture horses, not rooks. In both cases the
opponent immediately recaptures the cannon with its rook. The score is -60 at depth 3
and -160 at depth 4. The `tactical_exchange` trace found a second horizon example:
`(4,2)->(4,6)` scores +190 at depth 3, but depth 4 reveals the black-cannon capture
`(4,7)->(4,3)` of a red pawn behind the red cannon and brings the score to 0. This
explains these score shifts as concrete one-ply tactical horizon effects; it does not
by itself justify changing search selectivity or evaluation.

The tracer tests pass **4/4**; the complete suite passes **361 tests** after the
diagnostic additions.

## Root-ordering experiments

Tested two low-risk alternatives to the current iterative-deepening root ordering
using three reference positions and three repeated runs:

- Sorting every root move by one-ply static evaluation increased depth-4 median
  nodes from 17,079 to 34,334 (initial), 17,350 to 50,488 (early development), and
  16,887 to 41,314 (central development). Median times rose from 1.051s to 1.599s,
  1.333s to 2.618s, and 1.121s to 2.016s, respectively. Scores remained equal; one
  tied-score case selected a different move.
- Ordering by each root move's score from the previous iterative-deepening pass kept
  the same move and score on all six position/depth cases, but increased depth-4
  median nodes to 19,358, 20,525, and 17,504, with median times of 1.155s, 1.530s,
  and 1.193s. Depth-3 results were mixed and did not offset the depth-4 regressions.

Neither prototype is promoted. The result indicates that shallow static scores and
PVS root bounds are not reliable enough here to improve the established root order.
Existing previous-best-move ordering remains unchanged.

Also rechecked the existing optional MVV-LVA capture ordering at depths 3 and 4 on
the same positions (three runs each). Scores and selected moves matched the default
in all six cases, but performance was mixed: depth-4 nodes changed from 17,079 to
16,006 initially, 17,350 to 24,649 in early development, and 16,887 to 17,087 in
central development. The isolated initial-position improvement is not enough to
justify enabling it by default, especially given the large early-development
regression and lack of paired strength evidence. Keep MVV-LVA opt-in.

## Aspiration-window search

Implemented root aspiration windows centered on the score from the last completed
iterative-deepening pass. The default half-window is 100 evaluation points. If the
root score lands on or outside either bound, the same depth is searched again with a
full window before the iteration is accepted. Fixed-depth-only search remains
full-window. Cancellation during either pass preserves the last fully completed
iteration. `tools/benchmark_search.py` accepts `--aspiration-window` so this can be
compared reproducibly with a wide-window control.

With a three-run benchmark, depth-4 iterative search changed from full-window control
to a 100-point aspiration window as follows:

| Position | Control time / nodes | Aspiration time / nodes | score | best move |
| --- | ---: | ---: | --- | --- |
| Initial | 1.172s / 17,079 | 0.898s / 14,668 | same | same |
| Early development | 1.403s / 17,350 | 1.210s / 16,469 | same | tied move differed |
| Central development | 1.205s / 16,887 | 1.171s / 16,884 | same | same |

At depth 5, initial position improved from 4.945s / 137,851 nodes to 3.297s /
97,574 nodes, and early development from 6.106s / 130,259 nodes to 3.673s / 69,142
nodes. Central development was effectively unchanged (5.945s / 145,053 vs. 6.093s /
144,927). All scores matched; one depth-5 tied-best move differed. A 500 ms stop-time
check completed at depth 3 in all five runs for each setting on all three positions,
with identical moves and scores. Thus the optimization reduces work in some searches
but has not yet demonstrated an extra completed iteration under the tested short
time budget or a playing-strength gain.

A second fixed-time decision sample used eight distinct 10-ply positions selected
from the external-game corpus (seed `20261005`), with a 3.5-second search budget per
position. Baseline and aspiration chose the same move and completed the same depth in
all eight positions; the completed depths ranged from 2 to 4. Mean reported nodes
fell from 14,905 to 14,270 (4.3%). This supports a small efficiency improvement on
this sample, not a move-quality or playing-strength improvement. It also did not
show an extra completed iteration under 3.5 seconds.

On the initial and early-development reference positions, a separate three-run
3.5-second check completed depth 5 with aspiration while the full-window control
completed only depth 4 in every run. This shows a potential extra-ply benefit on
those positions under that budget. The external-opening sample shows that this is
not universal, and no game-level match has established a strength gain.

Aspiration correctness tests cover fail-high and fail-low re-search, narrow-window
and wide-window parity through depth 4, fixed-depth behavior, alpha-beta-disabled
search, invalid windows, and cancellation compatibility. The full suite passes
**373 tests**; the depth-2–4 mate, safe-capture, and exchange-trap
diagnostics also pass.

The paired fixed-opening follow-up can be reproduced with:

```bash
python tools/compare_engines_paired.py --source data/v0.10_depth4_vs_depth3_multiopening_100.jsonl --output data/v0.10_depth4_vs_depth3_paired_10openings.jsonl --opening-count 10 --opening-plies 10 --seed 20260929 --workers 8
```

The external-game paired sample can be reproduced with:

```bash
python tools/compare_engines_paired.py --source data/external_games.jsonl --output data/v0.10_depth4_vs_depth3_external_paired_10openings.jsonl --opening-count 10 --opening-plies 10 --seed 20260930 --workers 8
```

The expanded external-game match uses:

```bash
python tools/compare_engines_paired.py --source data/external_games.jsonl --output data/v0.10_depth4_vs_depth3_external_paired_20openings.jsonl --opening-count 20 --opening-plies 10 --seed 20260931 --max-moves 150 --workers 8
```

For broader coverage, retain the default randomized opening plies and increase the
game count; runtime will be substantial at depth 4.

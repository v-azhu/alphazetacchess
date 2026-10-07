# AlphaZetaChess Current Progress

Snapshot date: 2026-10-06

Starting revision: `dbb9ff9`; this checkpoint's changes are in the current worktree.

## Current engine status

- The primary playing engine is the alpha-beta `SearchEngine`; CLI and UCCI default to
  depth 5 with late-move reductions (LMR) enabled. The Web UI uses SEE-enhanced search,
  defaults to depth 5 with LMR, and offers depths 1–6 plus toggles for these search
  options. SEE capture ordering in quiescence is an opt-in Web experiment.
- MCTS, neural evaluation, and policy networks remain runnable experiments. Existing
  match results do not show them outperforming the traditional search baseline.
- Null-move pruning remains disabled by default. A current LMR-controlled paired match
  comparison is recorded below. The latest correctness and search-boundary work is in
  [`v0.10.0.md`](v0.10.0.md); older experiments remain in [`roadmap.md`](roadmap.md)
  and their version-specific documents.

## Latest completed work

### Raising the default search depth

Responding to feedback that the engine is still too easy to beat, raised the default
depth from 4 to 5 in the CLI, UCCI adapter, and Web UI. Depth 4 remains selectable in
the Web UI for quicker turns. On three reference positions, depth 5 took 3.9–5.8
seconds with the Web UI's SEE-enabled search, versus 0.9–1.0 seconds at depth 4.
Depth 5 kept the depth-4 move in all three positions; its evaluation changed by 60
points in each. The tactical fixtures continued to find the immediate mate and safe
capture; the exchange-trap fixture's selected move also remained unchanged.

This is a deliberate strength-versus-response-time tradeoff based on the request to
make the default opponent stronger. Greater depth is expected to improve play but
these spot checks are not a depth-5-vs-depth-4 match and do not quantify a playing
strength gain. The Web UI now indicates that depth 5 takes several seconds per move.

### Optional depth-six Web search

Measured depth 6 on the same three reference positions. The standard SearchEngine
completed iterative depth 6 in 13.1s (initial), 18.7s (early development), and 23.9s
(central development). The Web UI uses SEE-aware search, which completed in 17.7s,
23.6s, and 24.1s respectively. The mate-in-one and safe-capture tactical fixtures
continued to select the objective moves at depth 6; the exchange-trap fixture kept
the same selected move as at depth 5.

Added depth 6 as an optional Web UI choice, labeled as a slow experiment, while
retaining depth 5 as the default. These measurements quantify the response-time cost,
not a playing-strength gain; no depth-six match has been run.

### Enabling conservative LMR in play defaults

Compared late-move reductions (LMR) enabled and disabled at depths 5 and 6 on the
initial, early-development, and central-development reference positions, using both
the base search and the SEE search used by the Web UI. At depth 5, all six
base/SEE position comparisons retained the same score and best move. Base-search
times changed from 2.8/3.7/5.1s to 1.7/2.6/3.0s, and SEE-search times from
3.9/4.4/5.8s to 2.3/2.5/2.8s (initial/early/central). Node counts fell by about
45–60%.

At depth 6, LMR cut measured times by about 40–60%, but did not preserve the best move
in every position: one of three base-search cases and one of three SEE cases changed
its move; scores also shifted slightly. This confirms the expected selective-search
tradeoff rather than exact equivalence at deeper depth. An earlier 8-pair equal-time
match was neutral (50%, wide 25–75% paired interval), while LMR reached greater mean
depth; there is not enough match evidence to claim improved playing strength.

In an additional 3-second-per-move probe on the same three positions using the
SEE-enabled Web search, baseline completed depth 4 in each case while LMR completed
depth 5 in each. Both selected the same move at their respective completed iterations.
This is a small fixed-position throughput result, not a playing-strength measurement.

Enabled LMR by default in the CLI, UCCI, and Web UI to reduce search cost and make
deeper searches more practical. The Web UI exposes a checked-by-default toggle so it
can be disabled for comparison. It remains an explicitly experimental search
heuristic; users prioritizing conservative full-width search can turn it off.

### Null-move pruning on top of LMR

Extended `tools/compare_null_move_paired.py` with `--use-lmr`, so both sides can use
LMR while the paired match isolates null-move pruning. The runner now excludes every
opening in existing paired-match manifests, records both pruning settings, and reports
LMR counts. A disjoint 8-opening, 16-game match at 500 ms/move scored **6 wins, 6
losses, and 4 draws** for null-move search (50%). The paired bootstrap 95% interval
was **40.6–59.4%**. Both sides used LMR; null-move search averaged depth **3.72** over
718 moves versus **3.53** over 718 control moves. All games were replay-validated.

This is consistent with extra search throughput, not a playing-strength gain; the
interval spans neutral and the paired result is exactly even. Keep null-move pruning
disabled by default. Records and opening manifest:
`data/v0.10_null_move_with_lmr_vs_lmr_500ms_8pairs.jsonl` and its
`.manifest.json`.

A second disjoint 12-opening, 24-game batch scored **12 wins, 9 losses, and 3 draws**
(56.2%) for null-move search, with paired 95% interval **43.8–70.8%**. Across both
batches (20 opening pairs / 40 games), the result is **18 wins, 15 losses, and 7 draws**
(53.75%); a paired-opening bootstrap interval is **45.0–62.5%** (about **-35 to +88
Elo**). Null-move search averaged depth **3.61** over 1,664 moves versus **3.37** over
1,663 control moves. All additional games were replay-validated and the opening pairs
were disjoint. The larger sample remains inconclusive and does not justify enabling
null-move pruning by default.

Additional records and manifest:
`data/v0.10_null_move_with_lmr_vs_lmr_500ms_additional_12pairs.jsonl` and its
`.manifest.json`.

A third disjoint 12-opening, 24-game batch scored **6 wins, 10 losses, and 8 draws**
(41.7%) for null-move search; its paired interval was **29.2–50.0%**. Across all
32 opening pairs / 64 games, null-move search scored **24 wins, 25 losses, and 15
draws** (49.2%). The paired-opening bootstrap 95% interval was **42.2–56.2%** (about
**-55 to +43 Elo**). Null-move search still reached greater mean depth (**3.54** over
2,659 moves vs. **3.26** over 2,660 baseline moves), but this did not translate to a
match-score benefit in the expanded sample. Keep null-move pruning disabled by
default. All games were replay-validated and the new openings were disjoint from
previous paired experiments.

Third-batch records and manifest:
`data/v0.10_null_move_with_lmr_vs_lmr_500ms_final_12pairs.jsonl` and its
`.manifest.json`.

### Transposition-table capacity check

Compared 50,000-, 200,000-, and 500,000-entry caps on depth-6 LMR + SEE searches.
With the 50,000 cap, the table filled and searches needed 211,513 nodes / 10.86s
(initial) and 216,334 nodes / 13.61s (central development). At both 200,000 and
500,000 caps, the table never exceeded 113,327 entries; node counts and selected
moves were identical between capacities: 169,555 nodes / 8.49s initially and
203,308 nodes / about 12.1s centrally. Increasing the existing 200,000 default would
not help these searches; lowering it materially hurt. No capacity change is warranted
from this sample.

### SEE capture ordering in quiescence

The Web UI's SEE-aware search previously used SEE only for captures at normal
alpha-beta nodes; quiescence searched captures in generator order. Routed quiescence
captures through a dedicated ordering hook and enabled SEE ordering in the Web search,
with a Web UI toggle to disable it. Check evasions and quiet-check extensions keep
their existing behavior; only capture ordering changes.

At fixed depths 4 and 5 on the initial, early-development, and central-development
positions, scores and best moves matched the prior SEE search in all six cases. At
depth 5, node counts fell from 51,674 to 47,111 initially (8.8%), 50,080 to 47,795
in early development (4.6%), and 56,177 to 53,348 centrally (5.0%). Wall-clock time
was roughly unchanged to slightly slower (2.18 to 2.21s, 2.50 to 2.63s, 2.78 to
2.84s in the measured runs). SEE calls rose because quiescence captures are now
evaluated too. This is a modest node-count/order refinement, not yet a playing-strength
claim; a 3-second fixed-time probe reached the same depth and selected the same move in
all three positions. Since wall-clock time was neutral to slightly worse, keep this
option off by default and expose it only as a Web UI experiment pending paired match
evidence.

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

The optional prior-iteration root-score implementation was also checked at depth 4
with three repeated searches per position. Scores and moves matched baseline in all
three positions. Median nodes/time changed from 17,109/0.763s to 16,864/0.763s
(initial), 10,324/0.497s to 9,934/0.445s (early development), and
15,045/0.910s to 18,590/1.146s (central development). The central-position regression
outweighs the small, position-specific savings; leave the option disabled by default.

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

### Equal-time paired match: aspiration vs full-window control

Ran 20 games at a 500 ms/move budget using 10 distinct 10-ply positions selected
from `data/external_games.jsonl` (seed `20261005`). Each opening was played twice
from the same FEN, once with aspiration (100-point half-window) as Red and once as
Black; order was alternated between opening pairs. The full-window control used a
10,000-point half-window. The result for aspiration was **9 wins, 9 losses, 2 draws**
(50% score). The 10-opening paired bootstrap 95% interval was **37.5–60.0%**, or
approximately **-89 to +70 Elo** under the usual score-to-Elo conversion. Paired
opening scores were `[75%, 50%, 0%, 50%, 50%, 75%, 50%, 50%, 50%, 50%]`.

Aspiration averaged depth **3.071** over 659 moves versus **3.062** over 660 control
moves. By aspiration color, it scored 3/10 points as Red (2 wins, 6 losses, 2 draws)
and 7/10 as Black (7 wins, 3 losses); the color-swapped pairs account for the
opening/color effect, and the net paired result remained neutral. All 20 records
were replay-validated for legal moves, side-to-move, terminal state, and draw limit.
This does not support a measurable strength gain from aspiration; it is primarily a
search-efficiency optimization with position-dependent time savings. Records and
opening manifest:
`data/v0.10_aspiration_vs_full_window_500ms_10pairs.jsonl` and
`data/v0.10_aspiration_vs_full_window_500ms_10pairs.jsonl.manifest.json`.

### Experimental quiescence quiet checks

Added an opt-in quiescence extension for legal quiet checks (`quiescence_check_plies`,
default `0`, so normal search behavior is unchanged). The focused `free_capture`
fixture demonstrates a horizon effect: after Red captures the Horse, Black has two
legal replies and each permits an immediate Red mate. At depth 2, capture-only
quiescence evaluates the position at 1,570; a one-ply quiet-check extension finds the
forced mate in three plies (score 99,997). At depth 3, baseline search already finds
the mate. Separate rule-level validation confirms the new move generator returns
exactly the legal, non-capturing checks and restores the board.

The local six-position depth-2 benchmark showed quiet-check search taking 0.092s vs.
0.067s on the initial position, 0.048s vs. 0.035s on the tactical-exchange position,
and 0.010s vs. 0.004s on the mate-in-three fixture, compared with ordinary
capture-only quiescence. These are single-run timings and the sparse tactical
positions are especially sensitive to fixed overhead. The full suite passes **376
tests**. The extension remains disabled by default pending an equal-time paired match:
finding the fixture tactic does not establish a net playing-strength gain if added
work reduces the depth reached elsewhere.

The first equal-time match covered 10 distinct external-game openings, with each
played once per color at 500 ms/move. Quiet-check search scored **11 wins, 9 losses,
and 0 draws** (55%). The paired-opening bootstrap 95% interval was **35–75%** (about
**-107 to +191 Elo**), so this remains inconclusive. Quiet-check search averaged
depth **2.64** over 640 moves versus **2.80** for capture-only search over 639 moves,
consistent with its additional move-generation cost. All 20 game records passed
replay validation. This first sample was followed by a second, disjoint 20-opening
paired run; the combined result below remains inconclusive. Records:
`data/v0.10_qchecks_vs_capture_only_500ms_10pairs.jsonl` and its `.manifest.json`.

That disjoint second run completed **40 additional games / 20 opening pairs**.
Quiet-check search scored **17 wins, 19 losses, and 4 draws** (47.5%); the paired
95% interval was **32.5–62.5%** (about **-122 to +88 Elo**). Combining both
disjoint runs gives **30 opening pairs**, an even **30/60 points**, with a paired
bootstrap 95% interval of **37.5–62.5%** (about **-89 to +89 Elo**). Across the
combined samples, quiet-check search averaged depth **2.95** over 2,269 moves versus
**3.05** for capture-only search over 2,268 moves. All games were replay-validated.
This is no evidence of a net strength gain; retain the experiment as opt-in and off
by default. Additional records and opening manifest:
`data/v0.10_qchecks_vs_capture_only_500ms_additional_20pairs.jsonl` and its
`.manifest.json`.

### Evaluation hot-path profiling

Depth-3 profiling on the initial and early-development positions found evaluation
accounted for about 23% of cumulative search time. Its King Safety term rescanned
all 90 squares twice to count surviving Advisors and Elephants, after the main
evaluation loop had already visited those squares. `evaluate()` now accumulates those
guard scores during its existing scan and only performs the two short open-file
checks afterward; `_king_safety_score()` remains unchanged for feature extraction and
the reference calculation.

On repeated isolated evaluation calls (3,000 per sample, seven samples), the revised
evaluator took a median 48.2 ms vs. 56.8 ms on the initial position and 46.5 ms vs.
54.1 ms in early development (about 16–18% faster for that microbenchmark). Search
scores, moves, and node counts were identical at depth 3, but full-search wall time
did not show a clear improvement above run-to-run variation. This is a small
implementation-level saving, not evidence of a playing-strength gain. The full suite
passes **378 tests**.

Inlining material, pawn-river, and piece-square lookup work into the existing
evaluation loop removed two helper calls per piece and repeated table lookups. The
inlined version matched the helper-based reference exactly across 26 positions, both
perspectives, and five evaluation configurations. In an interleaved benchmark of
5,000 calls per sample over nine samples, median evaluation time fell from 87.2 ms to
63.4 ms (about 27%). Interleaved depth-3 search medians improved 4.7–6.9% on three
reference positions with identical scores, moves, and node counts. At a 500 ms
budget on 12 fresh external-game positions, the optimized evaluator completed one
extra iteration in one case, matched depth in the other 11, never fell behind, and
selected the same move in every position. This is a speed benefit that can sometimes
buy an additional ply, not proof that the resulting move is stronger.

The same profile showed move generation repeatedly calling `Board.get()` while
scanning the board for pieces. `MoveGenerator.generate_moves()` now binds the board
grid once and reads each row directly. Its full and capture-only outputs matched the
previous accessor-based scan for both sides across 20 replayed positions. In a
repeated mixed-position generator benchmark, median time fell from 11.7 ms to 10.8 ms
(about 8%). Depth-3 search timings improved about 3–5% on early/central development
positions but were effectively unchanged on the initial position; scores, moves,
and node counts matched exactly. Treat the end-to-end difference as modest and
position-dependent. Static movement offsets are also now stored as tuples on the
generator instead of allocating direction/candidate lists at every piece expansion;
the focused correctness suite remains green. A further profile-guided step inlined
the 9x10 bounds checks and grid lookups within piece move generation. Against the
pre-change generator from HEAD, full and capture-only move sequences matched for
both colors across 50 replayed positions; a mixed-position, repeated generator
benchmark improved median runtime from 29.38 ms to 20.42 ms (about 30% less time).
Seven-run depth-3 search medians moved from 206 to 192 ms on the initial position,
191 to 170 ms in early development, and 183 to 162 ms in central development, with
the same node counts, scores, and best moves. This throughput improvement is
position-dependent and does not itself establish stronger move choices.

A fixed-time depth check compared the HEAD generator against the optimized generator
on 12 additional, distinct 10-ply external-game positions, with a 1-second budget per
search. The optimized generator completed one extra iteration in 1/12 positions,
matched the control's depth in the other 11, and never completed a shallower
iteration. Mean completed depth was 3.00 vs. 3.08; the chosen move changed only in
the position where the optimized search completed an extra depth. This small,
single-run sample shows a possible practical time-control benefit but cannot support
a playing-strength claim.

Profiling also showed `Board.kings_facing()` on the legality-check hot path. It now
orders the two king ranks with a branch instead of allocating/sorting a list, and
reads the intervening file directly from the grid. Results matched the former
implementation across 50 replayed positions. A repeated isolated benchmark improved
median time from 68.1 ms to 54.1 ms per 100,000 calls. In seven interleaved depth-3
search comparisons, end-to-end medians improved by about 1–3% across the initial,
early-development, and central-development positions, with identical nodes, scores,
and moves. This remains a small performance-only change.

### Conservative null-move paired match

A new, disjoint 12-opening match compared conservative null-move pruning against
baseline search at 500 ms/move, with each opening played once per color. Null-move
search scored **13 wins, 8 losses, and 3 draws** (60.4%); the paired 95% bootstrap
interval was **47.9–72.9%** (about **-15 to +171 Elo**), so this single batch is
promising but not conclusive. It averaged completed depth **3.71** over 1,035 moves,
versus **3.36** over 1,034 baseline moves. The feature recorded 50,957 null attempts
and 31,408 cutoffs; mean reported nodes were higher because the pruning variant
completed deeper searches. All records were replay-validated. A second disjoint batch
has completed; null-move pruning remains opt-in pending further confirmation.
Records:
`data/v0.10_null_move_vs_baseline_500ms_12pairs.jsonl` and its `.manifest.json`.

The second disjoint batch scored **13 wins, 11 losses, and 0 draws** (54.2%), with a
paired 95% interval of **37.5–70.8%** (about **-89 to +151 Elo**). Combining both
samples yields **26 wins, 19 losses, and 3 draws** across 24 opening pairs (57.3%);
the paired bootstrap 95% interval is **45.8–68.8%** (about **-29 to +137 Elo**).
Average completed depth was 3.54 with null-move versus 3.19 for baseline across both
samples. This suggests the pruning may help under this time budget, but uncertainty
still includes neutral or negative effect. Keep it off by default for now; expand
the paired match before a promotion decision. Additional records and manifest:
`data/v0.10_null_move_vs_baseline_500ms_additional_12pairs.jsonl` and its
`.manifest.json`.

A third disjoint 12-pair batch scored **12 wins, 9 losses, and 3 draws** (56.2%),
with a paired 95% interval of **50.0–66.7%**. Across all 36 opening pairs / 72
games, null-move search scored **38 wins, 28 losses, and 6 draws** (56.9%); the
paired bootstrap 95% interval was **49.3–64.6%** (about **-5 to +104 Elo**). Average
completed depth was **3.65** with null-move versus **3.26** for baseline. The lower
interval bound remains just below neutral; continue to keep the feature experimental
while gathering another disjoint sample. Third-batch records and manifest:
`data/v0.10_null_move_vs_baseline_500ms_final_12pairs.jsonl` and its
`.manifest.json`.

A fourth disjoint batch scored **11 wins, 10 losses, and 3 draws** (52.1%), with a
paired interval of **35.4–68.8%**. Across all 48 opening pairs / 96 games,
null-move search scored **49 wins, 38 losses, and 9 draws** (55.7%); the paired
bootstrap 95% interval is **48.4–63.0%** (about **-11 to +93 Elo**). Mean completed
depth was **3.60** with null-move and **3.23** for baseline. All four batches used
disjoint 10-ply openings and passed replay validation. The engine reaches greater
depth, but match evidence still does not rule out a slight strength regression;
keep null-move pruning opt-in. Fourth-batch records and manifest:
`data/v0.10_null_move_vs_baseline_500ms_more_12pairs.jsonl` and its
`.manifest.json`.

### Conservative late-move reductions

Added optional late-move reductions (LMR) for late quiet moves at non-check nodes,
starting at move index 8 and depth 3. A reduced null-window search is followed by a
full-depth re-search if it beats alpha. Checks and captures are excluded, and the
feature remains disabled by default.

Fixed-depth checks showed substantially fewer nodes with unchanged score and best move
at depth 5 on the initial, early-development, and central-development positions; the
depth-6 central-development result also matched. At depth 5, node counts fell from
97,574 to 45,211 (initial), 69,142 to 41,367 (early), and 144,927 to 55,859 (central).
On the central position at depth 6, nodes fell from 477,533 to 256,346. At equal
time controls on 12 fresh positions, LMR matched baseline depth at 500 ms and 1.5 s.
At 3 s it completed one extra iteration on two positions, never completed a shallower
iteration, and selected a different move once.

The 8-opening, 16-game paired match at 3 s/move scored **7 wins, 7 losses, and 2
draws** for LMR (50%); the paired 95% bootstrap interval was **25–75%** (about
**-192 to +192 Elo**). Mean completed depth was **4.37** for LMR versus **4.01** for
baseline across recorded engine moves. All games passed legal replay and result
validation, and all eight openings were played with colors swapped. This is evidence
of increased search depth on this sample, not a demonstrated playing-strength gain;
at that checkpoint LMR remained opt-in pending more strength evidence. Subsequent
fixed-position testing motivated enabling it in the play front ends for throughput,
while keeping it configurable and experimental as described above. Records and
opening manifest:
`data/v0.10_lmr_vs_baseline_3s_8pairs.jsonl` and its `.manifest.json`.

After LMR was added, the complete test suite passed **383 tests** and
`git diff --check` was clean.

### Killer/history move-order integration

Corrected the ordering interaction in both the base and SEE search paths: history
sorting previously ran after killer promotion, so a high-history quiet move could
undo the killer priority. With MVV-LVA enabled, captures remain ahead of killers,
killers remain ahead of history-ranked quiets, and the transposition-table move stays
first. A regression test seeds conflicting history and killer scores in both search
implementations.

The fix preserved depth-4 score and best move on the initial and early-development
positions. In single fixed-depth runs, nodes increased from 14,668 to 15,298 and
16,853 to 17,450 respectively; this ordering correction has not shown a speed or
strength gain and should not be treated as one. The earlier full suite had 383 tests;
after the added regression test, **384 tests passed**.

### Side-specific history scores

History scores were keyed only by from/to coordinates, allowing a Red quiet move's
cutoff reward to affect the ordering of a Black move with the same coordinates (and
vice versa). The table now includes the moved piece's color in each key. Tests verify
that rewards and penalties remain isolated by side. Three depth-4 comparisons against
the coordinate-only history table produced identical scores, best moves, and node
counts; this fixes cross-side score contamination but does not demonstrate a strength
gain. The full suite now passes **385 tests**.

### Quiet-history isolation from captures

History lookup now returns zero for captures. Although history updates already ignore
captures, coordinate-matching quiet history could otherwise leak onto a later capture
and influence ordering. In the base search when MVV-LVA is disabled, history ranks
quiet moves only; captures keep their original relative order. The SEE path already
separates captures and quiets before applying history ordering.

Regression tests cover capture lookup after a matching quiet move was rewarded and
quiet reordering without changing capture order. The full suite passes **387 tests**.
Depth-4 score and best move stayed unchanged on initial, early-development, and
central-development positions. Single-run node counts were 17,109, 18,909, and 15,202
respectively; compared with the immediately prior recorded runs, these were higher.
This correctness refinement prevents stale capture-history bias, but has not shown a
strength or performance gain.

### Pikafish teacher book from the tournament archives

The two archived ICCS collections contain 41,743 WXF and 99,771 dpxq
result-bearing games. Mining their first 20 plies found **506,056 distinct positions**
over **141,514 games**. The archives document that illegal games were filtered before
distribution; this builder applies inexpensive turn/occupancy checks to every source
prefix and independently verifies each Pikafish-selected move with the Rule engine.
Ten sampled starting positions from the existing external-game set had no exact
book-root match after 4, 6, 8, or 10 plies, showing that coverage depends on common
lines.

Added `tools/build_pikafish_opening_book.py` to query a local Pikafish binary/network
on frequent positions and write an opt-in teacher book. The pilot selected the 300
most frequent positions among those seen in at least 500 distinct games. All 300
teacher moves were legal; search depths were 15–21 (mean 17.8) at 250 ms/position.
The resulting local artifact is `/tmp/alphazeta-pikafish-opening-book-pilot.json`.
It contains best moves and search metadata, not Pikafish code or weights. The local
Pikafish license restricts commercial use of its NNUE weights without permission;
do not redistribute the weights or assume generated artifacts are cleared for
commercial use.

An 8-opening / 16-game color-swapped, 500 ms/move pilot compared the book-enabled
SearchEngine with baseline search from common positions represented in the book.
Book scored **4 wins, 8 losses, and 4 draws** (37.5%); the paired 95% interval was
**18.8–59.4%** (approximately **-255 to +66 Elo**). Only 10 of the 16 games actually
used a teacher-book move, as opponent replies often left the covered lines. Every
game passed replay and result validation. This small experiment does not support
promoting the book; retain it as an opt-in experiment. Records and opening manifest:
`data/v0.10_pikafish_teacher_book_vs_search_500ms_8pairs.jsonl` and its
`.manifest.json`.

To test the poor coverage rather than immediately abandon the approach, built a
larger 2,000-position book from the same archives. The threshold was lowered to 100
source games per position (2,294 candidates qualified); all 2,000 Pikafish moves were
validated, with reported search depths 13–23 (mean 16.3). The reusable, ignored local
artifact is `trainingdata/pikafish_opening_book_2000.json`.

A second, disjoint 12-opening / 24-game color-swapped match at 500 ms/move scored
**10 wins, 7 losses, and 7 draws** for the expanded-book engine (56.25%); paired
95% interval **41.7–70.8%** (about **-58 to +154 Elo**). The book selected 20 moves
in the 24 games, compared with 10 in the first match's 16 games, but this modest
coverage increase does not establish a strength benefit. The opening positions were
disjoint from the first sample, all games passed replay/result validation, and the
interval still includes neutral and negative outcomes. Records and manifest:
`data/v0.10_pikafish_teacher_book_expanded_vs_search_500ms_12pairs.jsonl` and its
`.manifest.json`.

An additional 16 disjoint opening pairs / 32 games with the exact same 2,000-entry
book and time control scored **10 wins, 9 losses, and 13 draws** (51.6%); paired 95%
interval **39.1–65.6%**. All games passed replay validation. Combining only these
two same-configuration, disjoint batches gives **28 opening pairs / 56 games**,
**20 wins, 16 losses, and 20 draws** (53.6%), with a paired 95% bootstrap interval of
**43.8–63.4%** (approximately **-44 to +95 Elo**). Across the combined match the book
was used for 43 moves. The evidence remains inconclusive, with the interval spanning
neutral; do not enable the book by default. Additional records and manifest:
`data/v0.10_pikafish_teacher_book_expanded_vs_search_500ms_additional_16pairs.jsonl`
and its `.manifest.json`.

This is a direct, low-inference-cost form of Pikafish distillation into opening moves,
not a neural policy retraining. Earlier external-policy imitation did not improve
MCTS strength (see `docs/v0.9.4.md`), so no new neural policy was trained here.

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

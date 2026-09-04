# AlphaZetaChess Progress Snapshot — Endgame heuristics mechanism built (V0.5.3)

Snapshot date: 2026-09-04

## What happened this checkpoint

Per the hand-off left at the end of V0.5.2b ("proceeding here to
V0.5.3, endgame heuristics from self-play data — doesn't need a huge
or even real corpus yet"), built V0.5.3:

`src/alphazetacchess/engine/endgame.py`: a new optional evaluation
term grounded in a genuine, well-known Xiangqi endgame principle —
车赛全局，炮怕残棋 (Rook power holds up into the endgame; Cannon power
declines as screening pieces get traded off). `is_endgame(board)`
classifies phase by combined Rook+Cannon+Horse material dropping to
≤2600; `endgame_balance()` applies a flat +40-per-Rook / −40-per-Cannon
adjustment, but only inside that phase. Deliberately does **not** add
a king-activity term (the natural-looking Western-chess companion to
this): the Xiangqi King can never leave its palace at any phase, so
that heuristic simply has no equivalent here.

`src/alphazetacchess/selfplay/endgame_analysis.py` +
`tools/analyze_endgame.py`: mines self-play records for the actual
hypothesis test — among games reaching the endgame phase with a
non-tied Rook/Cannon edge, does the favored side win more often?
Mirrors V0.5.2's opening-book approach: mechanism built and tested
now, "trusting the specific constants" kept as a clearly separate,
re-runnable step once a larger corpus exists.

## What was verified this checkpoint

```
pytest tests/test_endgame_v053.py -q
13 passed in 0.05s

pytest -q   (full suite)
122 passed in 166.79s
```

Real CLI smoke test:
```
python tools/self_play.py --games 6 --depth 1 --max-moves 40  → 0/6 games reached endgame
python tools/self_play.py --games 3 --depth 1 --max-moves 100 → 1/3 games reached endgame
  Average endgame onset ply: 70.0
  Favored side won 0/1 (0%), lost 0, drew 1
  NOTE: sample too small to draw real conclusions -- collect more self-play data before trusting this number.
```
Confirms the full pipeline (self-play → onset detection → edge-vs-
outcome summary) works end to end, and incidentally confirms the phase
threshold's placement is reasonable: short/shallow games essentially
never reach it, a longer one does, at a plausibly late ply (70). Temp
files cleaned up, not left in the repo.

**Not run this checkpoint:** a real depth=2 batch with enough games to
make the win-rate number statistically meaningful (need ≥20 decided
endgame-onset positions; this session's smoke test only produced 1) —
same "local, long-running task" treatment as every other real
data-collection run in this project.

## What changed

- `src/alphazetacchess/engine/endgame.py` (new): `is_endgame`,
  `endgame_score`, `endgame_balance`, constants.
- `src/alphazetacchess/engine/evaluation.py`: new
  `use_endgame_heuristics` parameter (disabled by default).
- `src/alphazetacchess/engine/search.py`: `SearchEngine` gained
  `use_endgame_heuristics`, threaded through all four internal
  `evaluate()` call sites.
- `src/alphazetacchess/selfplay/endgame_analysis.py` (new):
  `find_endgame_onset`, `summarize_endgame_outcomes`.
- `tools/analyze_endgame.py` (new): CLI for the above.
- `tests/test_endgame_v053.py` (new, 13 tests).
- `docs/v0.5.3.md` (new): full design writeup.
- `docs/roadmap.md`: V0.5.3 section added, hand-off diagram updated,
  V0.5 header bumped to "V0.5.3 COMPLETE (mechanism)".
- `README.md`: status checklist and version history brought up to date
  through V0.5.3 (was stale at V0.3.3 — several versions had shipped
  without the top-level README being updated to match; fixed this
  checkpoint since it's the first thing anyone new to the repo reads).

## Exact next step

**Locally, whenever convenient (no rush, not blocking anything):**
```bash
python tools/self_play.py --games 30 --depth 2 --max-moves 150 --output data/selfplay.jsonl
python tools/build_opening_book.py
python tools/analyze_endgame.py
```
This single batch feeds both V0.5.2's opening book and V0.5.3's
endgame-heuristic validation — no need to run two separate collection
passes. Randomization is already the default (V0.5.2b), so this should
produce genuinely diverse games this time.

**Here:** V0.5.4 (per `docs/roadmap.md`'s original V0.5 description
and `recorder.py`'s own "planned downstream consumers" docstring) —
automated Elo-style strength comparison between `SearchEngine`
configurations, extending `tools/benchmark.py`'s `RandomEngine`-only
matches to `SearchEngine`-vs-`SearchEngine` now that V0.5.1 already
records win/loss/draw outcomes. Doesn't depend on the real-corpus step
above happening first. Will checkpoint again once that's in a
reasonable state.

## Handoff rule (unchanged, repeated for visibility)

At the next interruption, update this file with:
1. latest commit / repo state (or "continuing from this session's
   sandbox" when there isn't a fresh GitHub push to check);
2. pytest count/result;
3. benchmark result (or honest non-result, or "deliberately not
   attempted and why");
4. remaining checklist;
5. one exact next command.

This keeps the project resumable without relying on conversation
memory, and keeps each checkpoint's own work small enough to finish
within a single response.

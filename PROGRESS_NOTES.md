# AlphaZetaChess Progress Snapshot — V0.5 line's mechanisms all complete (V0.5.4)

Snapshot date: 2026-09-04

## What happened this checkpoint

Per the hand-off left at the end of V0.5.3 ("Next increment either
way: V0.5.4, automated SearchEngine-vs-SearchEngine strength
comparison"), built V0.5.4:

`src/alphazetacchess/selfplay/strength_comparison.py`:
`run_comparison_match()` plays N games between two independently
configurable engine setups, alternating colors so neither has a
systematic first-move advantage, and reports win/draw/loss plus a
standard log-odds Elo-difference estimate. Reuses V0.5.1's
`play_recorded_game` directly (rather than a separate play loop), so
every comparison-match game is automatically a complete, valid
self-play record — `--output` can point at the exact same
`data/selfplay.jsonl` corpus `tools/self_play.py`,
`tools/build_opening_book.py`, and `tools/analyze_endgame.py` already
read/write. A strength-comparison run and a data-collection run don't
have to compete for separate local time budgets; they can be the same
run.

`tools/compare_engines.py`: CLI exposing `--a-*`/`--b-*` flags for
both sides' depth and evaluation-term toggles (including V0.5.3's
`use_endgame_heuristics`), mirroring `tools/self_play.py`'s flag
style. `tools/benchmark.py` (the existing SearchEngine-vs-RandomEngine
sanity check) is untouched — different job, doesn't need generalizing.

## What was verified this checkpoint

```
pytest tests/test_strength_comparison_v054.py -q
8 passed in 0.16s

pytest -q   (full suite)
130 passed in 159.24s
```

Real CLI smoke tests:
```
python tools/compare_engines.py --a-depth 1 --b-depth 1 --a-use-mobility --games 4 --max-moves 30
  → 4/4 draws (move limit), A score rate 50%, Elo diff +0

python tools/compare_engines.py --a-depth 1 --b-depth 1 --games 2 --max-moves 10 --output /tmp/smoke_compare.jsonl
  → then: python tools/analyze_endgame.py --input /tmp/smoke_compare.jsonl
  → loaded both records cleanly, confirming cross-tool compatibility
    (compare_engines.py's output is directly readable by
    analyze_endgame.py, same JSON-lines format) isn't just a claim in
    the docstring -- actually tested it.
```
Temp files cleaned up, not left in the repo. Both smoke runs used
shallow depth/short move limits deliberately, purely to confirm the
pipeline works end to end without spending session time on a slow real
comparison — see docs/v0.5.4.md's Known Limitation for what this does
and doesn't establish.

**Not run this checkpoint:** any comparison at a depth/game-count
large enough to draw a real conclusion about which configuration is
actually stronger (need dozens of games at depth≥2 for that) — same
"local, long-running task" treatment every other real data-collection
run in this project gets.

## What changed

- `src/alphazetacchess/selfplay/strength_comparison.py` (new):
  `run_comparison_match`, `estimate_elo_diff`.
- `tools/compare_engines.py` (new): CLI for the above.
- `tests/test_strength_comparison_v054.py` (new, 8 tests).
- `docs/v0.5.4.md` (new): full design writeup.
- `docs/roadmap.md`: V0.5.4 section added, hand-off diagram updated,
  V0.5 header bumped to "V0.5.4 COMPLETE (all mechanisms); real local
  runs next".

`tools/benchmark.py`, `engine/*.py`, `core/*.py` — all untouched this
checkpoint. This was a pure-addition checkpoint (new files + doc
updates only), same shape as V0.5.1/V0.5.2/V0.5.3.

## Exact next step

**Locally, whenever convenient (no rush, not blocking anything) —**
one session now covers all three open V0.5.x validation questions at
once, since every tool reads/writes the same corpus:
```bash
python tools/compare_engines.py --a-depth 2 --a-use-endgame-heuristics --b-depth 2 --games 20 --output data/selfplay.jsonl
python tools/compare_engines.py --a-depth 3 --b-depth 2 --games 20 --output data/selfplay.jsonl
python tools/build_opening_book.py
python tools/analyze_endgame.py
```

**Here:** with V0.5.1 (recording) through V0.5.4 (strength comparison)
all in place as mechanisms, the V0.5 line's remaining work is almost
entirely "run real data through the tools that already exist" rather
than new code. Reasonable next options at the next checkpoint:
(a) pause new feature work here and prioritize a real local run of the
commands above, since three separate validation questions are now
blocked on exactly the same missing input; or (b) if continuing
feature work regardless, move to `docs/roadmap.md`'s V0.6+ section
(neural evaluation / MCTS), the next planned major line. Will
checkpoint again once one of those has actually happened.

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

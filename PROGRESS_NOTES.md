# AlphaZetaChess Progress Snapshot — Diversity bug found via real data, fixed (V0.5.2b)

Snapshot date: 2026-09-02

## What happened this checkpoint

You shared a real 10-game self-play batch (`data/selfplay.jsonl`,
depth=2, symmetric config). Inspected it directly:

**All 10 games were byte-for-byte identical** — same result
(`BLACK_WINS`), same length (82 moves), every move matching exactly.
This confirms — with real data, not just prediction — the "Known
limitation" flagged in `docs/v0.5.2.md`: `SearchEngine` is fully
deterministic, so naive self-play with identical configs on both sides
always replays the same game from the fixed starting position.

## Fix implemented and verified

`src/alphazetacchess/selfplay/opening_randomization.py`:
`RandomizedOpeningEngine` wraps any engine; for the first N plies, has
a configurable probability of playing a random legal move instead of
the wrapped engine's choice (standard epsilon-greedy exploration for
self-play diversity). `tools/self_play.py` now uses this **by default**
(10 plies, 30% probability; `--random-opening-prob 0` disables it for
old-style deterministic games).

## What was verified this checkpoint

```
python -m py_compile src/alphazetacchess/selfplay/opening_randomization.py tools/self_play.py
→ OK

pytest tests/test_opening_randomization_v052b.py -q
4 passed in 3.63s

pytest tests/ -q -k "v041 or v042 or v043 or v044 or v045 or v051 or v052"
64 passed, 45 deselected in 4.63s
```

Real CLI smoke test: `python tools/self_play.py --games 4 --depth 1
--max-moves 16` → confirmed all 4 games are now genuinely different
(different opening moves each), unlike the uploaded batch. Temp files
cleaned up, not left in the repo.

**Not run this checkpoint:** a real depth=2 batch with the fix in
place — that's the natural next local run for you, whenever
convenient, no rush.

## What changed

- `src/alphazetacchess/selfplay/opening_randomization.py` (new):
  `RandomizedOpeningEngine`.
- `tools/self_play.py`: uses the wrapper by default; new
  `--random-opening-plies`/`--random-opening-prob` flags; docstring
  updated to explain why and how to disable.
- `tests/test_opening_randomization_v052b.py` (new, 4 tests) —
  including one that directly reproduces the actual bug found (two
  randomized games with different seeds must differ).
- `docs/v0.5.3-data-check.md` (new): full diagnosis writeup — what was
  found, why, the fix, and verification.
- `docs/roadmap.md`: V0.5.2b section added, hand-off diagram updated.

## Your 10 uploaded games: not wasted, just not usable for the book/endgame work

They're a confirmed, reproduced diagnosis of a real problem, which is
genuinely useful — just not statistically informative for V0.5.2's
opening book or V0.5.3's endgame heuristics (nothing to learn from one
repeated line). No action needed on your end for those specific files.

## Exact next step

**Locally, whenever convenient (no rush, not blocking anything):**
```bash
python tools/self_play.py --games 20 --depth 2 --output data/selfplay.jsonl
```
No extra flags needed — randomization is now the default. Can append to
the same file as before; the old 10 identical games won't hurt anything
once mixed with real diverse data.

**Here:** proceeding independently to V0.5.3 (endgame heuristics from
self-play data) — same reasoning as V0.5.2, the mechanism can be built
and tested without a large or even real corpus yet. Will checkpoint
again once that's in a reasonable state.

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

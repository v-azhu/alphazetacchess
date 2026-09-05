# AlphaZetaChess Progress Snapshot — 63-game real checkpoint + book-comparison wiring

Snapshot date: 2026-09-05

## What happened this checkpoint

The user ran several real self-play/comparison batches locally (where
a real background process is practical, unlike this session's
sandbox) and pushed the results, along with a documentation cleanup
(removed duplicate root-level version docs that had been superseded by
their `docs/` counterparts; moved this file from repo root to
`docs/PROGRESS_NOTES.md`).

`data/selfplay.jsonl` grew from 12 to **63 real games** (all depth=2):
38 plain self-play + 25 `use_endgame_heuristics` on-vs-off comparison
games (14 with ON as Red, 11 with ON as Black).

Ran the existing tools against the full 63-game corpus:

- **Opening book**: the committed `data/opening_book.json` had gone
  stale at 689 positions (built against an intermediate, smaller
  version of the corpus partway through local collection). Rebuilt
  fresh from the final 63-game file: **1057 unique positions, 1121
  position-move entries**. Confirmed end to end (not just "the file
  exists") that `SearchEngine(use_opening_book=True, opening_book=...)
  .choose_move(Board(), Color.RED)` actually returns `from_book=True`.

- **Endgame heuristic**: `tools/analyze_endgame.py` found 30/63 games
  reached the endgame phase, 16 decided Rook/Cannon-edge positions,
  **exactly 50% favored-side win rate**. Isolating the 25 real
  `use_endgame_heuristics` on-vs-off comparison games specifically: 3
  wins / 3 wins / 19 draws — **50.0% score rate, Elo diff +0**. A real
  null result at this sample size and depth, not "too small to tell."
  The previous 12-game checkpoint's 75%-favored-side-won number is now
  understood to have been small-sample noise, exactly as its own
  caveat warned it might be.

- **Surfaced a real gap**: `tools/compare_engines.py` had no
  `--use-opening-book` flag (built before the book was substantial
  enough to be worth comparing). Added `--a-use-opening-book`/
  `--b-use-opening-book` + shared `--opening-book`/
  `--opening-book-min-games`, wired to `SearchEngine`'s existing
  V0.5.2 parameters. Documented the interaction with opening
  randomization (can override a book move by design;
  `--random-opening-prob 0` isolates the book's own effect).
  Smoke-tested both the happy path and the missing-book-file fallback.

`use_endgame_heuristics` and the opening book both **remain off by
default** — the checkpoint found no evidence of harm, but also none of
benefit yet, and the project's established posture is "on by default
only once measured to help."

## What was verified this checkpoint

```
pytest -q   (full suite)
130 passed in 126.10s
```
No `src/` changes were needed for the book-comparison CLI addition
(`SearchEngine`'s `use_opening_book` support already existed and is
already covered by V0.5.2's own test suite) — this checkpoint's code
change was additive-only in `tools/compare_engines.py`.

Manual smoke tests (documented in `docs/v0.5.4.md`'s addendum):
```
python tools/compare_engines.py --a-use-opening-book --random-opening-prob 0 --games 1 --max-moves 5 --a-depth 1 --b-depth 1
  → book loads (1057 positions), from_book move returned instantly (0.8s for the whole game)

python tools/compare_engines.py --a-use-opening-book --opening-book /tmp/does_not_exist.json --games 1 --max-moves 0
  → clear fallback message, continues without a book rather than crashing
```

## What changed

- `data/selfplay.jsonl`: 12 → 63 real games (user's local runs).
- `data/opening_book.json`: rebuilt fresh from the full 63-game
  corpus (689 → 1057 positions; the committed version had gone stale).
- `tools/compare_engines.py`: added `--a-use-opening-book`/
  `--b-use-opening-book`/`--opening-book`/`--opening-book-min-games`.
- `docs/v0.5-real-data-checkpoint-2.md` (new): full breakdown of the
  63-game corpus and what it does/doesn't establish.
- `docs/v0.5.4.md`: addendum documenting the book-comparison flags.
- `docs/roadmap.md`: hand-off section updated with the real 63-game
  numbers and the book-comparison gap/fix.
- Repo hygiene (user, before this checkpoint's work): removed
  duplicate root-level `.md` docs superseded by `docs/` versions;
  moved `PROGRESS_NOTES.md` to `docs/PROGRESS_NOTES.md`. Checked for
  broken cross-references from other docs — none found.

## Exact next step

Three open questions, all answerable by extending the same
`data/selfplay.jsonl` corpus (63 real games already banked):

```bash
# Does the book actually help? (mechanism confirmed; strength still untested)
python tools/compare_engines.py --a-use-opening-book --random-opening-prob 0 --games 20 --output data/selfplay.jsonl

# Does depth=3 beat depth=2?
python tools/compare_engines.py --a-depth 3 --b-depth 2 --games 20 --output data/selfplay.jsonl

# Does use_endgame_heuristics show a different (real) result at a depth
# where search can act on the material nudge more meaningfully?
python tools/compare_engines.py --a-depth 3 --a-use-endgame-heuristics --b-depth 3 --games 20 --output data/selfplay.jsonl
```

Also worth keeping in mind independent of any specific term: the
corpus's overall draw rate (40/63 ≈ 63%, and 19/25 ≈ 76% within the
endgame-heuristic comparison slice specifically) may itself be
limiting how much signal any depth=2 comparison can find, regardless
of sample size — worth revisiting if future comparisons keep coming
back "no detectable difference."

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

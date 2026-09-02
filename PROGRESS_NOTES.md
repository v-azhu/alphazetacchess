# AlphaZetaChess Progress Snapshot — V0.5.1 (Self-Play Recording) COMPLETE

Snapshot date: 2026-09-01

## Recovery note

This checkpoint resumed directly from a mid-work interruption: the
sandbox survived, `docs/v0.5.1.md` had already been fully written, but
`docs/roadmap.md`'s V0.5 section and this file hadn't been updated yet.
Picked up exactly there.

## Scope decision recorded

Per your call: Endgame Knowledge and Opening Knowledge (the two V0.4
items left undone after V0.4.5) will be learned from self-play data
rather than hand-coded, folded into V0.5 rather than becoming a
V0.4.6/V0.4.7. `docs/roadmap.md` now reflects this — V0.4 marked
COMPLETE (five of five original additive-scoring terms), V0.5 marked
CURRENT.

## What this checkpoint did

Built V0.5.1: self-play game **recording** infrastructure (not yet
analysis — that's V0.5.2+). This is the foundation everything else in
V0.5 depends on: an opening book or endgame heuristic both need
recorded games to derive from.

## What was verified this checkpoint

```
python -m py_compile src/alphazetacchess/selfplay/recorder.py tools/self_play.py
→ OK

pytest tests/test_selfplay_recorder_v051.py tests/test_mobility_v043.py \
       tests/test_evaluation_v043.py tests/test_search_v043_beta2.py \
       tests/test_evaluation_v041.py tests/test_evaluation_v042.py \
       tests/test_pawn_structure_v044.py tests/test_piece_coordination_v045.py -q
51 passed in 0.42s
```

Smoke test (from an earlier point in this session, files since cleaned
up): `python tools/self_play.py --games 2 --depth 1 --max-moves 20` ran
end to end in 22s, output file verified well-formed (correct keys,
correct move sequences, correct config dict).

**Not run this checkpoint (kept small deliberately):** any real
data-collection batch at `depth=2` (the realistic setting) — individual
games there have historically taken 1-3+ minutes, so a data set large
enough to be useful is a local, long-running task by design.

## What changed

- `src/alphazetacchess/selfplay/__init__.py`, `recorder.py` (new):
  `play_recorded_game()` (full move-by-move game recording, built on
  the same primitives `tools/benchmark.py`'s win-rate-only `play_game`
  uses), `append_record()`/`load_records()` (JSON-lines I/O,
  append-only).
- `tools/self_play.py` (new): CLI wrapper, `--games`/`--depth`/`--output`
  plus flags matching `SearchEngine`'s V0.4.1-4.5 toggles.
- `tests/test_selfplay_recorder_v051.py` (new, 5 tests) — including a
  fully deterministic decisive-game test that caught and fixed a real
  bug: `recorder.py`'s first draft read `.from_pos` directly off
  `choose_move()`'s return value, but every engine's `choose_move()`
  returns a uniform `SearchResult` wrapper (see `engine/base.py`), not
  a bare `Move`. Fixed to match how `tools/benchmark.py` already did
  it correctly.
- `data/README.md` (new), `.gitignore` updated to exclude `data/*.jsonl`
  — also fixed an unrelated pre-existing bug while touching this file:
  the original `.gitignore` had no trailing newline, so a naive append
  would have silently merged onto its last line; reconstructed the
  whole file explicitly instead.
- `docs/v0.5.1.md` (new): full design, record format, and reasoning.
- `docs/roadmap.md`: V0.4 → COMPLETE, V0.5 → CURRENT, V0.5.1 section
  added, hand-off diagram updated.

## Exact next step

**Locally, whenever convenient (not blocking anything else):**
```bash
python tools/self_play.py --games 20 --depth 2 --output data/selfplay.jsonl
```
Records accumulate across runs, so this can be run in small batches
over time rather than one long sitting. Re-run with `--use-mobility` /
`--use-pawn-structure` / `--use-piece-coordination` if you want data
specific to a particular evaluation configuration, or leave them off
for the default-configuration baseline.

**Here, independent of that:** V0.5.2 (a simple opening book — analyze
recorded move-1/move-2/... win rates, use the book for early moves
instead of searching) is the natural next increment, and the mechanism
can be built and tested even against a small data set (the earlier
smoke-test file, or a fresh small batch), with book quality simply
improving as more real data accumulates over time. I can start on this
now, or wait for you to run a real batch first — your call, since
neither blocks the other.

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

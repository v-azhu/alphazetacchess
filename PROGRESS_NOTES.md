# AlphaZetaChess Progress Snapshot — V0.5.2 (Opening Book) mechanism COMPLETE

Snapshot date: 2026-09-02

## Recovery note

Resumed from a mid-work interruption: sandbox survived. Exact break
point: `opening_book.py`, `tools/build_opening_book.py`, and
`SearchResult.from_book` had already been written, but `SearchEngine`
didn't have the book wired in yet. Picked up exactly there. (Also fixed
a self-inflicted syntax error from an earlier no-op edit that had
accidentally merged two lines in `search.py` — caught immediately by
the compile check, not by you.)

## What this checkpoint did

Built V0.5.2: an opening book derived from V0.5.1's self-play records,
wired into `SearchEngine` as an opt-in fast path that skips search
entirely when there's a confident book entry.

## What was verified this checkpoint

```
python -m py_compile src/alphazetacchess/engine/search.py \
                      src/alphazetacchess/engine/base.py \
                      src/alphazetacchess/selfplay/opening_book.py \
                      tools/build_opening_book.py
→ OK

pytest tests/ -q -k "v041 or v042 or v043 or v044 or v045 or v051 or v052"
60 passed, 45 deselected in 1.42s
```

Smoke test, self-play → book → book-driven move, full pipeline:
```
python tools/self_play.py --games 3 --depth 1 --max-moves 10 --output /tmp/smoke_selfplay.jsonl
python tools/build_opening_book.py --input /tmp/smoke_selfplay.jsonl --output /tmp/smoke_book.json --max-ply 4
→ 4 positions, correct per-move win/draw/loss/games stats
```
(temp files cleaned up after, not left in the repo).

**Not run this checkpoint:** any book built from a real, larger self-play
corpus (this session's data was a small deterministic smoke test only —
see "Known limitation" below), and no web UI wiring for loading/using a
book yet (deliberately deferred to keep this checkpoint focused on the
core mechanism).

## What changed

- `src/alphazetacchess/engine/base.py`: `SearchResult` gained
  `from_book: bool = False` (defaulted, doesn't break any existing
  construction call).
- `src/alphazetacchess/selfplay/opening_book.py` (new):
  `build_book_from_records()`, `select_book_move()`, `save_book()`/
  `load_book()`. Keyed by (Zobrist hash, color) for transposition
  sharing.
- `tools/build_opening_book.py` (new): CLI to build a book file from
  `tools/self_play.py`'s output.
- `src/alphazetacchess/engine/search.py`: `use_opening_book`/
  `opening_book`/`opening_book_min_games` constructor params;
  `choose_move()` checks the book first via a new `_book_move()`
  helper, falls through to normal search unchanged when there's no
  confident entry.
- `tests/test_opening_book_v052.py` (new, 9 tests).
- `docs/v0.5.2.md` (new): full design, known limitation, next steps.
- `docs/roadmap.md`: V0.5.2 section added, hand-off diagram updated.

## Known limitation (important, read before running a big self-play batch)

A fully-deterministic `SearchEngine` playing itself at low depth always
makes the same moves — so a book built from that kind of data has
exactly one candidate move per position, no real diversity to choose
between. This isn't a bug in V0.5.2's mechanism (the 9 tests confirm it
works correctly on whatever data it's given), it's a property of the
*data*. Before investing in a big `--games 100+` run, worth deciding
whether depth=2 self-play naturally diverges enough (material trades
create different branches) or whether intentional randomization during
data collection is needed. Full reasoning in `docs/v0.5.2.md`.

## Exact next step

**Locally, whenever convenient:**
```bash
python tools/self_play.py --games 20 --depth 2
python tools/build_opening_book.py
```
Then look at `data/opening_book.json` — if most positions still only
have one candidate move despite real games being played, that confirms
the diversity concern above and randomized move sampling becomes the
right next fix; if there's genuine variety, the book is already usable
as-is.

**Here, independent of that:** V0.5.3 (endgame heuristics from
self-play data — the other half of the scope originally deferred from
V0.4) doesn't depend on V0.5.2 having real data first. I can start
there next, or pick up web UI wiring for loading/using a book — happy
to take direction if you have a preference when you're back, otherwise
I'll use judgment on which is more valuable to do first.

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

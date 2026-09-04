# AlphaZetaChess Progress Snapshot — First real data checkpoint (post-V0.5.4)

Snapshot date: 2026-09-04

## What happened this checkpoint

Every V0.5.x doc through V0.5.4 ended with "mechanism complete, real
corpus still needed." This checkpoint is the first (small) real
installment of that corpus, not another mechanism.

Discovered the originally planned approach ("kick off a background
batch, keep working, check back later") doesn't work in this sandbox
-- a `nohup ... &` background process was gone by the next tool call.
Switched to running `tools/self_play.py --games 1` synchronously, one
game at a time with a `timeout` guard (depth=2 games take 70-250s
here; a few attempts hit the time limit mid-game and produced no
record, since `append_record` only writes after a game completes).

Collected 12 real games this way:
- 10 via `tools/self_play.py` (depth=2, no optional eval terms,
  random opening): 6 draws, 2 RED wins, 2 BLACK wins.
- 2 via `tools/compare_engines.py` (`--a-use-endgame-heuristics` vs
  plain depth=2): 1 loss and 1 draw for the heuristic-on side.

Ran the existing tools against this real corpus for the first time:
- `tools/build_opening_book.py`: 213 unique positions, 224
  position-move entries, saved to `data/opening_book.json`.
- `tools/analyze_endgame.py`: 8/12 games reached the endgame phase
  (average onset ply 67.2), 4 decided Rook/Cannon-edge positions (3/4
  favored side won) -- directionally consistent with
  `engine/endgame.py`'s hypothesis, but the tool's own "sample too
  small" caveat is exactly right and was NOT overridden or soft-pedaled.

## What was verified this checkpoint

Both `tools/build_opening_book.py` and `tools/analyze_endgame.py` ran
correctly end-to-end against real (not synthetic/smoke-test) data for
the first time -- this is itself a meaningful confirmation, separate
from whatever the small-sample numbers say. No new pytest tests added
this checkpoint (pure data-collection + doc-writing checkpoint, no
code changed); full suite last confirmed green at 130/130 in the
V0.5.4 checkpoint and nothing in `src/` changed since.

## What changed

- `data/selfplay.jsonl` (12 real game records) -- committed
  deliberately, overriding the default `.gitignore` rule, per
  `data/README.md`'s own stated exception for preserving a specific
  corpus. This is the first non-empty real corpus the project has had.
- `data/opening_book.json` (213 positions, built from the above) --
  committed alongside it.
- `docs/v0.5-real-data-checkpoint.md` (new): full breakdown of what
  was run and what it does/doesn't show.
- `docs/roadmap.md`: hand-off section updated with this checkpoint's
  real numbers.

## Exact next step

A much larger batch (30-50+ games) is still needed before any of
V0.5.2's book quality, V0.5.3's endgame constants, or V0.5.4's
strength-comparison questions can be trusted. `data/selfplay.jsonl`
already has 12 real games in it -- `tools/self_play.py --output
data/selfplay.jsonl` appends rather than overwrites, so this
checkpoint's data extends forward rather than needing to be redone:

```bash
python tools/self_play.py --games 40 --depth 2 --max-moves 150 --output data/selfplay.jsonl
python tools/build_opening_book.py --input data/selfplay.jsonl --output data/opening_book.json
python tools/analyze_endgame.py --input data/selfplay.jsonl
python tools/compare_engines.py --a-depth 2 --a-use-endgame-heuristics --b-depth 2 --games 20 --output data/selfplay.jsonl
```

Best run from an environment where a real background/long-running
process is practical (a real local machine), not a sandboxed session
that loses background processes between commands -- that constraint is
exactly what kept this checkpoint's corpus small (12 games rather than
the 20-40+ that would make analyze_endgame's numbers trustworthy).

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

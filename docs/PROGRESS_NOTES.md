# AlphaZetaChess Progress Snapshot — first real strength comparison result

Snapshot date: 2026-09-06

## What happened this checkpoint

Ran real `tools/compare_engines.py --a-use-neural-eval --a-depth 2
--b-depth 2` games — the actual answer to whether V0.6.2's distillation
pipeline helped, not another mechanism smoke test.

**First learned something about the tool itself before trusting any
result**: with `--random-opening-prob 0` (the setting used earlier to
isolate the opening book's effect), `SearchEngine` is fully
deterministic and the starting position is fixed, so re-running the
identical command reproduces the identical 2 games every time — not
new data. `--games N` under full determinism can only ever produce 2
distinct outcomes (one per color assignment) regardless of N. Caught
this by noticing a second run's output exactly matched the first
(same move counts, same results) rather than assuming more games meant
more data. Switched to the default (nonzero) `--random-opening-prob`
to actually accumulate distinct games.

**6 genuinely distinct real games** (depth=2, neural eval vs
heuristic; 2 from the deterministic runs, de-duplicated by exact move
sequence; 4 with randomization on):
```
Neural eval:    0 wins
Heuristic eval: 4 wins
Draws:          2
Neural score rate: 16.7%
Estimated Elo difference: -280
```

**A real, if still modest-sized, signal that the heuristic currently
outperforms the neural evaluator at depth=2.** Not a surprise given
the training-side evidence already on record: 776 cp of held-out RMSE
is a large absolute error (more than a full Rook's value) for guiding
move selection precisely, and the earlier capacity experiment (128→64
hidden units, only ~1.3% RMSE improvement) already pointed at the
feature representation — not more parameters, epochs, or even more
comparison games — as the more promising lever for closing this gap.
`use_neural_eval` should NOT default on based on this evidence.

## What was verified this checkpoint

```
pytest -q   (full suite, unchanged code)
178 passed in 140.26s
```
No source code changed this checkpoint — pure real-data collection via
`tools/compare_engines.py`, with the aggregate computed directly from
`data/selfplay.jsonl` (de-duplicating the accidental determinism-caused
repeat by exact move sequence) rather than trusted from memory of the
individual run outputs.

## What changed

- `data/selfplay.jsonl`: +6 real comparison games (neural eval vs
  heuristic, depth=2).
- `docs/v0.6.2.md`: 6th addendum with the full result and the
  determinism lesson.
- `docs/roadmap.md`: hand-off updated.

## Exact next step

**Most promising next step, per this checkpoint's own reasoning**: not
more comparison games against the current network, but revisiting
`neural/features.py`'s representation — add explicit features closer
to what `evaluation.py` already hand-encodes (mobility, king safety,
pawn structure, piece coordination) rather than relying on a small MLP
to discover that structure from a purely positional one-hot encoding.
This is a real design/implementation task, not a quick rerun.

**If pursuing more comparison data anyway** (e.g. to firm up the exact
Elo figure rather than just its direction): remember randomization
must be ON to get distinct games —
```bash
python tools/compare_engines.py --a-use-neural-eval --a-depth 2 --b-depth 2 --games 20 --output data/selfplay.jsonl
```
(no `--random-opening-prob 0`, unlike the opening-book-isolation case).

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

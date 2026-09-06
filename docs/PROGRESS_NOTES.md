# AlphaZetaChess Progress Snapshot — neural evaluator wired into real engines

Snapshot date: 2026-09-06

## What happened this checkpoint

User tried a bigger network (128→64 hidden units) on the full 94,872-
position corpus: held-out RMSE improved only marginally, 776 → 766 cp
(~1.3%) despite ~4x more parameters. That small a gain argues against
the "capacity-limited" hypothesis from the previous checkpoint and
toward the feature representation itself being the more likely
ceiling — `neural/features.py`'s one-hot piece-position encoding has
no explicit mobility/king-safety/pawn-structure notion the way
`evaluation.py`'s hand-crafted terms do. Decided not to chase further
architecture tuning (diminishing returns) and moved to the actual
point of this whole checkpoint: does the trained network help in real
search at all?

**Added a pluggable `eval_fn` to both `SearchEngine` and
`MCTSEngine`.** `SearchEngine` gained a single `_evaluate(self, board,
color)` method that all four of its internal evaluate() call sites now
go through — `eval_fn=None` (default) reproduces every prior version's
exact behavior; setting it (e.g. to a `NeuralEvaluator`, which already
matches `evaluate()`'s `(board, color) -> float` signature) replaces
the heuristic entirely. `MCTSEngine._expand_and_evaluate` got the
equivalent treatment.

**A real bug was caught by the new tests before it could ship, not
after**: consolidating `SearchEngine`'s four call sites accidentally
left `self.tt = TranspositionTable(...)` as dead code *after* a
`return` statement — meaning `self.tt` was never actually set on any
instance. This compiled cleanly (`py_compile` can't catch unreachable
code) and wasn't obvious by inspection; it surfaced immediately when
`tests/test_pluggable_eval_v062.py` called `_quiescence` directly and
hit `AttributeError: 'SearchEngine' object has no attribute 'tt'`.
Fixed by moving the line back into `__init__` proper, and — critically
— confirmed by rerunning the FULL test suite (178/178, including every
pre-existing `SearchEngine` test) rather than trusting the targeted
fix by inspection alone.

**6 new tests**: default-`eval_fn` baseline preservation for both
engines, confirming a custom `eval_fn` is actually invoked and its
value used/squashed correctly, and an end-to-end `MCTSEngine.
choose_move` smoke test with a custom evaluator plugged in.

**`tools/compare_engines.py`** gained `--a/b-use-neural-eval` +
`--neural-eval-path`, mirroring the existing `--use-opening-book`
pattern (including the same graceful fallback if the file doesn't
exist). Smoke-tested end to end: loads the real committed network,
plays real games with it on one side.

## What was verified this checkpoint

```
pytest -q   (full suite)
178 passed in 128.92s
```
Including the 6 new pluggable-eval tests and confirming the
`self.tt` bug fix didn't break anything else. Manual smoke test of
`tools/compare_engines.py --a-use-neural-eval` (depth=1, 20-move games,
purely to confirm the mechanism works end to end, not a strength claim).

## What changed

- `src/alphazetacchess/engine/search.py`: new `_evaluate()` method,
  `eval_fn` constructor param, all 4 evaluate() call sites
  consolidated through it. Fixed the `self.tt` dead-code bug introduced
  during this same edit.
- `src/alphazetacchess/engine/mcts.py`: `eval_fn` constructor param,
  `_expand_and_evaluate` uses it when set.
- `tests/test_pluggable_eval_v062.py` (new, 6 tests).
- `tools/compare_engines.py`: `--a/b-use-neural-eval` +
  `--neural-eval-path`.
- `docs/v0.6.2.md`: 5th addendum with the full story.
- `docs/roadmap.md`: hand-off updated.

## Exact next step

**Run an actual strength comparison** — not yet done; every run so far
has been a mechanism smoke test, not a strength claim:
```bash
python tools/compare_engines.py --a-use-neural-eval --a-depth 2 --b-depth 2 --games 20 --random-opening-prob 0
```
This is the real test of whether V0.6.2's distillation pipeline
actually improved play strength, not just Pikafish-score correlation —
the question every addendum in `docs/v0.6.2.md` has been building
toward. Worth trying at a couple of depths if time allows, since the
network's usefulness could plausibly differ between shallow and deeper
search.

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

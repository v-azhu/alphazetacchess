# AlphaZetaChess Progress Snapshot — augmented neural features (breaking change, incomplete retrain)

Snapshot date: 2026-09-06

## What happened this checkpoint

Acted on the previous checkpoint's own conclusion (heuristic beat the
neural evaluator -280 Elo; more comparison games wouldn't fix that,
the representation needed work): added 8 auxiliary hand-crafted
features to `neural/features.py`, reusing `engine/evaluation.py`'s own
sub-components directly — material balance, `mobility_balance`,
`pawn_structure_balance`, `piece_coordination_balance`,
`endgame_balance`, king safety (via `evaluate()`'s own private
`_king_safety_score`), and both sides' check status — rather than
reinventing feature engineering from scratch. The network's job
changes from "learn these heuristics from raw occupancy" to "learn how
to weigh/correct these heuristics against Pikafish's judgment."

**`FEATURE_DIM` changed 1260 → 1268 — a breaking change** for any
network trained on the old pure-one-hot encoding. `NeuralEvaluator.
__init__` now checks the loaded network's actual input dimension
against the current `FEATURE_DIM` and raises a clear, actionable
`ValueError` immediately, instead of letting an old network fail with
an opaque numpy matmul-shape error the first time it's evaluated.

**6 new tests**: exact `FEATURE_DIM`, auxiliary features zero on the
symmetric starting position, a hand-verified material-difference
assertion (removing a Rook produces exactly `900/500` from both
perspectives with correct sign), mirror-symmetry extended to the new
features, own/opponent check-status correctness, and the
stale-dimension rejection. Combined total: **184/184 green**.

**Retrained on the real corpus — honestly, an incomplete run.** This
sandbox's per-command time budget cut training short at 175 epochs
(the deterministic curve was still improving, hadn't triggered
`--patience`'s early stop yet). Best checkpoint at epoch 162: held-out
RMSE **767.2 cp** (vs. the old network's 776.3 cp — a real but modest
~1.2% improvement), correlation 0.782 (vs. 0.777, essentially
unchanged). One real strength-comparison game with the new network:
heuristic won again (76 moves) — consistent with the modest RMSE
change, but a single game proves nothing.

**Explicitly not claiming this is a fair test of the auxiliary
features' real potential.** The mechanism is solid and well-tested;
the actual verdict on whether it helps needs a full, uninterrupted
local training run and a real strength comparison, neither of which
this session's time budget could complete.

## What was verified this checkpoint

```
pytest -q   (full suite)
184 passed in 169.21s
```
Direct verification of the retrained network: weight magnitude sane
(2.34), input dimension matches (1268), held-out correlation/RMSE
computed against the training script's own train/val split.

## What changed

- `src/alphazetacchess/neural/features.py`: 8 auxiliary hand-crafted
  features added, `FEATURE_DIM` 1260 → 1268 (breaking change).
- `src/alphazetacchess/neural/evaluator.py`: explicit, clear
  dimension-mismatch check at construction time.
- `tests/test_network_v062.py`, `test_evaluator_v062.py`: 6 new tests.
- `data/neural_eval.npz`: retrained (incompletely — see above) on the
  new feature representation.
- `data/selfplay.jsonl`: +1 real comparison game with the new network.
- `docs/v0.6.2.md`: 8th addendum with the full, honest story.
- `docs/roadmap.md`: hand-off updated.

## Exact next step

**On the user's machine — a full, uncapped retrain and a real
comparison**, the honest headline question this whole V0.6.2 line has
been building toward:
```bash
python tools/train_neural_eval.py
python tools/compare_engines.py --a-use-neural-eval --a-depth 2 --b-depth 2 --games 20 --output data/selfplay.jsonl
```
Check whether the auxiliary features closed the -280 Elo gap from the
previous checkpoint's comparison, worsened it, or left it about the
same — any of those three is a real, informative answer at this point.

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

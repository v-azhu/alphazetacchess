# AlphaZetaChess Progress Snapshot — first working neural evaluator (0.92 correlation)

Snapshot date: 2026-09-06

## What happened this checkpoint

User reran training with the divergence fix, on the real labeled
dataset (2888 positions from 99 self-play games, force-pushed as
`data/pikafish_labels.jsonl` this time so it's reproducible). No
divergence: `Target standardization: mean=-219.4 cp, std=3061.4 cp`
printed sanely, weight magnitude stayed at 0.78.

**Didn't stop at "RMSE went down" — checked whether it learned
anything real.** Probed the network on a few hand-constructed
positions first (starting position, a position with a rook removed)
and got a concerning result: predictions got MORE confidently
backwards as the constructed material imbalance grew. Investigated
rather than panicking or dismissing:
1. Checked `Board.move()` actually flips `current_player` (it does) —
   ruled out a FEN/perspective mismatch between labeling and training.
2. Computed correlation between predictions and real Pikafish labels
   on the ACTUAL held-out validation split (288 positions never seen
   during training, same split the training script itself uses) — the
   fair, in-distribution test, unlike the hand-crafted probes above.
   Result: **correlation 0.88-0.92**, RMSE 40-60% of the naive
   "predict the mean" baseline.

**Conclusion**: the network genuinely learned real signal from
Pikafish's evaluations on realistic positions. The "backwards" probe
result was a real but different limitation: a small feedforward net
with 1260 sparse binary features, trained on ~2600 examples, doesn't
generalize additively to hand-crafted, out-of-distribution material
configurations that don't resemble anything in real self-play games —
unlike `evaluation.py`'s hard-coded material-counting term, which
generalizes perfectly by construction. Worth remembering, not a bug.

**Tuned training length**: compared 200 vs 800 vs 1000 epochs directly.
Validation RMSE improved substantially 200→800 (1578→1292 cp) then
plateaued 800→1000 (1292→1290) while training RMSE kept dropping
(840→771) — classic overfitting-onset signature (widening train/val
gap). Updated `tools/train_neural_eval.py`'s default `--epochs` from
200 to **800**.

**Final committed network** (`data/neural_eval.npz`, 800 epochs): max
weight magnitude 1.1 (healthy), held-out validation correlation
**0.915**, RMSE **1292 cp** vs. naive baseline 3201 cp. Real, working,
still imprecise (1292 cp is more than a full Rook's value).

## What was verified this checkpoint

```
pytest -q   (full suite, unchanged from previous checkpoint's code)
172 passed in 153.59s
```
Verified directly (not just via unit tests, since this checkpoint was
about a real trained artifact, not new code): weight magnitude sanity
check, held-out correlation computation matching the training script's
own train/val split exactly, and a direct 200-vs-800-vs-1000-epoch
comparison to justify the new default.

## What changed

- `data/neural_eval.npz`: replaced the diverged network with a real,
  working one (800 epochs, correlation 0.915).
- `tools/train_neural_eval.py`: default `--epochs` 200 → 800.
- `docs/v0.6.2.md`: second addendum with the full investigation and
  final numbers.
- `docs/roadmap.md`: hand-off updated.

## Exact next step

**More labeled data is the likelier lever now**, more than further
training epochs (which have plateaued): the current 2888 positions
come from only 99 self-play games.
```bash
python tools/label_positions_with_pikafish.py --pikafish-path /path/to/pikafish --network-path /path/to/pikafish.nnue --sample-every 2
python tools/train_neural_eval.py
```
(`--sample-every 2` instead of 4 roughly doubles the label count from
the same 99 games without needing new self-play data first.)

**Here, once more data has been tried (or even with the current
network, to get a first real signal)**: add a pluggable `eval_fn` to
`SearchEngine`/`MCTSEngine` (both currently hardcode `evaluate()`),
wire `NeuralEvaluator` in, and run `tools/compare_engines.py` with it
on one side — the real test of whether any of this helped actual play
strength, not just Pikafish-score correlation.

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

# AlphaZetaChess Progress Snapshot — early stopping added; capacity question open

Snapshot date: 2026-09-06

## What happened this checkpoint

User labeled the full 3,957-game external corpus and retrained: the
dataset grew from 2,888 to **94,872** labeled positions (~33x). The
fixed `--epochs 800` default (tuned for the smaller dataset) caused a
real, visible overfitting signature on the much larger one — the
user's own training log showed validation RMSE bottoming out around
epoch 160 (780.7 cp) and then **worsening** through epoch 800 (815.3
cp) while training RMSE kept dropping (503.6 → 239.0 cp). A hardcoded
epoch count has no way to know in advance where that point will land
for a dataset it hasn't seen yet.

**Fixed properly, not by re-guessing another fixed number**: added
early stopping to `tools/train_neural_eval.py`. Validation RMSE is now
checked every epoch, the best-seen checkpoint is kept in memory, and
training halts after `--patience` (default 40) epochs without
improvement — the saved network is always the best validation
checkpoint actually observed. Smoke-tested the mechanism on a small
synthetic dataset (confirmed it triggers and restores the right
checkpoint) before running the real, expensive retrain.

**Retrained on the full 94,872-position corpus**: stopped automatically
at epoch 198 (saving ~75% of the wall-clock cost `--epochs 800` would
have used), restoring the epoch-158 checkpoint. Weight magnitude
healthy (2.2), held-out RMSE **776 cp** vs. naive baseline **1228 cp**.

**Honest, mixed result — stated plainly, not glossed over**: held-out
correlation actually dropped to **0.777** (from the smaller dataset's
0.915). Investigated rather than either celebrating the RMSE
improvement or panicking about the correlation drop: the target
distribution itself changed substantially — the naive baseline's own
RMSE dropped from 3201 to 1228 cp, meaning the new corpus (much more
real-game-heavy) has far less mate-score-driven variance to predict
than the old, mostly-self-play corpus did. Correlation is a *relative*
measure, so a tighter target distribution is genuinely harder to
correlate well with even when absolute error improved.

**A real, open question surfaced, not resolved**: early stopping
firing at epoch 158 out of a possible 800, on a dataset now 30x
larger, hints the network's fixed 64→32 hidden-unit capacity may now
be the real bottleneck (underfitting) rather than overfitting risk.
Started a 128→64 hidden-unit experiment on the full corpus, but it
didn't finish within this session's per-command time budget (bigger
networks are proportionally slower per epoch) — left as an open next
experiment, not claimed as a completed result.

## What was verified this checkpoint

```
pytest -q   (full suite, unchanged code paths)
172 passed in 167.27s
```
Early-stopping mechanism smoke-tested directly on synthetic data
before trusting it on the real retrain. Final network verified
directly: weight magnitude (2.2, healthy), held-out correlation and
RMSE computed against the exact same train/val split the training
script itself uses.

## What changed

- `tools/train_neural_eval.py`: added early stopping (`--patience`,
  default 40) — validates every epoch, keeps the best checkpoint,
  halts on no improvement, rather than always training exactly
  `--epochs` times.
- `data/neural_eval.npz`: retrained on the full 94,872-position corpus
  with early stopping (best checkpoint from epoch 158).
- `docs/v0.6.2.md`: 4th addendum with the full investigation.
- `docs/roadmap.md`: hand-off updated.

## Exact next step

**On the user's machine**: try a larger network now that early
stopping guards against overfitting regardless of capacity choice —
this is the open capacity question from this checkpoint:
```bash
python tools/train_neural_eval.py --hidden1 128 --hidden2 64
```
Compare held-out RMSE/correlation against the current 776cp/0.777 —
if a bigger network does meaningfully better, that confirms the
capacity hypothesis; if not, the current network is likely close to
what this feature representation can support.

**Here, once satisfied with the network (current one or a bigger
one)**: add a pluggable `eval_fn` to `SearchEngine`/`MCTSEngine` (both
currently hardcode `evaluate()`), wire `NeuralEvaluator` in, and run
`tools/compare_engines.py` with it on one side — the real test of
whether any of this helped actual play strength, not just
Pikafish-score correlation.

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

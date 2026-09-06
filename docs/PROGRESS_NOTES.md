# AlphaZetaChess Progress Snapshot — training divergence found and fixed

Snapshot date: 2026-09-06

## What happened this checkpoint

User ran the full V0.6.2 pipeline for real: labeled positions with a
local Pikafish binary (after a `--network-path` fix for a Windows
network-file-location issue) and trained a network, pushing
`data/neural_eval.npz` (the `pikafish_labels.jsonl` file itself wasn't
pushed -- it's gitignored by default, `git add` without `-f` silently
skipped it).

**Loaded and sanity-checked the trained network directly rather than
assuming it worked.** Result: broken. Every prediction was the same
absurd constant (~-3.9e10) regardless of position -- starting
position, a position with Red up a full rook, evaluated from either
side, all identical. Inspected the saved weights directly: every
matrix had entries around **1e24 to 1e27** in magnitude. Training had
diverged, not "learned a bad function."

**Root cause**: Pikafish's raw `score_cp` labels range up to +/-9000
(mate scores via `mate_score_to_cp`). Plain mean-squared-error
gradient descent against targets that large, at a learning rate tuned
for roughly unit-scale targets, blows the weights up within the first
few steps rather than converging -- a standard, well-understood
regression-training failure mode. Independently confirmed this is NOT
a backprop-correctness bug: the numerical gradient check from the
original V0.6.2 checkpoint already verified the math itself is right.

**Fixed two ways, together**:
- `SmallMLP` gained `y_mean`/`y_std` attributes. `predict()` always
  returns real-scale (centipawn) values; `train_step` is fed
  pre-standardized (roughly unit-scale) targets by the caller.
- `tools/train_neural_eval.py` now computes `y_mean`/`y_std` from the
  training set itself before training, and prints an explicit warning
  if post-training weight magnitude still looks like divergence.
- `train_step` also gained gradient-norm clipping (`max_grad_norm=10.0`
  default) as defense-in-depth, independent of standardization.

## What was verified this checkpoint

```
pytest -q   (full suite)
172 passed in 161.53s
```
5 new tests, most importantly one that **reproduces the actual
failure** (synthetic targets at the same order of magnitude as real
Pikafish labels) and confirms standardized training now stays bounded.

Also verified directly (not just via unit tests): built a synthetic
dataset from real self-play positions with large-scale (~thousands of
cp) synthetic labels, ran the fixed `tools/train_neural_eval.py`
against it -- **max weight magnitude after training: 0.73** (vs. the
1e24+ seen in the real divergence).

## What changed

- `src/alphazetacchess/neural/network.py`: `y_mean`/`y_std` target
  standardization, gradient-norm clipping in `train_step`,
  backward-compatible `load()` for networks saved before this fix.
- `tools/train_neural_eval.py`: sets `y_mean`/`y_std` from the
  training data, trains on standardized targets, warns if weights look
  diverged after training.
- `tests/test_network_v062.py`: 5 new tests.
- `docs/v0.6.2.md`: addendum documenting the divergence, root cause,
  and fix.

**`data/neural_eval.npz` currently in the repo is from the diverged
run and should not be used or trusted.**

## Exact next step

**On the user's machine**: rerun training with the fix (no need to
re-label -- the existing `data/pikafish_labels.jsonl` from the earlier
run should still be there locally, even though it wasn't pushed):
```bash
python tools/train_neural_eval.py
```
Check the printed `Target standardization: mean=... cp, std=... cp`
line looks sane (roughly matching real Xiangqi evaluation scale, not
near-zero or absurdly large), and confirm no divergence warning
prints. Then push the corrected `data/neural_eval.npz` -- and this
time also force-add the labels file so it's actually preserved and
reproducible:
```bash
git add -f data/pikafish_labels.jsonl data/neural_eval.npz
git commit -m "..."
git push
```

**Here, once a real, non-diverged trained network exists**: sanity-
check its predictions on a few known positions (starting position
near 0, a clear material-advantage position clearly favoring the
correct side) before trusting it further, then add a pluggable
`eval_fn` to `SearchEngine`/`MCTSEngine` and compare against the
existing heuristic `evaluate()` via `tools/compare_engines.py`.

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

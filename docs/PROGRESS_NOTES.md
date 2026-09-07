# AlphaZetaChess Progress Snapshot — V0.6.2 concluded: a real negative result

Snapshot date: 2026-09-06

## What happened this checkpoint

User ran the full, uninterrupted retrain and the real 20-game
comparison the previous checkpoint called for.

**Training converged properly** (no session time-budget cutoff this
time): early stopping triggered at epoch 268, restoring the epoch-228
checkpoint. Held-out RMSE **760.5 cp**, correlation **0.786** — only
marginally better than the earlier interrupted run's 767.2 cp / 0.782.

**20 real games, depth=2, neural eval vs heuristic**:
```
Neural eval:    1 win
Heuristic eval: 14 wins
Draws:          5
Neural score rate: 17.5%
Estimated Elo difference: -269
```
Verified by recomputing directly from `data/selfplay.jsonl` (not
trusted from the printed summary alone).

**This is the real, final verdict for this approach at this scale —
not undertraining, not an artifact.** -269 Elo is essentially
unchanged from the pre-auxiliary-features result (-280 Elo on 6
games). Three attempts in a row, each reasonable at the time, showed
the same small, easily-exhausted return on actual playing strength:
more network capacity (128→64 hidden units: ~1.3% RMSE improvement),
~33x more training data (via the external-games import), and richer
features (8 hand-crafted auxiliary features: ~1.2% RMSE improvement).
A consistent picture, not three unrelated setbacks — this is a real
current ceiling for a small hand-featured MLP trained on ~95k
positions.

**A plausible reason correlation doesn't translate to strength**:
alpha-beta search needs the evaluation function to be *locally
consistent* across sibling nodes, not just *globally correlated* with
a strong reference engine on average. A network that's "usually
roughly right" but noisy on the specific close, tactically-sharp
decisions a depth-2 search actually has to make can plausibly cause
worse move choices than a less globally-accurate but more consistent,
monotonic-in-material heuristic — especially at shallow depth, where
there's little search to correct an early evaluation mistake.

**`use_neural_eval` stays off by default — now with real, converged,
statistically meaningful evidence behind that default.**

## V0.6.2 concludes here as a genuine, documented negative result

Consistent with this project's own established practice (V0.5.2's
opening-book and V0.5.3's endgame-heuristic null results) of
documenting negative findings as plainly as positive ones — not a
failure of the checkpoint, real information about where this specific
technique's current ceiling sits.

**Not recommended**: more of the same tweak pattern (yet more data,
capacity, or features) — three attempts have each shown the same small
return, diminishing further each time.

**A more promising alternative for the same 94,872 labeled positions**:
rather than training a black-box network from scratch, use the same
(FEN, Pikafish score) pairs to *calibrate `evaluation.py`'s own
hand-guessed constants* (`MATERIAL_VALUES`, mobility/pawn-structure/
piece-coordination weights, etc.) directly via regression against real
Pikafish scores. Fully interpretable, no `eval_fn` indirection needed
at all — the tuned constants would just replace the current
hand-guessed ones directly in `evaluation.py`. A fundamentally
different, likely more sample-efficient use of the same hard-won data.
Not attempted yet.

**Separately, still open**: `V0.6.1`'s `MCTSEngine` has never been
benchmarked for real strength (only shown to build a real material
advantage vs. `RandomEngine`, never compared against `SearchEngine` at
any depth) — a reasonable alternative next direction.

## What was verified this checkpoint

```
pytest -q   (full suite, unchanged code)
184 passed in 146.89s
```
Retrained network verified directly: weight magnitude sane (2.87),
input dimension correct (1268), held-out correlation/RMSE recomputed
independently. 20-game comparison result recomputed directly from
`data/selfplay.jsonl`, matching the user's reported numbers exactly.

## What changed

- `data/neural_eval.npz`: fully converged retrain (epoch 228 best
  checkpoint, early-stopped at 268).
- `data/selfplay.jsonl`: +20 real comparison games.
- `docs/v0.6.2.md`: final addendum with the converged result and
  V0.6.2's conclusion.
- `docs/roadmap.md`: hand-off updated, V0.6 header reflects V0.6.2's
  conclusion.

## Exact next step

Two independent options, neither blocking the other:

**(a) Calibrate the existing heuristic** using the same labeled data —
a new, different task (regression against `evaluation.py`'s own
constants, not training a new network). Not yet scoped in detail.

**(b) Benchmark `MCTSEngine`'s real strength** — still an open thread
from V0.6.1:
```bash
python tools/compare_engines.py --a-engine mcts ...  # not yet supported --
# tools/compare_engines.py only builds SearchEngine instances currently;
# adding an --a-engine/--b-engine selector is the natural small next step.
```

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

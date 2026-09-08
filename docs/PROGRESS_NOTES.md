# AlphaZetaChess Progress Snapshot — V0.6.3 calibration analysis (real findings, not yet applied)

Snapshot date: 2026-09-06

## What happened this checkpoint

Rather than a fourth iteration of V0.6.2's "more data/capacity/
features" pattern (three attempts, each showing the same small,
exhausted return, concluding with a real -269 Elo loss to the
heuristic), used the same 94,872 real labeled positions completely
differently: fit new values for `evaluate()`'s own hand-guessed
constants directly via linear regression against real Pikafish scores,
instead of training another black-box network.

**`engine/evaluation.py` gained `evaluate_components()`**: decomposes
a position into raw regression features (material counts per piece
type, PST/king-safety balances, and the existing `mobility_balance`/
`pawn_structure_balance`/`piece_coordination_balance`/`endgame_balance`
functions) — recombining these with the CURRENT hand-guessed constants
reproduces `evaluate()`'s own output exactly, tested directly as the
central correctness gate (a decomposition that doesn't sum back to the
same total isn't faithful, whatever else it computes).

**`tools/calibrate_evaluation.py`**: loads labels, computes components
for every position, fits an OLS regression (closed-form, no gradient
descent needed for 13 linear features) against real Pikafish scores,
reports fitted vs. current constants side by side, and compares
held-out RMSE/correlation against both the fitted model and the
current constants on the same split.

**Real, coherent finding, run against the actual 94,872-position
corpus**: normalized to Pawn=1, Rook/Cannon/Horse appear substantially
undervalued in the current hand-guessed material scale:

| Piece | Current ratio | Fitted ratio |
|---|---|---|
| Rook | 9.00 | 15.89 |
| Cannon | 4.50 | 7.80 |
| Horse | 4.00 | 7.25 |
| Elephant | 2.00 | 2.10 |
| Advisor | 2.00 | 1.68 |
| Pawn | 1.00 | 1.00 |

Elephant/Advisor/Pawn already look about right (within ~5-16%); Rook/
Cannon/Horse are low by a consistent ~1.7-1.9x factor — a coherent
pattern, not three unrelated numbers, and plausible on its own merits
(these pieces' value comes disproportionately from mobility/attacking
potential, which fixed material counts don't naturally capture).

Also found: a real **+40cp tempo-bias intercept** not currently
modeled anywhere in `evaluate()`; PST/king-safety calibrated to ~8-10x
their current implicit weight (suggestively too small, though this
doesn't reflect real-world impact since these ARE on by default —
worth more investigation); pawn-structure/piece-coordination
calibrated near zero (flagged with explicit caution — could mean
"doesn't matter" or "low variance in this data," not distinguished
yet, so NOT concluding these V0.4.4/V0.4.5 heuristics are useless).

**Honestly reported**: the overall linear model is LESS accurate at
predicting Pikafish's score than V0.6.2's neural network (1055cp RMSE
/ 0.511 correlation vs. 760cp / 0.786) — expected (linear features
have less expressive power than even a small MLP) and not the point:
the goal is better constants for the existing, fast, interpretable
heuristic, not a more accurate predictor in isolation.

## What was verified this checkpoint

```
pytest -q   (full suite)
191 passed in 170.33s
```
7 new tests, most importantly the recombination-matches-evaluate()
correctness gate (checked on the starting position, an asymmetric
position, and with every optional term enabled). Calibration tool run
against the real corpus, results verified by direct inspection of the
printed coefficients and RMSE/correlation numbers.

## What changed

- `src/alphazetacchess/engine/evaluation.py`: new
  `evaluate_components()` function.
- `tools/calibrate_evaluation.py` (new): OLS calibration CLI.
- `tests/test_evaluation_components_v063.py` (new, 7 tests).
- `docs/v0.6.3.md` (new): full findings writeup.
- `docs/roadmap.md`: hand-off updated.

**Nothing was applied back into `evaluate()`'s actual constants this
checkpoint** — this produced and validated the analysis, not a tested
improvement.

## Exact next step

**Test the material-value finding specifically** (most confident,
coherent, easiest to isolate without touching PST/king-safety/mobility
scaling at the same time): update `MATERIAL_VALUES` (or add an
opt-in alternate set) with the fitted Rook/Cannon/Horse values, keep
Elephant/Advisor/Pawn as-is, and run a real `tools/compare_engines.py`
comparison against the current constants. Not yet implemented — needs
a way to override `MATERIAL_VALUES` per-engine-instance first (e.g. a
constructor parameter), since it's currently a module-level constant.

**Before trusting the pawn-structure/piece-coordination near-zero
findings**: check each feature's actual variance/prevalence across the
real corpus — a near-zero regression coefficient on a rarely-nonzero
feature means something different than on a feature that varies a lot
but doesn't predict well.

**Separately, still open**: V0.6.1's `MCTSEngine` has never been
benchmarked for real strength against `SearchEngine` at any depth.

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

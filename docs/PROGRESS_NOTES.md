# AlphaZetaChess Progress Snapshot — calibrated material comparison: inconclusive at n=20

Snapshot date: 2026-09-06

## What happened this checkpoint

User ran the real, uninterrupted 20-game comparison the previous
checkpoint called for: `--a-use-calibrated-material --a-depth 2
--b-depth 2 --games 20`.

**Result**: 4 calibrated-values wins, 5 default-values wins, 11 draws
(55% draw rate). Score rate 47.5%, Elo -17. Verified directly from
`data/selfplay.jsonl`, matching the user's reported numbers exactly.

**-17 Elo is not a meaningful finding at this sample size — it's
statistical noise, not evidence of near-parity.** Computed the
approximate 95% confidence interval on the score rate: roughly
**[26%, 69%]** — wide enough to be consistent with anything from a
real, substantial disadvantage to a real, substantial advantage for
the calibrated values. Explicitly distinguished this from V0.6.2's
neural-evaluator result (a real, converged -269 Elo at the *same*
n=20 sample size, which WAS large enough to be confidently
distinguished from noise) — not every "small negative Elo number" this
project reports means the same thing, and conflating them would be a
real mistake.

**What this checkpoint can and cannot conclude**: cannot conclude the
calibrated values measurably help OR measurably hurt at depth=2 — the
sample doesn't support either claim. Can conclude the mechanism itself
works correctly end to end (confirmed by the unit tests and this real
run completing without error). Two genuinely separate things kept
straight: the *regression finding* itself (Rook/Cannon/Horse
undervalued ~1.7-1.9x vs. Pawn, fit against 94,872 real Pikafish
scores) is real and well-supported; whether *acting on it* measurably
improves actual game outcomes is a separate, still-open empirical
question this run couldn't resolve — would need very roughly 100+
games to narrow the confidence interval enough to detect an effect in
a plausible range.

`CALIBRATED_MATERIAL_VALUES` and `--use-calibrated-material` remain
available, tested, and off by default.

## What was verified this checkpoint

```
pytest -q   (full suite, unchanged code)
195 passed in 164.51s
```
Result recomputed directly from `data/selfplay.jsonl` (win/loss/draw
tally and Elo formula), plus an approximate confidence-interval
calculation to properly characterize what the sample size can and
cannot support — not just reporting the point estimate.

## What changed

- `docs/v0.6.3.md`: second addendum with the real comparison result
  and the inconclusive-vs-neutral distinction.
- `docs/roadmap.md`: hand-off updated.
- (`data/selfplay.jsonl` already had the 20 games from the user's push
  — no local change needed beyond documentation.)

## Exact next step

**A much larger comparison run (very roughly 100+ games)** is the
natural way to actually settle whether the calibrated material values
help, whenever that scale of compute is available:
```bash
python tools/compare_engines.py --a-use-calibrated-material --a-depth 2 --b-depth 2 --games 100 --output data/selfplay.jsonl
```
Not attempted further this session (would need many hours at this
project's current per-game speed).

**Still separately open**:
- Investigate the near-zero pawn-structure/piece-coordination
  regression coefficients' actual variance/prevalence in the real
  corpus before drawing any conclusion about them.
- V0.6.1's `MCTSEngine` still has no real strength benchmark against
  `SearchEngine` at any depth.

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

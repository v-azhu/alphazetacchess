# AlphaZetaChess Progress Snapshot — calibrated material values wired for real testing

Snapshot date: 2026-09-06

## What happened this checkpoint

Acted on V0.6.3's own "Next step" — rather than leave the material-
value finding (Rook/Cannon/Horse appear undervalued ~1.7-1.9x relative
to Pawn in the current hand-guessed scale) as analysis-only, made it
directly testable in real search.

**`evaluate()` gained an optional `material_values` parameter**: `None`
(default) reproduces every prior version's exact behavior; an override
dict replaces the material lookup table entirely. Threaded through
`_piece_score` (the only internal caller of `MATERIAL_VALUES`) and a
new `SearchEngine` constructor parameter of the same name, flowing
into `_evaluate()` alongside the existing `eval_fn` override — the
same pattern V0.6.2's pluggable evaluator already established.

**New `CALIBRATED_MATERIAL_VALUES` constant**: Rook 900→1500, Cannon
450→750, Horse 400→700 (rounded from the exact fitted 1525.7/749.0/
696.1 to the nearest 50 — a plausible, testable constant, not claiming
that precision matters). Elephant/Advisor/Pawn deliberately left
unchanged, isolating the single most confident finding from the more
speculative PST/king-safety-scaling and near-zero pawn-structure/
piece-coordination findings the same analysis produced.

**`tools/compare_engines.py`** gained `--a/b-use-calibrated-material`,
mirroring the existing `--use-opening-book`/`--use-neural-eval`
pattern exactly.

**4 new tests**: default preserves existing behavior; the calibrated
table changes a position's score by exactly the expected Rook-value
delta (600 = 1500-900) with everything else held constant;
`SearchEngine` correctly threads the override through; and
`CALIBRATED_MATERIAL_VALUES` itself is verified to leave Elephant/
Advisor/Pawn/King untouched.

## What was verified this checkpoint

```
pytest -q   (full suite)
195 passed in 166.03s
```
A real comparison game was started (`--a-use-calibrated-material
--a-depth 2 --b-depth 2`) but didn't complete within this sandbox's
per-command time budget — the same constraint every prior real
comparison in this project has run into (real depth-2 games take 1-3+
minutes here). The mechanism itself is confirmed correct via the
printed config line (`use_calibrated_material: True` for side A,
`False` for side B) and the unit tests above; the actual strength
verdict needs a real, uninterrupted run.

## What changed

- `src/alphazetacchess/engine/evaluation.py`: `material_values`
  parameter on `evaluate()`, new `CALIBRATED_MATERIAL_VALUES` constant.
- `src/alphazetacchess/engine/search.py`: `material_values` constructor
  parameter on `SearchEngine`, threaded through `_evaluate()`.
- `tools/compare_engines.py`: `--a/b-use-calibrated-material`.
- `tests/test_evaluation_components_v063.py`: 4 new tests.
- `docs/v0.6.3.md`: addendum with the wiring details.
- `docs/roadmap.md`: hand-off updated.

## Exact next step

**On the user's machine — the actual strength test**, the real answer
to whether the calibrated material values help:
```bash
python tools/compare_engines.py --a-use-calibrated-material --a-depth 2 --b-depth 2 --games 20 --output data/selfplay.jsonl
```

**Also still open**:
- Investigate the near-zero pawn-structure/piece-coordination
  regression coefficients' actual variance/prevalence across the real
  corpus before drawing any conclusion about them (flagged with
  caution in `docs/v0.6.3.md`, not yet checked).
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

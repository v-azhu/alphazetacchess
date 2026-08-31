# V0.4.3-beta-2 Progress Snapshot

## Current verified baseline

- Restored V0.4.2 `search.py`.
- Existing search regression: 24 tests passed.
- V0.4.3-beta-1 Mobility/Evaluation focused tests: 6 passed.

## Correction to previous package

The previous beta-2 patcher incorrectly assumed identical indentation for
all four `evaluate()` call sites and reported:

`Expected 4 ... found 2`

It aborted before writing `search.py`, so the user's SearchEngine remained
unchanged. The new patcher matches the actual source line containing
`use_king_safety=self.use_king_safety` and therefore handles the indentation
used by the current SearchEngine.

## Next action

Run:

```powershell
python tools/apply_v043_beta2.py
```

Then:

```powershell
pytest tests/test_search_v043_beta2.py
pytest tests/test_mobility_v043.py tests/test_evaluation_v043.py
```

If both pass, proceed to V0.4.3-beta-3: Mobility OFF/ON depth-2 benchmark.

Do not claim a playing-strength improvement from Mobility until the A/B
benchmark and human testing support it.

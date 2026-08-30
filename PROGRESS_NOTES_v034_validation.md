# AlphaZetaChess Progress Snapshot — V0.3.4 validation

Snapshot date: 2026-08-30

## Repository state verified

Latest main commit:
`f4b330ccfcf010ef4742e0dd4724cec3c47b4bf2` — `v0.3.3 submitted`

The repository roadmap now identifies V0.3.4 as CURRENT. The code in
`src/alphazetacchess/engine/search.py` already contains Quiescence Search,
check extensions, `quiescence_max_ply`, and the `use_quiescence` switch.

## Completed before this checkpoint

- V0.1 COMPLETE
- V0.2 COMPLETE
- V0.3.1 COMPLETE
- V0.3.2 COMPLETE
- V0.3.3 COMPLETE
- V0.3.4 core implementation present

The repository's existing `PROGRESS_NOTES.md` reports 32 tests green at the
time the V0.3.4 implementation was snapshotted.

## This checkpoint adds

- `tests/test_search_v034.py`
- `docs/v0.3.4.md`

These are validation artifacts; they do not change engine semantics.

## Not yet complete

- Run the new V0.3.4 tests locally.
- If they pass, run the V0.3.4 A/B benchmark.
- Record benchmark evidence in `docs/v0.3.4.md` and `docs/roadmap.md`.
- Only then mark V0.3.4 COMPLETE.
- Update `main.py` version comment if still stale.

## Exact next command

```powershell
pytest
```

If green:

```powershell
python tools/benchmark_v034.py --depths 2
```

Do not start depth=3 until the depth=2 benchmark is reviewed.

## Handoff rule

At the next interruption, update this file with:
1. latest commit;
2. pytest count/result;
3. benchmark result;
4. remaining checklist;
5. one exact next command.

This keeps the project resumable without relying on conversation memory.

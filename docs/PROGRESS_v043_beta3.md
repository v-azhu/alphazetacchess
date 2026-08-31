# V0.4.3-beta-3 Progress Snapshot

## Baseline

GitHub baseline: commit `82a9f610` (V0.4.3-beta-2).

Verified before this step:
- `tests/test_search_v043_beta2.py`: 3 passed
- `tests/test_mobility_v043.py tests/test_evaluation_v043.py`: 6 passed
- Mobility is optional and disabled by default.

## Beta-3 goal

Perform a controlled A/B comparison of the same SearchEngine with:
- Mobility OFF
- Mobility ON

Keep all other search settings identical:
- iterative deepening: ON
- transposition table: ON
- PVS: ON
- quiescence: ON
- same depth
- same position

Measure:
- score
- best move (coordinate signature, not Move object identity)
- nodes
- NPS
- wall time

## First experiment

Run:

```powershell
python tools/benchmark_v043_beta3.py --depths 2
```

Optional weight experiment:

```powershell
python tools/benchmark_v043_beta3.py --depths 2 --mobility-weight 2
```

Do not interpret a changed move as an automatic strength improvement.
The benchmark is an A/B diagnostic, not a playing-strength proof.

## Next checkpoint

After the depth-2 benchmark:
1. record output;
2. decide whether depth-3 is affordable/useful;
3. if results are promising, run real human-vs-engine UI games;
4. only then tune mobility weights or move to the next evaluation feature.

## Git workflow

The benchmark file could not be committed through the current GitHub integration (403).
The included file is ready for local copy/commit/push.

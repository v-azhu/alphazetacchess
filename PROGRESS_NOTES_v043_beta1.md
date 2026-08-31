# V0.4.3-beta-1 Progress Snapshot

## Baseline

- GitHub baseline: V0.4.3-alpha
- Owner-reported full suite: 64 passed
- Web UI: basic human-vs-engine functionality already manually verified

## This checkpoint

Added:

- optional `use_mobility` to `evaluate()`
- configurable `mobility_weight`
- regression test that mobility-off equals the V0.4.2 evaluation
- mobility-on evaluation tests
- V0.4.3 documentation

Intentionally not changed:

- SearchEngine
- Web UI
- mobility implementation itself

## Next

1. Run the focused V0.4.3 evaluation tests.
2. If green, add `use_mobility` to SearchEngine.
3. Run A/B benchmark with mobility OFF/ON.
4. Then run the complete regression suite.

## Safety rule

Do not tune mobility weights from one position. Use benchmark positions and,
once the engine is playable, human/self-play data.

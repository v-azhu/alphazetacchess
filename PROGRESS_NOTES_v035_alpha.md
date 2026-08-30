# V0.3.5-alpha Progress Snapshot

## Current state

V0.3.1–V0.3.4 search foundations are complete:
- Iterative deepening
- Move ordering
- Zobrist hashing / transposition table
- Negamax / PVS
- Quiescence search

V0.3.4 has been benchmarked with Quiescence OFF vs ON. The benchmark showed
that QS can materially change both node count and result, so `same_move=False`
is not treated as an automatic failure.

## V0.3.5-alpha

### Added
- `tests/test_search_v035.py`
- `docs/v0.3.5.md`

### Regression gates
1. Search returns a legal move.
2. Fresh identical searches are deterministic.
3. PVS preserves the minimax score.
4. TT preserves the minimax score.
5. QS-enabled search returns a legal move.

### Not yet done
- Explicit tactical regression positions.
- V0.3.5 performance optimization.
- V0.4 evaluation work.

## Next resume point

Run the full test suite. If green, add the first tactical regression positions.
Do not modify `search.py` until a regression test demonstrates a concrete
correctness problem.

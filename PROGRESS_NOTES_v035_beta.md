# V0.3.5-beta Progress Snapshot

## Investigation result

The first tactical test failed because the test position itself was illegal:
the two generals were directly facing each other.

This was caught by the engine's `Rule.is_in_check()` / flying-general logic.
No search.py change is justified by this failure.

## Fix

Added a blocker on the central file to make the free-rook position legal.

## Current status

- V0.3.5-alpha: 42/42 passed.
- V0.3.5-beta initial run: 44/45 passed.
- Failure classified as invalid regression position.
- Core search code: unchanged.

## Resume point

Run `pytest` after replacing `tests/test_search_v035_beta.py`.
Expected suite size remains 45 tests.

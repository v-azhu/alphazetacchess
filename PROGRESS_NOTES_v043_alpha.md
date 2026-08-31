# V0.4.3-alpha Progress Snapshot

## Baseline

Repository baseline is V0.4.2 + Web UI. The UI has already been manually
verified by the project owner for basic human-vs-engine play.

## V0.4.3-alpha

### Added

- `engine/mobility.py`
- `tests/test_mobility_v043.py`
- `docs/v0.4.3.md`

### Intentionally NOT changed

- `engine/evaluation.py`
- `engine/search.py`
- Web UI

This checkpoint validates the new evaluation signal before it enters the hot
search path.

## Current status

WAITING FOR LOCAL PYTEST

Expected suite growth:
- previous total: 45
- new tests: +3
- expected: 48 tests

## Resume point

After green tests, benchmark the mobility signal, then wire it into the
evaluation function behind `use_mobility=True`.

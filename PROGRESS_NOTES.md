# AlphaZetaChess Progress Snapshot — V0.4.2 code+tests written, awaiting local validation

Snapshot date: 2026-08-31

## Repository state verified

Latest main commit at start of this checkpoint: `f492bd6` — "v035 beta submitted"
(V0.4.1 and V0.4.2 work in this checkpoint are uncommitted local changes on top
of that commit; see the delivered zip for exact files to apply.)

## Workflow change starting this checkpoint

To avoid burning session time/usage on long-running test and benchmark
commands (which caused interruptions in the previous two checkpoints), the
current approach is: write code + tests + docs in-session, do only fast/cheap
sanity checks here (compiling, running a single new test file in isolation --
these take well under a second), and hand off the **full pytest suite** and
any **playing-strength self-play benchmark** to be run locally. Report the
results back and this file / the relevant docs/v0.4.x.md get updated to
COMPLETE from there.

## What this checkpoint changed

- `src/alphazetacchess/engine/evaluation.py`: added King Safety, two additive
  terms -- Guard Integrity (bonus per surviving Advisor/Elephant) and
  Open-File Exposure (penalty for a clear file from the king to an enemy
  Rook/Cannon). `evaluate()` gained `use_king_safety=True` (default),
  independent of `use_piece_square_tables`.
- `src/alphazetacchess/engine/search.py`: `SearchEngine` gained a matching
  `use_king_safety` constructor flag, threaded through all four internal
  `evaluate()` call sites.
- `tests/test_evaluation_v042.py` (new, 10 tests): guard integrity exact
  deltas, open-file exposure for Rook and Cannon, blocked-file cancellation,
  relative (not absolute) scoring, PST/king-safety independence, and a
  SearchEngine wiring check.
- `docs/v0.4.2.md` (new): full design rationale, scope boundaries (rank
  exposure and attacker-proximity scoring deliberately deferred), and an
  interesting interaction with Quiescence Search discovered while writing the
  wiring test (see below).
- `docs/roadmap.md`: V0.4.2 status set to "IMPLEMENTATION COMPLETE, LOCAL
  VALIDATION PENDING" (deliberately NOT marked COMPLETE yet -- the full suite
  has not been run this session), hand-off diagram updated with the exact
  local command to run next.

## Verified in-session (fast checks only)

```
pytest tests/test_evaluation_v042.py tests/test_evaluation_v041.py -q
16 passed in 0.03s

python -m py_compile src/alphazetacchess/engine/evaluation.py src/alphazetacchess/engine/search.py
compile OK
```

**The full pytest suite (all ~61 tests together) has NOT been run this
session.** Please run it locally and report the pass/fail count (and full
output if anything fails).

## A worthwhile bug-shaped finding while writing the tests

The first draft of the SearchEngine wiring test used an enemy Rook on a fully
open file to the king. That position turned out to also be an *actual,
immediate check* (nothing blocks a Rook's line of sight), so
`SearchEngine._quiescence` correctly took its "in check, must resolve, no
stand-pat" branch (V0.3.4 behavior) instead of returning a plain evaluation --
which made it diverge from a direct `evaluate()` call. Not a bug in the
production code; the fixture was testing the wrong thing. Fixed by switching
to a Cannon (a real King Safety threat that isn't itself an immediate check,
since a Cannon needs a screen to capture). Full writeup in `docs/v0.4.2.md`.

## Not yet started

- V0.4.2's playing-strength self-play benchmark (deliberately not attempted
  this session, unlike V0.4.1 -- see docs/v0.4.2.md for a suggested command
  to try locally if desired; V0.4.1 already found this tends to be
  inconclusive at practical depths, so it's optional, not blocking).
- V0.4.3 (rank-based king exposure, pawn structure, or piece coordination --
  not yet decided, no code exists).

## Exact next step

1. **You, locally:** run `pytest -q` (full suite) and report the result.
2. If green: I'll mark `docs/v0.4.2.md` and the `docs/roadmap.md` V0.4.2 entry
   COMPLETE, and we move on to V0.4.3.
3. If anything fails: paste the failure output and I'll fix it -- given the
   isolated test file already passes and the wiring test specifically
   exercises the SearchEngine integration, a full-suite-only failure would
   most likely be an interaction with some other existing test's fixture
   (e.g. a position that happens to combine with King Safety in an
   unexpected way), which the existing "kings on the same file" and
   "accidental check" pitfall notes in `docs/v0.4.2.md` and `docs/roadmap.md`
   V0.3.3-3.5 are good places to check first.

## Handoff rule (unchanged, repeated for visibility)

At the next interruption, update this file with:
1. latest commit;
2. pytest count/result;
3. benchmark result (or honest non-result);
4. remaining checklist;
5. one exact next command.

This keeps the project resumable without relying on conversation memory.

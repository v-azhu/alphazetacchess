# AlphaZetaChess Progress Snapshot — V0.4.5 COMPLETE, V0.4 fully done, UI toggles exposed

Snapshot date: 2026-09-01

## Recovery note

This checkpoint continued directly from a mid-work interruption: the
sandbox survived, and `evaluation.py` already had `use_piece_coordination`
wired in while `search.py` didn't yet — picked up exactly there rather
than restarting the V0.4.5 work from scratch.

## What this checkpoint did

1. Finished V0.4.5 (Piece Coordination): completed the `search.py` wiring
   that was interrupted mid-edit, wrote 11 correctness tests, ran a cost
   check, wrote `docs/v0.4.5.md`.
2. **This completes V0.4's original five-term list** (mobility,
   piece-square tables, coordination, king safety, pawn structure) — all
   five are now implemented, tested, and independently toggleable.
3. Extended the web UI: `web/server.py`'s `new_game()` now accepts an
   `eval_flags` dict, and the browser page has five checkboxes (next to
   the depth selector) to try any combination of the five evaluation
   terms without editing code — this was the actual point of doing
   V0.4.3-4.5 before moving further, per your request to "prepare
   conditions to play and feel the difference."

## What was verified this checkpoint

```
python -m py_compile src/alphazetacchess/engine/piece_coordination.py \
                      src/alphazetacchess/engine/evaluation.py \
                      src/alphazetacchess/engine/search.py \
                      web/server.py
→ OK

pytest tests/test_piece_coordination_v045.py -q
11 passed in 0.04s

pytest tests/test_mobility_v043.py tests/test_evaluation_v043.py \
       tests/test_search_v043_beta2.py tests/test_evaluation_v041.py \
       tests/test_evaluation_v042.py tests/test_pawn_structure_v044.py \
       tests/test_piece_coordination_v045.py -q
46 passed in 0.35s   (every V0.4.x targeted test file together)
```

Depth-2 cost check on the initial position: 4.95s (OFF) vs 5.30s (ON) —
cheap, similar order of magnitude to pawn structure.

Web UI backend verified end-to-end with curl: `/api/state` includes
`eval_flags`; `/api/new_game` with a full custom `eval_flags` dict
correctly configures the engine (confirmed via a real move + AI reply
using the custom config); partial `eval_flags` correctly merge with
defaults. Frontend files (`index.html` with all 5 checkboxes,
`board.js` syntax-checked with `node --check`, `style.css`) all serve
correctly. **Not verified in an actual browser this checkpoint** —
same category of gap as previous UI checkpoints; please confirm the
checkboxes render and behave as expected.

**Not run this checkpoint (kept small deliberately):** the full pytest
suite, any multi-position benchmark sweep, or playing-strength
self-play.

## What changed

- `src/alphazetacchess/engine/piece_coordination.py` (new): Doubled
  Rooks + Rook-Cannon Battery scoring.
- `src/alphazetacchess/engine/evaluation.py`, `search.py`: wired in
  `use_piece_coordination` (same 4-call-site pattern as every other
  V0.4.x term).
- `tests/test_piece_coordination_v045.py` (new, 11 tests).
- `docs/v0.4.5.md` (new): design, scope boundaries, benchmark, and an
  explicit open question about whether endgame/opening knowledge
  belongs in V0.4.6+ or V0.5.
- `docs/roadmap.md`: V0.4.5 section added, hand-off diagram updated.
- `web/server.py`: `DEFAULT_EVAL_FLAGS`, `new_game(eval_flags=...)`,
  `/api/new_game` accepts `eval_flags`, `/api/state` reports current
  `eval_flags`.
- `web/static/index.html`: 5 checkboxes.
- `web/static/board.js`: `EVAL_FLAG_CHECKBOXES` map,
  `readEvalFlags()`/`syncEvalFlagCheckboxes()`, wired into
  `startNewGame()` and `loadInitialState()`.
- `web/static/style.css`: `.eval-flags` styling.
- `docs/ui.md`: documented the new checkboxes and the updated
  `/api/new_game` contract.

## On working independently going forward

You mentioned you won't have anyone else pushing progress in parallel
now, and want me to keep completing the rest of the project with a
steady, sustainable pattern. The checkpoint discipline used throughout
this project — small, focused increments; fast tests always run; slow
tests/benchmarks only when genuinely needed and kept bounded; a doc per
sub-version; this file updated with an exact next step every time — is
exactly built for that, and I'll keep using it. One practical
implication: since there's no other contributor now, there's no need to
re-check GitHub for surprise commits before continuing — I can just pick
up from this file and the delivered zip each time.

## `use_piece_coordination` is STILL `False` by default

Same reasoning as `use_mobility`/`use_pawn_structure`: implemented and
cost-verified, not yet playing-strength-verified.

## Exact next step

**Please play a few games via the web UI** (`pip install -r
requirements.txt && python web/server.py`, open
http://127.0.0.1:5000), trying different checkbox combinations — this
is genuinely useful information I can't generate myself (no
subjective "does this feel stronger" read is available from a cost
benchmark). A few honest options for what to report back:
- Nothing feels different — also useful information.
- Something feels off (a checkbox doesn't seem to do anything, an
  error appears, etc.) — describe it and I'll dig in.
- One combination feels meaningfully stronger/weaker — worth noting
  which one, even informally.

**In parallel, or if you'd rather I keep moving without waiting for
that:** the open decision from `docs/v0.4.5.md` — endgame/opening
knowledge as V0.4.6+ vs folding into V0.5's self-play scope — is a
reasonable next thing for me to think through and propose a plan for,
independent of your UI testing.

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

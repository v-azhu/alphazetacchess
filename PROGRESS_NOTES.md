# AlphaZetaChess Progress Snapshot — UI two-step move fix, awaiting browser re-check

Snapshot date: 2026-08-31

## Status

1. **V0.4.2 (King Safety): COMPLETE.** Confirmed by your local `pytest -q`
   run (all green). Done, no action needed.
2. **Web UI: two bugs found via your real-browser testing, both now fixed
   in-session.** First bug (clicking did nothing) confirmed fixed by you.
   Second bug (Red's piece didn't visually move until Black had also
   moved) just fixed, needs your re-check.

## Bug 2, in one line

`POST /api/move` used to apply the human's move AND the AI's reply before
responding at all, so the frontend's one-and-only `render()` call for the
whole exchange only happened after both moves were already done —
nothing to show on screen until the AI (which can take several seconds)
had finished thinking.

## What was fixed

Split move application into two endpoints:
- `POST /api/move` — human's move only, responds immediately.
- `POST /api/ai_move` (new) — AI's reply, separate follow-up call.

`board.js`'s `playMove()` now: calls `/api/move`, renders immediately
(Red's piece updates on screen right away), shows a "🤔 AI 正在思考..."
status message, calls `/api/ai_move`, then renders again once that
resolves.

Verified in-session (server + curl, not a real browser):
- `node --check web/static/board.js` — syntax OK.
- Full two-step exchange via curl: `/api/move` returns immediately with
  only the human's move (no `ai_move` key at all now), current_player
  correctly flips to BLACK; a repeat call to `/api/move` at that point
  correctly fails with "not your turn"; `/api/ai_move` correctly computes
  and applies the AI's reply, current_player flips back to RED; a repeat
  call to `/api/ai_move` at that point correctly fails with "not AI's
  turn".

**Not verified this session:** actually watching it happen in a browser
(Red's piece should now visibly move the instant you click a destination,
before the AI's reply comes in a few seconds later).

## Exact next step

1. **You, locally:** refresh the browser (or restart `python
   web/server.py` if needed) and make a move. Confirm Red's piece moves
   immediately, then a "🤔 AI 正在思考..." message appears, then Black's
   piece moves once the AI replies.
2. If that's all correct: go through the rest of `docs/ui.md`'s "What to
   check locally" list if you haven't already (legal-move highlighting,
   check/checkmate messages, New Game + depth dropdown), then this can be
   marked COMPLETE and we move on to V0.4.3.
3. If anything's still off, describe what you see and I'll keep going —
   `docs/ui.md` has a running "Bug history" section tracking each issue
   found and fixed so far, in case it's useful context.

## Handoff rule (unchanged, repeated for visibility)

At the next interruption, update this file with:
1. latest commit;
2. pytest count/result;
3. UI/benchmark result (or honest non-result);
4. remaining checklist;
5. one exact next command.

This keeps the project resumable without relying on conversation memory.

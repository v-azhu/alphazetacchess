# AlphaZetaChess Web UI

## Status

**Click bug found and fixed (2026-08-31); re-verification pending.**

Real-browser testing found that the board rendered correctly, but Red
(the human side) could not move at all — neither click-based selection
nor drag worked. Root cause: piece circles were drawn on top of the
invisible click-target circles that hold all interaction logic, and
were missing `pointer-events: none`, so they silently swallowed every
click aimed at a piece (i.e. nearly every click, since selecting your
own piece is step one). Fixed in `web/static/style.css` — see "Bug
history" below for the full writeup. **Please re-check in a real
browser that clicking now works**; this was a CSS-only fix, verified
by inspection and by confirming the file serves correctly, not by
actually clicking in a browser.

Drag-to-move was never implemented in this first version — click
origin, then click destination, is the only supported interaction.
This is a documented scope limitation (see "Known limitations" below),
not a bug.

Backend API verified in-session (server boots, all four endpoints tested
directly with curl: initial state, legal-move lookup, playing a full move
including the AI's reply, illegal-move rejection, and starting a new game
at a custom AI depth).

## What this is

A local, single-user web UI so you can actually play against the engine
by clicking on a real Xiangqi board (river, palace diagonals, proper piece
characters) instead of typing coordinate pairs into the CLI. It's a thin
presentation layer: `web/server.py` calls exactly the same `Board` / `Rule`
/ `SearchEngine` classes the CLI (`src/main.py`) and the test suite use —
there is no second game implementation to keep in sync.

## Run it

```bash
pip install -r requirements.txt   # installs Flask
python web/server.py
```

Then open **http://127.0.0.1:5000** in a browser. Click one of your (red)
pieces to select it — legal destination squares light up — then click a
destination to move. The AI (black) replies automatically; its move,
evaluation score, search depth, node count, and think time appear in the
move log on the right. "新局 New Game" starts over, and the depth dropdown
(1/2/3) sets the AI's search depth for the next new game (matching
`AI_SEARCH_DEPTH` in the CLI, with the same depth/time tradeoffs documented
in `docs/v0.3.4.md` and `src/main.py`).

**Evaluation term checkboxes (added alongside V0.4.5):** five checkboxes —
Piece-Square Tables and King Safety (both on by default, matching
`SearchEngine`'s own defaults), Mobility, Pawn Structure, and Piece
Coordination (all off by default) — let you try any combination of the
V0.4.1-4.5 evaluation terms without editing any code. Checked state is read
when you click "New Game" (changes apply to the *next* game, not
mid-game), and the checkboxes sync back to whatever the server reports on
page load, so refreshing always shows the truth. This is the actual reason
V0.4.3-4.5 were built before moving on: there's now something concrete to
sit down and feel the difference of, e.g. try `use_mobility` +
`use_pawn_structure` + `use_piece_coordination` all on at once versus the
default, or turn everything off to compare against the plain V0.2 material
baseline.

Stop the server with Ctrl+C.

## Architecture

```
web/
├── server.py           # Flask app: serves the page + a small JSON API
└── static/
    ├── index.html       # page shell
    ├── style.css         # board + panel styling
    └── board.js          # SVG board rendering, click handling, fetch calls
```

`server.py` holds a single global `Board` + `SearchEngine` pair (this is a
local, single-browser-tab tool, not a multi-session server — see its module
docstring). Five endpoints:

- `GET /api/state` — current board + status, for the initial page load.
- `POST /api/new_game {ai_depth, eval_flags}` — reset the game, optionally
  at a different AI search depth and/or evaluation term configuration
  (`eval_flags` is a dict of the five `use_*` booleans; any flag omitted
  keeps its default — see `DEFAULT_EVAL_FLAGS` in `web/server.py`).
- `POST /api/legal_moves {x, y}` — legal destinations for the piece at
  `(x, y)`, if it belongs to the side to move. Used to highlight squares
  after a click.
- `POST /api/move {from: {x,y}, to: {x,y}}` — validates and applies ONLY
  the human's move via `Rule.generate_legal_moves` (rejects anything not
  in that list with HTTP 400) and returns immediately. Rejects with HTTP
  400 if called when it isn't the human's turn.
- `POST /api/ai_move` — computes and applies the AI's reply
  (`SearchEngine.choose_move`), separately from the human's move. Rejects
  with HTTP 400 if called when it isn't the AI's turn, or the game is
  already over.

These are deliberately two separate calls rather than one combined
request/response, specifically so the frontend can render the human's
move immediately and show a "thinking" indicator while awaiting the AI's
(potentially several-second) reply, rather than the whole board silently
freezing until both moves are done — see "Bug history" below for the
issue this fixed.

The frontend (`board.js`) renders the board as SVG, purely from what
`/api/state`-shaped JSON gives it — no game logic duplicated in
JavaScript. Board coordinates match `Board`'s own convention exactly
((0,0) = Red's own left corner), with `y=0` drawn at the bottom of the
SVG so Red sits at the bottom of the screen, matching how a human playing
Red would expect to see the board.

Piece characters use the traditional Red/Black-distinguishing set
(帥仕相俥傌炮兵 for Red, 將士象車馬砲卒 for Black) rather than a single
shared set, matching standard printed Xiangqi sets.

## What to check locally

Since this wasn't verified in a real browser this session, please check:

1. The board renders correctly (grid, river text, palace diagonals, all
   32 pieces in their correct starting squares).
2. Clicking a Red piece highlights its legal destinations (compare a few
   against what you'd expect — e.g. the opening Cannon and Horse moves).
3. Clicking a legal destination moves the piece, and the AI replies
   automatically a few seconds later (depth 2 default; see the timing
   table in `docs/v0.3.4.md` / `src/main.py` for what's normal).
4. Clicking an illegal destination, an opponent piece, or empty space with
   nothing selected doesn't do anything unexpected (should just
   select/deselect sensibly).
5. Check/checkmate/stalemate messages appear correctly when they occur.
6. "New Game" and the depth dropdown work.

Please report back anything that looks wrong (a screenshot description is
plenty if you can't paste one) and it'll get fixed.

## Known limitations / deliberately out of scope for this first version

- Human is always Red, AI always Black (matching the CLI's current
  behavior) — no side-switching yet.
- No move undo.
- No captured-pieces tray / material count display.
- No sound/animation — pieces snap to their new position on re-render
  rather than sliding.
- Single game state per server process (restart the server, or use "New
  Game", rather than expecting multiple simultaneous games).

None of these affect correctness of play — they're presentation
conveniences that can be added later if useful.

## Bug history

**2026-08-31 — Red couldn't move at all (click-to-select silently did
nothing).** Reported after real-browser testing: the board rendered
fine, but clicking a piece never selected it, for either origin or
destination clicks.

Root cause: `board.js` intentionally routes ALL board interaction
through a layer of invisible circles, one per intersection (see
`buildStaticGrid`'s comment — "empty squares and occupied squares
behave the same way"). Piece visuals (`.piece-group`, containing the
colored circle + Chinese character) are drawn in a separate layer on
top of that, purely for display. `style.css` gave the piece text
`pointer-events: none` so it wouldn't block clicks, but the piece
*circle* itself had no such rule — being opaque and sitting on top of
the invisible click-target circle underneath, in SVG's normal
top-element-wins hit-testing, every click aimed at a piece landed on
the (listener-less) piece circle instead of passing through to the
click-target circle beneath it. Since selecting your own piece is
necessarily the first click in any move, this broke the human side
completely while leaving the board's *appearance* entirely correct —
which is why it wasn't caught by the in-session backend-only checks
(curl doesn't render CSS or click anything).

Fix: added `pointer-events: none` to `.piece-group` as well, so clicks
pass straight through pieces to the click-target layer underneath,
matching the design that was already documented in `board.js` but not
fully implemented in the CSS.

Lesson for next time: an API-level check (curl, pytest) cannot catch a
CSS/hit-testing bug like this one — anything touching actual pointer
interaction in the browser needs an actual browser click, which is
exactly the kind of check this project's current workflow defers to
local testing rather than attempting to simulate in the sandbox.

**2026-08-31 — Red's piece didn't move until Black had also moved.**
Reported after the click fix above was confirmed working: clicking now
selected pieces and applied moves correctly, but Red's own piece
visually stayed in its old position on screen until the AI's reply had
also finished computing (several seconds later), at which point BOTH
moves appeared to happen at once.

Root cause: the original `POST /api/move` endpoint applied the human's
move AND the AI's reply move on the server before responding at all,
and the frontend only called `render()` once, after that entire
request resolved. So there was nothing correct to render until the AI
had already finished thinking.

Fix: split move application into two endpoints. `POST /api/move` now
applies only the human's move and returns immediately; the frontend
renders right away, so Red's piece updates on screen instantly. A new
`POST /api/ai_move` triggers and applies the AI's reply as a separate
request; the frontend shows a "🤔 AI 正在思考..." status message while
waiting for it, then renders again once it resolves. Each endpoint
guards against being called out of turn (`not your turn` /
`not AI's turn`), verified directly with curl: a same-request replay
of either endpoint while it isn't that side's turn correctly returns
HTTP 400.

Last updated: 2026-08-31

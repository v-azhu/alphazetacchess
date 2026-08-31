# AlphaZetaChess Web UI

## Status

**Implementation complete; local (real-browser) validation pending.**

Backend API verified in-session (server boots, all four endpoints tested
directly with curl: initial state, legal-move lookup, playing a full move
including the AI's reply, illegal-move rejection, and starting a new game
at a custom AI depth — see the checkpoint notes for exact output). The
actual board rendering and click-to-move interaction have **not** been
verified in a real browser this session, per the current workflow: local,
possibly-slow, or hard-to-automate verification is done locally and
reported back rather than attempted in the sandbox that writes the code.

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
docstring). Four endpoints:

- `GET /api/state` — current board + status, for the initial page load.
- `POST /api/new_game {ai_depth}` — reset the game, optionally at a
  different AI search depth.
- `POST /api/legal_moves {x, y}` — legal destinations for the piece at
  `(x, y)`, if it belongs to the side to move. Used to highlight squares
  after a click.
- `POST /api/move {from: {x,y}, to: {x,y}}` — validates and applies the
  human's move via `Rule.generate_legal_moves` (rejects anything not in
  that list with HTTP 400), then — if the game isn't over — calls
  `SearchEngine.choose_move` for the AI's reply and applies that too.
  Returns the resulting full state plus both moves' details in one
  response, so the frontend never has to poll or guess whether the AI has
  replied yet.

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

Last updated: 2026-08-31

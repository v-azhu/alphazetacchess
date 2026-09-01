"""
AlphaZetaChess Web UI server.

A local Flask app that serves a click-to-move Xiangqi board in the
browser, backed by the exact same Core (Board/Rule) and Engine
(SearchEngine) layers used by the CLI (src/main.py) and the test
suite -- this is a thin presentation layer, not a second game
implementation.

Run locally:

    pip install flask
    python web/server.py

Then open http://127.0.0.1:5000 in a browser.

Not intended for anything other than local, single-user play/testing:
game state is a single global (fine for one browser tab talking to one
local server), and Flask's built-in dev server is used directly.
"""

import os
import sys
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from flask import Flask, jsonify, request, send_from_directory

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine


app = Flask(__name__, static_folder="static", static_url_path="")

HUMAN_COLOR = Color.RED
AI_COLOR = Color.BLACK
DEFAULT_AI_DEPTH = 2

# V0.4.1-4.5 evaluation terms, each independently toggleable on
# SearchEngine. Keys here are exactly the SearchEngine constructor
# kwarg names, which keeps new_game()'s **eval_flags pass-through
# trivial -- adding a future V0.4.x term only means adding one line
# here (and one checkbox in web/static/index.html).
DEFAULT_EVAL_FLAGS = {
    "use_piece_square_tables": True,   # V0.4.1
    "use_king_safety": True,           # V0.4.2
    "use_mobility": False,             # V0.4.3 (beta-4: pseudo-legal, cheap)
    "use_pawn_structure": False,       # V0.4.4
    "use_piece_coordination": False,   # V0.4.5
}

# Single global game (see module docstring: this is a local,
# single-user tool, not a multi-session server).
game = {
    "board": None,
    "ai_engine": None,
    "ai_depth": DEFAULT_AI_DEPTH,
    "eval_flags": dict(DEFAULT_EVAL_FLAGS),
}


def new_game(ai_depth=None, eval_flags=None):
    if ai_depth is not None:
        game["ai_depth"] = ai_depth

    if eval_flags is not None:
        # Only accept known flags, and coerce to bool -- request JSON
        # is untrusted input, and SearchEngine's constructor has no
        # reason to see anything but real booleans for these kwargs.
        game["eval_flags"] = {
            key: bool(eval_flags[key])
            for key in DEFAULT_EVAL_FLAGS
            if key in eval_flags
        }
        # Fill in defaults for any flag the request didn't mention.
        for key, default in DEFAULT_EVAL_FLAGS.items():
            game["eval_flags"].setdefault(key, default)

    game["board"] = Board()
    game["ai_engine"] = SearchEngine(depth=game["ai_depth"], **game["eval_flags"])


new_game()


def serialize_board(board):
    cells = []
    for y in range(Board.HEIGHT):
        row = []
        for x in range(Board.WIDTH):
            piece = board.get(x, y)
            if piece is None:
                row.append(None)
            else:
                row.append({"type": piece.type.name, "color": piece.color.name})
        cells.append(row)
    return cells


def move_payload(move):
    if move is None:
        return None
    return {
        "from": {"x": move.from_pos[0], "y": move.from_pos[1]},
        "to": {"x": move.to_pos[0], "y": move.to_pos[1]},
        "captured": move.captured_piece.type.name if move.captured_piece else None,
    }


def state_payload(extra=None):
    board = game["board"]
    current = board.current_player

    is_checkmate = Rule.is_checkmate(board, current)
    is_stalemate = Rule.is_stalemate(board, current)
    game_over = is_checkmate or is_stalemate

    payload = {
        "board": serialize_board(board),
        "current_player": current.name,
        "human_color": HUMAN_COLOR.name,
        "ai_color": AI_COLOR.name,
        "ai_depth": game["ai_depth"],
        "eval_flags": game["eval_flags"],
        "in_check": Rule.is_in_check(board, current),
        "game_over": game_over,
        "is_checkmate": is_checkmate,
        "is_stalemate": is_stalemate,
        "winner": Board.opponent(current).name if game_over else None,
    }

    if extra:
        payload.update(extra)

    return payload


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/state")
def api_state():
    return jsonify(state_payload())


@app.route("/api/new_game", methods=["POST"])
def api_new_game():
    data = request.get_json(silent=True) or {}
    ai_depth = data.get("ai_depth")
    eval_flags = data.get("eval_flags")
    new_game(ai_depth=ai_depth, eval_flags=eval_flags)
    return jsonify(state_payload())


@app.route("/api/legal_moves", methods=["POST"])
def api_legal_moves():
    data = request.get_json(silent=True) or {}
    x, y = data.get("x"), data.get("y")
    board = game["board"]

    if x is None or y is None or not Board.in_bounds(x, y):
        return jsonify({"moves": []})

    piece = board.get(x, y)
    if piece is None or piece.color != board.current_player:
        return jsonify({"moves": []})

    legal_moves = Rule.generate_legal_moves(board, board.current_player)
    targets = [
        {"x": m.to_pos[0], "y": m.to_pos[1]}
        for m in legal_moves
        if m.from_pos == (x, y)
    ]
    return jsonify({"moves": targets})


@app.route("/api/move", methods=["POST"])
def api_move():
    """
    Applies ONLY the human's move and returns immediately -- the AI's
    reply is a separate call (POST /api/ai_move). Splitting these was
    a deliberate fix: the previous single-endpoint version applied
    both moves before responding at all, so the human's own piece
    never visually moved until the (multi-second) AI reply was also
    done computing. See docs/ui.md "Bug history".
    """
    data = request.get_json(silent=True) or {}
    board = game["board"]

    if board.current_player != HUMAN_COLOR:
        return jsonify({"error": "not your turn"}), 400

    try:
        from_pos = (data["from"]["x"], data["from"]["y"])
        to_pos = (data["to"]["x"], data["to"]["y"])
    except (KeyError, TypeError):
        return jsonify({"error": "malformed request"}), 400

    legal_moves = Rule.generate_legal_moves(board, HUMAN_COLOR)
    human_move = next(
        (m for m in legal_moves if m.from_pos == from_pos and m.to_pos == to_pos),
        None,
    )

    if human_move is None:
        return jsonify({"error": "illegal move"}), 400

    board.move(from_pos, to_pos)

    return jsonify(state_payload({"human_move": move_payload(human_move)}))


@app.route("/api/ai_move", methods=["POST"])
def api_ai_move():
    """
    Computes and applies the AI's move. Only valid when it is
    currently the AI's turn (i.e. right after a successful
    POST /api/move, unless the human's move already ended the game).
    """
    board = game["board"]

    if board.current_player != AI_COLOR:
        return jsonify({"error": "not AI's turn"}), 400

    if Rule.is_game_over(board, AI_COLOR):
        return jsonify({"error": "game is already over"}), 400

    engine = game["ai_engine"]
    started = time.time()
    result = engine.choose_move(board, AI_COLOR)
    elapsed = time.time() - started

    extra = {"ai_move": None, "ai_info": None}

    if result.best_move is not None:
        board.move(result.best_move.from_pos, result.best_move.to_pos)
        extra["ai_move"] = move_payload(result.best_move)
        extra["ai_info"] = {
            "score": result.score,
            "depth": result.depth,
            "nodes_evaluated": result.nodes_evaluated,
            "elapsed_seconds": round(elapsed, 2),
        }

    return jsonify(state_payload(extra))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

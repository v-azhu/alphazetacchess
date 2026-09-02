"""V0.5.1 self-play game recording.

Defines the JSON-lines game record format used by self-play data
collection, and helpers to play a fully move-by-move-recorded game and
to write/read records to/from disk.

Deliberately separate from tools/benchmark.py's `play_game` (which
only returns a winner and a move count, exactly enough for a win-rate
benchmark). Self-play needs the full move sequence recorded, since the
whole point is to later mine it for patterns -- see the downstream
consumers below.

Downstream consumers (planned, per docs/v0.5.1.md and docs/roadmap.md):
- V0.5.2: build a simple opening book from move-sequence win rates.
- V0.5.3: derive endgame-phase evaluation adjustments from recorded
  outcomes, conditioned on material/piece count.
- V0.5.4: automated strength comparison (Elo-style) between different
  SearchEngine configurations, extending tools/benchmark.py's
  RandomEngine-only matches to SearchEngine-vs-SearchEngine, now that
  win/loss/draw outcomes are being recorded anyway.
"""

import json
import time

from ..core.board import Board
from ..core.piece import Color
from ..core.rule import Rule


def play_recorded_game(
    engine_red, engine_black, max_moves, red_config=None, black_config=None, board=None
):
    """
    Play one game move by move, recording every move played and the
    final result. Returns a JSON-serializable dict (one game record).

    `red_config`/`black_config` are opaque, caller-supplied dicts
    describing how each engine was configured (e.g. search depth,
    which evaluation terms were on) -- stored alongside the moves so a
    later analysis pass can, for example, only look at games played
    with a specific evaluation configuration.

    `board` defaults to a fresh starting position; passing a
    pre-constructed `Board` (mainly useful for tests) plays from that
    position instead.
    """
    if board is None:
        board = Board()

    engines = {Color.RED: engine_red, Color.BLACK: engine_black}
    moves = []
    result = None

    while len(moves) < max_moves:
        current = board.current_player

        # In Xiangqi, having no legal move is always a loss (checkmate
        # and stalemate/困毙 are both losses -- see Rule for details).
        if Rule.is_game_over(board, current):
            result = "BLACK_WINS" if current == Color.RED else "RED_WINS"
            break

        chosen = engines[current].choose_move(board, current)
        move = chosen.best_move
        moves.append({
            "color": current.name,
            "from": list(move.from_pos),
            "to": list(move.to_pos),
        })
        board.move(move.from_pos, move.to_pos)
    else:
        result = "DRAW"  # move limit reached without the while loop's own break firing

    return {
        "red_config": red_config or {},
        "black_config": black_config or {},
        "result": result,
        "total_moves": len(moves),
        "moves": moves,
        "recorded_at": time.time(),
    }


def append_record(path, record):
    """Append one game record as a single line of JSON to `path`."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_records(path):
    """Load all game records from a JSON-lines file into a list."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

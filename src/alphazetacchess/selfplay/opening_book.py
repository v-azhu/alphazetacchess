"""V0.5.2 opening book, built from V0.5.1 self-play records.

Positions are keyed by (Zobrist hash, color to move) rather than by
move sequence, so transpositions (different move orders reaching the
same position) share statistics instead of being tracked separately --
Board.zobrist_hash already exists and is exactly the right key for
this (see core/zobrist.py).

For each position, we track win/draw/loss/games counts PER MOVE
actually played from there in recorded games. Move selection picks the
move with the best score (win=1, draw=0.5, loss=0, averaged over
games) among moves with at least `min_games` samples -- this is a
simple frequentist approach, deliberately not anything more
sophisticated (e.g. a proper confidence interval or UCB-style
exploration bonus), since with a small self-play corpus the extra
sophistication would just be noise on noise. Revisit once there is a
much larger corpus to work with.
"""

import json

from ..core.board import Board
from ..core.piece import Color


def _position_key(board, color):
    return f"{board.zobrist_hash}-{color.name}"


def _move_key(from_pos, to_pos):
    return f"{from_pos[0]},{from_pos[1]}-{to_pos[0]},{to_pos[1]}"


def _parse_move_key(move_key):
    from_part, to_part = move_key.split("-")
    fx, fy = (int(v) for v in from_part.split(","))
    tx, ty = (int(v) for v in to_part.split(","))
    return (fx, fy), (tx, ty)


def build_book_from_records(records, max_ply=20):
    """
    Replay every recorded game's move sequence and accumulate
    per-position, per-move win/draw/loss/games counts for the first
    `max_ply` half-moves of each game.

    Returns a JSON-serializable dict:
        {"<zobrist>-<COLOR>": {"<fx>,<fy>-<tx>,<ty>": {wins, draws, losses, games}}}
    """
    book = {}

    for record in records:
        board = Board()
        result = record["result"]  # "RED_WINS" | "BLACK_WINS" | "DRAW"

        for ply_index, move_entry in enumerate(record["moves"]):
            if ply_index >= max_ply:
                break

            color = Color[move_entry["color"]]
            from_pos = tuple(move_entry["from"])
            to_pos = tuple(move_entry["to"])

            position_key = _position_key(board, color)
            move_key = _move_key(from_pos, to_pos)

            stats = book.setdefault(position_key, {}).setdefault(
                move_key, {"wins": 0, "draws": 0, "losses": 0, "games": 0}
            )
            stats["games"] += 1
            if result == "DRAW":
                stats["draws"] += 1
            elif result == f"{color.name}_WINS":
                stats["wins"] += 1
            else:
                stats["losses"] += 1

            board.move(from_pos, to_pos)

    return book


def select_book_move(book, board, color, min_games=3):
    """
    Return (from_pos, to_pos) for the best-scoring book move at this
    position, or None if there's no book entry or nothing meets
    `min_games`.
    """
    entries = book.get(_position_key(board, color))
    if not entries:
        return None

    best_move_key = None
    best_score = None

    for move_key, stats in entries.items():
        if stats["games"] < min_games:
            continue
        score = (stats["wins"] + 0.5 * stats["draws"]) / stats["games"]
        if best_score is None or score > best_score:
            best_score = score
            best_move_key = move_key

    if best_move_key is None:
        return None

    return _parse_move_key(best_move_key)


def save_book(book, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(book, f, ensure_ascii=False, indent=2)


def load_book(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

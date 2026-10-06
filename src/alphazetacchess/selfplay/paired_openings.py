"""Select replayable, fixed opening positions from recorded games."""

import random

from ..core.board import Board
from ..core.fen import board_from_fen, board_to_fen
from ..core.move import Move
from ..core.piece import Color
from ..core.rule import Rule


def select_paired_openings(records, opening_count, opening_plies=10, seed=0):
    """Return distinct legal opening positions suitable for color-swapped pairs.

    Each source record is replayed from its recorded initial FEN or the standard
    starting position. Only positions with Red to move are eligible, which
    requires an even number of opening plies.
    """
    if opening_count < 1:
        raise ValueError("opening_count must be positive")
    if opening_plies < 2 or opening_plies % 2:
        raise ValueError("opening_plies must be a positive even number")

    candidates = {}
    for record in records:
        board = board_from_fen(record["initial_fen"]) if record.get("initial_fen") else Board()
        prefix = []
        for raw_move in record.get("moves", [])[:opening_plies]:
            if Rule.is_game_over(board, board.current_player):
                break
            move = Move(tuple(raw_move["from"]), tuple(raw_move["to"]))
            if not Rule.is_legal_move(board, move, board.current_player):
                raise ValueError(f"Illegal source opening move: {raw_move!r}")
            prefix.append(raw_move)
            board.move(move.from_pos, move.to_pos)

        if len(prefix) != opening_plies or board.current_player != Color.RED:
            continue

        fen = board_to_fen(board)
        position_key = " ".join(fen.split()[:2])
        candidates.setdefault(position_key, {
            "initial_fen": fen,
            "opening_prefix": prefix,
        })

    if len(candidates) < opening_count:
        raise ValueError(
            f"Need {opening_count} distinct legal openings, found {len(candidates)}"
        )

    selected = random.Random(seed).sample(list(candidates.values()), opening_count)
    for index, opening in enumerate(selected):
        opening["opening_index"] = index
    return selected

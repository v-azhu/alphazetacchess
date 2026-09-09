"""Perft utilities for validating Xiangqi legal move generation.

Perft counts the number of legal leaf positions reachable in exactly ``depth``
plies.  It is intentionally independent from the search engine so that move
generation and make/unmake correctness can be regression-tested directly.
"""

from ..core.board import Board
from ..core.rule import Rule


def perft(board: Board, depth: int, color=None) -> int:
    """Return the legal leaf-node count at exactly ``depth`` plies.

    Args:
        board: Position to search from. The board is restored to its original
            state before returning.
        depth: Number of plies to enumerate. ``0`` returns one leaf (the
            current position).
        color: Side to move. Defaults to ``board.current_player``.
    """
    if depth < 0:
        raise ValueError("depth must be non-negative")

    if color is None:
        color = board.current_player

    if depth == 0:
        return 1

    moves = Rule.generate_legal_moves(board, color)
    if depth == 1:
        return len(moves)

    total = 0
    for move in moves:
        board.move(move.from_pos, move.to_pos)
        total += perft(board, depth - 1, board.current_player)
        board.undo()

    return total


def perft_divide(board: Board, depth: int, color=None) -> dict:
    """Return per-root-move perft counts for debugging move generation."""
    if depth < 1:
        raise ValueError("depth must be at least 1")

    if color is None:
        color = board.current_player

    result = {}
    for move in Rule.generate_legal_moves(board, color):
        board.move(move.from_pos, move.to_pos)
        result[repr(move)] = perft(board, depth - 1, board.current_player)
        board.undo()

    return result

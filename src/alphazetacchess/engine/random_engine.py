import random

from ..core.rule import Rule
from .base import ChessEngine, SearchResult
from .evaluation import evaluate


class RandomEngine(ChessEngine):
    """
    Picks a uniformly random legal move.

    This is the v0.1 baseline opponent, and also the benchmark that
    the v0.2 SearchEngine is expected to reliably defeat (see
    docs/roadmap.md, V0.2 acceptance criteria and "Engine Benchmark").
    """

    def choose_move(self, board, color):
        legal_moves = Rule.generate_legal_moves(board, color)

        if not legal_moves:
            return SearchResult(None, evaluate(board, color), 0, 0)

        move = random.choice(legal_moves)
        return SearchResult(move, evaluate(board, color), 0, 0)

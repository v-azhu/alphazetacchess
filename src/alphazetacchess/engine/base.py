from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    """
    Uniform return value for every engine's choose_move(), so the game
    loop (or any future GUI / analysis tool) can display *why* an
    engine picked a move, regardless of which engine produced it.
    """
    best_move: Optional[object]
    score: float
    nodes_evaluated: int
    depth: int


class ChessEngine:
    """
    Common interface for all AlphaZetaChess engines
    (see docs/design/engine-design.md, section 3).

    Every engine implementation -- RandomEngine, SearchEngine (this
    version), and future MCTSEngine / NeuralEngine / HybridEngine --
    must be swappable without changing the Core layer or the game loop.
    """

    def choose_move(self, board, color):
        raise NotImplementedError

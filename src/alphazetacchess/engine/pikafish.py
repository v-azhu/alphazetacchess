"""Pikafish adapter implementing the project's ChessEngine interface."""

import time

from ..core.fen import board_to_fen
from ..core.game_record import GameRecord
from ..core.piece import Color
from ..core.rule import Rule
from ..neural.pikafish_client import PikafishClient, mate_score_to_cp
from .base import ChessEngine, SearchResult


class PikafishEngine(ChessEngine):
    """Use a UCI-compatible Pikafish process to choose legal Xiangqi moves."""

    def __init__(
        self, engine_path, network_path, search_depth=None, movetime_ms=200
    ):
        self.client = PikafishClient(
            engine_path,
            movetime_ms=movetime_ms,
            network_path=network_path,
            search_depth=search_depth,
        )
        self.depth = search_depth
        self.search_stats = []

    def choose_move(self, board, color):
        if color != board.current_player:
            raise ValueError("Requested color does not match the board's side to move")
        started = time.monotonic()
        result = self.client.evaluate_fen(board_to_fen(board))
        elapsed_ms = (time.monotonic() - started) * 1000
        notation = result["best_move"]
        if not notation or notation == "0000":
            raise RuntimeError("Pikafish returned no move for a non-terminal position")

        move = GameRecord.move_from_iccs(notation)
        if not Rule.is_legal_move(board, move, color):
            raise RuntimeError(f"Pikafish returned illegal move {notation!r}")

        score = result["score_cp"]
        if score is None and result["mate_in"] is not None:
            score = mate_score_to_cp(result["mate_in"])
        if score is None:
            raise RuntimeError("Pikafish returned a move without a centipawn or mate score")
        depth = result["depth"] or self.depth or 0
        self.search_stats.append({
            "side": color.name,
            "depth": depth,
            "elapsed_ms": round(elapsed_ms, 2),
        })
        return SearchResult(move, score, 0, depth)

    @property
    def engine_info(self):
        return tuple(
            line for line in self.client.uci_lines if line.startswith("id ")
        )

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

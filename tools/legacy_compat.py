"""Small source-compatibility helpers for retired comparison scripts.

Keep the old importable symbols here so each legacy CLI remains a thin wrapper
around the unified match runner.
"""
from __future__ import annotations

import threading
import time

from alphazetacchess.engine.search import SearchEngine


def _config_for_depth(records, depth):
    """Return a recorded config for depth, or the historical baseline defaults."""
    for record in records:
        for side in ("red_config", "black_config"):
            config = record.get(side, {})
            if config.get("depth") == depth:
                result = dict(config)
                result["depth"] = depth
                return result
    return {
        "engine": "search",
        "depth": depth,
        "use_mobility": False,
        "use_pawn_structure": False,
        "use_piece_coordination": False,
        "use_endgame_heuristics": False,
        "use_killer_moves": True,
        "use_mvv_lva": False,
        "use_opening_book": False,
        "use_neural_eval": False,
        "use_calibrated_material": False,
        "use_calibrated_weights": False,
    }


class TimedSearch:
    """Legacy timed SearchEngine adapter retained for source compatibility."""

    def __init__(self, movetime_ms, depth_cap, use_null_move, use_lmr=False):
        self.engine = SearchEngine(
            depth=depth_cap,
            use_null_move=use_null_move,
            use_late_move_reductions=use_lmr,
        )
        self.movetime_ms = movetime_ms
        self.stats = []

    def choose_move(self, board, color):
        stop_event = threading.Event()
        timer = threading.Timer(self.movetime_ms / 1000, stop_event.set)
        started = time.monotonic()
        timer.start()
        try:
            result = self.engine.choose_move(board, color, stop_event=stop_event)
            self.stats.append({
                "depth": result.depth,
                "nodes": result.nodes_evaluated,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
                "null_move_attempts": self.engine.null_move_attempts,
                "null_move_cutoffs": self.engine.null_move_cutoffs,
                "late_move_reductions": self.engine.late_move_reductions,
            })
            return result
        finally:
            timer.cancel()
            timer.join()

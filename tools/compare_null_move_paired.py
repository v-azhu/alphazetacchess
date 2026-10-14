"""Compatibility CLI for the V0.11.1 unified match runner.

The legacy TimedSearch helper remains importable for regression tests and
external callers. Importing this module never parses command-line arguments.
Run this file directly to invoke the unified match runner.
"""
from pathlib import Path
import runpy
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alphazetacchess.engine.search import SearchEngine


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


def main() -> None:
    runner = Path(__file__).with_name("match.py")
    sys.argv[0] = str(runner)
    runpy.run_path(str(runner), run_name="__main__")


if __name__ == "__main__":
    main()

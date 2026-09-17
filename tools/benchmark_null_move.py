"""Compare baseline search with conservative Null Move Pruning.

Run from the repository root, for example:
    python tools/benchmark_null_move.py --depth 4

The benchmark uses identical search settings except for Null Move Pruning.
It reports elapsed time, nodes, NPS, selected move, score, and null-move
cutoff diagnostics.
"""

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.search import SearchEngine


POSITIONS = (
    ("initial", None),
    (
        "capture_rich",
        "4k4/9/9/4p4/9/9/9/r8/p8/R3K4 w - - 0 1",
    ),
)


def move_signature(move):
    if move is None:
        return "-"
    return f"{move.from_pos}->{move.to_pos}"


def run_engine(label, engine, board):
    start = time.perf_counter()
    result = engine.choose_move(board, Color.RED)
    elapsed = time.perf_counter() - start
    nodes = result.nodes_evaluated
    nps = nodes / elapsed if elapsed > 0 else 0.0

    print(
        f"{label:10} time={elapsed:8.3f}s  nodes={nodes:9d}  "
        f"nps={nps:9.1f}  depth={result.depth:2d}  "
        f"score={result.score!s:>8}  move={move_signature(result.best_move)}"
    )
    print(
        f"{'Null stats':10} attempts={engine.null_move_attempts:7d}  "
        f"cutoffs={engine.null_move_cutoffs:7d}  "
        f"reduction={engine.null_move_reduction:2d}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--reduction", type=int, default=2)
    parser.add_argument("--min-pieces", type=int, default=7)
    args = parser.parse_args()

    for name, fen in POSITIONS:
        print(f"\n=== {name} ===")
        board = Board() if fen is None else board_from_fen(fen)

        baseline = SearchEngine(
            depth=args.depth,
            iterative_deepening=True,
            use_history=True,
            use_null_move=False,
        )
        null_engine = SearchEngine(
            depth=args.depth,
            iterative_deepening=True,
            use_history=True,
            use_null_move=True,
            null_move_reduction=args.reduction,
            null_move_min_pieces=args.min_pieces,
        )

        run_engine("baseline", baseline, board)
        run_engine("null-move", null_engine, board)


if __name__ == "__main__":
    main()

"""Compare baseline search with SEE-aware move ordering.

Run from the repository root, for example:
    python tools/benchmark_see.py --depth 4

The benchmark uses identical search settings except for SEE capture ordering.
It reports elapsed time, nodes, NPS, selected move, and SEE diagnostics.
"""

import argparse
import time

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.engine.search_see import SeeSearchEngine


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
    if isinstance(engine, SeeSearchEngine):
        print(
            f"{'SEE stats':10} calls={engine.see.calls:9d}  "
            f"exchange_nodes={engine.see.exchange_nodes:9d}  "
            f"max_exchange_depth={engine.see.max_depth_reached:2d}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--see-depth", type=int, default=12)
    args = parser.parse_args()

    for name, fen in POSITIONS:
        print(f"\n=== {name} ===")
        board = Board() if fen is None else board_from_fen(fen)

        baseline = SearchEngine(
            depth=args.depth,
            iterative_deepening=True,
            use_history=True,
        )
        see_engine = SeeSearchEngine(
            depth=args.depth,
            iterative_deepening=True,
            use_history=True,
            use_see=True,
            see_max_depth=args.see_depth,
        )

        run_engine("baseline", baseline, board)
        run_engine("SEE", see_engine, board)


if __name__ == "__main__":
    main()

"""Measure best-move stability as search depth increases.

Run from the repository root:
    python tools/benchmark_search_stability.py --depths 2 3 4
    python tools/benchmark_search_stability.py --depths 3 4 5 --null-move

This is diagnostic, not a strength rating. A deeper search may legitimately
change the best move; repeated changes and large score swings are the useful
signals for further investigation.
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
    ("initial", None, "ordinary starting position"),
    ("open_position", "rnbakabnr/9/1c5c1/p1p1p1p1p/9/4P4/P1P3P1P/1C5C1/9/RNBAKABNR w - - 0 1", "early central-pawn development"),
    ("tactical_exchange", "r3k4/9/1n2c4/p3p3p/9/9/P3P3P/1N2C4/9/R3K4 w - - 0 1", "rook/cannon/horse and pawn tactical material"),
)


def move_signature(move):
    return "-" if move is None else f"{move.from_pos}->{move.to_pos}"


def run_at_depth(board, depth, use_null_move):
    engine = SearchEngine(depth=depth, iterative_deepening=True, use_history=True, use_null_move=use_null_move)
    start = time.perf_counter()
    result = engine.choose_move(board, Color.RED)
    elapsed = time.perf_counter() - start
    nps = result.nodes_evaluated / elapsed if elapsed > 0 else 0.0
    return result, elapsed, nps, engine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depths", nargs="+", type=int, default=[2, 3, 4])
    parser.add_argument("--null-move", action="store_true", help="enable conservative Null Move Pruning")
    args = parser.parse_args()
    depths = sorted(set(args.depths))
    if any(depth < 1 for depth in depths):
        parser.error("all depths must be >= 1")

    print(f"depths={depths}  null_move={args.null_move}")
    for name, fen, description in POSITIONS:
        print(f"\n=== {name}: {description} ===")
        board = Board() if fen is None else board_from_fen(fen)
        previous_move = None
        previous_score = None
        for depth in depths:
            result, elapsed, nps, engine = run_at_depth(board, depth, args.null_move)
            move = move_signature(result.best_move)
            changed = previous_move is not None and move != previous_move
            delta = None if previous_score is None else result.score - previous_score
            delta_text = "-" if delta is None else f"{delta:+d}"
            print(
                f"depth={depth:2d}  time={elapsed:8.3f}s  nodes={result.nodes_evaluated:9d}  "
                f"nps={nps:9.1f}  score={result.score:8d}  move={move:>15}  "
                f"move_vs_prev={'changed' if changed else 'stable':7s}  score_delta={delta_text}"
            )
            if args.null_move:
                print(f"           null_attempts={engine.null_move_attempts:7d}  null_cutoffs={engine.null_move_cutoffs:7d}")
            previous_move = move
            previous_score = result.score


if __name__ == "__main__":
    main()

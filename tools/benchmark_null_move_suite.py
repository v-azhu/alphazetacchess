"""Regression-oriented A/B suite for conservative Null Move Pruning.

Run from the repository root, for example:
    python tools/benchmark_null_move_suite.py --depth 4

This suite intentionally mixes ordinary, tactical, check, and small-endgame
positions. It is not a strength test by itself; it is a quick way to detect
search-result changes introduced by Null Move Pruning while also showing how
much search work it actually removes.
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
    (
        "initial",
        None,
        "ordinary starting position",
    ),
    (
        "open_position",
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/4P4/P1P3P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        "early central-pawn development",
    ),
    (
        "tactical_exchange",
        "r3k4/9/1n2c4/p3p3p/9/9/P3P3P/1N2C4/9/R3K4 w - - 0 1",
        "rook/cannon/horse and pawn tactical material",
    ),
    (
        "small_endgame",
        "4k4/9/9/9/9/9/9/9/9/R3K4 w - - 0 1",
        "two-king-plus-rook endgame; Null Move must be guarded",
    ),
    (
        "in_check",
        "4k4/9/9/9/9/9/9/4r4/9/4K4 w - - 0 1",
        "side to move is in check; Null Move must be disabled",
    ),
)


def move_signature(move):
    if move is None:
        return "-"
    return f"{move.from_pos}->{move.to_pos}"


def run_engine(engine, board):
    start = time.perf_counter()
    result = engine.choose_move(board, Color.RED)
    elapsed = time.perf_counter() - start
    nodes = result.nodes_evaluated
    nps = nodes / elapsed if elapsed > 0 else 0.0
    return result, elapsed, nps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--reduction", type=int, default=2)
    parser.add_argument("--min-pieces", type=int, default=7)
    args = parser.parse_args()

    total_baseline_nodes = 0
    total_null_nodes = 0
    changed_results = 0

    for name, fen, description in POSITIONS:
        print(f"\n=== {name}: {description} ===")
        source = Board() if fen is None else board_from_fen(fen)

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

        baseline_result, baseline_time, baseline_nps = run_engine(baseline, source)
        null_result, null_time, null_nps = run_engine(null_engine, source)

        total_baseline_nodes += baseline_result.nodes_evaluated
        total_null_nodes += null_result.nodes_evaluated

        same_score = baseline_result.score == null_result.score
        same_move = move_signature(baseline_result.best_move) == move_signature(null_result.best_move)
        if not (same_score and same_move):
            changed_results += 1

        node_delta = 0.0
        if baseline_result.nodes_evaluated:
            node_delta = (1.0 - null_result.nodes_evaluated / baseline_result.nodes_evaluated) * 100.0

        print(
            f"baseline   time={baseline_time:8.3f}s  nodes={baseline_result.nodes_evaluated:9d}  "
            f"nps={baseline_nps:9.1f}  score={str(baseline_result.score):>8}  "
            f"move={move_signature(baseline_result.best_move)}"
        )
        print(
            f"null-move  time={null_time:8.3f}s  nodes={null_result.nodes_evaluated:9d}  "
            f"nps={null_nps:9.1f}  score={str(null_result.score):>8}  "
            f"move={move_signature(null_result.best_move)}"
        )
        print(
            f"Null stats attempts={null_engine.null_move_attempts:7d}  "
            f"cutoffs={null_engine.null_move_cutoffs:7d}  "
            f"node_reduction={node_delta:6.1f}%  "
            f"result={'same' if same_score and same_move else 'CHANGED'}"
        )

    total_reduction = 0.0
    if total_baseline_nodes:
        total_reduction = (1.0 - total_null_nodes / total_baseline_nodes) * 100.0

    print("\n=== summary ===")
    print(f"baseline total nodes={total_baseline_nodes}")
    print(f"null-move total nodes={total_null_nodes}")
    print(f"total node reduction={total_reduction:.1f}%")
    print(f"changed results={changed_results}/{len(POSITIONS)}")


if __name__ == "__main__":
    main()

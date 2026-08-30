"""Strict V0.3.4 A/B benchmark: Quiescence Search OFF vs ON."""

import argparse
import time
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.search import SearchEngine


def make_position(name):
    board = Board()
    if name == "initial":
        return board

    sequences = {
        "early_development": [
            ((1, 0), (2, 2)),
            ((1, 9), (2, 7)),
            ((7, 0), (6, 2)),
            ((7, 9), (6, 7)),
        ],
        "central_development": [
            ((1, 0), (2, 2)),
            ((1, 9), (2, 7)),
            ((2, 0), (4, 2)),
            ((2, 9), (4, 7)),
            ((4, 0), (4, 1)),
            ((4, 9), (4, 8)),
        ],
    }
    for from_pos, to_pos in sequences[name]:
        board.move(from_pos, to_pos)
    return board


def move_signature(move):
    if move is None:
        return None
    return move.from_pos, move.to_pos


def run_once(position_name, depth, use_quiescence):
    board = make_position(position_name)
    engine = SearchEngine(
        depth=depth,
        iterative_deepening=True,
        use_transposition_table=True,
        use_pvs=True,
        use_quiescence=use_quiescence,
    )

    started = time.perf_counter()
    result = engine.choose_move(board, Color.RED)
    elapsed = time.perf_counter() - started

    return {
        "time": elapsed,
        "nodes": result.nodes_evaluated,
        "nps": result.nodes_evaluated / elapsed if elapsed else 0.0,
        "score": result.score,
        "move": move_signature(result.best_move),
        "depth": result.depth,
    }


def compare(position_name, depth):
    off = run_once(position_name, depth, False)
    on = run_once(position_name, depth, True)

    same_score = off["score"] == on["score"]
    same_move = off["move"] == on["move"]
    node_delta = (on["nodes"] - off["nodes"]) / off["nodes"] * 100 if off["nodes"] else 0.0
    time_delta = (on["time"] - off["time"]) / off["time"] * 100 if off["time"] else 0.0

    print(
        f"[{position_name:>19}] depth={depth} | "
        f"QS OFF {off['time']:8.3f}s {off['nodes']:8d} nodes {off['nps']:8.0f} NPS | "
        f"QS ON {on['time']:8.3f}s {on['nodes']:8d} nodes {on['nps']:8.0f} NPS | "
        f"nodes {node_delta:+6.1f}% | time {time_delta:+6.1f}% | "
        f"same(score/move)={same_score}/{same_move}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depths", nargs="+", type=int, default=[2])
    parser.add_argument(
        "--positions",
        nargs="+",
        default=["initial", "early_development", "central_development"],
    )
    args = parser.parse_args()

    print("AlphaZetaChess V0.3.4 Search Benchmark")
    print("Iterative Deepening + PVS + TT: Quiescence OFF vs ON")
    print()

    for depth in args.depths:
        for position in args.positions:
            compare(position, depth)


if __name__ == "__main__":
    main()

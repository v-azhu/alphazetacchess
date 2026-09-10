"""
AlphaZetaChess V0.8.2 Killer Move micro-benchmark.

Compares the same SearchEngine configuration with Killer Moves disabled
and enabled on a fixed deterministic midgame position.

Primary correctness checks: best move and score equality.
Primary performance metric: node count. Time and NPS are secondary.

Usage:
    python tools/benchmark_killer_moves.py
    python tools/benchmark_killer_moves.py --depth 4 --runs 5
"""

import argparse
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.engine.search import SearchEngine


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    return board


def benchmark_position():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 3))
    board._place(Piece(PieceType.HORSE, Color.RED, 2, 2))
    board._place(Piece(PieceType.CANNON, Color.BLACK, 4, 6))
    board._place(Piece(PieceType.HORSE, Color.BLACK, 7, 7))
    board._place(Piece(PieceType.PAWN, Color.RED, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 5))
    return board


def run_once(depth, use_killer_moves):
    board = benchmark_position()
    engine = SearchEngine(depth=depth, use_killer_moves=use_killer_moves)

    started = time.perf_counter()
    result = engine.choose_move(board, Color.RED)
    elapsed = time.perf_counter() - started

    if result.best_move is None:
        raise RuntimeError("Search returned no best move")

    return {
        "score": result.score,
        "best_move": (result.best_move.from_pos, result.best_move.to_pos),
        "nodes": engine.nodes_evaluated,
        "elapsed": elapsed,
        "nps": engine.nodes_evaluated / elapsed if elapsed > 0 else float("inf"),
        "depth": result.depth,
    }


def format_move(move):
    return f"{move[0]}->{move[1]}"


def summarize(runs):
    return {
        "score": runs[0]["score"],
        "best_move": runs[0]["best_move"],
        "depth": runs[0]["depth"],
        "nodes_median": statistics.median(r["nodes"] for r in runs),
        "time_median": statistics.median(r["elapsed"] for r in runs),
        "nps_median": statistics.median(r["nps"] for r in runs),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    if args.depth < 1:
        parser.error("--depth must be >= 1")
    if args.runs < 1:
        parser.error("--runs must be >= 1")

    print("AlphaZetaChess V0.8.2 Killer Move Benchmark")
    print("  Position : fixed V0.8.2 small midgame")
    print(f"  Depth    : {args.depth}")
    print(f"  Runs     : {args.runs}")
    print()

    results = {}
    for use_killer_moves, label in ((False, "Killer OFF"), (True, "Killer ON")):
        print(f"{label}:")
        runs = []
        for i in range(args.runs):
            run = run_once(args.depth, use_killer_moves)
            runs.append(run)
            print(
                f"  run {i + 1:>2}/{args.runs}: "
                f"score={run['score']:>8.1f}  "
                f"best={format_move(run['best_move'])}  "
                f"nodes={run['nodes']:>8}  "
                f"time={run['elapsed']:.4f}s  "
                f"NPS={run['nps']:.0f}"
            )
        results[label] = summarize(runs)
        print()

    off = results["Killer OFF"]
    on = results["Killer ON"]

    same_score = off["score"] == on["score"]
    same_move = off["best_move"] == on["best_move"]

    node_delta = off["nodes_median"] - on["nodes_median"]
    node_reduction = node_delta / off["nodes_median"] if off["nodes_median"] else 0.0
    time_delta = off["time_median"] - on["time_median"]
    time_change = time_delta / off["time_median"] if off["time_median"] else 0.0
    nps_change = on["nps_median"] / off["nps_median"] - 1.0 if off["nps_median"] else 0.0

    print("Summary (median of measured runs):")
    print(f"  Killer OFF: nodes={off['nodes_median']:.0f}, time={off['time_median']:.4f}s, NPS={off['nps_median']:.0f}")
    print(f"  Killer ON : nodes={on['nodes_median']:.0f}, time={on['time_median']:.4f}s, NPS={on['nps_median']:.0f}")
    print()
    print("Correctness:")
    print(f"  Same score     : {'PASS' if same_score else 'FAIL'}")
    print(f"  Same best move : {'PASS' if same_move else 'FAIL'}")
    print()
    print("Performance:")
    print(f"  Node reduction : {node_reduction:+.2%} ({node_delta:+.0f} nodes)")
    print(f"  Time change    : {time_change:+.2%} ({time_delta:+.4f}s)")
    print(f"  NPS change     : {nps_change:+.2%}")

    if not same_score or not same_move:
        raise SystemExit(
            "ERROR: Killer ON changed the search result. "
            "Do not treat this benchmark as a successful optimization."
        )


if __name__ == "__main__":
    main()

"""
AlphaZetaChess V0.3.1 search benchmark.

Compares the V0.2 fixed-depth Alpha-Beta baseline with the V0.3.1
iterative-deepening + root-move-ordering search.

Examples:
    python tools/benchmark_search.py
    python tools/benchmark_search.py --depths 2 3
    python tools/benchmark_search.py --depths 2 3 --repeat 2
"""

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"),
)

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.search import SearchEngine


@dataclass
class BenchmarkResult:
    position: str
    mode: str
    max_depth: int
    repeat: int
    elapsed_seconds: float
    nodes: int
    nps: float
    score: float
    best_move: str
    completed_depth: int


def move_signature(move):
    if move is None:
        return None
    return (move.from_pos, move.to_pos)


def move_text(move):
    signature = move_signature(move)
    return "-" if signature is None else f"{signature[0]}->{signature[1]}"


def make_position(name):
    """
    Return deterministic benchmark positions.

    The move sequences are deliberately simple and are validated through
    the normal Rule/Board path by the engine when searched.
    """
    board = Board()

    sequences = {
        "initial": [],
        "early_development": [
            ((1, 0), (2, 2)),  # red horse
            ((1, 9), (2, 7)),  # black horse
            ((1, 2), (1, 4)),  # red cannon
            ((1, 7), (1, 5)),  # black cannon
        ],
        "central_development": [
            ((1, 0), (2, 2)),
            ((1, 9), (2, 7)),
            ((7, 0), (6, 2)),
            ((7, 9), (6, 7)),
            ((1, 2), (1, 4)),
            ((7, 7), (7, 5)),
        ],
    }

    for from_pos, to_pos in sequences[name]:
        board.move(from_pos, to_pos)

    return board


def run_once(position_name, mode, depth):
    board = make_position(position_name)

    engine = SearchEngine(
        depth=depth,
        iterative_deepening=(mode == "iterative"),
    )

    started = time.perf_counter()
    result = engine.choose_move(board, board.current_player)
    elapsed = time.perf_counter() - started

    nodes = result.nodes_evaluated
    nps = nodes / elapsed if elapsed > 0 else float("inf")

    return BenchmarkResult(
        position=position_name,
        mode=mode,
        max_depth=depth,
        repeat=1,
        elapsed_seconds=elapsed,
        nodes=nodes,
        nps=nps,
        score=result.score,
        best_move=move_text(result.best_move),
        completed_depth=result.depth,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--depths",
        type=int,
        nargs="+",
        default=[2, 3],
        help="search depths to benchmark",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="number of repetitions per case",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="optional JSON output path",
    )
    args = parser.parse_args()

    positions = [
        "initial",
        "early_development",
        "central_development",
    ]

    all_results = []

    print("AlphaZetaChess V0.3.1 Search Benchmark")
    print("Fixed Alpha-Beta vs Iterative Deepening + Move Ordering")
    print()

    for depth in args.depths:
        for position in positions:
            baseline = None
            optimized = None

            for mode in ("fixed", "iterative"):
                samples = []

                for _ in range(args.repeat):
                    sample = run_once(position, mode, depth)
                    samples.append(sample)

                # Use the arithmetic mean for timing/node reporting.
                sample = samples[-1]
                sample.repeat = args.repeat
                sample.elapsed_seconds = sum(
                    x.elapsed_seconds for x in samples
                ) / args.repeat
                sample.nodes = round(
                    sum(x.nodes for x in samples) / args.repeat
                )
                sample.nps = (
                    sample.nodes / sample.elapsed_seconds
                    if sample.elapsed_seconds > 0
                    else float("inf")
                )

                all_results.append(sample)

                if mode == "fixed":
                    baseline = sample
                else:
                    optimized = sample

            same_score = baseline.score == optimized.score
            same_move = baseline.best_move == optimized.best_move

            print(
                f"[{position:>18}] depth={depth} | "
                f"fixed {baseline.elapsed_seconds:8.3f}s "
                f"{baseline.nodes:>9} nodes "
                f"{baseline.nps:>10.0f} NPS | "
                f"ID {optimized.elapsed_seconds:8.3f}s "
                f"{optimized.nodes:>9} nodes "
                f"{optimized.nps:>10.0f} NPS | "
                f"same(score/move)={same_score}/{same_move}"
            )

    print()
    print("Notes:")
    print("- Iterative nodes include all completed depths (1..N).")
    print("- Compare both time and nodes; fewer nodes does not necessarily mean less wall time.")
    print("- A mismatch in score or best move is a correctness regression, not a performance result.")

    if args.output:
        payload = [asdict(result) for result in all_results]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"\nJSON report written to: {args.output}")


if __name__ == "__main__":
    main()

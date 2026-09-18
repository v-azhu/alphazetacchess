"""Root-candidate diagnostic for evaluation vs search horizon.

Run from the repository root:
    python tools/benchmark_root_candidates.py --positions initial --depths 2 3 4
    python tools/benchmark_root_candidates.py --positions tactical_exchange --depths 3 4
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
for path in (SRC, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine
from test_tactical_positions import TACTICAL_POSITIONS


POSITIONS = {
    "initial": (None, Color.RED),
    "open_position": (
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/4P4/P1P3P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        Color.RED,
    ),
    "tactical_exchange": (
        "r3k4/9/1n2c4/p3p3p/9/9/P3P3P/1N2C4/9/R3K4 w - - 0 1",
        Color.RED,
    ),
    "mate_in_one": (TACTICAL_POSITIONS["mate_in_one"]["fen"], Color.RED),
    "free_capture": (TACTICAL_POSITIONS["free_capture"]["fen"], Color.RED),
    "exchange_trap": (TACTICAL_POSITIONS["exchange_trap"]["fen"], Color.RED),
}


def move_key(move):
    return None if move is None else (move.from_pos, move.to_pos)


def move_text(move):
    return "None" if move is None else f"{move.from_pos}->{move.to_pos}"


def static_score(engine, board, color, move):
    board.move(move.from_pos, move.to_pos)
    try:
        return -engine._evaluate(board, board.opponent(color))
    finally:
        board.undo()


def search_root_candidates(board, color, depth, top_static):
    engine = SearchEngine(
        depth=depth,
        use_transposition_table=True,
        use_pvs=True,
        use_quiescence=True,
        use_null_move=False,
        use_history=True,
    )
    legal_moves = Rule.generate_legal_moves(board, color)
    candidates = [(static_score(engine, board, color, move), move) for move in legal_moves]
    candidates.sort(key=lambda item: item[0], reverse=True)

    selected = candidates[:top_static]

    baseline = SearchEngine(
        depth=depth,
        use_transposition_table=True,
        use_pvs=True,
        use_quiescence=True,
        use_null_move=False,
        use_history=True,
    )
    baseline_result = baseline.choose_move(board, color)
    baseline_key = move_key(baseline_result.best_move)
    if baseline_key is not None and all(move_key(move) != baseline_key for _, move in selected):
        for item in candidates:
            if move_key(item[1]) == baseline_key:
                selected.append(item)
                break

    results = []
    started_total = time.perf_counter()
    for static, move in selected:
        board.move(move.from_pos, move.to_pos)
        try:
            opponent = board.opponent(color)
            started = time.perf_counter()
            score = -engine._negamax(
                board,
                depth - 1,
                float("-inf"),
                float("inf"),
                opponent,
                depth,
                use_pruning=True,
            )
            elapsed = time.perf_counter() - started
        finally:
            board.undo()
        results.append({
            "move": move_key(move),
            "static": static,
            "score": score,
            "delta": score - static,
            "time": elapsed,
        })

    results.sort(key=lambda item: item["score"], reverse=True)
    return results, baseline_result, time.perf_counter() - started_total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--positions", nargs="+", choices=sorted(POSITIONS), default=["initial"])
    parser.add_argument("--depths", nargs="+", type=int, default=[2, 3, 4])
    parser.add_argument("--top-static", type=int, default=8)
    args = parser.parse_args()

    if args.top_static < 1:
        parser.error("--top-static must be >= 1")
    if any(depth < 1 for depth in args.depths):
        parser.error("all depths must be >= 1")

    for name in args.positions:
        fen, color = POSITIONS[name]
        print(f"\n=== {name} ===")
        for depth in sorted(set(args.depths)):
            board = Board() if fen is None else board_from_fen(fen)
            results, baseline, elapsed = search_root_candidates(
                board, color, depth, args.top_static
            )
            print(
                f"d{depth}: engine_best={move_text(baseline.best_move)} "
                f"score={baseline.score} nodes={baseline.nodes_evaluated} "
                f"diagnostic_time={elapsed:.3f}s"
            )
            print("  rank  move                    static  search  delta")
            for index, item in enumerate(results, 1):
                move = item["move"]
                print(
                    "  {:>4}  {:<23s} {:>7} {:>7} {:+7}".format(
                        index,
                        f"{move[0]}->{move[1]}",
                        item["static"],
                        item["score"],
                        item["delta"],
                    )
                )
            print(
                "  note: candidates are selected by static evaluation; "
                "engine_best is always included."
            )


if __name__ == "__main__":
    main()

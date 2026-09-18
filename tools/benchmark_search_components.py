"""A/B diagnostic for TT and PVS effects on search results.

Run from the repository root:
    python tools/benchmark_search_components.py --depths 2 3 4
    python tools/benchmark_search_components.py --depths 3 4 5
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
from alphazetacchess.engine.search import SearchEngine
from test_tactical_positions import TACTICAL_POSITIONS


POSITIONS = (
    ("initial", None, Color.RED),
    ("open_position", "rnbakabnr/9/1c5c1/p1p1p1p1p/9/4P4/P1P3P1P/1C5C1/9/RNBAKABNR w - - 0 1", Color.RED),
    ("tactical_exchange", "r3k4/9/1n2c4/p3p3p/9/9/P3P3P/1N2C4/9/R3K4 w - - 0 1", Color.RED),
    ("mate_in_one", TACTICAL_POSITIONS["mate_in_one"]["fen"], Color.RED),
    ("free_capture", TACTICAL_POSITIONS["free_capture"]["fen"], Color.RED),
    ("exchange_trap", TACTICAL_POSITIONS["exchange_trap"]["fen"], Color.RED),
)


def move_key(move):
    return None if move is None else (move.from_pos, move.to_pos)


def run_case(board, color, depth, use_tt, use_pvs):
    engine = SearchEngine(
        depth=depth,
        use_transposition_table=use_tt,
        use_pvs=use_pvs,
        use_quiescence=True,
        use_null_move=False,
        use_history=True,
    )
    before_hash = board.zobrist_hash
    before_player = board.current_player
    started = time.perf_counter()
    result = engine.choose_move(board, color)
    elapsed = time.perf_counter() - started
    state_ok = (
        board.zobrist_hash == before_hash
        and board.current_player == before_player
    )
    nps = result.nodes_evaluated / elapsed if elapsed > 0 else 0.0
    return {
        "time": elapsed,
        "nodes": result.nodes_evaluated,
        "nps": nps,
        "score": result.score,
        "move": move_key(result.best_move),
        "state_ok": state_ok,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--depths", nargs="+", type=int, default=[2, 3, 4],
        help="search depths to benchmark (default: 2 3 4)",
    )
    args = parser.parse_args()
    depths = sorted(set(args.depths))
    if any(depth < 1 for depth in depths):
        parser.error("all depths must be >= 1")

    variants = (
        ("FULL", True, True),
        ("NO_TT", False, True),
        ("NO_PVS", True, False),
        ("NO_TT_NO_PVS", False, False),
    )

    print(f"depths={depths}  QS=True  null_move=False")
    for name, fen, color in POSITIONS:
        print(f"\n=== {name} ===")
        board = Board() if fen is None else board_from_fen(fen)
        for depth in depths:
            print(f"d{depth}:")
            results = {}
            for label, use_tt, use_pvs in variants:
                result = run_case(board, color, depth, use_tt, use_pvs)
                results[label] = result
                print(
                    "  {:13s} time={:.3f}s nodes={:7d} nps={:8.1f} "
                    "score={:7d} move={} state_ok={}".format(
                        label,
                        result["time"],
                        result["nodes"],
                        result["nps"],
                        result["score"],
                        result["move"],
                        result["state_ok"],
                    )
                )
            full = results["FULL"]
            for label in ("NO_TT", "NO_PVS", "NO_TT_NO_PVS"):
                other = results[label]
                print(
                    "    vs FULL {:13s} move_same={} score_delta={:+d}".format(
                        label,
                        other["move"] == full["move"],
                        other["score"] - full["score"],
                    )
                )


if __name__ == "__main__":
    main()

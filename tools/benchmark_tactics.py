"""Benchmark the engine against small, objectively checkable tactical positions."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Allow direct execution from the repository root, e.g.:
#   python tools/benchmark_tactics.py --depths 2 3 4
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
for path in (SRC, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine
from test_tactical_positions import TACTICAL_POSITIONS, immediate_mates


def move_key(move):
    if move is None:
        return None
    return (move.from_pos, move.to_pos)


def free_capture_targets(board, color):
    """Find captures whose destination cannot be immediately recaptured."""
    targets = []
    for move in Rule.generate_legal_moves(board, color):
        if move.captured_piece is None:
            continue
        board.move(move.from_pos, move.to_pos)
        try:
            opponent = board.opponent(color)
            recaptures = [
                reply
                for reply in Rule.generate_legal_moves(board, opponent)
                if reply.to_pos == move.to_pos
            ]
            if not recaptures:
                targets.append(move)
        finally:
            board.undo()
    return targets


def exchange_trap_targets(board, color):
    """Find captures that allow an immediate opponent recapture."""
    targets = []
    for move in Rule.generate_legal_moves(board, color):
        if move.captured_piece is None:
            continue
        board.move(move.from_pos, move.to_pos)
        try:
            opponent = board.opponent(color)
            recaptures = [
                reply
                for reply in Rule.generate_legal_moves(board, opponent)
                if reply.to_pos == move.to_pos
            ]
            if recaptures:
                targets.append(move)
        finally:
            board.undo()
    return targets


def run_position(name, depths, use_null_move=False):
    spec = TACTICAL_POSITIONS[name]
    print(f"\n=== {name} ===")

    board = board_from_fen(spec["fen"])
    color = spec["side"]

    mates = immediate_mates(board, color)
    free_captures = free_capture_targets(board, color)
    trap_captures = exchange_trap_targets(board, color)

    print("objective checks:")
    print("  immediate mates:", [move_key(m) for m in mates])
    print("  free captures:", [move_key(m) for m in free_captures])
    print("  immediately recapturable captures:", [move_key(m) for m in trap_captures])

    for depth in depths:
        engine = SearchEngine(depth=depth, use_null_move=use_null_move)
        before_hash = board.zobrist_hash
        before_player = board.current_player
        started = time.perf_counter()
        result = engine.choose_move(board, color)
        elapsed = time.perf_counter() - started

        selected = move_key(result.best_move)
        mate_hit = selected in {move_key(m) for m in mates}
        free_hit = selected in {move_key(m) for m in free_captures}
        trap_hit = selected in {move_key(m) for m in trap_captures}
        state_ok = board.zobrist_hash == before_hash and board.current_player == before_player
        nps = result.nodes_evaluated / elapsed if elapsed > 0 else 0.0

        print(
            f"d{depth} time={elapsed:.3f}s nodes={result.nodes_evaluated} "
            f"nps={nps:.1f} score={result.score} move={selected} "
            f"mate_hit={mate_hit} free_hit={free_hit} trap_hit={trap_hit} "
            f"state_ok={state_ok} null_attempts={engine.null_move_attempts} "
            f"null_cutoffs={engine.null_move_cutoffs}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--depths",
        nargs="+",
        type=int,
        default=[2, 3, 4],
        help="search depths to benchmark (default: 2 3 4)",
    )
    parser.add_argument(
        "--null-move",
        action="store_true",
        help="enable the experimental Null Move pruning",
    )
    args = parser.parse_args()

    for name in TACTICAL_POSITIONS:
        run_position(name, args.depths, use_null_move=args.null_move)


if __name__ == "__main__":
    main()

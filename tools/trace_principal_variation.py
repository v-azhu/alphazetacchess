"""Trace searched root candidates and their transposition-table principal lines.

Examples:
    python tools/trace_principal_variation.py --position tactical_exchange --depths 3 4
    python tools/trace_principal_variation.py --position initial --depths 3 4 \
        --candidates 1,2:1,9 7,2:7,9
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
for path in (SRC, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen, board_to_fen
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


def parse_move(value):
    try:
        source_text, target_text = value.split(":")
        source = tuple(int(coord) for coord in source_text.split(","))
        target = tuple(int(coord) for coord in target_text.split(","))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            f"invalid move {value!r}; expected x,y:x,y"
        ) from exc
    if len(source) != 2 or len(target) != 2:
        raise argparse.ArgumentTypeError(
            f"invalid move {value!r}; expected x,y:x,y"
        )
    return source, target


def move_text(move):
    return f"{move[0][0]},{move[0][1]}->{move[1][0]},{move[1][1]}"


def capture_text(piece):
    return None if piece is None else f"{piece.color.name} {piece.type.name}"


def trace_candidate(board, color, move_key, depth):
    """Search one root move with an isolated TT and trace its stored replies."""
    if depth < 1:
        raise ValueError("depth must be at least 1")
    if board.current_player != color:
        raise ValueError("board.current_player must match the root search color")
    legal_moves = Rule.generate_legal_moves(board, color)
    move = next(
        (
            candidate
            for candidate in legal_moves
            if (candidate.from_pos, candidate.to_pos) == move_key
        ),
        None,
    )
    if move is None:
        raise ValueError(f"root candidate {move_text(move_key)} is not legal")

    engine = SearchEngine(depth=depth, iterative_deepening=False)
    original_state = (
        board_to_fen(board),
        board.zobrist_hash,
        tuple(board.position_history),
        tuple(board.repetition_history),
        len(board.history),
    )
    board.move(move.from_pos, move.to_pos)
    try:
        searched_score = -engine._negamax(
            board,
            depth - 1,
            float("-inf"),
            float("inf"),
            board.current_player,
            depth,
            use_pruning=True,
        )
        static_score = -engine._evaluate(board, board.current_player)

        principal_line = [move_key]
        captures = [capture_text(move.captured_piece)]
        tt_steps = []
        remaining_depth = depth - 1
        while remaining_depth > 0:
            # This diagnostic deliberately reads the TT directly: probe()
            # applies search-bound cutoffs, while the tracer needs each stored
            # move and its bound metadata to explain the observed line.
            entry = engine.tt._table.get(board.zobrist_hash)
            if entry is None or entry.depth < remaining_depth or entry.best_move is None:
                break

            reply = entry.best_move
            legal_replies = Rule.generate_legal_moves(board, board.current_player)
            reply_move = next(
                (
                    candidate
                    for candidate in legal_replies
                    if candidate.from_pos == reply[0] and candidate.to_pos == reply[1]
                ),
                None,
            )
            if reply_move is None:
                break

            tt_steps.append({
                "move": reply,
                "depth": entry.depth,
                "bound": entry.bound.name,
                "captured_piece": capture_text(reply_move.captured_piece),
            })
            principal_line.append(reply)
            captures.append(capture_text(reply_move.captured_piece))
            board.move(*reply)
            remaining_depth -= 1

        leaf_evaluation = engine._evaluate(board, board.current_player)
        leaf_quiescence = engine._quiescence(
            board,
            float("-inf"),
            float("inf"),
            board.current_player,
            depth,
            0,
        )
    finally:
        while len(board.history) > original_state[4]:
            board.undo()

    restored_state = (
        board_to_fen(board),
        board.zobrist_hash,
        tuple(board.position_history),
        tuple(board.repetition_history),
    )
    if restored_state != original_state[:4]:
        raise RuntimeError("PV trace failed to restore the input board")

    return {
        "move": move_key,
        "static_score": static_score,
        "searched_score": searched_score,
        "delta": searched_score - static_score,
        "principal_line": principal_line,
        "captures": captures,
        "tt_steps": tt_steps,
        "leaf_evaluation": leaf_evaluation,
        "leaf_quiescence": leaf_quiescence,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--position", choices=sorted(POSITIONS), default="tactical_exchange")
    parser.add_argument("--depths", nargs="+", type=int, default=[3, 4])
    parser.add_argument(
        "--candidates",
        nargs="+",
        type=parse_move,
        help="root moves in x,y:x,y form; default is the engine choice at each depth",
    )
    args = parser.parse_args()
    if any(depth < 1 for depth in args.depths):
        parser.error("all depths must be >= 1")

    fen, color = POSITIONS[args.position]
    for depth in sorted(set(args.depths)):
        board = Board() if fen is None else board_from_fen(fen)
        candidates = args.candidates
        if candidates is None:
            result = SearchEngine(depth=depth).choose_move(board, color)
            if result.best_move is None:
                raise RuntimeError(f"no root move available for {args.position}")
            candidates = [(result.best_move.from_pos, result.best_move.to_pos)]

        print(f"\n=== {args.position} depth {depth} ===")
        for candidate in candidates:
            trace = trace_candidate(board, color, candidate, depth)
            line = " ".join(
                move_text(step)
                + (f" x {captured}" if captured is not None else "")
                for step, captured in zip(
                    trace["principal_line"], trace["captures"], strict=True
                )
            )
            print(
                f"root={move_text(candidate)} static={trace['static_score']} "
                f"search={trace['searched_score']} delta={trace['delta']:+}"
            )
            print(f"  tt-line: {line}")
            print(
                f"  TT steps: {trace['tt_steps']}; "
                f"leaf static={trace['leaf_evaluation']} "
                f"leaf quiescence={trace['leaf_quiescence']}"
            )

    print(
        "\nCaveat: TT lines can contain bound moves, not only exact PV moves. "
        "The reported quiescence score is recomputed at the end of the traced line; "
        "it is not guaranteed to be the exact leaf that produced the root score."
    )


if __name__ == "__main__":
    main()

"""Extract V0.10 positions where AlphaZeta returned a depth-zero move."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alphazetacchess.core.fen import board_from_fen, board_to_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.core.move import Move
from alphazetacchess.core.rule import Rule


DEFAULT_INPUT = (
    ROOT / "data" / "v0.10_pikafish_vs_search_500ms_10openings_post_qsearch_dispatch.jsonl"
)
DEFAULT_OUTPUT = ROOT / "data" / "suites" / "az_fallback_25.json"


def absolute_ply_from_fen(fen):
    fields = fen.split()
    if len(fields) < 6:
        raise ValueError(f"FEN is missing its fullmove number: {fen!r}")
    fullmove = int(fields[5])
    if fullmove < 1:
        raise ValueError(f"Invalid FEN fullmove number: {fullmove}")
    return (fullmove - 1) * 2 + (1 if fields[1] == "w" else 2)


def extract_fallback_positions(records):
    positions = []
    for game_index, record in enumerate(records, start=1):
        initial_fen = record.get("initial_fen")
        if not initial_fen:
            raise ValueError(f"Game {game_index} has no initial_fen")
        board = board_from_fen(initial_fen)
        alpha_stats = record.get("search_stats", {}).get("alphazeta", [])
        alpha_index = 0
        next_absolute_ply = absolute_ply_from_fen(initial_fen)

        for move_index, raw_move in enumerate(record.get("moves", []), start=1):
            mover = board.current_player.name
            if mover != record.get("pikafish_color"):
                if alpha_index >= len(alpha_stats):
                    raise ValueError(
                        f"Game {game_index} has fewer AlphaZeta stats than moves"
                    )
                stats = alpha_stats[alpha_index]
                alpha_index += 1
                if stats.get("side") != mover:
                    raise ValueError(
                        f"Game {game_index} AlphaZeta stat side mismatch at move "
                        f"{move_index}: {stats.get('side')} != {mover}"
                    )
                if stats.get("depth") == 0:
                    fen = board_to_fen(board)
                    move = Move(tuple(raw_move["from"]), tuple(raw_move["to"]))
                    positions.append({
                        "game_index": game_index,
                        "opening_index": record.get("opening_index"),
                        "move_index": move_index,
                        "game_ply": next_absolute_ply,
                        "side_to_move": mover,
                        "position_fen": fen,
                        "move_played": GameRecord.move_to_iccs(move),
                        "search_depth": 0,
                        "nodes": stats.get("nodes"),
                        "elapsed_ms": stats.get("elapsed_ms"),
                    })

            move = Move(tuple(raw_move["from"]), tuple(raw_move["to"]))
            if not Rule.is_legal_move(board, move, board.current_player):
                raise ValueError(
                    f"Illegal move in game {game_index}, ply {move_index}: {raw_move!r}"
                )
            board.move(move.from_pos, move.to_pos)
            next_absolute_ply += 1

        if alpha_index != len(alpha_stats):
            raise ValueError(
                f"Game {game_index} has {len(alpha_stats) - alpha_index} unused "
                "AlphaZeta search-stat record(s)"
            )
    return positions


def read_records(path):
    with Path(path).open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_number}") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-count", type=int, default=25)
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"input file does not exist: {args.input}")
    if args.expected_count < 0:
        parser.error("--expected-count must be non-negative")

    positions = extract_fallback_positions(read_records(args.input))
    if args.expected_count and len(positions) != args.expected_count:
        raise RuntimeError(
            f"Expected {args.expected_count} depth-zero positions, found {len(positions)}"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "format": "alphazeta-az-fallback-25-v1",
        "source": str(args.input.relative_to(ROOT))
        if args.input.is_relative_to(ROOT) else str(args.input),
        "positions": positions,
    }
    with args.output.open("w", encoding="utf-8") as target:
        json.dump(output, target, separators=(",", ":"), ensure_ascii=False)
        target.write("\n")
    print(f"Extracted {len(positions)} depth-zero positions to {args.output}")


if __name__ == "__main__":
    main()

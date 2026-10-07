"""Build an opt-in Pikafish opening book from frequent tournament positions.

The game archives provide realistic positions; a local Pikafish process supplies
the move choice for each selected position. Only moves and public search metadata
are written to the output -- the NNUE weights are never copied or modified.

Example:
    python tools/build_pikafish_opening_book.py \\
        --input trainingdata/wxf-41743games.zip trainingdata/dpxq-99813games.zip \\
        --pikafish-path /path/to/Pikafish-Linux-x86-64-universal \\
        --network-path /path/to/pikafish.nnue \\
        --output data/pikafish_opening_book.json

Use with the existing engine switch:
    python tools/compare_engines.py --a-use-opening-book \\
        --opening-book data/pikafish_opening_book.json
"""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tools.import_external_games import parse_games
from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen, board_to_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.core.move import Move
from alphazetacchess.core.rule import Rule
from alphazetacchess.neural.pikafish_client import PikafishClient, mate_score_to_cp


BOOK_FORMAT = "alphazeta-pikafish-opening-book-v1"


def read_games(path):
    """Yield parsed games from a raw PGNs file or a zip containing one."""
    source = Path(path)
    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            members = [
                name for name in archive.namelist()
                if name.lower().endswith((".pgns", ".pgn"))
            ]
            if len(members) != 1:
                raise ValueError(
                    f"Expected exactly one .pgns/.pgn member in {source}, found {len(members)}"
                )
            text = archive.read(members[0]).decode("utf-8", errors="replace")
    else:
        text = source.read_text(encoding="utf-8", errors="replace")
    yield from parse_games(text)


def collect_frequent_positions(games, max_ply):
    """Count distinct source positions once per game with cheap board sanity checks.

    The archived sources report that illegal games were filtered before
    distribution. Full rule-legal validation at every ply would regenerate all
    legal moves millions of times; teacher-selected moves are still validated
    with Rule.is_legal_move before they enter the book.
    """
    visits = Counter()
    position_fens = {}
    rejected_games = 0
    parsed_games = 0

    for moves, _result in games:
        parsed_games += 1
        board = Board()
        game_positions = {}
        valid_prefix = True
        for from_pos, to_pos in moves[:max_ply]:
            from_x, from_y = from_pos
            to_x, to_y = to_pos
            piece = board.board[from_y][from_x]
            target = board.board[to_y][to_x]
            if (
                piece is None
                or piece.color != board.current_player
                or (target is not None and target.color == board.current_player)
            ):
                valid_prefix = False
                break
            key = f"{board.zobrist_hash}-{board.current_player.name}"
            game_positions.setdefault(key, board_to_fen(board))
            board.move(from_pos, to_pos)

        if not valid_prefix:
            rejected_games += 1
            continue
        for key, fen in game_positions.items():
            visits[key] += 1
            position_fens.setdefault(key, fen)

    return parsed_games, rejected_games, visits, position_fens


def build_teacher_book(visits, position_fens, client, min_visits, max_positions):
    """Ask Pikafish for a legal best move at each frequent position."""
    candidates = sorted(
        (
            (key, count) for key, count in visits.items()
            if count >= min_visits
        ),
        key=lambda item: (-item[1], item[0]),
    )
    if max_positions is not None:
        candidates = candidates[:max_positions]

    book = {"_format": BOOK_FORMAT}
    for index, (key, game_count) in enumerate(candidates, start=1):
        fen = position_fens[key]
        result = client.evaluate_fen(fen)
        notation = result["best_move"]
        if not notation or notation == "0000":
            raise RuntimeError(f"Pikafish returned no move for book position {key}")

        board = board_from_fen(fen)
        move = GameRecord.move_from_iccs(notation)
        if not Rule.is_legal_move(board, move, board.current_player):
            raise RuntimeError(
                f"Pikafish returned illegal move {notation!r} for book position {key}"
            )
        score_cp = result["score_cp"]
        if score_cp is None and result["mate_in"] is not None:
            score_cp = mate_score_to_cp(result["mate_in"])

        book[key] = {
            "best_move": GameRecord.move_to_iccs(move),
            "score_cp": score_cp,
            "depth": result["depth"],
            "source_games": game_count,
            "fen": fen,
        }
        if index % 50 == 0 or index == len(candidates):
            print(f"  Pikafish-labeled {index}/{len(candidates)} positions", flush=True)
    return book


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True, help="PGNs or zip archives")
    parser.add_argument("--pikafish-path", required=True)
    parser.add_argument("--network-path", default=None)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-ply", type=int, default=20)
    parser.add_argument(
        "--min-visits", type=int, default=100,
        help="minimum distinct source games containing a position before labeling it",
    )
    parser.add_argument("--max-positions", type=int, default=2000)
    parser.add_argument("--movetime-ms", type=int, default=250)
    args = parser.parse_args()
    if min(args.max_ply, args.min_visits, args.movetime_ms) < 1:
        parser.error("--max-ply, --min-visits, and --movetime-ms must be positive")
    if args.max_positions is not None and args.max_positions < 1:
        parser.error("--max-positions must be positive")

    output = Path(args.output)
    if output.exists():
        parser.error(f"output already exists: {output}")

    print(f"Mining legal positions through ply {args.max_ply}...", flush=True)
    parsed_games, rejected_games, visits, fens = collect_frequent_positions(
        (game for path in args.input for game in read_games(path)),
        args.max_ply,
    )
    print(
        f"Parsed {parsed_games} result-bearing games; rejected {rejected_games} "
        f"with inconsistent piece occupancy/turn; found {len(visits)} distinct positions.",
        flush=True,
    )
    eligible = sum(count >= args.min_visits for count in visits.values())
    print(
        f"{eligible} positions meet min-visits={args.min_visits}; "
        f"label cap={args.max_positions}.",
        flush=True,
    )

    with PikafishClient(
        args.pikafish_path,
        movetime_ms=args.movetime_ms,
        network_path=args.network_path,
    ) as client:
        book = build_teacher_book(
            visits, fens, client, args.min_visits, args.max_positions
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as target:
        json.dump(book, target, ensure_ascii=False, separators=(",", ":"))
        target.write("\n")
    print(
        f"Saved {len(book) - 1} Pikafish-selected positions to {output}. "
        "The engine's opening_book_min_games also applies to each entry's source_games count.",
        flush=True,
    )


if __name__ == "__main__":
    main()

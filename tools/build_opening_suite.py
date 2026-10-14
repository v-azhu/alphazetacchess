"""Build the balanced, replayable 8-ply opening suite for V0.11.1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen, board_to_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color, PieceType
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.evaluation import MATERIAL_VALUES
from alphazetacchess.neural.pikafish_client import PikafishClient, mate_score_to_cp


DEFAULT_INPUTS = [
    ROOT / "trainingdata" / "wxf-41743games.zip",
    ROOT / "trainingdata" / "dpxq-99813games.zip",
]
DEFAULT_OUTPUT = ROOT / "data" / "suites" / "openings_8ply_v1.json"
DEFAULT_MANIFEST = ROOT / "data" / "suites" / "openings_8ply_v1.manifest.json"


def read_records(paths):
    for path in paths:
        path = Path(path)
        if zipfile.is_zipfile(path):
            from tools.import_external_games import parse_games

            with zipfile.ZipFile(path) as archive:
                members = [
                    name for name in archive.namelist()
                    if name.lower().endswith((".pgns", ".pgn"))
                ]
                if len(members) != 1:
                    raise ValueError(
                        f"Expected one .pgns/.pgn member in {path}, found {len(members)}"
                    )
                text = archive.read(members[0]).decode("utf-8", errors="replace")
            for moves, _result in parse_games(text):
                yield {
                    "_source_moves_prevalidated": True,
                    "moves": [
                        {"from": list(from_pos), "to": list(to_pos)}
                        for from_pos, to_pos in moves
                    ],
                }
            continue
        with Path(path).open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in {path}:{line_number}") from exc


def _move_parts(raw_move):
    if isinstance(raw_move, str):
        move = GameRecord.move_from_iccs(raw_move)
        return move.from_pos, move.to_pos
    return tuple(raw_move["from"]), tuple(raw_move["to"])


def _position_key(fen):
    return " ".join(fen.split()[:2])


def material_balance_cp(board):
    balance = 0
    for row in board.board:
        for piece in row:
            if piece is None or piece.type == PieceType.KING:
                continue
            value = MATERIAL_VALUES[piece.type]
            balance += value if piece.color == Color.RED else -value
    return balance


def opening_from_record(record, opening_plies=8):
    board = (
        board_from_fen(record["initial_fen"])
        if record.get("initial_fen")
        else Board()
    )
    prefix = []
    for raw_move in record.get("moves", [])[:opening_plies]:
        from_pos, to_pos = _move_parts(raw_move)
        move = Move(from_pos, to_pos)
        if record.get("_source_moves_prevalidated"):
            piece = board.get(*from_pos)
            target = board.get(*to_pos)
            if (
                piece is None
                or piece.color != board.current_player
                or (target is not None and target.color == board.current_player)
            ):
                return None
        elif not Rule.is_legal_move(board, move, board.current_player):
            return None
        prefix.append({
            "color": board.current_player.name,
            "from": list(from_pos),
            "to": list(to_pos),
        })
        board.move(from_pos, to_pos)
    if len(prefix) != opening_plies or board.current_player != Color.RED:
        return None
    if not Rule.generate_legal_moves(board, board.current_player):
        return None
    fen = board_to_fen(board)
    return {
        "initial_fen": fen,
        "opening_prefix": prefix,
        "_position_key": _position_key(fen),
        "_material_balance_cp": material_balance_cp(board),
    }


def collect_candidates(records, opening_plies=8):
    candidates = {}
    replayed = 0
    for record in records:
        opening = opening_from_record(record, opening_plies)
        if opening is None:
            continue
        replayed += 1
        candidates.setdefault(opening["_position_key"], opening)
    return list(candidates.values()), replayed


def _score_cp(result):
    score = result.get("score_cp")
    if score is None and result.get("mate_in") is not None:
        score = mate_score_to_cp(result["mate_in"])
    if score is None:
        raise RuntimeError("Pikafish returned neither a centipawn nor mate score")
    return score


def build_openings(
    records,
    opening_count=2000,
    opening_plies=8,
    seed=0,
    max_abs_eval_cp=100,
    pikafish_client=None,
):
    if opening_count < 1:
        raise ValueError("opening_count must be positive")
    if opening_plies < 2 or opening_plies % 2:
        raise ValueError("opening_plies must be a positive even number")

    candidates, replayed = collect_candidates(records, opening_plies)
    balanced = []
    for opening in candidates:
        if pikafish_client is None:
            score = opening["_material_balance_cp"]
        else:
            score = _score_cp(pikafish_client.evaluate_fen(opening["initial_fen"]))
        if abs(score) <= max_abs_eval_cp:
            opening["opening_eval_cp"] = score
            balanced.append(opening)

    if len(balanced) < opening_count:
        raise ValueError(
            f"Need {opening_count} balanced distinct openings, found {len(balanced)} "
            f"from {replayed} replayable records"
        )

    selected = random.Random(seed).sample(balanced, opening_count)
    output = []
    for index, opening in enumerate(selected):
        output.append({
            "initial_fen": opening["initial_fen"],
            "opening_prefix": opening["opening_prefix"],
            "opening_index": index,
        })
    return output, {
        "source_records_replayed": replayed,
        "distinct_openings": len(candidates),
        "balanced_openings": len(balanced),
    }


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--count", type=int, default=2000)
    parser.add_argument("--opening-plies", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-abs-eval-cp", type=int, default=100)
    parser.add_argument("--pikafish-path", type=Path)
    parser.add_argument("--network-path", type=Path)
    parser.add_argument("--eval-depth", type=int, default=12)
    args = parser.parse_args()
    if args.max_abs_eval_cp < 0 or args.eval_depth < 1:
        parser.error("--max-abs-eval-cp must be non-negative and --eval-depth positive")
    if args.network_path and not args.pikafish_path:
        parser.error("--network-path requires --pikafish-path")
    missing = [str(path) for path in args.input if not path.is_file()]
    if missing:
        parser.error(f"input file(s) do not exist: {', '.join(missing)}")

    client = None
    try:
        if args.pikafish_path:
            client = PikafishClient(
                str(args.pikafish_path),
                network_path=str(args.network_path) if args.network_path else None,
                search_depth=args.eval_depth,
            )
        suite, counts = build_openings(
            read_records(args.input),
            opening_count=args.count,
            opening_plies=args.opening_plies,
            seed=args.seed,
            max_abs_eval_cp=args.max_abs_eval_cp,
            pikafish_client=client,
        )
    finally:
        if client is not None:
            client.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as target:
        json.dump(suite, target, separators=(",", ":"), ensure_ascii=False)
        target.write("\n")
    manifest = {
        "format": "alphazeta-opening-suite-manifest-v1",
        "suite": args.output.name,
        "count": len(suite),
        "opening_plies": args.opening_plies,
        "seed": args.seed,
        "max_abs_eval_cp": args.max_abs_eval_cp,
        "pikafish_filtered": client is not None,
        "filter": "pikafish" if client is not None else "material-only",
        "pikafish_eval_depth": args.eval_depth if client is not None else None,
        "inputs": [
            {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
             "sha256": sha256_file(path)}
            for path in args.input
        ],
        **counts,
    }
    with args.manifest.open("w", encoding="utf-8") as target:
        json.dump(manifest, target, indent=2, sort_keys=True)
        target.write("\n")
    print(
        f"Wrote {len(suite)} openings to {args.output}; "
        f"Pikafish-filtered={manifest['pikafish_filtered']} "
        f"({counts['balanced_openings']} balanced candidates)."
    )


if __name__ == "__main__":
    main()

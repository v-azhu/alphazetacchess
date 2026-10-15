"""Evaluate an engine or the first-generated-move baseline on a tactics suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import socket
import sys
from threading import Event, Timer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.neural.pikafish_client import PikafishClient


DEFAULT_SUITE = ROOT / "data" / "suites" / "az_tac_500.json"


def load_suite(path):
    with Path(path).open(encoding="utf-8") as source:
        suite = json.load(source)
    if not isinstance(suite.get("positions"), list):
        raise ValueError("Tactics suite must contain a positions array")
    return suite


def _validated_legal_moves(position, board):
    moves = Rule.generate_legal_moves(board, board.current_player)
    notations = [GameRecord.move_to_iccs(move) for move in moves]
    if set(notations) != set(position["legal_moves"]):
        raise ValueError(
            f"stored legal-move set disagrees with rules for {position['fen']}"
        )
    return moves


def choose_move(position, engine_spec, time_ms, engine=None):
    board = board_from_fen(position["fen"])
    legal_moves = _validated_legal_moves(position, board)
    if not legal_moves:
        raise ValueError(f"tactics position has no legal move: {position['fen']}")
    if engine_spec == "first":
        return GameRecord.move_from_iccs(position["legal_moves"][0])
    if engine_spec == "search":
        engine.tt.clear()
        stop_event = Event()
        timer = Timer(time_ms / 1000, stop_event.set)
        timer.start()
        try:
            result = engine.choose_move(board, board.current_player, stop_event=stop_event)
        finally:
            timer.cancel()
        move = result.best_move
    elif engine_spec == "uci":
        result = engine.evaluate_fen(position["fen"])
        notation = result["best_move"]
        if not notation or notation == "0000":
            raise RuntimeError(f"UCI engine returned no move for {position['fen']}")
        move = GameRecord.move_from_iccs(notation)
    else:
        raise ValueError(f"unsupported engine spec: {engine_spec}")
    if (
        move is None
        or GameRecord.move_to_iccs(move) not in position["legal_moves"]
    ):
        raise RuntimeError(f"{engine_spec} returned an illegal move for {position['fen']}")
    return move


def score_position(position, move):
    move_notation = GameRecord.move_to_iccs(move)
    scores = {entry["move"]: entry for entry in position["move_scores"]}
    if set(scores) != set(position["legal_moves"]):
        raise ValueError(f"incomplete or duplicate score labels for {position['fen']}")
    if move_notation not in scores:
        raise ValueError(f"chosen move {move_notation} has no score label")
    best_score = position["best_score_cp"]
    move_score = scores[move_notation]["score_cp"]
    cp_loss = max(0, best_score - move_score)
    best_moves = position.get("best_moves") or [position["best_move"]]
    return {
        "move": move_notation,
        "solve": move_notation in best_moves,
        "blunder": cp_loss >= 300,
        "centipawn_loss": cp_loss,
        "best_score_cp": best_score,
        "move_score_cp": move_score,
    }


def _aggregate(results):
    count = len(results)
    if not count:
        return {
            "positions": 0,
            "solve_rate": None,
            "blunder_rate": None,
            "mean_centipawn_loss": None,
        }
    return {
        "positions": count,
        "solve_rate": sum(item["solve"] for item in results) / count,
        "blunder_rate": sum(item["blunder"] for item in results) / count,
        "mean_centipawn_loss": sum(item["centipawn_loss"] for item in results) / count,
    }


def evaluate_suite(suite, engine_spec="first", time_ms=100, engine=None):
    if time_ms < 1:
        raise ValueError("time_ms must be positive")
    results = []
    for position in suite["positions"]:
        move = choose_move(position, engine_spec, time_ms, engine)
        results.append({
            "position_hash": position["position_hash"],
            "split": position.get("split"),
            "category": position.get("category"),
            **score_position(position, move),
        })
    groups = {}
    for key in ("split", "category"):
        for value in sorted({item[key] for item in results if item.get(key) is not None}):
            groups[value] = _aggregate(
                [item for item in results if item.get(key) == value]
            )
    return {
        "suite_format": suite.get("format"),
        "smoke_only": bool(suite.get("smoke_only")),
        "engine_spec": engine_spec,
        "time_ms_per_position": time_ms,
        "overall": _aggregate(results),
        "groups": groups,
        "positions": results,
        "machine": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "processor": platform.processor() or None,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--engine-spec", choices=("first", "search", "uci"), default="first")
    parser.add_argument("--time-ms", type=int, default=100)
    parser.add_argument("--engine-path", type=Path)
    parser.add_argument("--network-path", type=Path)
    parser.add_argument("--engine-config", default="{}", help="SearchEngine kwargs as JSON")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.suite.is_file():
        parser.error(f"suite file does not exist: {args.suite}")
    if args.time_ms < 1:
        parser.error("--time-ms must be positive")
    if args.network_path and not args.engine_path:
        parser.error("--network-path requires --engine-path")

    suite = load_suite(args.suite)
    engine = None
    if args.engine_spec == "search":
        try:
            config = json.loads(args.engine_config)
        except json.JSONDecodeError as exc:
            parser.error(f"invalid --engine-config JSON: {exc}")
        if not isinstance(config, dict):
            parser.error("--engine-config must decode to a JSON object")
        config.setdefault("depth", 64)
        engine = SearchEngine(**config)
    elif args.engine_spec == "uci":
        if not args.engine_path:
            parser.error("--engine-spec uci requires --engine-path")
        engine = PikafishClient(
            str(args.engine_path),
            movetime_ms=args.time_ms,
            network_path=str(args.network_path) if args.network_path else None,
        )

    try:
        report = evaluate_suite(suite, args.engine_spec, args.time_ms, engine)
    finally:
        if isinstance(engine, PikafishClient):
            engine.close()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as target:
            json.dump(report, target, indent=2, sort_keys=True)
            target.write("\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

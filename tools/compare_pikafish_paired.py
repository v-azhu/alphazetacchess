"""Compare AlphaZetaChess with Pikafish on paired, time-controlled openings.

Each selected opening is played twice, once with each engine as Red. Games
write independent records and are replay-validated before a merged JSONL and
opening manifest are saved. Search times are per-move limits, not hard
real-time guarantees.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import math
import os
import pathlib
import random
import statistics
import sys
import tempfile
import threading
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.pikafish import PikafishEngine
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.selfplay.paired_openings import select_paired_openings
from alphazetacchess.selfplay.recorder import append_record, load_records, play_recorded_game


class _TimedSearchEngine:
    def __init__(self, movetime_ms, depth_cap):
        self.search = SearchEngine(depth=depth_cap)
        self.movetime_ms = movetime_ms
        self.search_stats = []

    def choose_move(self, board, color):
        stop_event = threading.Event()
        timer = threading.Timer(self.movetime_ms / 1000, stop_event.set)
        started = time.monotonic()
        timer.start()
        try:
            result = self.search.choose_move(board, color, stop_event=stop_event)
            self.search_stats.append({
                "side": color.name,
                "depth": result.depth,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            })
            return result
        finally:
            timer.cancel()
            timer.join()


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _play_game(game_index, opening, max_moves, pikafish_path, network_path,
               pikafish_time_ms, search_time_ms, search_depth_cap, shard):
    if hasattr(os, "nice"):
        os.nice(10)
    pikafish_is_red = game_index % 2 == 0
    search = _TimedSearchEngine(search_time_ms, search_depth_cap)
    with PikafishEngine(
        pikafish_path, network_path, movetime_ms=pikafish_time_ms
    ) as pikafish:
        red, black = (
            (pikafish, search) if pikafish_is_red
            else (search, pikafish)
        )
        record = play_recorded_game(
            red,
            black,
            max_moves,
            red_config=(
                {"engine": "pikafish", "movetime_ms": pikafish_time_ms}
                if pikafish_is_red else {
                    "engine": "search",
                    "movetime_ms": search_time_ms,
                    "depth_cap": search_depth_cap,
                }
            ),
            black_config=(
                {
                    "engine": "search",
                    "movetime_ms": search_time_ms,
                    "depth_cap": search_depth_cap,
                }
                if pikafish_is_red else {
                    "engine": "pikafish",
                    "movetime_ms": pikafish_time_ms,
                }
            ),
            board=board_from_fen(opening["initial_fen"]),
        )
        record["initial_fen"] = opening["initial_fen"]
        record["opening_index"] = game_index // 2
        record["pikafish_color"] = "RED" if pikafish_is_red else "BLACK"
        record["pikafish_engine_info"] = list(pikafish.engine_info)
        record["search_stats"] = {
            "alphazeta": search.search_stats,
            "pikafish": pikafish.search_stats,
        }
    append_record(shard, record)
    return game_index, record["result"], record["total_moves"]


def _validate(
    records, openings, max_moves, pikafish_time_ms, search_time_ms, search_depth_cap
):
    if len(records) != 2 * len(openings):
        raise ValueError(f"Expected {2 * len(openings)} games; got {len(records)}")

    scores_by_opening = [[] for _ in openings]
    colors_by_opening = [[] for _ in openings]
    stats = {
        "pikafish_wins": 0,
        "search_wins": 0,
        "draws": 0,
        "pikafish_red": {"wins": 0, "losses": 0, "draws": 0},
        "pikafish_black": {"wins": 0, "losses": 0, "draws": 0},
    }

    for index, record in enumerate(records):
        game_number = index + 1
        opening_index = record.get("opening_index")
        if opening_index != index // 2:
            raise ValueError(f"Game {game_number}: unexpected opening order")
        if record.get("initial_fen") != openings[opening_index]["initial_fen"]:
            raise ValueError(f"Game {game_number}: wrong initial position")
        pikafish_color = "RED" if index % 2 == 0 else "BLACK"
        if record.get("pikafish_color") != pikafish_color:
            raise ValueError(f"Game {game_number}: colors were not swapped")
        colors_by_opening[opening_index].append(pikafish_color)
        engines = (
            record["red_config"].get("engine"),
            record["black_config"].get("engine"),
        )
        expected_engines = (
            ("pikafish", "search")
            if pikafish_color == "RED" else ("search", "pikafish")
        )
        if engines != expected_engines:
            raise ValueError(f"Game {game_number}: engine/color metadata mismatch")
        engine_configs = {
            "pikafish": (
                {"engine": "pikafish", "movetime_ms": pikafish_time_ms},
                record["red_config"] if pikafish_color == "RED" else record["black_config"],
            ),
            "search": (
                {
                    "engine": "search",
                    "movetime_ms": search_time_ms,
                    "depth_cap": search_depth_cap,
                },
                record["black_config"] if pikafish_color == "RED" else record["red_config"],
            ),
        }
        for name, (expected_config, actual_config) in engine_configs.items():
            if actual_config != expected_config:
                raise ValueError(f"Game {game_number}: {name} time-control metadata mismatch")

        board = board_from_fen(record["initial_fen"])
        moves = record.get("moves", [])
        if record.get("total_moves") != len(moves):
            raise ValueError(f"Game {game_number}: move-count metadata mismatch")
        expected_turns = {"RED": 0, "BLACK": 0}
        for ply, item in enumerate(moves, start=1):
            side = "RED" if board.current_player == Color.RED else "BLACK"
            if item.get("color") != side:
                raise ValueError(f"Game {game_number}, ply {ply}: wrong side to move")
            expected_turns[side] += 1
            move = Move(tuple(item["from"]), tuple(item["to"]))
            if not Rule.is_legal_move(board, move, board.current_player):
                raise ValueError(f"Game {game_number}, ply {ply}: illegal move {item!r}")
            board.move(move.from_pos, move.to_pos)
            if ply < len(moves) and Rule.is_game_over(board, board.current_player):
                raise ValueError(f"Game {game_number}: moves continue after terminal state")
        search_stats = record.get("search_stats", {})
        stats_by_engine = {
            "pikafish": search_stats.get("pikafish", []),
            "search": search_stats.get("alphazeta", []),
        }
        for engine_name, turns in stats_by_engine.items():
            side = (
                "RED" if (engine_name == "pikafish") == (pikafish_color == "RED")
                else "BLACK"
            )
            if len(turns) != expected_turns[side]:
                raise ValueError(
                    f"Game {game_number}: {engine_name} search stats do not match move count"
                )
            if any(
                turn.get("side") != side
                or turn.get("depth", -1) < 0
                or turn.get("elapsed_ms", -1) < 0
                for turn in turns
            ):
                raise ValueError(f"Game {game_number}: invalid {engine_name} search stats")

        result = record.get("result")
        if len(moves) == max_moves and not Rule.is_game_over(board, board.current_player):
            if result != "DRAW":
                raise ValueError(f"Game {game_number}: non-terminal move-cap result must be DRAW")
        else:
            if not Rule.is_game_over(board, board.current_player):
                raise ValueError(f"Game {game_number}: ended before terminal state or move cap")
            expected_result = "BLACK_WINS" if board.current_player == Color.RED else "RED_WINS"
            if result != expected_result:
                raise ValueError(f"Game {game_number}: result does not match terminal board")

        engine_color_stats = (
            stats["pikafish_red"] if pikafish_color == "RED"
            else stats["pikafish_black"]
        )
        pikafish_won = result == (
            "RED_WINS" if pikafish_color == "RED" else "BLACK_WINS"
        )
        if result == "DRAW":
            stats["draws"] += 1
            engine_color_stats["draws"] += 1
            scores_by_opening[opening_index].append(0.5)
        elif result in ("RED_WINS", "BLACK_WINS"):
            if pikafish_won:
                stats["pikafish_wins"] += 1
                engine_color_stats["wins"] += 1
                scores_by_opening[opening_index].append(1.0)
            else:
                stats["search_wins"] += 1
                engine_color_stats["losses"] += 1
                scores_by_opening[opening_index].append(0.0)
        else:
            raise ValueError(f"Game {game_number}: invalid result {result!r}")

    if any(len(scores) != 2 for scores in scores_by_opening):
        raise ValueError("Each opening must contain two games")
    if any(set(colors) != {"RED", "BLACK"} for colors in colors_by_opening):
        raise ValueError("Each opening must be played once with Pikafish as each color")
    stats["scores_by_opening"] = scores_by_opening
    return stats


def _bootstrap(scores_by_opening, samples, seed):
    rng = random.Random(seed)
    pair_scores = [sum(scores) / 2 for scores in scores_by_opening]
    estimates = sorted(
        sum(pair_scores[rng.randrange(len(pair_scores))] for _ in pair_scores)
        / len(pair_scores)
        for _ in range(samples)
    )
    return estimates[int(0.025 * (samples - 1))], estimates[int(0.975 * (samples - 1))]


def _elo(score):
    return 400 * math.log10(score / (1 - score)) if 0 < score < 1 else None


def _search_metrics(records):
    metrics = {}
    for engine_name, record_key in (
        ("pikafish", "pikafish"),
        ("alphazeta", "alphazeta"),
    ):
        turns = [
            turn
            for record in records
            for turn in record["search_stats"][record_key]
        ]
        metrics[engine_name] = {
            "turns": len(turns),
            "mean_depth": round(statistics.mean(turn["depth"] for turn in turns), 2),
            "mean_elapsed_ms": round(
                statistics.mean(turn["elapsed_ms"] for turn in turns), 2
            ),
            "max_elapsed_ms": max(turn["elapsed_ms"] for turn in turns),
        }
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pikafish-path", required=True)
    parser.add_argument("--network-path", required=True)
    parser.add_argument("--opening-count", type=int, default=10)
    parser.add_argument("--opening-plies", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20261005)
    parser.add_argument("--pikafish-time-ms", type=int, default=500)
    parser.add_argument("--search-time-ms", type=int, default=500)
    parser.add_argument("--search-depth-cap", type=int, default=64)
    parser.add_argument("--max-moves", type=int, default=150)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    args = parser.parse_args()
    if min(
        args.pikafish_time_ms, args.search_time_ms, args.search_depth_cap,
        args.max_moves, args.workers,
    ) < 1:
        parser.error("time limits, depth cap, max-moves, and workers must all be positive")
    if not os.path.isfile(args.pikafish_path) or not os.access(args.pikafish_path, os.X_OK):
        parser.error("--pikafish-path must point to an executable file")
    if not os.path.isfile(args.network_path):
        parser.error("--network-path must point to a readable network file")

    output = pathlib.Path(args.output)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    if output.exists() or manifest_path.exists():
        parser.error(f"output or manifest already exists: {output}")
    source_records = load_records(args.source)
    openings = select_paired_openings(
        source_records, args.opening_count, args.opening_plies, args.seed
    )

    with PikafishEngine(
        args.pikafish_path, args.network_path, movetime_ms=args.pikafish_time_ms
    ) as probe:
        engine_info = list(probe.engine_info)

    game_specs = [(i, openings[i // 2]) for i in range(2 * len(openings))]
    print(
        f"Running {len(game_specs)} games: SearchEngine and Pikafish at "
        f"{args.search_time_ms}/{args.pikafish_time_ms} ms per move, "
        f"{args.opening_count} paired openings, "
        f"{args.workers} workers",
        flush=True,
    )
    started = time.monotonic()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="alphazeta-pikafish-paired-") as temp_dir:
        shard_dir = pathlib.Path(temp_dir)
        completed = []
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    _play_game,
                    game_index,
                    opening,
                    args.max_moves,
                    args.pikafish_path,
                    args.network_path,
                    args.pikafish_time_ms,
                    args.search_time_ms,
                    args.search_depth_cap,
                    str(shard_dir / f"game-{game_index:04d}.jsonl"),
                ): game_index
                for game_index, opening in game_specs
            }
            for future in as_completed(futures):
                game_index, result, plies = future.result()
                completed.append(game_index)
                print(
                    f"Completed {len(completed):>3}/{len(game_specs)} "
                    f"(opening {game_index // 2 + 1}, Pikafish "
                    f"{'Red' if game_index % 2 == 0 else 'Black'}): "
                    f"{result}, {plies} plies",
                    flush=True,
                )
        if len(completed) != len(game_specs):
            raise RuntimeError("Not all games completed; refusing to merge")

        records = []
        for game_index, _ in game_specs:
            shard_records = load_records(shard_dir / f"game-{game_index:04d}.jsonl")
            if len(shard_records) != 1:
                raise ValueError(f"Expected one game record for game {game_index}")
            records.extend(shard_records)
        stats = _validate(
            records,
            openings,
            args.max_moves,
            args.pikafish_time_ms,
            args.search_time_ms,
            args.search_depth_cap,
        )
        score = (stats["pikafish_wins"] + 0.5 * stats["draws"]) / len(records)
        ci = _bootstrap(stats["scores_by_opening"], 20000, args.seed)
        search_metrics = _search_metrics(records)

        with output.with_suffix(output.suffix + ".tmp").open("w", encoding="utf-8") as out:
            for record in records:
                out.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        os.replace(output.with_suffix(output.suffix + ".tmp"), output)
        manifest = {
            "source": str(args.source),
            "seed": args.seed,
            "opening_plies": args.opening_plies,
            "openings": openings,
            "pikafish_path": os.path.abspath(args.pikafish_path),
            "pikafish_sha256": _sha256(args.pikafish_path),
            "network_path": os.path.abspath(args.network_path),
            "network_sha256": _sha256(args.network_path),
            "pikafish_engine_info": engine_info,
            "pikafish_time_ms": args.pikafish_time_ms,
            "search_time_ms": args.search_time_ms,
            "search_depth_cap": args.search_depth_cap,
            "max_moves": args.max_moves,
            "pairing": "each opening played once with Pikafish as Red and once as Black",
            "games": len(records),
            "results": {
                "pikafish_wins": stats["pikafish_wins"],
                "search_wins": stats["search_wins"],
                "draws": stats["draws"],
                "score_rate": score,
                "paired_bootstrap_95_percent_score_interval": list(ci),
                "elo_estimate": _elo(score),
                "by_color": {
                    "pikafish_red": stats["pikafish_red"],
                    "pikafish_black": stats["pikafish_black"],
                },
            },
            "search_metrics": search_metrics,
            "timing_note": (
                "Per-move limits are equal but not hard real-time guarantees; "
                "the Python search timer may overshoot slightly."
            ),
        }
        with manifest_path.open("w", encoding="utf-8") as out:
            json.dump(manifest, out, ensure_ascii=False, indent=2)
            out.write("\n")

    print(
        f"Pikafish W/L/D={stats['pikafish_wins']}/{stats['search_wins']}/"
        f"{stats['draws']}; score={score:.1%}; paired bootstrap 95% "
        f"CI={ci[0]:.1%}..{ci[1]:.1%}; Elo={_elo(score)}",
        flush=True,
    )
    print(
        f"Per color: Pikafish Red {stats['pikafish_red']}; "
        f"Black {stats['pikafish_black']}",
        flush=True,
    )
    print(f"Search metrics: {search_metrics}", flush=True)
    print(
        f"Validated data: {output}; manifest: {manifest_path}; "
        f"elapsed={(time.monotonic() - started) / 60:.1f} minutes",
        flush=True,
    )


if __name__ == "__main__":
    main()

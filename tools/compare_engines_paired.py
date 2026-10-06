"""Run a fixed-opening, color-swapped SearchEngine comparison.

Openings are sampled reproducibly from distinct legal prefixes in a JSONL
game corpus. Each selected position is played twice, once with depth 4 as Red
and once with depth 4 as Black. If source records contain depth-specific search
configuration, it is reused; otherwise baseline SearchEngine settings are used.
Games run in separate worker processes and write isolated JSONL shards; the
final file is created only after all records have been replay-validated.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
import os
import pathlib
import random
import sys
import tempfile
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.selfplay.paired_openings import select_paired_openings
from alphazetacchess.selfplay.recorder import (
    append_record,
    load_records,
    play_recorded_game,
)


def _play_one_game(game_index, opening, max_moves, depth4_config, depth3_config, shard):
    if hasattr(os, "nice"):
        os.nice(10)
    opening_index = game_index // 2
    depth4_is_red = game_index % 2 == 0
    depth4_engine = _build_engine(depth4_config)
    depth3_engine = _build_engine(depth3_config)
    red_engine, black_engine = (
        (depth4_engine, depth3_engine) if depth4_is_red
        else (depth3_engine, depth4_engine)
    )
    record = play_recorded_game(
        red_engine,
        black_engine,
        max_moves,
        red_config=depth4_config if depth4_is_red else depth3_config,
        black_config=depth3_config if depth4_is_red else depth4_config,
        board=board_from_fen(opening["initial_fen"]),
    )
    record["initial_fen"] = opening["initial_fen"]
    record["opening_index"] = opening_index
    record["depth4_color"] = "RED" if depth4_is_red else "BLACK"
    append_record(shard, record)
    return game_index, record["result"], record["total_moves"]


def _build_engine(config):
    from compare_engines import build_engine

    return build_engine(config, random_opening_plies=0, random_opening_prob=0)


def _validate_records(records, openings, max_moves):
    if len(records) != 2 * len(openings):
        raise ValueError(f"Expected {2 * len(openings)} games, found {len(records)}")

    scores_by_opening = [[] for _ in openings]
    colors_by_opening = [[] for _ in openings]
    wins = losses = draws = 0
    depth4_red = {"wins": 0, "losses": 0, "draws": 0}
    depth4_black = {"wins": 0, "losses": 0, "draws": 0}
    for game_number, record in enumerate(records, start=1):
        opening_index = record.get("opening_index")
        if not isinstance(opening_index, int) or not 0 <= opening_index < len(openings):
            raise ValueError(f"Game {game_number}: invalid opening index {opening_index!r}")
        expected_fen = openings[opening_index]["initial_fen"]
        if record.get("initial_fen") != expected_fen:
            raise ValueError(f"Game {game_number}: starting FEN does not match its opening")
        # Records are sorted by game_index before validation, preserving the
        # prescribed Red/Black ordering within each opening pair.
        expected_color = "RED" if (game_number - 1) % 2 == 0 else "BLACK"
        if record.get("depth4_color") != expected_color:
            raise ValueError(f"Game {game_number}: color assignment is not paired")
        colors_by_opening[opening_index].append(expected_color)
        red_depth = record["red_config"].get("depth")
        black_depth = record["black_config"].get("depth")
        if (red_depth, black_depth) != (
            (4, 3) if expected_color == "RED" else (3, 4)
        ):
            raise ValueError(f"Game {game_number}: unexpected engine depths")

        board = board_from_fen(expected_fen)
        moves = record.get("moves", [])
        if record.get("total_moves") != len(moves):
            raise ValueError(f"Game {game_number}: move count metadata mismatch")
        for ply, raw_move in enumerate(moves, start=1):
            side = "RED" if board.current_player == Color.RED else "BLACK"
            if raw_move.get("color") != side:
                raise ValueError(f"Game {game_number}, ply {ply}: wrong side to move")
            move = Move(tuple(raw_move["from"]), tuple(raw_move["to"]))
            if not Rule.is_legal_move(board, move, board.current_player):
                raise ValueError(f"Game {game_number}, ply {ply}: illegal move {raw_move!r}")
            board.move(move.from_pos, move.to_pos)
            if ply < len(moves) and Rule.is_game_over(board, board.current_player):
                raise ValueError(f"Game {game_number}: moves continue after terminal position")
        if len(moves) == max_moves:
            if record["result"] != "DRAW":
                raise ValueError(f"Game {game_number}: move-limit result must be a draw")
        else:
            if not Rule.is_game_over(board, board.current_player):
                raise ValueError(f"Game {game_number}: ended before terminal result or move limit")
            expected_result = (
                "BLACK_WINS" if board.current_player == Color.RED else "RED_WINS"
            )
            if record["result"] != expected_result:
                raise ValueError(f"Game {game_number}: result does not match terminal position")

        result = record.get("result")
        depth4_won = result == ("RED_WINS" if expected_color == "RED" else "BLACK_WINS")
        color_stats = depth4_red if expected_color == "RED" else depth4_black
        if result == "DRAW":
            draws += 1
            color_stats["draws"] += 1
            scores_by_opening[opening_index].append(0.5)
        elif result in ("RED_WINS", "BLACK_WINS"):
            if depth4_won:
                wins += 1
                color_stats["wins"] += 1
                scores_by_opening[opening_index].append(1.0)
            else:
                losses += 1
                color_stats["losses"] += 1
                scores_by_opening[opening_index].append(0.0)
        else:
            raise ValueError(f"Game {game_number}: invalid result {result!r}")

    if any(len(pair_scores) != 2 for pair_scores in scores_by_opening):
        raise ValueError("Each opening must have exactly one game per color")
    if any(set(colors) != {"RED", "BLACK"} for colors in colors_by_opening):
        raise ValueError("Each opening must be played once with depth 4 as Red and once as Black")
    return {
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "depth4_red": depth4_red,
        "depth4_black": depth4_black,
        "scores_by_opening": scores_by_opening,
    }


def _bootstrap_paired_score(scores_by_opening, samples=20000, seed=0):
    rng = random.Random(seed)
    pair_scores = [sum(scores) / 2 for scores in scores_by_opening]
    estimates = sorted(
        sum(pair_scores[rng.randrange(len(pair_scores))] for _ in pair_scores)
        / len(pair_scores)
        for _ in range(samples)
    )
    return estimates[int(0.025 * (samples - 1))], estimates[int(0.975 * (samples - 1))]


def _elo(score_rate):
    return 400 * math.log10(score_rate / (1 - score_rate)) if 0 < score_rate < 1 else None


def _config_for_depth(records, depth):
    for record in records:
        for side in ("red_config", "black_config"):
            config = record.get(side, {})
            if config.get("depth") == depth:
                result = dict(config)
                result["depth"] = depth
                return result
    return {
        "engine": "search",
        "depth": depth,
        "use_mobility": False,
        "use_pawn_structure": False,
        "use_piece_coordination": False,
        "use_endgame_heuristics": False,
        "use_killer_moves": True,
        "use_mvv_lva": False,
        "use_opening_book": False,
        "use_neural_eval": False,
        "use_calibrated_material": False,
        "use_calibrated_weights": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="source JSONL containing legal games")
    parser.add_argument("--output", required=True, help="new merged JSONL output path")
    parser.add_argument("--opening-count", type=int, default=10)
    parser.add_argument("--opening-plies", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260929)
    parser.add_argument("--max-moves", type=int, default=150)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    args = parser.parse_args()
    if args.max_moves < 1 or args.workers < 1:
        parser.error("--max-moves and --workers must be positive")

    source = pathlib.Path(args.source)
    output = pathlib.Path(args.output)
    if output.exists():
        parser.error(f"output already exists: {output}")
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    if manifest_path.exists():
        parser.error(f"opening manifest already exists: {manifest_path}")
    source_records = load_records(source)
    openings = select_paired_openings(
        source_records, args.opening_count, args.opening_plies, args.seed
    )
    depth4_config = _config_for_depth(source_records, 4)
    depth3_config = _config_for_depth(source_records, 3)
    print(
        "No depth-specific engine configurations found in source; "
        "using baseline SearchEngine settings."
        if not any(
            config.get("depth") in (3, 4)
            for record in source_records
            for config in (record.get("red_config", {}), record.get("black_config", {}))
        )
        else "Using depth-3 and depth-4 SearchEngine configurations from source records.",
        flush=True,
    )

    game_specs = [
        (game_index, openings[game_index // 2])
        for game_index in range(2 * len(openings))
    ]
    print(
        f"Running {len(game_specs)} paired games on {len(openings)} openings "
        f"with {args.workers} workers; seed={args.seed}",
        flush=True,
    )
    started = time.monotonic()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="alphazeta-paired-") as temp_dir:
        shard_dir = pathlib.Path(temp_dir)
        completed = []
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    _play_one_game,
                    game_index,
                    opening,
                    args.max_moves,
                    depth4_config,
                    depth3_config,
                    str(shard_dir / f"game-{game_index:04d}.jsonl"),
                ): game_index
                for game_index, opening in game_specs
            }
            for future in as_completed(futures):
                game_index, result, moves = future.result()
                completed.append(game_index)
                print(
                    f"Completed {len(completed):>3}/{len(game_specs)} "
                    f"(opening {game_index // 2 + 1}, depth4 "
                    f"{'Red' if game_index % 2 == 0 else 'Black'}): "
                    f"{result}, {moves} plies",
                    flush=True,
                )

        if len(completed) != len(game_specs):
            raise RuntimeError("Not all paired games completed")
        records = []
        for game_index, _ in game_specs:
            shard_path = shard_dir / f"game-{game_index:04d}.jsonl"
            shard_records = load_records(shard_path)
            if len(shard_records) != 1:
                raise ValueError(f"Expected one record in {shard_path}")
            records.extend(shard_records)

        stats = _validate_records(records, openings, args.max_moves)
        score_rate = (stats["wins"] + 0.5 * stats["draws"]) / len(records)
        ci = _bootstrap_paired_score(stats["scores_by_opening"], seed=args.seed)
        manifest = {
            "source": str(source),
            "seed": args.seed,
            "opening_plies": args.opening_plies,
            "openings": openings,
            "pairing": "each opening played twice; depth 4 alternates Red then Black",
        }
        with output.with_suffix(output.suffix + ".tmp").open("w", encoding="utf-8") as merged:
            for record in records:
                merged.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        os.replace(output.with_suffix(output.suffix + ".tmp"), output)
        with manifest_path.open("w", encoding="utf-8") as manifest_file:
            json.dump(manifest, manifest_file, ensure_ascii=False, indent=2)
            manifest_file.write("\n")

    elo_ci = (_elo(ci[0]), _elo(ci[1]))
    print(
        f"Depth-4 W/L/D={stats['wins']}/{stats['losses']}/{stats['draws']}; "
        f"score={score_rate:.1%}; paired bootstrap 95% CI={ci[0]:.1%}..{ci[1]:.1%}",
        flush=True,
    )
    elo_point = _elo(score_rate)
    elo_text = f"{elo_point:+.0f}" if elo_point is not None else "undefined"
    elo_ci_text = (
        f"{elo_ci[0]:+.0f}..{elo_ci[1]:+.0f}"
        if elo_ci[0] is not None and elo_ci[1] is not None
        else "undefined"
    )
    print(
        f"Depth 4 as Red W/L/D={stats['depth4_red']['wins']}/"
        f"{stats['depth4_red']['losses']}/{stats['depth4_red']['draws']}; "
        f"as Black={stats['depth4_black']['wins']}/"
        f"{stats['depth4_black']['losses']}/{stats['depth4_black']['draws']}; "
        f"Elo={elo_text}, Elo CI={elo_ci_text}",
        flush=True,
    )
    print(f"Validated records: {output}; opening manifest: {manifest_path}", flush=True)
    print(f"Elapsed: {(time.monotonic() - started) / 60:.1f} minutes", flush=True)


if __name__ == "__main__":
    main()

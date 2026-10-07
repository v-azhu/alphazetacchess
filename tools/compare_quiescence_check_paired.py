"""Compare capture-only and quiet-check quiescence on paired openings.

Run from the repository root:
    python tools/compare_quiescence_check_paired.py \
        --source data/external_games.jsonl \
        --output data/v0.10_qchecks_vs_capture_only_500ms_10pairs.jsonl

Every opening is played twice with colors swapped. Search is time-limited per
move; records are replay-validated as each game finishes.
"""

import argparse
import json
import math
import random
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.selfplay.paired_openings import select_paired_openings
from alphazetacchess.selfplay.recorder import append_record, load_records, play_recorded_game


class TimedSearch:
    def __init__(self, movetime_ms, depth_cap, check_plies):
        self.engine = SearchEngine(
            depth=depth_cap,
            quiescence_check_plies=check_plies,
        )
        self.movetime_ms = movetime_ms
        self.stats = []

    def choose_move(self, board, color):
        stop_event = threading.Event()
        timer = threading.Timer(self.movetime_ms / 1000, stop_event.set)
        started = time.monotonic()
        timer.start()
        try:
            result = self.engine.choose_move(board, color, stop_event=stop_event)
            self.stats.append({
                "depth": result.depth,
                "nodes": result.nodes_evaluated,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            })
            return result
        finally:
            timer.cancel()
            timer.join()


def validate_game(record, max_moves):
    board = board_from_fen(record["initial_fen"])
    moves = record["moves"]
    if record["total_moves"] != len(moves):
        raise ValueError("Recorded move count does not match the move list")
    for ply, raw_move in enumerate(moves, start=1):
        if Rule.is_game_over(board, board.current_player):
            raise ValueError(f"Game continued after a terminal position at ply {ply}")
        if raw_move["color"] != board.current_player.name:
            raise ValueError(f"Wrong side to move at ply {ply}")
        move = Move(tuple(raw_move["from"]), tuple(raw_move["to"]))
        if not Rule.is_legal_move(board, move, board.current_player):
            raise ValueError(f"Illegal move at ply {ply}: {raw_move}")
        board.move(move.from_pos, move.to_pos)

    is_terminal = Rule.is_game_over(board, board.current_player)
    if len(moves) == max_moves and not is_terminal:
        if record["result"] != "DRAW":
            raise ValueError("Non-terminal move-limit result must be a draw")
    elif not is_terminal:
        raise ValueError("Game ended before a terminal result or move limit")
    else:
        winner = "BLACK_WINS" if board.current_player == Color.RED else "RED_WINS"
        if record["result"] != winner:
            raise ValueError("Recorded result does not match the terminal position")


def paired_bootstrap(scores, seed, samples=20000):
    rng = random.Random(seed)
    pair_scores = [sum(pair) / 2 for pair in scores]
    estimates = sorted(
        sum(pair_scores[rng.randrange(len(pair_scores))] for _ in pair_scores)
        / len(pair_scores)
        for _ in range(samples)
    )
    return estimates[int(0.025 * (samples - 1))], estimates[int(0.975 * (samples - 1))]


def score(result, variant_color):
    if result == "DRAW":
        return 0.5
    variant_won = result == ("RED_WINS" if variant_color == "RED" else "BLACK_WINS")
    return 1.0 if variant_won else 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--opening-count", type=int, default=10)
    parser.add_argument("--opening-plies", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20261006)
    parser.add_argument("--movetime-ms", type=int, default=500)
    parser.add_argument("--depth-cap", type=int, default=64)
    parser.add_argument("--max-moves", type=int, default=150)
    args = parser.parse_args()
    if min(args.opening_count, args.opening_plies, args.movetime_ms, args.depth_cap, args.max_moves) < 1:
        parser.error("opening count, opening plies, time, depth cap, and move limit must be positive")
    if args.opening_plies % 2:
        parser.error("--opening-plies must be even so every opening starts with Red to move")

    source = Path(args.source)
    output = Path(args.output)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    if output.exists() or manifest_path.exists():
        parser.error("output JSONL or manifest already exists")
    records = load_records(source)
    candidates = select_paired_openings(
        records,
        max(args.opening_count * 5, args.opening_count),
        args.opening_plies,
        args.seed,
    )
    excluded_fens = set()
    prior_manifests = (
        ROOT / "data/v0.10_aspiration_vs_full_window_500ms_10pairs.jsonl.manifest.json",
        ROOT / "data/v0.10_qchecks_vs_capture_only_500ms_10pairs.jsonl.manifest.json",
    )
    for prior_manifest in prior_manifests:
        if not prior_manifest.exists():
            continue
        excluded_fens.update(
            item["initial_fen"] for item in json.loads(prior_manifest.read_text())["openings"]
        )
    openings = [
        opening for opening in candidates
        if opening["initial_fen"] not in excluded_fens
    ][:args.opening_count]
    if len(openings) != args.opening_count:
        raise ValueError("Could not select enough openings disjoint from the aspiration match")
    for index, opening in enumerate(openings):
        opening["opening_index"] = index

    output.parent.mkdir(parents=True, exist_ok=True)
    paired_scores = [[] for _ in openings]
    wins = losses = draws = 0
    with output.open("x", encoding="utf-8") as records_file:
        for game_index in range(2 * len(openings)):
            opening_index = game_index // 2
            variant_color = "RED" if game_index % 2 == 0 else "BLACK"
            base = TimedSearch(args.movetime_ms, args.depth_cap, 0)
            variant = TimedSearch(args.movetime_ms, args.depth_cap, 1)
            red_engine, black_engine = (
                (variant, base) if variant_color == "RED" else (base, variant)
            )
            record = play_recorded_game(
                red_engine,
                black_engine,
                args.max_moves,
                red_config={
                    "engine": "search",
                    "quiescence_check_plies": 1 if variant_color == "RED" else 0,
                    "movetime_ms": args.movetime_ms,
                    "depth_cap": args.depth_cap,
                },
                black_config={
                    "engine": "search",
                    "quiescence_check_plies": 1 if variant_color == "BLACK" else 0,
                    "movetime_ms": args.movetime_ms,
                    "depth_cap": args.depth_cap,
                },
                board=board_from_fen(openings[opening_index]["initial_fen"]),
            )
            record["initial_fen"] = openings[opening_index]["initial_fen"]
            record["opening_index"] = opening_index
            record["variant_color"] = variant_color
            record["search_stats"] = {
                "capture_only": base.stats,
                "quiet_check": variant.stats,
            }
            validate_game(record, args.max_moves)
            records_file.write(json.dumps(record, separators=(",", ":")) + "\n")
            records_file.flush()
            result_score = score(record["result"], variant_color)
            paired_scores[opening_index].append(result_score)
            if result_score == 1:
                wins += 1
            elif result_score == 0:
                losses += 1
            else:
                draws += 1
            print(
                f"{game_index + 1}/{2 * len(openings)} opening={opening_index + 1} "
                f"quiet-check={variant_color} result={record['result']} "
                f"plies={record['total_moves']}",
                flush=True,
            )

    score_rate = (wins + 0.5 * draws) / (2 * len(openings))
    interval = paired_bootstrap(paired_scores, args.seed)
    manifest = {
        "source": str(source),
        "seed": args.seed,
        "opening_plies": args.opening_plies,
        "movetime_ms": args.movetime_ms,
        "depth_cap": args.depth_cap,
        "max_moves": args.max_moves,
        "openings": openings,
        "pairing": "each opening played once with quiet-check search as Red and once as Black",
        "paired_scores": paired_scores,
        "score_rate": score_rate,
        "paired_bootstrap_95_percent": interval,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    elo = 400 * math.log10(score_rate / (1 - score_rate)) if 0 < score_rate < 1 else None
    print(
        f"quiet-check W/L/D={wins}/{losses}/{draws}; score={score_rate:.1%}; "
        f"paired 95% CI={interval[0]:.1%}..{interval[1]:.1%}; Elo={elo}",
        flush=True,
    )


if __name__ == "__main__":
    main()

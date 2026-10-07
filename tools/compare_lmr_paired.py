"""Compare experimental late-move reductions against baseline search.

Run from the repository root:
    python tools/compare_lmr_paired.py --source data/external_games.jsonl \
        --output data/v0.10_lmr_vs_baseline_3s_8pairs.jsonl \
        --opening-count 8 --movetime-ms 3000

Each opening is played twice with colors swapped. Search is time-limited per
move, and each completed game is replay-validated before it is recorded.
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
from alphazetacchess.selfplay.recorder import load_records, play_recorded_game


class TimedSearch:
    def __init__(self, movetime_ms, depth_cap, use_lmr):
        self.engine = SearchEngine(
            depth=depth_cap,
            use_late_move_reductions=use_lmr,
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
                "lmr_reductions": self.engine.late_move_reductions,
                "lmr_researches": self.engine.late_move_researches,
            })
            return result
        finally:
            timer.cancel()
            timer.join()


def validate_game(record, max_moves):
    board = board_from_fen(record["initial_fen"])
    moves = record["moves"]
    if record["total_moves"] != len(moves):
        raise ValueError("Recorded move count does not match move list")
    for ply, raw_move in enumerate(moves, start=1):
        if Rule.is_game_over(board, board.current_player):
            raise ValueError(f"Game continued after terminal position at ply {ply}")
        if raw_move["color"] != board.current_player.name:
            raise ValueError(f"Wrong side to move at ply {ply}")
        move = Move(tuple(raw_move["from"]), tuple(raw_move["to"]))
        if not Rule.is_legal_move(board, move, board.current_player):
            raise ValueError(f"Illegal move at ply {ply}: {raw_move}")
        board.move(move.from_pos, move.to_pos)

    terminal = Rule.is_game_over(board, board.current_player)
    if len(moves) == max_moves and not terminal:
        if record["result"] != "DRAW":
            raise ValueError("Non-terminal move-limit result must be a draw")
    elif not terminal:
        raise ValueError("Game ended before a terminal result or move limit")
    else:
        winner = "BLACK_WINS" if board.current_player == Color.RED else "RED_WINS"
        if record["result"] != winner:
            raise ValueError("Recorded result does not match terminal position")


def paired_bootstrap(scores, seed, samples=20000):
    rng = random.Random(seed)
    paired_scores = [sum(pair) / 2 for pair in scores]
    estimates = sorted(
        sum(paired_scores[rng.randrange(len(paired_scores))] for _ in paired_scores)
        / len(paired_scores)
        for _ in range(samples)
    )
    return estimates[int(0.025 * (samples - 1))], estimates[int(0.975 * (samples - 1))]


def variant_score(result, variant_color):
    if result == "DRAW":
        return 0.5
    return float(result == ("RED_WINS" if variant_color == "RED" else "BLACK_WINS"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--opening-count", type=int, default=8)
    parser.add_argument("--opening-plies", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--movetime-ms", type=int, default=3000)
    parser.add_argument("--depth-cap", type=int, default=64)
    parser.add_argument("--max-moves", type=int, default=150)
    args = parser.parse_args()
    if min(args.opening_count, args.opening_plies, args.movetime_ms, args.depth_cap, args.max_moves) < 1:
        parser.error("all counts, time limits, depth cap, and move limit must be positive")
    if args.opening_plies % 2:
        parser.error("--opening-plies must be even")

    source = Path(args.source)
    output = Path(args.output)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    if output.exists() or manifest_path.exists():
        parser.error("output JSONL or manifest already exists")

    source_records = load_records(source)
    candidates = select_paired_openings(
        source_records,
        args.opening_count * 12,
        args.opening_plies,
        args.seed,
    )
    excluded = set()
    for manifest in ROOT.glob("data/v0.10_*pairs.jsonl.manifest.json"):
        excluded.update(
            item["initial_fen"] for item in json.loads(manifest.read_text())["openings"]
        )
    openings = [
        item for item in candidates if item["initial_fen"] not in excluded
    ][:args.opening_count]
    if len(openings) != args.opening_count:
        raise ValueError("Could not select enough openings disjoint from prior samples")
    for index, opening in enumerate(openings):
        opening["opening_index"] = index

    output.parent.mkdir(parents=True, exist_ok=True)
    scores_by_opening = [[] for _ in openings]
    wins = losses = draws = 0
    with output.open("x", encoding="utf-8") as records_file:
        for game_index in range(2 * len(openings)):
            opening_index = game_index // 2
            variant_color = "RED" if game_index % 2 == 0 else "BLACK"
            baseline = TimedSearch(args.movetime_ms, args.depth_cap, False)
            lmr = TimedSearch(args.movetime_ms, args.depth_cap, True)
            red_engine, black_engine = (
                (lmr, baseline) if variant_color == "RED" else (baseline, lmr)
            )
            record = play_recorded_game(
                red_engine,
                black_engine,
                args.max_moves,
                red_config={
                    "engine": "search",
                    "use_late_move_reductions": variant_color == "RED",
                    "movetime_ms": args.movetime_ms,
                    "depth_cap": args.depth_cap,
                },
                black_config={
                    "engine": "search",
                    "use_late_move_reductions": variant_color == "BLACK",
                    "movetime_ms": args.movetime_ms,
                    "depth_cap": args.depth_cap,
                },
                board=board_from_fen(openings[opening_index]["initial_fen"]),
            )
            record["initial_fen"] = openings[opening_index]["initial_fen"]
            record["opening_index"] = opening_index
            record["variant_color"] = variant_color
            record["search_stats"] = {
                "baseline": baseline.stats,
                "lmr": lmr.stats,
            }
            validate_game(record, args.max_moves)
            records_file.write(json.dumps(record, separators=(",", ":")) + "\n")
            records_file.flush()

            score = variant_score(record["result"], variant_color)
            scores_by_opening[opening_index].append(score)
            if score == 1:
                wins += 1
            elif score == 0:
                losses += 1
            else:
                draws += 1
            print(
                f"{game_index + 1}/{2 * len(openings)} opening={opening_index + 1} "
                f"LMR={variant_color} result={record['result']} "
                f"plies={record['total_moves']}",
                flush=True,
            )

    score_rate = (wins + 0.5 * draws) / (2 * len(openings))
    interval = paired_bootstrap(scores_by_opening, args.seed)
    manifest = {
        "source": str(source),
        "seed": args.seed,
        "opening_plies": args.opening_plies,
        "movetime_ms": args.movetime_ms,
        "depth_cap": args.depth_cap,
        "max_moves": args.max_moves,
        "openings": openings,
        "pairing": "each opening played once with LMR search as Red and once as Black",
        "paired_scores": scores_by_opening,
        "score_rate": score_rate,
        "paired_bootstrap_95_percent": interval,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    elo = 400 * math.log10(score_rate / (1 - score_rate)) if 0 < score_rate < 1 else None
    print(
        f"LMR W/L/D={wins}/{losses}/{draws}; score={score_rate:.1%}; "
        f"paired 95% CI={interval[0]:.1%}..{interval[1]:.1%}; Elo={elo}",
        flush=True,
    )


if __name__ == "__main__":
    main()

"""Run complete depth-one and depth-two searches on AZ-FALLBACK-25."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.engine.search import SearchEngine


DEFAULT_INPUT = ROOT / "data" / "suites" / "az_fallback_25.json"
DEFAULT_OUTPUT = ROOT / "data" / "suites" / "az_fallback_25.measurements.json"


def git_revision():
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def machine_info():
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "processor": platform.processor() or None,
        "logical_cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "git_revision": git_revision(),
    }


def measure_position(position, depths=(1, 2)):
    measurements = {}
    for depth in depths:
        board = board_from_fen(position["position_fen"])
        started = time.perf_counter()
        result = SearchEngine(depth=depth).choose_move(board, board.current_player)
        elapsed = time.perf_counter() - started
        if result.depth != depth or result.best_move is None:
            raise RuntimeError(
                f"Incomplete depth-{depth} search for game {position.get('game_index')} "
                f"ply {position.get('game_ply')}: result depth={result.depth}"
            )
        measurements[str(depth)] = {
            "depth": result.depth,
            "nodes": result.nodes_evaluated,
            "elapsed_seconds": round(elapsed, 6),
            "score_cp": result.score,
            "best_move": GameRecord.move_to_iccs(result.best_move),
        }
    return measurements


def load_suite(path):
    with Path(path).open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data.get("positions"), list):
        raise ValueError("Fallback suite must contain a positions array")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"input file does not exist: {args.input}")
    suite = load_suite(args.input)
    positions = []
    for index, position in enumerate(suite["positions"], start=1):
        positions.append({
            **position,
            "measurements": measure_position(position),
        })
        print(f"Measured {index}/{len(suite['positions'])}", flush=True)

    result = {
        "format": "alphazeta-az-fallback-measurements-v1",
        "source_suite": args.input.name,
        "machine": machine_info(),
        "search": {
            "engine": "alphazetacchess.engine.search.SearchEngine",
            "configuration": "default constructor settings; complete fixed depth",
        },
        "positions": positions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as target:
        json.dump(result, target, indent=2, sort_keys=True)
        target.write("\n")
    print(f"Saved measurements to {args.output}")


if __name__ == "__main__":
    main()

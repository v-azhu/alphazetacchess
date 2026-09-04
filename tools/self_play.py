"""
AlphaZetaChess self-play data collection tool (V0.5.1).

Runs N self-play games (SearchEngine vs SearchEngine, same
configuration on both sides by default) and appends each game's full
move-by-move record to a JSON-lines file for later analysis --
V0.5.2's planned opening book, V0.5.3's planned endgame heuristics,
V0.5.4's planned strength comparison between configurations.

Usage:
    python tools/self_play.py --games 20 --depth 2 --output data/selfplay.jsonl
    python tools/self_play.py --games 10 --depth 2 --use-mobility --use-pawn-structure
    python tools/self_play.py --games 20 --depth 2 --random-opening-prob 0  # no randomization

Each line of the output file is one game record (see
alphazetacchess.selfplay.recorder for the exact format). The file is
appended to, not overwritten, so multiple runs accumulate data over
time -- this is meant to be run repeatedly, including across sessions.

Opening randomization is ON by default (see
alphazetacchess.selfplay.opening_randomization): a fully deterministic
SearchEngine playing itself always makes identical moves from
identical positions, so naive self-play from the fixed starting
position produces byte-for-byte identical games every time -- confirmed
directly from a real 10-game batch, see docs/v0.5.3-data-check.md. For
the first --random-opening-plies plies, each side has
--random-opening-prob probability of playing a uniformly random legal
move instead of the engine's own choice, so games actually diverge.
Pass --random-opening-prob 0 to disable and get pure, fully
deterministic self-play instead (useful for reproducing/debugging a
specific line, not for building a diverse data set).

Performance note: at depth 2, a single game commonly takes 1-3 minutes
depending on how decisive it is (see docs/v0.3.4.md and
docs/v0.4.3_beta3-results.md for related per-move timing data) --
running a meaningfully large batch (dozens+ games) is a local,
long-running task by design, not something to run inside a single
interactive session. Start with a small --games count to sanity check
your configuration before committing to a big run.
"""

import argparse
import os
import sys
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.selfplay.recorder import play_recorded_game, append_record
from alphazetacchess.selfplay.opening_randomization import RandomizedOpeningEngine


def build_engine(config):
    engine = SearchEngine(
        depth=config["depth"],
        use_mobility=config["use_mobility"],
        use_pawn_structure=config["use_pawn_structure"],
        use_piece_coordination=config["use_piece_coordination"],
    )

    if config["random_opening_plies"] > 0 and config["random_opening_prob"] > 0:
        engine = RandomizedOpeningEngine(
            engine,
            random_plies=config["random_opening_plies"],
            random_prob=config["random_opening_prob"],
        )

    return engine


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--games", type=int, default=10, help="number of games to play")
    parser.add_argument("--depth", type=int, default=2, help="SearchEngine search depth")
    parser.add_argument("--max-moves", type=int, default=150, help="per-game move limit")
    parser.add_argument(
        "--output", default="data/selfplay.jsonl", help="JSON-lines file to append records to"
    )
    parser.add_argument("--use-mobility", action="store_true")
    parser.add_argument("--use-pawn-structure", action="store_true")
    parser.add_argument("--use-piece-coordination", action="store_true")
    parser.add_argument(
        "--random-opening-plies", type=int, default=10,
        help="number of leading plies eligible for a random move (0 disables)",
    )
    parser.add_argument(
        "--random-opening-prob", type=float, default=0.3,
        help="probability of a random move on each eligible ply (0 disables)",
    )
    args = parser.parse_args()

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    config = {
        "depth": args.depth,
        "use_mobility": args.use_mobility,
        "use_pawn_structure": args.use_pawn_structure,
        "use_piece_coordination": args.use_piece_coordination,
        "random_opening_plies": args.random_opening_plies,
        "random_opening_prob": args.random_opening_prob,
    }

    print(f"AlphaZetaChess self-play: {args.games} games, config={config}")
    print(f"Appending records to {args.output}\n")

    started = time.time()
    results = {"RED_WINS": 0, "BLACK_WINS": 0, "DRAW": 0}

    for i in range(args.games):
        engine_red = build_engine(config)
        engine_black = build_engine(config)

        game_started = time.time()
        record = play_recorded_game(
            engine_red, engine_black, args.max_moves,
            red_config=config, black_config=config,
        )
        game_elapsed = time.time() - game_started

        append_record(args.output, record)
        results[record["result"]] += 1

        print(
            f"  game {i + 1:>4}/{args.games}: {record['result']:<11} "
            f"({record['total_moves']:>3} moves, {game_elapsed:6.1f}s)"
        )

    elapsed = time.time() - started
    print()
    print(f"Done in {elapsed:.1f}s. Results: {results}")
    print(f"Records appended to {args.output}")


if __name__ == "__main__":
    main()

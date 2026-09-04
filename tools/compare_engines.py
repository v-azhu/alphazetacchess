"""
AlphaZetaChess engine strength comparison tool (V0.5.4).

Plays N games between two independently configurable SearchEngine
setups (search depth, which V0.4.x/V0.5.3 evaluation terms are on,
opening randomization) and reports win/draw/loss counts plus an
Elo-style difference estimate -- the "SearchEngine-vs-SearchEngine"
extension of tools/benchmark.py's SearchEngine-vs-RandomEngine sanity
check, using the same Engine Benchmark methodology
(docs/roadmap.md section 3 / docs/design/engine-design.md section 10).

Every game is a full V0.5.1 self-play record under the hood, so
--output can point at the same data/selfplay.jsonl corpus used by
tools/build_opening_book.py and tools/analyze_endgame.py -- a
strength-comparison run and a self-play data-collection run are not
mutually exclusive, they can be the same run.

Usage:
    python tools/compare_engines.py --a-depth 2 --b-depth 3 --games 10
    python tools/compare_engines.py --a-use-mobility --games 20
    python tools/compare_engines.py --a-use-endgame-heuristics --games 20 --output data/selfplay.jsonl

Performance note: same as tools/self_play.py -- at depth 2, individual
games commonly take 1-3+ minutes, so a statistically meaningful batch
(dozens of games) is a local, long-running task by design. Start with
a small --games count to sanity check your configuration first.
"""

import argparse
import os
import sys
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.selfplay.opening_randomization import RandomizedOpeningEngine
from alphazetacchess.selfplay.strength_comparison import run_comparison_match


def add_side_args(parser, prefix):
    parser.add_argument(f"--{prefix}-depth", type=int, default=2)
    parser.add_argument(f"--{prefix}-use-mobility", action="store_true")
    parser.add_argument(f"--{prefix}-use-pawn-structure", action="store_true")
    parser.add_argument(f"--{prefix}-use-piece-coordination", action="store_true")
    parser.add_argument(f"--{prefix}-use-endgame-heuristics", action="store_true")


def config_from_args(args, prefix):
    return {
        "depth": getattr(args, f"{prefix}_depth"),
        "use_mobility": getattr(args, f"{prefix}_use_mobility"),
        "use_pawn_structure": getattr(args, f"{prefix}_use_pawn_structure"),
        "use_piece_coordination": getattr(args, f"{prefix}_use_piece_coordination"),
        "use_endgame_heuristics": getattr(args, f"{prefix}_use_endgame_heuristics"),
    }


def build_engine(config, random_opening_plies, random_opening_prob):
    engine = SearchEngine(
        depth=config["depth"],
        use_mobility=config["use_mobility"],
        use_pawn_structure=config["use_pawn_structure"],
        use_piece_coordination=config["use_piece_coordination"],
        use_endgame_heuristics=config["use_endgame_heuristics"],
    )

    if random_opening_plies > 0 and random_opening_prob > 0:
        engine = RandomizedOpeningEngine(
            engine, random_plies=random_opening_plies, random_prob=random_opening_prob,
        )

    return engine


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--games", type=int, default=10, help="number of games to play")
    parser.add_argument("--max-moves", type=int, default=150, help="per-game move limit")
    parser.add_argument(
        "--output", default=None,
        help="optional JSON-lines file to append every game's full record to "
             "(same format as tools/self_play.py -- reusable by build_opening_book.py "
             "/ analyze_endgame.py)",
    )
    parser.add_argument(
        "--random-opening-plies", type=int, default=10,
        help="number of leading plies eligible for a random move (0 disables)",
    )
    parser.add_argument(
        "--random-opening-prob", type=float, default=0.3,
        help="probability of a random move on each eligible ply (0 disables)",
    )
    add_side_args(parser, "a")
    add_side_args(parser, "b")
    args = parser.parse_args()

    a_config = config_from_args(args, "a")
    b_config = config_from_args(args, "b")

    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

    print(f"AlphaZetaChess strength comparison: {args.games} games")
    print(f"  A: {a_config}")
    print(f"  B: {b_config}")
    if args.output:
        print(f"  Appending records to {args.output}")
    print()

    def on_game_complete(i, record, a_is_red):
        result = record["result"]
        if result == "DRAW":
            outcome = "draw (move limit)"
        elif (result == "RED_WINS") == a_is_red:
            outcome = "A wins"
        else:
            outcome = "B wins"
        print(
            f"  game {i + 1:>4}/{args.games}: {outcome:<17} "
            f"({record['total_moves']:>3} moves)"
        )

    started = time.time()
    stats = run_comparison_match(
        engine_a_factory=lambda: build_engine(
            a_config, args.random_opening_plies, args.random_opening_prob
        ),
        engine_b_factory=lambda: build_engine(
            b_config, args.random_opening_plies, args.random_opening_prob
        ),
        games=args.games,
        max_moves=args.max_moves,
        a_config=a_config,
        b_config=b_config,
        output_path=args.output,
        on_game_complete=on_game_complete,
    )
    elapsed = time.time() - started

    print()
    print(f"Results over {stats['games']} games ({elapsed:.1f}s total):")
    print(f"  A wins : {stats['a_wins']}")
    print(f"  B wins : {stats['b_wins']}")
    print(f"  Draws  : {stats['draws']}")
    print(f"  A score rate : {stats['a_score_rate']:.0%}")
    if stats["elo_diff"] is not None:
        print(f"  Estimated Elo difference (A - B) : {stats['elo_diff']:+.0f}")
    else:
        print("  Estimated Elo difference (A - B) : undefined (100%/0% score)")
    if args.output:
        print(f"Records appended to {args.output}")


if __name__ == "__main__":
    main()

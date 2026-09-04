"""
AlphaZetaChess endgame-heuristic analysis tool (V0.5.3).

Reads self-play records produced by tools/self_play.py and reports
whether engine/endgame.py's core hypothesis -- more Rooks and fewer
Cannons at endgame onset correlates with winning -- actually holds up
against recorded data. See docs/v0.5.3.md.

Usage:
    python tools/analyze_endgame.py
    python tools/analyze_endgame.py --input data/selfplay.jsonl
"""

import argparse
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.selfplay.recorder import load_records
from alphazetacchess.selfplay.endgame_analysis import summarize_endgame_outcomes


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input", default="data/selfplay.jsonl")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"No records found at {args.input}. Run tools/self_play.py first.")
        return

    records = load_records(args.input)
    print(f"Loaded {len(records)} game record(s) from {args.input}")

    stats = summarize_endgame_outcomes(records)

    print(f"Reached endgame phase: {stats['reached_endgame']}/{stats['games']} games")
    if stats["avg_onset_ply"] is not None:
        print(f"Average endgame onset ply: {stats['avg_onset_ply']:.1f}")

    decided = (
        stats["edge_favored_wins"]
        + stats["edge_favored_losses"]
        + stats["edge_favored_draws"]
    )
    print(f"Positions with a Rook/Cannon edge at onset: {decided} (tied: {stats['no_edge']})")
    if decided:
        win_rate = stats["edge_favored_wins"] / decided
        print(
            f"  Favored side won {stats['edge_favored_wins']}/{decided} "
            f"({win_rate:.0%}), lost {stats['edge_favored_losses']}, "
            f"drew {stats['edge_favored_draws']}"
        )
        if decided < 20:
            print(
                "  NOTE: sample too small to draw real conclusions -- "
                "collect more self-play data before trusting this number."
            )
    else:
        print("  No decided endgame-onset positions in this corpus yet.")


if __name__ == "__main__":
    main()

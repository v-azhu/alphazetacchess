"""
AlphaZetaChess opening book builder (V0.5.2).

Reads self-play records produced by tools/self_play.py and builds an
opening book (per-position, per-move win/draw/loss statistics for the
first --max-ply half-moves of each game).

Usage:
    python tools/build_opening_book.py
    python tools/build_opening_book.py --input data/selfplay.jsonl --output data/opening_book.json --max-ply 20
"""

import argparse
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.selfplay.recorder import load_records
from alphazetacchess.selfplay.opening_book import build_book_from_records, save_book


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="data/selfplay.jsonl")
    parser.add_argument("--output", default="data/opening_book.json")
    parser.add_argument("--max-ply", type=int, default=20)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"No records found at {args.input}. Run tools/self_play.py first.")
        return

    records = load_records(args.input)
    print(f"Loaded {len(records)} game record(s) from {args.input}")

    book = build_book_from_records(records, max_ply=args.max_ply)
    total_entries = sum(len(moves) for moves in book.values())
    print(f"Built book: {len(book)} unique position(s), {total_entries} position-move entries")

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    save_book(book, args.output)
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()

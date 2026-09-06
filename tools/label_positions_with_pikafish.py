"""
AlphaZetaChess Pikafish position-labeling tool (V0.6.2).

Replays real self-play games (from tools/self_play.py's V0.5.1
records) and asks a locally-running Pikafish (or any UCI-compatible
engine) binary to evaluate a sample of the positions reached, saving
(FEN, score_cp) pairs as training labels for tools/train_neural_eval.py.

This is the ONE step in the V0.6.2 pipeline that needs to run on a
machine with a working Pikafish binary -- everything downstream
(feature extraction, network training) is pure Python/numpy and has
no such dependency. See docs/v0.6.2.md for the full pipeline and why
this project distills from Pikafish's evaluations rather than trying
to port its NNUE weights directly.

Usage:
    python tools/label_positions_with_pikafish.py --pikafish-path /path/to/pikafish
    python tools/label_positions_with_pikafish.py --pikafish-path ./pikafish.exe \\
        --movetime-ms 300 --sample-every 4 --max-positions 5000

Getting a Pikafish binary: download a prebuilt release from
https://github.com/official-pikafish/Pikafish/releases (pick the build
matching your OS/CPU), or build from source. No network file path
needs to be passed here -- Pikafish loads its own default network
automatically.
"""

import argparse
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_to_fen
from alphazetacchess.selfplay.recorder import load_records, append_record
from alphazetacchess.neural.pikafish_client import PikafishClient, mate_score_to_cp


def positions_from_record(record, sample_every):
    """
    Replay one game record's moves, yielding a FEN string every
    `sample_every`-th ply (ply 0 = the starting position). Sampling
    rather than labeling every single ply keeps consecutive, nearly-
    identical positions from dominating the training set, and keeps
    the number of (slow) Pikafish calls proportional to how much
    positional variety actually exists across the corpus.
    """
    board = Board()
    if 0 % sample_every == 0:
        yield board_to_fen(board)

    for ply_index, move_entry in enumerate(record["moves"], start=1):
        from_pos = tuple(move_entry["from"])
        to_pos = tuple(move_entry["to"])
        board.move(from_pos, to_pos)
        if ply_index % sample_every == 0:
            yield board_to_fen(board)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--pikafish-path", required=True, help="path to a Pikafish (or other UCI) executable")
    parser.add_argument("--input", default="data/selfplay.jsonl", help="V0.5.1 self-play records to sample positions from")
    parser.add_argument("--output", default="data/pikafish_labels.jsonl")
    parser.add_argument("--movetime-ms", type=int, default=200, help="think time per position, in milliseconds")
    parser.add_argument("--sample-every", type=int, default=4, help="label every Nth ply of each game")
    parser.add_argument("--max-positions", type=int, default=None, help="stop after labeling this many positions total")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"No records found at {args.input}. Run tools/self_play.py first.")
        return

    records = load_records(args.input)
    print(f"Loaded {len(records)} game record(s) from {args.input}")
    print(f"Starting Pikafish: {args.pikafish_path}")

    client = PikafishClient(args.pikafish_path, movetime_ms=args.movetime_ms)
    labeled_count = 0

    try:
        for game_index, record in enumerate(records):
            for fen in positions_from_record(record, args.sample_every):
                if args.max_positions is not None and labeled_count >= args.max_positions:
                    break

                result = client.evaluate_fen(fen)
                if result["score_cp"] is not None:
                    score_cp = result["score_cp"]
                elif result["mate_in"] is not None:
                    score_cp = mate_score_to_cp(result["mate_in"])
                else:
                    continue  # engine gave neither -- skip rather than guess

                append_record(args.output, {"fen": fen, "score_cp": score_cp})
                labeled_count += 1

                if labeled_count % 50 == 0:
                    print(f"  labeled {labeled_count} position(s)... (game {game_index + 1}/{len(records)})")

            if args.max_positions is not None and labeled_count >= args.max_positions:
                break
    finally:
        client.close()

    print(f"Done. {labeled_count} labeled position(s) written to {args.output}")


if __name__ == "__main__":
    main()

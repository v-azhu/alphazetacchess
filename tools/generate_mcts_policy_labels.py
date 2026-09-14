"""
AlphaZetaChess self-play policy label generator (V0.9.6).

Plays MCTSEngine against itself and records, at each position, the
search's OWN most-visited root move as a policy training label --
`{fen, score_cp, best_move}`, the *exact same* format
`tools/label_positions_with_pikafish.py` produces and
`tools/train_policy_network.py` already consumes, so no changes to
the training tool are needed.

This is the real AlphaZero-style training signal `docs/v0.9.4.md`'s
two rounds of Pikafish-imitation training identified as the more
promising untried direction, after finding that imitating an external
engine's independent move preference didn't transfer into a better
PUCT prior for this specific, weak, shallow-leaf-evaluation MCTS (see
that doc's "Round 2" section). The label source here is different in
kind, not just degree: instead of "what would a much stronger,
independent engine play here," each label is "what did THIS search,
with THIS leaf evaluation, actually conclude was best after N
simulations" -- training the policy toward the search's own refined
opinion rather than an external one, which is what real AlphaZero-
style self-play distillation actually does. Unlike the Pikafish
labeling pipeline, this needs no external engine or user-local
setup at all -- MCTSEngine already IS the label source.

`score_cp` is populated from the root's own value estimate
(un-squashed back through atanh, since MCTSEngine's internal values
are tanh-squashed -- see engine/mcts.py's module docstring) purely for
schema compatibility with the shared label format; the policy target
(`best_move`) doesn't depend on it.

Usage:
    python tools/generate_mcts_policy_labels.py --games 20 --simulations 200 \\
        --output data/mcts_policy_labels.jsonl
"""

import argparse
import math
import os
import sys
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.core.fen import board_to_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.engine.mcts import MCTSEngine
from alphazetacchess.selfplay.recorder import append_record


def unsquash(value, value_scale):
    """Inverse of engine/mcts.py's _squash: value_scale * atanh(value),
    clamped away from +/-1 where atanh diverges (a root value can
    legitimately reach exactly +/-1 for a clearly winning/losing
    position after enough simulations)."""
    clamped = max(-0.999999, min(0.999999, value))
    return value_scale * math.atanh(clamped)


def play_one_game(engine, max_moves, random_opening_plies, random_opening_prob, rng):
    """Plays one self-play game, MCTSEngine against itself, recording
    a policy label at every move (not a sampled subset -- unlike the
    Pikafish labeling tool, there's no external cost per position
    here, so there's no reason to skip any). Returns
    (labels, result_string, total_moves).

    Early plies get the same random-move-with-probability opening
    randomization `selfplay/opening_randomization.py` already uses for
    SearchEngine self-play, applied by hand here rather than via
    RandomizedOpeningEngine, since a random move still needs its own
    policy label recorded honestly: recording "the search's actual
    choice was X" as the label even on a ply where a random move gets
    played instead (for game-diversity reasons) reflects what the
    search actually concluded, rather than misrepresenting the random
    move as if it were the search's own preference.
    """
    board = Board()
    labels = []
    moves_played = 0

    while moves_played < max_moves:
        current = board.current_player

        if Rule.is_game_over(board, current):
            result = "BLACK_WINS" if current == Color.RED else "RED_WINS"
            return labels, result, moves_played

        legal_moves = Rule.generate_legal_moves(board, current)

        root, _, completed = engine.search_root(board, current)
        if root is not None and root.expanded:
            best_move, best_child = max(
                root.children.items(), key=lambda item: item[1].visit_count
            )
            root_value = (
                best_child.value_sum / best_child.visit_count
                if best_child.visit_count > 0 else 0.0
            )
            score_cp = round(unsquash(root_value, engine.value_scale))
            fen = board_to_fen(board)
            best_move_str = GameRecord.move_to_iccs(best_move)
            labels.append({"fen": fen, "score_cp": score_cp, "best_move": best_move_str})
        else:
            best_move = legal_moves[0]

        if moves_played < random_opening_plies and rng.random() < random_opening_prob:
            move_to_play = legal_moves[rng.randrange(len(legal_moves))]
        else:
            move_to_play = best_move

        board.move(move_to_play.from_pos, move_to_play.to_pos)
        moves_played += 1

    return labels, "DRAW", moves_played


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--simulations", type=int, default=200, help="MCTSEngine simulation budget per move")
    parser.add_argument("--max-moves", type=int, default=150)
    parser.add_argument("--output", default="data/mcts_policy_labels.jsonl")
    parser.add_argument(
        "--random-opening-plies", type=int, default=10,
        help="number of leading plies eligible for a random move (0 disables) -- "
             "see play_one_game's own docstring for why the recorded label still "
             "reflects the search's real choice even on a randomized ply",
    )
    parser.add_argument("--random-opening-prob", type=float, default=0.3)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    import random
    rng = random.Random(args.seed)

    print(
        f"AlphaZetaChess MCTS self-play policy label generation: {args.games} games, "
        f"{args.simulations} simulations/move"
    )
    print(f"Appending records to {args.output}\n")

    started = time.time()
    results = {"RED_WINS": 0, "BLACK_WINS": 0, "DRAW": 0}
    total_labels = 0

    for i in range(args.games):
        engine = MCTSEngine(simulations=args.simulations)
        game_started = time.time()
        labels, result, total_moves = play_one_game(
            engine, args.max_moves, args.random_opening_plies, args.random_opening_prob, rng
        )
        game_elapsed = time.time() - game_started

        for label in labels:
            append_record(args.output, label)
        total_labels += len(labels)
        results[result] += 1

        print(
            f"  game {i + 1:>4}/{args.games}: {result:<11} "
            f"({total_moves:>3} moves, {len(labels):>3} labels, {game_elapsed:6.1f}s)"
        )

    elapsed = time.time() - started
    print()
    print(f"Done in {elapsed:.1f}s. Results: {results}")
    print(f"{total_labels} label(s) appended to {args.output}")


if __name__ == "__main__":
    main()

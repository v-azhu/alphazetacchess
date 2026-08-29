"""
AlphaZetaChess engine benchmark tool.

Implements the "Engine Benchmark" methodology described in
docs/roadmap.md (section 3) and docs/design/engine-design.md
(section 10): play N games between two engines and report win /
draw / loss counts plus a rough Elo-difference estimate.

Usage:
    python tools/benchmark.py
    python tools/benchmark.py --games 20 --depth 2
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
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.engine.random_engine import RandomEngine


def play_game(engine_red, engine_black, max_moves):
    board = Board()
    engines = {Color.RED: engine_red, Color.BLACK: engine_black}
    moves = 0

    while moves < max_moves:
        current = board.current_player

        # In Xiangqi, having no legal move is always a loss (checkmate
        # and stalemate/困毙 are both losses -- see Rule for details).
        if Rule.is_game_over(board, current):
            return Board.opponent(current), moves

        result = engines[current].choose_move(board, current)
        board.move(result.best_move.from_pos, result.best_move.to_pos)
        moves += 1

    return None, moves  # move limit reached: treated as a draw


def estimate_elo_diff(win_rate):
    """
    Standard Elo-difference estimate from a win rate (draws counted as
    half a point). Returns None at the 0%/100% extremes, where the
    formula is undefined.
    """
    if win_rate <= 0 or win_rate >= 1:
        return None
    return 400 * math.log10(win_rate / (1 - win_rate))


def run_match(engine_a_factory, engine_b_factory, games, max_moves):
    a_wins = 0
    b_wins = 0
    draws = 0

    for i in range(games):
        # Alternate colors every game so neither engine always enjoys
        # the first-move advantage.
        if i % 2 == 0:
            red, black = engine_a_factory(), engine_b_factory()
            a_is_red = True
        else:
            red, black = engine_b_factory(), engine_a_factory()
            a_is_red = False

        winner, moves = play_game(red, black, max_moves)

        if winner is None:
            draws += 1
            outcome = "draw (move limit)"
        elif (winner == Color.RED) == a_is_red:
            a_wins += 1
            outcome = "A wins"
        else:
            b_wins += 1
            outcome = "B wins"

        print(f"  game {i + 1:>3}/{games}: {outcome} ({moves} moves)")

    return a_wins, b_wins, draws


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=10, help="number of games to play")
    parser.add_argument("--depth", type=int, default=2, help="SearchEngine search depth")
    parser.add_argument("--max-moves", type=int, default=150, help="per-game move limit")
    args = parser.parse_args()

    print(f"AlphaZetaChess Benchmark: SearchEngine(depth={args.depth}) [A] "
          f"vs RandomEngine [B], {args.games} games\n")

    t0 = time.time()
    a_wins, b_wins, draws = run_match(
        lambda: SearchEngine(depth=args.depth),
        lambda: RandomEngine(),
        games=args.games,
        max_moves=args.max_moves,
    )
    elapsed = time.time() - t0

    win_rate = (a_wins + 0.5 * draws) / args.games
    elo_diff = estimate_elo_diff(win_rate)

    print()
    print(f"Results over {args.games} games ({elapsed:.1f}s total):")
    print(f"  SearchEngine(depth={args.depth}) wins : {a_wins}")
    print(f"  RandomEngine wins                     : {b_wins}")
    print(f"  Draws (move limit)                    : {draws}")
    print(f"  SearchEngine score rate               : {win_rate:.0%}")
    if elo_diff is not None:
        print(f"  Estimated Elo difference              : {elo_diff:+.0f}")
    else:
        print("  Estimated Elo difference              : undefined (100%/0% score)")


if __name__ == "__main__":
    main()

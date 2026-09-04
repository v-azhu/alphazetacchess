"""V0.5.2b opening randomization tests."""

import random

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.selfplay.opening_randomization import RandomizedOpeningEngine


def test_random_prob_zero_always_defers_to_the_wrapped_engine():
    board = Board()
    inner = SearchEngine(depth=1)
    wrapped = RandomizedOpeningEngine(inner, random_plies=10, random_prob=0.0)

    expected = inner.choose_move(board, Color.RED)
    actual = wrapped.choose_move(board, Color.RED)

    assert (actual.best_move.from_pos, actual.best_move.to_pos) == (
        expected.best_move.from_pos, expected.best_move.to_pos,
    )


def test_random_prob_one_always_picks_a_legal_random_move():
    board = Board()
    inner = SearchEngine(depth=1)
    wrapped = RandomizedOpeningEngine(
        inner, random_plies=10, random_prob=1.0, rng=random.Random(0)
    )

    result = wrapped.choose_move(board, Color.RED)

    legal_moves = Rule.generate_legal_moves(board, Color.RED)
    legal_pairs = {(m.from_pos, m.to_pos) for m in legal_moves}
    assert (result.best_move.from_pos, result.best_move.to_pos) in legal_pairs


def test_randomization_only_applies_within_random_plies():
    board = Board()
    inner = SearchEngine(depth=1)
    wrapped = RandomizedOpeningEngine(
        inner, random_plies=1, random_prob=1.0, rng=random.Random(0)
    )

    wrapped.choose_move(board, Color.RED)  # ply 1: eligible for randomization
    board.move((0, 0), (0, 1))  # arbitrary legal-ish state change for the 2nd call's board

    # ply 2 is beyond random_plies=1, so it must exactly match the
    # wrapped engine's own choice regardless of rng/random_prob.
    expected = inner.choose_move(board, Color.BLACK)
    actual = wrapped.choose_move(board, Color.BLACK)

    assert (actual.best_move.from_pos, actual.best_move.to_pos) == (
        expected.best_move.from_pos, expected.best_move.to_pos,
    )


def test_repeated_self_play_with_randomization_produces_different_games():
    from alphazetacchess.selfplay.recorder import play_recorded_game

    def make_engine(seed):
        return RandomizedOpeningEngine(
            SearchEngine(depth=1), random_plies=6, random_prob=0.5, rng=random.Random(seed)
        )

    game_a = play_recorded_game(make_engine(1), make_engine(2), max_moves=12)
    game_b = play_recorded_game(make_engine(3), make_engine(4), max_moves=12)

    # This is the actual issue the uploaded 10-game batch demonstrated:
    # fully deterministic self-play produces byte-identical games. With
    # randomization and different seeds, they should differ.
    assert game_a["moves"] != game_b["moves"]

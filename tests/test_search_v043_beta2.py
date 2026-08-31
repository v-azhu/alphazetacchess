from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.search import SearchEngine


def test_default_mobility_is_disabled():
    engine = SearchEngine(depth=1)
    assert engine.use_mobility is False
    assert engine.mobility_weight == 1


def test_search_engine_mobility_configuration_is_reachable():
    off = SearchEngine(depth=1, use_mobility=False)
    on = SearchEngine(depth=1, use_mobility=True, mobility_weight=3)

    assert off.use_mobility is False
    assert on.use_mobility is True
    assert on.mobility_weight == 3


def test_search_default_matches_explicit_mobility_off():
    board = Board()

    implicit = SearchEngine(
        depth=1,
        iterative_deepening=False,
        use_transposition_table=False,
        use_pvs=False,
        use_quiescence=False,
    ).choose_move(board, Color.RED)

    explicit = SearchEngine(
        depth=1,
        iterative_deepening=False,
        use_transposition_table=False,
        use_pvs=False,
        use_quiescence=False,
        use_mobility=False,
    ).choose_move(board, Color.RED)

    assert implicit.score == explicit.score
    assert (
        implicit.best_move.from_pos,
        implicit.best_move.to_pos,
    ) == (
        explicit.best_move.from_pos,
        explicit.best_move.to_pos,
    )
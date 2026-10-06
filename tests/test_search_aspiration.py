import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine


def move_key(move):
    return move.from_pos, move.to_pos


@pytest.mark.parametrize("window", [1, 50, 100, 200])
def test_aspiration_search_matches_full_window_search(window):
    board = Board()
    baseline = SearchEngine(depth=3, aspiration_window=10_000)
    aspiration = SearchEngine(depth=3, aspiration_window=window)

    baseline_result = baseline.choose_move(board, Color.RED)
    aspiration_result = aspiration.choose_move(board, Color.RED)

    assert aspiration_result.score == baseline_result.score
    assert move_key(aspiration_result.best_move) == move_key(baseline_result.best_move)
    assert aspiration_result.depth == baseline_result.depth == 3
    if window == 1:
        assert aspiration.aspiration_researches > 0
    assert board.zobrist_hash == Board().zobrist_hash


def test_fixed_depth_search_does_not_use_aspiration_guess():
    board = Board()
    engine = SearchEngine(depth=2, iterative_deepening=False, aspiration_window=1)
    result = engine.choose_move(board, Color.RED)

    assert result.depth == 2
    assert engine.aspiration_researches == 0
    assert board.zobrist_hash == Board().zobrist_hash


@pytest.mark.parametrize("guess", [-100_000, 100_000], ids=["fail-high", "fail-low"])
def test_out_of_window_root_score_retries_with_full_window(guess):
    board = Board()
    original_hash = board.zobrist_hash
    engine = SearchEngine(depth=2, aspiration_window=1_000)
    baseline = SearchEngine(depth=2, aspiration_window=100_000)
    legal_moves = Rule.generate_legal_moves(board, Color.RED)

    expected = baseline._search_fixed_depth(
        board, Color.RED, legal_moves, depth=2
    )
    engine._aspiration_guess = guess
    actual = engine._search_fixed_depth(board, Color.RED, legal_moves, depth=2)

    assert actual.score == expected.score
    assert engine.aspiration_researches == 1
    assert board.zobrist_hash == original_hash


def test_aspiration_is_skipped_without_alpha_beta_pruning():
    engine = SearchEngine(
        depth=2,
        use_alpha_beta=False,
        aspiration_window=1,
    )

    engine.choose_move(Board(), Color.RED)

    assert engine.aspiration_researches == 0


@pytest.mark.parametrize(
    "opening_moves",
    [
        (),
        (
            ((1, 0), (2, 2)),
            ((1, 9), (2, 7)),
            ((1, 2), (1, 4)),
            ((1, 7), (1, 5)),
        ),
    ],
    ids=["initial", "early-development"],
)
def test_depth_four_aspiration_matches_full_window_score(opening_moves):
    board = Board()
    for source, target in opening_moves:
        board.move(source, target)
    color = board.current_player
    original_hash = board.zobrist_hash

    baseline = SearchEngine(depth=4, aspiration_window=10_000)
    aspiration = SearchEngine(depth=4, aspiration_window=100)
    baseline_result = baseline.choose_move(board, color)
    aspiration_result = aspiration.choose_move(board, color)

    assert aspiration_result.score == baseline_result.score
    assert aspiration_result.depth == baseline_result.depth == 4
    assert any(
        move_key(legal_move) == move_key(aspiration_result.best_move)
        for legal_move in Rule.generate_legal_moves(board, color)
    )
    assert board.zobrist_hash == original_hash


@pytest.mark.parametrize("window", [0, -1])
def test_aspiration_window_must_be_positive(window):
    with pytest.raises(ValueError, match="aspiration_window must be at least 1"):
        SearchEngine(aspiration_window=window)

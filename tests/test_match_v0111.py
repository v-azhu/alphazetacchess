"""Focused tests for match-runner helpers; no external engine is required."""
import pytest

from tools.match import candidate_score, canonical_hash, validate_game
from alphazetacchess.core.fen import board_to_fen
from alphazetacchess.core.board import Board


def test_canonical_hash_is_order_independent():
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})


@pytest.mark.parametrize(
    ("result", "color", "expected"),
    [
        ("RED_WINS", "RED", 1.0),
        ("BLACK_WINS", "RED", 0.0),
        ("DRAW", "RED", 0.5),
        ("BLACK_WINS", "BLACK", 1.0),
        ("RED_WINS", "BLACK", 0.0),
    ],
)
def test_candidate_score(result, color, expected):
    assert candidate_score(result, color) == expected


def test_replay_validation_accepts_a_move_limit_draw():
    board = Board()
    record = {
        "initial_fen": board_to_fen(board),
        "moves": [],
        "total_moves": 0,
        "result": "DRAW",
    }
    validate_game(record, max_moves=0)


def test_replay_validation_rejects_wrong_result_for_empty_nonterminal_game():
    board = Board()
    record = {
        "initial_fen": board_to_fen(board),
        "moves": [],
        "total_moves": 0,
        "result": "RED_WINS",
    }
    with pytest.raises(ValueError):
        validate_game(record, max_moves=0)

"""Focused tests for match-runner helpers; no external engine is required."""
import pytest

from tools.match import (
    candidate_score, canonical_hash, parse_command, partition_openings, validate_game,
)
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


def test_parse_command_preserves_executable_path_with_spaces():
    assert parse_command(r"C:\Program Files\Pikafish\pikafish.exe") == [
        r"C:\Program Files\Pikafish\pikafish.exe"
    ]


def test_parse_command_supports_json_argv():
    assert parse_command('["engine.exe", "--option", "value"]') == [
        "engine.exe", "--option", "value"
    ]



def test_partition_openings_preserves_every_pair_exactly_once():
    openings = [{"opening_index": index} for index in range(11)]
    chunks = partition_openings(openings, workers=3)

    flattened = [opening for chunk in chunks for opening in chunk]
    assert len(chunks) == 3
    assert sorted(item["opening_index"] for item in flattened) == list(range(11))
    assert len({item["opening_index"] for item in flattened}) == len(openings)


def test_partition_openings_is_balanced_and_caps_workers_to_work():
    openings = [{"opening_index": index} for index in range(2)]
    chunks = partition_openings(openings, workers=8)

    assert len(chunks) == 2
    assert [len(chunk) for chunk in chunks] == [1, 1]


def test_partition_openings_rejects_non_positive_worker_count():
    with pytest.raises(ValueError, match="at least 1"):
        partition_openings([], workers=0)

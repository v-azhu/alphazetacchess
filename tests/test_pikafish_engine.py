import os
import sys

import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.pikafish import PikafishEngine


_FAKE_ENGINE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "fake_uci_engine.py"
)


def _engine():
    return PikafishEngine(
        [sys.executable, _FAKE_ENGINE, "cp", "37"],
        network_path="/tmp/fake.nnue",
        search_depth=4,
    )


def test_pikafish_adapter_returns_legal_move_and_search_score():
    board = Board()
    with _engine() as engine:
        result = engine.choose_move(board, Color.RED)
        assert engine.engine_info == ("id name FakeEngine",)

    assert result.best_move.from_pos == (0, 0)
    assert result.best_move.to_pos == (0, 1)
    assert result.score == 37
    assert result.depth == 1


def test_pikafish_adapter_rejects_wrong_side_to_move():
    with _engine() as engine:
        with pytest.raises(ValueError, match="side to move"):
            engine.choose_move(Board(), Color.BLACK)


def test_pikafish_adapter_rejects_illegal_external_move():
    command = [sys.executable, _FAKE_ENGINE, "cp", "0"]
    board = Board()
    board.move((0, 0), (0, 1))
    with PikafishEngine(command, network_path="/tmp/fake.nnue") as engine:
        with pytest.raises(RuntimeError, match="illegal move"):
            engine.choose_move(board, Color.BLACK)

import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen, board_to_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from tools.trace_principal_variation import trace_candidate


def test_trace_candidate_restores_board_and_emits_legal_tt_line():
    board = Board()
    board.move((1, 0), (2, 2))
    board.move((1, 9), (2, 7))
    root_move = Rule.generate_legal_moves(board, Color.RED)[0]
    original_fen = board_to_fen(board)
    original_hash = board.zobrist_hash
    original_position_history = list(board.position_history)
    original_repetition_history = list(board.repetition_history)

    trace = trace_candidate(
        board,
        Color.RED,
        (root_move.from_pos, root_move.to_pos),
        depth=3,
    )

    assert trace["principal_line"][0] == (root_move.from_pos, root_move.to_pos)
    assert len(trace["captures"]) == len(trace["principal_line"])
    assert isinstance(trace["static_score"], (int, float))
    assert isinstance(trace["searched_score"], (int, float))
    assert board_to_fen(board) == original_fen
    assert board.zobrist_hash == original_hash
    assert board.position_history == original_position_history
    assert board.repetition_history == original_repetition_history

    replay = board_from_fen(original_fen)
    for index, move_key in enumerate(trace["principal_line"]):
        side_to_move = Color.RED if index % 2 == 0 else Color.BLACK
        assert replay.current_player == side_to_move
        legal = Rule.generate_legal_moves(replay, side_to_move)
        assert any(
            move.from_pos == move_key[0] and move.to_pos == move_key[1]
            for move in legal
        )
        replay.move(*move_key)


def test_trace_candidate_rejects_illegal_root_move():
    with pytest.raises(ValueError, match="is not legal"):
        trace_candidate(Board(), Color.RED, ((0, 0), (1, 1)), depth=2)


def test_trace_candidate_requires_side_to_move():
    board = Board()
    board.move((1, 0), (2, 2))

    with pytest.raises(ValueError, match="must match"):
        trace_candidate(board, Color.RED, ((1, 9), (2, 7)), depth=2)


def test_trace_candidate_rejects_nonpositive_depth():
    with pytest.raises(ValueError, match="depth must be at least 1"):
        trace_candidate(Board(), Color.RED, ((1, 0), (2, 2)), depth=0)

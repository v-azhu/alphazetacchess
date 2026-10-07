from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine
from tools.compare_null_move_paired import TimedSearch


def test_null_move_preserves_board_and_restores_exact_state():
    board = Board()
    before_hash = board.zobrist_hash
    before_player = board.current_player
    before_history = list(board.history)
    before_positions = list(board.position_history)
    before_repetitions = list(board.repetition_history)
    before_text = str(board)

    board.null_move()

    assert board.current_player == Color.BLACK
    assert board.zobrist_hash != before_hash
    assert str(board) == before_text
    assert board.history == before_history
    assert board.position_history[-1] == board.zobrist_hash
    assert board.repetition_history == before_repetitions

    board.undo_null_move()

    assert board.zobrist_hash == before_hash
    assert board.current_player == before_player
    assert board.history == before_history
    assert board.position_history == before_positions
    assert board.repetition_history == before_repetitions
    assert str(board) == before_text


def test_null_move_is_invisible_to_normal_move_undo_history():
    board = Board()
    before_hash = board.zobrist_hash
    move = (4, 0), (4, 1)

    board.null_move()
    board.undo_null_move()
    board.move(*move)
    board.undo()

    assert board.zobrist_hash == before_hash
    assert board.current_player == Color.RED
    assert board.history == []
    assert len(board.position_history) == 1


def test_null_move_is_disabled_in_check():
    board = board_from_fen("4k4/9/9/9/9/9/9/4r4/9/4K4 w - - 0 1")
    engine = SearchEngine(
        depth=4,
        use_null_move=True,
        null_move_min_pieces=2,
    )
    legal_moves = Rule.generate_legal_moves(board, Color.RED)

    assert Rule.is_in_check(board, Color.RED)
    assert len(legal_moves) > 1
    assert engine._null_move_allowed(board, Color.RED, 4, 1, legal_moves) is False


def test_null_move_disabled_for_small_endgame_position():
    board = board_from_fen("4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1")
    engine = SearchEngine(
        depth=4,
        use_null_move=True,
        null_move_min_pieces=7,
    )
    legal_moves = Rule.generate_legal_moves(board, Color.RED)

    assert engine._null_move_allowed(board, Color.RED, 4, 1, legal_moves) is False


def test_null_move_search_restores_board_state():
    board = Board()
    before_hash = board.zobrist_hash
    before_player = board.current_player
    before_text = str(board)

    engine = SearchEngine(
        depth=3,
        use_null_move=True,
        null_move_min_pieces=7,
    )
    result = engine.choose_move(board, Color.RED)

    assert result.best_move is not None
    assert board.zobrist_hash == before_hash
    assert board.current_player == before_player
    assert str(board) == before_text
    assert board.history == []
    assert len(board.position_history) == 1


def test_paired_null_move_runner_can_hold_lmr_constant():
    baseline = TimedSearch(100, 4, use_null_move=False, use_lmr=True)
    variant = TimedSearch(100, 4, use_null_move=True, use_lmr=True)

    assert baseline.engine.use_late_move_reductions is True
    assert baseline.engine.use_null_move is False
    assert variant.engine.use_late_move_reductions is True
    assert variant.engine.use_null_move is True

"""V0.4.5 piece coordination (Doubled Rooks, Rook-Cannon Battery) tests."""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.evaluation import evaluate
from alphazetacchess.engine.piece_coordination import (
    piece_coordination_score,
    piece_coordination_balance,
    DOUBLED_ROOKS_BONUS,
    ROOK_CANNON_BATTERY_BONUS,
)


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def put(board, piece_type, color, x, y):
    board.board[y][x] = Piece(piece_type, color, x, y)


def test_single_rook_alone_scores_zero():
    board = empty_board()
    put(board, PieceType.ROOK, Color.RED, 0, 0)

    assert piece_coordination_score(board, Color.RED) == 0


def test_doubled_rooks_on_same_file_score_the_bonus():
    board = empty_board()
    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.ROOK, Color.RED, 0, 5)  # same file, different rank

    assert piece_coordination_score(board, Color.RED) == DOUBLED_ROOKS_BONUS


def test_rooks_on_different_files_score_zero():
    board = empty_board()
    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.ROOK, Color.RED, 1, 0)  # different file

    assert piece_coordination_score(board, Color.RED) == 0


def test_rook_cannon_battery_on_same_file_scores_the_bonus():
    board = empty_board()
    put(board, PieceType.ROOK, Color.RED, 4, 0)
    put(board, PieceType.CANNON, Color.RED, 4, 7)  # same file, far apart

    assert piece_coordination_score(board, Color.RED) == ROOK_CANNON_BATTERY_BONUS


def test_doubled_rooks_and_battery_stack_on_the_same_file():
    board = empty_board()
    put(board, PieceType.ROOK, Color.RED, 4, 0)
    put(board, PieceType.ROOK, Color.RED, 4, 2)
    put(board, PieceType.CANNON, Color.RED, 4, 7)

    expected = DOUBLED_ROOKS_BONUS + ROOK_CANNON_BATTERY_BONUS
    assert piece_coordination_score(board, Color.RED) == expected


def test_horse_and_elephant_do_not_count_toward_coordination():
    # Only Rook/Cannon file-sharing counts for this first version -- see
    # docs/v0.4.5.md "deliberately out of scope".
    board = empty_board()
    put(board, PieceType.HORSE, Color.RED, 4, 0)
    put(board, PieceType.ELEPHANT, Color.RED, 4, 2)
    put(board, PieceType.ROOK, Color.RED, 4, 5)

    assert piece_coordination_score(board, Color.RED) == 0


def test_enemy_piece_on_the_same_file_does_not_count():
    board = empty_board()
    put(board, PieceType.ROOK, Color.RED, 4, 0)
    put(board, PieceType.ROOK, Color.BLACK, 4, 9)  # enemy rook, same file

    assert piece_coordination_score(board, Color.RED) == 0


def test_piece_coordination_is_symmetric_between_colors():
    board = empty_board()
    put(board, PieceType.ROOK, Color.RED, 4, 0)
    put(board, PieceType.ROOK, Color.RED, 4, 2)
    put(board, PieceType.ROOK, Color.BLACK, 3, 9)
    put(board, PieceType.ROOK, Color.BLACK, 3, 7)

    assert piece_coordination_balance(board, Color.RED) == -piece_coordination_balance(
        board, Color.BLACK
    )


def test_piece_coordination_disabled_by_default_preserves_v044_evaluation():
    board = Board()

    baseline = evaluate(
        board, Color.RED,
        use_piece_square_tables=True, use_king_safety=True,
        use_mobility=False, use_pawn_structure=False,
    )
    explicit_off = evaluate(
        board, Color.RED,
        use_piece_square_tables=True, use_king_safety=True,
        use_mobility=False, use_pawn_structure=False,
        use_piece_coordination=False,
    )

    assert explicit_off == baseline


def test_piece_coordination_toggle_changes_evaluation_when_relevant():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 3, 9)
    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.ROOK, Color.RED, 0, 5)

    without = evaluate(
        board, Color.RED,
        use_piece_square_tables=False, use_king_safety=False,
        use_mobility=False, use_pawn_structure=False,
        use_piece_coordination=False,
    )
    with_pc = evaluate(
        board, Color.RED,
        use_piece_square_tables=False, use_king_safety=False,
        use_mobility=False, use_pawn_structure=False,
        use_piece_coordination=True,
    )

    assert with_pc - without == DOUBLED_ROOKS_BONUS


def test_search_engine_use_piece_coordination_toggle_reaches_evaluation():
    from alphazetacchess.engine.search import SearchEngine

    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 3, 9)
    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.ROOK, Color.RED, 0, 5)

    with_pc = SearchEngine(use_piece_coordination=True)
    without_pc = SearchEngine(use_piece_coordination=False)

    score_with = with_pc._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )
    score_without = without_pc._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )

    assert score_with == evaluate(board, Color.RED, use_piece_coordination=True)
    assert score_without == evaluate(board, Color.RED, use_piece_coordination=False)
    assert score_with != score_without
